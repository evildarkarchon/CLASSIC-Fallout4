//! Python bindings for PatternMatcher - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::PatternMatcher;
use pyo3::prelude::*;

/// Python wrapper for PatternMatcher
#[pyclass(name = "PatternMatcher")]
pub struct PyPatternMatcher {
    inner: PatternMatcher,
}

#[pymethods]
impl PyPatternMatcher {
    #[new]
    pub fn new(patterns: Vec<String>) -> PyResult<Self> {
        let inner = PatternMatcher::new(patterns).map_err(crate::to_pyerr)?;
        Ok(Self { inner })
    }

    /// Find all matches in text
    pub fn find_all(&self, text: String) -> Vec<(usize, String)> {
        self.inner.find_all(&text)
    }

    /// Check if text has any match
    pub fn has_match(&self, text: String) -> bool {
        self.inner.has_match(&text)
    }

    /// Find first match in text
    pub fn find_first(&self, text: String) -> Option<(usize, String)> {
        self.inner.find_first(&text)
    }

    /// Replace all matches with replacement string
    pub fn replace_all(&self, text: String, replacement: String) -> String {
        self.inner.replace_all(&text, &replacement)
    }

    /// Clear pattern cache
    pub fn clear_cache(&self) {
        self.inner.clear_cache();
    }

    /// Get cache statistics (pattern_count, cache_size)
    pub fn get_stats(&self) -> (usize, usize) {
        self.inner.get_stats()
    }
}
