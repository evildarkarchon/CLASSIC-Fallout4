//! Mirrored client rules for YAML Data publishing.
//!
//! xtask links no CLASSIC product crate at run time, so the client rules a
//! publish must satisfy are restated here:
//!
//! - the yaml-cache basename rule and the Windows duplicate-name key
//!   (`classic-update-core`, `yaml_update::validate_cache_file_name`);
//! - the `schema_version` / range-bound format (`classic-shared-core`,
//!   `SchemaVersion::from_str`): `MAJOR.MINOR`, ASCII digits only, each part a
//!   `u32`;
//! - the `client-schema-ranges.yaml` shape (`classic-config-core`,
//!   `client_schema_ranges::parse_client_schema_ranges`).
//!
//! The sibling tests run each mirror and the real implementation over one
//! shared table of cases, so the two cannot drift apart silently.
//!
//! Intended deltas from the retired Python tool: version strings follow the
//! client (ASCII digits, `u32` range, no trailing newline accepted), and a
//! ranges entry's `name` must be a YAML string instead of being stringified.

use yaml_rust2::Yaml;

/// Reserved Windows device stems, compared ASCII-uppercase.
const RESERVED_DEVICE_STEMS: [&str; 22] = [
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8",
    "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
];

/// Whether `name` is a plain basename a Windows client can install into its
/// yaml-cache directory.
///
/// String-based and host-independent on purpose: publish validation runs on
/// Linux CI, the files are consumed on Windows. Rejecting separators and `:`
/// also rejects rooted, drive-relative and multi-component paths, so the
/// client's extra host-`Path` checks have nothing left to catch.
pub(crate) fn is_valid_cache_file_name(name: &str) -> bool {
    if name.is_empty() || name == "." || name == ".." {
        return false;
    }
    if name.contains(['/', '\\', ':', '\0']) {
        return false;
    }
    if name.ends_with([' ', '.']) {
        return false;
    }
    !is_reserved_windows_device_basename(name)
}

/// Whether the stem of `name` (text before the first `.`, trailing spaces
/// removed) is a reserved Windows device name. An empty stem is not reserved.
fn is_reserved_windows_device_basename(name: &str) -> bool {
    let stem = name
        .split('.')
        .next()
        .unwrap_or_default()
        .trim_end_matches(' ');
    !stem.is_empty()
        && RESERVED_DEVICE_STEMS
            .iter()
            .any(|reserved| stem.eq_ignore_ascii_case(reserved))
}

/// The identity Windows path lookup gives `name`: trailing spaces and dots
/// dropped, ASCII-lowercased. Two names with the same key collide on disk.
pub(crate) fn windows_normalized_cache_file_key(name: &str) -> String {
    name.trim_end_matches([' ', '.']).to_ascii_lowercase()
}

/// Parses a `MAJOR.MINOR` schema version the way the client does, returning
/// `(major, minor)`, or `None` when the client would refuse it.
pub(crate) fn parse_schema_version(value: &str) -> Option<(u32, u32)> {
    let (major, minor) = value.split_once('.')?;
    let digits = |part: &str| !part.is_empty() && part.bytes().all(|b| b.is_ascii_digit());
    if !digits(major) || !digits(minor) {
        return None;
    }
    Some((major.parse().ok()?, minor.parse().ok()?))
}

/// One problem found in a ranges document, before a path is attached.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct RangeProblem {
    /// Entry name the problem belongs to, when the entry has one (used to
    /// locate the finding's line).
    pub entry_name: Option<String>,
    /// Stable kebab-case rule id.
    pub rule: &'static str,
    /// Human-readable explanation.
    pub message: String,
}

/// A ranges entry that passed every rule.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct RangeEntry {
    /// Shippable file name.
    pub name: String,
    /// `min_client_schema`, exactly as authored.
    pub min_client_schema: String,
    /// `max_client_schema`, exactly as authored.
    pub max_client_schema: String,
}

/// Every entry and every problem in a parsed ranges document.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub(crate) struct Ranges {
    /// Entries that passed every rule, in file order.
    pub entries: Vec<RangeEntry>,
    /// Every string `name` listed, whether or not its entry passed.
    pub listed_names: Vec<String>,
    /// Every problem found; all are collected, unlike the client loader,
    /// which stops at the first.
    pub problems: Vec<RangeProblem>,
}

impl Ranges {
    fn problem(&mut self, entry_name: Option<&str>, rule: &'static str, message: String) {
        self.problems.push(RangeProblem {
            entry_name: entry_name.map(str::to_owned),
            rule,
            message,
        });
    }
}

