//! Known game-version queries for CLASSIC, plus a transitional facade over the
//! loose version and PE helpers.
//!
//! The domain-neutral helpers — loose version parsing, comparison, extraction,
//! formatting, and PE file-version extraction — are owned by
//! [`classic_shared_core::version`]. This crate re-exports them under their
//! historical paths only until it retires (#258); new callers should import
//! the shared-core owner directly.
//!
//! What this crate still owns is the known-version policy:
//! [`is_known_fallout4_version`] and [`is_known_f4se_version`] answer their
//! questions from the Version Registry.
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_version_core::is_known_fallout4_version;
//! use classic_shared_core::version::parse_version;
//!
//! let version = parse_version("1.10.163.0").unwrap();
//! assert!(is_known_fallout4_version(&version));
//! ```

use semver::Version;

/// Transitional facade over [`classic_shared_core::version::pe_version`].
///
/// Kept so `classic_version_core::pe_version::*` keeps resolving until this
/// crate retires (#258). New callers import the shared-core owner.
pub use classic_shared_core::version::pe_version;

// Transitional facade: the loose-parsing and PE items are owned by
// `classic_shared_core::version`. These root re-exports end with #258.
pub use classic_shared_core::version::{
    PeVersionError, PeVersionResult, VersionError, VersionResult, compare_versions,
    extract_all_versions, extract_pe_version, extract_version_from_filename,
    extract_version_from_log, format_version, is_valid_executable_path, parse_version,
    try_parse_version,
};

// Re-export VersionRegistry for version information
pub use classic_version_registry_core::{
    VersionInfo, VersionRegistry, VersionRegistryError, get_version_registry,
};

// Re-export NULL_VERSION for convenience
pub use classic_version_registry_core::NULL_VERSION;

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
            // Call the shared-core owner directly, not this crate's transitional
            // re-export, so the policy code survives the facade's retirement (#258).
            if let Some(parsed) =
                classic_shared_core::version::try_parse_version(&xse.compatible_version)
                && &parsed == version
            {
                return true;
            }
        }
    }
    false
}

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
