//! Application constants and enumerations for CLASSIC.
//!
//! This crate provides zero-cost compile-time constants and type-safe enumerations
//! used throughout CLASSIC. It has no dependencies on PyO3 and can be used by
//! pure Rust applications or through Python bindings.
//!
//! ## Features
//!
//! - **Version Constants**: Fallout 4 and F4SE version identifiers
//! - **YAML File Enumeration**: Type-safe YAML configuration file identifiers
//! - **Game Identifiers**: Supported game name constants
//! - **Settings Constants**: Application-wide settings and ignore lists
//! - **VersionRegistry Integration**: All version metadata comes from VersionRegistry
//!
//! ## Design Philosophy
//!
//! The `Fallout4Version` enum uses the `classic-version-registry-core` crate
//! as the **single source of truth** for all version metadata. This ensures
//! consistency between Rust and Python implementations.
//!
//! **MANDATORY**: All code that needs version information MUST use the
//! VersionRegistry subsystem. Direct hardcoding of version-specific values
//! is prohibited.
//!
//! ## Examples
//!
//! ```rust,no_run
//! use classic_constants_core::{YamlFile, GameId, Fallout4Version};
//! use semver::Version;
//!
//! // Use Fallout4Version with VersionRegistry
//! let version = Fallout4Version::Vr;
//! assert!(version.is_vr());
//! // Version metadata comes from VersionRegistry:
//! let info = version.get_version_info();
//! assert!(info.is_some());
//!
//! // Use YAML file enumeration
//! let settings_file = YamlFile::Settings;
//! assert_eq!(settings_file.as_str(), "Settings");
//!
//! // Use game identifiers
//! let game = GameId::Fallout4;
//! assert_eq!(game.as_str(), "Fallout4");
//! ```

use semver::Version;
use serde::{Deserialize, Serialize};

// Re-export VersionRegistry types for convenience
pub use classic_version_registry_core::{
    MatchConfidence, MatchResult, VersionInfo, VersionRegistry, VersionRegistryError,
    get_version_registry,
};

// ============================================================================
// Version Constants
// ============================================================================

/// Null/invalid version identifier (0.0.0).
pub const NULL_VERSION: Version = Version::new(0, 0, 0);

// ============================================================================
// Fallout 4 Version Variants
// ============================================================================

/// Fallout 4-specific version variants.
///
/// This enum represents the four main version variants of Fallout 4:
/// - Original (OG): Pre-Next-Gen update version (1.10.163)
/// - NextGen (NG): Next-Gen update version (1.10.984)
/// - AnniversaryEdition (AE): Anniversary Edition version (1.11.137+)
/// - Vr: Virtual Reality version (1.2.72)
///
/// Unlike `GameId` which treats VR as a separate game, this enum treats
/// VR as a version variant of Fallout 4, allowing unified handling of
/// game-specific logic with version-aware configuration.
///
/// **MANDATORY**: All version metadata is sourced from the [`VersionRegistry`].
/// Methods like [`exe_name()`](Self::exe_name), [`docs_folder_name()`](Self::docs_folder_name),
/// etc. delegate to the VersionRegistry for their data. Use [`get_version_info()`](Self::get_version_info)
/// for direct access to the full [`VersionInfo`] from the registry.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_constants_core::Fallout4Version;
///
/// let version = Fallout4Version::Vr;
/// assert!(version.is_vr());
///
/// // Get full VersionInfo from the registry (RECOMMENDED)
/// if let Some(info) = version.get_version_info() {
///     println!("Display name: {}", info.display_name);
///     if let Some(addr_lib) = &info.address_library {
///         println!("Address Library: {}", addr_lib.filename);
///     }
/// }
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
pub enum Fallout4Version {
    /// Original pre-Next-Gen version (1.10.163).
    ///
    /// This is the final version before the 2024 Next-Gen update.
    /// Uses standard F4SE (0.6.23) and non-VR Address Library.
    #[default]
    Original,

    /// Next-Gen update version (1.10.984).
    ///
    /// Released in 2024 with updated engine features and improved
    /// performance. Uses updated F4SE (0.7.2) and non-VR Address Library.
    NextGen,

    /// Anniversary Edition version (1.11.137+).
    ///
    /// Released as an active development branch with ongoing updates.
    /// Version range starts at 1.11.137 and continues to evolve.
    /// Uses updated F4SE (0.7.3+) and non-VR Address Library.
    AnniversaryEdition,

    /// Virtual Reality version (1.2.72).
    ///
    /// Standalone VR release with different executable and configuration.
    /// Uses F4SEVR and VR-specific Address Library.
    Vr,
}

