//! Python bindings for OrchestratorCore - Thin wrapper over classic-scanlog-core

use classic_config_core::{CoreModEntry, CrashgenEntryRaw, ModConflictEntry, YamlDataCore};
use classic_database_core::DatabasePool;
use classic_scanlog_core::{
    AnalysisConfig, AnalysisResult, OrchestratorCore, build_analysis_config_from_yaml,
};
use classic_shared::{pyany_to_indexmap_str, pyany_to_indexmap_vecstr, without_gil};
use classic_shared_core::get_runtime;
use indexmap::IndexMap;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use crate::crashgen_rules::parse_settings_rules;

fn parse_crashgen_registry_from_py(
    registry_any: &Bound<'_, PyAny>,
) -> HashMap<String, CrashgenEntryRaw> {
    let Ok(registry_dict) = registry_any.cast::<PyDict>() else {
        return HashMap::new();
    };
    let mut entries: HashMap<String, CrashgenEntryRaw> = HashMap::new();

    for (name_any, entry_any) in registry_dict.iter() {
        let name = match name_any.extract::<String>() {
            Ok(n) => n,
            Err(_) => continue,
        };

        let entry_dict = match entry_any.cast::<PyDict>() {
            Ok(d) => d,
            Err(_) => continue,
        };

        let display_section = entry_dict
            .get_item("display_section")
            .ok()
            .flatten()
            .and_then(|v| v.extract::<String>().ok())
            .unwrap_or_default();

        let ignore_keys = entry_dict
            .get_item("ignore_keys")
            .ok()
            .flatten()
            .and_then(|v| v.extract::<Vec<String>>().ok())
            .unwrap_or_default()
            .into_iter()
            .collect();

        let checks: Vec<String> = entry_dict
            .get_item("checks")
            .ok()
            .flatten()
            .and_then(|v| v.extract::<Vec<String>>().ok())
            .unwrap_or_default();

        let settings_rules_version = entry_dict
            .get_item("settings_rules_version")
            .ok()
            .flatten()
            .and_then(|v| v.extract::<u32>().ok());

        let settings_rules = entry_dict
            .get_item("settings_rules")
            .ok()
            .flatten()
            .and_then(|v| parse_settings_rules(&v));

        let entry = CrashgenEntryRaw {
            display_section,
            ignore_keys,
            checks,
            settings_rules_version,
            settings_rules,
        };

        entries.insert(name, entry);
    }

    entries
}

fn extract_string_attr(yamldata: &Bound<'_, PyAny>, attr_name: &str) -> String {
    yamldata
        .getattr(attr_name)
        .ok()
        .and_then(|attr| attr.extract::<String>().ok())
        .unwrap_or_default()
}

fn extract_vec_string_attr(yamldata: &Bound<'_, PyAny>, attr_name: &str) -> Vec<String> {
    yamldata
        .getattr(attr_name)
        .ok()
        .and_then(|attr| attr.extract::<Vec<String>>().ok())
        .unwrap_or_default()
}

fn extract_indexmap_str_attr(
    yamldata: &Bound<'_, PyAny>,
    attr_name: &str,
) -> IndexMap<String, String> {
    yamldata
        .getattr(attr_name)
        .map(|attr| pyany_to_indexmap_str(&attr))
        .unwrap_or_default()
}

fn extract_indexmap_vecstr_attr(
    yamldata: &Bound<'_, PyAny>,
    attr_name: &str,
) -> IndexMap<String, Vec<String>> {
    yamldata
        .getattr(attr_name)
        .map(|attr| pyany_to_indexmap_vecstr(&attr))
        .unwrap_or_default()
}

fn extract_mod_conflict_entries(yamldata: &Bound<'_, PyAny>, attr_name: &str) -> Vec<ModConflictEntry> {
    let Ok(attr) = yamldata.getattr(attr_name) else {
        return Vec::new();
    };
    let Ok(list) = attr.extract::<Vec<Bound<'_, PyAny>>>() else {
        return Vec::new();
    };
    list.iter()
        .filter_map(|item| {
            let dict = item.cast::<PyDict>().ok()?;
            Some(ModConflictEntry {
                mod_a: dict.get_item("mod_a").ok()??.extract::<String>().ok()?,
                mod_b: dict.get_item("mod_b").ok()??.extract::<String>().ok()?,
                name_a: dict.get_item("name_a").ok()??.extract::<String>().ok()?,
                name_b: dict.get_item("name_b").ok()??.extract::<String>().ok()?,
                description: dict.get_item("description").ok()??.extract::<String>().ok()?,
                fix: dict.get_item("fix").ok()??.extract::<String>().ok()?,
                link: dict
                    .get_item("link")
                    .ok()
                    .flatten()
                    .and_then(|v| v.extract::<String>().ok()),
            })
        })
        .collect()
}

