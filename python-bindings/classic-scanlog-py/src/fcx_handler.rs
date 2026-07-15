//! Python bindings for FcxModeHandler - Thin wrapper over classic-scanlog-core

use crate::FcxResetError as PyFcxResetError;
use classic_scangame_core::{GameSetupIntake, detect_config_issues};
use classic_scanlog_core::{ConfigIssue, FcxModeHandler, FcxResetError};
use classic_user_settings_core::UserSettings;
use parking_lot::Mutex;
use pyo3::prelude::*;
use pyo3::types::PyType;
use std::path::PathBuf;
use std::sync::LazyLock;

/// Binding-owned FCX result cache keyed by the explicit CLASSIC root.
///
/// The core global handler can also be updated by non-Python scan-run paths, so
/// keeping the root and handler together prevents unrelated core state from being
/// mistaken for this binding's root-scoped cache entry.
static FCX_CACHE: LazyLock<Mutex<Option<(PathBuf, FcxModeHandler)>>> =
    LazyLock::new(|| Mutex::new(None));

fn to_scanlog_issue(issue: classic_scangame_core::ConfigIssue) -> ConfigIssue {
    ConfigIssue::new(
        issue.file_path.display().to_string(),
        Some(issue.section),
        issue.setting,
        issue.current_value,
        issue.recommended_value,
        issue.description,
        match issue.severity {
            classic_scangame_core::IssueSeverity::Error => "error",
            classic_scangame_core::IssueSeverity::Warning => "warning",
            classic_scangame_core::IssueSeverity::Info => "info",
        }
        .to_string(),
    )
}

fn format_detected_issues(issues: &[ConfigIssue]) -> String {
    issues.iter().map(ConfigIssue::format_report).collect()
}

/// Python wrapper for ConfigIssue
#[pyclass(name = "ConfigIssue", from_py_object)]
#[derive(Clone)]
pub struct PyConfigIssue {
    inner: ConfigIssue,
}

#[pymethods]
impl PyConfigIssue {
    /// Create a new configuration issue
    #[new]
    #[pyo3(signature = (file_path, section, setting, current_value, recommended_value, description, severity = "warning".to_string()))]
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
            inner: ConfigIssue::new(
                file_path,
                section,
                setting,
                current_value,
                recommended_value,
                description,
                severity,
            ),
        }
    }

    /// Path to the configuration file
    #[getter]
    pub fn file_path(&self) -> String {
        self.inner.file_path.clone()
    }

    /// INI section name (None for TOML or non-sectioned files)
    #[getter]
    pub fn section(&self) -> Option<String> {
        self.inner.section.clone()
    }

    /// Setting/key name
    #[getter]
    pub fn setting(&self) -> String {
        self.inner.setting.clone()
    }

    /// Current value in the file
    #[getter]
    pub fn current_value(&self) -> String {
        self.inner.current_value.clone()
    }

    /// Recommended value to fix the issue
    #[getter]
    pub fn recommended_value(&self) -> String {
        self.inner.recommended_value.clone()
    }

    /// Human-readable description of the issue
    #[getter]
    pub fn description(&self) -> String {
        self.inner.description.clone()
    }

    /// Issue severity level ("error", "warning", "info")
    #[getter]
    pub fn severity(&self) -> String {
        self.inner.severity.clone()
    }

    /// Format issue as human-readable report section
    pub fn format_report(&self) -> String {
        self.inner.format_report()
    }

    /// String representation
    pub fn __repr__(&self) -> String {
        format!(
            "ConfigIssue(file='{}', section={:?}, setting='{}', current='{}', recommended='{}')",
            self.inner.file_path,
            self.inner.section,
            self.inner.setting,
            self.inner.current_value,
            self.inner.recommended_value
        )
    }
}

impl From<ConfigIssue> for PyConfigIssue {
    fn from(issue: ConfigIssue) -> Self {
        Self { inner: issue }
    }
}

/// Python wrapper for FcxModeHandler
#[pyclass(name = "FcxModeHandler")]
pub struct PyFcxModeHandler {
    inner: FcxModeHandler,
}

#[pymethods]
impl PyFcxModeHandler {
    /// Create a new instance

    #[new]
    pub fn new(fcx_mode: bool) -> Self {
        Self {
            inner: FcxModeHandler::new(fcx_mode),
        }
    }