impl Fallout4Version {
    /// Get the VersionRegistry ID for this version variant.
    ///
    /// This is used to look up the full [`VersionInfo`] from the registry.
    ///
    /// # Returns
    ///
    /// The registry ID string (e.g., "FO4_OG", "FO4_NG", "FO4_VR").
    #[must_use]
    pub const fn registry_id(&self) -> &'static str {
        match self {
            Self::Original => "FO4_OG",
            Self::NextGen => "FO4_NG",
            Self::AnniversaryEdition => "FO4_AE",
            Self::Vr => "FO4_VR",
        }
    }

    /// Get the full [`VersionInfo`] from the [`VersionRegistry`].
    ///
    /// This is the **primary method** for accessing version metadata.
    /// All other accessor methods delegate to the `VersionInfo` returned here.
    ///
    /// # Returns
    ///
    /// The `VersionInfo` for this version, or `None` if not found in the registry.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_constants_core::Fallout4Version;
    ///
    /// let version = Fallout4Version::Original;
    /// if let Some(info) = version.get_version_info() {
    ///     println!("Version: {}", info.version);
    ///     println!("Display Name: {}", info.display_name);
    ///     if let Some(xse) = &info.xse {
    ///         println!("XSE: {}", xse.acronym);
    ///     }
    /// }
    /// ```
    #[must_use]
    pub fn get_version_info(&self) -> Option<&'static VersionInfo> {
        get_version_registry().get_by_id(self.registry_id())
    }

    /// Returns `true` if this is the VR version.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::Fallout4Version;
    ///
    /// assert!(!Fallout4Version::Original.is_vr());
    /// assert!(!Fallout4Version::NextGen.is_vr());
    /// assert!(Fallout4Version::Vr.is_vr());
    /// ```
    #[must_use]
    pub const fn is_vr(&self) -> bool {
        matches!(self, Self::Vr)
    }

    /// Returns `true` if this is a standard (non-VR) version.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::Fallout4Version;
    ///
    /// assert!(Fallout4Version::Original.is_standard());
    /// assert!(Fallout4Version::NextGen.is_standard());
    /// assert!(!Fallout4Version::Vr.is_standard());
    /// ```
    #[must_use]
    pub const fn is_standard(&self) -> bool {
        !self.is_vr()
    }

    /// Get the game executable name for this version.
    ///
    /// The value is derived from the VR status rather than hardcoded,
    /// following the pattern used by the VersionRegistry.
    ///
    /// # Returns
    ///
    /// The executable filename for this version variant.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::Fallout4Version;
    ///
    /// assert_eq!(Fallout4Version::Original.exe_name(), "Fallout4.exe");
    /// assert_eq!(Fallout4Version::NextGen.exe_name(), "Fallout4.exe");
    /// assert_eq!(Fallout4Version::Vr.exe_name(), "Fallout4VR.exe");
    /// ```
    #[must_use]
    pub const fn exe_name(&self) -> &'static str {
        // VR-based derivation matches VersionRegistry behavior
        if self.is_vr() {
            "Fallout4VR.exe"
        } else {
            "Fallout4.exe"
        }
    }

    /// Get the Documents folder name for this version.
    ///
    /// This is the subfolder under "My Games" where saves, INIs, and logs are stored.
    /// Derived from VR status to match VersionRegistry behavior.
    ///
    /// # Returns
    ///
    /// The Documents folder name for this version variant.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::Fallout4Version;
    ///
    /// assert_eq!(Fallout4Version::Original.docs_folder_name(), "Fallout4");
    /// assert_eq!(Fallout4Version::NextGen.docs_folder_name(), "Fallout4");
    /// assert_eq!(Fallout4Version::Vr.docs_folder_name(), "Fallout4VR");
    /// ```
    #[must_use]
    pub const fn docs_folder_name(&self) -> &'static str {
        // VR-based derivation matches VersionRegistry behavior
        if self.is_vr() {
            "Fallout4VR"
        } else {
            "Fallout4"
        }
    }

    /// Get the Steam App ID for this version.
    ///
    /// # Returns
    ///
    /// The Steam App ID for this version variant.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::Fallout4Version;
    ///
    /// assert_eq!(Fallout4Version::Original.steam_app_id(), 377160);
    /// assert_eq!(Fallout4Version::NextGen.steam_app_id(), 377160);
    /// assert_eq!(Fallout4Version::Vr.steam_app_id(), 611660);
    /// ```
    #[must_use]
    pub const fn steam_app_id(&self) -> u32 {
        // VR-based derivation
        if self.is_vr() { 611660 } else { 377160 }
    }

    /// Get the game version from the VersionRegistry.
    ///
    /// This returns the 4-component [`GameVersion`](classic_version_registry_core::GameVersion)
    /// from the VersionRegistry. For semver [`Version`] compatibility, use
    /// [`version_semver()`](Self::version_semver) instead.
    ///
    /// # Returns
    ///
    /// The game version from the registry, or a default if not found.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_constants_core::Fallout4Version;
    ///
    /// let version = Fallout4Version::Original;
    /// let game_ver = version.game_version();
    /// println!("Version: {}", game_ver);
    /// ```
    #[must_use]
    pub fn game_version(&self) -> classic_version_registry_core::GameVersion {
        self.get_version_info()
            .map(|info| info.version)
            .unwrap_or_else(|| classic_version_registry_core::GameVersion::new(0, 0, 0, 0))
    }

    /// Get the semver [`Version`] for this variant.
    ///
    /// Converts the 4-component game version to a 3-component semver Version
    /// for compatibility with existing code that uses semver.
    ///
    /// # Returns
    ///
    /// The semantic version corresponding to this variant.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_constants_core::Fallout4Version;
    ///
    /// let version = Fallout4Version::Original;
    /// let semver = version.version_semver();
    /// println!("Semver: {}", semver);
    /// ```
    #[must_use]
    pub fn version_semver(&self) -> Version {
        let gv = self.game_version();
        Version::new(
            u64::from(gv.major),
            u64::from(gv.minor),
            u64::from(gv.patch),
        )
    }

    /// Get the YAML configuration section name for this version.
    ///
    /// This determines which section of the game YAML file to read
    /// configuration from (e.g., `Game_Info` vs `GameVR_Info`).
    /// Derived from VR status to match VersionRegistry behavior.
    ///
    /// # Returns
    ///
    /// The YAML section name for this version variant.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::Fallout4Version;
    ///
    /// assert_eq!(Fallout4Version::Original.config_section(), "Game_Info");
    /// assert_eq!(Fallout4Version::NextGen.config_section(), "Game_Info");
    /// assert_eq!(Fallout4Version::Vr.config_section(), "GameVR_Info");
    /// ```
    #[must_use]
    pub const fn config_section(&self) -> &'static str {
        if self.is_vr() {
            "GameVR_Info"
        } else {
            "Game_Info"
        }
    }

    /// Get the configuration suffix for registry lookups.
    ///
    /// This provides backward compatibility with the legacy VR suffix system.
    /// Returns `""` for standard versions and `"VR"` for VR version.
    ///
    /// # Returns
    ///
    /// The legacy VR suffix for configuration lookups.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::Fallout4Version;
    ///
    /// assert_eq!(Fallout4Version::Original.config_suffix(), "");
    /// assert_eq!(Fallout4Version::NextGen.config_suffix(), "");
    /// assert_eq!(Fallout4Version::Vr.config_suffix(), "VR");
    /// ```
    #[must_use]
    pub const fn config_suffix(&self) -> &'static str {
        if self.is_vr() { "VR" } else { "" }
    }

    /// Get the XSE acronym for this version from the VersionRegistry.
    ///
    /// # Returns
    ///
    /// The Script Extender acronym (e.g., "F4SE" or "F4SEVR").
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_constants_core::Fallout4Version;
    ///
    /// let acronym = Fallout4Version::Original.xse_acronym();
    /// assert_eq!(acronym, "F4SE");
    /// ```
    #[must_use]
    pub fn xse_acronym(&self) -> &'static str {
        self.get_version_info()
            .and_then(|info| info.xse.as_ref())
            .map(|xse| {
                // Return static str by matching known acronyms
                // This maintains backward compatibility with const fn expectations
                match xse.acronym.as_str() {
                    "F4SEVR" => "F4SEVR",
                    _ => "F4SE",
                }
            })
            .unwrap_or(if self.is_vr() { "F4SEVR" } else { "F4SE" })
    }

    /// Get the XSE acronym as a String from the VersionRegistry.
    ///
    /// Unlike [`xse_acronym()`](Self::xse_acronym), this returns the actual
    /// value from the registry without mapping to static strings.
    ///
    /// # Returns
    ///
    /// The Script Extender acronym from the registry.
    #[must_use]
    pub fn xse_acronym_string(&self) -> String {
        self.get_version_info()
            .and_then(|info| info.xse.as_ref())
            .map(|xse| xse.acronym.clone())
            .unwrap_or_else(|| {
                if self.is_vr() {
                    "F4SEVR".to_string()
                } else {
                    "F4SE".to_string()
                }
            })
    }

    /// Get a human-readable display name from the VersionRegistry.
    ///
    /// # Returns
    ///
    /// A user-friendly version name from the registry.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_constants_core::Fallout4Version;
    ///
    /// let name = Fallout4Version::Original.display_name();
    /// // Returns the display name from VersionRegistry
    /// ```
    #[must_use]
    pub fn display_name(&self) -> &'static str {
        self.get_version_info()
            .map(|info| {
                // Return static str by matching known names
                match info.short_name.as_str() {
                    "OG" => "Fallout 4 Original",
                    "NG" => "Fallout 4 Next-Gen",
                    "AE" => "Fallout 4 Anniversary Edition",
                    "VR" => "Fallout 4 VR",
                    _ => "Unknown",
                }
            })
            .unwrap_or("Unknown")
    }

    /// Get the display name as a String from the VersionRegistry.
    ///
    /// Unlike [`display_name()`](Self::display_name), this returns the actual
    /// `display_name` field from the registry.
    ///
    /// # Returns
    ///
    /// The display name from the registry.
    #[must_use]
    pub fn display_name_string(&self) -> String {
        self.get_version_info()
            .map(|info| info.display_name.clone())
            .unwrap_or_else(|| "Unknown".to_string())
    }

    /// Get the short name from the VersionRegistry.
    ///
    /// # Returns
    ///
    /// The short name (e.g., "OG", "NG", "VR").
    #[must_use]
    pub fn short_name(&self) -> &'static str {
        match self {
            Self::Original => "OG",
            Self::NextGen => "NG",
            Self::AnniversaryEdition => "AE",
            Self::Vr => "VR",
        }
    }

    /// Get the string representation for serialization and settings.
    ///
    /// # Returns
    ///
    /// A short identifier string for this version.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::Fallout4Version;
    ///
    /// assert_eq!(Fallout4Version::Original.as_str(), "Original");
    /// assert_eq!(Fallout4Version::NextGen.as_str(), "NextGen");
    /// assert_eq!(Fallout4Version::Vr.as_str(), "VR");
    /// ```
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Original => "Original",
            Self::NextGen => "NextGen",
            Self::AnniversaryEdition => "AnniversaryEdition",
            Self::Vr => "VR",
        }
    }

    /// Get all Fallout 4 version variants as an array.
    ///
    /// # Returns
    ///
    /// Array of all `Fallout4Version` variants.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::Fallout4Version;
    ///
    /// let all_versions = Fallout4Version::all();
    /// assert_eq!(all_versions.len(), 4);
    /// ```
    #[must_use]
    pub const fn all() -> [Self; 4] {
        [
            Self::Original,
            Self::NextGen,
            Self::AnniversaryEdition,
            Self::Vr,
        ]
    }

    /// Get the Address Library configuration from the VersionRegistry.
    ///
    /// # Returns
    ///
    /// The Address Library configuration, or `None` if not available.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_constants_core::Fallout4Version;
    ///
    /// let version = Fallout4Version::Original;
    /// if let Some(addr_lib) = version.address_library() {
    ///     println!("Filename: {}", addr_lib.filename);
    ///     println!("Format: {:?}", addr_lib.format);
    /// }
    /// ```
    #[must_use]
    pub fn address_library(
        &self,
    ) -> Option<&'static classic_version_registry_core::AddressLibraryConfig> {
        self.get_version_info()
            .and_then(|info| info.address_library.as_ref())
    }

    /// Get the XSE configuration from the VersionRegistry.
    ///
    /// # Returns
    ///
    /// The XSE configuration, or `None` if not available.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_constants_core::Fallout4Version;
    ///
    /// let version = Fallout4Version::Original;
    /// if let Some(xse) = version.xse_config() {
    ///     println!("Acronym: {}", xse.acronym);
    ///     println!("Compatible version: {}", xse.compatible_version);
    /// }
    /// ```
    #[must_use]
    pub fn xse_config(&self) -> Option<&'static classic_version_registry_core::XseConfig> {
        self.get_version_info().and_then(|info| info.xse.as_ref())
    }
}

