//! Documents configuration checking and validation.
//!
//! This module provides read-only checking of documents folder configuration,
//! including OneDrive detection and INI file validation.
//!
//! # Design Philosophy
//!
//! **Read-Only Operation**: This module ONLY detects configuration issues without
//! modifying files. It reports what's wrong and lets the caller decide how to fix it.
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_path_core::DocumentsChecker;
//! use std::path::Path;
//!
//! let checker = DocumentsChecker::new("Fallout4");
//! let docs_path = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
//!
//! // Check for OneDrive in path
//! if let Some(warning) = checker.check_onedrive_in_path(docs_path) {
//!     println!("Warning: {}", warning);
//! }
//!
//! // Validate an INI file
//! match checker.validate_ini_file(docs_path, "Fallout4.ini") {
//!     Ok(result) => println!("{}", result.message),
//!     Err(e) => eprintln!("Error: {}", e),
//! }
//! ```

use crate::IniFile;
use crate::error::DocsPathResult;
use std::path::Path;

/// Result of an INI file validation check.
///
/// This struct contains information about the validation status and any
/// issues detected in the INI file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IniCheckResult {
    /// The name of the INI file that was checked.
    pub ini_name: String,

    /// Whether the INI file exists.
    pub exists: bool,

    /// Whether the INI file is valid and parseable.
    pub is_valid: bool,

    /// Human-readable message describing the check result.
    pub message: String,

    /// Optional issue detected (e.g., "missing", "corrupted", "read_only", "missing_archive_section").
    pub issue: Option<String>,
}

impl IniCheckResult {
    /// Create a new IniCheckResult.
    ///
    /// # Arguments
    ///
    /// * `ini_name` - Name of the INI file
    /// * `exists` - Whether the file exists
    /// * `is_valid` - Whether the file is valid
    /// * `message` - Human-readable message
    /// * `issue` - Optional issue identifier
    ///
    /// # Returns
    ///
    /// A new IniCheckResult instance.
    pub fn new(
        ini_name: impl Into<String>,
        exists: bool,
        is_valid: bool,
        message: impl Into<String>,
        issue: Option<String>,
    ) -> Self {
        Self {
            ini_name: ini_name.into(),
            exists,
            is_valid,
            message: message.into(),
            issue,
        }
    }

    /// Check if this result indicates a problem.
    ///
    /// # Returns
    ///
    /// `true` if there's an issue, `false` otherwise.
    pub fn has_issue(&self) -> bool {
        self.issue.is_some()
    }
}

/// Documents configuration checker.
///
/// This checker validates documents folder configuration and INI files
/// in a read-only manner, reporting issues without modifying any files.
///
/// # Examples
///
/// ```rust
/// use classic_path_core::DocumentsChecker;
///
/// let checker = DocumentsChecker::new("Fallout4");
/// assert_eq!(checker.game_name(), "Fallout4");
/// ```
#[derive(Debug, Clone)]
pub struct DocumentsChecker {
    /// Game name (e.g., "Fallout4", "Skyrim")
    game_name: String,
}

impl DocumentsChecker {
    /// Create a new DocumentsChecker.
    ///
    /// # Arguments
    ///
    /// * `game_name` - Name of the game (e.g., "Fallout4")
    ///
    /// # Returns
    ///
    /// A new DocumentsChecker instance.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_path_core::DocumentsChecker;
    ///
    /// let checker = DocumentsChecker::new("Fallout4");
    /// ```
    pub fn new(game_name: impl Into<String>) -> Self {
        Self {
            game_name: game_name.into(),
        }
    }

    /// Check if OneDrive is detected in the documents path.
    ///
    /// Returns a warning message if "onedrive" is found in the path string.
    ///
    /// # Arguments
    ///
    /// * `docs_path` - The documents folder path to check
    ///
    /// # Returns
    ///
    /// `Some(warning_message)` if OneDrive is detected, `None` otherwise.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_path_core::DocumentsChecker;
    /// use std::path::Path;
    ///
    /// let checker = DocumentsChecker::new("Fallout4");
    ///
    /// let normal_path = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
    /// assert!(checker.check_onedrive_in_path(normal_path).is_none());
    ///
    /// let onedrive_path = Path::new("C:\\Users\\Name\\OneDrive\\Documents\\My Games\\Fallout4");
    /// assert!(checker.check_onedrive_in_path(onedrive_path).is_some());
    /// ```
    pub fn check_onedrive_in_path(&self, docs_path: &Path) -> Option<String> {
        let path_str = docs_path.to_string_lossy().to_lowercase();

        if path_str.contains("onedrive") {
            Some(format!(
                "⚠️ WARNING: OneDrive detected in documents path.\n\
                 OneDrive sync may interfere with game files and cause issues.\n\
                 Path: {}\n\
                 -----",
                docs_path.display()
            ))
        } else {
            None
        }
    }

