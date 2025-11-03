//! Python bindings for OrchestratorCore - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::{AnalysisConfig, AnalysisResult, OrchestratorCore};
use classic_shared::without_gil;
use classic_shared_core::get_runtime;
use pyo3::prelude::*;

/// Python wrapper for AnalysisConfig
///
/// Provides Python bindings for the Rust AnalysisConfig struct,
/// which configures crash log analysis parameters for a specific game.
#[pyclass(name = "AnalysisConfig")]
#[derive(Clone)]
pub struct PyAnalysisConfig {
    /// Inner Rust AnalysisConfig instance
    pub(crate) inner: AnalysisConfig,
}

#[pymethods]
impl PyAnalysisConfig {
    /// Create a new analysis configuration
    ///
    /// # Arguments
    /// * `game` - Game identifier (e.g., "Fallout4", "Skyrim")
    /// * `vr_mode` - Whether to use VR-specific configuration
    #[new]
    pub fn new(game: String, vr_mode: bool) -> Self {
        Self {
            inner: AnalysisConfig::new(game, vr_mode),
        }
    }

    /// Get the game identifier
    #[getter]
    pub fn game(&self) -> String {
        self.inner.game.clone()
    }

    /// Set the game identifier
    #[setter]
    pub fn set_game(&mut self, value: String) {
        self.inner.game = value;
    }

    /// Get whether VR mode is enabled
    #[getter]
    pub fn vr_mode(&self) -> bool {
        self.inner.vr_mode
    }

    /// Set whether VR mode is enabled
    #[setter]
    pub fn set_vr_mode(&mut self, value: bool) {
        self.inner.vr_mode = value;
    }

    /// Get the crash generator name
    #[getter]
    pub fn crashgen_name(&self) -> String {
        self.inner.crashgen_name.clone()
    }

    /// Set the crash generator name
    #[setter]
    pub fn set_crashgen_name(&mut self, value: String) {
        self.inner.crashgen_name = value;
    }

    /// Get the latest crash generator version
    #[getter]
    pub fn crashgen_latest(&self) -> String {
        self.inner.crashgen_latest.clone()
    }

    /// Set the latest crash generator version
    #[setter]
    pub fn set_crashgen_latest(&mut self, value: String) {
        self.inner.crashgen_latest = value;
    }

    /// Get the game version
    #[getter]
    pub fn game_version(&self) -> String {
        self.inner.game_version.clone()
    }

    /// Set the game version
    #[setter]
    pub fn set_game_version(&mut self, value: String) {
        self.inner.game_version = value;
    }

    /// Get the XSE (script extender) acronym
    #[getter]
    pub fn xse_acronym(&self) -> String {
        self.inner.xse_acronym.clone()
    }

    /// Set the XSE (script extender) acronym
    #[setter]
    pub fn set_xse_acronym(&mut self, value: String) {
        self.inner.xse_acronym = value;
    }

    /// Get the list of plugins to ignore during analysis
    #[getter]
    pub fn ignore_plugins(&self) -> Vec<String> {
        self.inner.ignore_plugins.clone()
    }

    /// Set the list of plugins to ignore during analysis
    #[setter]
    pub fn set_ignore_plugins(&mut self, value: Vec<String>) {
        self.inner.ignore_plugins = value;
    }

    /// Get the list of records to ignore during analysis
    #[getter]
    pub fn ignore_records(&self) -> Vec<String> {
        self.inner.ignore_records.clone()
    }

    /// Set the list of records to ignore during analysis
    #[setter]
    pub fn set_ignore_records(&mut self, value: Vec<String>) {
        self.inner.ignore_records = value;
    }

    /// Get the general ignore list
    #[getter]
    pub fn ignore_list(&self) -> Vec<String> {
        self.inner.ignore_list.clone()
    }

    /// Set the general ignore list
    #[setter]
    pub fn set_ignore_list(&mut self, value: Vec<String>) {
        self.inner.ignore_list = value;
    }
}

