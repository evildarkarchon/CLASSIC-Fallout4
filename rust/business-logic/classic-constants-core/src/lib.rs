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
//!
//! ## Design Philosophy
//!
//! All constants are defined as `const` or `static` for zero runtime overhead.
//! Enums are simple value types without complex behavior - they serve as
//! type-safe identifiers.
//!
//! ## Examples
//!
//! ```rust
//! use classic_constants_core::{YamlFile, GameId, FALLOUT4_OG_VERSION};
//! use semver::Version;
//!
//! // Use version constants
//! let og_version = FALLOUT4_OG_VERSION;
//! assert_eq!(og_version.to_string(), "1.10.163");
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

// ============================================================================
// Version Constants
// ============================================================================

/// Null/invalid version identifier (0.0.0).
pub const NULL_VERSION: Version = Version::new(0, 0, 0);

/// Fallout 4 Original/OG version (1.10.163.0).
///
/// This is the final pre-Next-Gen update version.
pub const FALLOUT4_OG_VERSION: Version = Version::new(1, 10, 163);

/// Fallout 4 Next-Gen version (1.10.984.0).
///
/// This is the Next-Gen update version with updated engine features.
pub const FALLOUT4_NG_VERSION: Version = Version::new(1, 10, 984);

/// Fallout 4 VR version (1.2.72.0).
pub const FALLOUT4_VR_VERSION: Version = Version::new(1, 2, 72);

/// F4SE version for Original/OG Fallout 4 (0.6.23).
pub const F4SE_OG_VERSION: Version = Version::new(0, 6, 23);

/// F4SE version for Next-Gen Fallout 4 (0.7.2).
pub const F4SE_NG_VERSION: Version = Version::new(0, 7, 2);

/// All supported Fallout 4 game versions (OG and NG).
pub const FALLOUT4_VERSIONS: [Version; 2] = [FALLOUT4_OG_VERSION, FALLOUT4_NG_VERSION];

/// All supported F4SE versions (OG and NG).
pub const F4SE_VERSIONS: [Version; 2] = [F4SE_OG_VERSION, F4SE_NG_VERSION];

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
    fn test_version_constants() {
        assert_eq!(NULL_VERSION, Version::new(0, 0, 0));
        assert_eq!(FALLOUT4_OG_VERSION, Version::new(1, 10, 163));
        assert_eq!(FALLOUT4_NG_VERSION, Version::new(1, 10, 984));
        assert_eq!(FALLOUT4_VR_VERSION, Version::new(1, 2, 72));
        assert_eq!(F4SE_OG_VERSION, Version::new(0, 6, 23));
        assert_eq!(F4SE_NG_VERSION, Version::new(0, 7, 2));
    }

    #[test]
    fn test_version_arrays() {
        assert_eq!(FALLOUT4_VERSIONS.len(), 2);
        assert_eq!(F4SE_VERSIONS.len(), 2);
        assert!(FALLOUT4_VERSIONS.contains(&FALLOUT4_OG_VERSION));
        assert!(FALLOUT4_VERSIONS.contains(&FALLOUT4_NG_VERSION));
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
}
