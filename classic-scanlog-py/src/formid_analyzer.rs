//! Python bindings for FormIDAnalyzerCore - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::FormIDAnalyzerCore;
use pyo3::prelude::*;
use std::collections::HashMap;

/// Python wrapper for FormIDAnalyzerCore
#[pyclass(name = "FormIDAnalyzerCore")]
pub struct PyFormIDAnalyzerCore {
    inner: FormIDAnalyzerCore,
}

#[pymethods]
impl PyFormIDAnalyzerCore {
    #[new]
    #[pyo3(signature = (show_formid_values=false, crashgen_name="".to_string(), important_mods=HashMap::new(), mods_single=HashMap::new(), mods_double=HashMap::new()))]
    pub fn new(
        show_formid_values: bool,
        crashgen_name: String,
        important_mods: HashMap<String, String>,
        mods_single: HashMap<String, String>,
        mods_double: HashMap<String, String>,
    ) -> PyResult<Self> {
        let inner = FormIDAnalyzerCore::new(
            None,  // db_pool not exposed to Python API (would need wrapper)
            show_formid_values,
            crashgen_name,
            important_mods,
            mods_single,
            mods_double,
        ).map_err(crate::to_pyerr)?;
        Ok(Self { inner })
    }

    /// Extract FormIDs from callstack segment
    pub fn extract_formids(
        &self,
        segment_callstack: Vec<String>,
    ) -> PyResult<Vec<String>> {
        // extract_formids returns Vec<String>, not Result
        Ok(self.inner.extract_formids(segment_callstack))
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
