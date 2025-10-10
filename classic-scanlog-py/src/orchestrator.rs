//! Python bindings for OrchestratorCore - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::{AnalysisConfig, AnalysisResult, OrchestratorCore};
use classic_shared::get_runtime;
use pyo3::prelude::*;
use std::collections::HashMap;

/// Python wrapper for AnalysisConfig
#[pyclass(name = "AnalysisConfig")]
#[derive(Clone)]
pub struct PyAnalysisConfig {
    pub(crate) inner: AnalysisConfig,
}

#[pymethods]
impl PyAnalysisConfig {
    #[new]
    pub fn new(game: String, vr_mode: bool) -> Self {
        Self {
            inner: AnalysisConfig::new(game, vr_mode),
        }
    }

    #[getter]
    pub fn game(&self) -> String {
        self.inner.game.clone()
    }

    #[setter]
    pub fn set_game(&mut self, value: String) {
        self.inner.game = value;
    }

    #[getter]
    pub fn vr_mode(&self) -> bool {
        self.inner.vr_mode
    }

    #[setter]
    pub fn set_vr_mode(&mut self, value: bool) {
        self.inner.vr_mode = value;
    }

    #[getter]
    pub fn crashgen_name(&self) -> String {
        self.inner.crashgen_name.clone()
    }

    #[setter]
    pub fn set_crashgen_name(&mut self, value: String) {
        self.inner.crashgen_name = value;
    }

    #[getter]
    pub fn crashgen_latest(&self) -> String {
        self.inner.crashgen_latest.clone()
    }

    #[setter]
    pub fn set_crashgen_latest(&mut self, value: String) {
        self.inner.crashgen_latest = value;
    }

    #[getter]
    pub fn game_version(&self) -> String {
        self.inner.game_version.clone()
    }

    #[setter]
    pub fn set_game_version(&mut self, value: String) {
        self.inner.game_version = value;
    }

    #[getter]
    pub fn xse_acronym(&self) -> String {
        self.inner.xse_acronym.clone()
    }

    #[setter]
    pub fn set_xse_acronym(&mut self, value: String) {
        self.inner.xse_acronym = value;
    }

    #[getter]
    pub fn ignore_plugins(&self) -> Vec<String> {
        self.inner.ignore_plugins.clone()
    }

    #[setter]
    pub fn set_ignore_plugins(&mut self, value: Vec<String>) {
        self.inner.ignore_plugins = value;
    }

    #[getter]
    pub fn ignore_records(&self) -> Vec<String> {
        self.inner.ignore_records.clone()
    }

    #[setter]
    pub fn set_ignore_records(&mut self, value: Vec<String>) {
        self.inner.ignore_records = value;
    }

    #[getter]
    pub fn ignore_list(&self) -> Vec<String> {
        self.inner.ignore_list.clone()
    }

    #[setter]
    pub fn set_ignore_list(&mut self, value: Vec<String>) {
        self.inner.ignore_list = value;
    }
}

/// Python wrapper for AnalysisResult
#[pyclass(name = "AnalysisResult")]
#[derive(Clone)]
pub struct PyAnalysisResult {
    pub(crate) inner: AnalysisResult,
}

#[pymethods]
impl PyAnalysisResult {
    #[getter]
    pub fn log_path(&self) -> String {
        self.inner.log_path.clone()
    }

    #[getter]
    pub fn report_lines(&self) -> Vec<String> {
        self.inner.report_lines.clone()
    }

    #[getter]
    pub fn success(&self) -> bool {
        self.inner.success
    }

    #[getter]
    pub fn error(&self) -> Option<String> {
        self.inner.error.clone()
    }

    #[getter]
    pub fn processing_time_ms(&self) -> u64 {
        self.inner.processing_time_ms
    }

    #[getter]
    pub fn formid_count(&self) -> usize {
        self.inner.formid_count
    }

    #[getter]
    pub fn plugin_count(&self) -> usize {
        self.inner.plugin_count
    }

    #[getter]
    pub fn suspect_count(&self) -> usize {
        self.inner.suspect_count
    }
}

/// Python wrapper for OrchestratorCore
#[pyclass(name = "RustOrchestrator")]
pub struct PyRustOrchestrator {
    inner: OrchestratorCore,
}

#[pymethods]
impl PyRustOrchestrator {
    #[new]
    pub fn new(config: PyAnalysisConfig) -> PyResult<Self> {
        let inner = OrchestratorCore::new(config.inner).map_err(crate::to_pyerr)?;
        Ok(Self { inner })
    }

    /// Analyze a single crash log file
    pub fn process_log(&self, log_path: String) -> PyResult<PyAnalysisResult> {
        // Use shared runtime to run async method
        let result = get_runtime()
            .block_on(async { self.inner.process_log(log_path).await })
            .map_err(crate::to_pyerr)?;
        Ok(PyAnalysisResult { inner: result })
    }

    /// Analyze multiple crash logs in parallel
    pub fn process_logs_batch(&self, log_paths: Vec<String>) -> PyResult<Vec<PyAnalysisResult>> {
        // Use shared runtime to run async method
        let results =
            get_runtime().block_on(async { self.inner.process_logs_batch(log_paths).await });
        Ok(results
            .into_iter()
            .map(|r| PyAnalysisResult { inner: r })
            .collect())
    }

    /// Get the configuration
    pub fn config(&self) -> PyAnalysisConfig {
        PyAnalysisConfig {
            inner: self.inner.config().clone(),
        }
    }
}
