//! Python bindings for FormIDAnalyzerCore - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::FormIDAnalyzerCore;
use classic_shared::{pydict_to_indexmap_str, without_gil_block_on};
use pyo3::prelude::*;
use pyo3::types::PyDict;

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
    /// # Returns
    ///
    /// A new `PyFormIDAnalyzerCore` instance ready to analyze FormIDs.
    ///
    /// # Errors
    ///
    /// Returns `PyErr` if the underlying core analyzer fails to initialize.
    #[new]
    #[pyo3(signature = (show_formid_values=false, crashgen_name="".to_string()))]
    pub fn new(show_formid_values: bool, crashgen_name: String) -> PyResult<Self> {
        let inner = FormIDAnalyzerCore::new(None, show_formid_values, crashgen_name)
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
        // Release the GIL while running async FormID matching on the shared runtime.
        without_gil_block_on(py, || async {
            self.inner
                .formid_match(formids, &plugins_map)
                .await
                .map_err(crate::to_pyerr)
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
