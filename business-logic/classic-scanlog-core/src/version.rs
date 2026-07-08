//! Version handling for crash generator version comparison
//!
//! This module provides version parsing and comparison functionality compatible
//! with Python's `packaging.version.Version` for crash generator versions.
//!
//! Crash generator versions typically follow semver format (e.g., "1.28.0", "1.29.1").
//!
//! # Floor-based Version Checking
//!
//! The `check_version_status` function treats configured crash generator versions
//! as minimum supported floors. A detected version at or above the lowest configured
//! version is valid, allowing newer crash generators without a data-file update.

use regex::Regex;
use semver::Version;
use std::cmp::Ordering;
use std::sync::LazyLock;

fn compile_static_regex(pattern: &str, name: &str) -> Regex {
    match Regex::new(pattern) {
        Ok(regex) => regex,
        Err(error) => panic!("invalid static regex {name}: {error}"),
    }
}

/// Status of a crash generator version relative to supported version floors.
///
/// This enum represents the result of checking a crash generator version
/// against supported versions for a specific game version.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CrashgenVersionStatus {
    /// The version is supported by the configured version floor.
    Valid,
    /// The version is older than the configured version floor.
    Outdated,
    /// The version is newer than the highest known version.
    NewerThanKnown,
    /// No crash generator is supported for this game version.
    NoSupportedVersion,
}

/// Pattern to extract version numbers from strings like "Buffout 4 v1.28.0"
static VERSION_PATTERN: LazyLock<Regex> =
    LazyLock::new(|| compile_static_regex(r"v?(\d+)\.(\d+)\.?(\d*)", "VERSION_PATTERN"));

/// Represents a crashgen version that can be compared
///
/// Two `CrashgenVersion` instances are considered equal if they have the same
/// major, minor, and patch version numbers, regardless of the original string
/// representation. This allows "Buffout 4 v1.28.6" to equal "1.28.6".
#[derive(Debug, Clone, Default)]
pub struct CrashgenVersion {
    /// Major version number (e.g., 1 in "1.28.0")
    pub major: u64,
    /// Minor version number (e.g., 28 in "1.28.0")
    pub minor: u64,
    /// Patch version number (e.g., 0 in "1.28.0")
    pub patch: u64,
    /// Original version string for display
    pub original: String,
}

impl CrashgenVersion {
    /// Creates a new CrashgenVersion from components.
    ///
    /// # Arguments
    ///
    /// * `major` - Major version number
    /// * `minor` - Minor version number
    /// * `patch` - Patch version number
    ///
    /// # Returns
    ///
    /// A new `CrashgenVersion` instance.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::version::CrashgenVersion;
    ///
    /// let v = CrashgenVersion::new(1, 28, 0);
    /// assert_eq!(v.major, 1);
    /// assert_eq!(v.minor, 28);
    /// assert_eq!(v.patch, 0);
    /// ```
    pub fn new(major: u64, minor: u64, patch: u64) -> Self {
        Self {
            major,
            minor,
            patch,
            original: format!("{}.{}.{}", major, minor, patch),
        }
    }

    /// Parses a version string into a CrashgenVersion.
    ///
    /// This function handles various formats:
    /// - "1.28.0" (standard semver)
    /// - "v1.28.0" (with v prefix)
    /// - "Buffout 4 v1.28.0" (with crashgen name)
    /// - "1.28" (missing patch, defaults to 0)
    ///
    /// # Arguments
    ///
    /// * `version_str` - Version string to parse
    ///
    /// # Returns
    ///
    /// `Some(CrashgenVersion)` if parsing succeeded, `None` otherwise.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::version::CrashgenVersion;
    ///
    /// let v = CrashgenVersion::parse("v1.28.0").unwrap();
    /// assert_eq!(v.major, 1);
    /// assert_eq!(v.minor, 28);
    /// assert_eq!(v.patch, 0);
    ///
    /// // Also handles full crashgen strings
    /// let v2 = CrashgenVersion::parse("Buffout 4 v1.29.1").unwrap();
    /// assert_eq!(v2.minor, 29);
    /// ```
    pub fn parse(version_str: &str) -> Option<Self> {
        // Try to match the version pattern
        if let Some(captures) = VERSION_PATTERN.captures(version_str) {
            let major = captures.get(1)?.as_str().parse().ok()?;
            let minor = captures.get(2)?.as_str().parse().ok()?;
            let patch = captures
                .get(3)
                .and_then(|m| {
                    let s = m.as_str();
                    if s.is_empty() { None } else { s.parse().ok() }
                })
                .unwrap_or(0);

            Some(Self {
                major,
                minor,
                patch,
                original: version_str.to_string(),
            })
        } else {
            // Try semver parsing as fallback
            Version::parse(version_str).ok().map(|v| Self {
                major: v.major,
                minor: v.minor,
                patch: v.patch,
                original: version_str.to_string(),
            })
        }
    }

