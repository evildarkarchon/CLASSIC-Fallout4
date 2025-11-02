//! XSE (F4SE/SKSE) plugin validation module for Address Library checking.
//!
//! This module provides functionality to validate the correct Address Library
//! version is installed for the current game mode (VR vs non-VR). It detects
//! both correct and incorrect versions and provides user-friendly messages
//! to guide resolution of compatibility issues.

use std::path::{Path, PathBuf};
use thiserror::Error;

/// Error types for XSE plugin validation operations.
#[derive(Debug, Error)]
pub enum XseError {
    /// IO error during file operations
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    /// Path is invalid or not found
    #[error("Invalid path: {0}")]
    InvalidPath(String),

    /// Version detection failed
    #[error("Version detection failed: {0}")]
    VersionDetection(String),
}

/// Game version enum matching the Python Version constants.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameVersion {
    /// No version detected (0.0.0.0)
    Null,
    /// Original/Old Gen version (1.10.163.0)
    Original,
    /// New Gen version (1.10.984.0)
    NextGen,
    /// VR version (1.2.72.0)
    Vr,
}

impl GameVersion {
    /// Returns true if this is the null version (not detected).
    pub fn is_null(&self) -> bool {
        matches!(self, Self::Null)
    }

    /// Returns a human-readable description of this version.
    pub fn description(&self) -> &'static str {
        match self {
            Self::Null => "Not Detected",
            Self::Original => "Original (1.10.163.0)",
            Self::NextGen => "Next Gen (1.10.984.0)",
            Self::Vr => "VR (1.2.72.0)",
        }
    }
}

/// Information about an Address Library version.
#[derive(Debug, Clone)]
pub struct AddressLibInfo {
    /// Version constant
    pub version: GameVersion,
    /// Filename of the Address Library file (e.g., "version-1-10-163-0.bin")
    pub filename: String,
    /// Human-readable description (e.g., "Non-VR (Regular) version")
    pub description: String,
    /// Nexus Mods URL for download
    pub url: String,
}

impl AddressLibInfo {
    /// Create VR Address Library info.
    pub fn vr() -> Self {
        Self {
            version: GameVersion::Vr,
            filename: "version-1-2-72-0.csv".to_string(),
            description: "Virtual Reality (VR) version".to_string(),
            url: "https://www.nexusmods.com/fallout4/mods/64879?tab=files".to_string(),
        }
    }

    /// Create Original (OG) Address Library info.
    pub fn original() -> Self {
        Self {
            version: GameVersion::Original,
            filename: "version-1-10-163-0.bin".to_string(),
            description: "Non-VR (Regular) version".to_string(),
            url: "https://www.nexusmods.com/fallout4/mods/47327?tab=files".to_string(),
        }
    }

    /// Create Next Gen (NG) Address Library info.
    pub fn next_gen() -> Self {
        Self {
            version: GameVersion::NextGen,
            filename: "version-1-10-984-0.bin".to_string(),
            description: "Non-VR (Next Gen) version".to_string(),
            url: "https://www.nexusmods.com/fallout4/mods/47327?tab=files".to_string(),
        }
    }
}

/// Result of Address Library validation check.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ValidationResult {
    /// Correct Address Library version is installed
    CorrectVersion,
    /// Wrong Address Library version is installed
    WrongVersion,
    /// Address Library not found
    NotFound,
    /// Version could not be detected
    VersionNotDetected,
    /// Plugins path not found
    PluginsPathNotFound,
}

/// XSE plugin checker for validating Address Library installation.
pub struct XseChecker {
    /// Path to the plugins directory
    plugins_path: PathBuf,
    /// Whether running in VR mode
    is_vr_mode: bool,
    /// Detected game version
    game_version: GameVersion,
}

impl XseChecker {
    /// Create a new XSE checker.
    ///
    /// # Arguments
    ///
    /// * `plugins_path` - Path to the F4SE/SKSE plugins directory
    /// * `is_vr_mode` - Whether the game is running in VR mode
    /// * `game_version` - Detected game version
    ///
    /// # Errors
    ///
    /// Returns an error if the plugins path is invalid.
    pub fn new(
        plugins_path: impl AsRef<Path>,
        is_vr_mode: bool,
        game_version: GameVersion,
    ) -> Result<Self, XseError> {
        let plugins_path = plugins_path.as_ref().to_path_buf();

        if !plugins_path.exists() {
            return Err(XseError::InvalidPath(format!(
                "Plugins path does not exist: {}",
                plugins_path.display()
            )));
        }

        Ok(Self {
            plugins_path,
            is_vr_mode,
            game_version,
        })
    }

