//! Declared normalization and exact comparison of scenario observations.
//!
//! A receipt observation is compared with the compiled expectation only after
//! the pack's declared normalization, which is narrow on purpose:
//!
//! 1. `rootRelativePaths`: an actual-side `path` member that is absolute or
//!    uses `\` is rewritten relative to the run plan's `fixtureRoot`, in POSIX
//!    form, and must stay beneath it;
//! 2. `optionalEmptyFiles`: at most one exact empty regular-file entry is
//!    removed from the named tree on either side;
//! 3. `excludedPaths`: each exact path is removed from both sides, deepest and
//!    highest index first so removals never shift a later target;
//! 4. `unorderedPaths`: each exact path's array is sorted by canonical bytes on
//!    both sides.
//!
//! [`exact_differences`] then reports every structural difference, comparing
//! JSON types before values. Display-content carriers are validated with
//! [`validate_display_content`] for families that declare them.

use std::cmp::Ordering;

use serde_json::{Map, Value};

use super::families::{NormalizationError, Observation};
use super::json::canonical_bytes;
use super::schema::Normalization;

/// One stable path where the actual observation differs from the expected one.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Difference {
    /// `$.a[0].b`-style path.
    pub path: String,
    /// `type_mismatch`, `missing_field`, `extra_field`, `missing_element`,
    /// `extra_element` or `value_mismatch`.
    pub kind: &'static str,
}

/// One token of an exact JSON path.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Token {
    Field(String),
    Index(usize),
}

/// Parses an exact JSON path (`$.a[0].b`) into tokens.
fn tokens(path: &str) -> Result<Vec<Token>, NormalizationError> {
    let invalid = || NormalizationError::new("normalization path is invalid", path);
    let mut rest = path.strip_prefix('$').ok_or_else(invalid)?;
    let mut tokens = Vec::new();
    while !rest.is_empty() {
        if let Some(after) = rest.strip_prefix('.') {
            let end = after
                .find(|c: char| !(c.is_ascii_alphanumeric() || c == '_' || c == '-'))
                .unwrap_or(after.len());
            let name = &after[..end];
            if !name.starts_with(|c: char| c.is_ascii_alphabetic() || c == '_') {
                return Err(invalid());
            }
            tokens.push(Token::Field(name.to_owned()));
            rest = &after[end..];
        } else if let Some(after) = rest.strip_prefix('[') {
            let close = after.find(']').ok_or_else(invalid)?;
            let index = &after[..close];
            let canonical = index == "0"
                || (!index.is_empty()
                    && !index.starts_with('0')
                    && index.bytes().all(|byte| byte.is_ascii_digit()));
            if !canonical {
                return Err(invalid());
            }
            tokens.push(Token::Index(index.parse().map_err(|_| invalid())?));
            rest = &after[close + 1..];
        } else {
            return Err(invalid());
        }
    }
    if tokens.is_empty() {
        return Err(invalid());
    }
    Ok(tokens)
}

/// Resolves `tokens` in `value`; `Ok(None)` when a member or element is
/// absent.
fn resolve<'a>(
    value: &'a mut Value,
    tokens: &[Token],
    path: &str,
) -> Result<Option<&'a mut Value>, NormalizationError> {
    let mut current = value;
    for token in tokens {
        current = match token {
            Token::Field(name) => {
                let Value::Object(map) = current else {
                    return Err(NormalizationError::new(
                        "normalization field traverses a non-object value",
                        path,
                    ));
                };
                match map.get_mut(name) {
                    Some(child) => child,
                    None => return Ok(None),
                }
            }
            Token::Index(index) => {
                let Value::Array(items) = current else {
                    return Err(NormalizationError::new(
                        "normalization index traverses a non-array value",
                        path,
                    ));
                };
                match items.get_mut(*index) {
                    Some(child) => child,
                    None => return Ok(None),
                }
            }
        };
    }
    Ok(Some(current))
}

/// Removes the member or element at `tokens` when it is present.
fn remove(value: &mut Value, tokens: &[Token], path: &str) -> Result<(), NormalizationError> {
    let (last, parents) = tokens.split_last().expect("paths have at least one token");
    let Some(parent) = resolve(value, parents, path)? else {
        return Ok(());
    };
    match last {
        Token::Field(name) => {
            let Value::Object(map) = parent else {
                return Err(NormalizationError::new(
                    "normalization exclusion targets a field on a non-object",
                    path,
                ));
            };
            map.remove(name);
        }
        Token::Index(index) => {
            let Value::Array(items) = parent else {
                return Err(NormalizationError::new(
                    "normalization exclusion targets an index on a non-array",
                    path,
                ));
            };
            if *index < items.len() {
                items.remove(*index);
            }
        }
    }
    Ok(())
}

