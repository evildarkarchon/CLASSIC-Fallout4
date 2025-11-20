//! Game integrity checking module
//!
//! This module provides functionality for validating game installations including:
//! - Executable version checking via SHA256 hash comparison
//! - Installation location validation (Program Files detection)
//! - Steam INI detection (indicates outdated version)

use std::path::{Path, PathBuf};
use thiserror::Error;

/// Errors that can occur during integrity checking
#[derive(Debug, Error)]
pub enum IntegrityError {
    /// I/O error
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    /// File not found
    #[error("File not found: {0}")]
    FileNotFound(PathBuf),

    /// Hash calculation failed
    #[error("Failed to calculate hash: {0}")]
    HashError(String),
}

/// Configuration for game integrity checking
#[derive(Debug, Clone)]
pub struct IntegrityConfig {
    /// Path to the game executable
    pub game_exe_path: PathBuf,

    /// SHA256 hash of the old game version
    pub exe_hash_old: String,

    /// SHA256 hash of the new game version
    pub exe_hash_new: String,

    /// Path to Steam INI (indicates outdated installation if present)
    pub steam_ini_path: Option<PathBuf>,

    /// Game root name (e.g., "Fallout 4", "Skyrim")
    pub root_name: String,

    /// Warning message for Program Files installation
    pub root_warn: Option<String>,
}

impl IntegrityConfig {
    /// Create a new integrity configuration
    ///
    /// # Arguments
    ///
    /// * `game_exe_path` - Path to the game executable
    /// * `exe_hash_old` - SHA256 hash of the old version
    /// * `exe_hash_new` - SHA256 hash of the new version
    /// * `root_name` - Game root name
    ///
    /// # Returns
    ///
    /// A new `IntegrityConfig` instance
    pub fn new(
        game_exe_path: PathBuf,
        exe_hash_old: String,
        exe_hash_new: String,
        root_name: String,
    ) -> Self {
        Self {
            game_exe_path,
            exe_hash_old,
            exe_hash_new,
            steam_ini_path: None,
            root_name,
            root_warn: None,
        }
    }

    /// Set the Steam INI path
    pub fn with_steam_ini(mut self, steam_ini_path: PathBuf) -> Self {
        self.steam_ini_path = Some(steam_ini_path);
        self
    }

    /// Set the root warning message
    pub fn with_root_warn(mut self, root_warn: String) -> Self {
        self.root_warn = Some(root_warn);
        self
    }
}

impl Default for IntegrityConfig {
    fn default() -> Self {
        Self::new(PathBuf::new(), String::new(), String::new(), String::new())
    }
}

/// Result of an integrity check
#[derive(Debug, Clone, PartialEq)]
pub struct IntegrityCheckResult {
    /// Whether the check passed
    pub is_valid: bool,

    /// Message describing the check result
    pub message: String,

    /// Type of check performed
    pub check_type: CheckType,
}

/// Type of integrity check
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CheckType {
    /// Executable version check
    ExecutableVersion,

    /// Installation location check
    InstallationLocation,
}

impl IntegrityCheckResult {
    /// Create a new check result
    pub fn new(is_valid: bool, message: String, check_type: CheckType) -> Self {
        Self {
            is_valid,
            message,
            check_type,
        }
    }
}

/// Game integrity checker
pub struct GameIntegrityChecker {
    /// Configuration for integrity checking
    config: IntegrityConfig,
}

impl GameIntegrityChecker {
    /// Create a new game integrity checker
    ///
    /// # Arguments
    ///
    /// * `config` - Integrity checking configuration
    ///
    /// # Returns
    ///
    /// A new `GameIntegrityChecker` instance
    pub fn new(config: IntegrityConfig) -> Self {
        Self { config }
    }

