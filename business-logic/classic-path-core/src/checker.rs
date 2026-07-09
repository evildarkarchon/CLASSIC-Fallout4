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

/// Structured state for one documents-folder check message.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DocumentsCheckState {
    /// The documents-folder expectation passed.
    Passed,
    /// The expectation produced a non-blocking warning.
    Warning,
    /// The expectation failed and should be surfaced as a setup issue.
    Failed,
}

impl DocumentsCheckState {
    /// Return the stable adapter-facing state identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Passed => "passed",
            Self::Warning => "warning",
            Self::Failed => "failed",
        }
    }
}

/// Rendered documents-folder check message paired with structured state.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentsCheckResult {
    /// Structured state for the rendered message.
    pub state: DocumentsCheckState,
    /// Human-readable message describing the check result.
    pub message: String,
}

impl DocumentsCheckResult {
    /// Create a documents check result with an explicit state and message.
    #[must_use]
    pub fn new(state: DocumentsCheckState, message: impl Into<String>) -> Self {
        Self {
            state,
            message: message.into(),
        }
    }
}

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

    /// Return the setup-facing state represented by this INI check.
    ///
    /// Missing, corrupted, and incomplete INI files are represented by
    /// `issue`, while parsed INIs without an issue are considered passed.
    #[must_use]
    pub fn state(&self) -> DocumentsCheckState {
        if self.has_issue() {
            DocumentsCheckState::Failed
        } else {
            DocumentsCheckState::Passed
        }
    }
}

impl From<IniCheckResult> for DocumentsCheckResult {
    fn from(result: IniCheckResult) -> Self {
        Self::new(result.state(), result.message)
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
        self.check_onedrive_in_path_result(docs_path)
            .map(|result| result.message)
    }

    /// Check if OneDrive is detected and return a structured warning result.
    ///
    /// Returns `Some` only when "onedrive" is found in the path string. The
    /// result state is always [`DocumentsCheckState::Warning`] because this
    /// condition is advisory rather than a hard validation failure.
    #[must_use]
    pub fn check_onedrive_in_path_result(&self, docs_path: &Path) -> Option<DocumentsCheckResult> {
        let path_str = docs_path.to_string_lossy().to_lowercase();

        if path_str.contains("onedrive") {
            Some(DocumentsCheckResult::new(
                DocumentsCheckState::Warning,
                format!(
                    "⚠️ WARNING: OneDrive detected in documents path.\n\
                 OneDrive sync may interfere with game files and cause issues.\n\
                 Path: {}\n\
                 -----",
                    docs_path.display()
                ),
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
    /// 3. For Custom.ini files, if the `[Archive]` section exists
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
    /// A vector of structured check results (only non-empty messages).
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
    /// match checker.run_all_check_results(docs_path) {
    ///     Ok(results) => {
    ///         for result in results {
    ///             println!("{}: {}", result.state.as_str(), result.message);
    ///         }
    ///     }
    ///     Err(e) => eprintln!("Error: {}", e),
    /// }
    /// ```
    pub fn run_all_check_results(
        &self,
        docs_path: &Path,
    ) -> DocsPathResult<Vec<DocumentsCheckResult>> {
        let mut results = Vec::new();

        // Check for OneDrive
        if let Some(onedrive_warning) = self.check_onedrive_in_path_result(docs_path) {
            results.push(onedrive_warning);
        }

        // Validate main INI
        let main_ini = format!("{}.ini", self.game_name);
        if let Ok(result) = self.validate_ini_file(docs_path, &main_ini)
            && !result.message.is_empty()
        {
            results.push(result.into());
        }

        // Validate Custom INI
        let custom_ini = format!("{}Custom.ini", self.game_name);
        if let Ok(result) = self.validate_ini_file(docs_path, &custom_ini)
            && !result.message.is_empty()
        {
            results.push(result.into());
        }

        // Validate Prefs INI
        let prefs_ini = format!("{}Prefs.ini", self.game_name);
        if let Ok(result) = self.validate_ini_file(docs_path, &prefs_ini)
            && !result.message.is_empty()
        {
            results.push(result.into());
        }

        Ok(results)
    }

    /// Run all document checks and return rendered messages.
    ///
    /// This compatibility wrapper preserves the historical `Vec<String>` API.
    /// Call [`Self::run_all_check_results`] when the caller needs structured
    /// pass/warning/failure state without parsing the rendered text.
    pub fn run_all_checks(&self, docs_path: &Path) -> DocsPathResult<Vec<String>> {
        Ok(self
            .run_all_check_results(docs_path)?
            .into_iter()
            .map(|result| result.message)
            .collect())
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
#[path = "checker_tests.rs"]
mod tests;