    /// Determine the correct and wrong Address Library versions based on VR mode.
    fn determine_relevant_versions(&self) -> (Vec<AddressLibInfo>, Vec<AddressLibInfo>) {
        if self.is_vr_mode {
            // VR mode: correct = VR, wrong = OG + NG
            let correct = vec![AddressLibInfo::vr()];
            let wrong = vec![AddressLibInfo::original(), AddressLibInfo::next_gen()];
            (correct, wrong)
        } else {
            // Non-VR mode: correct = OG + NG, wrong = VR
            let correct = vec![AddressLibInfo::original(), AddressLibInfo::next_gen()];
            let wrong = vec![AddressLibInfo::vr()];
            (correct, wrong)
        }
    }

    /// Check if a specific Address Library file exists.
    fn file_exists(&self, filename: &str) -> bool {
        self.plugins_path.join(filename).exists()
    }

    /// Check if any of the correct versions exist.
    fn correct_version_exists(&self) -> bool {
        let (correct_versions, _) = self.determine_relevant_versions();
        correct_versions
            .iter()
            .any(|info| self.file_exists(&info.filename))
    }

    /// Check if any of the wrong versions exist.
    fn wrong_version_exists(&self) -> bool {
        let (_, wrong_versions) = self.determine_relevant_versions();
        wrong_versions
            .iter()
            .any(|info| self.file_exists(&info.filename))
    }

    /// Get the first correct version info (for error messages).
    fn get_correct_version_info(&self) -> AddressLibInfo {
        let (correct_versions, _) = self.determine_relevant_versions();
        correct_versions[0].clone()
    }

    /// Perform the validation check.
    ///
    /// Returns a `ValidationResult` indicating the status of the Address Library installation.
    pub fn check(&self) -> ValidationResult {
        // Check if version was detected
        if self.game_version.is_null() {
            return ValidationResult::VersionNotDetected;
        }

        // Check for correct and wrong versions
        let correct_exists = self.correct_version_exists();
        let wrong_exists = self.wrong_version_exists();

        if correct_exists {
            ValidationResult::CorrectVersion
        } else if wrong_exists {
            ValidationResult::WrongVersion
        } else {
            ValidationResult::NotFound
        }
    }

    /// Format a user-friendly message based on validation result.
    ///
    /// Returns a formatted message string with appropriate emoji and instructions.
    pub fn format_message(&self, result: &ValidationResult) -> String {
        match result {
            ValidationResult::CorrectVersion => {
                "✔️ You have the correct version of the Address Library file!\n-----\n".to_string()
            }
            ValidationResult::WrongVersion => {
                let info = self.get_correct_version_info();
                format!(
                    "❌ CAUTION: You have installed the wrong version of the Address Library file!\n  \
                     Remove the current Address Library file and install the {}.\n  \
                     Link: {}\n-----\n",
                    info.description, info.url
                )
            }
            ValidationResult::NotFound => {
                let info = self.get_correct_version_info();
                format!(
                    "❓ NOTICE: Address Library file not found\n  \
                     Please install the {} for proper functionality.\n  \
                     Link: {}\n-----\n",
                    info.description, info.url
                )
            }
            ValidationResult::VersionNotDetected => {
                "❓ NOTICE : Unable to locate Address Library\n  \
                 If you have Address Library installed, please check the path in your settings.\n  \
                 If you don't have it installed, you can find it on the Nexus.\n  \
                 Link: Regular: https://www.nexusmods.com/fallout4/mods/47327?tab=files or \
                 VR: https://www.nexusmods.com/fallout4/mods/64879?tab=files\n-----\n"
                    .to_string()
            }
            ValidationResult::PluginsPathNotFound => {
                "❌ ERROR: Could not locate plugins folder path in settings\n-----\n".to_string()
            }
        }
    }