    /// Check if game executable is up to date
    ///
    /// This function:
    /// 1. Calculates the SHA256 hash of the game executable
    /// 2. Compares it against known old and new versions
    /// 3. Checks for Steam INI presence (indicates outdated version)
    ///
    /// # Returns
    ///
    /// Result containing check status and message
    ///
    /// # Errors
    ///
    /// Returns error if:
    /// - Executable file doesn't exist
    /// - Failed to read the executable
    /// - Hash calculation fails
    pub fn check_executable_version(&self) -> Result<IntegrityCheckResult, IntegrityError> {
        // Check if executable exists
        if !self.config.game_exe_path.exists() {
            return Ok(IntegrityCheckResult::new(
                false,
                "Game executable not found".to_string(),
                CheckType::ExecutableVersion,
            ));
        }

        // Calculate SHA256 hash of the executable
        let local_hash = calculate_sha256_file(&self.config.game_exe_path)?;

        // Check if hash matches known versions
        let is_valid_version =
            local_hash == self.config.exe_hash_old || local_hash == self.config.exe_hash_new;

        // Check for Steam INI (indicates outdated installation)
        let steam_ini_exists = self
            .config
            .steam_ini_path
            .as_ref()
            .map(|p| p.exists())
            .unwrap_or(false);

        let (is_valid, message) = if is_valid_version && !steam_ini_exists {
            (
                true,
                format!(
                    "✔️ You have the latest version of {}! \n-----\n",
                    self.config.root_name
                ),
            )
        } else {
            let icon = if steam_ini_exists { "\u{1f480}" } else { "❌" };
            (
                false,
                format!(
                    "{} CAUTION : YOUR {} GAME / EXE VERSION IS OUT OF DATE \n-----\n",
                    icon, self.config.root_name
                ),
            )
        };

        Ok(IntegrityCheckResult::new(
            is_valid,
            message,
            CheckType::ExecutableVersion,
        ))
    }

    /// Verify game is installed in recommended location
    ///
    /// Checks if the game is installed outside of Program Files,
    /// which is recommended to avoid permission issues.
    ///
    /// # Returns
    ///
    /// Result containing check status and message
    pub fn check_installation_location(&self) -> Result<IntegrityCheckResult, IntegrityError> {
        // Check if executable exists
        if !self.config.game_exe_path.exists() {
            return Ok(IntegrityCheckResult::new(
                false,
                String::new(),
                CheckType::InstallationLocation,
            ));
        }

        // Check if path contains "Program Files"
        let path_str = self.config.game_exe_path.to_string_lossy();
        let in_program_files = path_str.contains("Program Files");

        let (is_valid, message) = if !in_program_files {
            (
                true,
                format!(
                    "✔️ Your {} game files are installed outside of the Program Files folder! \n-----\n",
                    self.config.root_name
                ),
            )
        } else {
            (false, self.config.root_warn.clone().unwrap_or_default())
        };

        Ok(IntegrityCheckResult::new(
            is_valid,
            message,
            CheckType::InstallationLocation,
        ))
    }

    /// Run all integrity checks and return combined results
    ///
    /// Performs the following checks:
    /// 1. Game executable version validation
    /// 2. Installation location verification
    ///
    /// # Returns
    ///
    /// Vector of all check results
    ///
    /// # Errors
    ///
    /// Returns error if any check fails
    pub fn run_all_checks(&self) -> Result<Vec<IntegrityCheckResult>, IntegrityError> {
        let mut results = Vec::new();

        // Check game executable version
        results.push(self.check_executable_version()?);

        // Check installation location
        results.push(self.check_installation_location()?);

        Ok(results)
    }

    /// Run all checks and return combined message string
    ///
    /// This is a convenience method that matches the Python API.
    ///
    /// # Returns
    ///
    /// Combined message string from all checks
    ///
    /// # Errors
    ///
    /// Returns error if any check fails
    pub fn run_full_check(&self) -> Result<String, IntegrityError> {
        let results = self.run_all_checks()?;

        let messages: Vec<String> = results
            .into_iter()
            .filter(|r| !r.message.is_empty())
            .map(|r| r.message)
            .collect();

        Ok(messages.join(""))
    }

    /// Get the configuration
    pub fn config(&self) -> &IntegrityConfig {
        &self.config
    }
}

