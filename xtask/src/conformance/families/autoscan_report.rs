//! Expectation compiler and normalizer for `autoscan-report`.
//!
//! The pack names each persisted report by a `template`: a separately
//! authored Markdown golden beneath the fixture root, which only the central
//! validator reads (it is never staged for an adapter). Compiling replaces the
//! template with the golden's exact `bytesHex`, `sha256` and `byteLength`.
//!
//! Participants return the report bytes unmodified. FCX-mode reports embed
//! absolute paths, so before comparison the expected side expands the three
//! authored FCX path tokens using the observation's `executionRoot`.

use std::path::PathBuf;

use serde_json::{Map, Value, json};

use super::{
    Compiled, InputContext, NormalizationError, decode_hex, encode_hex, expectation_issue,
    read_oracle, sha256_hex,
};
use crate::conformance::Issue;

/// Replaces every report `template` with the golden's byte identity.
pub(super) fn compile(context: &InputContext<'_>) -> Result<Compiled, Issue> {
    let base = context.fixture_root()?;
    let inputs = context.fixture_paths(&base);
    let mut compiled = Compiled::identity(context.pack);
    for (index, expected) in compiled.expected.iter_mut().enumerate() {
        let reports = expected
            .get_mut("durableEffects")
            .and_then(|effects| effects.get_mut("reports"))
            .and_then(Value::as_array_mut)
            .ok_or_else(|| {
                expectation_issue(index, "expected durableEffects.reports must be an array")
            })?;
        for report in reports {
            let report = report.as_object_mut().ok_or_else(|| {
                expectation_issue(index, "each expected report must be an object")
            })?;
            let Some(Value::String(template)) = report.remove("template") else {
                return Err(expectation_issue(
                    index,
                    "each expected report must name its golden by a string template",
                ));
            };
            let oracle: PathBuf = super::oracle_file(&base, &template)
                .map_err(|message| expectation_issue(index, format!("report oracle: {message}")))?;
            if inputs.contains(&oracle) {
                return Err(expectation_issue(
                    index,
                    format!("report oracle {template} cannot be an adapter input fixture"),
                ));
            }
            let data = read_oracle(&base, &template)
                .map_err(|message| expectation_issue(index, message))?;
            set_bytes(report, &data);
            compiled
                .oracles
                .push(format!("{}/{template}", context.pack.fixture_root));
        }
    }
    Ok(compiled)
}

/// Writes the byte identity of `data` into `report`.
fn set_bytes(report: &mut Map<String, Value>, data: &[u8]) {
    report.insert("bytesHex".into(), json!(encode_hex(data)));
    report.insert("sha256".into(), json!(sha256_hex(data)));
    report.insert("byteLength".into(), json!(data.len()));
}

/// Expands the FCX path tokens of the expected reports with the observed
/// `executionRoot`, and takes the root itself from the observation.
///
/// Only FCX-mode scenarios (`semanticInputs.fcxMode`) expand tokens; every
/// other expected byte is kept, and the byte identity is recomputed.
///
/// # Errors
///
/// Fails when the observed root is not a clean absolute Windows or POSIX path
/// (empty, holding line breaks, NUL, braces or `..`), or the compiled
/// expectation lacks its reports.
#[cfg_attr(
    not(test),
    expect(dead_code, reason = "receipt validation (Engine A3) is the caller")
)]
pub(super) fn expand(
    expected: &Map<String, Value>,
    actual: &Map<String, Value>,
) -> Result<Map<String, Value>, NormalizationError> {
    let root_error = || {
        NormalizationError::new(
            "report execution root must be an absolute path",
            "$.executionRoot",
        )
    };
    let root = match actual.get("executionRoot") {
        Some(Value::String(root))
            if !root.is_empty() && !root.contains(['\r', '\n', '\0', '{', '}']) =>
        {
            root
        }
        _ => return Err(root_error()),
    };
    let root_path = RootPath::parse(root).ok_or_else(root_error)?;
    let malformed = |message: &str| NormalizationError::new(message, "$.durableEffects.reports");
    let mut result = expected.clone();
    result.insert("executionRoot".into(), json!(root));
    let fcx_mode = expected
        .get("semanticInputs")
        .and_then(|inputs| inputs.get("fcxMode"))
        .and_then(Value::as_bool)
        .ok_or_else(|| malformed("expected semanticInputs.fcxMode must be a boolean"))?;
    let reports = result
        .get_mut("durableEffects")
        .and_then(|effects| effects.get_mut("reports"))
        .and_then(Value::as_array_mut)
        .ok_or_else(|| malformed("expected durableEffects.reports must be an array"))?;
    for report in reports {
        let report = report
            .as_object_mut()
            .ok_or_else(|| malformed("each expected report must be an object"))?;
        let mut data = report
            .get("bytesHex")
            .and_then(Value::as_str)
            .and_then(decode_hex)
            .ok_or_else(|| malformed("expected report bytes must be lowercase hexadecimal"))?;
        if fcx_mode {
            for (token, value) in [
                ("{{FCX_GAME_ROOT}}", root_path.join("fcx-game")),
                ("{{FCX_DOCUMENTS_ROOT}}", root_path.join("fcx-documents")),
                ("{{PATH_SEPARATOR}}", root_path.separator().to_owned()),
            ] {
                data = replace_bytes(&data, token.as_bytes(), value.as_bytes());
            }
        }
        set_bytes(report, &data);
    }
    Ok(result)
}