/// Orders exclusions so that deeper paths, then larger indices, come first
/// when sorted in reverse: removing them first never shifts a later target.
fn exclusion_order(left: &[Token], right: &[Token]) -> Ordering {
    left.len().cmp(&right.len()).then_with(|| {
        for (a, b) in left.iter().zip(right) {
            let ordering = match (a, b) {
                (Token::Field(a), Token::Field(b)) => a.cmp(b),
                (Token::Index(a), Token::Index(b)) => a.cmp(b),
                // Python compared ("field", name) with ("index", n) tuples:
                // "field" sorts before "index".
                (Token::Field(_), Token::Index(_)) => Ordering::Less,
                (Token::Index(_), Token::Field(_)) => Ordering::Greater,
            };
            if ordering != Ordering::Equal {
                return ordering;
            }
        }
        Ordering::Equal
    })
}

/// Applies the scenario's declared normalization to both observations.
///
/// `fixture_root` is the run plan's absolute `fixtureRoot`, the base for
/// `rootRelativePaths`.
///
/// # Errors
///
/// Returns a [`NormalizationError`] when a declared path cannot be applied
/// (it traverses the wrong type, or an unordered path is not an array), an
/// actual path escapes the fixture root, or an optional empty file is
/// malformed.
pub(crate) fn normalize(
    expected: Map<String, Value>,
    actual: Map<String, Value>,
    normalization: &Normalization,
    fixture_root: &str,
) -> Result<(Observation, Observation), NormalizationError> {
    let mut expected = Value::Object(expected);
    let mut actual = Value::Object(actual);
    if normalization.root_relative_paths {
        relativize(&mut expected, &mut actual, fixture_root, "$", None)?;
    }
    // Optional evidence is validated before broader transforms could hide a
    // malformed file entry.
    for optional in normalization.optional_empty_files.iter().flatten() {
        for side in [&mut expected, &mut actual] {
            remove_optional_empty_file(side, &optional.path, &optional.relative_path)?;
        }
    }
    let mut exclusions = Vec::new();
    for exclusion in &normalization.excluded_paths {
        exclusions.push((tokens(&exclusion.path)?, exclusion.path.as_str()));
    }
    exclusions.sort_by(|(left, _), (right, _)| exclusion_order(right, left));
    for (tokens, path) in &exclusions {
        remove(&mut expected, tokens, path)?;
        remove(&mut actual, tokens, path)?;
    }
    for path in &normalization.unordered_paths {
        let tokens = tokens(path)?;
        for (label, side) in [("expected", &mut expected), ("actual", &mut actual)] {
            match resolve(side, &tokens, path)? {
                None => {}
                Some(Value::Array(items)) => items.sort_by_key(canonical_bytes),
                Some(_) => {
                    return Err(NormalizationError::new(
                        format!("declared unordered path resolves to a non-array {label} value"),
                        path,
                    ));
                }
            }
        }
    }
    match (expected, actual) {
        (Value::Object(expected), Value::Object(actual)) => Ok((expected, actual)),
        _ => unreachable!("normalization keeps both observations objects"),
    }
}

/// Walks both sides in parallel and rewrites actual-side `path` carriers that
/// are absolute or use `\`.
fn relativize(
    expected: &mut Value,
    actual: &mut Value,
    fixture_root: &str,
    path: &str,
    field: Option<&str>,
) -> Result<(), NormalizationError> {
    match (expected, actual) {
        (Value::Object(expected), Value::Object(actual)) => {
            let mut keys: Vec<String> = expected
                .keys()
                .filter(|key| actual.contains_key(*key))
                .cloned()
                .collect();
            keys.sort();
            for key in keys {
                let child = format!("{path}.{key}");
                let (Some(left), Some(right)) = (expected.get_mut(&key), actual.get_mut(&key))
                else {
                    continue;
                };
                relativize(left, right, fixture_root, &child, Some(&key))?;
            }
        }
        (Value::Array(expected), Value::Array(actual)) => {
            for (index, (left, right)) in expected.iter_mut().zip(actual.iter_mut()).enumerate() {
                relativize(
                    left,
                    right,
                    fixture_root,
                    &format!("{path}[{index}]"),
                    field,
                )?;
            }
        }
        // The durable-effect and display-content shapes reserve `path` for
        // path payloads; every other scalar stays exact domain data.
        (Value::String(_), Value::String(value))
            if field == Some("path")
                && (value.starts_with('/')
                    || is_windows_absolute(value)
                    || value.contains('\\')) =>
        {
            *value = fixture_relative(value, fixture_root, path)?;
        }
        _ => {}
    }
    Ok(())
}

