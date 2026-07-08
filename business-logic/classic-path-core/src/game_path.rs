//! Game path detection and management.
//!
//! This module provides multi-strategy game path detection for Bethesda games:
//! 1. **Cache Check**: Load cached path from YAML settings
//! 2. **Registry Query**: Query Windows registry for installation path
//! 3. **XSE Log Parsing**: Parse script extender logs for plugin directory
//! 4. **User Input**: Prompt user to select game directory
//!
//! The module supports:
//! - Game executable validation
//! - XSE loader detection
//! - Platform-specific path generation
//! - Integration with YAML settings cache

use crate::error::{GamePathError, GamePathResult};
use crate::validator::validate_required_files;
use std::fs;
use std::path::{Path, PathBuf};

#[cfg(target_os = "windows")]
use crate::platform::windows::query_game_registry;

/// Game path finder with multi-strategy detection.
///
/// This struct encapsulates the logic for finding game installation paths
/// using multiple detection strategies, falling back to the next strategy
/// if the previous one fails.
///
/// # Strategy Order
///
/// 1. **Cache**: Check YAML settings for cached path
/// 2. **Registry**: Query Windows registry (Windows only)
/// 3. **XSE Log**: Parse script extender logs
/// 4. **User Input**: Prompt for manual selection
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::GamePathFinder;
///
/// let finder = GamePathFinder::new(
///     "Fallout4.exe",
///     Some("f4se_loader.exe"),
///     "Fallout4",
///     false, // not VR
/// );
///
/// let game_path = finder.find_game_path(None, None)?;
/// println!("Found game at: {}", game_path.display());
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub struct GamePathFinder {
    /// Name of the game executable (e.g., "Fallout4.exe")
    game_exe: String,

    /// Optional XSE loader executable (e.g., "f4se_loader.exe")
    xse_loader: Option<String>,

    /// Game name for registry queries (e.g., "Fallout4")
    #[cfg_attr(not(target_os = "windows"), allow(dead_code))]
    game_name: String,

    /// Whether this is a VR version of the game
    is_vr: bool,
}

impl GamePathFinder {
    /// Create a new GamePathFinder.
    ///
    /// # Arguments
    ///
    /// * `game_exe` - The game executable name (e.g., "Fallout4.exe")
    /// * `xse_loader` - Optional XSE loader name (e.g., "f4se_loader.exe")
    /// * `game_name` - Game name for registry queries (e.g., "Fallout4")
    /// * `is_vr` - Whether this is a VR version
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_path_core::GamePathFinder;
    ///
    /// let finder = GamePathFinder::new(
    ///     "Fallout4.exe",
    ///     Some("f4se_loader.exe"),
    ///     "Fallout4",
    ///     false,
    /// );
    /// ```
    pub fn new<S1, S2, S3>(game_exe: S1, xse_loader: Option<S2>, game_name: S3, is_vr: bool) -> Self
    where
        S1: Into<String>,
        S2: Into<String>,
        S3: Into<String>,
    {
        Self {
            game_exe: game_exe.into(),
            xse_loader: xse_loader.map(Into::into),
            game_name: game_name.into(),
            is_vr,
        }
    }

    /// Find the game installation path using multiple strategies.
    ///
    /// This method attempts to find the game path using the following strategies in order:
    /// 1. Use cached path if provided and valid
    /// 2. Query Windows registry (Windows only)
    /// 3. Parse XSE log file if path provided
    /// 4. Return error if all strategies fail
    ///
    /// # Arguments
    ///
    /// * `cached_path` - Optional cached path from YAML settings
    /// * `xse_log_path` - Optional path to XSE log file for parsing
    ///
    /// # Returns
    ///
    /// The validated game installation path, or an error if not found.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::GamePathFinder;
    /// use std::path::PathBuf;
    ///
    /// let finder = GamePathFinder::new("Fallout4.exe", None::<&str>, "Fallout4", false);
    ///
    /// // Try with cached path
    /// let cached = Some(PathBuf::from("C:\\Games\\Fallout4"));
    /// let path = finder.find_game_path(cached.as_deref(), None)?;
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn find_game_path(
        &self,
        cached_path: Option<&Path>,
        xse_log_path: Option<&Path>,
    ) -> GamePathResult<PathBuf> {
        // Strategy 1: Try cached path
        if let Some(path) = cached_path
            && let Ok(()) = self.validate_game_path(path)
        {
            return Ok(path.to_path_buf());
        }

        // Strategy 2: Try registry (Windows only)
        #[cfg(target_os = "windows")]
        {
            if let Ok(path) = self.find_via_registry() {
                return Ok(path);
            }
        }

        // Strategy 3: Try XSE log parsing
        if let Some(log_path) = xse_log_path
            && let Ok(path) = self.find_via_xse_log(log_path)
        {
            return Ok(path);
        }

        // All strategies failed
        Err(GamePathError::NotFound)
    }