    /// Validate an INI file in the documents folder.
    ///
    /// This method checks:
    /// 1. If the INI file exists
    /// 2. If it's parseable
    /// 3. For Custom.ini files, if the [Archive] section exists
    ///
    /// # Arguments
    ///
    /// * `docs_path` - The documents folder path
    /// * `ini_name` - Name of the INI file (e.g., "Fallout4.ini")
    ///
    /// # Returns
    ///
    /// An `IniCheckResult` containing the validation status.
    ///
    /// # Errors
    ///
    /// Returns error if there are I/O issues (not for missing/invalid files).
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::DocumentsChecker;
    /// use std::path::Path;
    ///
    /// let checker = DocumentsChecker::new("Fallout4");
    /// let docs_path = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
    ///
    /// match checker.validate_ini_file(docs_path, "Fallout4.ini") {
    ///     Ok(result) => {
    ///         if result.has_issue() {
    ///             println!("Issue: {:?}", result.issue);
    ///         }
    ///     }
    ///     Err(e) => eprintln!("Error: {}", e),
    /// }
    /// ```
    pub fn validate_ini_file(
        &self,
        docs_path: &Path,
        ini_name: &str,
    ) -> DocsPathResult<IniCheckResult> {
        let ini_path = docs_path.join(ini_name);

        // Check if file exists
        if !ini_path.exists() {
            return Ok(self.handle_missing_ini(ini_name));
        }

        // Try to parse the INI file
        match IniFile::load(&ini_path) {
            Ok(ini_file) => Ok(self.check_existing_ini(&ini_file, ini_name)),
            Err(e) => Ok(IniCheckResult::new(
                ini_name,
                true,
                false,
                format!(
                    "❌ CAUTION: {} file appears to be corrupted.\n\
                     Error: {}\n\
                     Consider deleting and regenerating this file.\n\
                     -----",
                    ini_name, e
                ),
                Some("corrupted".to_string()),
            )),
        }
    }

    /// Check an existing INI file.
    ///
    /// # Arguments
    ///
    /// * `ini_file` - The parsed INI file
    /// * `ini_name` - Name of the INI file
    ///
    /// # Returns
    ///
    /// An `IniCheckResult` with the validation status.
    fn check_existing_ini(&self, ini_file: &IniFile, ini_name: &str) -> IniCheckResult {
        // Base success message
        let mut message = format!(
            "✔️ No obvious corruption detected in {}, file seems OK!\n\
             -----",
            ini_name
        );

        let mut issue = None;

        // Special check for Custom.ini files
        if ini_name.to_lowercase() == format!("{}custom.ini", self.game_name.to_lowercase()) {
            if !ini_file.has_section("Archive") {
                message = format!(
                    "❌ WARNING: Archive Invalidation / Loose Files setting is not enabled.\n\
                     The [Archive] section is missing in {}Custom.ini.\n\
                     This setting is required for mods to work properly.\n\
                     -----",
                    self.game_name
                );
                issue = Some("missing_archive_section".to_string());
            } else {
                message = "✔️ Archive Invalidation / Loose Files setting is enabled!\n\
                     -----"
                    .to_string();
            }
        }

        IniCheckResult::new(ini_name, true, true, message, issue)
    }