/// An absolute execution root, rendered the way Python's `pathlib` renders
/// it: the retired expander used `PureWindowsPath` when the root is absolute
/// on Windows (a drive letter with a root, or a UNC share), else
/// `PurePosixPath`. Empty and `.` components are dropped and Windows
/// separators are normalized to `\`.
///
/// A root that starts with two separators must be a complete UNC share
/// (`\\server\share`). pathlib renders incomplete ones (`//tmp`, `\\host`) as
/// odd drive-only paths; no participant reports such a root, so they are
/// rejected instead of reproduced.
#[derive(Debug, PartialEq, Eq)]
pub(super) struct RootPath {
    /// `C:\`, `\\server\share\` or `/`.
    anchor: String,
    /// The components after the anchor.
    parts: Vec<String>,
    /// The flavour's separator.
    separator: &'static str,
}

impl RootPath {
    /// Parses an absolute root; `None` for a relative root, an incomplete UNC
    /// root, or one containing a `..` component.
    pub fn parse(root: &str) -> Option<Self> {
        let normalized = root.replace('/', "\\");
        let bytes = normalized.as_bytes();
        let path = if let Some(unc) = normalized.strip_prefix("\\\\") {
            let mut pieces = unc.splitn(3, '\\');
            let server = pieces.next().filter(|piece| !piece.is_empty())?;
            let share = pieces.next().filter(|piece| !piece.is_empty())?;
            Self {
                anchor: format!("\\\\{server}\\{share}\\"),
                parts: components(pieces.next().unwrap_or(""), '\\'),
                separator: "\\",
            }
        } else if bytes.len() >= 3
            && bytes[0].is_ascii_alphabetic()
            && bytes[1] == b':'
            && bytes[2] == b'\\'
        {
            Self {
                anchor: format!("{}\\", &normalized[..2]),
                parts: components(&normalized[3..], '\\'),
                separator: "\\",
            }
        } else if root.starts_with('/') {
            Self {
                anchor: "/".into(),
                parts: components(root, '/'),
                separator: "/",
            }
        } else {
            return None;
        };
        (!path.parts.iter().any(|part| part == "..")).then_some(path)
    }

    /// The root joined with `child`, as pathlib's `str(root / child)`.
    pub fn join(&self, child: &str) -> String {
        let mut joined = self.anchor.clone();
        for part in self.parts.iter().map(String::as_str).chain([child]) {
            if !joined.ends_with(self.separator) {
                joined.push_str(self.separator);
            }
            joined.push_str(part);
        }
        joined
    }

    /// The flavour's separator.
    pub fn separator(&self) -> &'static str {
        self.separator
    }
}

/// Path components with empty and `.` components dropped, as pathlib does.
fn components(path: &str, separator: char) -> Vec<String> {
    path.split(separator)
        .filter(|part| !part.is_empty() && *part != ".")
        .map(str::to_owned)
        .collect()
}

/// Replaces every non-overlapping occurrence of `needle`, left to right.
fn replace_bytes(data: &[u8], needle: &[u8], replacement: &[u8]) -> Vec<u8> {
    let mut result = Vec::with_capacity(data.len());
    let mut index = 0;
    while index < data.len() {
        if data[index..].starts_with(needle) {
            result.extend_from_slice(replacement);
            index += needle.len();
        } else {
            result.push(data[index]);
            index += 1;
        }
    }
    result
}

#[cfg(test)]
#[path = "autoscan_report_tests.rs"]
mod tests;
