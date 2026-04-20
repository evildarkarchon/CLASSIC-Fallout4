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

    /// Current game identifier.
    ///
    /// Stores the current game name (e.g., "Fallout4", "Skyrim").
    /// Defaults to "Fallout4" if not set.
    pub const GAME: &'static str = "gamevars_game";

    /// Current game version for Fallout 4.
    ///
    /// Stores the detected or manually selected Fallout 4 version variant
    /// as a `Fallout4Version` enum value (Original, NextGen, or Vr).
    ///
    /// This replaces the legacy VR mode toggle with a unified version system
    /// that treats VR as a version variant alongside OG and NG versions.
    ///
    /// # Examples
    ///
    /// ```rust,ignore
    /// use classic_registry_core::{register, get, Keys};
    /// use classic_version_registry_core::Fallout4Version;
    ///
    /// // Register a version
    /// register(Keys::GAME_VERSION, Fallout4Version::Vr);
    ///
    /// // Retrieve the version
    /// let version: Option<Fallout4Version> = get(Keys::GAME_VERSION);
    /// assert_eq!(version, Some(Fallout4Version::Vr));
    /// ```
    pub const GAME_VERSION: &'static str = "gamevars_version";

    /// Whether the game version was auto-detected.
    ///
    /// Boolean flag indicating whether the current [`Keys::GAME_VERSION`] was
    /// automatically detected from the game installation (true) or
    /// manually selected by the user (false).
    ///
    /// This helps the UI know whether to show the detected version or
    /// preserve a user's manual override.
    pub const VERSION_AUTO_DETECTED: &'static str = "gamevars_version_auto";

    /// Local application directory.
    ///
    /// Stores the path to the local application directory, typically the
    /// current working directory or installation location.
    pub const LOCAL_DIR: &'static str = "local_dir";

    /// Application directory override for settings resolution.
    ///
    /// When set, `classic-config-core` uses this directory instead of
    /// `current_exe().parent()` to anchor settings and data files.
    ///
    /// Binding layers (Python, Node) auto-register this to `current_dir()`
    /// at module init so settings resolve relative to the working directory
    /// rather than the interpreter's install directory.
    pub const APP_DIR: &'static str = "app_dir";

    /// Prerelease flag.
    ///
    /// Boolean flag indicating whether this is a prerelease version.
    pub const IS_PRERELEASE: &'static str = "is_prerelease";

    /// XSE validation status.
    ///
    /// Boolean flag indicating whether XSE (Script Extender) validation passed.
    pub const XSE_VALID: &'static str = "xse_validation_passed";

    /// Detected XSE version.
    ///
    /// Stores the detected version string of the Script Extender.
    pub const XSE_VERSION: &'static str = "xse_detected_version";

    /// ENB binaries presence flag.
    ///
    /// Boolean flag indicating whether ENB binaries were detected.
    pub const ENB_PRESENT: &'static str = "enb_binaries_present";

    /// Detected game executable version.
    ///
    /// Stores the version string of the game executable.
    pub const GAME_VERSION_DETECTED: &'static str = "game_exe_version";
}

#[cfg(test)]
#[path = "keys_tests.rs"]
mod tests;
