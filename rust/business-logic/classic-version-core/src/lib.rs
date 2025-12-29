//! Version detection and parsing utilities for CLASSIC.
//!
//! This crate provides comprehensive version handling for game versions, XSE versions,
//! and mod versions. It includes parsing from various string formats, comparison,
//! validation, and extraction from file names and log files.
//!
//! # Features
//!
//! - **Version Parsing**: Parse versions from strings with flexible formats
//! - **Version Comparison**: Semantic version comparison
//! - **Version Extraction**: Extract versions from file names and log content
//! - **Version Validation**: Validate version strings against known versions
//!
//! # Examples
//!
//! ```rust
//! use classic_version_core::{parse_version, compare_versions, extract_version_from_filename};
//! use semver::Version;
//!
//! // Parse a version string
//! let version = parse_version("1.10.163.0").unwrap();
//! assert_eq!(version, Version::new(1, 10, 163));
//!
//! // Compare versions
//! let v1 = Version::new(1, 10, 163);
//! let v2 = Version::new(1, 10, 984);
//! assert!(compare_versions(&v1, &v2).is_lt());
//!
//! // Extract version from filename
//! if let Some(version) = extract_version_from_filename("MyMod-v1.2.3.esp") {
//!     assert_eq!(version, Version::new(1, 2, 3));
//! }
//! ```

use regex::Regex;
use semver::Version;
use std::cmp::Ordering;
use thiserror::Error;

// Re-export version constants from classic-constants-core
// These are deprecated - use get_version_registry() instead
#[allow(deprecated)]
pub use classic_constants_core::{
    F4SE_NG_VERSION, F4SE_OG_VERSION, F4SE_VERSIONS, FALLOUT4_NG_VERSION, FALLOUT4_OG_VERSION,
    FALLOUT4_VERSIONS, FALLOUT4_VR_VERSION, NULL_VERSION,
};

// Re-export VersionRegistry for new code
pub use classic_constants_core::{
    VersionInfo, VersionRegistry, VersionRegistryError, get_version_registry,
};

/// Version parsing and comparison errors.
#[derive(Error, Debug)]
pub enum VersionError {
    /// Failed to parse version string.
    #[error("Invalid version string: {0}")]
    ParseError(String),

    /// Version string is empty.
    #[error("Version string is empty")]
    EmptyVersion,

    /// Version not found in input.
    #[error("No version found in: {0}")]
    NotFound(String),

    /// Invalid version format.
    #[error("Invalid version format: {0}")]
    InvalidFormat(String),
}

/// Result type for version operations.
pub type VersionResult<T> = Result<T, VersionError>;

// ============================================================================
// Version Parsing
// ============================================================================

/// Parse a version string into a `semver::Version`.
///
/// Accepts various version formats:
/// - "1.10.163" → Version::new(1, 10, 163)
/// - "1.10.163.0" → Version::new(1, 10, 163)
/// - "v1.10.163" → Version::new(1, 10, 163)
/// - "1.10" → Version::new(1, 10, 0)
///
/// The fourth component (build number) is ignored if present.
///
/// # Arguments
///
/// * `version_str` - The version string to parse
///
/// # Returns
///
/// A `Version` object or a `VersionError` if parsing fails.
///
/// # Examples
///
/// ```rust
/// use classic_version_core::parse_version;
/// use semver::Version;
///
/// let v = parse_version("1.10.163.0").unwrap();
/// assert_eq!(v, Version::new(1, 10, 163));
///
/// let v = parse_version("v1.10.163").unwrap();
/// assert_eq!(v, Version::new(1, 10, 163));
/// ```
pub fn parse_version(version_str: &str) -> VersionResult<Version> {
    if version_str.is_empty() {
        return Err(VersionError::EmptyVersion);
    }

    // Remove common prefixes
    let cleaned = version_str
        .trim()
        .trim_start_matches('v')
        .trim_start_matches('V');

    // Split by dots
    let parts: Vec<&str> = cleaned.split('.').collect();

    if parts.is_empty() || parts.len() < 2 {
        return Err(VersionError::InvalidFormat(format!(
            "Version must have at least major.minor: {}",
            version_str
        )));
    }

    // Parse major, minor, and optional patch
    let major = parts[0]
        .parse::<u64>()
        .map_err(|_| VersionError::ParseError(format!("Invalid major version: {}", parts[0])))?;

    let minor = parts[1]
        .parse::<u64>()
        .map_err(|_| VersionError::ParseError(format!("Invalid minor version: {}", parts[1])))?;

    let patch = if parts.len() >= 3 {
        parts[2]
            .parse::<u64>()
            .map_err(|_| VersionError::ParseError(format!("Invalid patch version: {}", parts[2])))?
    } else {
        0
    };

    // Note: We ignore the 4th component (build number) if present
    // semver only supports major.minor.patch

    Ok(Version::new(major, minor, patch))
}