    /// Handle a missing INI file.
    ///
    /// # Arguments
    ///
    /// * `ini_name` - Name of the missing INI file
    ///
    /// # Returns
    ///
    /// An `IniCheckResult` with information about the missing file.
    fn handle_missing_ini(&self, ini_name: &str) -> IniCheckResult {
        let ini_lower = ini_name.to_lowercase();
        let game_lower = self.game_name.to_lowercase();

        if ini_lower == format!("{}.ini", game_lower) {
            IniCheckResult::new(
                ini_name,
                false,
                false,
                format!(
                    "❌ CAUTION: {} file is missing from your documents folder!\n\
                     You need to run the game at least once with {}Launcher.exe.\n\
                     This will create files and INI settings required for the game to run.\n\
                     -----",
                    ini_name, self.game_name
                ),
                Some("missing".to_string()),
            )
        } else if ini_lower == format!("{}custom.ini", game_lower) {
            IniCheckResult::new(
                ini_name,
                false,
                false,
                format!(
                    "❌ WARNING: {}Custom.ini is missing.\n\
                     Archive Invalidation / Loose Files setting is not enabled.\n\
                     This setting is required for mods to work properly.\n\
                     -----",
                    self.game_name
                ),
                Some("missing".to_string()),
            )
        } else {
            IniCheckResult::new(
                ini_name,
                false,
                false,
                format!(
                    "❌ CAUTION: {} file is missing from your documents folder!\n\
                     -----",
                    ini_name
                ),
                Some("missing".to_string()),
            )
        }
    }

    /// Run all document checks for the game.
    ///
    /// This performs:
    /// 1. OneDrive detection check
    /// 2. Validation of main game INI
    /// 3. Validation of Custom INI
    /// 4. Validation of Prefs INI
    ///
    /// # Arguments
    ///
    /// * `docs_path` - The documents folder path
    ///
    /// # Returns
    ///
    /// A vector of check result messages (only non-empty results).
    ///
    /// # Errors
    ///
    /// Returns error if there are I/O issues.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_path_core::DocumentsChecker;
    /// use std::path::Path;
    ///
    /// let checker = DocumentsChecker::new("Fallout4");
    /// let docs_path = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
    ///
    /// match checker.run_all_checks(docs_path) {
    ///     Ok(messages) => {
    ///         for msg in messages {
    ///             println!("{}", msg);
    ///         }
    ///     }
    ///     Err(e) => eprintln!("Error: {}", e),
    /// }
    /// ```
    pub fn run_all_checks(&self, docs_path: &Path) -> DocsPathResult<Vec<String>> {
        let mut messages = Vec::new();

        // Check for OneDrive
        if let Some(onedrive_warning) = self.check_onedrive_in_path(docs_path) {
            messages.push(onedrive_warning);
        }

        // Validate main INI
        let main_ini = format!("{}.ini", self.game_name);
        if let Ok(result) = self.validate_ini_file(docs_path, &main_ini) {
            if !result.message.is_empty() {
                messages.push(result.message);
            }
        }

        // Validate Custom INI
        let custom_ini = format!("{}Custom.ini", self.game_name);
        if let Ok(result) = self.validate_ini_file(docs_path, &custom_ini) {
            if !result.message.is_empty() {
                messages.push(result.message);
            }
        }

        // Validate Prefs INI
        let prefs_ini = format!("{}Prefs.ini", self.game_name);
        if let Ok(result) = self.validate_ini_file(docs_path, &prefs_ini) {
            if !result.message.is_empty() {
                messages.push(result.message);
            }
        }

        Ok(messages)
    }

    /// Get the game name.
    ///
    /// # Returns
    ///
    /// The game name string.
    pub fn game_name(&self) -> &str {
        &self.game_name
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn create_test_docs(temp_dir: &Path, game_name: &str) -> std::path::PathBuf {
        let docs_path = temp_dir.join("My Games").join(game_name);
        fs::create_dir_all(&docs_path).unwrap();
        docs_path
    }

    fn create_test_ini(docs_path: &Path, ini_name: &str, content: &str) {
        let ini_path = docs_path.join(ini_name);
        fs::write(&ini_path, content).unwrap();
    }

    #[test]
    fn test_new() {
        let checker = DocumentsChecker::new("Fallout4");
        assert_eq!(checker.game_name(), "Fallout4");
    }

    #[test]
    fn test_check_onedrive_not_present() {
        let checker = DocumentsChecker::new("Fallout4");
        let path = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
        assert!(checker.check_onedrive_in_path(path).is_none());
    }

    #[test]
    fn test_check_onedrive_present() {
        let checker = DocumentsChecker::new("Fallout4");
        let path = Path::new("C:\\Users\\Name\\OneDrive\\Documents\\My Games\\Fallout4");
        let warning = checker.check_onedrive_in_path(path);
        assert!(warning.is_some());
        assert!(warning.unwrap().contains("OneDrive"));
    }

    #[test]
    fn test_validate_ini_file_missing() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs(temp_dir.path(), "Fallout4");

        let checker = DocumentsChecker::new("Fallout4");
        let result = checker
            .validate_ini_file(&docs_path, "Fallout4.ini")
            .unwrap();

        assert!(!result.exists);
        assert!(!result.is_valid);
        assert!(result.has_issue());
        assert_eq!(result.issue, Some("missing".to_string()));
    }

