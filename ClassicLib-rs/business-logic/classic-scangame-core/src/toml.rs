//! TOML Configuration Validation Module
//!
//! Provides high-performance TOML configuration validation for crash generator mods (Buffout4).
//! Replaces Python CheckCrashgen with native Rust implementation offering:
//! - Fast TOML parsing with toml crate
//! - Plugin detection from filesystem
//! - Read-only configuration issue detection
//! - Memory-efficient validation
//!
//! ## Architecture
//!
//! Validates Buffout4/crash generator TOML configuration and detects:
//! - Missing or duplicate configuration files
//! - Installed plugin conflicts (X-Cell, Achievements, F4EE)
//! - Incorrect TOML settings for installed plugins
//! - Configuration issues with recommended fixes (read-only)

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use thiserror::Error;
use toml::Value;

/// Errors that can occur during TOML validation
#[derive(Debug, Error)]
pub enum TomlError {
    /// Failed to read TOML file
    #[error("Failed to read TOML file: {0}")]
    IoError(#[from] std::io::Error),

    /// Failed to parse TOML file
    #[error("Failed to parse TOML file: {0}")]
    ParseError(#[from] toml::de::Error),

    /// Configuration not found
    #[error("Configuration not found: {0}")]
    NotFound(String),
}

/// Result type for TOML operations
pub type Result<T> = std::result::Result<T, TomlError>;

/// Severity level for configuration issues
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TomlIssueSeverity {
    /// Error level issue
    Error,
    /// Warning level issue
    Warning,
    /// Informational issue
    Info,
}

/// Configuration issue detected in TOML file
#[derive(Debug, Clone)]
pub struct TomlConfigIssue {
    /// Path to the configuration file
    pub file_path: PathBuf,

    /// Section in the TOML file
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
    pub severity: TomlIssueSeverity,
}

/// Setting to check in TOML configuration
#[derive(Debug, Clone)]
struct TomlSetting {
    /// Section name
    section: String,

    /// Key name
    key: String,

    /// Display name
    name: String,

    /// Whether condition is met (plugin installed)
    condition: bool,

    /// Desired value
    desired_value: Value,

    /// Description for user
    description: String,

    /// Reason for the setting
    reason: String,

    /// Special case handling (e.g., "bakascrapheap")
    special_case: Option<String>,
}

/// Buffout4/Crash Generator configuration checker
///
/// Validates crash generator TOML configuration and detects plugin conflicts.
/// Operates in read-only mode - reports issues without modifying files.
///
/// # Example
///
/// ```rust,no_run
/// use classic_scangame_core::toml::CrashgenChecker;
/// use std::path::Path;
///
/// let mut checker = CrashgenChecker::new(
///     Path::new("/plugins"),
///     "Buffout4"
/// );
/// let (report, issues) = checker.check()?;
/// println!("{}", report);
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub struct CrashgenChecker {
    /// Name of crash generator (e.g., "Buffout4")
    crashgen_name: String,

    /// Path to plugins directory
    plugins_path: PathBuf,

    /// Configuration file path
    config_file: Option<PathBuf>,

    /// Installed plugins (lowercase DLL names)
    installed_plugins: Vec<String>,

    /// Parsed TOML data
    toml_data: Option<HashMap<String, Value>>,

    /// Message list for reporting
    message_list: Vec<String>,
}

impl CrashgenChecker {
    /// Create a new TOML configuration checker
    ///
    /// # Arguments
    ///
    /// * `plugins_path` - Path to plugins directory
    /// * `crashgen_name` - Name of crash generator (e.g., "Buffout4")
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scangame_core::toml::CrashgenChecker;
    /// use std::path::Path;
    ///
    /// let checker = CrashgenChecker::new(
    ///     Path::new("/game/Data/F4SE/Plugins"),
    ///     "Buffout4"
    /// );
    /// ```
    pub fn new(plugins_path: &Path, crashgen_name: impl Into<String>) -> Self {
        let crashgen_name = crashgen_name.into();
        let plugins_path = plugins_path.to_path_buf();

        let mut checker = Self {
            crashgen_name,
            plugins_path: plugins_path.clone(),
            config_file: None,
            installed_plugins: Vec::new(),
            toml_data: None,
            message_list: Vec::new(),
        };

        // Detect installed plugins
        checker.installed_plugins = checker.detect_installed_plugins();

        // Find config file
        checker.config_file = checker.find_config_file();

        checker
    }

    /// Get the resolved configuration file path, if found
    pub fn config_file(&self) -> Option<&PathBuf> {
        self.config_file.as_ref()
    }

    /// Get the list of installed plugins (lowercase DLL names)
    pub fn installed_plugins(&self) -> &[String] {
        &self.installed_plugins
    }

    /// Find the configuration file
    ///
    /// Checks for both Buffout4/config.toml and Buffout4.toml
    ///
    /// # Returns
    ///
    /// Path to config file if found, None otherwise
    fn find_config_file(&mut self) -> Option<PathBuf> {
        let crashgen_toml_og = self.plugins_path.join("Buffout4/config.toml");
        let crashgen_toml_vr = self.plugins_path.join("Buffout4.toml");

        let og_exists = crashgen_toml_og.exists();
        let vr_exists = crashgen_toml_vr.exists();

        // Check for missing config files
        if !og_exists && !vr_exists {
            self.message_list.push(format!(
                "# ❌ CAUTION : {} TOML SETTINGS FILE NOT FOUND! #\n",
                self.crashgen_name.to_uppercase()
            ));
            self.message_list.push(format!(
                "Please recheck your {} installation and delete any obsolete files.\n-----\n",
                self.crashgen_name
            ));
            return None;
        }

        // Check for duplicate config files
        if og_exists && vr_exists {
            self.message_list.push(format!(
                "# ❌ CAUTION : BOTH VERSIONS OF {} TOML SETTINGS FILES WERE FOUND! #\n",
                self.crashgen_name.to_uppercase()
            ));
            self.message_list.push(format!(
                "When editing {} toml settings, make sure you are editing the correct file.\n",
                self.crashgen_name
            ));
            self.message_list.push(format!(
                "Please recheck your {} installation and delete any obsolete files.\n-----\n",
                self.crashgen_name
            ));
        }

        // Return the appropriate config file
        if og_exists {
            Some(crashgen_toml_og)
        } else if vr_exists {
            Some(crashgen_toml_vr)
        } else {
            None
        }
    }

    /// Detect installed plugins by scanning plugins directory
    ///
    /// # Returns
    ///
    /// Vector of lowercase DLL file names
    fn detect_installed_plugins(&self) -> Vec<String> {
        let mut plugins = Vec::new();

        if self.plugins_path.exists() {
            if let Ok(entries) = fs::read_dir(&self.plugins_path) {
                for entry in entries.flatten() {
                    if let Ok(file_name) = entry.file_name().into_string() {
                        plugins.push(file_name.to_lowercase());
                    }
                }
            }
        }

        plugins
    }

    /// Check if any of the specified plugins are installed
    ///
    /// # Arguments
    ///
    /// * `plugin_names` - List of plugin names to check
    ///
    /// # Returns
    ///
    /// true if any plugin is installed, false otherwise
    fn has_plugin(&self, plugin_names: &[&str]) -> bool {
        plugin_names
            .iter()
            .any(|plugin| self.installed_plugins.contains(&plugin.to_lowercase()))
    }

    /// Load and parse TOML configuration file
    ///
    /// # Returns
    ///
    /// Ok(()) if successful, error otherwise
    fn load_toml(&mut self) -> Result<()> {
        if let Some(ref config_file) = self.config_file {
            let content = fs::read_to_string(config_file)?;
            let data: HashMap<String, Value> = toml::from_str(&content)?;
            self.toml_data = Some(data);
            Ok(())
        } else {
            Err(TomlError::NotFound("Config file not found".to_string()))
        }
    }

    /// Get a value from TOML configuration
    ///
    /// # Arguments
    ///
    /// * `section` - Section name
    /// * `key` - Key name
    ///
    /// # Returns
    ///
    /// Value if found, None otherwise
    fn get_value(&self, section: &str, key: &str) -> Option<&Value> {
        self.toml_data.as_ref()?.get(section)?.as_table()?.get(key)
    }

    /// Get settings to check based on installed plugins
    ///
    /// # Returns
    ///
    /// Vector of settings to validate
    fn get_settings_to_check(&self) -> Vec<TomlSetting> {
        let has_xcell = self.has_plugin(&[
            "x-cell-fo4.dll",
            "x-cell-og.dll",
            "x-cell-ng2.dll",
            "x-cell-ae.dll",
        ]);
        let has_achievements =
            self.has_plugin(&["achievements.dll", "achievementsmodsenablerloader.dll"]);
        let has_looksmenu = self.installed_plugins.iter().any(|f| f.contains("f4ee"));
        let is_og_config = self
            .config_file
            .as_ref()
            .map(|p| {
                p.to_string_lossy()
                    .to_lowercase()
                    .contains("buffout4/config.toml")
            })
            .unwrap_or(false);

        vec![
            // Patches section settings
            TomlSetting {
                section: "Patches".to_string(),
                key: "Achievements".to_string(),
                name: "Achievements".to_string(),
                condition: has_achievements,
                desired_value: Value::Boolean(false),
                description: "The Achievements Mod and/or Unlimited Survival Mode is installed"
                    .to_string(),
                reason: format!("to prevent conflicts with {}", self.crashgen_name),
                special_case: None,
            },
            TomlSetting {
                section: "Patches".to_string(),
                key: "MemoryManager".to_string(),
                name: "Memory Manager".to_string(),
                condition: has_xcell,
                desired_value: Value::Boolean(false),
                description: "The X-Cell/Addictol Mod is installed".to_string(),
                reason: "to prevent conflicts with X-Cell/Addictol".to_string(),
                special_case: Some("bakascrapheap".to_string()),
            },
            TomlSetting {
                section: "Patches".to_string(),
                key: "HavokMemorySystem".to_string(),
                name: "Havok Memory System".to_string(),
                condition: has_xcell,
                desired_value: Value::Boolean(false),
                description: "The X-Cell/Addictol Mod is installed".to_string(),
                reason: "to prevent conflicts with X-Cell/Addictol".to_string(),
                special_case: None,
            },
            TomlSetting {
                section: "Patches".to_string(),
                key: "BSTextureStreamerLocalHeap".to_string(),
                name: "BS Texture Streamer Local Heap".to_string(),
                condition: has_xcell,
                desired_value: Value::Boolean(false),
                description: "The X-Cell/Addictol Mod is installed".to_string(),
                reason: "to prevent conflicts with X-Cell/Addictol".to_string(),
                special_case: None,
            },
            TomlSetting {
                section: "Patches".to_string(),
                key: "ScaleformAllocator".to_string(),
                name: "Scaleform Allocator".to_string(),
                condition: has_xcell,
                desired_value: Value::Boolean(false),
                description: "The X-Cell/Addictol Mod is installed".to_string(),
                reason: "to prevent conflicts with X-Cell/Addictol".to_string(),
                special_case: None,
            },
            TomlSetting {
                section: "Patches".to_string(),
                key: "SmallBlockAllocator".to_string(),
                name: "Small Block Allocator".to_string(),
                condition: has_xcell,
                desired_value: Value::Boolean(false),
                description: "The X-Cell/Addictol Mod is installed".to_string(),
                reason: "to prevent conflicts with X-Cell/Addictol".to_string(),
                special_case: None,
            },
            TomlSetting {
                section: "Patches".to_string(),
                key: "ArchiveLimit".to_string(),
                name: "Archive Limit".to_string(),
                condition: is_og_config,
                desired_value: Value::Boolean(false),
                description: "Archive Limit is enabled".to_string(),
                reason: "to prevent crashes".to_string(),
                special_case: None,
            },
            TomlSetting {
                section: "Patches".to_string(),
                key: "MaxStdIO".to_string(),
                name: "MaxStdIO".to_string(),
                condition: false, // Always check but don't flag as issue
                desired_value: Value::Integer(2048),
                description: "MaxStdIO is set to a low value".to_string(),
                reason: "to improve performance".to_string(),
                special_case: None,
            },
            // Compatibility section settings
            TomlSetting {
                section: "Compatibility".to_string(),
                key: "F4EE".to_string(),
                name: "F4EE (Looks Menu)".to_string(),
                condition: has_looksmenu,
                desired_value: Value::Boolean(true),
                description: "Looks Menu is installed, but F4EE parameter is set to FALSE"
                    .to_string(),
                reason: "to prevent bugs and crashes from Looks Menu".to_string(),
                special_case: None,
            },
        ]
    }

    /// Detect configuration issues without modifying files
    ///
    /// # Returns
    ///
    /// Vector of detected configuration issues
    fn detect_settings_issues(&mut self) -> Vec<TomlConfigIssue> {
        let mut issues = Vec::new();

        // Early return if no config file
        let config_file = match &self.config_file {
            Some(f) => f.clone(),
            None => return issues,
        };

        let has_bakascrapheap = self.has_plugin(&["bakascrapheap.dll"]);

        for setting in self.get_settings_to_check() {
            // Get current value from TOML
            let current_value = self.get_value(&setting.section, &setting.key);

            // Special case for BakaScrapHeap with MemoryManager
            if setting.special_case.as_deref() == Some("bakascrapheap")
                && has_bakascrapheap
                && current_value.is_some()
            {
                let issue = TomlConfigIssue {
                    file_path: config_file.clone(),
                    section: setting.section.clone(),
                    setting: setting.key.clone(),
                    current_value: format!("{:?}", current_value),
                    recommended_value: format!("{:?}", setting.desired_value),
                    description: format!(
                        "The Baka ScrapHeap Mod is installed, but is redundant with {}. \
                         Uninstall the Baka ScrapHeap Mod to prevent conflicts with {}.",
                        self.crashgen_name, self.crashgen_name
                    ),
                    severity: TomlIssueSeverity::Error,
                };
                issues.push(issue);
                self.message_list.push(format!(
                    "# ❌ CAUTION : The Baka ScrapHeap Mod is installed, but is redundant with {} #\n",
                    self.crashgen_name
                ));
                self.message_list.push(format!(
                    " FIX: Uninstall the Baka ScrapHeap Mod, this prevents conflicts with {}.\n-----\n",
                    self.crashgen_name
                ));
                continue;
            }

            // Check if condition is met and setting needs attention
            if setting.condition {
                if let Some(current) = current_value {
                    if current != &setting.desired_value {
                        let issue = TomlConfigIssue {
                            file_path: config_file.clone(),
                            section: setting.section.clone(),
                            setting: setting.key.clone(),
                            current_value: format!("{:?}", current),
                            recommended_value: format!("{:?}", setting.desired_value),
                            description: format!("{}. {}", setting.description, setting.reason),
                            severity: TomlIssueSeverity::Warning,
                        };
                        issues.push(issue);
                        self.message_list.push(format!(
                            "# ❌ CAUTION : {}, but {} parameter is set to {:?} #\n",
                            setting.description, setting.name, current
                        ));
                        self.message_list.push(format!(
                            " FIX: Open {}'s TOML file and change {} to {:?} {}.\n-----\n",
                            self.crashgen_name, setting.name, setting.desired_value, setting.reason
                        ));
                    } else {
                        // Setting is correctly configured
                        self.message_list.push(format!(
                            "✔️ {} parameter is correctly configured in your {} settings!\n-----\n",
                            setting.name, self.crashgen_name
                        ));
                    }
                }
            }
        }

        issues
    }

    /// Check configuration and detect issues
    ///
    /// # Returns
    ///
    /// Tuple of (report_string, issues_vector)
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// # use classic_scangame_core::toml::CrashgenChecker;
    /// # use std::path::Path;
    /// # let mut checker = CrashgenChecker::new(Path::new("/plugins"), "Buffout4");
    /// let (report, issues) = checker.check()?;
    /// if !issues.is_empty() {
    ///     println!("Found {} issues", issues.len());
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn check(&mut self) -> Result<(String, Vec<TomlConfigIssue>)> {
        // If no config file found, return message without raising exception
        if self.config_file.is_none() {
            self.message_list.push(format!(
                "# [!] NOTICE : Unable to find the {} config file, settings check will be skipped. #\n",
                self.crashgen_name
            ));
            self.message_list.push(format!(
                "  To ensure this check doesn't get skipped, {} has to be installed manually.\n",
                self.crashgen_name
            ));
            self.message_list.push(
                "  [ If you are using Mod Organizer 2, you need to run CLASSIC through a shortcut in MO2. ]\n-----\n"
                    .to_string(),
            );
            return Ok((self.message_list.join(""), Vec::new()));
        }

        // If Addictol is installed, skip all Buffout TOML checks.
        // Some Addictol versions mask themselves as Buffout in the crash log header,
        // so we detect via DLL presence rather than relying on the header.
        if self.has_plugin(&["addictol.dll"]) {
            if self.has_plugin(&["buffout4.dll"]) {
                // Both present: warn about incompatibility
                self.message_list.push(format!(
                    "# ⚠️ NOTICE : {} and Addictol are incompatible, remove one to avoid crashes. #\n",
                    self.crashgen_name
                ));
                self.message_list.push(format!(
                    "  Skipping {} TOML settings checks.\n-----\n",
                    self.crashgen_name
                ));
            } else {
                // Addictol only: skip silently
                self.message_list.push(format!(
                    "# [!] NOTICE : Addictol detected — skipping {} TOML settings checks. #\n-----\n",
                    self.crashgen_name
                ));
            }
            return Ok((self.message_list.join(""), Vec::new()));
        }

        // Load TOML data
        self.load_toml()?;

        // Detect issues
        let issues = self.detect_settings_issues();

        Ok((self.message_list.join(""), issues))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_checker_creation() {
        let temp_dir = TempDir::new().unwrap();
        let checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
        assert_eq!(checker.crashgen_name, "Buffout4");
    }

    #[test]
    fn test_plugin_detection() {
        let temp_dir = TempDir::new().unwrap();

        // Create fake DLL files
        fs::write(temp_dir.path().join("x-cell-fo4.dll"), b"").unwrap();
        fs::write(temp_dir.path().join("achievements.dll"), b"").unwrap();

        let checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
        assert!(checker.has_plugin(&["x-cell-fo4.dll"]));
        assert!(checker.has_plugin(&["achievements.dll"]));
        assert!(!checker.has_plugin(&["nonexistent.dll"]));
    }

    #[test]
    fn test_config_file_detection() {
        let temp_dir = TempDir::new().unwrap();
        let buffout_dir = temp_dir.path().join("Buffout4");
        fs::create_dir(&buffout_dir).unwrap();

        let config_file = buffout_dir.join("config.toml");
        fs::write(&config_file, "[Patches]\nAchievements = true\n").unwrap();

        let checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
        assert!(checker.config_file.is_some());
        assert_eq!(checker.config_file.unwrap(), config_file);
    }

    #[test]
    fn test_toml_parsing() {
        let temp_dir = TempDir::new().unwrap();
        let buffout_dir = temp_dir.path().join("Buffout4");
        fs::create_dir(&buffout_dir).unwrap();

        let config_file = buffout_dir.join("config.toml");
        fs::write(
            &config_file,
            "[Patches]\nAchievements = true\nMemoryManager = true\n",
        )
        .unwrap();

        let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
        checker.load_toml().unwrap();

        assert_eq!(
            checker.get_value("Patches", "Achievements"),
            Some(&Value::Boolean(true))
        );
        assert_eq!(
            checker.get_value("Patches", "MemoryManager"),
            Some(&Value::Boolean(true))
        );
    }

    #[test]
    fn test_issue_detection() {
        let temp_dir = TempDir::new().unwrap();
        let buffout_dir = temp_dir.path().join("Buffout4");
        fs::create_dir(&buffout_dir).unwrap();

        // Create config with Achievements enabled
        let config_file = buffout_dir.join("config.toml");
        fs::write(&config_file, "[Patches]\nAchievements = true\n").unwrap();

        // Create achievements.dll to trigger condition
        fs::write(temp_dir.path().join("achievements.dll"), b"").unwrap();

        let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
        let (_report, issues) = checker.check().unwrap();

        // Should detect Achievements issue
        assert!(!issues.is_empty());
        assert!(issues.iter().any(|i| i.setting == "Achievements"));
    }

    #[test]
    fn test_addictol_skips_all_toml_checks() {
        let temp_dir = TempDir::new().unwrap();
        let buffout_dir = temp_dir.path().join("Buffout4");
        fs::create_dir(&buffout_dir).unwrap();

        // Create config with MemoryManager enabled (would normally be flagged)
        let config_file = buffout_dir.join("config.toml");
        fs::write(&config_file, "[Patches]\nMemoryManager = true\n").unwrap();

        // Addictol DLL only (no Buffout4 DLL) — skip silently, no incompatibility warning
        fs::write(temp_dir.path().join("Addictol.dll"), b"").unwrap();

        let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
        let (report, issues) = checker.check().unwrap();

        assert!(
            issues.is_empty(),
            "No issues should be reported when Addictol is detected"
        );
        assert!(
            report.contains("Addictol detected"),
            "Report should mention Addictol"
        );
        assert!(
            !report.contains("incompatible"),
            "Should NOT warn about incompatibility when only Addictol is present"
        );
    }

    #[test]
    fn test_addictol_and_buffout_shows_incompatibility_warning() {
        let temp_dir = TempDir::new().unwrap();
        let buffout_dir = temp_dir.path().join("Buffout4");
        fs::create_dir(&buffout_dir).unwrap();

        // Create config with MemoryManager enabled (would normally be flagged)
        let config_file = buffout_dir.join("config.toml");
        fs::write(&config_file, "[Patches]\nMemoryManager = true\n").unwrap();

        // Both Addictol AND Buffout4 DLLs present — should warn about incompatibility
        fs::write(temp_dir.path().join("Addictol.dll"), b"").unwrap();
        fs::write(temp_dir.path().join("Buffout4.dll"), b"").unwrap();

        let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
        let (report, issues) = checker.check().unwrap();

        assert!(
            issues.is_empty(),
            "No issues should be reported — TOML checks are skipped"
        );
        assert!(
            report.contains("incompatible"),
            "Should warn about incompatibility when both are present"
        );
        assert!(
            report.contains("remove one to avoid crashes"),
            "Should have clear removal guidance"
        );
    }

    #[test]
    fn test_xcell_still_triggers_memory_checks_without_addictol() {
        let temp_dir = TempDir::new().unwrap();
        let buffout_dir = temp_dir.path().join("Buffout4");
        fs::create_dir(&buffout_dir).unwrap();

        let config_file = buffout_dir.join("config.toml");
        fs::write(&config_file, "[Patches]\nMemoryManager = true\n").unwrap();

        // Only X-Cell DLL, no Addictol
        fs::write(temp_dir.path().join("x-cell-fo4.dll"), b"").unwrap();

        let mut checker = CrashgenChecker::new(temp_dir.path(), "Buffout4");
        let (_report, issues) = checker.check().unwrap();

        assert!(issues.iter().any(|i| i.setting == "MemoryManager"));
    }
}
