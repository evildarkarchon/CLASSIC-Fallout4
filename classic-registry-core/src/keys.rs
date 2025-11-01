//! Predefined registry keys for common CLASSIC components.
//!
//! This module provides a set of well-known registry keys used throughout
//! the CLASSIC application for storing singleton instances and configuration.

/// Predefined registry keys.
///
/// These constants define the standard keys used for storing common
/// singletons and configuration values in the global registry.
///
/// # Examples
///
/// ```rust
/// use classic_registry_core::{Keys, register, get};
///
/// register(Keys::GAME, "Fallout4".to_string());
/// let game: Option<String> = get(Keys::GAME);
/// ```
pub struct Keys;

impl Keys {
    /// YAML settings cache instance.
    ///
    /// Stores the global `YamlSettingsCache` singleton for efficient
    /// configuration file access.
    pub const YAML_CACHE: &'static str = "yaml_cache";

    /// Manual documents GUI widget reference.
    ///
    /// Stores a reference to the GUI widget for manual document path selection.
    pub const MANUAL_DOCS_GUI: &'static str = "manual_docs_gui";

    /// Game path GUI widget reference.
    ///
    /// Stores a reference to the GUI widget for game installation path selection.
    pub const GAME_PATH_GUI: &'static str = "game_path_gui";

    /// Game installation path.
    ///
    /// Stores the detected or configured game installation directory path.
    pub const GAME_PATH: &'static str = "game_path";

    /// Documents folder path.
    ///
    /// Stores the path to the game's documents folder (e.g., for save games,
    /// configuration files, logs).
    pub const DOCS_PATH: &'static str = "docs_path";

    /// GUI mode flag.
    ///
    /// Boolean flag indicating whether the application is running in GUI mode
    /// (true) or CLI mode (false). Affects message routing and progress display.
    pub const IS_GUI_MODE: &'static str = "is_gui_mode";

    /// File open function reference.
    ///
    /// Stores a reference to the function used for opening files with proper
    /// encoding handling.
    pub const OPEN_FILE_FUNC: &'static str = "open_file_with_encoding";

    /// VR game variant identifier.
    ///
    /// Stores the VR variant of the game (e.g., "SkyrimVR", "Fallout4VR").
    pub const VR: &'static str = "gamevars_vr";

    /// Current game identifier.
    ///
    /// Stores the current game name (e.g., "Fallout4", "Skyrim").
    /// Defaults to "Fallout4" if not set.
    pub const GAME: &'static str = "gamevars_game";

    /// Local application directory.
    ///
    /// Stores the path to the local application directory, typically the
    /// current working directory or installation location.
    pub const LOCAL_DIR: &'static str = "local_dir";

    /// Prerelease flag.
    ///
    /// Boolean flag indicating whether this is a prerelease version.
    pub const IS_PRERELEASE: &'static str = "is_prerelease";
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_keys_are_unique() {
        // Ensure all keys are distinct
        let keys = vec![
            Keys::YAML_CACHE,
            Keys::MANUAL_DOCS_GUI,
            Keys::GAME_PATH_GUI,
            Keys::GAME_PATH,
            Keys::DOCS_PATH,
            Keys::IS_GUI_MODE,
            Keys::OPEN_FILE_FUNC,
            Keys::VR,
            Keys::GAME,
            Keys::LOCAL_DIR,
            Keys::IS_PRERELEASE,
        ];

        let mut unique_keys = keys.clone();
        unique_keys.sort();
        unique_keys.dedup();

        assert_eq!(keys.len(), unique_keys.len(), "Keys must be unique");
    }

    #[test]
    fn test_key_values() {
        assert_eq!(Keys::YAML_CACHE, "yaml_cache");
        assert_eq!(Keys::GAME, "gamevars_game");
        assert_eq!(Keys::IS_GUI_MODE, "is_gui_mode");
        assert_eq!(Keys::LOCAL_DIR, "local_dir");
    }
}