/// Python wrapper for AnalysisResult
///
/// Contains the results of analyzing a crash log, including the generated report,
/// statistics, and any errors encountered during processing.
#[pyclass(name = "AnalysisResult")]
#[derive(Clone)]
pub struct PyAnalysisResult {
    /// Inner Rust AnalysisResult instance
    pub(crate) inner: AnalysisResult,
}

#[pymethods]
impl PyAnalysisResult {
    /// Get the path to the analyzed crash log file
    #[getter]
    pub fn log_path(&self) -> String {
        self.inner.log_path.clone()
    }

    /// Get the generated report lines
    #[getter]
    pub fn report_lines(&self) -> Vec<String> {
        self.inner.report_lines.clone()
    }

    /// Get whether the analysis completed successfully
    #[getter]
    pub fn success(&self) -> bool {
        self.inner.success
    }

    /// Get the error message if analysis failed
    #[getter]
    pub fn error(&self) -> Option<String> {
        self.inner.error.clone()
    }

    /// Get the processing time in milliseconds
    #[getter]
    pub fn processing_time_ms(&self) -> u64 {
        self.inner.processing_time_ms
    }

    /// Get the number of FormIDs found in the log
    #[getter]
    pub fn formid_count(&self) -> usize {
        self.inner.formid_count
    }

    /// Get the number of plugins referenced in the log
    #[getter]
    pub fn plugin_count(&self) -> usize {
        self.inner.plugin_count
    }

    /// Get the number of suspect patterns detected
    #[getter]
    pub fn suspect_count(&self) -> usize {
        self.inner.suspect_count
    }
}

/// Python wrapper for OrchestratorCore
///
/// Coordinates the analysis of crash logs, providing both single-file and batch processing
/// capabilities with automatic parallelism and GIL release for optimal performance.
#[pyclass(name = "RustOrchestrator")]
pub struct PyRustOrchestrator {
    /// Inner Rust OrchestratorCore instance
    inner: OrchestratorCore,
}

#[pymethods]
impl PyRustOrchestrator {
    /// Create a new orchestrator with the given configuration
    ///
    /// # Arguments
    /// * `config` - Analysis configuration for crash log processing
    ///
    /// # Returns
    /// New RustOrchestrator instance
    #[new]
    pub fn new(config: PyAnalysisConfig) -> PyResult<Self> {
        let inner = OrchestratorCore::new(config.inner).map_err(crate::to_pyerr)?;
        Ok(Self { inner })
    }

    /// Analyze a single crash log file
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    ///
    /// # Arguments
    /// * `py` - Python GIL token
    /// * `log_path` - Path to the crash log file to analyze
    ///
    /// # Returns
    /// Analysis result containing report lines and statistics
    pub fn process_log(&self, py: Python<'_>, log_path: String) -> PyResult<PyAnalysisResult> {
        // Release GIL during log processing
        let result = without_gil(py, || {
            get_runtime()
                .block_on(async { self.inner.process_log(log_path).await })
                .map_err(crate::to_pyerr)
        })?;
        Ok(PyAnalysisResult { inner: result })
    }

    /// Analyze multiple crash logs in parallel
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    /// The batch processing itself uses Rust parallelism for optimal performance.
    ///
    /// # Arguments
    /// * `py` - Python GIL token
    /// * `log_paths` - Paths to crash log files to analyze
    ///
    /// # Returns
    /// Vector of analysis results for each log file
    pub fn process_logs_batch(
        &self,
        py: Python<'_>,
        log_paths: Vec<String>,
    ) -> PyResult<Vec<PyAnalysisResult>> {
        // Release GIL during parallel batch processing
        let results = without_gil(py, || {
            get_runtime().block_on(async { self.inner.process_logs_batch(log_paths).await })
        });
        Ok(results
            .into_iter()
            .map(|r| PyAnalysisResult { inner: r })
            .collect())
    }

    /// Get the current configuration
    ///
    /// # Returns
    /// Copy of the analysis configuration
    pub fn config(&self) -> PyAnalysisConfig {
        PyAnalysisConfig {
            inner: self.inner.config().clone(),
        }
    }
}
