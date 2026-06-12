//! Data models for version registry.
//!
//! This module defines the core data structures used to represent game version
//! metadata, including version information, Address Library configuration,
//! Script Extender configuration, crash generator configuration, and version
//! matching structures.

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
    /// Full display name (e.g., "Fallout 4 Script Extender (F4SE)").
    pub full_name: String,
    /// Compatible XSE version (e.g., "0.6.23").
    pub compatible_version: String,
    /// Loader executable name (e.g., "f4se_loader.exe").
    pub loader: String,
    /// Expected number of script files (e.g., 29).
    pub file_count: u32,
    /// SHA-256 hashes for XSE script files, as (filename, hash) pairs.
    /// Used for validating that installed scripts match the expected version.
    pub script_hashes: Vec<(String, String)>,
}

impl XseConfig {
    /// Create a new XSE configuration.
    #[must_use]
    pub fn new(
        acronym: impl Into<String>,
        full_name: impl Into<String>,
        compatible_version: impl Into<String>,
        loader: impl Into<String>,
        file_count: u32,
    ) -> Self {
        Self {
            acronym: acronym.into(),
            full_name: full_name.into(),
            compatible_version: compatible_version.into(),
            loader: loader.into(),
            file_count,
            script_hashes: Vec::new(),
        }
    }

