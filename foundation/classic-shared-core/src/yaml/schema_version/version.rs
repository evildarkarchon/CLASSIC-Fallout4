//! Schema version parsing and formatting.

use std::fmt;
use std::str::FromStr;

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

#[cfg(test)]
#[path = "version_tests.rs"]
mod tests;