impl std::fmt::Display for Fallout4Version {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.display_name())
    }
}

impl std::str::FromStr for Fallout4Version {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let lower = s.to_lowercase();
        match lower.as_str() {
            "original" | "og" | "1.10.163" => Ok(Self::Original),
            "nextgen" | "next-gen" | "ng" | "1.10.984" => Ok(Self::NextGen),
            "anniversaryedition" | "anniversary-edition" | "anniversary" | "ae" => {
                Ok(Self::AnniversaryEdition)
            }
            "vr" | "1.2.72" => Ok(Self::Vr),
            "auto" => Ok(Self::default()), // Auto defaults to Original
            // Try to match version numbers starting with 1.11 as Anniversary Edition
            _ if lower.starts_with("1.11.") => Ok(Self::AnniversaryEdition),
            _ => Err(format!("Unknown Fallout 4 version: {}", s)),
        }
    }
}

// ============================================================================
// YAML File Enumeration
// ============================================================================

/// Enumeration for YAML configuration files used by CLASSIC.
///
/// Each variant corresponds to a specific YAML file in the application's
/// configuration hierarchy. This provides type-safe access to configuration
/// file identifiers.
///
/// # Examples
///
/// ```rust
/// use classic_constants_core::YamlFile;
///
/// let settings = YamlFile::Settings;
/// assert_eq!(settings.as_str(), "Settings");
/// assert_eq!(settings.description(), "CLASSIC Settings.yaml");
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum YamlFile {
    /// CLASSIC Data/databases/CLASSIC Main.yaml
    Main,
    /// CLASSIC Settings.yaml
    Settings,
    /// CLASSIC Ignore.yaml
    Ignore,
    /// CLASSIC Data/databases/CLASSIC {Game}.yaml
    Game,
    /// CLASSIC Data/CLASSIC {Game} Local.yaml
    GameLocal,
    /// tests/test_settings.yaml (for testing only)
    Test,
    /// User config dir/CLASSIC-Fallout4/cache.yaml (persistent cache for uvx)
    Cache,
}

