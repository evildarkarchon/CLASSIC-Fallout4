//! FCX Mode Handler - Read-only FCX mode state management and message generation
//!
//! This module handles FCX (File Check eXtended) mode operations:
//! - Managing FCX mode enabled/disabled state
//! - Generating appropriate FCX mode messages
//! - Collecting file check results (delegated to Python for complex imports)
//!
//! **Important**: FCX mode operates in read-only mode - it detects configuration issues
//! but does not modify any files. All detected issues are reported with recommendations
//! for manual fixes.

use crate::report::ReportFragment;
use parking_lot::Mutex;
use std::sync::LazyLock;
use thiserror::Error;

/// Global FCX mode handler for shared state across scan sessions
///
/// This static provides session-wide caching for FCX mode checks, enabling
/// run-once optimization for batch scanning (10x performance improvement).
///
/// Call `FcxModeHandler::reset_global_state()` at the start of each scan session
/// to clear cached results.
pub static GLOBAL_FCX_HANDLER: LazyLock<Mutex<FcxModeHandler>> =
    LazyLock::new(|| Mutex::new(FcxModeHandler::new(false)));

/// Typed outcome for resetting the global FCX handler state.
#[derive(Clone, Debug, Error, Eq, PartialEq)]
pub enum FcxResetError {
    /// The global handler was already clean, so no reset work was needed.
    #[error("FCX global state reset was unnecessary")]
    Unnecessary,

    /// Reserved binding-visible failure path for future reset precondition errors.
    #[error("FCX global state reset failed: {0}")]
    Failed(&'static str),
}

/// Configuration issue detected by FCX mode
#[derive(Clone, Debug)]
pub struct ConfigIssue {
    /// Path to the configuration file
    pub file_path: String,

    /// INI section name (None for TOML or non-sectioned files)
    pub section: Option<String>,

    /// Setting/key name
    pub setting: String,

    /// Current value in the file
    pub current_value: String,

    /// Recommended value to fix the issue
    pub recommended_value: String,

    /// Human-readable description of the issue
    pub description: String,

    /// Issue severity level ("error", "warning", "info")
    pub severity: String,
}

impl ConfigIssue {
    /// Create a new configuration issue
    pub fn new(
        file_path: String,
        section: Option<String>,
        setting: String,
        current_value: String,
        recommended_value: String,
        description: String,
        severity: String,
    ) -> Self {
        Self {
            file_path,
            section,
            setting,
            current_value,
            recommended_value,
            description,
            severity,
        }
    }

    /// Format issue as human-readable report section
    pub fn format_report(&self) -> String {
        let icon = match self.severity.as_str() {
            "error" => "❌",
            "warning" => "⚠️",
            "info" => "ℹ️",
            _ => "⚠️",
        };

        let section_str = self
            .section
            .as_ref()
            .map(|s| format!("[{}]", s))
            .unwrap_or_else(|| "N/A".to_string());

        format!(
            "{} DETECTED ISSUE: {}\n   File: {}\n   Section: {}\n   Setting: {}\n   Current Value: {}\n   Recommended Value: {}\n\n",
            icon,
            self.description,
            self.file_path,
            section_str,
            self.setting,
            self.current_value,
            self.recommended_value
        )
    }
}

/// FCX Mode Handler for managing file check operations (read-only)
#[derive(Clone, Debug)]
pub struct FcxModeHandler {
    /// Whether FCX mode is enabled
    pub fcx_mode: bool,

    /// Main files check result (from Python)
    pub main_files_check: Option<String>,

    /// Game files check result (from Python)
    pub game_files_check: Option<String>,

    /// Detected configuration issues (read-only detection)
    pub detected_issues: Vec<ConfigIssue>,

    /// Flag indicating whether FCX checks have been run in this session
    ///
    /// This enables run-once caching for batch scanning performance.
    /// When true, subsequent check_fcx_mode() calls reuse cached results
    /// instead of re-running expensive operations (INI parsing, registry reads, etc.).
    ///
    /// Reset via reset() method between scan sessions.
    pub checks_run: bool,
}

impl FcxModeHandler {
    /// Create a new FCX Mode Handler
    ///
    /// # Arguments
    ///
    /// * `fcx_mode` - Whether FCX mode should be enabled (true) or disabled (false)
    ///
    /// # Returns
    ///
    /// A new `FcxModeHandler` instance with the specified FCX mode state and empty check results
    ///
    /// # Example
    ///
    /// ```
    /// use classic_scanlog_core::FcxModeHandler;
    ///
    /// // Create handler with FCX mode enabled
    /// let handler = FcxModeHandler::new(true);
    ///
    /// // Create handler with FCX mode disabled  
    /// let handler = FcxModeHandler::new(false);
    /// ```
    pub fn new(fcx_mode: bool) -> Self {
        Self {
            fcx_mode,
            main_files_check: None,
            game_files_check: None,
            detected_issues: Vec::new(),
            checks_run: false,
        }
    }

