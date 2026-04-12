//! ENB (ENBoost/ENBSeries) detection module.
//!
//! This module provides functionality to detect ENB installation by checking
//! for the presence of ENB binaries and configuration files.

use std::path::{Path, PathBuf};
use thiserror::Error;

/// Error types for ENB detection operations.
#[derive(Debug, Error)]
pub enum EnbError {
    /// IO error during file operations
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    /// Path is invalid or not found
    #[error("Invalid path: {0}")]
    InvalidPath(String),
}

/// Result of ENB detection check.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EnbResult {
    /// ENB is fully installed (d3d11.dll + d3dcompiler_46e.dll present)
    Present,
    /// Only some ENB files found (partial installation)
    Partial,
    /// No ENB files detected
    NotInstalled,
}

/// Result of ENB config check.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EnbConfigResult {
    /// enbseries.ini exists and is readable
    Valid,
    /// enbseries.ini not found
    NotFound,
    /// enbseries.ini exists but cannot be read
    Unreadable,
}

/// Combined ENB validation result.
#[derive(Debug, Clone)]
pub struct EnbValidationResult {
    /// Whether ENB binaries are present
    pub binaries: EnbResult,
    /// Whether ENB config is valid
    pub config: EnbConfigResult,
}

impl EnbValidationResult {
    /// Check if ENB is present (binaries exist).
    pub fn is_present(&self) -> bool {
        matches!(self.binaries, EnbResult::Present | EnbResult::Partial)
    }

    /// Check if ENB is fully configured (binaries + config).
    pub fn is_fully_configured(&self) -> bool {
        self.binaries == EnbResult::Present && self.config == EnbConfigResult::Valid
    }
}

/// ENB detection checker.
pub struct EnbChecker {
    game_path: PathBuf,
}

impl EnbChecker {
    /// Create a new ENB checker for the specified game directory.
    ///
    /// # Arguments
    ///
    /// * `game_path` - Path to the game installation directory
    pub fn new(game_path: impl AsRef<Path>) -> Self {
        Self {
            game_path: game_path.as_ref().to_path_buf(),
        }
    }

    /// Check if ENB binaries exist.
    ///
    /// ENB requires:
    /// - d3d11.dll (main ENB binary)
    /// - d3dcompiler_46e.dll (optional, for ENB effects)
    pub fn check_binaries(&self) -> EnbResult {
        let d3d11 = self.game_path.join("d3d11.dll");
        let d3dcompiler = self.game_path.join("d3dcompiler_46e.dll");

        let d3d11_exists = d3d11.exists();
        let d3dcompiler_exists = d3dcompiler.exists();

        if d3d11_exists && d3dcompiler_exists {
            EnbResult::Present
        } else if d3d11_exists || d3dcompiler_exists {
            EnbResult::Partial
        } else {
            EnbResult::NotInstalled
        }
    }

    /// Check if ENB config exists and is readable.
    pub fn check_config(&self) -> EnbConfigResult {
        let config_path = self.game_path.join("enbseries.ini");

        if !config_path.exists() {
            return EnbConfigResult::NotFound;
        }

        // Try to read the file to verify it's accessible
        match std::fs::metadata(&config_path) {
            Ok(meta) if meta.is_file() => EnbConfigResult::Valid,
            _ => EnbConfigResult::Unreadable,
        }
    }

    /// Perform combined validation.
    pub fn validate(&self) -> EnbValidationResult {
        EnbValidationResult {
            binaries: self.check_binaries(),
            config: self.check_config(),
        }
    }

    /// Format a user-friendly message based on validation result.
    pub fn format_message(&self, result: &EnbValidationResult) -> String {
        match result.binaries {
            EnbResult::Present => {
                if result.config == EnbConfigResult::Valid {
                    "ENB is installed and configured.\n".to_string()
                } else {
                    "ENB binaries found but enbseries.ini is missing or unreadable.\n".to_string()
                }
            }
            EnbResult::Partial => {
                "Partial ENB installation detected. Some ENB files may be missing.\n".to_string()
            }
            EnbResult::NotInstalled => "ENB is not installed.\n".to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn create_test_game_dir(files: &[&str]) -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        for file in files {
            let file_path = temp_dir.path().join(file);
            fs::write(file_path, b"test content").unwrap();
        }
        temp_dir
    }

    #[test]
    fn test_enb_not_installed() {
        let temp_dir = create_test_game_dir(&[]);
        let checker = EnbChecker::new(temp_dir.path());

        assert_eq!(checker.check_binaries(), EnbResult::NotInstalled);
        assert_eq!(checker.check_config(), EnbConfigResult::NotFound);
    }

    #[test]
    fn test_enb_present() {
        let temp_dir = create_test_game_dir(&["d3d11.dll", "d3dcompiler_46e.dll", "enbseries.ini"]);
        let checker = EnbChecker::new(temp_dir.path());

        assert_eq!(checker.check_binaries(), EnbResult::Present);
        assert_eq!(checker.check_config(), EnbConfigResult::Valid);

        let result = checker.validate();
        assert!(result.is_present());
        assert!(result.is_fully_configured());
    }

    #[test]
    fn test_enb_partial() {
        let temp_dir = create_test_game_dir(&["d3d11.dll"]); // Missing d3dcompiler
        let checker = EnbChecker::new(temp_dir.path());

        assert_eq!(checker.check_binaries(), EnbResult::Partial);
    }

    #[test]
    fn test_enb_partial_is_present() {
        let temp_dir = create_test_game_dir(&["d3d11.dll"]);
        let checker = EnbChecker::new(temp_dir.path());

        let result = checker.validate();
        assert!(result.is_present()); // Partial is still "present"
        assert!(!result.is_fully_configured()); // But not fully configured
    }

    #[test]
    fn test_enb_present_no_config() {
        let temp_dir = create_test_game_dir(&["d3d11.dll", "d3dcompiler_46e.dll"]);
        let checker = EnbChecker::new(temp_dir.path());

        let result = checker.validate();
        assert!(result.is_present());
        assert!(!result.is_fully_configured()); // Missing config
        assert_eq!(result.config, EnbConfigResult::NotFound);
    }

    #[test]
    fn test_format_message_present() {
        let temp_dir = create_test_game_dir(&["d3d11.dll", "d3dcompiler_46e.dll", "enbseries.ini"]);
        let checker = EnbChecker::new(temp_dir.path());

        let result = checker.validate();
        let message = checker.format_message(&result);
        assert!(message.contains("ENB is installed and configured"));
    }

    #[test]
    fn test_format_message_not_installed() {
        let temp_dir = create_test_game_dir(&[]);
        let checker = EnbChecker::new(temp_dir.path());

        let result = checker.validate();
        let message = checker.format_message(&result);
        assert!(message.contains("ENB is not installed"));
    }

    #[test]
    fn test_format_message_partial() {
        let temp_dir = create_test_game_dir(&["d3d11.dll"]);
        let checker = EnbChecker::new(temp_dir.path());

        let result = checker.validate();
        let message = checker.format_message(&result);
        assert!(message.contains("Partial ENB installation"));
    }
}
