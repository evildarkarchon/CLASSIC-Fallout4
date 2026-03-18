//! Version handling for crash generator version comparison
//!
//! This module provides version parsing and comparison functionality compatible
//! with Python's `packaging.version.Version` for crash generator versions.
//!
//! Crash generator versions typically follow semver format (e.g., "1.28.0", "1.29.1").
//!
//! # List-based Version Checking
//!
//! The new `check_version_status` function supports list-based version validation,
//! where multiple versions can be valid for a single game version (e.g., FO4_OG
//! supports both 1.28.6 and 1.37.0).

use once_cell::sync::Lazy;
use regex::Regex;
use semver::Version;
use std::cmp::Ordering;

/// Status of a crash generator version relative to valid versions.
///
/// This enum represents the result of checking a crash generator version
/// against a list of valid versions for a specific game version.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CrashgenVersionStatus {
    /// The version is in the list of valid versions.
    Valid,
    /// The version is older than all valid versions.
    Outdated,
    /// The version is newer than the highest known valid version.
    NewerThanKnown,
    /// No crash generator is supported for this game version.
    NoSupportedVersion,
}

/// Pattern to extract version numbers from strings like "Buffout 4 v1.28.0"
static VERSION_PATTERN: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"v?(\d+)\.(\d+)\.?(\d*)").expect("Invalid version regex pattern"));

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
    /// A tuple `(u32, u32, u32)` suitable for `SettingsValidator::scan_archivelimit_setting()`.
    pub fn to_tuple(&self) -> (u32, u32, u32) {
        (self.major as u32, self.minor as u32, self.patch as u32)
    }

    /// Checks if this version is outdated compared to the latest versions.
    ///
    /// **Deprecated**: Use `check_version_status()` with a list of valid versions instead.
    /// This legacy method only supports single-version comparison.
    ///
    /// This matches Python's version comparison logic:
    /// - If VR mode: Check against both version_latest_vr AND version_latest
    /// - If non-VR: Check only against version_latest
    ///
    /// # Arguments
    ///
    /// * `latest` - The latest non-VR version
    /// * `latest_vr` - The latest VR version
    /// * `selected_version_is_vr` - Whether the selected version is VR
    ///
    /// # Returns
    ///
    /// `true` if the current version is outdated, `false` otherwise.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::version::CrashgenVersion;
    ///
    /// let current = CrashgenVersion::new(1, 26, 0);
    /// let latest = CrashgenVersion::new(1, 28, 0);
    /// let latest_vr = CrashgenVersion::new(1, 27, 0);
    ///
    /// // Non-VR: only compare against latest
    /// assert!(current.is_outdated(&latest, &latest_vr, false));
    ///
    /// // VR: compare against both
    /// assert!(current.is_outdated(&latest, &latest_vr, true));
    /// ```
    #[deprecated(
        since = "0.2.0",
        note = "Use check_version_status() with a list of valid versions instead"
    )]
    pub fn is_outdated(
        &self,
        latest: &CrashgenVersion,
        latest_vr: &CrashgenVersion,
        selected_version_is_vr: bool,
    ) -> bool {
        // Port of Python logic:
        // if (version_current < version_latest_vr and version_current != version_latest) or
        //    (not game_is_vr and version_current < version_latest):
        //     # outdated

        if selected_version_is_vr {
            // VR mode: Check against VR version, but allow if matches non-VR latest
            self < latest_vr && self != latest
        } else {
            // Non-VR mode: Check against non-VR latest
            self < latest
        }
    }

    /// Checks this version against a list of valid versions.
    ///
    /// This is the new list-based version validation that supports multiple valid
    /// versions per game version (e.g., FO4_OG supports both 1.28.6 and 1.37.0).
    ///
    /// # Arguments
    ///
    /// * `valid_versions` - Slice of valid versions for the game version
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
    /// // Newer than known
    /// let newer = CrashgenVersion::new(1, 40, 0);
    /// let status = newer.check_version_status(&valid);
    /// assert_eq!(status, CrashgenVersionStatus::NewerThanKnown);
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
        // Handle no supported version case
        if valid_versions.is_empty() {
            return CrashgenVersionStatus::NoSupportedVersion;
        }

        // Check if version is in the valid list (exact match)
        if valid_versions.iter().any(|v| v == self) {
            return CrashgenVersionStatus::Valid;
        }

        // Find the maximum valid version
        let max_valid = valid_versions.iter().max();

        match max_valid {
            Some(max) if self > max => CrashgenVersionStatus::NewerThanKnown,
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

/// Checks a version string against a list of valid version strings.
///
/// This is a convenience function that parses the version strings and
/// performs list-based version validation.
///
/// # Arguments
///
/// * `detected_version` - The detected crash generator version string
/// * `valid_versions` - Slice of valid version strings
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
    let detected = crashgen_version_gen(detected_version);
    let valid: Vec<CrashgenVersion> = valid_versions
        .iter()
        .filter_map(|v| CrashgenVersion::parse(v))
        .collect();

    detected.check_version_status(&valid)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_simple_version() {
        let v = CrashgenVersion::parse("1.28.0").unwrap();
        assert_eq!(v.major, 1);
        assert_eq!(v.minor, 28);
        assert_eq!(v.patch, 0);
    }

    #[test]
    fn test_parse_version_with_v_prefix() {
        let v = CrashgenVersion::parse("v1.29.1").unwrap();
        assert_eq!(v.major, 1);
        assert_eq!(v.minor, 29);
        assert_eq!(v.patch, 1);
    }

    #[test]
    fn test_parse_version_from_crashgen_string() {
        let v = CrashgenVersion::parse("Buffout 4 v1.30.2").unwrap();
        assert_eq!(v.major, 1);
        assert_eq!(v.minor, 30);
        assert_eq!(v.patch, 2);
    }

    #[test]
    fn test_parse_version_without_patch() {
        let v = CrashgenVersion::parse("1.28").unwrap();
        assert_eq!(v.major, 1);
        assert_eq!(v.minor, 28);
        assert_eq!(v.patch, 0);
    }

    #[test]
    fn test_version_comparison() {
        let v1 = CrashgenVersion::new(1, 26, 0);
        let v2 = CrashgenVersion::new(1, 28, 0);
        let v3 = CrashgenVersion::new(1, 28, 1);

        assert!(v1 < v2);
        assert!(v2 < v3);
        assert!(v1 < v3);
    }

    // Legacy tests for deprecated is_outdated method
    #[test]
    #[allow(deprecated)]
    fn test_is_outdated_non_vr() {
        let current = CrashgenVersion::new(1, 26, 0);
        let latest = CrashgenVersion::new(1, 28, 0);
        let latest_vr = CrashgenVersion::new(1, 27, 0);

        assert!(current.is_outdated(&latest, &latest_vr, false));
    }

    #[test]
    #[allow(deprecated)]
    fn test_is_outdated_vr() {
        let current = CrashgenVersion::new(1, 26, 0);
        let latest = CrashgenVersion::new(1, 28, 0);
        let latest_vr = CrashgenVersion::new(1, 27, 0);

        assert!(current.is_outdated(&latest, &latest_vr, true));
    }

    #[test]
    #[allow(deprecated)]
    fn test_not_outdated_when_matches_latest() {
        let current = CrashgenVersion::new(1, 28, 0);
        let latest = CrashgenVersion::new(1, 28, 0);
        let latest_vr = CrashgenVersion::new(1, 27, 0);

        // VR mode: not outdated if matches non-VR latest
        assert!(!current.is_outdated(&latest, &latest_vr, true));
    }

    #[test]
    fn test_crashgen_version_gen() {
        let v = crashgen_version_gen("v1.28.0");
        assert_eq!(v.major, 1);
        assert_eq!(v.minor, 28);

        // Invalid version defaults to 0.0.0
        let v_invalid = crashgen_version_gen("invalid");
        assert_eq!(v_invalid.major, 0);
    }

    // ========== List-based version checking tests ==========

    #[test]
    fn test_check_version_status_valid() {
        let current = CrashgenVersion::new(1, 28, 6);
        let valid = vec![
            CrashgenVersion::new(1, 28, 6),
            CrashgenVersion::new(1, 37, 0),
        ];

        let status = current.check_version_status(&valid);
        assert_eq!(status, CrashgenVersionStatus::Valid);
    }

    #[test]
    fn test_check_version_status_valid_second_option() {
        let current = CrashgenVersion::new(1, 37, 0);
        let valid = vec![
            CrashgenVersion::new(1, 28, 6),
            CrashgenVersion::new(1, 37, 0),
        ];

        let status = current.check_version_status(&valid);
        assert_eq!(status, CrashgenVersionStatus::Valid);
    }

    #[test]
    fn test_check_version_status_outdated() {
        let current = CrashgenVersion::new(1, 26, 0);
        let valid = vec![
            CrashgenVersion::new(1, 28, 6),
            CrashgenVersion::new(1, 37, 0),
        ];

        let status = current.check_version_status(&valid);
        assert_eq!(status, CrashgenVersionStatus::Outdated);
    }

    #[test]
    fn test_check_version_status_newer_than_known() {
        let current = CrashgenVersion::new(1, 40, 0);
        let valid = vec![
            CrashgenVersion::new(1, 28, 6),
            CrashgenVersion::new(1, 37, 0),
        ];

        let status = current.check_version_status(&valid);
        assert_eq!(status, CrashgenVersionStatus::NewerThanKnown);
    }

    #[test]
    fn test_check_version_status_no_supported_version() {
        let current = CrashgenVersion::new(1, 28, 6);
        let valid: Vec<CrashgenVersion> = vec![];

        let status = current.check_version_status(&valid);
        assert_eq!(status, CrashgenVersionStatus::NoSupportedVersion);
    }

    #[test]
    fn test_check_crashgen_version_status_convenience() {
        // Valid version
        let status = check_crashgen_version_status("1.28.6", &["1.28.6", "1.37.0"]);
        assert_eq!(status, CrashgenVersionStatus::Valid);

        // Outdated version
        let status = check_crashgen_version_status("1.26.0", &["1.28.6", "1.37.0"]);
        assert_eq!(status, CrashgenVersionStatus::Outdated);

        // Newer than known
        let status = check_crashgen_version_status("1.40.0", &["1.28.6", "1.37.0"]);
        assert_eq!(status, CrashgenVersionStatus::NewerThanKnown);

        // No supported version
        let status = check_crashgen_version_status("1.28.6", &[]);
        assert_eq!(status, CrashgenVersionStatus::NoSupportedVersion);
    }

    #[test]
    fn test_check_version_status_between_valid_versions() {
        // Version 1.30.0 is between 1.28.6 and 1.37.0 but not in the list
        let current = CrashgenVersion::new(1, 30, 0);
        let valid = vec![
            CrashgenVersion::new(1, 28, 6),
            CrashgenVersion::new(1, 37, 0),
        ];

        // This should be outdated because it's not in the valid list
        // and is less than the max valid version
        let status = current.check_version_status(&valid);
        assert_eq!(status, CrashgenVersionStatus::Outdated);
    }

    #[test]
    fn test_version_equality_ignores_original_string() {
        // Parse from different string formats that yield the same version
        let v1 = CrashgenVersion::parse("Buffout 4 v1.28.6").unwrap();
        let v2 = CrashgenVersion::parse("1.28.6").unwrap();
        let v3 = CrashgenVersion::parse("v1.28.6").unwrap();

        // Verify they have different original strings
        assert_ne!(v1.original, v2.original);
        assert_ne!(v1.original, v3.original);

        // But they should be equal because major/minor/patch are the same
        assert_eq!(v1, v2);
        assert_eq!(v1, v3);
        assert_eq!(v2, v3);
    }

    #[test]
    fn test_check_version_status_with_different_original_strings() {
        // This is the real-world scenario: crash log contains "Buffout 4 v1.28.6"
        // but valid versions list contains "1.28.6"
        let current = CrashgenVersion::parse("Buffout 4 v1.28.6").unwrap();
        let valid = vec![
            CrashgenVersion::parse("1.28.6").unwrap(),
            CrashgenVersion::parse("1.37.0").unwrap(),
        ];

        // Should be Valid because version numbers match, regardless of original string
        let status = current.check_version_status(&valid);
        assert_eq!(status, CrashgenVersionStatus::Valid);
    }

    #[test]
    fn test_check_crashgen_version_status_with_crashgen_prefix() {
        // Test the convenience function with real-world inputs
        let status = check_crashgen_version_status("Buffout 4 v1.28.6", &["1.28.6", "1.37.0"]);
        assert_eq!(status, CrashgenVersionStatus::Valid);

        let status = check_crashgen_version_status("Buffout 4 v1.37.0", &["1.28.6", "1.37.0"]);
        assert_eq!(status, CrashgenVersionStatus::Valid);

        let status = check_crashgen_version_status("Buffout 4 v1.26.0", &["1.28.6", "1.37.0"]);
        assert_eq!(status, CrashgenVersionStatus::Outdated);
    }
}