impl YamlFile {
    /// Get the string representation of the YAML file variant.
    ///
    /// # Returns
    ///
    /// The variant name as a string slice.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::YamlFile;
    ///
    /// assert_eq!(YamlFile::Main.as_str(), "Main");
    /// assert_eq!(YamlFile::Settings.as_str(), "Settings");
    /// ```
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Main => "Main",
            Self::Settings => "Settings",
            Self::Ignore => "Ignore",
            Self::Game => "Game",
            Self::GameLocal => "GameLocal",
            Self::Test => "Test",
            Self::Cache => "Cache",
        }
    }

    /// Get a human-readable description of the YAML file.
    ///
    /// # Returns
    ///
    /// A description string including the typical file path.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::YamlFile;
    ///
    /// let desc = YamlFile::Main.description();
    /// assert!(desc.contains("CLASSIC Main.yaml"));
    /// ```
    #[must_use]
    pub const fn description(&self) -> &'static str {
        match self {
            Self::Main => "CLASSIC Data/databases/CLASSIC Main.yaml",
            Self::Settings => "CLASSIC Settings.yaml",
            Self::Ignore => "CLASSIC Ignore.yaml",
            Self::Game => "CLASSIC Data/databases/CLASSIC {Game}.yaml",
            Self::GameLocal => "CLASSIC Data/CLASSIC {Game} Local.yaml",
            Self::Test => "tests/test_settings.yaml",
            Self::Cache => "User config dir/CLASSIC-Fallout4/cache.yaml",
        }
    }

    /// Get all YAML file variants as an array.
    ///
    /// # Returns
    ///
    /// Array of all `YamlFile` variants.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::YamlFile;
    ///
    /// let all_files = YamlFile::all();
    /// assert_eq!(all_files.len(), 7);
    /// ```
    #[must_use]
    pub const fn all() -> [Self; 7] {
        [
            Self::Main,
            Self::Settings,
            Self::Ignore,
            Self::Game,
            Self::GameLocal,
            Self::Test,
            Self::Cache,
        ]
    }
}