    /// Perform validation and return formatted message.
    ///
    /// This is the main entry point that combines `check()` and `format_message()`.
    pub fn validate(&self) -> String {
        let result = self.check();
        self.format_message(&result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    /// Helper to create a test plugins directory with optional files.
    fn setup_test_plugins_dir(files: &[&str]) -> TempDir {
        let temp_dir = TempDir::new().unwrap();

        for file in files {
            let file_path = temp_dir.path().join(file);
            fs::write(file_path, b"test content").unwrap();
        }

        temp_dir
    }

    #[test]
    fn test_game_version_is_null() {
        assert!(GameVersion::Null.is_null());
        assert!(!GameVersion::Original.is_null());
        assert!(!GameVersion::NextGen.is_null());
        assert!(!GameVersion::Vr.is_null());
    }

    #[test]
    fn test_address_lib_info_creation() {
        let vr_info = AddressLibInfo::vr();
        assert_eq!(vr_info.version, GameVersion::Vr);
        assert_eq!(vr_info.filename, "version-1-2-72-0.csv");

        let og_info = AddressLibInfo::original();
        assert_eq!(og_info.version, GameVersion::Original);
        assert_eq!(og_info.filename, "version-1-10-163-0.bin");

        let ng_info = AddressLibInfo::next_gen();
        assert_eq!(ng_info.version, GameVersion::NextGen);
        assert_eq!(ng_info.filename, "version-1-10-984-0.bin");
    }

    #[test]
    fn test_correct_version_vr_mode() {
        let temp_dir = setup_test_plugins_dir(&["version-1-2-72-0.csv"]);
        let checker = XseChecker::new(temp_dir.path(), true, GameVersion::Vr).unwrap();

        let result = checker.check();
        assert_eq!(result, ValidationResult::CorrectVersion);
    }

    #[test]
    fn test_correct_version_non_vr_og() {
        let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::Original).unwrap();

        let result = checker.check();
        assert_eq!(result, ValidationResult::CorrectVersion);
    }

    #[test]
    fn test_correct_version_non_vr_ng() {
        let temp_dir = setup_test_plugins_dir(&["version-1-10-984-0.bin"]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::NextGen).unwrap();

        let result = checker.check();
        assert_eq!(result, ValidationResult::CorrectVersion);
    }

    #[test]
    fn test_wrong_version_vr_has_og() {
        let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
        let checker = XseChecker::new(temp_dir.path(), true, GameVersion::Vr).unwrap();

        let result = checker.check();
        assert_eq!(result, ValidationResult::WrongVersion);
    }

    #[test]
    fn test_wrong_version_non_vr_has_vr() {
        let temp_dir = setup_test_plugins_dir(&["version-1-2-72-0.csv"]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::Original).unwrap();

        let result = checker.check();
        assert_eq!(result, ValidationResult::WrongVersion);
    }

    #[test]
    fn test_not_found() {
        let temp_dir = setup_test_plugins_dir(&[]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::Original).unwrap();

        let result = checker.check();
        assert_eq!(result, ValidationResult::NotFound);
    }

    #[test]
    fn test_version_not_detected() {
        let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::Null).unwrap();

        let result = checker.check();
        assert_eq!(result, ValidationResult::VersionNotDetected);
    }

    #[test]
    fn test_invalid_plugins_path() {
        let result = XseChecker::new("/nonexistent/path", false, GameVersion::Original);
        assert!(result.is_err());
    }

    #[test]
    fn test_message_formatting_correct() {
        let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::Original).unwrap();

        let message = checker.validate();
        assert!(message.contains("✔️"));
        assert!(message.contains("correct version"));
    }

    #[test]
    fn test_message_formatting_wrong() {
        let temp_dir = setup_test_plugins_dir(&["version-1-2-72-0.csv"]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::Original).unwrap();

        let message = checker.validate();
        assert!(message.contains("❌"));
        assert!(message.contains("wrong version"));
        assert!(message.contains("Non-VR (Regular) version"));
    }

    #[test]
    fn test_message_formatting_not_found() {
        let temp_dir = setup_test_plugins_dir(&[]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::Original).unwrap();

        let message = checker.validate();
        assert!(message.contains("❓"));
        assert!(message.contains("not found"));
    }

    #[test]
    fn test_message_formatting_version_not_detected() {
        let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::Null).unwrap();

        let message = checker.validate();
        assert!(message.contains("❓"));
        assert!(message.contains("Unable to locate"));
    }

    #[test]
    fn test_multiple_correct_versions_non_vr() {
        // Non-VR can have either OG or NG - both are correct
        let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin", "version-1-10-984-0.bin"]);
        let checker = XseChecker::new(temp_dir.path(), false, GameVersion::Original).unwrap();

        let result = checker.check();
        assert_eq!(result, ValidationResult::CorrectVersion);
    }
}
