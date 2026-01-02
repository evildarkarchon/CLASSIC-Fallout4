//! Data models for version registry.
//!
//! This module defines the core data structures used to represent game version
//! metadata, including version information, Address Library configuration,
//! Script Extender configuration, and version matching structures.

use std::collections::HashMap;
use std::convert::Infallible;
use std::str::FromStr;

use crate::GameVersion;

/// Address Library file format.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub enum AddressLibFormat {
    /// Binary format (.bin) - used by non-VR versions.
    #[default]
    Bin,
    /// CSV format (.csv) - used by VR versions.
    Csv,
}

impl FromStr for AddressLibFormat {
    type Err = Infallible;

    /// Parse format from string.
    ///
    /// # Arguments
    ///
    /// * `s` - Format string ("bin" or "csv")
    ///
    /// # Returns
    ///
    /// The parsed format, defaulting to `Bin` for unrecognized values.
    /// This implementation is infallible - it always succeeds.
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(match s.to_lowercase().as_str() {
            "csv" => Self::Csv,
            _ => Self::Bin,
        })
    }
}

impl AddressLibFormat {
    /// Get the file extension for this format.
    #[must_use]
    pub const fn extension(&self) -> &'static str {
        match self {
            Self::Bin => "bin",
            Self::Csv => "csv",
        }
    }
}

/// Address Library configuration for a game version.
///
/// Contains the filename and download URL for the Address Library file
/// required by script extenders for this game version.
#[derive(Debug, Clone)]
pub struct AddressLibraryConfig {
    /// Filename of the Address Library file (e.g., "version-1-10-163-0.bin").
    pub filename: String,
    /// File format (bin or csv).
    pub format: AddressLibFormat,
    /// Nexus Mods download URL.
    pub nexus_url: String,
}

impl AddressLibraryConfig {
    /// Create a new Address Library configuration.
    #[must_use]
    pub fn new(
        filename: impl Into<String>,
        format: AddressLibFormat,
        nexus_url: impl Into<String>,
    ) -> Self {
        Self {
            filename: filename.into(),
            format,
            nexus_url: nexus_url.into(),
        }
    }
}

/// Script Extender (XSE) configuration for a game version.
///
/// Contains information about the script extender compatible with this
/// game version, including the version and loader executable.
#[derive(Debug, Clone)]
pub struct XseConfig {
    /// XSE acronym (e.g., "F4SE", "F4SEVR", "SKSE").
    pub acronym: String,
    /// Compatible XSE version (e.g., "0.6.23").
    pub compatible_version: String,
    /// Loader executable name (e.g., "f4se_loader.exe").
    pub loader: String,
}

impl XseConfig {
    /// Create a new XSE configuration.
    #[must_use]
    pub fn new(
        acronym: impl Into<String>,
        compatible_version: impl Into<String>,
        loader: impl Into<String>,
    ) -> Self {
        Self {
            acronym: acronym.into(),
            compatible_version: compatible_version.into(),
            loader: loader.into(),
        }
    }
}

/// Version range for matching unknown versions.
///
/// Defines a range of versions that are considered compatible with
/// a specific version entry. Used for graceful matching when the
/// exact version is not in the registry.
#[derive(Debug, Clone)]
pub struct CompatibleRange {
    /// Minimum version (inclusive).
    pub min_version: GameVersion,
    /// Maximum version (inclusive).
    pub max_version: GameVersion,
}

impl CompatibleRange {
    /// Create a new compatible range.
    #[must_use]
    pub const fn new(min_version: GameVersion, max_version: GameVersion) -> Self {
        Self {
            min_version,
            max_version,
        }
    }

    /// Create from version strings.
    ///
    /// # Arguments
    ///
    /// * `min_str` - Minimum version string
    /// * `max_str` - Maximum version string
    ///
    /// # Returns
    ///
    /// * `Ok(CompatibleRange)` - Successfully parsed range
    /// * `Err(VersionRegistryError)` - Invalid version string
    pub fn from_strings(min_str: &str, max_str: &str) -> crate::Result<Self> {
        Ok(Self {
            min_version: GameVersion::parse(min_str)?,
            max_version: GameVersion::parse(max_str)?,
        })
    }

    /// Check if a version falls within this range.
    ///
    /// # Arguments
    ///
    /// * `version` - The version to check
    ///
    /// # Returns
    ///
    /// `true` if the version is within the range (inclusive).
    #[must_use]
    pub fn contains(&self, version: &GameVersion) -> bool {
        version >= &self.min_version && version <= &self.max_version
    }
}

