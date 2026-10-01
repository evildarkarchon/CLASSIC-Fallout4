//! Extract schema versions from YAML documents.

use super::version::{SchemaParseError, SchemaVersion};
use thiserror::Error;
use yaml_rust2::Yaml;

/// The YAML root-level key that identifies a shippable file's schema version.
pub const SCHEMA_VERSION_KEY: &str = "schema_version";

/// Errors produced while reading a `schema_version` header from a YAML document.
#[derive(Debug, Error)]
pub enum YamlSchemaError {
    /// The YAML document has no root-level `schema_version` key.
    ///
    /// Shippable YAML files are required to carry one; a bare file with no header
    /// is refused rather than silently loaded.
    #[error("YAML document is missing required `schema_version` header")]
    Missing,

    /// The `schema_version` key exists but its value is not a valid
    /// `MAJOR.MINOR` string.
    ///
    /// `file` carries caller-supplied context (typically the file name), or an
    /// empty string when the caller did not provide one. `value` is the raw
    /// string that failed to parse.
    #[error("YAML `schema_version` in `{file}` is malformed: {reason} (value: {value:?})")]
    Malformed {
        /// Caller-supplied file label (empty string when unknown).
        file: String,
        /// The raw offending value.
        value: String,
        /// The low-level reason the value did not parse as `MAJOR.MINOR`.
        reason: SchemaParseError,
    },
}

impl YamlSchemaError {
    /// Attach a file label to a [`YamlSchemaError::Malformed`] returned without
    /// one. Leaves [`YamlSchemaError::Missing`] untouched.
    pub fn with_file(self, file_label: impl Into<String>) -> Self {
        match self {
            Self::Malformed { value, reason, .. } => Self::Malformed {
                file: file_label.into(),
                value,
                reason,
            },
            other => other,
        }
    }
}

/// Read the root-level `schema_version` field from a YAML document.
///
/// Callers that want a file label embedded in [`YamlSchemaError::Malformed`] can
/// chain [`YamlSchemaError::with_file`] onto the returned error, since this
/// function does not know the file the document came from.
///
/// # Errors
///
/// - [`YamlSchemaError::Missing`] when the `schema_version` key is absent.
/// - [`YamlSchemaError::Malformed`] when the key exists but is not a valid
///   `MAJOR.MINOR` string (including YAML-level type mismatches such as the
///   unquoted numeric `1.0`, which yaml-rust2 parses as `Yaml::Real`, not
///   `Yaml::String`).
pub fn extract_schema_version(doc: &Yaml) -> Result<SchemaVersion, YamlSchemaError> {
    // yaml-rust2 returns `Yaml::BadValue` for a missing key lookup against a
    // mapping, so treat BadValue on the root-level key lookup as Missing.
    let value = &doc[SCHEMA_VERSION_KEY];

    match value {
        Yaml::BadValue | Yaml::Null => Err(YamlSchemaError::Missing),
        Yaml::String(s) => {
            s.parse::<SchemaVersion>()
                .map_err(|reason| YamlSchemaError::Malformed {
                    file: String::new(),
                    value: s.clone(),
                    reason,
                })
        }
        // An unquoted `1.0` in YAML parses as Yaml::Real; reject because the
        // format contract requires a quoted string (spec scenario
        // "schema_version malformed", unquoted-number case).
        Yaml::Real(raw) => Err(YamlSchemaError::Malformed {
            file: String::new(),
            value: raw.clone(),
            reason: SchemaParseError::NonDigitComponent,
        }),
        Yaml::Integer(i) => Err(YamlSchemaError::Malformed {
            file: String::new(),
            value: i.to_string(),
            reason: SchemaParseError::MissingSeparator,
        }),
        other => Err(YamlSchemaError::Malformed {
            file: String::new(),
            value: format!("{other:?}"),
            reason: SchemaParseError::NonDigitComponent,
        }),
    }
}

#[cfg(test)]
#[path = "extract_tests.rs"]
mod tests;
