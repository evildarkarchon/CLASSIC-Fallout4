//! Version handling for crash generator version comparison
//!
//! This module provides version parsing and comparison functionality compatible
//! with Python's `packaging.version.Version` for crash generator versions.
//!
//! Crash generator versions typically follow semver format (e.g., "1.28.0", "1.29.1").

use once_cell::sync::Lazy;
use regex::Regex;
use semver::Version;
use std::cmp::Ordering;

/// Pattern to extract version numbers from strings like "Buffout 4 v1.28.0"
static VERSION_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"v?(\d+)\.(\d+)\.?(\d*)").expect("Invalid version regex pattern")
});

/// Represents a crashgen version that can be compared
#[derive(Debug, Clone, Default, PartialEq, Eq)]
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
                    if s.is_empty() {
                        None
                    } else {
                        s.parse().ok()
                    }
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
    /// This matches Python's version comparison logic:
    /// - If VR mode: Check against both version_latest_vr AND version_latest
    /// - If non-VR: Check only against version_latest
    ///
    /// # Arguments
    ///
    /// * `latest` - The latest non-VR version
    /// * `latest_vr` - The latest VR version
    /// * `is_vr_mode` - Whether the game is in VR mode
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
    pub fn is_outdated(&self, latest: &CrashgenVersion, latest_vr: &CrashgenVersion, is_vr_mode: bool) -> bool {
        // Port of Python logic:
        // if (version_current < version_latest_vr and version_current != version_latest) or
        //    (not game_is_vr and version_current < version_latest):
        //     # outdated

        if is_vr_mode {
            // VR mode: Check against VR version, but allow if matches non-VR latest
            self < latest_vr && self != latest
        } else {
            // Non-VR mode: Check against non-VR latest
            self < latest
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

    #[test]
    fn test_is_outdated_non_vr() {
        let current = CrashgenVersion::new(1, 26, 0);
        let latest = CrashgenVersion::new(1, 28, 0);
        let latest_vr = CrashgenVersion::new(1, 27, 0);

        assert!(current.is_outdated(&latest, &latest_vr, false));
    }

    #[test]
    fn test_is_outdated_vr() {
        let current = CrashgenVersion::new(1, 26, 0);
        let latest = CrashgenVersion::new(1, 28, 0);
        let latest_vr = CrashgenVersion::new(1, 27, 0);

        assert!(current.is_outdated(&latest, &latest_vr, true));
    }

    #[test]
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
}