/// Try to parse a version string, returning None on failure.
///
/// This is a convenience wrapper around `parse_version` that returns `None`
/// instead of an error.
///
/// # Arguments
///
/// * `version_str` - The version string to parse
///
/// # Returns
///
/// `Some(Version)` if parsing succeeds, `None` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_version_core::try_parse_version;
///
/// assert!(try_parse_version("1.10.163").is_some());
/// assert!(try_parse_version("invalid").is_none());
/// ```
pub fn try_parse_version(version_str: &str) -> Option<Version> {
    parse_version(version_str).ok()
}

// ============================================================================
// Version Comparison
// ============================================================================

/// Compare two versions.
///
/// # Arguments
///
/// * `v1` - First version
/// * `v2` - Second version
///
/// # Returns
///
/// `Ordering` indicating whether v1 is less than, equal to, or greater than v2.
///
/// # Examples
///
/// ```rust
/// use classic_version_core::compare_versions;
/// use semver::Version;
/// use std::cmp::Ordering;
///
/// let v1 = Version::new(1, 10, 163);
/// let v2 = Version::new(1, 10, 984);
/// assert_eq!(compare_versions(&v1, &v2), Ordering::Less);
/// ```
#[must_use]
pub fn compare_versions(v1: &Version, v2: &Version) -> Ordering {
    v1.cmp(v2)
}

/// Check if a version matches a known game version.
///
/// Uses the VersionRegistry to look up all known Fallout 4 game versions
/// (OG and NG, excluding VR).
///
/// # Arguments
///
/// * `version` - The version to check
///
/// # Returns
///
/// `true` if the version matches a known Fallout 4 version.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_version_core::is_known_fallout4_version;
/// use semver::Version;
///
/// let og_version = Version::new(1, 10, 163);
/// assert!(is_known_fallout4_version(&og_version));
/// ```
#[must_use]
pub fn is_known_fallout4_version(version: &Version) -> bool {
    let registry = get_version_registry();
    // Get all Fallout4 versions (non-VR only, matching old FALLOUT4_VERSIONS behavior)
    for info in registry.get_all_for_game("Fallout4", Some(false)) {
        let game_ver = &info.version;
        let semver = Version::new(
            u64::from(game_ver.major),
            u64::from(game_ver.minor),
            u64::from(game_ver.patch),
        );
        if &semver == version {
            return true;
        }
    }
    false
}

/// Check if a version matches a known F4SE version.
///
/// Uses the VersionRegistry to look up all known F4SE versions.
///
/// # Arguments
///
/// * `version` - The version to check
///
/// # Returns
///
/// `true` if the version matches a known F4SE version.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_version_core::is_known_f4se_version;
/// use semver::Version;
///
/// let f4se_og_version = Version::new(0, 6, 23);
/// assert!(is_known_f4se_version(&f4se_og_version));
/// ```
#[must_use]
pub fn is_known_f4se_version(version: &Version) -> bool {
    let registry = get_version_registry();
    // Get all Fallout4 versions (non-VR only, matching old F4SE_VERSIONS behavior)
    for info in registry.get_all_for_game("Fallout4", Some(false)) {
        if let Some(xse) = &info.xse {
            // compatible_version is a String like "0.6.23", parse it
            if let Some(parsed) = try_parse_version(&xse.compatible_version) {
                if &parsed == version {
                    return true;
                }
            }
        }
    }
    false
}

// ============================================================================
// Version Extraction
// ============================================================================

