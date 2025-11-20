//! Python bindings for FormID analyzers - Thin wrappers over classic-scanlog-core

use classic_scanlog_core::{FormIDAnalyzer, RustFormIDAnalyzer};
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
    #[pyo3(signature = (segment_callstack))]
    pub fn extract_formids(&self, segment_callstack: Vec<String>) -> PyResult<Vec<String>> {
        // extract_formids returns Vec<String>, not Result
        Ok(self.inner.extract_formids(&segment_callstack))
    }

    /// Parse and validate a FormID string
    pub fn parse_formid(&self, formid: &str) -> Option<u32> {
        self.inner.parse_formid(formid)
    }

    /// Batch analyze FormIDs with plugin resolution
    #[pyo3(signature = (formids, plugins))]
    pub fn analyze_batch(
        &self,
        formids: Vec<String>,
        plugins: Bound<'_, PyDict>,
    ) -> PyResult<Vec<(String, Option<String>)>> {
        // Convert PyDict to HashMap<String, String>
        let plugins_map: HashMap<String, String> = plugins.extract()?;
        // analyze_batch returns Vec<...>, not Result
        Ok(self.inner.analyze_batch(formids, &plugins_map))
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

/// Python wrapper for FormIDAnalyzer (backward compatibility)
#[pyclass(name = "FormIDAnalyzer")]
pub struct PyFormIDAnalyzer {
    inner: FormIDAnalyzer,
}

impl Default for PyFormIDAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyFormIDAnalyzer {
    /// Create a new instance
    #[new]
    pub fn new() -> Self {
        Self {
            inner: FormIDAnalyzer::new(),
        }
    }

    /// Extract FormIDs from a callstack segment
    #[pyo3(signature = (segment_callstack))]
    pub fn extract_formids(&self, segment_callstack: Vec<String>) -> PyResult<Vec<String>> {
        // extract_formids returns Vec<String>, not Result
        Ok(self.inner.extract_formids(&segment_callstack))
    }

    /// Parse and validate a FormID string
    pub fn parse_formid(&self, formid: &str) -> Option<u32> {
        self.inner.parse_formid(formid)
    }

    /// Batch analyze FormIDs with plugin resolution
    #[pyo3(signature = (formids, plugins))]
    pub fn analyze_batch(
        &self,
        formids: Vec<String>,
        plugins: Bound<'_, PyDict>,
    ) -> PyResult<Vec<(String, Option<String>)>> {
        // Convert PyDict to HashMap<String, String>
        let plugins_map: HashMap<String, String> = plugins.extract()?;
        // analyze_batch returns Vec<...>, not Result
        Ok(self.inner.analyze_batch(formids, &plugins_map))
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
