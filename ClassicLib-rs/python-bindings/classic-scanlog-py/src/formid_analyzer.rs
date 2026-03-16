//! Python bindings for FormIDAnalyzerCore - Thin wrapper over classic-scanlog-core

use classic_config_core::ModConflictEntry;
use classic_scanlog_core::FormIDAnalyzerCore;
use classic_shared::{pydict_to_indexmap_str, pydict_to_indexmap_str_optional, without_gil};
use classic_shared_core::get_runtime;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList};

/// Python wrapper for FormIDAnalyzerCore
#[pyclass(name = "FormIDAnalyzerCore")]
pub struct PyFormIDAnalyzerCore {
    inner: FormIDAnalyzerCore,
}

#[pymethods]
impl PyFormIDAnalyzerCore {
    /// Creates a new FormID analyzer with the given configuration.
    ///
    /// # Arguments
    ///
    /// * `show_formid_values` - Whether to display FormID values in output
    /// * `crashgen_name` - Name of the crash generator (e.g., "Buffout 4")
    /// * `important_mods` - Map of important mod names to their identifiers (order preserved)
    /// * `mods_single` - Map of single-byte mod identifiers
    /// * `mods_double` - List of mod conflict entry dicts
    ///
    /// # Returns
    ///
    /// A new `PyFormIDAnalyzerCore` instance ready to analyze FormIDs.
    ///
    /// # Errors
    ///
    /// Returns `PyErr` if the underlying core analyzer fails to initialize.
    #[new]
    #[pyo3(signature = (show_formid_values=false, crashgen_name="".to_string(), important_mods=None, mods_single=None, mods_double=None))]
    pub fn new(
        show_formid_values: bool,
        crashgen_name: String,
        important_mods: Option<&Bound<'_, PyDict>>,
        mods_single: Option<&Bound<'_, PyDict>>,
        mods_double: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let important_mods_map = pydict_to_indexmap_str_optional(important_mods);
        let mods_single_map = pydict_to_indexmap_str_optional(mods_single);
        let mods_double_vec: Vec<ModConflictEntry> = mods_double
            .and_then(|v| v.cast::<PyList>().ok())
            .map(|list| {
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
                            link: dict.get_item("link").ok().flatten().and_then(|v| v.extract::<String>().ok()),
                        })
                    })
                    .collect()
            })
            .unwrap_or_default();
        let inner = FormIDAnalyzerCore::new(
            None,
            show_formid_values,
            crashgen_name,
            important_mods_map,
            mods_single_map,
            mods_double_vec,
        )
        .map_err(crate::to_pyerr)?;
        Ok(Self { inner })
    }

    /// Extract FormIDs from callstack segment
    pub fn extract_formids(&self, segment_callstack: Vec<String>) -> PyResult<Vec<String>> {
        // extract_formids returns Vec<String>, not Result
        Ok(self.inner.extract_formids(segment_callstack))
    }

    /// Match FormIDs against crash log plugins and return formatted report lines.
    ///
    /// This function correlates extracted FormIDs with plugin load order IDs from
    /// the crash log, generating a report section with plugin associations and counts.
    ///
    /// # Arguments
    ///
    /// * `formids` - FormID strings extracted from callstack (e.g., "Form ID: 12345678")
    /// * `crashlog_plugins` - Mapping of plugin names to their load order IDs
    ///
    /// # Returns
    ///
    /// A list of formatted report lines ready for inclusion in the analysis report.
    ///
    /// # Example
    ///
    /// ```python
    /// analyzer = FormIDAnalyzerCore(show_formid_values=True, crashgen_name="Buffout 4")
    /// formids = analyzer.extract_formids(callstack_lines)
    /// report_lines = analyzer.formid_match(formids, plugins_dict)
    /// for line in report_lines:
    ///     print(line)
    /// ```
    pub fn formid_match(
        &self,
        py: Python<'_>,
        formids: Vec<String>,
        crashlog_plugins: &Bound<'_, PyDict>,
    ) -> PyResult<Vec<String>> {
        let plugins_map = pydict_to_indexmap_str(crashlog_plugins)?;
        // Use without_gil to release GIL while running async operation
        without_gil(py, || {
            get_runtime().block_on(async {
                self.inner
                    .formid_match(formids, &plugins_map)
                    .await
                    .map_err(crate::to_pyerr)
            })
        })
    }
}

/// Extract FormIDs from multiple callstack segments (standalone function)
#[pyfunction]
pub fn extract_formids_batch(callstack_segments: Vec<Vec<String>>) -> Vec<Vec<String>> {
    classic_scanlog_core::extract_formids_batch(callstack_segments)
}

/// Validate if a string is a valid FormID (standalone function)
#[pyfunction]
pub fn is_valid_formid(formid: &str) -> bool {
    classic_scanlog_core::is_valid_formid(formid)
}

/// Validate multiple FormIDs (standalone function)
#[pyfunction]
pub fn validate_formids_batch(formids: Vec<String>) -> Vec<bool> {
    classic_scanlog_core::validate_formids_batch(formids)
}