/// Calculate SHA256 hash of a file
///
/// This is a convenience function that wraps file I/O and hash calculation.
///
/// # Arguments
///
/// * `path` - Path to the file to hash
///
/// # Returns
///
/// SHA256 hash as a lowercase hex string
///
/// # Errors
///
/// Returns error if:
/// - File doesn't exist
/// - Failed to read file
fn calculate_sha256_file(path: &Path) -> Result<String, IntegrityError> {
    use sha2::{Digest, Sha256};
    use std::fs::File;
    use std::io::Read;

    if !path.exists() {
        return Err(IntegrityError::FileNotFound(path.to_path_buf()));
    }

    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 8192];

    loop {
        let bytes_read = file.read(&mut buffer)?;
        if bytes_read == 0 {
            break;
        }
        hasher.update(&buffer[..bytes_read]);
    }

    let result = hasher.finalize();
    Ok(format!("{:x}", result))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_integrity_config_creation() {
        let config = IntegrityConfig::new(
            PathBuf::from("/path/to/game.exe"),
            "old_hash".to_string(),
            "new_hash".to_string(),
            "Test Game".to_string(),
        );

        assert_eq!(config.game_exe_path, PathBuf::from("/path/to/game.exe"));
        assert_eq!(config.exe_hash_old, "old_hash");
        assert_eq!(config.exe_hash_new, "new_hash");
        assert_eq!(config.root_name, "Test Game");
        assert!(config.steam_ini_path.is_none());
        assert!(config.root_warn.is_none());
    }

    #[test]
    fn test_integrity_config_builders() {
        let config = IntegrityConfig::new(
            PathBuf::from("/path/to/game.exe"),
            "old_hash".to_string(),
            "new_hash".to_string(),
            "Test Game".to_string(),
        )
        .with_steam_ini(PathBuf::from("/path/to/steam.ini"))
        .with_root_warn("Warning message".to_string());

        assert_eq!(
            config.steam_ini_path,
            Some(PathBuf::from("/path/to/steam.ini"))
        );
        assert_eq!(config.root_warn, Some("Warning message".to_string()));
    }

    #[test]
    fn test_calculate_sha256_file() {
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "Test content").unwrap();
        temp_file.flush().unwrap();

        let hash = calculate_sha256_file(temp_file.path()).unwrap();

        // SHA256 of "Test content\n" (with newline)
        assert!(!hash.is_empty());
        assert_eq!(hash.len(), 64); // SHA256 produces 64 hex characters
    }

    #[test]
    fn test_calculate_sha256_nonexistent_file() {
        let result = calculate_sha256_file(Path::new("/nonexistent/file.exe"));
        assert!(result.is_err());
        assert!(matches!(result, Err(IntegrityError::FileNotFound(_))));
    }

    #[test]
    fn test_check_installation_location() {
        // Create a temporary file to simulate game executable
        let temp_file = NamedTempFile::new().unwrap();
        let temp_path = temp_file.path().to_path_buf();

        let config = IntegrityConfig::new(
            temp_path,
            "old_hash".to_string(),
            "new_hash".to_string(),
            "Test Game".to_string(),
        );

        let checker = GameIntegrityChecker::new(config);
        let result = checker.check_installation_location().unwrap();

        // Temporary file should not be in Program Files
        assert!(result.is_valid);
        assert!(
            result
                .message
                .contains("outside of the Program Files folder")
        );
    }

    #[test]
    fn test_check_installation_location_nonexistent() {
        let config = IntegrityConfig::new(
            PathBuf::from("/nonexistent/game.exe"),
            "old_hash".to_string(),
            "new_hash".to_string(),
            "Test Game".to_string(),
        );

        let checker = GameIntegrityChecker::new(config);
        let result = checker.check_installation_location().unwrap();

        assert!(!result.is_valid);
        assert!(result.message.is_empty());
    }

    #[test]
    fn test_integrity_check_result() {
        let result = IntegrityCheckResult::new(
            true,
            "Test message".to_string(),
            CheckType::ExecutableVersion,
        );

        assert!(result.is_valid);
        assert_eq!(result.message, "Test message");
        assert_eq!(result.check_type, CheckType::ExecutableVersion);
    }
}
