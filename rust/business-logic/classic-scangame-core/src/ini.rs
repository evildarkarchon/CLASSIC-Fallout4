//! INI File Validation Module
//!
//! Provides high-performance INI file validation for game configuration files.
//! Replaces Python ScanModInis with native Rust implementation offering:
//! - Fast INI parsing with configparser crate
//! - Efficient multi-file validation
//! - Read-only issue detection (no auto-fix)
//! - Memory-efficient result collection
//!
//! ## Architecture
//!
//! Validates INI configuration files and detects:
//! - Console command settings that may slow startup
//! - VSync settings across multiple configuration files
//! - Configuration issues with recommended fixes (read-only)
//! - Duplicate configuration files (via config module)

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use configparser::ini::Ini;
use thiserror::Error;

/// Errors that can occur during INI validation
#[derive(Debug, Error)]
pub enum IniError {
    /// Failed to read INI file
    #[error("Failed to read INI file: {0}")]
    IoError(#[from] std::io::Error),

    /// Failed to parse INI file
    #[error("Failed to parse INI file: {0}")]
    ParseError(String),

    /// Configuration not found
    #[error("Configuration not found: {0}")]
    NotFound(String),
}

/// Result type for INI operations
pub type Result<T> = std::result::Result<T, IniError>;

/// Severity level for configuration issues
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IssueSeverity {
    /// Error level issue
    Error,
    /// Warning level issue
    Warning,
    /// Informational issue
    Info,
}

/// Configuration issue detected in INI file
#[derive(Debug, Clone)]
pub struct ConfigIssue {
    /// Path to the configuration file
    pub file_path: PathBuf,

    /// Section in the INI file
    pub section: String,

    /// Setting name
    pub setting: String,

    /// Current value
    pub current_value: String,

    /// Recommended value
    pub recommended_value: String,

    /// Human-readable description
    pub description: String,

    /// Issue severity
    pub severity: IssueSeverity,
}

/// VSync setting configuration
#[derive(Debug, Clone)]
struct VsyncSetting {
    /// File name (lowercase)
    file_name: String,

    /// Section in INI file
    section: String,

    /// Setting name
    setting: String,
}

/// INI file validator
///
/// Validates game configuration files and detects issues.
/// Operates in read-only mode - reports issues without modifying files.
///
/// # Example
///
/// ```rust
/// use classic_scangame_core::ini::IniValidator;
/// use std::path::Path;
///
/// let validator = IniValidator::new("Fallout4");
/// let report = validator.validate_inis(Path::new("/game"))?;
/// println!("{}", report);
/// ```
pub struct IniValidator {
    /// Game name (e.g., "Fallout4", "Skyrim")
    game_name: String,

    /// Cache of parsed INI files
    ini_cache: HashMap<String, Ini>,

    /// VSync settings to check
    vsync_settings: Vec<VsyncSetting>,
}

impl IniValidator {
    /// Create a new INI validator
    ///
    /// # Arguments
    ///
    /// * `game_name` - Name of the game (e.g., "Fallout4")
    ///
    /// # Example
    ///
    /// ```rust
    /// let validator = IniValidator::new("Fallout4");
    /// ```
    pub fn new(game_name: impl Into<String>) -> Self {
        let game_name = game_name.into();

        // Initialize VSync settings to check
        let vsync_settings = vec![
            VsyncSetting {
                file_name: "dxvk.conf".to_string(),
                section: format!("{}.exe", game_name),
                setting: "dxgi.syncInterval".to_string(),
            },
            VsyncSetting {
                file_name: "enblocal.ini".to_string(),
                section: "ENGINE".to_string(),
                setting: "ForceVSync".to_string(),
            },
            VsyncSetting {
                file_name: "longloadingtimesfix.ini".to_string(),
                section: "Limiter".to_string(),
                setting: "EnableVSync".to_string(),
            },
            VsyncSetting {
                file_name: "reshade.ini".to_string(),
                section: "APP".to_string(),
                setting: "ForceVsync".to_string(),
            },
            VsyncSetting {
                file_name: "fallout4_test.ini".to_string(),
                section: "CreationKit".to_string(),
                setting: "VSyncRender".to_string(),
            },
        ];

        Self {
            game_name,
            ini_cache: HashMap::new(),
            vsync_settings,
        }
    }