    #[test]
    fn test_validate_ini_file_exists_valid() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
        create_test_ini(&docs_path, "Fallout4.ini", "[General]\nkey=value\n");

        let checker = DocumentsChecker::new("Fallout4");
        let result = checker
            .validate_ini_file(&docs_path, "Fallout4.ini")
            .unwrap();

        assert!(result.exists);
        assert!(result.is_valid);
        assert!(!result.has_issue());
        assert!(result.message.contains("✔️"));
    }

    #[test]
    fn test_validate_ini_file_corrupted() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
        // Create invalid INI with malformed section header
        create_test_ini(&docs_path, "Fallout4.ini", "[General\nkey=value\n");

        let checker = DocumentsChecker::new("Fallout4");
        let result = checker
            .validate_ini_file(&docs_path, "Fallout4.ini")
            .unwrap();

        assert!(result.exists);
        assert!(!result.is_valid);
        assert!(result.has_issue());
        assert_eq!(result.issue, Some("corrupted".to_string()));
    }

    #[test]
    fn test_validate_custom_ini_missing_archive() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
        create_test_ini(&docs_path, "Fallout4Custom.ini", "[General]\nkey=value\n");

        let checker = DocumentsChecker::new("Fallout4");
        let result = checker
            .validate_ini_file(&docs_path, "Fallout4Custom.ini")
            .unwrap();

        assert!(result.exists);
        assert!(result.is_valid);
        assert!(result.has_issue());
        assert_eq!(result.issue, Some("missing_archive_section".to_string()));
        assert!(result.message.contains("Archive Invalidation"));
    }

    #[test]
    fn test_validate_custom_ini_has_archive() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
        create_test_ini(
            &docs_path,
            "Fallout4Custom.ini",
            "[Archive]\nbInvalidateOlderFiles=1\n",
        );

        let checker = DocumentsChecker::new("Fallout4");
        let result = checker
            .validate_ini_file(&docs_path, "Fallout4Custom.ini")
            .unwrap();

        assert!(result.exists);
        assert!(result.is_valid);
        assert!(!result.has_issue());
        assert!(result.message.contains("enabled"));
    }

    #[test]
    fn test_run_all_checks() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
        create_test_ini(&docs_path, "Fallout4.ini", "[General]\nkey=value\n");
        create_test_ini(
            &docs_path,
            "Fallout4Custom.ini",
            "[Archive]\nbInvalidateOlderFiles=1\n",
        );
        create_test_ini(&docs_path, "Fallout4Prefs.ini", "[Display]\niSize W=1920\n");

        let checker = DocumentsChecker::new("Fallout4");
        let messages = checker.run_all_checks(&docs_path).unwrap();

        // Should have 3 messages (all OK)
        assert_eq!(messages.len(), 3);
        assert!(
            messages
                .iter()
                .all(|m| m.contains("✔️") || m.contains("enabled"))
        );
    }

    #[test]
    fn test_run_all_checks_with_issues() {
        let temp_dir = TempDir::new().unwrap();
        let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
        // Only create main INI, missing Custom and Prefs

        create_test_ini(&docs_path, "Fallout4.ini", "[General]\nkey=value\n");

        let checker = DocumentsChecker::new("Fallout4");
        let messages = checker.run_all_checks(&docs_path).unwrap();

        // Should have 3 messages (1 OK, 2 missing)
        assert_eq!(messages.len(), 3);
        assert!(messages[0].contains("✔️")); // Main INI OK
        assert!(messages[1].contains("❌")); // Custom INI missing
        assert!(messages[2].contains("❌")); // Prefs INI missing
    }
}
