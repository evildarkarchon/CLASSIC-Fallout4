//! Python bindings for FcxModeHandler - Thin wrapper over classic-scanlog-core

use crate::FcxResetError as PyFcxResetError;
use classic_config_core::ClassicConfig;
use classic_constants_core::GameId;
use classic_scangame_core::integrity::IntegrityConfig;
use classic_scangame_core::{SetupCheckConfig, detect_config_issues, run_combined_checks};
use classic_scanlog_core::{ConfigIssue, FcxModeHandler, FcxResetError};
use classic_shared_core::get_runtime;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyType;

fn load_classic_config() -> PyResult<ClassicConfig> {
    get_runtime()
        .block_on(ClassicConfig::load_or_default())
        .map_err(|error| PyRuntimeError::new_err(format!("failed to load CLASSIC config: {error}")))
}

fn infer_game_id(config: &ClassicConfig) -> Option<GameId> {
    let game_root = &config.paths.game_root;
    if !game_root.as_os_str().is_empty() {
        if let Some(game_id) = GameId::all()
            .into_iter()
            .find(|game_id| game_root.join(game_id.exe_name()).exists())
        {
            return Some(game_id);
        }

        if let Some(name) = game_root.file_name().and_then(|name| name.to_str())
            && let Ok(game_id) = name.parse::<GameId>()
        {
            return Some(game_id);
        }
    }

    None
}

fn build_setup_check_config(config: &ClassicConfig, game_id: GameId) -> Option<SetupCheckConfig> {
    if config.paths.game_root.as_os_str().is_empty() {
        return None;
    }

    Some(SetupCheckConfig {
        integrity: IntegrityConfig::new(
            config.paths.game_root.join(game_id.exe_name()),
            Vec::new(),
            game_id.as_str().to_string(),
        ),
        game_name: game_id.as_str().to_string(),
        docs_path: config
            .paths
            .docs_root
            .as_ref()
            .or(config.paths.ini_folder.as_ref())
            .map(|path| path.to_string_lossy().into_owned()),
        xse_hashes: Vec::new(),
    })
}

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
#[pyclass(name = "ConfigIssue")]
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
    /// Uses run-once caching via global singleton for batch scanning performance.
    /// When checks have already been run in this session, cached results are reused
    /// instead of re-running expensive operations (10x speedup for batch scans).
    ///
    /// IMPORTANT: This method assumes game paths have already been generated
    /// via game_generate_paths() before being called. This should be done
    /// in the scan executor or orchestrator initialization.
    pub fn check_fcx_mode(&mut self, _py: Python<'_>) -> PyResult<()> {
        // Use global handler for session-wide caching
        use classic_scanlog_core::GLOBAL_FCX_HANDLER;
        let mut global_handler = GLOBAL_FCX_HANDLER.lock();

        // If checks already run in this session, use cached results
        if global_handler.checks_run {
            // Copy cached results to this instance
            self.inner = global_handler.clone();
            return Ok(());
        }

        if !self.inner.fcx_mode {
            // FCX mode disabled - set default messages
            self.inner.set_main_files_result(
                "❌ FCX Mode is disabled, skipping game files check... \n-----\n".to_string(),
            );
            self.inner.set_game_files_result(String::new());

            // Mark as run even when disabled (don't re-run for each log)
            global_handler.checks_run = true;
            global_handler.fcx_mode = false;
            global_handler.set_main_files_result(
                "❌ FCX Mode is disabled, skipping game files check... \n-----\n".to_string(),
            );
            global_handler.set_game_files_result(String::new());

            return Ok(());
        }

        let config = load_classic_config()?;
        let game_id = infer_game_id(&config).ok_or_else(|| {
            PyRuntimeError::new_err(
                "failed to infer game id from configured game root; run path detection first",
            )
        })?;

        let main_result = build_setup_check_config(&config, game_id)
            .map(|setup_config| run_combined_checks(&setup_config).combined())
            .unwrap_or_default();
        self.inner.set_main_files_result(main_result);

        let rust_issues: Vec<ConfigIssue> = if config.paths.game_root.as_os_str().is_empty() {
            Vec::new()
        } else {
            detect_config_issues(&config.paths.game_root, game_id.as_str())
                .into_iter()
                .map(to_scanlog_issue)
                .collect()
        };
        let game_result = format_detected_issues(&rust_issues);

        self.inner.set_game_files_result(game_result);
        self.inner.set_detected_issues(rust_issues.clone());

        // Cache results in global handler for subsequent calls
        global_handler.checks_run = true;
        global_handler.fcx_mode = self.inner.fcx_mode;
        global_handler
            .set_main_files_result(self.inner.main_files_check.clone().unwrap_or_default());
        global_handler
            .set_game_files_result(self.inner.game_files_check.clone().unwrap_or_default());
        global_handler.set_detected_issues(rust_issues);

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
            Ok(()) | Err(FcxResetError::Unnecessary) => Ok(()),
            Err(error) => Err(PyFcxResetError::new_err(format!(
                "failed to reset FCX global state: {error}"
            ))),
        }
    }
}