    /// Load an INI file into cache
    ///
    /// # Arguments
    ///
    /// * `file_path` - Path to the INI file
    ///
    /// # Returns
    ///
    /// Ok(()) if successful, error otherwise
    fn load_ini(&mut self, file_path: &Path) -> Result<()> {
        let file_name_lower = file_path
            .file_name()
            .and_then(|n| n.to_str())
            .map(|s| s.to_lowercase())
            .ok_or_else(|| IniError::NotFound("Invalid file path".to_string()))?;

        // Skip if already cached
        if self.ini_cache.contains_key(&file_name_lower) {
            return Ok(());
        }

        // Read file content
        let content = fs::read_to_string(file_path)?;

        // Parse INI
        let mut ini = Ini::new();
        ini.read(content).map_err(IniError::ParseError)?;

        self.ini_cache.insert(file_name_lower, ini);
        Ok(())
    }

    /// Check if a setting exists in an INI file
    ///
    /// # Arguments
    ///
    /// * `file_name_lower` - Lowercase file name
    /// * `section` - Section name
    /// * `setting` - Setting name
    ///
    /// # Returns
    ///
    /// true if setting exists, false otherwise
    fn has_setting(&self, file_name_lower: &str, section: &str, setting: &str) -> bool {
        if let Some(ini) = self.ini_cache.get(file_name_lower) {
            ini.get(section, setting).is_some()
        } else {
            false
        }
    }

    /// Get a setting value from an INI file
    ///
    /// # Arguments
    ///
    /// * `file_name_lower` - Lowercase file name
    /// * `section` - Section name
    /// * `setting` - Setting name
    ///
    /// # Returns
    ///
    /// Setting value if found, None otherwise
    fn get_setting(&self, file_name_lower: &str, section: &str, setting: &str) -> Option<String> {
        self.ini_cache
            .get(file_name_lower)
            .and_then(|ini| ini.get(section, setting))
    }

    /// Check for console command settings
    ///
    /// # Arguments
    ///
    /// * `config_files` - Map of file name (lowercase) to file path
    ///
    /// # Returns
    ///
    /// List of notice messages for console command settings
    fn check_console_command(&self, config_files: &HashMap<String, PathBuf>) -> Vec<String> {
        let mut messages = Vec::new();
        let game_lower = self.game_name.to_lowercase();

        for (file_lower, file_path) in config_files {
            if file_lower.starts_with(&game_lower)
                && self.has_setting(file_lower, "General", "sStartingConsoleCommand")
            {
                messages.push(format!(
                    "[!] NOTICE: {} contains the *sStartingConsoleCommand* setting.\n",
                    file_path.display()
                ));
                messages.push(
                    "In rare cases, this setting can slow down the initial game startup time for some players.\n\
                     You can test your initial startup time difference by removing this setting from the INI file.\n-----\n"
                        .to_string(),
                );
            }
        }

        messages
    }

    /// Check VSync settings in configuration files
    ///
    /// # Arguments
    ///
    /// * `config_files` - Map of file name (lowercase) to file path
    ///
    /// # Returns
    ///
    /// List of VSync status messages
    fn check_vsync_settings(&self, config_files: &HashMap<String, PathBuf>) -> Vec<String> {
        let mut vsync_list = Vec::new();

        // Check standard VSync settings
        for vsync_setting in &self.vsync_settings {
            if let Some(file_path) = config_files.get(&vsync_setting.file_name) {
                if let Some(value) = self.get_setting(
                    &vsync_setting.file_name,
                    &vsync_setting.section,
                    &vsync_setting.setting,
                ) {
                    // Check if value represents "enabled" (true, 1, yes, etc.)
                    let enabled = value.trim().eq_ignore_ascii_case("true")
                        || value.trim().eq_ignore_ascii_case("1")
                        || value.trim().eq_ignore_ascii_case("yes");

                    if enabled {
                        vsync_list.push(format!(
                            "{} | SETTING: {}\n",
                            file_path.display(),
                            vsync_setting.setting
                        ));
                    }
                }
            }
        }

        // Check highfpsphysicsfix.ini separately
        if let Some(file_path) = config_files.get("highfpsphysicsfix.ini") {
            if let Some(value) = self.get_setting("highfpsphysicsfix.ini", "Main", "EnableVSync") {
                let enabled = value.trim().eq_ignore_ascii_case("true")
                    || value.trim().eq_ignore_ascii_case("1")
                    || value.trim().eq_ignore_ascii_case("yes");

                if enabled {
                    vsync_list.push(format!("{} | SETTING: EnableVSync\n", file_path.display()));
                }
            }
        }

        vsync_list
    }