/// Checks a parsed `client-schema-ranges.yaml` document.
///
/// Applies the client loader's rules (a `files` list of mappings, a string
/// `name`, an optional string `client_schemas_const`, quoted `MAJOR.MINOR`
/// bounds with `min <= max`) plus the publish rules the loader does not own:
/// every name is a valid cache basename, no two names collide on Windows, and
/// the list is not empty.
pub(crate) fn check_ranges(document: &Yaml) -> Ranges {
    let mut ranges = Ranges::default();
    let files = match document {
        Yaml::Hash(_) => document["files"].as_vec(),
        _ => None,
    };
    let Some(files) = files else {
        ranges.problem(
            None,
            "ranges-missing-files",
            "has no top-level 'files' list".to_owned(),
        );
        return ranges;
    };

    let mut seen_keys = std::collections::HashSet::new();
    for (index, entry) in files.iter().enumerate() {
        if !matches!(entry, Yaml::Hash(_)) {
            ranges.problem(
                None,
                "ranges-entry-invalid",
                format!("entry {index} is not a mapping"),
            );
            continue;
        }
        let Some(name) = entry["name"].as_str() else {
            ranges.problem(
                None,
                "ranges-entry-invalid",
                format!("entry {index} has no string 'name'"),
            );
            continue;
        };
        ranges.listed_names.push(name.to_owned());
        let mut ok = true;
        if !is_valid_cache_file_name(name) {
            ranges.problem(
                Some(name),
                "invalid-cache-file-name",
                format!(
                    "entry {}: file name is not a valid cache/install basename",
                    quoted(name)
                ),
            );
            ok = false;
        } else if !seen_keys.insert(windows_normalized_cache_file_key(name)) {
            ranges.problem(
                Some(name),
                "duplicate-cache-file-name",
                format!(
                    "contains duplicate entry for {}; each file must appear at most once",
                    quoted(name)
                ),
            );
            ok = false;
        }
        if !matches!(
            entry["client_schemas_const"],
            Yaml::BadValue | Yaml::String(_)
        ) {
            ranges.problem(
                Some(name),
                "ranges-entry-invalid",
                format!(
                    "entry {}: client_schemas_const must be a string",
                    quoted(name)
                ),
            );
            ok = false;
        }
        let min = check_bound(&mut ranges, name, entry, "min_client_schema");
        let max = check_bound(&mut ranges, name, entry, "max_client_schema");
        let (Some((min, min_point)), Some((max, max_point))) = (min, max) else {
            continue;
        };
        if min_point > max_point {
            ranges.problem(
                Some(name),
                "empty-schema-range",
                format!(
                    "entry {}: min_client_schema={} > max_client_schema={} \
                     (declared range is empty; no client could ever accept it)",
                    quoted(name),
                    quoted(&min),
                    quoted(&max)
                ),
            );
            continue;
        }
        if ok {
            ranges.entries.push(RangeEntry {
                name: name.to_owned(),
                min_client_schema: min,
                max_client_schema: max,
            });
        }
    }
    if files.is_empty() {
        ranges.problem(None, "ranges-no-files", "contains no files".to_owned());
    }
    ranges
}

/// Checks one range bound and returns it with its parsed `(major, minor)`.
fn check_bound(
    ranges: &mut Ranges,
    name: &str,
    entry: &Yaml,
    field: &'static str,
) -> Option<(String, (u32, u32))> {
    let value = match &entry[field] {
        Yaml::BadValue => {
            ranges.problem(
                Some(name),
                "ranges-entry-invalid",
                format!("entry {} missing '{field}'", quoted(name)),
            );
            return None;
        }
        Yaml::String(value) => value,
        other => {
            ranges.problem(
                Some(name),
                "schema-range-not-string",
                format!(
                    "entry {}: {field} must be a quoted string, got {}",
                    quoted(name),
                    describe(other)
                ),
            );
            return None;
        }
    };
    match parse_schema_version(value) {
        Some(point) => Some((value.clone(), point)),
        None => {
            ranges.problem(
                Some(name),
                "malformed-schema-range",
                format!(
                    "entry {}: {field}={} is not a MAJOR.MINOR schema version",
                    quoted(name),
                    quoted(value)
                ),
            );
            None
        }
    }
}

/// Renders a string in single quotes, the way the Python tool's `repr`
/// messages did (so log searches keep matching).
pub(crate) fn quoted(value: &str) -> String {
    format!("'{}'", value.replace('\\', "\\\\").replace('\'', "\\'"))
}

/// Describes a non-string YAML value as `<type> (<value>)` for messages.
pub(crate) fn describe(value: &Yaml) -> String {
    match value {
        Yaml::Real(text) => format!("float ({text})"),
        Yaml::Integer(number) => format!("int ({number})"),
        Yaml::Boolean(flag) => format!("bool ({flag})"),
        Yaml::Null => "null".to_owned(),
        Yaml::Array(_) => "list".to_owned(),
        Yaml::Hash(_) => "mapping".to_owned(),
        Yaml::String(text) => format!("str ({})", quoted(text)),
        Yaml::Alias(_) | Yaml::BadValue => "invalid value".to_owned(),
    }
}

#[cfg(test)]
#[path = "client_rules_tests.rs"]
mod tests;