/// Extract version from a filename.
///
/// Looks for common version patterns in filenames:
/// - "ModName-v1.2.3.esp"
/// - "ModName_1.2.3.esp"
/// - "ModName 1.2.3.esp"
/// - "ModName-1.2.3-suffix.esp"
///
/// # Arguments
///
/// * `filename` - The filename to parse
///
/// # Returns
///
/// `Some(Version)` if a version is found, `None` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_version_core::extract_version_from_filename;
/// use semver::Version;
///
/// let version = extract_version_from_filename("MyMod-v1.2.3.esp").unwrap();
/// assert_eq!(version, Version::new(1, 2, 3));
///
/// let version = extract_version_from_filename("MyMod_1.2.3.esp").unwrap();
/// assert_eq!(version, Version::new(1, 2, 3));
/// ```
pub fn extract_version_from_filename(filename: &str) -> Option<Version> {
    // Common patterns for versions in filenames
    let patterns = [
        r"v?(\d+)\.(\d+)\.(\d+)\.(\d+)", // 1.2.3.4 or v1.2.3.4
        r"v?(\d+)\.(\d+)\.(\d+)",        // 1.2.3 or v1.2.3
        r"v?(\d+)\.(\d+)",               // 1.2 or v1.2
    ];

    for pattern in &patterns {
        if let Ok(re) = Regex::new(pattern) {
            if let Some(captures) = re.captures(filename) {
                let major = captures.get(1)?.as_str().parse::<u64>().ok()?;
                let minor = captures.get(2)?.as_str().parse::<u64>().ok()?;
                let patch = captures
                    .get(3)
                    .and_then(|m| m.as_str().parse::<u64>().ok())
                    .unwrap_or(0);

                return Some(Version::new(major, minor, patch));
            }
        }
    }

    None
}

/// Extract version from log content.
///
/// Searches for version patterns in log file content.
/// Common patterns include:
/// - "version: 1.2.3"
/// - "v1.2.3"
/// - "Version 1.2.3.4"
///
/// # Arguments
///
/// * `log_content` - The log file content to parse
///
/// # Returns
///
/// `Some(Version)` if a version is found, `None` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_version_core::extract_version_from_log;
/// use semver::Version;
///
/// let log = "F4SE version: 0.6.23\nGame version: 1.10.163";
/// let version = extract_version_from_log(log).unwrap();
/// // Returns the first version found
/// ```
pub fn extract_version_from_log(log_content: &str) -> Option<Version> {
    // Pattern for version in logs (more flexible)
    let pattern = r"(?i)version[:\s]+v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?";

    if let Ok(re) = Regex::new(pattern) {
        if let Some(captures) = re.captures(log_content) {
            let major = captures.get(1)?.as_str().parse::<u64>().ok()?;
            let minor = captures.get(2)?.as_str().parse::<u64>().ok()?;
            let patch = captures
                .get(3)
                .and_then(|m| m.as_str().parse::<u64>().ok())
                .unwrap_or(0);

            return Some(Version::new(major, minor, patch));
        }
    }

    // Fallback: Try to extract any version-like pattern
    extract_version_from_filename(log_content)
}

/// Extract all versions from text content.
///
/// Finds all version patterns in the text and returns them as a vector.
///
/// # Arguments
///
/// * `content` - The text content to parse
///
/// # Returns
///
/// A vector of all versions found in the content.
///
/// # Examples
///
/// ```rust
/// use classic_version_core::extract_all_versions;
///
/// let text = "Supports versions 1.10.163 and 1.10.984";
/// let versions = extract_all_versions(text);
/// assert_eq!(versions.len(), 2);
/// ```
pub fn extract_all_versions(content: &str) -> Vec<Version> {
    let mut versions = Vec::new();
    let pattern = r"v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?";

    if let Ok(re) = Regex::new(pattern) {
        for captures in re.captures_iter(content) {
            if let Some(major) = captures.get(1).and_then(|m| m.as_str().parse::<u64>().ok()) {
                if let Some(minor) = captures.get(2).and_then(|m| m.as_str().parse::<u64>().ok()) {
                    let patch = captures
                        .get(3)
                        .and_then(|m| m.as_str().parse::<u64>().ok())
                        .unwrap_or(0);

                    versions.push(Version::new(major, minor, patch));
                }
            }
        }
    }

    versions
}

