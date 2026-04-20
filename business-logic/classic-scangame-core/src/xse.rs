//! XSE (F4SE/SKSE) plugin validation module for Address Library checking.
//!
//! This module provides functionality to validate the correct Address Library
//! version is installed for the current game mode (VR vs non-VR). It detects
//! both correct and incorrect versions and provides user-friendly messages
//! to guide resolution of compatibility issues.

use std::path::{Path, PathBuf};
use thiserror::Error;

use classic_version_registry_core::get_version_registry;

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
    /// Anniversary Edition version (1.11.137.0 - 1.11.191.0+)
    AnniversaryEdition,
    /// VR version (1.2.72.0)
    Vr,
}

impl GameVersion {
    /// Get the VersionRegistry ID for this version.
    fn registry_id(&self) -> Option<&'static str> {
        match self {
            Self::Null => None,
            Self::Original => Some("FO4_OG"),
            Self::NextGen => Some("FO4_NG"),
            Self::AnniversaryEdition => Some("FO4_AE"),
            Self::Vr => Some("FO4_VR"),
        }
    }

    /// Returns true if this is the null version (not detected).
    pub fn is_null(&self) -> bool {
        matches!(self, Self::Null)
    }

    /// Returns a human-readable description of this version.
    ///
    /// Uses the VersionRegistry to get the display name and version string.
    /// Falls back to hardcoded values if registry lookup fails.
    pub fn description(&self) -> String {
        if let Some(id) = self.registry_id() {
            let registry = get_version_registry();
            if let Some(info) = registry.get_by_id(id) {
                return format!("{} ({})", info.display_name, info.version);
            }
        }
        // Fallback to hardcoded values if registry fails
        match self {
            Self::Null => "Not Detected".to_string(),
            Self::Original => "Original (1.10.163.0)".to_string(),
            Self::NextGen => "Next Gen (1.10.984.0)".to_string(),
            Self::AnniversaryEdition => "Anniversary Edition (1.11.137.0 - 1.11.191.0)".to_string(),
            Self::Vr => "VR (1.2.72.0)".to_string(),
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
    /// Create Address Library info from VersionRegistry with fallback.
    ///
    /// Attempts to get Address Library configuration from the registry,
    /// falling back to hardcoded values if not available.
    fn from_registry_id(
        id: &str,
        version: GameVersion,
        fallback_filename: &str,
        fallback_desc: &str,
        fallback_url: &str,
    ) -> Self {
        let registry = get_version_registry();

        if let Some(info) = registry.get_by_id(id) {
            if let Some(addr_lib) = &info.address_library {
                return Self {
                    version,
                    filename: addr_lib.filename.clone(),
                    description: format!("{} ({})", info.display_name, info.short_name),
                    url: addr_lib.nexus_url.clone(),
                };
            }
        }

        // Fallback to hardcoded values
        Self {
            version,
            filename: fallback_filename.to_string(),
            description: fallback_desc.to_string(),
            url: fallback_url.to_string(),
        }
    }

    /// Create VR Address Library info.
    ///
    /// Uses VersionRegistry when available, falls back to hardcoded values.
    pub fn vr() -> Self {
        Self::from_registry_id(
            "FO4_VR",
            GameVersion::Vr,
            "version-1-2-72-0.csv",
            "Virtual Reality (VR) version",
            "https://www.nexusmods.com/fallout4/mods/64879?tab=files",
        )
    }

    /// Create Original (OG) Address Library info.
    ///
    /// Uses VersionRegistry when available, falls back to hardcoded values.
    pub fn original() -> Self {
        Self::from_registry_id(
            "FO4_OG",
            GameVersion::Original,
            "version-1-10-163-0.bin",
            "Non-VR (Regular) version",
            "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )
    }

    /// Create Next Gen (NG) Address Library info.
    ///
    /// Uses VersionRegistry when available, falls back to hardcoded values.
    pub fn next_gen() -> Self {
        Self::from_registry_id(
            "FO4_NG",
            GameVersion::NextGen,
            "version-1-10-984-0.bin",
            "Non-VR (Next Gen) version",
            "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )
    }

    /// Create Anniversary Edition (AE) Address Library info.
    ///
    /// Uses VersionRegistry when available, falls back to hardcoded values.
    pub fn anniversary_edition() -> Self {
        Self::from_registry_id(
            "FO4_AE",
            GameVersion::AnniversaryEdition,
            "version-1-11-191-0.bin",
            "Non-VR (Anniversary Edition) version",
            "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )
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
    /// Detected game version
    game_version: GameVersion,
}

impl XseChecker {
    /// Create a new XSE checker.
    ///
    /// # Arguments
    ///
    /// * `plugins_path` - Path to the F4SE/SKSE plugins directory
    /// * `game_version` - Detected game version
    ///
    /// # Errors
    ///
    /// Returns an error if the plugins path is invalid.
    pub fn new(
        plugins_path: impl AsRef<Path>,
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
            game_version,
        })
    }

    /// Determine the correct and wrong Address Library versions for the selected game version.
    fn determine_relevant_versions(&self) -> (Vec<AddressLibInfo>, Vec<AddressLibInfo>) {
        if matches!(self.game_version, GameVersion::Vr) {
            // VR mode: correct = VR, wrong = OG + NG + AE
            let correct = vec![AddressLibInfo::vr()];
            let wrong = vec![
                AddressLibInfo::original(),
                AddressLibInfo::next_gen(),
                AddressLibInfo::anniversary_edition(),
            ];
            (correct, wrong)
        } else {
            // Non-VR mode: correct = OG + NG + AE, wrong = VR
            let correct = vec![
                AddressLibInfo::original(),
                AddressLibInfo::next_gen(),
                AddressLibInfo::anniversary_edition(),
            ];
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
#[path = "xse_tests.rs"]
mod tests;