impl std::fmt::Display for YamlFile {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

// ============================================================================
// Game Identifiers
// ============================================================================

/// Enumeration of supported game identifiers.
///
/// Each variant corresponds to a Bethesda game supported by CLASSIC.
/// The names match the game's main ESM or EXE file name for consistency.
///
/// # Examples
///
/// ```rust
/// use classic_constants_core::GameId;
///
/// let game = GameId::Fallout4;
/// assert_eq!(game.as_str(), "Fallout4");
/// assert_eq!(game.exe_name(), "Fallout4.exe");
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GameId {
    /// Fallout 4 (base game)
    Fallout4,
    /// Fallout 4 VR
    Fallout4VR,
    /// Skyrim Special Edition
    Skyrim,
    /// Starfield
    Starfield,
}

impl GameId {
    /// Get the string representation of the game identifier.
    ///
    /// # Returns
    ///
    /// The game name as a string slice.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::GameId;
    ///
    /// assert_eq!(GameId::Fallout4.as_str(), "Fallout4");
    /// assert_eq!(GameId::Fallout4VR.as_str(), "Fallout4VR");
    /// ```
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Fallout4 => "Fallout4",
            Self::Fallout4VR => "Fallout4VR",
            Self::Skyrim => "Skyrim",
            Self::Starfield => "Starfield",
        }
    }

    /// Get the executable name for this game.
    ///
    /// # Returns
    ///
    /// The game executable filename (e.g., "Fallout4.exe").
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::GameId;
    ///
    /// assert_eq!(GameId::Fallout4.exe_name(), "Fallout4.exe");
    /// ```
    #[must_use]
    pub const fn exe_name(&self) -> &'static str {
        match self {
            Self::Fallout4 => "Fallout4.exe",
            Self::Fallout4VR => "Fallout4VR.exe",
            Self::Skyrim => "SkyrimSE.exe",
            Self::Starfield => "Starfield.exe",
        }
    }

    /// Check if this is a VR game.
    ///
    /// # Returns
    ///
    /// `true` if this is a VR variant, `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::GameId;
    ///
    /// assert!(!GameId::Fallout4.is_vr());
    /// assert!(GameId::Fallout4VR.is_vr());
    /// ```
    #[must_use]
    pub const fn is_vr(&self) -> bool {
        matches!(self, Self::Fallout4VR)
    }

    /// Get all game identifiers as an array.
    ///
    /// # Returns
    ///
    /// Array of all `GameId` variants.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_constants_core::GameId;
    ///
    /// let all_games = GameId::all();
    /// assert_eq!(all_games.len(), 4);
    /// ```
    #[must_use]
    pub const fn all() -> [Self; 4] {
        [
            Self::Fallout4,
            Self::Fallout4VR,
            Self::Skyrim,
            Self::Starfield,
        ]
    }
}