/// Whether `value` is absolute in Windows terms: a drive with a root
/// (`C:\`, `C:/`) or a UNC share (`\\server\share`).
fn is_windows_absolute(value: &str) -> bool {
    windows_anchor(value).is_some()
}

/// The lowercased anchor (drive or UNC share) of a Windows-absolute path, and
/// the remaining text.
fn windows_anchor(value: &str) -> Option<(String, &str)> {
    let bytes = value.as_bytes();
    let separator = |byte: u8| byte == b'\\' || byte == b'/';
    if bytes.len() >= 3 && bytes[0].is_ascii_alphabetic() && bytes[1] == b':' && separator(bytes[2])
    {
        return Some((value[..2].to_ascii_lowercase(), &value[3..]));
    }
    if bytes.len() >= 2 && separator(bytes[0]) && separator(bytes[1]) {
        let rest = &value[2..];
        let mut pieces = rest.splitn(3, ['\\', '/']);
        let server = pieces.next().filter(|piece| !piece.is_empty())?;
        let share = pieces.next().filter(|piece| !piece.is_empty())?;
        let remainder = pieces.next().unwrap_or("");
        return Some((
            format!("\\\\{}\\{}", server.to_lowercase(), share.to_lowercase()),
            remainder,
        ));
    }
    None
}

/// Path components with empty and `.` components dropped, as pathlib does.
fn parts(text: &str, separators: &[char]) -> Vec<String> {
    text.split(separators)
        .filter(|part| !part.is_empty() && *part != ".")
        .map(str::to_owned)
        .collect()
}

/// Projects one actual-side path beneath `fixture_root` to canonical POSIX
/// form.
fn fixture_relative(
    value: &str,
    fixture_root: &str,
    path: &str,
) -> Result<String, NormalizationError> {
    let outside = || {
        NormalizationError::new(
            "declared absolute path is outside the prepared fixture root",
            path,
        )
    };
    let beneath = || {
        NormalizationError::new(
            "declared fixture path must remain beneath the fixture root",
            path,
        )
    };
    let relative: Vec<String> = if let Some((anchor, rest)) = windows_anchor(value) {
        // Windows paths compare case-insensitively, as `PureWindowsPath` does.
        let (root_anchor, root_rest) = windows_anchor(fixture_root).ok_or_else(outside)?;
        let value_parts = parts(rest, &['\\', '/']);
        let root_parts = parts(root_rest, &['\\', '/']);
        let prefix = root_parts.len() <= value_parts.len()
            && root_parts
                .iter()
                .zip(&value_parts)
                .all(|(a, b)| a.to_lowercase() == b.to_lowercase());
        if anchor != root_anchor || !prefix {
            return Err(outside());
        }
        value_parts[root_parts.len()..].to_vec()
    } else if value.starts_with('/') {
        let root = fixture_root.replace('\\', "/");
        if !root.starts_with('/') {
            return Err(outside());
        }
        let value_parts = parts(value, &['/']);
        let root_parts = parts(&root, &['/']);
        if !value_parts.starts_with(&root_parts) {
            return Err(outside());
        }
        value_parts[root_parts.len()..].to_vec()
    } else {
        let normalized = value.replace('\\', "/");
        if normalized
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
        {
            return Err(beneath());
        }
        return Ok(normalized);
    };
    if relative.is_empty() || relative.iter().any(|part| part == "..") {
        return Err(beneath());
    }
    Ok(relative.join("/"))
}