/// Complete version information for a game version.
///
/// Contains all metadata about a specific game version, including
/// version number, display name, Address Library configuration,
/// script extender configuration, and matching settings.
#[derive(Debug, Clone)]
pub struct VersionInfo {
    /// Unique identifier (e.g., "FO4_OG", "FO4_NG", "FO4_VR").
    pub id: String,
    /// Game identifier (e.g., "Fallout4", "SkyrimSE").
    pub game: String,
    /// Whether this is a VR version.
    pub is_vr: bool,
    /// The game version.
    pub version: GameVersion,
    /// Human-readable display name (e.g., "Fallout 4 Original").
    pub display_name: String,
    /// Short name for quick reference (e.g., "OG", "NG", "VR").
    pub short_name: String,
    /// Description of this version.
    pub description: String,
    /// Address Library configuration, if applicable.
    pub address_library: Option<AddressLibraryConfig>,
    /// Script Extender configuration, if applicable.
    pub xse: Option<XseConfig>,
    /// Compatible version range for matching.
    pub compatible_range: Option<CompatibleRange>,
    /// Priority for matching (higher = preferred).
    pub priority: i32,
    /// Whether this version is deprecated.
    pub deprecated: bool,
}

impl VersionInfo {
    /// Get the version as a string.
    #[must_use]
    pub fn version_string(&self) -> String {
        self.version.to_string()
    }

    /// Check if a detected version is compatible with this version.
    ///
    /// Uses the compatible_range if defined, otherwise requires exact match.
    #[must_use]
    pub fn is_compatible_with(&self, detected: &GameVersion) -> bool {
        if let Some(range) = &self.compatible_range {
            range.contains(detected)
        } else {
            &self.version == detected
        }
    }
}

/// Strategy for handling unknown versions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub enum UnknownVersionStrategy {
    /// Try to match to the nearest known version.
    #[default]
    NearestMatch,
    /// Only allow exact matches (fail on unknown versions).
    Strict,
    /// Use a default version for the game.
    DefaultOnly,
}

impl FromStr for UnknownVersionStrategy {
    type Err = Infallible;

    /// Parse strategy from string.
    ///
    /// Defaults to `NearestMatch` for unrecognized values.
    /// This implementation is infallible - it always succeeds.
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(match s.to_lowercase().as_str() {
            "strict" => Self::Strict,
            "default_only" => Self::DefaultOnly,
            _ => Self::NearestMatch,
        })
    }
}

/// Log level for unknown version warnings.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub enum LogLevel {
    /// Debug level (not shown by default).
    Debug,
    /// Warning level (shown by default).
    #[default]
    Warning,
    /// Error level (always shown).
    Error,
}

impl FromStr for LogLevel {
    type Err = Infallible;

    /// Parse log level from string.
    ///
    /// Defaults to `Warning` for unrecognized values.
    /// This implementation is infallible - it always succeeds.
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(match s.to_lowercase().as_str() {
            "debug" => Self::Debug,
            "error" => Self::Error,
            _ => Self::Warning,
        })
    }
}

/// Configuration for handling unknown versions.
///
/// Specifies how the registry should handle versions that are not
/// explicitly defined in the configuration.
#[derive(Debug, Clone, Default)]
pub struct UnknownVersionHandling {
    /// Strategy for matching unknown versions.
    pub strategy: UnknownVersionStrategy,
    /// Default version IDs for each game (game -> version_id).
    pub defaults: HashMap<String, String>,
    /// Log level for unknown version warnings.
    pub log_level: LogLevel,
}

impl UnknownVersionHandling {
    /// Create a new unknown version handling configuration.
    #[must_use]
    pub fn new(
        strategy: UnknownVersionStrategy,
        defaults: HashMap<String, String>,
        log_level: LogLevel,
    ) -> Self {
        Self {
            strategy,
            defaults,
            log_level,
        }
    }

    /// Get the default version ID for a game.
    #[must_use]
    pub fn get_default(&self, game: &str) -> Option<&str> {
        self.defaults.get(game).map(String::as_str)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_address_lib_format() {
        assert_eq!(
            "bin".parse::<AddressLibFormat>().unwrap(),
            AddressLibFormat::Bin
        );
        assert_eq!(
            "csv".parse::<AddressLibFormat>().unwrap(),
            AddressLibFormat::Csv
        );
        assert_eq!(
            "CSV".parse::<AddressLibFormat>().unwrap(),
            AddressLibFormat::Csv
        );
        assert_eq!(
            "unknown".parse::<AddressLibFormat>().unwrap(),
            AddressLibFormat::Bin
        );
    }

    #[test]
    fn test_compatible_range() {
        let range = CompatibleRange::from_strings("1.10.163.0", "1.10.163.999").unwrap();

        assert!(range.contains(&GameVersion::parse("1.10.163.0").unwrap()));
        assert!(range.contains(&GameVersion::parse("1.10.163.500").unwrap()));
        assert!(range.contains(&GameVersion::parse("1.10.163.999").unwrap()));
        assert!(!range.contains(&GameVersion::parse("1.10.164.0").unwrap()));
        assert!(!range.contains(&GameVersion::parse("1.10.162.0").unwrap()));
    }

    #[test]
    fn test_unknown_version_strategy() {
        assert_eq!(
            "nearest_match".parse::<UnknownVersionStrategy>().unwrap(),
            UnknownVersionStrategy::NearestMatch
        );
        assert_eq!(
            "strict".parse::<UnknownVersionStrategy>().unwrap(),
            UnknownVersionStrategy::Strict
        );
        assert_eq!(
            "default_only".parse::<UnknownVersionStrategy>().unwrap(),
            UnknownVersionStrategy::DefaultOnly
        );
    }
}
