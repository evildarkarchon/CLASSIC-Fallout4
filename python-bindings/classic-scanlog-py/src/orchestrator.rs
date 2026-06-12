//! Python bindings for OrchestratorCore - Thin wrapper over classic-scanlog-core

use classic_config_core::{
    ModSolutionCriteria, SuspectErrorRule, SuspectStackCountRule, SuspectStackRule, YamlDataCore,
};
use classic_database_core::DatabasePool;
use classic_scanlog_core::{
    AnalysisConfig, AnalysisResult, BatchScanEventKind, BatchScanOptions, OrchestratorCore,
    build_analysis_config_from_yaml,
};
use classic_shared::without_gil_block_on;
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use crate::core_mod_convert::exclude_when_to_pydict;
use crate::py_adapters::{
    core_mod_entries_from_attr, core_mod_entries_from_py, mod_conflict_entries_from_attr,
    mod_conflict_entries_from_py, mod_solution_entries_from_attr, mod_solution_entries_from_py,
    parse_crashgen_registry_from_py, string_attr_or_default, vec_string_attr_or_default,
};

macro_rules! required_field {
    ($dict:expr, $key:literal, $context:expr, $ty:ty) => {{
        $dict
            .get_item($key)?
            .ok_or_else(|| PyValueError::new_err(format!("missing {}.{}", $context, $key)))?
            .extract::<$ty>()
            .map_err(|err| {
                PyTypeError::new_err(format!("invalid {}.{}: {}", $context, $key, err))
            })?
    }};
}

macro_rules! analysis_config_pymethods {
    (
        clone: [$(($clone_getter:ident, $clone_setter:ident, $clone_field:ident, $clone_ty:ty, $clone_getter_doc:literal, $clone_setter_doc:literal)),+ $(,)?],
        copy: [$(($copy_getter:ident, $copy_setter:ident, $copy_field:ident, $copy_ty:ty, $copy_getter_doc:literal, $copy_setter_doc:literal)),+ $(,)?],
        $($method:item)*
    ) => {
        #[pymethods]
        impl PyAnalysisConfig {
            $(
                #[doc = $clone_getter_doc]
                #[getter]
                pub fn $clone_getter(&self) -> $clone_ty {
                    self.inner.$clone_field.clone()
                }

                #[doc = $clone_setter_doc]
                #[setter]
                pub fn $clone_setter(&mut self, value: $clone_ty) {
                    self.inner.$clone_field = value;
                }
            )+

            $(
                #[doc = $copy_getter_doc]
                #[getter]
                pub fn $copy_getter(&self) -> $copy_ty {
                    self.inner.$copy_field
                }

                #[doc = $copy_setter_doc]
                #[setter]
                pub fn $copy_setter(&mut self, value: $copy_ty) {
                    self.inner.$copy_field = value;
                }
            )+

            $($method)*
        }
    };
}

fn extract_suspect_error_rules(
    yamldata: &Bound<'_, PyAny>,
    attr_name: &str,
) -> PyResult<Vec<SuspectErrorRule>> {
    let Ok(attr) = yamldata.getattr(attr_name) else {
        return Ok(Vec::new());
    };
    let Ok(list) = attr.extract::<Vec<Bound<'_, PyAny>>>() else {
        return Ok(Vec::new());
    };

    parse_suspect_error_rules(&list, attr_name)
}

fn extract_suspect_stack_rules(
    yamldata: &Bound<'_, PyAny>,
    attr_name: &str,
) -> PyResult<Vec<SuspectStackRule>> {
    let Ok(attr) = yamldata.getattr(attr_name) else {
        return Ok(Vec::new());
    };
    let Ok(list) = attr.extract::<Vec<Bound<'_, PyAny>>>() else {
        return Ok(Vec::new());
    };

    parse_suspect_stack_rules(&list, attr_name)
}