/// Removes at most one declared empty file from the tree at `path`, after
/// checking every entry is a well-formed path carrier and the declared file,
/// when present, is exactly an empty regular file.
fn remove_optional_empty_file(
    value: &mut Value,
    path: &str,
    relative_path: &str,
) -> Result<(), NormalizationError> {
    let tokens = tokens(path)?;
    let Some(Value::Array(tree)) = resolve(value, &tokens, path)? else {
        return Err(NormalizationError::new(
            "optional empty file requires a present tree array",
            path,
        ));
    };
    let mut matching = Vec::new();
    for (index, entry) in tree.iter().enumerate() {
        let carrier = entry
            .get("path")
            .and_then(Value::as_object)
            .filter(|carrier| carrier.len() == 1)
            .and_then(|carrier| carrier.get("path"))
            .and_then(Value::as_str);
        let kind = entry.get("kind").and_then(Value::as_str);
        let (Some(entry_path), Some("file" | "directory")) = (carrier, kind) else {
            return Err(NormalizationError::new(
                "optional empty file checkpoint has a malformed path carrier",
                path,
            ));
        };
        if entry_path == relative_path {
            matching.push(index);
            let exact = serde_json::json!({
                "path": {"path": relative_path},
                "kind": "file",
                "bytesHex": "",
            });
            if entry != &exact {
                return Err(NormalizationError::new(
                    "optional empty file must be an exact empty regular file",
                    path,
                ));
            }
        }
    }
    if matching.len() > 1 {
        return Err(NormalizationError::new(
            "optional empty file checkpoint contains duplicate entries",
            path,
        ));
    }
    if let Some(index) = matching.first() {
        tree.remove(*index);
    }
    Ok(())
}

/// The variant name of a JSON value, for type comparison.
fn kind(value: &Value) -> u8 {
    match value {
        Value::Null => 0,
        Value::Bool(_) => 1,
        Value::Number(_) => 2,
        Value::String(_) => 3,
        Value::Array(_) => 4,
        Value::Object(_) => 5,
    }
}

/// Every structural difference between `expected` and `actual`, in
/// deterministic path order (object members sorted by name).
///
/// Types compare first, so `true` never equals `1`.
pub(crate) fn exact_differences(expected: &Value, actual: &Value) -> Vec<Difference> {
    let mut differences = Vec::new();
    differ(expected, actual, "$", &mut differences);
    differences
}

fn differ(expected: &Value, actual: &Value, path: &str, out: &mut Vec<Difference>) {
    let difference = |path: String, kind| Difference { path, kind };
    if kind(expected) != kind(actual) {
        out.push(difference(path.to_owned(), "type_mismatch"));
        return;
    }
    match (expected, actual) {
        (Value::Object(expected), Value::Object(actual)) => {
            let mut missing: Vec<&String> = expected
                .keys()
                .filter(|key| !actual.contains_key(*key))
                .collect();
            missing.sort();
            for key in missing {
                out.push(difference(format!("{path}.{key}"), "missing_field"));
            }
            let mut extra: Vec<&String> = actual
                .keys()
                .filter(|key| !expected.contains_key(*key))
                .collect();
            extra.sort();
            for key in extra {
                out.push(difference(format!("{path}.{key}"), "extra_field"));
            }
            let mut shared: Vec<&String> = expected
                .keys()
                .filter(|key| actual.contains_key(*key))
                .collect();
            shared.sort();
            for key in shared {
                differ(&expected[key], &actual[key], &format!("{path}.{key}"), out);
            }
        }
        (Value::Array(expected), Value::Array(actual)) => {
            let shared = expected.len().min(actual.len());
            for index in 0..shared {
                differ(
                    &expected[index],
                    &actual[index],
                    &format!("{path}[{index}]"),
                    out,
                );
            }
            for index in shared..expected.len() {
                out.push(difference(format!("{path}[{index}]"), "missing_element"));
            }
            for index in shared..actual.len() {
                out.push(difference(format!("{path}[{index}]"), "extra_element"));
            }
        }
        _ if expected != actual => out.push(difference(path.to_owned(), "value_mismatch")),
        _ => {}
    }
}

/// Validates the actual display-content carriers at the locations the
/// expected observation establishes.
///
/// A member holding `segments`, or anything under a `displayContent` member,
/// is a display line: exactly `{severity, segments}`, with each segment
/// exactly `{kind, text, path, count}` and only its kind's payload set.
///
/// # Errors
///
/// Returns a [`NormalizationError`] at the first malformed carrier.
pub(crate) fn validate_display_content(
    expected: &Value,
    actual: &Value,
) -> Result<(), NormalizationError> {
    carriers(expected, actual, "$", false)
}