    /// Converts to a semver Version for comparison.
    ///
    /// # Returns
    ///
    /// A `semver::Version` instance for this version.
    pub fn to_semver(&self) -> Version {
        Version::new(self.major, self.minor, self.patch)
    }

    /// Converts to a tuple of (major, minor, patch) for settings validator.
    ///
    /// # Returns
    ///
    /// A tuple `(u32, u32, u32)` suitable for Crashgen Expectation evaluation.
    pub fn to_tuple(&self) -> (u32, u32, u32) {
        (self.major as u32, self.minor as u32, self.patch as u32)
    }

    /// Checks this version against supported version floors.
    ///
    /// Configured versions are treated as minimum supported floors, so a detected
    /// version greater than or equal to the lowest configured version is valid.
    ///
    /// # Arguments
    ///
    /// * `valid_versions` - Slice of supported version floors for the game version
    ///
    /// # Returns
    ///
    /// A `CrashgenVersionStatus` indicating the validation result.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::version::{CrashgenVersion, CrashgenVersionStatus};
    ///
    /// let current = CrashgenVersion::new(1, 28, 6);
    /// let valid = vec![
    ///     CrashgenVersion::new(1, 28, 6),
    ///     CrashgenVersion::new(1, 37, 0),
    /// ];
    ///
    /// let status = current.check_version_status(&valid);
    /// assert_eq!(status, CrashgenVersionStatus::Valid);
    ///
    /// // Outdated version
    /// let outdated = CrashgenVersion::new(1, 26, 0);
    /// let status = outdated.check_version_status(&valid);
    /// assert_eq!(status, CrashgenVersionStatus::Outdated);
    ///
    /// // Newer than the configured floor
    /// let newer = CrashgenVersion::new(1, 40, 0);
    /// let status = newer.check_version_status(&valid);
    /// assert_eq!(status, CrashgenVersionStatus::Valid);
    ///
    /// // No supported version
    /// let empty: Vec<CrashgenVersion> = vec![];
    /// let status = current.check_version_status(&empty);
    /// assert_eq!(status, CrashgenVersionStatus::NoSupportedVersion);
    /// ```
    pub fn check_version_status(
        &self,
        valid_versions: &[CrashgenVersion],
    ) -> CrashgenVersionStatus {
        self.check_version_status_with_exceptions(valid_versions, &[])
    }

    /// Checks version status using floor versions plus optional exact-match exceptions.
    ///
    /// Exception versions are valid only on exact equality and are excluded from floor
    /// computation. Floor versions behave as minimum supported versions: any detected
    /// version at or above the lowest floor is acceptable.
    pub fn check_version_status_with_exceptions(
        &self,
        floors: &[CrashgenVersion],
        exceptions: &[CrashgenVersion],
    ) -> CrashgenVersionStatus {
        if exceptions.iter().any(|exception| self == exception) {
            return CrashgenVersionStatus::Valid;
        }

        if floors.is_empty() && exceptions.is_empty() {
            return CrashgenVersionStatus::NoSupportedVersion;
        }

        match floors.iter().min() {
            Some(floor) if self >= floor => CrashgenVersionStatus::Valid,
            _ => CrashgenVersionStatus::Outdated,
        }
    }
}

