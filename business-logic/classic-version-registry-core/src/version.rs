//! Game version type with 4-component support.
//!
//! This module provides the `GameVersion` type for representing game versions
//! with four components (major.minor.patch.build), as used by Bethesda games.
//!
//! The standard `semver` crate only supports 3 components, so we need a custom
//! type to properly handle versions like "1.10.163.0".

use std::cmp::Ordering;
use std::fmt;
use std::hash::{Hash, Hasher};
use std::str::FromStr;

use crate::VersionRegistryError;

/// A 4-component game version (major.minor.patch.build).
///
/// Represents game versions like "1.10.163.0" used by Bethesda games.
/// Supports parsing, comparison, and semantic distance calculations.
///
/// # Examples
///
/// ```rust
/// use classic_version_registry_core::GameVersion;
///
/// let v = GameVersion::parse("1.10.163.0").unwrap();
/// assert_eq!(v.major, 1);
/// assert_eq!(v.minor, 10);
/// assert_eq!(v.patch, 163);
/// assert_eq!(v.build, 0);
/// ```
#[derive(Debug, Clone, Copy)]
pub struct GameVersion {
    /// Major version component.
    pub major: u32,
    /// Minor version component.
    pub minor: u32,
    /// Patch version component.
    pub patch: u32,
    /// Build version component.
    pub build: u32,
}

impl GameVersion {
    /// Create a new GameVersion from components.
    ///
    /// # Arguments
    ///
    /// * `major` - Major version number
    /// * `minor` - Minor version number
    /// * `patch` - Patch version number
    /// * `build` - Build version number
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_version_registry_core::GameVersion;
    ///
    /// let v = GameVersion::new(1, 10, 163, 0);
    /// assert_eq!(v.to_string(), "1.10.163.0");
    /// ```
    #[must_use]
    pub const fn new(major: u32, minor: u32, patch: u32, build: u32) -> Self {
        Self {
            major,
            minor,
            patch,
            build,
        }
    }

    /// Parse a version string into a GameVersion.
    ///
    /// Accepts either 3-component ("1.10.163") or 4-component ("1.10.163.0")
    /// version strings. If only 3 components are provided, build defaults to 0.
    ///
    /// # Arguments
    ///
    /// * `s` - Version string to parse
    ///
    /// # Returns
    ///
    /// * `Ok(GameVersion)` - Successfully parsed version
    /// * `Err(VersionRegistryError)` - Invalid version string
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_version_registry_core::GameVersion;
    ///
    /// // 4-component version
    /// let v1 = GameVersion::parse("1.10.163.0").unwrap();
    /// assert_eq!(v1.build, 0);
    ///
    /// // 3-component version (build defaults to 0)
    /// let v2 = GameVersion::parse("1.10.163").unwrap();
    /// assert_eq!(v2.build, 0);
    /// ```
    pub fn parse(s: &str) -> Result<Self, VersionRegistryError> {
        let parts: Vec<&str> = s.trim().split('.').collect();

        if parts.len() < 3 || parts.len() > 4 {
            return Err(VersionRegistryError::InvalidVersion(format!(
                "Expected 3 or 4 components, got {}: '{}'",
                parts.len(),
                s
            )));
        }

        let major = parts[0].parse::<u32>().map_err(|_| {
            VersionRegistryError::InvalidVersion(format!("Invalid major version in '{}'", s))
        })?;

        let minor = parts[1].parse::<u32>().map_err(|_| {
            VersionRegistryError::InvalidVersion(format!("Invalid minor version in '{}'", s))
        })?;

        let patch = parts[2].parse::<u32>().map_err(|_| {
            VersionRegistryError::InvalidVersion(format!("Invalid patch version in '{}'", s))
        })?;

        let build = if parts.len() == 4 {
            parts[3].parse::<u32>().map_err(|_| {
                VersionRegistryError::InvalidVersion(format!("Invalid build version in '{}'", s))
            })?
        } else {
            0
        };

        Ok(Self {
            major,
            minor,
            patch,
            build,
        })
    }

    /// Calculate the semantic distance between two versions.
    ///
    /// Uses a weighted formula where major differences are most significant:
    /// - Major difference: × 1,000,000
    /// - Minor difference: × 1,000
    /// - Patch difference: × 1
    /// - Build differences are not included (too fine-grained)
    ///
    /// This is used by the version matcher to find the nearest known version.
    ///
    /// # Arguments
    ///
    /// * `other` - The other version to compare against
    ///
    /// # Returns
    ///
    /// The semantic distance as a u64.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_version_registry_core::GameVersion;
    ///
    /// let v1 = GameVersion::parse("1.10.163.0").unwrap();
    /// let v2 = GameVersion::parse("1.10.500.0").unwrap();
    /// let v3 = GameVersion::parse("2.0.0.0").unwrap();
    ///
    /// // Same major version, patch difference
    /// assert_eq!(v1.semantic_distance(&v2), 337);
    ///
    /// // Different major version - much larger distance
    /// assert!(v1.semantic_distance(&v3) > 1_000_000);
    /// ```
    #[must_use]
    pub fn semantic_distance(&self, other: &Self) -> u64 {
        let major_diff = (self.major as i64 - other.major as i64).unsigned_abs();
        let minor_diff = (self.minor as i64 - other.minor as i64).unsigned_abs();
        let patch_diff = (self.patch as i64 - other.patch as i64).unsigned_abs();

        major_diff * 1_000_000 + minor_diff * 1_000 + patch_diff
    }

    /// Check if this version has the same major version as another.
    ///
    /// Used by the version matcher to ensure nearest matches are
    /// within the same major version.
    ///
    /// # Arguments
    ///
    /// * `other` - The other version to compare
    ///
    /// # Returns
    ///
    /// `true` if both versions have the same major component.
    #[must_use]
    pub fn same_major(&self, other: &Self) -> bool {
        self.major == other.major
    }
}

impl fmt::Display for GameVersion {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}.{}.{}.{}",
            self.major, self.minor, self.patch, self.build
        )
    }
}

impl FromStr for GameVersion {
    type Err = VersionRegistryError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Self::parse(s)
    }
}

impl PartialEq for GameVersion {
    fn eq(&self, other: &Self) -> bool {
        self.major == other.major
            && self.minor == other.minor
            && self.patch == other.patch
            && self.build == other.build
    }
}

impl Eq for GameVersion {}

impl PartialOrd for GameVersion {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for GameVersion {
    fn cmp(&self, other: &Self) -> Ordering {
        match self.major.cmp(&other.major) {
            Ordering::Equal => {}
            ord => return ord,
        }
        match self.minor.cmp(&other.minor) {
            Ordering::Equal => {}
            ord => return ord,
        }
        match self.patch.cmp(&other.patch) {
            Ordering::Equal => {}
            ord => return ord,
        }
        self.build.cmp(&other.build)
    }
}

impl Hash for GameVersion {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.major.hash(state);
        self.minor.hash(state);
        self.patch.hash(state);
        self.build.hash(state);
    }
}

impl Default for GameVersion {
    fn default() -> Self {
        Self::new(0, 0, 0, 0)
    }
}

#[cfg(test)]
#[path = "version_tests.rs"]
mod tests;