    /// Create a new XSE configuration with script hashes.
    #[must_use]
    pub fn with_script_hashes(
        acronym: impl Into<String>,
        full_name: impl Into<String>,
        compatible_version: impl Into<String>,
        loader: impl Into<String>,
        file_count: u32,
        script_hashes: Vec<(String, String)>,
    ) -> Self {
        Self {
            acronym: acronym.into(),
            full_name: full_name.into(),
            compatible_version: compatible_version.into(),
            loader: loader.into(),
            file_count,
            script_hashes,
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

/// Crash generator configuration for a specific version.
///
/// Contains metadata about a crash generator (e.g., Buffout 4) including
/// its version, name, description, download URL, and optional compatible
/// game version range.
///
/// # Examples
///
/// ```rust
/// use classic_version_registry_core::CrashgenConfig;
///
/// // Simple config with just version
/// let simple = CrashgenConfig::from_version_string("1.38.1");
///
/// // Full config with all metadata
/// let full = CrashgenConfig::new(
///     "1.28.6",
///     "Buffout 4",
///     "BO4",
///     "buffout4.dll",
///     "Legacy version for OG",
///     "https://www.nexusmods.com/fallout4/mods/47359",
/// );
/// ```
#[derive(Debug, Clone)]
pub struct CrashgenConfig {
    /// Version string of the crash generator (e.g., "1.28.6", "1.38.1").
    pub version: String,
    /// Display name (e.g., "Buffout 4", "Buffout 4 NG").
    pub name: String,
    /// Short identifier/acronym (e.g., "BO4", "BO4 NG").
    pub acronym: String,
    /// DLL filename (e.g., "buffout4.dll").
    pub dll_file: String,
    /// Description of this crash generator version.
    pub description: String,
    /// Nexus Mods or other download URL.
    pub download_url: String,
    /// Optional game version range this crash generator is compatible with.
    /// If `None`, the crash generator is valid for any game version in the parent `VersionInfo`.
    pub compatible_range: Option<CompatibleRange>,
    /// When `true`, this version is valid only on exact equality and is excluded from floor
    /// computation. Use for legacy builds that remain acceptable but must not lower the floor.
    pub exact_match: bool,
}

impl CrashgenConfig {
    /// Create a new crash generator configuration.
    ///
    /// # Arguments
    ///
    /// * `version` - Version string of the crash generator
    /// * `name` - Display name
    /// * `acronym` - Short identifier (e.g., "BO4", "BO4 NG")
    /// * `dll_file` - DLL filename (e.g., "buffout4.dll")
    /// * `description` - Description of this version
    /// * `download_url` - Download URL
    #[must_use]
    pub fn new(
        version: impl Into<String>,
        name: impl Into<String>,
        acronym: impl Into<String>,
        dll_file: impl Into<String>,
        description: impl Into<String>,
        download_url: impl Into<String>,
    ) -> Self {
        Self {
            version: version.into(),
            name: name.into(),
            acronym: acronym.into(),
            dll_file: dll_file.into(),
            description: description.into(),
            download_url: download_url.into(),
            compatible_range: None,
            exact_match: false,
        }
    }

    /// Create a new crash generator configuration with a compatible range.
    ///
    /// # Arguments
    ///
    /// * `version` - Version string of the crash generator
    /// * `name` - Display name
    /// * `acronym` - Short identifier (e.g., "BO4", "BO4 NG")
    /// * `dll_file` - DLL filename (e.g., "buffout4.dll")
    /// * `description` - Description of this version
    /// * `download_url` - Download URL
    /// * `compatible_range` - Game version range this crash generator is compatible with
    #[must_use]
    pub fn with_range(
        version: impl Into<String>,
        name: impl Into<String>,
        acronym: impl Into<String>,
        dll_file: impl Into<String>,
        description: impl Into<String>,
        download_url: impl Into<String>,
        compatible_range: CompatibleRange,
    ) -> Self {
        Self {
            version: version.into(),
            name: name.into(),
            acronym: acronym.into(),
            dll_file: dll_file.into(),
            description: description.into(),
            download_url: download_url.into(),
            compatible_range: Some(compatible_range),
            exact_match: false,
        }
    }

    /// Create a `CrashgenConfig` from just a version string.
    ///
    /// Convenience factory for backward compatibility when crash generator
    /// versions are specified as simple strings in YAML.
    ///
    /// # Arguments
    ///
    /// * `version` - The crash generator version string
    #[must_use]
    pub fn from_version_string(version: impl Into<String>) -> Self {
        Self {
            version: version.into(),
            name: String::new(),
            acronym: String::new(),
            dll_file: String::new(),
            description: String::new(),
            download_url: String::new(),
            compatible_range: None,
            exact_match: false,
        }
    }

    /// Check if this crash generator is compatible with a game version.
    ///
    /// If no `compatible_range` is defined, returns `true` (compatible with any version).
    /// Otherwise, checks if the game version falls within the compatible range.
    ///
    /// # Arguments
    ///
    /// * `game_version` - The game version to check compatibility with
    ///
    /// # Returns
    ///
    /// `true` if compatible, `false` otherwise.
    #[must_use]
    pub fn is_compatible_with(&self, game_version: &GameVersion) -> bool {
        match &self.compatible_range {
            Some(range) => range.contains(game_version),
            None => true,
        }
    }
}

/// Complete version information for a game version.
///
/// Contains all metadata about a specific game version, including
/// version number, display name, Address Library configuration,
/// script extender configuration, crash generator versions, and matching settings.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_version_registry_core::{VersionInfo, CrashgenConfig};
///
/// // Access crash generator versions
/// let registry = classic_version_registry_core::get_version_registry();
/// if let Some(og) = registry.get_by_id("FO4_OG") {
///     for crashgen in &og.crashgen_versions {
///         println!("{}: {}", crashgen.name, crashgen.version);
///     }
/// }
/// ```
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
    /// My Documents subfolder name (e.g., "Fallout4", "Fallout4VR").
    pub docs_name: String,
    /// Steam application ID (e.g., 377160, 611660).
    pub steam_id: u32,
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
    /// SHA-256 hash of the game executable for this version.
    /// Used for validating game executable integrity.
    pub exe_hash: Option<String>,
    /// Crash generator versions compatible with this game version.
    ///
    /// Each `CrashgenConfig` contains version, name, description, download_url,
    /// and optional compatible_range. For example, FO4_OG supports both
    /// Buffout 4 (1.28.6), Buffout 4 NG (1.38.1), and Addictol (1.3.0),
    /// while FO4_NG supports Buffout 4 NG (1.38.1) and Addictol (1.3.0).
    /// An empty Vec means no crash
    /// generator is configured yet.
    pub crashgen_versions: Vec<CrashgenConfig>,
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

    /// Get crash generator versions as simple version strings.
    ///
    /// Provides backward-compatible access to just the version strings
    /// of the crash generators, without the additional metadata.
    ///
    /// # Returns
    ///
    /// A vector of version strings from `crashgen_versions`.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use classic_version_registry_core::get_version_registry;
    ///
    /// let registry = get_version_registry();
    /// if let Some(og) = registry.get_by_id("FO4_OG") {
    ///     let versions = og.get_crashgen_version_strings();
    ///     // Returns ["1.28.6", "1.38.1", "1.3.0"]
    /// }
    /// ```
    #[must_use]
    pub fn get_crashgen_version_strings(&self) -> Vec<&str> {
        self.crashgen_versions
            .iter()
            .map(|c| c.version.as_str())
            .collect()
    }

    /// Get a specific `CrashgenConfig` by its version string.
    ///
    /// # Arguments
    ///
    /// * `crashgen_version` - The crash generator version to look up
    ///
    /// # Returns
    ///
    /// The `CrashgenConfig` with the matching version, or `None` if not found.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use classic_version_registry_core::get_version_registry;
    ///
    /// let registry = get_version_registry();
    /// if let Some(og) = registry.get_by_id("FO4_OG") {
    ///     if let Some(config) = og.get_crashgen_for_version("1.28.6") {
    ///         println!("Name: {}", config.name);
    ///     }
    /// }
    /// ```
    #[must_use]
    pub fn get_crashgen_for_version(&self, crashgen_version: &str) -> Option<&CrashgenConfig> {
        self.crashgen_versions
            .iter()
            .find(|c| c.version == crashgen_version)
    }

    /// Get crash generators compatible with a specific game version.
    ///
    /// Filters `crashgen_versions` by their `compatible_range`. If a crash generator
    /// has no `compatible_range` defined, it is considered compatible with all
    /// game versions.
    ///
    /// # Arguments
    ///
    /// * `game_version` - The game version to check compatibility with.
    ///   If `None`, uses this `VersionInfo`'s version.
    ///
    /// # Returns
    ///
    /// A vector of references to `CrashgenConfig` objects compatible with the game version.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use classic_version_registry_core::get_version_registry;
    ///
    /// let registry = get_version_registry();
    /// if let Some(og) = registry.get_by_id("FO4_OG") {
    ///     let compatible = og.get_compatible_crashgens(None);
    ///     for config in compatible {
    ///         println!("{}: {}", config.name, config.version);
    ///     }
    /// }
    /// ```
    #[must_use]
    pub fn get_compatible_crashgens(
        &self,
        game_version: Option<&GameVersion>,
    ) -> Vec<&CrashgenConfig> {
        let check_version = game_version.unwrap_or(&self.version);
        self.crashgen_versions
            .iter()
            .filter(|c| c.is_compatible_with(check_version))
            .collect()
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
#[path = "models_tests.rs"]
mod tests;