fn extract_core_mod_entries(yamldata: &Bound<'_, PyAny>, attr_name: &str) -> Vec<CoreModEntry> {
    let Ok(attr) = yamldata.getattr(attr_name) else {
        return Vec::new();
    };
    let Ok(list) = attr.extract::<Vec<Bound<'_, PyAny>>>() else {
        return Vec::new();
    };
    list.iter()
        .filter_map(|item| {
            let dict = item.cast::<PyDict>().ok()?;
            Some(CoreModEntry {
                detect: dict.get_item("detect").ok()??.extract::<String>().ok()?,
                name: dict.get_item("name").ok()??.extract::<String>().ok()?,
                description: dict
                    .get_item("description")
                    .ok()??
                    .extract::<String>()
                    .ok()?,
                gpu: dict
                    .get_item("gpu")
                    .ok()
                    .flatten()
                    .and_then(|v| v.extract::<String>().ok()),
                gpu_mismatch_warning: None,
                exclude_when: None,
            })
        })
        .collect()
}

fn adapt_yamldata_to_core(yamldata: &Bound<'_, PyAny>) -> YamlDataCore {
    let crashgen_registry = yamldata
        .getattr("crashgen_registry")
        .ok()
        .map(|attr| parse_crashgen_registry_from_py(&attr))
        .unwrap_or_default();
    let mut classic_version = extract_string_attr(yamldata, "classic_version");
    if classic_version.is_empty() {
        classic_version = "CLASSIC".to_string();
    }

    YamlDataCore {
        classic_game_hints: extract_vec_string_attr(yamldata, "classic_game_hints"),
        classic_records_list: extract_vec_string_attr(yamldata, "classic_records_list"),
        classic_version,
        classic_version_date: extract_string_attr(yamldata, "classic_version_date"),
        crashgen_name: extract_string_attr(yamldata, "crashgen_name"),
        crashgen_latest_og: extract_string_attr(yamldata, "crashgen_latest_og"),
        crashgen_ignore: extract_vec_string_attr(yamldata, "crashgen_ignore"),
        warn_noplugins: extract_string_attr(yamldata, "warn_noplugins"),
        warn_outdated: extract_string_attr(yamldata, "warn_outdated"),
        xse_acronym: extract_string_attr(yamldata, "xse_acronym"),
        game_ignore_plugins: extract_vec_string_attr(yamldata, "game_ignore_plugins"),
        game_ignore_records: extract_vec_string_attr(yamldata, "game_ignore_records"),
        ignore_list: extract_vec_string_attr(yamldata, "ignore_list"),
        suspects_error_list: extract_indexmap_str_attr(yamldata, "suspects_error_list"),
        suspects_stack_list: extract_indexmap_vecstr_attr(yamldata, "suspects_stack_list"),
        game_mods_conf: extract_mod_conflict_entries(yamldata, "game_mods_conf"),
        game_mods_core: extract_core_mod_entries(yamldata, "game_mods_core"),
        game_mods_freq: extract_indexmap_str_attr(yamldata, "game_mods_freq"),
        game_mods_opc2: extract_indexmap_str_attr(yamldata, "game_mods_opc2"),
        game_mods_solu: extract_indexmap_str_attr(yamldata, "game_mods_solu"),
        autoscan_text: extract_string_attr(yamldata, "autoscan_text"),
        game_version: extract_string_attr(yamldata, "game_version"),
        game_root_name: extract_string_attr(yamldata, "game_root_name"),
        crashgen_registry,
    }
}

// =============================================================================
// Cancellation Token
// =============================================================================