    /// Set main files check result (called from Python after running checks)
    ///
    /// Args:
    ///     result: Main files check result string
    pub fn set_main_files_result(&mut self, result: String) {
        self.main_files_check = Some(result);
    }

    /// Set game files check result (called from Python after running checks)
    ///
    /// Args:
    ///     result: Game files check result string
    pub fn set_game_files_result(&mut self, result: String) {
        self.game_files_check = Some(result);
    }

    /// Add a detected configuration issue
    ///
    /// Args:
    ///     issue: ConfigIssue to add to the detected issues list
    pub fn add_issue(&mut self, issue: ConfigIssue) {
        self.detected_issues.push(issue);
    }

    /// Set detected configuration issues (replaces existing list)
    ///
    /// Args:
    ///     issues: Vector of ConfigIssue objects
    pub fn set_detected_issues(&mut self, issues: Vec<ConfigIssue>) {
        self.detected_issues = issues;
    }

    /// Get reference to detected issues
    ///
    /// Returns:
    ///     Reference to the vector of detected issues
    pub fn get_detected_issues(&self) -> &[ConfigIssue] {
        &self.detected_issues
    }

    /// Generate FCX mode messages based on current state
    ///
    /// Returns:
    ///     ReportFragment containing FCX mode messages
    pub fn get_fcx_messages(&self) -> ReportFragment {
        let mut lines = Vec::new();

        if self.fcx_mode {
            lines.push("* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION * \n\n".to_string());
            lines.push("[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ] \n\n".to_string());

            // Add main files check if available
            if let Some(ref main_check) = self.main_files_check
                && !main_check.is_empty()
            {
                lines.push(main_check.clone());
            }

            // Add game files check if available
            if let Some(ref game_check) = self.game_files_check
                && !game_check.is_empty()
            {
                lines.push(game_check.clone());
            }

            // Add detected configuration issues section if any issues were found
            if !self.detected_issues.is_empty() {
                lines.push("\n--- DETECTED CONFIGURATION ISSUES ---\n\n".to_string());
                for issue in &self.detected_issues {
                    lines.push(issue.format_report());
                }
            }
        }

        ReportFragment::from_lines(lines)
    }

    /// Get FCX mode enabled message only (for quick checks)
    ///
    /// Returns:
    ///     String with FCX mode status message
    pub fn get_fcx_status_message(&self) -> String {
        if self.fcx_mode {
            "FCX Mode: ENABLED".to_string()
        } else {
            "FCX Mode: DISABLED".to_string()
        }
    }

    /// Check if FCX mode has any results to display
    ///
    /// Returns:
    ///     True if there are check results available
    pub fn has_results(&self) -> bool {
        if !self.fcx_mode {
            return false;
        }

        self.main_files_check
            .as_ref()
            .is_some_and(|s| !s.is_empty())
            || self
                .game_files_check
                .as_ref()
                .is_some_and(|s| !s.is_empty())
    }

    fn needs_reset(&self) -> bool {
        self.main_files_check.is_some()
            || self.game_files_check.is_some()
            || !self.detected_issues.is_empty()
            || self.checks_run
    }

    /// Reset all FCX check results (for new scan session)
    pub fn reset(&mut self) {
        self.main_files_check = None;
        self.game_files_check = None;
        self.detected_issues.clear();
        self.checks_run = false;
    }

    /// Reset the global FCX handler state (class method for Python compatibility).
    ///
    /// This method provides a way to reset the shared global FCX handler state
    /// between scan sessions, ensuring clean state for each new analysis run.
    /// It's designed to be called as a class method from Python via PyO3.
    ///
    /// # Example
    ///
    /// ```
    /// use classic_scanlog_core::FcxModeHandler;
    ///
    /// // Reset global state before starting a new scan
    /// let _ = FcxModeHandler::reset_global_state();
    /// ```
    ///
    /// # Thread Safety
    ///
    /// This method is thread-safe and can be called from multiple threads
    /// without risk of data races. It uses a mutex-protected global state.
    pub fn reset_global_state() -> Result<(), FcxResetError> {
        let mut handler = GLOBAL_FCX_HANDLER.lock();

        if !handler.needs_reset() {
            return Err(FcxResetError::Unnecessary);
        }

        handler.reset();
        Ok(())
    }

    /// Create a disabled FCX handler (convenience constructor)
    pub fn disabled() -> Self {
        Self {
            fcx_mode: false,
            main_files_check: None,
            game_files_check: None,
            detected_issues: Vec::new(),
            checks_run: false,
        }
    }

    /// Create an enabled FCX handler (convenience constructor)
    pub fn enabled() -> Self {
        Self {
            fcx_mode: true,
            main_files_check: None,
            game_files_check: None,
            detected_issues: Vec::new(),
            checks_run: false,
        }
    }
}

#[cfg(test)]
#[path = "fcx_handler_tests.rs"]
mod tests;