    /// Detect all known configuration issues
    ///
    /// # Arguments
    ///
    /// * `config_files` - Map of file name (lowercase) to file path
    ///
    /// # Returns
    ///
    /// List of detected configuration issues
    pub fn detect_all_issues(&self, config_files: &HashMap<String, PathBuf>) -> Vec<ConfigIssue> {
        let mut issues = Vec::new();

        // ESPExplorer hotkey check
        if let Some(file_path) = config_files.get("espexplorer.ini") {
            if let Some(value) = self.get_setting("espexplorer.ini", "General", "HotKey") {
                if value.contains("; F10") {
                    issues.push(ConfigIssue {
                        file_path: file_path.clone(),
                        section: "General".to_string(),
                        setting: "HotKey".to_string(),
                        current_value: value,
                        recommended_value: "0x79".to_string(),
                        description: "Hotkey is commented out and won't work. Change to hex code 0x79 for F10.".to_string(),
                        severity: IssueSeverity::Warning,
                    });
                }
            }
        }

        // EPO particle count check
        if let Some(file_path) = config_files.get("epo.ini") {
            if let Some(value) = self.get_setting("epo.ini", "Particles", "iMaxDesired") {
                if let Ok(count) = value.parse::<i32>() {
                    if count > 5000 {
                        issues.push(ConfigIssue {
                            file_path: file_path.clone(),
                            section: "Particles".to_string(),
                            setting: "iMaxDesired".to_string(),
                            current_value: value,
                            recommended_value: "5000".to_string(),
                            description:
                                "High particle count can cause performance issues and crashes."
                                    .to_string(),
                            severity: IssueSeverity::Warning,
                        });
                    }
                }
            }
        }

        // F4EE settings checks
        if let Some(file_path) = config_files.get("f4ee.ini") {
            // Head parts unlock check
            if let Some(value) = self.get_setting("f4ee.ini", "CharGen", "bUnlockHeadParts") {
                if value.trim() == "0" {
                    issues.push(ConfigIssue {
                        file_path: file_path.clone(),
                        section: "CharGen".to_string(),
                        setting: "bUnlockHeadParts".to_string(),
                        current_value: value,
                        recommended_value: "1".to_string(),
                        description: "Head parts are locked. Set to 1 to unlock all head parts."
                            .to_string(),
                        severity: IssueSeverity::Warning,
                    });
                }
            }

            // Face tints unlock check
            if let Some(value) = self.get_setting("f4ee.ini", "CharGen", "bUnlockTints") {
                if value.trim() == "0" {
                    issues.push(ConfigIssue {
                        file_path: file_path.clone(),
                        section: "CharGen".to_string(),
                        setting: "bUnlockTints".to_string(),
                        current_value: value,
                        recommended_value: "1".to_string(),
                        description: "Face tints are locked. Set to 1 to unlock all face tints."
                            .to_string(),
                        severity: IssueSeverity::Warning,
                    });
                }
            }
        }

        // High FPS Physics Fix loading screen FPS check
        if let Some(file_path) = config_files.get("highfpsphysicsfix.ini") {
            if let Some(value) =
                self.get_setting("highfpsphysicsfix.ini", "Limiter", "LoadingScreenFPS")
            {
                if let Ok(fps) = value.parse::<f64>() {
                    if fps < 600.0 {
                        issues.push(ConfigIssue {
                            file_path: file_path.clone(),
                            section: "Limiter".to_string(),
                            setting: "LoadingScreenFPS".to_string(),
                            current_value: value,
                            recommended_value: "600.0".to_string(),
                            description: "Loading screen FPS is too low. Increase to 600.0 to prevent physics issues.".to_string(),
                            severity: IssueSeverity::Warning,
                        });
                    }
                }
            }
        }

        issues
    }

    /// Validate INI files and generate report
    ///
    /// # Arguments
    ///
    /// * `game_root` - Root directory of the game installation
    ///
    /// # Returns
    ///
    /// Formatted validation report string
    ///
    /// # Example
    ///
    /// ```rust
    /// let report = validator.validate_inis(Path::new("/game"))?;
    /// if !report.is_empty() {
    ///     println!("Issues found:\n{}", report);
    /// }
    /// ```
    pub fn validate_inis(&mut self, game_root: &Path) -> Result<String> {
        // Scan for INI files
        let config_files = self.scan_config_files(game_root)?;

        // Load all INI files into cache
        for file_path in config_files.values() {
            if let Err(e) = self.load_ini(file_path) {
                eprintln!("Warning: Failed to load {}: {}", file_path.display(), e);
            }
        }

        let mut report = String::new();

        // Check console command settings
        let console_messages = self.check_console_command(&config_files);
        report.push_str(&console_messages.join(""));

        // Check VSync settings
        let vsync_list = self.check_vsync_settings(&config_files);
        if !vsync_list.is_empty() {
            report.push_str("* NOTICE : VSYNC IS CURRENTLY ENABLED IN THE FOLLOWING FILES *\n");
            report.push_str(&vsync_list.join(""));
        }

        Ok(report)
    }

