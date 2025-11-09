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

    /// Create AnalysisConfig from YamlData
    ///
    /// Converts a YamlData object from classic_config into an AnalysisConfig
    /// for use with the orchestrator.
    ///
    /// # Arguments
    /// * `yamldata` - YamlData object from classic_config module
    ///
    /// # Returns
    /// Configured AnalysisConfig instance
    #[staticmethod]
    pub fn from_yamldata(yamldata: &Bound<'_, pyo3::types::PyAny>) -> PyResult<Self> {
        // Extract game and vr_mode (not available in YamlData, use defaults)
        let game = yamldata.getattr("crashgen_name")?.extract::<String>()?;
        let vr_mode = false; // YamlData doesn't expose this directly

        // Create base config
        let mut config = AnalysisConfig::new(game, vr_mode);

        // Populate from YamlData fields
        config.crashgen_name = yamldata.getattr("crashgen_name")?.extract::<String>()?;
        config.crashgen_latest = yamldata.getattr("crashgen_latest_og")?.extract::<String>()?;
        config.game_version = yamldata.getattr("game_version")?.extract::<String>()?;
        config.game_version_vr = yamldata.getattr("game_version_vr")?.extract::<String>()?;
        config.game_version_new = yamldata.getattr("game_version_new")?.extract::<String>()?;
        config.xse_acronym = yamldata.getattr("xse_acronym")?.extract::<String>()?;

        config.ignore_plugins = yamldata.getattr("game_ignore_plugins")?.extract::<Vec<String>>()?;
        config.ignore_records = yamldata.getattr("game_ignore_records")?.extract::<Vec<String>>()?;
        config.ignore_list = yamldata.getattr("ignore_list")?.extract::<Vec<String>>()?;

        config.show_formid_values = false; // Not in YamlData

        // Extract dictionaries
        config.suspects_error = yamldata
            .getattr("suspects_error_list")?
            .extract::<std::collections::HashMap<String, String>>()?;

        config.suspects_stack = yamldata
            .getattr("suspects_stack_list")?
            .extract::<std::collections::HashMap<String, String>>()?
            .into_iter()
            .map(|(k, v)| {
                // Convert string values to Vec<String> by splitting on newlines
                let patterns: Vec<String> = v
                    .lines()
                    .map(|line| line.trim().to_string())
                    .filter(|line| !line.is_empty())
                    .collect();
                (k, patterns)
            })
            .collect();

        config.mods_core = yamldata
            .getattr("game_mods_core")?
            .extract::<std::collections::HashMap<String, String>>()?;
        config.mods_freq = yamldata
            .getattr("game_mods_freq")?
            .extract::<std::collections::HashMap<String, String>>()?;
        config.mods_conf = yamldata
            .getattr("game_mods_conf")?
            .extract::<std::collections::HashMap<String, String>>()?;
        config.mods_solu = yamldata
            .getattr("game_mods_solu")?
            .extract::<std::collections::HashMap<String, String>>()?;
        config.mods_opc2 = yamldata
            .getattr("game_mods_opc2")?
            .extract::<std::collections::HashMap<String, String>>()?;

        Ok(Self { inner: config })
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

    /// Get the VR game version
    #[getter]
    pub fn game_version_vr(&self) -> String {
        self.inner.game_version_vr.clone()
    }

    /// Set the VR game version
    #[setter]
    pub fn set_game_version_vr(&mut self, value: String) {
        self.inner.game_version_vr = value;
    }

    /// Get the new/updated game version
    #[getter]
    pub fn game_version_new(&self) -> String {
        self.inner.game_version_new.clone()
    }

    /// Set the new/updated game version
    #[setter]
    pub fn set_game_version_new(&mut self, value: String) {
        self.inner.game_version_new = value;
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

    /// Get whether to show FormID values in reports
    #[getter]
    pub fn show_formid_values(&self) -> bool {
        self.inner.show_formid_values
    }

    /// Set whether to show FormID values in reports
    #[setter]
    pub fn set_show_formid_values(&mut self, value: bool) {
        self.inner.show_formid_values = value;
    }

    /// Get the suspect error patterns dictionary
    #[getter]
    pub fn suspects_error(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new(py);
        for (key, value) in &self.inner.suspects_error {
            dict.set_item(key, value)?;
        }
        Ok(dict.into())
    }

    /// Set the suspect error patterns dictionary
    #[setter]
    pub fn set_suspects_error(&mut self, value: std::collections::HashMap<String, String>) {
        self.inner.suspects_error = value;
    }

    /// Get the suspect stack patterns dictionary
    #[getter]
    pub fn suspects_stack(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new(py);
        for (key, value) in &self.inner.suspects_stack {
            dict.set_item(key, value)?;
        }
        Ok(dict.into())
    }

    /// Set the suspect stack patterns dictionary
    #[setter]
    pub fn set_suspects_stack(&mut self, value: std::collections::HashMap<String, Vec<String>>) {
        self.inner.suspects_stack = value;
    }

    /// Get the core mods database
    #[getter]
    pub fn mods_core(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new(py);
        for (key, value) in &self.inner.mods_core {
            dict.set_item(key, value)?;
        }
        Ok(dict.into())
    }

    /// Set the core mods database
    #[setter]
    pub fn set_mods_core(&mut self, value: std::collections::HashMap<String, String>) {
        self.inner.mods_core = value;
    }

    /// Get the frequently problematic mods database
    #[getter]
    pub fn mods_freq(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new(py);
        for (key, value) in &self.inner.mods_freq {
            dict.set_item(key, value)?;
        }
        Ok(dict.into())
    }

    /// Set the frequently problematic mods database
    #[setter]
    pub fn set_mods_freq(&mut self, value: std::collections::HashMap<String, String>) {
        self.inner.mods_freq = value;
    }

    /// Get the mod conflicts database
    #[getter]
    pub fn mods_conf(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new(py);
        for (key, value) in &self.inner.mods_conf {
            dict.set_item(key, value)?;
        }
        Ok(dict.into())
    }

    /// Set the mod conflicts database
    #[setter]
    pub fn set_mods_conf(&mut self, value: std::collections::HashMap<String, String>) {
        self.inner.mods_conf = value;
    }

    /// Get the mod solutions database
    #[getter]
    pub fn mods_solu(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new(py);
        for (key, value) in &self.inner.mods_solu {
            dict.set_item(key, value)?;
        }
        Ok(dict.into())
    }

    /// Set the mod solutions database
    #[setter]
    pub fn set_mods_solu(&mut self, value: std::collections::HashMap<String, String>) {
        self.inner.mods_solu = value;
    }

    /// Get the outdated/redundant/community patch mods database
    #[getter]
    pub fn mods_opc2(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new(py);
        for (key, value) in &self.inner.mods_opc2 {
            dict.set_item(key, value)?;
        }
        Ok(dict.into())
    }

    /// Set the outdated/redundant/community patch mods database
    #[setter]
    pub fn set_mods_opc2(&mut self, value: std::collections::HashMap<String, String>) {
        self.inner.mods_opc2 = value;
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
#[pyclass(name = "Orchestrator")]
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