impl PartialOrd for CrashgenVersion {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for CrashgenVersion {
    fn cmp(&self, other: &Self) -> Ordering {
        match self.major.cmp(&other.major) {
            Ordering::Equal => match self.minor.cmp(&other.minor) {
                Ordering::Equal => self.patch.cmp(&other.patch),
                other => other,
            },
            other => other,
        }
    }
}

impl PartialEq for CrashgenVersion {
    /// Compares two versions based only on major, minor, and patch numbers.
    ///
    /// The `original` string is intentionally excluded from comparison, allowing
    /// versions parsed from different string representations to be equal if they
    /// have the same version numbers. For example, "Buffout 4 v1.28.6" equals "1.28.6".
    fn eq(&self, other: &Self) -> bool {
        self.major == other.major && self.minor == other.minor && self.patch == other.patch
    }
}

impl Eq for CrashgenVersion {}

impl std::fmt::Display for CrashgenVersion {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}.{}.{}", self.major, self.minor, self.patch)
    }
}

/// Parses a version string into a CrashgenVersion (convenience function).
///
/// This is the Rust equivalent of Python's `crashgen_version_gen()` function.
///
/// # Arguments
///
/// * `version_str` - Version string to parse
///
/// # Returns
///
/// A `CrashgenVersion` (defaults to 0.0.0 if parsing fails).
///
/// # Example
///
/// ```rust
/// use classic_scanlog_core::version::crashgen_version_gen;
///
/// let v = crashgen_version_gen("v1.28.0");
/// assert_eq!(v.major, 1);
/// assert_eq!(v.minor, 28);
/// ```
pub fn crashgen_version_gen(version_str: &str) -> CrashgenVersion {
    CrashgenVersion::parse(version_str).unwrap_or_default()
}

/// Checks a version string against supported version floor strings.
///
/// This is a convenience function that parses the version strings and
/// performs floor-based version validation.
///
/// # Arguments
///
/// * `detected_version` - The detected crash generator version string
/// * `valid_versions` - Slice of supported version floor strings
///
/// # Returns
///
/// A `CrashgenVersionStatus` indicating the validation result.
///
/// # Example
///
/// ```rust
/// use classic_scanlog_core::version::{check_crashgen_version_status, CrashgenVersionStatus};
///
/// let status = check_crashgen_version_status("1.28.6", &["1.28.6", "1.37.0"]);
/// assert_eq!(status, CrashgenVersionStatus::Valid);
///
/// let status = check_crashgen_version_status("1.26.0", &["1.28.6", "1.37.0"]);
/// assert_eq!(status, CrashgenVersionStatus::Outdated);
/// ```
pub fn check_crashgen_version_status(
    detected_version: &str,
    valid_versions: &[&str],
) -> CrashgenVersionStatus {
    check_crashgen_version_status_with_exceptions(detected_version, valid_versions, &[])
}

/// Checks a version string against floor versions and exact-match exception versions.
pub fn check_crashgen_version_status_with_exceptions(
    detected_version: &str,
    floor_versions: &[&str],
    exception_versions: &[&str],
) -> CrashgenVersionStatus {
    let detected = crashgen_version_gen(detected_version);
    let floors: Vec<CrashgenVersion> = floor_versions
        .iter()
        .filter_map(|v| CrashgenVersion::parse(v))
        .collect();
    let exceptions: Vec<CrashgenVersion> = exception_versions
        .iter()
        .filter_map(|v| CrashgenVersion::parse(v))
        .collect();

    detected.check_version_status_with_exceptions(&floors, &exceptions)
}

/// Returns whether a crash log is using a fake Buffout 4 version for bot compatibility.
///
/// Addictol's bot-compatible mode can present itself as `Buffout 4` with a low semantic
/// version so legacy report bots continue parsing the log. Real Buffout 4 versions used by
/// CLASSIC start well above this threshold, so versions below `1.20.0` are treated as fake
/// and skip normal Buffout version/settings validation.
pub(crate) fn is_fake_bot_compatible_buffout_version(crashgen_version_str: &str) -> bool {
    let normalized = crashgen_version_str.to_ascii_lowercase();
    if !normalized.contains("buffout") {
        return false;
    }

    CrashgenVersion::parse(crashgen_version_str)
        .map(|version| version < CrashgenVersion::new(1, 20, 0))
        .unwrap_or(false)
}

#[cfg(test)]
#[path = "version_tests.rs"]
mod tests;
