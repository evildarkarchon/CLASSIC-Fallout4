//! Known game-version queries.
//!
//! These answer "is this a known Fallout 4 / F4SE version?" from Version
//! Registry data. The methods on [`VersionRegistry`] answer from that
//! snapshot, so a caller holding a [`crate::VersionRegistryScope`] queries its
//! own scope; the free functions answer from the process default snapshot.
//!
//! Both queries consider only non-VR `Fallout4` entries and compare the first
//! three components, matching the historical `FALLOUT4_VERSIONS` and
//! `F4SE_VERSIONS` tables they replaced.

use semver::Version;

use crate::{VersionRegistry, get_version_registry};

impl VersionRegistry {
    /// Report whether `version` equals a known non-VR Fallout 4 game version.
    ///
    /// Each registry `GameVersion` is compared as `major.minor.patch`; the
    /// fourth (build) component is dropped. Only exact equality counts.
    #[must_use]
    pub fn is_known_fallout4_version(&self, version: &Version) -> bool {
        self.get_all_for_game("Fallout4", Some(false))
            .into_iter()
            .any(|info| {
                let game_version = &info.version;
                Version::new(
                    u64::from(game_version.major),
                    u64::from(game_version.minor),
                    u64::from(game_version.patch),
                ) == *version
            })
    }

    /// Report whether `version` equals the F4SE version a non-VR Fallout 4
    /// entry declares as compatible.
    ///
    /// Each entry's `xse.compatible_version` string is parsed with the
    /// lenient shared-core [`try_parse_version`]; entries without an XSE
    /// section or with an unparseable string never match.
    ///
    /// [`try_parse_version`]: classic_shared_core::version::try_parse_version
    #[must_use]
    pub fn is_known_f4se_version(&self, version: &Version) -> bool {
        self.get_all_for_game("Fallout4", Some(false))
            .into_iter()
            .filter_map(|info| info.xse.as_ref())
            .filter_map(|xse| {
                classic_shared_core::version::try_parse_version(&xse.compatible_version)
            })
            .any(|parsed| parsed == *version)
    }
}

/// Check a version against the default snapshot's known Fallout 4 versions.
///
/// Equivalent to `get_version_registry().is_known_fallout4_version(version)`;
/// see [`VersionRegistry::is_known_fallout4_version`].
///
/// # Examples
///
/// ```rust,no_run
/// use classic_version_registry_core::is_known_fallout4_version;
/// use semver::Version;
///
/// assert!(is_known_fallout4_version(&Version::new(1, 10, 163)));
/// ```
#[must_use]
pub fn is_known_fallout4_version(version: &Version) -> bool {
    get_version_registry().is_known_fallout4_version(version)
}

/// Check a version against the default snapshot's known F4SE versions.
///
/// Equivalent to `get_version_registry().is_known_f4se_version(version)`;
/// see [`VersionRegistry::is_known_f4se_version`].
///
/// # Examples
///
/// ```rust,no_run
/// use classic_version_registry_core::is_known_f4se_version;
/// use semver::Version;
///
/// assert!(is_known_f4se_version(&Version::new(0, 6, 23)));
/// ```
#[must_use]
pub fn is_known_f4se_version(version: &Version) -> bool {
    get_version_registry().is_known_f4se_version(version)
}

#[cfg(test)]
#[path = "known_versions_tests.rs"]
mod tests;
