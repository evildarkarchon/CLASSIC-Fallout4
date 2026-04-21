//! Crash Generator Check Orchestrator
//!
//! High-level orchestration layer for Buffout4/crash generator validation.
//! Wraps `CrashgenChecker` (from the `toml` module) with path resolution,
//! plugin detection, and report formatting.
//!
//! Replaces Python `ClassicLib.scanning.game.check_crashgen.check_crashgen_settings()`
//! and the `CrashgenChecker.__init__()` path resolution logic.
//!
//! ## Architecture
//!
//! The orchestrator handles:
//! 1. **Path resolution** - finding the crashgen TOML config from a game plugins directory
//! 2. **Plugin detection** - scanning the DLL directory for installed plugins
//! 3. **Settings validation** - delegating to `CrashgenChecker` for TOML checks
//! 4. **Report generation** - producing a `CrashgenReport` with formatted messages
//!
//! The underlying `CrashgenChecker` does the actual TOML parsing and validation.
//! This orchestrator adds the "find the right files" logic on top.

use std::path::{Path, PathBuf};

use thiserror::Error;

use crate::toml::{CrashgenChecker, TomlConfigIssue};
use classic_config_core::CrashgenSettingsRules;

/// Errors that can occur during crash generator orchestration
#[derive(Debug, Error)]
pub enum CrashgenOrchestratorError {
    /// Plugins directory not found or inaccessible
    #[error("Plugins directory not found: {0}")]
    PluginsDirNotFound(String),

    /// I/O error during file operations
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    /// TOML validation error
    #[error("TOML validation error: {0}")]
    Toml(#[from] crate::toml::TomlError),
}

/// Result type for orchestrator operations
pub type Result<T> = std::result::Result<T, CrashgenOrchestratorError>;

/// Report produced by the crash generator check
#[derive(Debug, Clone)]
pub struct CrashgenReport {
    /// Formatted message string (for display or backward compatibility)
    pub message: String,

    /// Structured list of configuration issues detected
    pub issues: Vec<TomlConfigIssue>,

    /// Name of the crash generator being checked
    pub crashgen_name: String,

    /// Path to the configuration file that was checked (if found)
    pub config_path: Option<PathBuf>,

    /// Set of installed plugin DLL names (lowercase)
    pub installed_plugins: Vec<String>,
}

/// Orchestrator for crash generator (Buffout4) configuration checks
///
/// Encapsulates the full check workflow: locate config files, detect plugins,
/// validate settings, and produce a structured report.
///
/// # Example
///
/// ```rust,no_run
/// use classic_scangame_core::crashgen_orchestrator::CrashgenCheckOrchestrator;
/// use std::path::Path;
///
/// let report = CrashgenCheckOrchestrator::check(
///     Path::new("C:/Games/Fallout4/Data/F4SE/Plugins"),
///     "Buffout4",
/// )?;
/// println!("{}", report.message);
/// for issue in &report.issues {
///     println!("Issue: {} = {} (should be {})", issue.setting, issue.current_value, issue.recommended_value);
/// }
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub struct CrashgenCheckOrchestrator;

impl CrashgenCheckOrchestrator {
    /// Run the full crash generator check
    ///
    /// This is the main entry point that replaces Python's `check_crashgen_settings()`.
    /// It creates a `CrashgenChecker`, runs the check, and wraps the result in a
    /// `CrashgenReport`.
    ///
    /// # Arguments
    ///
    /// * `plugins_path` - Path to the game's plugin directory (e.g., `Data/F4SE/Plugins`)
    /// * `crashgen_name` - Name of the crash generator (e.g., "Buffout4")
    ///
    /// # Returns
    ///
    /// A `CrashgenReport` containing the formatted message and any detected issues
    pub fn check(plugins_path: &Path, crashgen_name: &str) -> Result<CrashgenReport> {
        Self::check_with_rules(plugins_path, crashgen_name, None)
    }

    /// Run the full crash generator check with optional YAML-defined settings rules.
    pub fn check_with_rules(
        plugins_path: &Path,
        crashgen_name: &str,
        settings_rules: Option<CrashgenSettingsRules>,
    ) -> Result<CrashgenReport> {
        let mut checker =
            CrashgenChecker::new_with_rules(plugins_path, crashgen_name, settings_rules);

        let config_path = checker.config_file().cloned();
        let installed_plugins = checker.installed_plugins().to_vec();

        let (message, issues) = checker.check()?;

        Ok(CrashgenReport {
            message,
            issues,
            crashgen_name: crashgen_name.to_string(),
            config_path,
            installed_plugins,
        })
    }

    /// Scan a plugins directory and return the list of installed DLL names (lowercase)
    ///
    /// This is useful for callers that need plugin detection without running the
    /// full TOML validation.
    ///
    /// # Arguments
    ///
    /// * `plugins_path` - Path to scan for DLL files
    ///
    /// # Returns
    ///
    /// Vector of lowercase filenames found in the directory
    pub fn detect_plugins(plugins_path: &Path) -> Result<Vec<String>> {
        let mut plugins = Vec::new();

        if !plugins_path.exists() {
            return Err(CrashgenOrchestratorError::PluginsDirNotFound(
                plugins_path.display().to_string(),
            ));
        }

        let entries = std::fs::read_dir(plugins_path)?;
        for entry in entries.flatten() {
            if let Ok(name) = entry.file_name().into_string() {
                plugins.push(name.to_lowercase());
            }
        }

        Ok(plugins)
    }

    /// Resolve the crashgen TOML config file path from a plugins directory
    ///
    /// Checks for both `Buffout4/config.toml` (OG layout) and `Buffout4.toml`
    /// (VR layout). Returns the path if found, or None if neither exists.
    ///
    /// # Arguments
    ///
    /// * `plugins_path` - Path to the game's plugin directory
    ///
    /// # Returns
    ///
    /// The resolved config file path, or None if not found
    pub fn resolve_config_path(plugins_path: &Path) -> Option<PathBuf> {
        let og_path = plugins_path.join("Buffout4/config.toml");
        let vr_path = plugins_path.join("Buffout4.toml");

        if og_path.is_file() {
            Some(og_path)
        } else if vr_path.is_file() {
            Some(vr_path)
        } else {
            None
        }
    }
}

#[cfg(test)]
#[path = "crashgen_orchestrator_tests.rs"]
mod tests;