    /// Check and update FCX mode state using Rust core checks.
    ///
    /// Uses a binding-owned, root-and-mode-keyed cache for batch scanning performance.
    /// Matching checks reuse the retained handler instead of re-running expensive
    /// operations such as INI parsing and path inspection.
    ///
    /// `classic_root` is explicit so FCX preparation never consults an implicit
    /// application directory or interprets the retired flat configuration schema.
    pub fn check_fcx_mode(&mut self, _py: Python<'_>, classic_root: String) -> PyResult<()> {
        let classic_root = PathBuf::from(classic_root);
        let mut cache = FCX_CACHE.lock();
        if let Some((cache_root, cached_handler)) = cache.as_ref()
            && cache_root == &classic_root
            && cached_handler.fcx_mode == self.inner.fcx_mode
        {
            self.inner = cached_handler.clone();
            return Ok(());
        }

        // Keep the core singleton synchronized for non-Python FCX consumers.
        use classic_scanlog_core::GLOBAL_FCX_HANDLER;
        let mut global_handler = GLOBAL_FCX_HANDLER.lock();

        if !self.inner.fcx_mode {
            // FCX mode is off; leave report output empty but mark the session checked.
            self.inner.set_main_files_result(String::new());
            self.inner.set_game_files_result(String::new());

            // Mark as run even when disabled (don't re-run for each log)
            global_handler.checks_run = true;
            global_handler.fcx_mode = false;
            global_handler.set_main_files_result(String::new());
            global_handler.set_game_files_result(String::new());
            *cache = Some((classic_root, self.inner.clone()));

            return Ok(());
        }

        let user_settings = UserSettings::open(&classic_root);
        let intake = GameSetupIntake::from_user_settings(user_settings.game_setup_settings());
        let game_id = intake.game_id;
        let setup = intake.run();
        let game_root = setup.paths.game_root.clone();
        let main_result = setup.rendered_report;
        self.inner.set_main_files_result(main_result);

        let rust_issues: Vec<ConfigIssue> = game_root
            .as_deref()
            .map(|game_root| {
                detect_config_issues(game_root, game_id.as_str())
                    .into_iter()
                    .map(to_scanlog_issue)
                    .collect()
            })
            .unwrap_or_default();
        let game_result = format_detected_issues(&rust_issues);

        self.inner.set_game_files_result(game_result);
        self.inner.set_detected_issues(rust_issues.clone());

        // Publish the completed result to the core singleton for other consumers.
        global_handler.checks_run = true;
        global_handler.fcx_mode = self.inner.fcx_mode;
        global_handler
            .set_main_files_result(self.inner.main_files_check.clone().unwrap_or_default());
        global_handler
            .set_game_files_result(self.inner.game_files_check.clone().unwrap_or_default());
        global_handler.set_detected_issues(rust_issues);
        *cache = Some((classic_root, self.inner.clone()));

        Ok(())
    }

    /// Set main files check result
    pub fn set_main_files_result(&mut self, result: String) {
        self.inner.set_main_files_result(result);
    }

    /// Set game files check result
    pub fn set_game_files_result(&mut self, result: String) {
        self.inner.set_game_files_result(result);
    }

    /// Generate FCX mode messages
    pub fn get_fcx_messages(&self) -> Vec<String> {
        self.inner.get_fcx_messages().to_list()
    }

    /// Get FCX mode status message
    pub fn get_fcx_status_message(&self) -> String {
        self.inner.get_fcx_status_message()
    }

    /// Check if FCX mode has any results to display
    pub fn has_results(&self) -> bool {
        self.inner.has_results()
    }

    /// Get FCX mode enabled state
    #[getter]
    pub fn fcx_mode(&self) -> bool {
        self.inner.fcx_mode
    }

    /// Set FCX mode enabled state
    #[setter]
    pub fn set_fcx_mode(&mut self, value: bool) {
        self.inner.fcx_mode = value;
    }

    /// Add a detected configuration issue
    pub fn add_issue(&mut self, issue: PyConfigIssue) {
        self.inner.add_issue(issue.inner.clone());
    }

    /// Set detected configuration issues (replaces existing list)
    pub fn set_detected_issues(&mut self, issues: Vec<PyConfigIssue>) {
        let rust_issues: Vec<ConfigIssue> =
            issues.into_iter().map(|py_issue| py_issue.inner).collect();
        self.inner.set_detected_issues(rust_issues);
    }

    /// Get detected configuration issues
    pub fn get_detected_issues(&self) -> Vec<PyConfigIssue> {
        self.inner
            .get_detected_issues()
            .iter()
            .cloned()
            .map(PyConfigIssue::from)
            .collect()
    }

    /// Reset all FCX check results
    pub fn reset(&mut self) {
        self.inner.reset();
    }

    /// Reset the global FCX handler state (class method).
    ///
    /// This class method resets the shared global FCX handler state
    /// between scan sessions. It's designed to match the Python API
    /// where FCXModeHandler.reset_fcx_checks() is called as a class method.
    ///
    /// # Example (Python)
    ///
    /// ```python
    /// from classic_scanlog import FcxModeHandler
    ///
    /// # Reset global FCX state before starting a new scan
    /// FcxModeHandler.reset_fcx_checks()
    /// ```
    #[classmethod]
    fn reset_fcx_checks(_cls: &Bound<'_, PyType>) -> PyResult<()> {
        match FcxModeHandler::reset_global_state() {
            Ok(()) | Err(FcxResetError::Unnecessary) => {
                *FCX_CACHE.lock() = None;
                Ok(())
            }
            Err(error) => Err(PyFcxResetError::new_err(format!(
                "failed to reset FCX global state: {error}"
            ))),
        }
    }
}