    /// Scan for configuration files in game directory
    ///
    /// # Arguments
    ///
    /// * `game_root` - Root directory to scan
    ///
    /// # Returns
    ///
    /// Map of lowercase file name to file path
    fn scan_config_files(&self, game_root: &Path) -> Result<HashMap<String, PathBuf>> {
        let mut config_files = HashMap::new();

        // Walk the game root directory
        for entry in walkdir::WalkDir::new(game_root)
            .follow_links(false)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();

            // Only process .ini and .conf files
            if let Some(ext) = path.extension() {
                let ext_lower = ext.to_string_lossy().to_lowercase();
                if ext_lower == "ini" || ext_lower == "conf" {
                    if let Some(file_name) = path.file_name() {
                        let file_name_lower = file_name.to_string_lossy().to_lowercase();
                        config_files.insert(file_name_lower, path.to_path_buf());
                    }
                }
            }
        }

        Ok(config_files)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_validator_creation() {
        let validator = IniValidator::new("Fallout4");
        assert_eq!(validator.game_name, "Fallout4");
        assert_eq!(validator.vsync_settings.len(), 5);
    }

    #[test]
    fn test_console_command_detection() {
        let temp_dir = TempDir::new().unwrap();
        let ini_file = temp_dir.path().join("fallout4.ini");

        fs::write(
            &ini_file,
            "[General]\nsStartingConsoleCommand=bat autoexec\n",
        )
        .unwrap();

        let mut validator = IniValidator::new("Fallout4");
        validator.load_ini(&ini_file).unwrap();

        let mut config_files = HashMap::new();
        config_files.insert("fallout4.ini".to_string(), ini_file.clone());

        let messages = validator.check_console_command(&config_files);
        assert!(!messages.is_empty());
        assert!(messages[0].contains("sStartingConsoleCommand"));
    }

    #[test]
    fn test_vsync_detection() {
        let temp_dir = TempDir::new().unwrap();
        let ini_file = temp_dir.path().join("enblocal.ini");

        fs::write(&ini_file, "[ENGINE]\nForceVSync=true\n").unwrap();

        let mut validator = IniValidator::new("Fallout4");
        validator.load_ini(&ini_file).unwrap();

        let mut config_files = HashMap::new();
        config_files.insert("enblocal.ini".to_string(), ini_file.clone());

        let vsync_list = validator.check_vsync_settings(&config_files);
        assert!(!vsync_list.is_empty());
        assert!(vsync_list[0].contains("ForceVSync"));
    }

    #[test]
    fn test_issue_detection_epo() {
        let temp_dir = TempDir::new().unwrap();
        let ini_file = temp_dir.path().join("epo.ini");

        fs::write(&ini_file, "[Particles]\niMaxDesired=10000\n").unwrap();

        let mut validator = IniValidator::new("Fallout4");
        validator.load_ini(&ini_file).unwrap();

        let mut config_files = HashMap::new();
        config_files.insert("epo.ini".to_string(), ini_file.clone());

        let issues = validator.detect_all_issues(&config_files);
        assert!(!issues.is_empty());
        assert_eq!(issues[0].setting, "iMaxDesired");
        assert_eq!(issues[0].recommended_value, "5000");
    }

    #[test]
    fn test_issue_detection_f4ee() {
        let temp_dir = TempDir::new().unwrap();
        let ini_file = temp_dir.path().join("f4ee.ini");

        fs::write(&ini_file, "[CharGen]\nbUnlockHeadParts=0\nbUnlockTints=0\n").unwrap();

        let mut validator = IniValidator::new("Fallout4");
        validator.load_ini(&ini_file).unwrap();

        let mut config_files = HashMap::new();
        config_files.insert("f4ee.ini".to_string(), ini_file.clone());

        let issues = validator.detect_all_issues(&config_files);
        assert_eq!(issues.len(), 2);
        assert!(issues.iter().any(|i| i.setting == "bUnlockHeadParts"));
        assert!(issues.iter().any(|i| i.setting == "bUnlockTints"));
    }
}
