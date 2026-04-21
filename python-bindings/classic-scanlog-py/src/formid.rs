//! Python bindings for FormID analyzers - Thin wrappers over classic-scanlog-core

use classic_scanlog_core::RustFormIDAnalyzer;
use classic_shared::without_gil;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

/// Python wrapper for RustFormIDAnalyzer
#[pyclass(name = "FormIDAnalyzer")]
pub struct PyRustFormIDAnalyzer {
    inner: RustFormIDAnalyzer,
}

impl Default for PyRustFormIDAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyRustFormIDAnalyzer {
    /// Create a new instance
    #[new]
    pub fn new() -> Self {
        Self {
            inner: RustFormIDAnalyzer::new(),
        }
    }

    /// Extract FormIDs from a callstack segment
    ///
    /// Releases GIL during extraction to allow concurrent Python threads.
    #[pyo3(signature = (segment_callstack))]
    pub fn extract_formids(
        &self,
        py: Python<'_>,
        segment_callstack: Vec<String>,
    ) -> PyResult<Vec<String>> {
        // Release GIL during FormID extraction
        Ok(without_gil(py, || {
            self.inner.extract_formids(&segment_callstack)
        }))
    }

    /// Parse and validate a FormID string
    pub fn parse_formid(&self, formid: &str) -> Option<u32> {
        self.inner.parse_formid(formid)
    }

    /// Batch analyze FormIDs with plugin resolution
    ///
    /// Releases GIL during batch analysis to allow concurrent Python threads.
    #[pyo3(signature = (formids, plugins))]
    pub fn analyze_batch(
        &self,
        py: Python<'_>,
        formids: Vec<String>,
        plugins: Bound<'_, PyDict>,
    ) -> PyResult<Vec<(String, Option<String>)>> {
        // Convert PyDict to HashMap<String, String> before releasing GIL
        let plugins_map: HashMap<String, String> = plugins.extract()?;
        // Release GIL during batch analysis
        Ok(without_gil(py, || {
            self.inner.analyze_batch(formids.clone(), &plugins_map)
        }))
    }

    /// Clear all caches
    pub fn clear_cache(&self) {
        self.inner.clear_cache();
    }

    /// Get cache statistics
    pub fn cache_stats(&self) -> (usize, usize) {
        self.inner.cache_stats()
    }
}