fn carriers(
    expected: &Value,
    actual: &Value,
    path: &str,
    display: bool,
) -> Result<(), NormalizationError> {
    if display {
        if let Value::Array(lines) = expected {
            let Value::Array(actual_lines) = actual else {
                return Err(NormalizationError::new(
                    "display content must be an ordered array of line objects",
                    path,
                ));
            };
            for (index, line) in lines.iter().enumerate() {
                display_line(line, &format!("{path}[{index}]"))?;
            }
            for (index, line) in actual_lines.iter().enumerate() {
                display_line(line, &format!("{path}[{index}]"))?;
            }
        } else {
            display_line(expected, path)?;
            display_line(actual, path)?;
        }
        return Ok(());
    }
    match (expected, actual) {
        (Value::Object(map), _) if map.contains_key("segments") => {
            display_line(expected, path)?;
            display_line(actual, path)
        }
        (Value::Object(expected), Value::Object(actual)) => {
            let mut keys: Vec<&String> = expected
                .keys()
                .filter(|key| actual.contains_key(*key))
                .collect();
            keys.sort();
            for key in keys {
                carriers(
                    &expected[key],
                    &actual[key],
                    &format!("{path}.{key}"),
                    key == "displayContent",
                )?;
            }
            Ok(())
        }
        (Value::Array(expected), Value::Array(actual)) => {
            for (index, (left, right)) in expected.iter().zip(actual).enumerate() {
                carriers(left, right, &format!("{path}[{index}]"), false)?;
            }
            Ok(())
        }
        _ => Ok(()),
    }
}

fn display_line(line: &Value, path: &str) -> Result<(), NormalizationError> {
    let Some(map) = line.as_object().filter(|map| {
        map.len() == 2 && map.contains_key("severity") && map.contains_key("segments")
    }) else {
        return Err(NormalizationError::new(
            "display line must contain exactly severity and segments",
            path,
        ));
    };
    if !matches!(
        map["severity"].as_str(),
        Some("info" | "notice" | "warning" | "failure" | "success")
    ) {
        return Err(NormalizationError::new(
            "display line severity is unsupported",
            &format!("{path}.severity"),
        ));
    }
    let Value::Array(segments) = &map["segments"] else {
        return Err(NormalizationError::new(
            "display line segments must be an ordered array",
            &format!("{path}.segments"),
        ));
    };
    for (index, segment) in segments.iter().enumerate() {
        display_segment(segment, &format!("{path}.segments[{index}]"))?;
    }
    Ok(())
}

fn display_segment(segment: &Value, path: &str) -> Result<(), NormalizationError> {
    let Some(map) = segment.as_object().filter(|map| {
        map.len() == 4
            && ["kind", "text", "path", "count"]
                .iter()
                .all(|key| map.contains_key(*key))
    }) else {
        return Err(NormalizationError::new(
            "display segment must contain exactly kind, text, path, and count",
            path,
        ));
    };
    let kind = map["kind"]
        .as_str()
        .filter(|kind| {
            matches!(
                *kind,
                "text" | "label" | "count" | "path" | "name" | "emphasis"
            )
        })
        .ok_or_else(|| {
            NormalizationError::new(
                "display segment kind is unsupported",
                &format!("{path}.kind"),
            )
        })?;
    let text = map["text"].as_str().ok_or_else(|| {
        NormalizationError::new(
            "display segment text must be a string",
            &format!("{path}.text"),
        )
    })?;
    let segment_path = map["path"].as_str().ok_or_else(|| {
        NormalizationError::new(
            "display segment path must be a string",
            &format!("{path}.path"),
        )
    })?;
    let count = map["count"].as_u64().ok_or_else(|| {
        NormalizationError::new(
            "display segment count must be a non-negative integer",
            &format!("{path}.count"),
        )
    })?;
    match kind {
        "path" => {
            let invalid = segment_path.is_empty()
                || !text.is_empty()
                || count != 0
                || segment_path.contains('\\')
                || segment_path.starts_with('/')
                || is_windows_absolute(segment_path)
                // pathlib drops `.` components, so only `..` escapes.
                || segment_path.split('/').any(|part| part == "..");
            if invalid {
                return Err(NormalizationError::new(
                    "path display segment must use only its canonical relative path payload",
                    path,
                ));
            }
        }
        "count" => {
            if text.is_empty() || !segment_path.is_empty() {
                return Err(NormalizationError::new(
                    "count display segment must use only its text and count payloads",
                    path,
                ));
            }
        }
        _ => {
            if text.is_empty() || !segment_path.is_empty() || count != 0 {
                return Err(NormalizationError::new(
                    "textual display segment must use only its text payload",
                    path,
                ));
            }
        }
    }
    Ok(())
}

#[cfg(test)]
#[path = "compare_tests.rs"]
mod tests;