// ============================================================================
// Version Formatting
// ============================================================================

/// Format version as string with optional prefix.
///
/// # Arguments
///
/// * `version` - The version to format
/// * `prefix` - Optional prefix (e.g., "v")
///
/// # Returns
///
/// Formatted version string.
///
/// # Examples
///
/// ```rust
/// use classic_version_core::format_version;
/// use semver::Version;
///
/// let v = Version::new(1, 10, 163);
/// assert_eq!(format_version(&v, Some("v")), "v1.10.163");
/// assert_eq!(format_version(&v, None), "1.10.163");
/// ```
#[must_use]
pub fn format_version(version: &Version, prefix: Option<&str>) -> String {
    match prefix {
        Some(p) => format!("{}{}", p, version),
        None => version.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_version() {
        assert_eq!(parse_version("1.10.163").unwrap(), Version::new(1, 10, 163));
        assert_eq!(
            parse_version("1.10.163.0").unwrap(),
            Version::new(1, 10, 163)
        );
        assert_eq!(
            parse_version("v1.10.163").unwrap(),
            Version::new(1, 10, 163)
        );
        assert_eq!(parse_version("0.6.23").unwrap(), Version::new(0, 6, 23));
    }

    #[test]
    fn test_parse_version_errors() {
        assert!(parse_version("").is_err());
        assert!(parse_version("invalid").is_err());
        assert!(parse_version("1").is_err());
    }

    #[test]
    fn test_try_parse_version() {
        assert!(try_parse_version("1.10.163").is_some());
        assert!(try_parse_version("invalid").is_none());
    }

    #[test]
    fn test_compare_versions() {
        let v1 = Version::new(1, 10, 163);
        let v2 = Version::new(1, 10, 984);
        assert_eq!(compare_versions(&v1, &v2), Ordering::Less);
        assert_eq!(compare_versions(&v2, &v1), Ordering::Greater);
        assert_eq!(compare_versions(&v1, &v1), Ordering::Equal);
    }

    #[test]
    #[allow(deprecated)]
    fn test_is_known_fallout4_version() {
        assert!(is_known_fallout4_version(&FALLOUT4_OG_VERSION));
        assert!(is_known_fallout4_version(&FALLOUT4_NG_VERSION));
        assert!(!is_known_fallout4_version(&Version::new(9, 9, 9)));
    }

    #[test]
    #[allow(deprecated)]
    fn test_is_known_f4se_version() {
        assert!(is_known_f4se_version(&F4SE_OG_VERSION));
        assert!(is_known_f4se_version(&F4SE_NG_VERSION));
        assert!(!is_known_f4se_version(&Version::new(9, 9, 9)));
    }

    #[test]
    fn test_extract_version_from_filename() {
        assert_eq!(
            extract_version_from_filename("MyMod-v1.2.3.esp"),
            Some(Version::new(1, 2, 3))
        );
        assert_eq!(
            extract_version_from_filename("MyMod_1.2.3.esp"),
            Some(Version::new(1, 2, 3))
        );
        assert_eq!(
            extract_version_from_filename("MyMod-1.2.3.4-suffix.esp"),
            Some(Version::new(1, 2, 3))
        );
        assert!(extract_version_from_filename("NoVersion.esp").is_none());
    }

    #[test]
    fn test_extract_version_from_log() {
        let log = "F4SE version: 0.6.23\nGame version: 1.10.163";
        let version = extract_version_from_log(log).unwrap();
        assert_eq!(version, Version::new(0, 6, 23));
    }

    #[test]
    fn test_extract_all_versions() {
        let text = "Supports versions 1.10.163 and 1.10.984";
        let versions = extract_all_versions(text);
        assert_eq!(versions.len(), 2);
        assert!(versions.contains(&Version::new(1, 10, 163)));
        assert!(versions.contains(&Version::new(1, 10, 984)));
    }

    #[test]
    fn test_format_version() {
        let v = Version::new(1, 10, 163);
        assert_eq!(format_version(&v, Some("v")), "v1.10.163");
        assert_eq!(format_version(&v, None), "1.10.163");
    }
}