impl std::fmt::Display for GameId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl std::str::FromStr for GameId {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "Fallout4" => Ok(Self::Fallout4),
            "Fallout4VR" => Ok(Self::Fallout4VR),
            "Skyrim" => Ok(Self::Skyrim),
            "Starfield" => Ok(Self::Starfield),
            _ => Err(format!("Unknown game identifier: {}", s)),
        }
    }
}

// ============================================================================
// Settings Constants
// ============================================================================

/// Settings keys that should not have "None" values.
///
/// These settings must have valid values and cannot be set to None/null.
/// This set is used for validation when loading and saving settings.
///
/// # Examples
///
/// ```rust
/// use classic_constants_core::SETTINGS_IGNORE_NONE;
///
/// assert!(SETTINGS_IGNORE_NONE.contains(&"SCAN Custom Path"));
/// assert!(SETTINGS_IGNORE_NONE.contains(&"Root_Folder_Game"));
/// ```
pub const SETTINGS_IGNORE_NONE: &[&str] = &[
    "SCAN Custom Path",
    "MODS Folder Path",
    "INI Folder Path",
    "Root_Folder_Game",
    "Root_Folder_Docs",
];

/// Check if a settings key should not allow None values.
///
/// # Arguments
///
/// * `key` - The settings key to check
///
/// # Returns
///
/// `true` if the key must not be None, `false` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_constants_core::must_not_be_none;
///
/// assert!(must_not_be_none("SCAN Custom Path"));
/// assert!(!must_not_be_none("Some Other Setting"));
/// ```
#[must_use]
pub fn must_not_be_none(key: &str) -> bool {
    SETTINGS_IGNORE_NONE.contains(&key)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_null_version() {
        assert_eq!(NULL_VERSION, Version::new(0, 0, 0));
    }

    #[test]
    fn test_yaml_file_as_str() {
        assert_eq!(YamlFile::Main.as_str(), "Main");
        assert_eq!(YamlFile::Settings.as_str(), "Settings");
        assert_eq!(YamlFile::Ignore.as_str(), "Ignore");
        assert_eq!(YamlFile::Game.as_str(), "Game");
        assert_eq!(YamlFile::GameLocal.as_str(), "GameLocal");
        assert_eq!(YamlFile::Test.as_str(), "Test");
        assert_eq!(YamlFile::Cache.as_str(), "Cache");
    }

    #[test]
    fn test_yaml_file_description() {
        let desc = YamlFile::Main.description();
        assert!(desc.contains("CLASSIC Main.yaml"));

        let desc = YamlFile::Settings.description();
        assert!(desc.contains("CLASSIC Settings.yaml"));
    }

    #[test]
    fn test_yaml_file_all() {
        let all = YamlFile::all();
        assert_eq!(all.len(), 7);
        assert!(all.contains(&YamlFile::Main));
        assert!(all.contains(&YamlFile::Settings));
    }

    #[test]
    fn test_yaml_file_display() {
        assert_eq!(format!("{}", YamlFile::Main), "Main");
        assert_eq!(format!("{}", YamlFile::Settings), "Settings");
    }

    #[test]
    fn test_game_id_as_str() {
        assert_eq!(GameId::Fallout4.as_str(), "Fallout4");
        assert_eq!(GameId::Fallout4VR.as_str(), "Fallout4VR");
        assert_eq!(GameId::Skyrim.as_str(), "Skyrim");
        assert_eq!(GameId::Starfield.as_str(), "Starfield");
    }

    #[test]
    fn test_game_id_exe_name() {
        assert_eq!(GameId::Fallout4.exe_name(), "Fallout4.exe");
        assert_eq!(GameId::Fallout4VR.exe_name(), "Fallout4VR.exe");
        assert_eq!(GameId::Skyrim.exe_name(), "SkyrimSE.exe");
        assert_eq!(GameId::Starfield.exe_name(), "Starfield.exe");
    }

    #[test]
    fn test_game_id_is_vr() {
        assert!(!GameId::Fallout4.is_vr());
        assert!(GameId::Fallout4VR.is_vr());
        assert!(!GameId::Skyrim.is_vr());
        assert!(!GameId::Starfield.is_vr());
    }

    #[test]
    fn test_game_id_all() {
        let all = GameId::all();
        assert_eq!(all.len(), 4);
        assert!(all.contains(&GameId::Fallout4));
        assert!(all.contains(&GameId::Fallout4VR));
    }

    #[test]
    fn test_game_id_from_str() {
        assert_eq!("Fallout4".parse::<GameId>().unwrap(), GameId::Fallout4);
        assert_eq!("Fallout4VR".parse::<GameId>().unwrap(), GameId::Fallout4VR);
        assert_eq!("Skyrim".parse::<GameId>().unwrap(), GameId::Skyrim);
        assert_eq!("Starfield".parse::<GameId>().unwrap(), GameId::Starfield);
        assert!("UnknownGame".parse::<GameId>().is_err());
    }

    #[test]
    fn test_game_id_display() {
        assert_eq!(format!("{}", GameId::Fallout4), "Fallout4");
        assert_eq!(format!("{}", GameId::Fallout4VR), "Fallout4VR");
    }

    #[test]
    fn test_settings_ignore_none() {
        assert_eq!(SETTINGS_IGNORE_NONE.len(), 5);
        assert!(SETTINGS_IGNORE_NONE.contains(&"SCAN Custom Path"));
        assert!(SETTINGS_IGNORE_NONE.contains(&"Root_Folder_Game"));
    }

    #[test]
    fn test_must_not_be_none() {
        assert!(must_not_be_none("SCAN Custom Path"));
        assert!(must_not_be_none("Root_Folder_Game"));
        assert!(!must_not_be_none("Some Other Setting"));
    }

    #[test]
    fn test_yaml_file_serialization() {
        let yaml = YamlFile::Settings;
        let json = serde_json::to_string(&yaml).unwrap();
        let deserialized: YamlFile = serde_json::from_str(&json).unwrap();
        assert_eq!(yaml, deserialized);
    }

    #[test]
    fn test_game_id_serialization() {
        let game = GameId::Fallout4;
        let json = serde_json::to_string(&game).unwrap();
        let deserialized: GameId = serde_json::from_str(&json).unwrap();
        assert_eq!(game, deserialized);
    }

    // ========================================================================
    // Fallout4Version Tests
    // ========================================================================

    #[test]
    fn test_fallout4_version_is_vr() {
        assert!(!Fallout4Version::Original.is_vr());
        assert!(!Fallout4Version::NextGen.is_vr());
        assert!(Fallout4Version::Vr.is_vr());
    }

    #[test]
    fn test_fallout4_version_is_standard() {
        assert!(Fallout4Version::Original.is_standard());
        assert!(Fallout4Version::NextGen.is_standard());
        assert!(!Fallout4Version::Vr.is_standard());
    }

    #[test]
    fn test_fallout4_version_exe_name() {
        assert_eq!(Fallout4Version::Original.exe_name(), "Fallout4.exe");
        assert_eq!(Fallout4Version::NextGen.exe_name(), "Fallout4.exe");
        assert_eq!(Fallout4Version::Vr.exe_name(), "Fallout4VR.exe");
    }

    #[test]
    fn test_fallout4_version_docs_folder_name() {
        assert_eq!(Fallout4Version::Original.docs_folder_name(), "Fallout4");
        assert_eq!(Fallout4Version::NextGen.docs_folder_name(), "Fallout4");
        assert_eq!(Fallout4Version::Vr.docs_folder_name(), "Fallout4VR");
    }

    #[test]
    fn test_fallout4_version_steam_app_id() {
        assert_eq!(Fallout4Version::Original.steam_app_id(), 377160);
        assert_eq!(Fallout4Version::NextGen.steam_app_id(), 377160);
        assert_eq!(Fallout4Version::Vr.steam_app_id(), 611660);
    }

    #[test]
    fn test_fallout4_version_version_semver() {
        // Versions now use VersionRegistry, but fall back to defaults
        // The default registry provides all three versions
        let og_version = Fallout4Version::Original.version_semver();
        let ng_version = Fallout4Version::NextGen.version_semver();
        let vr_version = Fallout4Version::Vr.version_semver();

        // Check that versions are reasonable (major version 1 for all)
        assert_eq!(og_version.major, 1);
        assert_eq!(ng_version.major, 1);
        assert_eq!(vr_version.major, 1);
    }

    #[test]
    fn test_fallout4_version_config_section() {
        assert_eq!(Fallout4Version::Original.config_section(), "Game_Info");
        assert_eq!(Fallout4Version::NextGen.config_section(), "Game_Info");
        assert_eq!(Fallout4Version::Vr.config_section(), "GameVR_Info");
    }

    #[test]
    fn test_fallout4_version_config_suffix() {
        assert_eq!(Fallout4Version::Original.config_suffix(), "");
        assert_eq!(Fallout4Version::NextGen.config_suffix(), "");
        assert_eq!(Fallout4Version::Vr.config_suffix(), "VR");
    }

    #[test]
    fn test_fallout4_version_xse_acronym() {
        assert_eq!(Fallout4Version::Original.xse_acronym(), "F4SE");
        assert_eq!(Fallout4Version::NextGen.xse_acronym(), "F4SE");
        assert_eq!(Fallout4Version::Vr.xse_acronym(), "F4SEVR");
    }

    #[test]
    fn test_fallout4_version_display_name() {
        // display_name() now returns names from VersionRegistry
        assert_eq!(
            Fallout4Version::Original.display_name(),
            "Fallout 4 Original"
        );
        assert_eq!(
            Fallout4Version::NextGen.display_name(),
            "Fallout 4 Next-Gen"
        );
        assert_eq!(Fallout4Version::Vr.display_name(), "Fallout 4 VR");
    }

    #[test]
    fn test_fallout4_version_as_str() {
        assert_eq!(Fallout4Version::Original.as_str(), "Original");
        assert_eq!(Fallout4Version::NextGen.as_str(), "NextGen");
        assert_eq!(Fallout4Version::Vr.as_str(), "VR");
    }

    #[test]
    fn test_fallout4_version_all() {
        let all = Fallout4Version::all();
        assert_eq!(all.len(), 4);
        assert!(all.contains(&Fallout4Version::Original));
        assert!(all.contains(&Fallout4Version::NextGen));
        assert!(all.contains(&Fallout4Version::AnniversaryEdition));
        assert!(all.contains(&Fallout4Version::Vr));
    }

    #[test]
    fn test_fallout4_version_default() {
        let default: Fallout4Version = Default::default();
        assert_eq!(default, Fallout4Version::Original);
    }

    #[test]
    fn test_fallout4_version_display() {
        // Display trait uses display_name() which now comes from VersionRegistry
        assert_eq!(
            format!("{}", Fallout4Version::Original),
            "Fallout 4 Original"
        );
        assert_eq!(
            format!("{}", Fallout4Version::NextGen),
            "Fallout 4 Next-Gen"
        );
        assert_eq!(format!("{}", Fallout4Version::Vr), "Fallout 4 VR");
    }

    #[test]
    fn test_fallout4_version_from_str() {
        // Standard names
        assert_eq!(
            "Original".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Original
        );
        assert_eq!(
            "NextGen".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::NextGen
        );
        assert_eq!(
            "AnniversaryEdition".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "VR".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Vr
        );

        // Alternate names (case-insensitive)
        assert_eq!(
            "og".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Original
        );
        assert_eq!(
            "NG".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::NextGen
        );
        assert_eq!(
            "next-gen".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::NextGen
        );
        assert_eq!(
            "ae".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "anniversary".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "anniversary-edition".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "vr".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Vr
        );

        // Version numbers
        assert_eq!(
            "1.10.163".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Original
        );
        assert_eq!(
            "1.10.984".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::NextGen
        );
        // Anniversary Edition version range (1.11.137 to 1.11.191+)
        assert_eq!(
            "1.11.137".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "1.11.191".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        // Future versions in 1.11.x should also match
        assert_eq!(
            "1.11.999".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::AnniversaryEdition
        );
        assert_eq!(
            "1.2.72".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Vr
        );

        // Auto defaults to Original
        assert_eq!(
            "auto".parse::<Fallout4Version>().unwrap(),
            Fallout4Version::Original
        );

        // Invalid
        assert!("unknown".parse::<Fallout4Version>().is_err());
    }

    #[test]
    fn test_fallout4_version_serialization() {
        let version = Fallout4Version::Vr;
        let json = serde_json::to_string(&version).unwrap();
        let deserialized: Fallout4Version = serde_json::from_str(&json).unwrap();
        assert_eq!(version, deserialized);
    }
}