/// Python-accessible cancellation token for batch operations.
///
/// Allows Python code to signal cancellation to Rust batch processing.
/// The token uses atomic operations for thread-safe cancellation signaling.
///
/// # Example
///
/// ```python
/// from classic_scanlog import CancellationToken, Orchestrator
///
/// token = CancellationToken()
///
/// # In another thread or async task:
/// token.cancel()  # Request cancellation
///
/// # The orchestrator checks this between logs
/// results = orchestrator.process_logs_batch(paths, cancellation_token=token)
/// ```
#[pyclass(name = "CancellationToken")]
#[derive(Clone)]
pub struct PyCancellationToken {
    inner: Arc<AtomicBool>,
}

#[pymethods]
impl PyCancellationToken {
    /// Create a new cancellation token (initially not cancelled).
    #[new]
    pub fn new() -> Self {
        Self {
            inner: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Request cancellation - signals the orchestrator to stop after current log.
    ///
    /// Once cancelled, the orchestrator will complete processing of the current log,
    /// then return results for all completed logs plus placeholder entries for
    /// remaining logs marked as "Cancelled by user".
    pub fn cancel(&self) {
        self.inner.store(true, Ordering::Relaxed);
    }

    /// Check if cancellation has been requested.
    ///
    /// Returns:
    ///     True if cancel() has been called on this token.
    pub fn is_cancelled(&self) -> bool {
        self.inner.load(Ordering::Relaxed)
    }

    /// Reset the token for reuse (clears cancellation state).
    ///
    /// Allows the same token to be used for multiple batch operations.
    pub fn reset(&self) {
        self.inner.store(false, Ordering::Relaxed);
    }
}

impl Default for PyCancellationToken {
    fn default() -> Self {
        Self::new()
    }
}

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
    /// * `game_version` - Selected mode
    ///   ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR")
    #[new]
    pub fn new(game: String, game_version: String) -> Self {
        Self {
            inner: AnalysisConfig::new(game, game_version),
        }
    }

    /// Create AnalysisConfig from YamlData
    ///
    /// Converts a YamlData object from classic_config into an AnalysisConfig
    /// for use with the orchestrator.
    ///
    /// # Arguments
    /// * `yamldata` - YamlData object from classic_config module
    /// * `game` - Game identifier (e.g., "Fallout4", "Skyrim")
    /// * `game_version` - Selected mode
    ///   ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR")
    /// * `show_formid_values` - Whether to show FormID values (default: false)
    /// * `fcx_mode` - Whether FCX mode is enabled (default: false)
    /// * `simplify_logs` - Whether to simplify logs (default: false)
    ///
    /// # Returns
    /// Configured AnalysisConfig instance
    #[staticmethod]
    #[pyo3(signature = (yamldata, game, game_version, show_formid_values=false, fcx_mode=false, simplify_logs=false, remove_list=Vec::new()))]
    pub fn from_yamldata(
        yamldata: &Bound<'_, pyo3::types::PyAny>,
        game: String,
        game_version: String,
        show_formid_values: bool,
        fcx_mode: bool,
        simplify_logs: bool,
        remove_list: Vec<String>,
    ) -> PyResult<Self> {
        let yaml_core = adapt_yamldata_to_core(yamldata);
        let config = build_analysis_config_from_yaml(
            &yaml_core,
            &game,
            &game_version,
            show_formid_values,
            fcx_mode,
            simplify_logs,
            remove_list,
        );
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

    /// Set the suspect error patterns dictionary (preserves dict order)
    #[setter]
    pub fn set_suspects_error(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        self.inner.suspects_error = pyany_to_indexmap_str(value);
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

    /// Set the suspect stack patterns dictionary (preserves dict order)
    #[setter]
    pub fn set_suspects_stack(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        self.inner.suspects_stack = pyany_to_indexmap_vecstr(value);
    }

    /// Get the core mods database as a list of dicts
    #[getter]
    pub fn mods_core(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyList>> {
        let list = pyo3::types::PyList::empty(py);
        for entry in &self.inner.mods_core {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("detect", &entry.detect)?;
            dict.set_item("name", &entry.name)?;
            dict.set_item("description", &entry.description)?;
            dict.set_item("gpu", &entry.gpu)?;
            list.append(dict)?;
        }
        Ok(list.into())
    }

    /// Set the core mods database from a list of dicts
    #[setter]
    pub fn set_mods_core(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        if let Ok(list) = value.extract::<Vec<Bound<'_, pyo3::types::PyAny>>>() {
            self.inner.mods_core = list
                .iter()
                .filter_map(|item| {
                    let dict = item.cast::<pyo3::types::PyDict>().ok()?;
                    Some(CoreModEntry {
                        detect: dict.get_item("detect").ok()??.extract::<String>().ok()?,
                        name: dict.get_item("name").ok()??.extract::<String>().ok()?,
                        description: dict
                            .get_item("description")
                            .ok()??
                            .extract::<String>()
                            .ok()?,
                        gpu: dict
                            .get_item("gpu")
                            .ok()
                            .flatten()
                            .and_then(|v| v.extract::<String>().ok()),
                        gpu_mismatch_warning: None,
                        exclude_when: None,
                    })
                })
                .collect();
        }
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

    /// Set the frequently problematic mods database (preserves insertion order)
    #[setter]
    pub fn set_mods_freq(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        self.inner.mods_freq = pyany_to_indexmap_str(value);
    }

    /// Get the mod conflicts database as a list of dicts
    #[getter]
    pub fn mods_conf(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyList>> {
        let list = pyo3::types::PyList::empty(py);
        for entry in &self.inner.mods_conf {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("mod_a", &entry.mod_a)?;
            dict.set_item("mod_b", &entry.mod_b)?;
            dict.set_item("name_a", &entry.name_a)?;
            dict.set_item("name_b", &entry.name_b)?;
            dict.set_item("description", &entry.description)?;
            dict.set_item("fix", &entry.fix)?;
            dict.set_item("link", &entry.link)?;
            list.append(dict)?;
        }
        Ok(list.into())
    }

    /// Set the mod conflicts database from a list of dicts
    #[setter]
    pub fn set_mods_conf(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        let Ok(list) = value.extract::<Vec<Bound<'_, pyo3::types::PyAny>>>() else {
            self.inner.mods_conf = Vec::new();
            return;
        };
        self.inner.mods_conf = list
            .iter()
            .filter_map(|item| {
                let dict = item.cast::<pyo3::types::PyDict>().ok()?;
                Some(ModConflictEntry {
                    mod_a: dict.get_item("mod_a").ok()??.extract::<String>().ok()?,
                    mod_b: dict.get_item("mod_b").ok()??.extract::<String>().ok()?,
                    name_a: dict.get_item("name_a").ok()??.extract::<String>().ok()?,
                    name_b: dict.get_item("name_b").ok()??.extract::<String>().ok()?,
                    description: dict.get_item("description").ok()??.extract::<String>().ok()?,
                    fix: dict.get_item("fix").ok()??.extract::<String>().ok()?,
                    link: dict
                        .get_item("link")
                        .ok()
                        .flatten()
                        .and_then(|v| v.extract::<String>().ok()),
                })
            })
            .collect();
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

    /// Set the mod solutions database (preserves insertion order)
    #[setter]
    pub fn set_mods_solu(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        self.inner.mods_solu = pyany_to_indexmap_str(value);
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

    /// Set the outdated/redundant/community patch mods database (preserves insertion order)
    #[setter]
    pub fn set_mods_opc2(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        self.inner.mods_opc2 = pyany_to_indexmap_str(value);
    }

    // ============================================================================
    // New fields added for Python-Rust parity
    // ============================================================================

    /// Get the latest VR crashgen version
    #[getter]
    pub fn crashgen_latest_vr(&self) -> String {
        self.inner.crashgen_latest_vr.clone()
    }

    /// Set the latest VR crashgen version
    #[setter]
    pub fn set_crashgen_latest_vr(&mut self, value: String) {
        self.inner.crashgen_latest_vr = value;
    }

    /// Get the game root name (e.g., "Fallout4")
    #[getter]
    pub fn game_root_name(&self) -> String {
        self.inner.game_root_name.clone()
    }

    /// Set the game root name
    #[setter]
    pub fn set_game_root_name(&mut self, value: String) {
        self.inner.game_root_name = value;
    }

    /// Get the CLASSIC version string
    #[getter]
    pub fn classic_version(&self) -> String {
        self.inner.classic_version.clone()
    }

    /// Set the CLASSIC version string
    #[setter]
    pub fn set_classic_version(&mut self, value: String) {
        self.inner.classic_version = value;
    }

    /// Get whether FCX mode is enabled
    #[getter]
    pub fn fcx_mode(&self) -> bool {
        self.inner.fcx_mode
    }

    /// Set whether FCX mode is enabled
    #[setter]
    pub fn set_fcx_mode(&mut self, value: bool) {
        self.inner.fcx_mode = value;
    }

    /// Get whether to simplify logs by removing strings
    #[getter]
    pub fn simplify_logs(&self) -> bool {
        self.inner.simplify_logs
    }

    /// Set whether to simplify logs
    #[setter]
    pub fn set_simplify_logs(&mut self, value: bool) {
        self.inner.simplify_logs = value;
    }

    /// Get the list of strings to remove when simplifying logs
    #[getter]
    pub fn remove_list(&self) -> Vec<String> {
        self.inner.remove_list.clone()
    }

    /// Set the list of strings to remove when simplifying logs
    #[setter]
    pub fn set_remove_list(&mut self, value: Vec<String>) {
        self.inner.remove_list = value;
    }

    /// Get the list of named records to scan for
    #[getter]
    pub fn classic_records_list(&self) -> Vec<String> {
        self.inner.classic_records_list.clone()
    }

    /// Set the list of named records to scan for
    #[setter]
    pub fn set_classic_records_list(&mut self, value: Vec<String>) {
        self.inner.classic_records_list = value;
    }

    /// Get the list of crashgen settings to ignore during validation.
    ///
    /// Deprecated: Returns an empty list. Use the Crashgen_Registry in YAML instead.
    #[getter]
    pub fn crashgen_ignore(&self) -> Vec<String> {
        Vec::new() // Superseded by per-crashgen registry entries
    }

    /// Set the list of crashgen settings to ignore during validation.
    ///
    /// Deprecated: No-op. Use the Crashgen_Registry in YAML instead.
    #[setter]
    pub fn set_crashgen_ignore(&mut self, _value: Vec<String>) {
        // No-op: superseded by per-crashgen registry entries
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

    /// Get the processing time in milliseconds (minimum 1ms for non-zero processing)
    #[getter]
    pub fn processing_time_ms(&self) -> u64 {
        self.inner.processing_time_ms
    }

    /// Get the processing time in microseconds (for sub-millisecond precision)
    #[getter]
    pub fn processing_time_us(&self) -> u64 {
        self.inner.processing_time_us
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

    // ============================================================================
    // Statistics fields for Python-Rust parity (Counter[str] compatibility)
    // ============================================================================

    /// Get the number of logs successfully scanned (1 for success, 0 for failure)
    #[getter]
    pub fn scanned(&self) -> u32 {
        self.inner.scanned
    }

    /// Get the number of logs detected as incomplete (missing plugin segment)
    #[getter]
    pub fn incomplete(&self) -> u32 {
        self.inner.incomplete
    }

    /// Get the number of logs that failed to scan
    #[getter]
    pub fn failed(&self) -> u32 {
        self.inner.failed
    }

    /// Get whether the scan triggered a failure condition
    #[getter]
    pub fn trigger_scan_failed(&self) -> bool {
        self.inner.trigger_scan_failed
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

    /// Analyze multiple crash logs in batch mode with configurable parallelism.
    ///
    /// Batch processes multiple crash logs with parallel execution. The level of
    /// parallelism can be controlled via `max_concurrent`, or left to auto-detect
    /// based on CPU cores and batch size.
    ///
    /// **Results are returned in input order** - each position in the output
    /// corresponds to the same position in the input. Failed logs have placeholder
    /// entries with error information.
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    ///
    /// # Arguments
    /// * `py` - Python GIL token
    /// * `log_paths` - Paths to crash log files to analyze
    /// * `max_concurrent` - Optional maximum number of concurrent processing tasks.
    ///   If `None`, uses adaptive concurrency based on CPU count and batch size.
    ///   If `Some(n)`, uses exactly `n` concurrent tasks (minimum 1).
    /// * `progress_callback` - Optional callback function called when each log completes.
    ///   Signature: `(current: int, total: int, filename: str) -> None`
    /// * `cancellation_token` - Optional token to cancel batch processing.
    ///   Call `token.cancel()` to stop after the current log completes.
    ///
    /// # Returns
    /// Vector of analysis results in the same order as input paths
    #[pyo3(signature = (log_paths, max_concurrent = None, progress_callback = None, cancellation_token = None))]
    pub fn process_logs_batch(
        &self,
        py: Python<'_>,
        log_paths: Vec<String>,
        max_concurrent: Option<usize>,
        progress_callback: Option<Py<PyAny>>,
        cancellation_token: Option<PyCancellationToken>,
    ) -> PyResult<Vec<PyAnalysisResult>> {
        use futures::stream::{self, StreamExt};
        use std::collections::HashMap;

        if log_paths.is_empty() {
            return Ok(Vec::new());
        }

        let total = log_paths.len();
        let cancellation = cancellation_token.map(|t| t.inner.clone());

        // Wrap the callback in Arc for sharing across async tasks
        // Clone the Py<PyAny> while we have the GIL (increment refcount)
        let callback: Option<Arc<Py<PyAny>>> =
            progress_callback.map(|cb| Arc::new(cb.clone_ref(py)));

        // Determine concurrency level
        let concurrency = match max_concurrent {
            Some(n) => n.max(1), // User-specified, minimum 1
            None => {
                // Adaptive concurrency: start with CPU count, scale based on batch size
                let num_cpus = num_cpus::get();
                if total < num_cpus {
                    total.max(1) // Small batch: process all concurrently, min 1
                } else {
                    num_cpus.max(4) // Large batch: use CPU count (min 4 for good throughput)
                }
            }
        };

        // Clone log_paths for use inside the closure (needed for placeholder generation)
        let log_paths_clone = log_paths.clone();

        // Release GIL during parallel batch processing
        let indexed_results: HashMap<usize, AnalysisResult> = without_gil(py, || {
            get_runtime().block_on(async {
                // Process with index tracking for order preservation
                stream::iter(log_paths.into_iter().enumerate())
                    .map(|(index, log_path)| {
                        let cancellation = cancellation.clone();
                        let callback = callback.clone();
                        let log_path_clone = log_path.clone();
                        async move {
                            // Check cancellation before processing each log
                            if let Some(ref cancel) = cancellation {
                                if cancel.load(Ordering::Relaxed) {
                                    return (
                                        index,
                                        AnalysisResult::failure(
                                            log_path_clone,
                                            "Cancelled by user".to_string(),
                                        ),
                                    );
                                }
                            }

                            // Process the log
                            let result = match self.inner.process_log(log_path.clone()).await {
                                Ok(r) => r,
                                Err(e) => {
                                    AnalysisResult::failure(log_path_clone.clone(), e.to_string())
                                }
                            };

                            // Report progress after each log completes (with GIL)
                            if let Some(ref cb) = callback {
                                let current = index + 1;
                                let filename = log_path_clone.clone();
                                // Re-acquire GIL to call Python callback
                                Python::attach(|py_inner| {
                                    // Best-effort callback invocation - don't fail batch on callback error
                                    let _ = cb.call1(py_inner, (current, total, filename));
                                });
                            }

                            (index, result)
                        }
                    })
                    .buffer_unordered(concurrency)
                    .collect()
                    .await
            })
        });

        // Reconstruct results in input order with placeholders for any missing entries
        let results: Vec<PyAnalysisResult> = (0..total)
            .map(|i| {
                indexed_results.get(&i).cloned().unwrap_or_else(|| {
                    AnalysisResult::failure(
                        log_paths_clone[i].clone(),
                        "Processing result missing".to_string(),
                    )
                })
            })
            .map(|r| PyAnalysisResult { inner: r })
            .collect();

        Ok(results)
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

    /// Check if the orchestrator has all features required for Rust-first processing.
    ///
    /// A feature-complete orchestrator can replace Python's OrchestratorCore for
    /// both single-log and batch processing.
    ///
    /// # Returns
    /// True if all required features are available
    pub fn is_feature_complete(&self) -> bool {
        self.inner.is_feature_complete()
    }

    /// Attach a database pool for FormID value lookups.
    ///
    /// Creates a DatabasePool from the given database file paths, initializes it,
    /// and attaches it to the orchestrator for FormID description resolution.
    ///
    /// # Arguments
    /// * `py` - Python GIL token
    /// * `db_paths` - Paths to SQLite database files (e.g., "Fallout4 FormIDs Main.db")
    /// * `game_table` - Optional game table name for lookups (e.g., "Fallout4")
    ///
    /// # Errors
    /// Returns PyErr if database initialization fails.
    #[pyo3(signature = (db_paths, game_table = None))]
    pub fn attach_database(
        &mut self,
        py: Python<'_>,
        db_paths: Vec<String>,
        game_table: Option<String>,
    ) -> PyResult<()> {
        let table = game_table.unwrap_or_else(|| self.inner.config().game.clone());
        let pool = DatabasePool::new(None, Duration::from_secs(300), table);

        let paths: Vec<PathBuf> = db_paths.iter().map(PathBuf::from).collect();

        // Initialize the pool (async) with GIL released
        without_gil(py, || {
            get_runtime()
                .block_on(async { pool.initialize(paths).await })
                .map_err(|e| {
                    pyo3::exceptions::PyRuntimeError::new_err(format!(
                        "Database initialization failed: {}",
                        e
                    ))
                })
        })?;

        self.inner
            .attach_database_pool(Arc::new(pool))
            .map_err(crate::to_pyerr)?;
        Ok(())
    }

    /// Check if this orchestrator has a database pool attached.
    ///
    /// # Returns
    /// True if database pool is available for FormID lookups
    pub fn has_database_pool(&self) -> bool {
        self.inner.has_database_pool()
    }

    /// Check if the orchestrator has been initialized via async_enter.
    ///
    /// # Returns
    /// True if initialized
    pub fn is_initialized(&self) -> bool {
        self.inner.is_initialized()
    }

    /// Write batch reports to files.
    ///
    /// This operation writes multiple report files concurrently, generating
    /// autoscan filenames (e.g., crash.log -> crash-AUTOSCAN.md).
    ///
    /// # Arguments
    /// * `py` - Python GIL token
    /// * `reports` - List of tuples: (log_path, report_lines, scan_failed)
    ///
    /// # Returns
    /// List of paths to successfully written reports
    pub fn write_reports_batch(
        &self,
        py: Python<'_>,
        reports: Vec<(String, Vec<String>, bool)>,
    ) -> PyResult<Vec<String>> {
        // Convert String paths to PathBuf
        let reports_pathbuf: Vec<(std::path::PathBuf, Vec<String>, bool)> = reports
            .into_iter()
            .map(|(path, lines, failed)| (std::path::PathBuf::from(path), lines, failed))
            .collect();

        // Release GIL during file I/O
        let result = without_gil(py, || {
            get_runtime()
                .block_on(async { self.inner.write_reports_batch(reports_pathbuf).await })
                .map_err(crate::to_pyerr)
        })?;

        // Convert PathBuf back to String
        Ok(result
            .into_iter()
            .map(|p| p.to_string_lossy().to_string())
            .collect())
    }

    /// Check if a loadorder.txt file exists in the specified directory.
    ///
    /// # Arguments
    /// * `dir_path` - Directory path to check
    ///
    /// # Returns
    /// True if loadorder.txt exists
    #[staticmethod]
    pub fn check_loadorder_exists(dir_path: String) -> bool {
        OrchestratorCore::check_loadorder_exists(std::path::Path::new(&dir_path))
    }

    /// Load plugins from a loadorder.txt file.
    ///
    /// # Arguments
    /// * `py` - Python GIL token
    /// * `loadorder_path` - Path to the loadorder.txt file
    ///
    /// # Returns
    /// Tuple of (plugins_dict, info_lines) where plugins_dict maps plugin names
    /// to their origin marker ("LO")
    pub fn load_loadorder(
        &self,
        py: Python<'_>,
        loadorder_path: String,
    ) -> PyResult<(std::collections::HashMap<String, String>, Vec<String>)> {
        let path = std::path::Path::new(&loadorder_path);

        let result = without_gil(py, || {
            get_runtime()
                .block_on(async { self.inner.load_loadorder_async(path).await })
                .map_err(crate::to_pyerr)
        })?;

        Ok((result.0, result.1.to_list()))
    }

}