fn parse_suspect_error_rules(
    list: &[Bound<'_, PyAny>],
    context_prefix: &str,
) -> PyResult<Vec<SuspectErrorRule>> {
    list.iter()
        .enumerate()
        .map(|(index, item)| -> PyResult<_> {
            let context = format!("{context_prefix}[{index}]");
            let dict = item
                .cast::<PyDict>()
                .map_err(|_| PyTypeError::new_err(format!("{context} must be a dict")))?;

            Ok(SuspectErrorRule {
                id: required_field!(dict, "id", context.as_str(), String),
                name: required_field!(dict, "name", context.as_str(), String),
                severity: required_field!(dict, "severity", context.as_str(), i32),
                main_error_contains_any: required_field!(
                    dict,
                    "main_error_contains_any",
                    context.as_str(),
                    Vec<String>
                ),
            })
        })
        .collect()
}

fn parse_suspect_stack_count_rules(
    dict: &Bound<'_, PyDict>,
    context: &str,
) -> PyResult<Vec<SuspectStackCountRule>> {
    required_field!(
        dict,
        "stack_contains_at_least",
        context,
        Vec<Bound<'_, PyAny>>
    )
    .iter()
    .enumerate()
    .map(|(count_index, count_item)| -> PyResult<_> {
        let count_context = format!("{context}.stack_contains_at_least[{count_index}]");
        let count_dict = count_item
            .cast::<PyDict>()
            .map_err(|_| PyTypeError::new_err(format!("{count_context} must be a dict")))?;

        Ok(SuspectStackCountRule {
            substring: required_field!(count_dict, "substring", count_context.as_str(), String),
            count: required_field!(count_dict, "count", count_context.as_str(), usize),
        })
    })
    .collect()
}

fn parse_suspect_stack_rules(
    list: &[Bound<'_, PyAny>],
    context_prefix: &str,
) -> PyResult<Vec<SuspectStackRule>> {
    list.iter()
        .enumerate()
        .map(|(index, item)| -> PyResult<_> {
            let context = format!("{context_prefix}[{index}]");
            let dict = item
                .cast::<PyDict>()
                .map_err(|_| PyTypeError::new_err(format!("{context} must be a dict")))?;
            let count_rules = parse_suspect_stack_count_rules(dict, context.as_str())?;

            Ok(SuspectStackRule {
                id: required_field!(dict, "id", context.as_str(), String),
                name: required_field!(dict, "name", context.as_str(), String),
                severity: required_field!(dict, "severity", context.as_str(), i32),
                main_error_required_any: required_field!(
                    dict,
                    "main_error_required_any",
                    context.as_str(),
                    Vec<String>
                ),
                main_error_optional_any: required_field!(
                    dict,
                    "main_error_optional_any",
                    context.as_str(),
                    Vec<String>
                ),
                stack_contains_any: required_field!(
                    dict,
                    "stack_contains_any",
                    context.as_str(),
                    Vec<String>
                ),
                exclude_if_stack_contains_any: required_field!(
                    dict,
                    "exclude_if_stack_contains_any",
                    context.as_str(),
                    Vec<String>
                ),
                stack_contains_at_least: count_rules,
            })
        })
        .collect()
}

fn pyany_to_suspect_error_rules(value: &Bound<'_, PyAny>) -> PyResult<Vec<SuspectErrorRule>> {
    let list = value.extract::<Vec<Bound<'_, PyAny>>>()?;
    parse_suspect_error_rules(&list, "suspect_error_rules")
}

fn pyany_to_suspect_stack_rules(value: &Bound<'_, PyAny>) -> PyResult<Vec<SuspectStackRule>> {
    let list = value.extract::<Vec<Bound<'_, PyAny>>>()?;
    parse_suspect_stack_rules(&list, "suspect_stack_rules")
}

fn adapt_yamldata_to_core(yamldata: &Bound<'_, PyAny>) -> PyResult<YamlDataCore> {
    let crashgen_registry = yamldata
        .getattr("crashgen_registry")
        .ok()
        .map(|attr| parse_crashgen_registry_from_py(&attr))
        .unwrap_or_default();
    let mut classic_version = string_attr_or_default(yamldata, "classic_version");
    if classic_version.is_empty() {
        classic_version = "CLASSIC".to_string();
    }

    Ok(YamlDataCore {
        classic_game_hints: vec_string_attr_or_default(yamldata, "classic_game_hints"),
        classic_records_list: vec_string_attr_or_default(yamldata, "classic_records_list"),
        classic_version,
        classic_version_date: string_attr_or_default(yamldata, "classic_version_date"),
        crashgen_name: string_attr_or_default(yamldata, "crashgen_name"),
        crashgen_latest_og: string_attr_or_default(yamldata, "crashgen_latest_og"),
        crashgen_ignore: vec_string_attr_or_default(yamldata, "crashgen_ignore"),
        warn_noplugins: string_attr_or_default(yamldata, "warn_noplugins"),
        warn_outdated: string_attr_or_default(yamldata, "warn_outdated"),
        xse_acronym: string_attr_or_default(yamldata, "xse_acronym"),
        game_ignore_plugins: vec_string_attr_or_default(yamldata, "game_ignore_plugins"),
        game_ignore_records: vec_string_attr_or_default(yamldata, "game_ignore_records"),
        ignore_list: vec_string_attr_or_default(yamldata, "ignore_list"),
        suspect_error_rules: extract_suspect_error_rules(yamldata, "suspect_error_rules")?,
        suspect_stack_rules: extract_suspect_stack_rules(yamldata, "suspect_stack_rules")?,
        game_mods_conf: mod_conflict_entries_from_attr(yamldata, "game_mods_conf"),
        game_mods_core: core_mod_entries_from_attr(yamldata, "game_mods_core"),
        game_mods_freq: mod_solution_entries_from_attr(yamldata, "game_mods_freq"),
        game_mods_solu: mod_solution_entries_from_attr(yamldata, "game_mods_solu"),
        autoscan_text: string_attr_or_default(yamldata, "autoscan_text"),
        game_version: string_attr_or_default(yamldata, "game_version"),
        game_root_name: string_attr_or_default(yamldata, "game_root_name"),
        crashgen_registry,
    })
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
#[pyclass(name = "CancellationToken", from_py_object)]
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
#[pyclass(name = "AnalysisConfig", from_py_object)]
#[derive(Clone)]
pub struct PyAnalysisConfig {
    /// Inner Rust AnalysisConfig instance
    pub(crate) inner: AnalysisConfig,
}

analysis_config_pymethods! {
    clone: [
        (game, set_game, game, String, "Get the game identifier", "Set the game identifier"),
        (
            crashgen_name,
            set_crashgen_name,
            crashgen_name,
            String,
            "Get the crash generator name",
            "Set the crash generator name"
        ),
        (
            crashgen_latest,
            set_crashgen_latest,
            crashgen_latest,
            String,
            "Get the latest crash generator version",
            "Set the latest crash generator version"
        ),
        (
            game_version,
            set_game_version,
            game_version,
            String,
            "Get the game version",
            "Set the game version"
        ),
        (
            game_version_vr,
            set_game_version_vr,
            game_version_vr,
            String,
            "Get the VR game version",
            "Set the VR game version"
        ),
        (
            xse_acronym,
            set_xse_acronym,
            xse_acronym,
            String,
            "Get the XSE (script extender) acronym",
            "Set the XSE (script extender) acronym"
        ),
        (
            ignore_plugins,
            set_ignore_plugins,
            ignore_plugins,
            Vec<String>,
            "Get the list of plugins to ignore during analysis",
            "Set the list of plugins to ignore during analysis"
        ),
        (
            ignore_records,
            set_ignore_records,
            ignore_records,
            Vec<String>,
            "Get the list of records to ignore during analysis",
            "Set the list of records to ignore during analysis"
        ),
        (
            ignore_list,
            set_ignore_list,
            ignore_list,
            Vec<String>,
            "Get the general ignore list",
            "Set the general ignore list"
        ),
        (
            crashgen_latest_vr,
            set_crashgen_latest_vr,
            crashgen_latest_vr,
            String,
            "Get the latest VR crashgen version",
            "Set the latest VR crashgen version"
        ),
        (
            game_root_name,
            set_game_root_name,
            game_root_name,
            String,
            "Get the game root name (e.g., Fallout4)",
            "Set the game root name"
        ),
        (
            classic_version,
            set_classic_version,
            classic_version,
            String,
            "Get the CLASSIC version string",
            "Set the CLASSIC version string"
        ),
        (
            remove_list,
            set_remove_list,
            remove_list,
            Vec<String>,
            "Get the list of strings to remove when simplifying logs",
            "Set the list of strings to remove when simplifying logs"
        ),
        (
            classic_records_list,
            set_classic_records_list,
            classic_records_list,
            Vec<String>,
            "Get the list of named records to scan for",
            "Set the list of named records to scan for"
        ),
    ],
    copy: [
        (
            show_formid_values,
            set_show_formid_values,
            show_formid_values,
            bool,
            "Get whether to show FormID values in reports",
            "Set whether to show FormID values in reports"
        ),
        (
            fcx_mode,
            set_fcx_mode,
            fcx_mode,
            bool,
            "Get whether FCX mode is enabled",
            "Set whether FCX mode is enabled"
        ),
        (
            simplify_logs,
            set_simplify_logs,
            simplify_logs,
            bool,
            "Get whether to simplify logs by removing strings",
            "Set whether to simplify logs"
        ),
    ],


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
        let yaml_core = adapt_yamldata_to_core(yamldata)?;
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

    /// Get the structured suspect error rules.
    #[getter]
    pub fn suspect_error_rules(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyList>> {
        let list = pyo3::types::PyList::empty(py);
        for rule in &self.inner.suspect_error_rules {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("id", &rule.id)?;
            dict.set_item("name", &rule.name)?;
            dict.set_item("severity", rule.severity)?;
            dict.set_item("main_error_contains_any", &rule.main_error_contains_any)?;
            list.append(dict)?;
        }
        Ok(list.into())
    }

    /// Set the structured suspect error rules.
    #[setter]
    pub fn set_suspect_error_rules(
        &mut self,
        value: &Bound<'_, pyo3::types::PyAny>,
    ) -> PyResult<()> {
        self.inner.suspect_error_rules = pyany_to_suspect_error_rules(value)?;
        Ok(())
    }

    /// Get the structured suspect stack rules.
    #[getter]
    pub fn suspect_stack_rules(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyList>> {
        let list = pyo3::types::PyList::empty(py);
        for rule in &self.inner.suspect_stack_rules {
            let dict = pyo3::types::PyDict::new(py);
            let count_rules = pyo3::types::PyList::empty(py);
            for count_rule in &rule.stack_contains_at_least {
                let count_dict = pyo3::types::PyDict::new(py);
                count_dict.set_item("substring", &count_rule.substring)?;
                count_dict.set_item("count", count_rule.count)?;
                count_rules.append(count_dict)?;
            }
            dict.set_item("id", &rule.id)?;
            dict.set_item("name", &rule.name)?;
            dict.set_item("severity", rule.severity)?;
            dict.set_item("main_error_required_any", &rule.main_error_required_any)?;
            dict.set_item("main_error_optional_any", &rule.main_error_optional_any)?;
            dict.set_item("stack_contains_any", &rule.stack_contains_any)?;
            dict.set_item(
                "exclude_if_stack_contains_any",
                &rule.exclude_if_stack_contains_any,
            )?;
            dict.set_item("stack_contains_at_least", count_rules)?;
            list.append(dict)?;
        }
        Ok(list.into())
    }

    /// Set the structured suspect stack rules.
    #[setter]
    pub fn set_suspect_stack_rules(
        &mut self,
        value: &Bound<'_, pyo3::types::PyAny>,
    ) -> PyResult<()> {
        self.inner.suspect_stack_rules = pyany_to_suspect_stack_rules(value)?;
        Ok(())
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
            dict.set_item("gpu_mismatch_warning", &entry.gpu_mismatch_warning)?;
            if let Some(ew_dict) = exclude_when_to_pydict(py, &entry.exclude_when)? {
                dict.set_item("exclude_when", ew_dict)?;
            }
            list.append(dict)?;
        }
        Ok(list.into())
    }

    /// Set the core mods database from a list of dicts
    #[setter]
    pub fn set_mods_core(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        if let Some(entries) = core_mod_entries_from_py(value) {
            self.inner.mods_core = entries;
        }
    }

    /// Get the frequently problematic mods database
    #[getter]
    pub fn mods_freq(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyList>> {
        let list = pyo3::types::PyList::empty(py);
        for entry in &self.inner.mods_freq {
            let dict = pyo3::types::PyDict::new(py);
            let criteria = pyo3::types::PyDict::new(py);
            match &entry.criteria {
                ModSolutionCriteria::Any(values) => criteria.set_item("any", values)?,
                ModSolutionCriteria::All(values) => criteria.set_item("all", values)?,
            }
            dict.set_item("id", &entry.id)?;
            dict.set_item("criteria", criteria)?;
            dict.set_item("exceptions", &entry.exceptions)?;
            dict.set_item("name", &entry.name)?;
            dict.set_item("description", &entry.description)?;
            list.append(dict)?;
        }
        Ok(list.into())
    }

    /// Set the frequently problematic mods database (preserves insertion order)
    #[setter]
    pub fn set_mods_freq(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        if let Some(entries) = mod_solution_entries_from_py(value) {
            self.inner.mods_freq = entries;
        }
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
        self.inner.mods_conf = mod_conflict_entries_from_py(value).unwrap_or_default();
    }

    /// Get the mod solutions database
    #[getter]
    pub fn mods_solu(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyList>> {
        let list = pyo3::types::PyList::empty(py);
        for entry in &self.inner.mods_solu {
            let dict = pyo3::types::PyDict::new(py);
            let criteria = pyo3::types::PyDict::new(py);
            match &entry.criteria {
                ModSolutionCriteria::Any(values) => criteria.set_item("any", values)?,
                ModSolutionCriteria::All(values) => criteria.set_item("all", values)?,
            }
            dict.set_item("id", &entry.id)?;
            dict.set_item("criteria", criteria)?;
            dict.set_item("exceptions", &entry.exceptions)?;
            dict.set_item("name", &entry.name)?;
            dict.set_item("description", &entry.description)?;
            list.append(dict)?;
        }
        Ok(list.into())
    }

    /// Set the mod solutions database (preserves insertion order)
    #[setter]
    pub fn set_mods_solu(&mut self, value: &Bound<'_, pyo3::types::PyAny>) {
        self.inner.mods_solu = mod_solution_entries_from_py(value).unwrap_or_default();
    }


}

/// Python wrapper for AnalysisResult
///
/// Contains the results of analyzing a crash log, including the generated report,
/// statistics, and any errors encountered during processing.
#[pyclass(name = "AnalysisResult", from_py_object)]
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
        let result = without_gil_block_on(py, || async { self.inner.process_log(log_path).await })
            .map_err(crate::to_pyerr)?;
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
        if log_paths.is_empty() {
            return Ok(Vec::new());
        }

        let total = log_paths.len();
        let cancellation = cancellation_token.map(|t| t.inner.clone());
        let callback: Option<Arc<Py<PyAny>>> =
            progress_callback.map(|cb| Arc::new(cb.clone_ref(py)));

        let indexed_results = without_gil_block_on(py, || async {
            self.inner
                .process_logs_batch_with_events(
                    log_paths,
                    BatchScanOptions {
                        max_concurrent,
                        preserve_order: true,
                        cancellation,
                    },
                    |event| {
                        if !matches!(
                            event.kind,
                            BatchScanEventKind::Completed | BatchScanEventKind::Failed
                        ) {
                            return;
                        }
                        if let Some(ref cb) = callback {
                            let current = event.input_index + 1;
                            let filename = event.log_path.clone();
                            Python::attach(|py_inner| {
                                let _ = cb.call1(py_inner, (current, total, filename));
                            });
                        }
                    },
                )
                .await
        });

        let results = indexed_results
            .into_iter()
            .map(|indexed| PyAnalysisResult {
                inner: indexed.result,
            })
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
        without_gil_block_on(py, || async { pool.initialize(paths).await }).map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!(
                "Database initialization failed: {}",
                e
            ))
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
        let result = without_gil_block_on(py, || async {
            self.inner.write_reports_batch(reports_pathbuf).await
        })
        .map_err(crate::to_pyerr)?;

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

        let result =
            without_gil_block_on(py, || async { self.inner.load_loadorder_async(path).await })
                .map_err(crate::to_pyerr)?;

        Ok((result.0, result.1.to_list()))
    }
}

#[cfg(test)]
#[path = "orchestrator_tests.rs"]
mod tests;
