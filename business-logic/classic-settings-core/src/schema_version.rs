//! YAML schema versioning for shippable CLASSIC data files.
//!
//! Every shippable YAML file (`CLASSIC Main.yaml`, `CLASSIC Fallout4.yaml`, future
//! per-game additions) carries a root-level `schema_version` field whose value is a
//! `MAJOR.MINOR` integer pair. Clients declare a `SchemaCompat` range per file
//! family; the loader calls [`schema_compat_check`] to decide whether a given file
//! is safe to merge.
//!
//! # Version grammar
//!
//! A valid `schema_version` value is a quoted YAML string matching the regex
//! `^\d+\.\d+$`:
//!
//! - `"1.0"`, `"2.17"`, `"0.9"` — valid
//! - `"1"`, `"1.2.3"`, `"v1.2"`, `"1.0-beta"`, unquoted `1.0` — invalid
//!
//! # Compatibility rule
//!
//! A file with `schema_version: "X.Y"` is compatible with a client declaring
//! `SchemaCompat { accepted_major, minimum_minor }` iff:
//!
//! ```text
//! X == accepted_major && Y >= minimum_minor
//! ```
//!
//! - MAJOR bumps are breaking; a new MAJOR stops older clients from loading the file.
//! - MINOR bumps are additive; older clients that accept the MAJOR continue loading.
//!
//! # Examples
//!
//! ```
//! use classic_settings_core::{SchemaVersion, SchemaCompat, schema_compat_check, Compatibility};
//!
//! let file_version: SchemaVersion = "1.3".parse().unwrap();
//! let compat = SchemaCompat { accepted_major: 1, minimum_minor: 2 };
//!
//! assert!(matches!(schema_compat_check(&file_version, &compat), Compatibility::Compatible));
//! ```

use std::fmt;
use std::str::FromStr;
use thiserror::Error;
use yaml_rust2::Yaml;

/// The YAML root-level key that identifies a shippable file's schema version.
pub const SCHEMA_VERSION_KEY: &str = "schema_version";

/// Parsed `MAJOR.MINOR` schema version declared by a shippable YAML file.
///
/// Ordering compares MAJOR first, then MINOR, so `1.9 < 2.0` and `2.3 < 2.10`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SchemaVersion {
    /// Breaking-change component. Incremented whenever keys are removed, renamed,
    /// or change value shape / required semantics.
    pub major: u32,
    /// Additive-change component. Incremented whenever optional keys are added
    /// that existing clients can ignore; resets to `0` on a MAJOR bump.
    pub minor: u32,
}

impl SchemaVersion {
    /// Construct a schema version from explicit components.
    pub const fn new(major: u32, minor: u32) -> Self {
        Self { major, minor }
    }
}

impl fmt::Display for SchemaVersion {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}.{}", self.major, self.minor)
    }
}

impl FromStr for SchemaVersion {
    type Err = SchemaParseError;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        let (major_s, minor_s) = value
            .split_once('.')
            .ok_or(SchemaParseError::MissingSeparator)?;

        if major_s.is_empty() || minor_s.is_empty() {
            return Err(SchemaParseError::EmptyComponent);
        }

        if minor_s.contains('.') {
            return Err(SchemaParseError::TooManyComponents);
        }

        if !major_s.bytes().all(|b| b.is_ascii_digit())
            || !minor_s.bytes().all(|b| b.is_ascii_digit())
        {
            return Err(SchemaParseError::NonDigitComponent);
        }

        let major: u32 = major_s
            .parse()
            .map_err(|_| SchemaParseError::ComponentOverflow)?;
        let minor: u32 = minor_s
            .parse()
            .map_err(|_| SchemaParseError::ComponentOverflow)?;

        Ok(Self { major, minor })
    }
}

/// Low-level parse failure reason, produced by [`SchemaVersion::from_str`] and
/// folded into [`YamlSchemaError::Malformed`] by [`extract_schema_version`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SchemaParseError {
    /// The string contains no `.` separator (e.g., `"1"`).
    MissingSeparator,
    /// The string contains more than one `.` (e.g., `"1.2.3"`).
    TooManyComponents,
    /// One of the `MAJOR` / `MINOR` components is the empty string
    /// (e.g., `".1"` or `"1."`).
    EmptyComponent,
    /// One of the components contains a non-ASCII-digit byte (e.g., `"v1.2"`).
    NonDigitComponent,
    /// A component does not fit in `u32`.
    ComponentOverflow,
}

impl fmt::Display for SchemaParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingSeparator => f.write_str("expected `MAJOR.MINOR`, found no `.` separator"),
            Self::TooManyComponents => {
                f.write_str("expected `MAJOR.MINOR`, found more than one `.`")
            }
            Self::EmptyComponent => f.write_str("`MAJOR` or `MINOR` component is empty"),
            Self::NonDigitComponent => {
                f.write_str("`MAJOR`/`MINOR` components must be base-10 digits")
            }
            Self::ComponentOverflow => f.write_str("`MAJOR`/`MINOR` component does not fit in u32"),
        }
    }
}

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

/// Per-file client compatibility declaration.
///
/// A client build declares one `SchemaCompat` per shippable file family (e.g.,
/// `MAIN_YAML`, `GAME_FALLOUT4_YAML`). These values are compile-time constants
/// so that drift between bundled YAML schemas and client-accepted ranges can be
/// caught by a CI gate rather than at runtime.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SchemaCompat {
    /// The single MAJOR the client is built to parse. Mismatch is an immediate
    /// incompatibility (the whole file is refused).
    pub accepted_major: u32,
    /// The lowest MINOR the client still supports at `accepted_major`. Files
    /// with a lower MINOR are assumed to predate a field the client now depends
    /// on; higher MINOR is always accepted (additive-only contract).
    pub minimum_minor: u32,
}

impl SchemaCompat {
    /// Construct a compatibility range. `const` so consumers can declare these
    /// as module-level constants.
    pub const fn new(accepted_major: u32, minimum_minor: u32) -> Self {
        Self {
            accepted_major,
            minimum_minor,
        }
    }
}

/// Outcome of comparing a file's [`SchemaVersion`] against a client's
/// [`SchemaCompat`] range.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Compatibility {
    /// File version fits the client's accepted range; safe to load.
    Compatible,
    /// File MAJOR differs from the client's `accepted_major`; incompatible
    /// regardless of MINOR.
    IncompatibleMajor {
        /// The MAJOR component declared by the file.
        file_major: u32,
        /// The MAJOR the client is built to accept.
        client_accepted_major: u32,
    },
    /// File MAJOR matches, but MINOR is below the client's `minimum_minor`.
    IncompatibleMinor {
        /// The MINOR component declared by the file.
        file_minor: u32,
        /// The MINOR floor the client requires.
        client_minimum_minor: u32,
    },
}

/// Decide whether a file's schema version is compatible with a client range.
///
/// Rule (restated for the reader):
/// `version.major == compat.accepted_major && version.minor >= compat.minimum_minor`.
pub fn schema_compat_check(version: &SchemaVersion, compat: &SchemaCompat) -> Compatibility {
    if version.major != compat.accepted_major {
        return Compatibility::IncompatibleMajor {
            file_major: version.major,
            client_accepted_major: compat.accepted_major,
        };
    }
    if version.minor < compat.minimum_minor {
        return Compatibility::IncompatibleMinor {
            file_minor: version.minor,
            client_minimum_minor: compat.minimum_minor,
        };
    }
    Compatibility::Compatible
}

#[cfg(test)]
#[path = "schema_version_tests.rs"]
mod tests;