    /// Find game path via Windows registry.
    ///
    /// Queries the Windows registry for Bethesda game installation paths.
    /// Supports both regular and GOG versions of games.
    ///
    /// # Returns
    ///
    /// The game path from registry, or an error if not found.
    #[cfg(target_os = "windows")]
    fn find_via_registry(&self) -> GamePathResult<PathBuf> {
        let vr_suffix = if self.is_vr { " VR" } else { "" };
        let try_gog = self.game_name == "Fallout4";

        let path = query_game_registry(&self.game_name, vr_suffix, try_gog)?;

        // Validate the path before returning
        self.validate_game_path(&path)?;
        Ok(path)
    }

    /// Find game path by parsing XSE log file.
    ///
    /// Parses script extender (XSE) log files to extract the plugin directory,
    /// which indicates the game installation path.
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the XSE log file (e.g., "f4se.log")
    ///
    /// # Returns
    ///
    /// The game path extracted from the log, or an error if parsing failed.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::GamePathFinder;
    /// use std::path::Path;
    ///
    /// let finder = GamePathFinder::new("Fallout4.exe", None::<&str>, "Fallout4", false);
    /// let log_path = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4\\F4SE\\f4se.log");
    ///
    /// let game_path = finder.find_via_xse_log(log_path)?;
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn find_via_xse_log(&self, log_path: &Path) -> GamePathResult<PathBuf> {
        let game_path = parse_xse_log(log_path)?;

        // Validate the extracted path
        self.validate_game_path(&game_path)?;
        Ok(game_path)
    }

    /// Validate that a path is a valid game installation directory.
    ///
    /// Checks that:
    /// 1. The path exists and is a directory
    /// 2. The game executable exists
    /// 3. The XSE loader exists (if configured)
    ///
    /// # Arguments
    ///
    /// * `path` - The path to validate
    ///
    /// # Returns
    ///
    /// `Ok(())` if valid, or a `GamePathError` if validation fails.
    pub fn validate_game_path(&self, path: &Path) -> GamePathResult<()> {
        // Build list of required files
        let mut required_files = vec![self.game_exe.clone()];
        if let Some(ref loader) = self.xse_loader {
            required_files.push(loader.clone());
        }

        // Validate directory and required files
        validate_required_files(path, &required_files)
            .map_err(|e| GamePathError::ValidationFailed(e.to_string()))?;

        Ok(())
    }

    /// Get the name of the game executable.
    ///
    /// # Returns
    ///
    /// The game executable name (e.g., "Fallout4.exe").
    pub fn game_exe(&self) -> &str {
        &self.game_exe
    }

    /// Get the name of the XSE loader executable.
    ///
    /// # Returns
    ///
    /// The XSE loader name if configured, or `None`.
    pub fn xse_loader(&self) -> Option<&str> {
        self.xse_loader.as_deref()
    }

    /// Check if this is a VR version of the game.
    ///
    /// # Returns
    ///
    /// `true` if this is a VR version, `false` otherwise.
    pub fn is_vr(&self) -> bool {
        self.is_vr
    }
}

/// Parse XSE log file to extract game installation path.
///
/// This function parses script extender (XSE) log files looking for the
/// "plugin directory = " line, which contains the game installation path.
///
/// # Arguments
///
/// * `log_path` - Path to the XSE log file
///
/// # Returns
///
/// The game installation path, or an error if parsing failed.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::parse_xse_log;
/// use std::path::Path;
///
/// let log_path = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4\\F4SE\\f4se.log");
/// let game_path = parse_xse_log(log_path)?;
/// println!("Game installed at: {}", game_path.display());
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn parse_xse_log(log_path: &Path) -> GamePathResult<PathBuf> {
    if !log_path.exists() {
        return Err(GamePathError::XseLogNotFound(log_path.to_path_buf()));
    }

    let content = fs::read_to_string(log_path).map_err(|e| GamePathError::XseLogReadError {
        path: log_path.to_path_buf(),
        source: e,
    })?;

    // Look for the plugin directory line
    // Format: "plugin directory = C:\Games\Fallout4\Data\F4SE\Plugins\"
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("plugin directory = ") || trimmed.starts_with("plugin directory=") {
            // Extract the path after the equals sign
            let path_str = if let Some(pos) = trimmed.find('=') {
                trimmed[pos + 1..].trim()
            } else {
                continue;
            };

            // Remove quotes if present
            let path_str = path_str.trim_matches('"');

            // The path typically ends with "Data\F4SE\Plugins" or similar
            // We need to go up to the game root
            let mut path = PathBuf::from(path_str);

            // Go up from Plugins -> F4SE -> Data -> Game Root
            for _ in 0..3 {
                if !path.pop() {
                    return Err(GamePathError::XseLogParseError(
                        "Could not extract game root from plugin directory path".to_string(),
                    ));
                }
            }

            return Ok(path);
        }
    }

    Err(GamePathError::XseLogParseError(
        "Could not find 'plugin directory' line in XSE log".to_string(),
    ))
}

#[cfg(test)]
#[path = "game_path_tests.rs"]
mod tests;
