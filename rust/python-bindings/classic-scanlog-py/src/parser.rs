//! Python bindings for LogParser - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::LogParser;
use classic_shared::without_gil;
use pyo3::prelude::*;
use pyo3::types::{PyList, PyString};
use std::collections::HashMap;
use std::sync::Arc;

/// Helper to convert Vec<String> to Vec<Arc<str>> for core library
fn to_arc_str_vec(strings: &[String]) -> Vec<Arc<str>> {
    strings.iter().map(|s| Arc::from(s.as_str())).collect()
}

/// Python-facing log parser wrapper
#[pyclass(name = "LogParser")]
pub struct PyLogParser {
    inner: LogParser,
}

#[pymethods]
impl PyLogParser {
    /// Creates a new log parser with optional custom segment boundaries.
    ///
    /// This constructor initializes a parser that can analyze Bethesda game crash logs
    /// using SIMD-optimized boundary detection and pattern matching. The parser supports
    /// automatic GIL release for large operations and comprehensive caching.
    ///
    /// # Arguments
    ///
    /// * `custom_boundaries` - Optional list of (start_marker, end_marker) tuples defining
    ///   custom log segment boundaries. If `None`, uses default boundaries for standard
    ///   Fallout 4/Skyrim crash logs.
    ///
    /// # Returns
    ///
    /// A new `PyLogParser` instance ready to parse crash logs.
    ///
    /// # Errors
    ///
    /// Returns `PyErr` if the underlying core parser fails to initialize (e.g., invalid
    /// boundary patterns or regex compilation errors).
    ///
    /// # Example
    ///
    /// ```python
    /// # Python usage
    /// from classic_core import LogParser
    ///
    /// # Default boundaries
    /// parser = LogParser()
    ///
    /// # Custom boundaries
    /// parser = LogParser([("START", "END"), ("BEGIN", "FINISH")])
    /// ```
    #[new]
    #[pyo3(signature = (custom_boundaries=None))]
    pub fn new(custom_boundaries: Option<Vec<(String, String)>>) -> PyResult<Self> {
        let inner = LogParser::new(custom_boundaries).map_err(crate::to_pyerr)?;
        Ok(Self { inner })
    }

    /// Add a custom regex pattern for matching
    pub fn add_pattern(&self, name: String, pattern: String) -> PyResult<()> {
        self.inner
            .add_pattern(&name, &pattern)
            .map_err(crate::to_pyerr)
    }

    /// Clear all caches to free memory
    pub fn clear_caches(&self) {
        self.inner.clear_caches();
    }

    /// Parse log into segments using SIMD-optimized boundary detection
    ///
    /// For large logs (>1000 lines), this releases the GIL to allow other Python threads to run.
    pub fn parse_segments<'py>(
        &self,
        py: Python<'py>,
        lines: Vec<String>,
    ) -> PyResult<Bound<'py, PyList>> {
        let arc_lines = to_arc_str_vec(&lines);

        // Release GIL for large parsing operations
        let result = if lines.len() > 1000 {
            without_gil(py, || self.inner.parse_segments(&arc_lines))
        } else {
            // Keep GIL for small operations (overhead not worth it)
            self.inner.parse_segments(&arc_lines)
        };

        // Convert result back to list[list[str]] without intermediate String allocation
        let mut outer_items = Vec::with_capacity(result.len());
        for segment in result {
            // Create PyString directly from Arc<str> reference (no String allocation)
            let inner_items = segment.iter().map(|line| PyString::new(py, line));
            let inner_list = PyList::new(py, inner_items)?;
            outer_items.push(inner_list);
        }
        PyList::new(py, outer_items)
    }

    /// Parse segments in parallel for large logs
    ///
    /// This operation always releases the GIL to allow other Python threads to run concurrently.
    #[pyo3(name = "parse_segments_parallel", signature = (lines, chunk_size=None))]
    pub fn parse_segments_parallel<'py>(
        &self,
        py: Python<'py>,
        lines: Vec<String>,
        chunk_size: Option<usize>,
    ) -> PyResult<Bound<'py, PyList>> {
        let arc_lines = to_arc_str_vec(&lines);

        // Always release GIL for parallel operations
        let result = without_gil(py, || {
            self.inner.parse_segments_parallel(&arc_lines, chunk_size)
        });

        // Convert result back to list[list[str]] without intermediate String allocation
        let mut outer_items = Vec::with_capacity(result.len());
        for segment in result {
            // Create PyString directly from Arc<str> reference (no String allocation)
            let inner_items = segment.iter().map(|line| PyString::new(py, line));
            let inner_list = PyList::new(py, inner_items)?;
            outer_items.push(inner_list);
        }
        PyList::new(py, outer_items)
    }

    /// Find all pattern matches in parallel with caching
    ///
    /// For large logs (>1000 lines), this releases the GIL to allow other Python threads to run.
    pub fn find_patterns(
        &self,
        py: Python<'_>,
        lines: Vec<String>,
    ) -> Vec<(usize, String, String)> {
        // Release GIL for large pattern matching
        if lines.len() > 1000 {
            without_gil(py, || self.inner.find_patterns(&lines))
        } else {
            self.inner.find_patterns(&lines)
        }
    }

    /// Find patterns in parallel chunks for better performance
    ///
    /// This operation always releases the GIL to allow other Python threads to run concurrently.
    #[pyo3(name = "find_patterns_chunked", signature = (lines, chunk_size=None))]
    pub fn find_patterns_chunked(
        &self,
        py: Python<'_>,
        lines: Vec<String>,
        chunk_size: Option<usize>,
    ) -> Vec<(usize, String, String)> {
        // Always release GIL for chunked/parallel operations
        without_gil(py, || self.inner.find_patterns_chunked(&lines, chunk_size))
    }

    /// Extract section from log (Python-exposed method)
    #[pyo3(name = "extract_section")]
    pub fn py_extract_section(
        &self,
        lines: Vec<String>,
        start_marker: String,
        end_marker: String,
    ) -> Option<Vec<String>> {
        self.inner
            .extract_section(&lines, &start_marker, &end_marker)
    }

    /// Extract multiple sections batch (Python-exposed method)
    #[pyo3(name = "extract_sections_batch")]
    pub fn py_extract_sections_batch(
        &self,
        lines: Vec<String>,
        markers: Vec<(String, String)>,
    ) -> Vec<Option<Vec<String>>> {
        self.inner.extract_sections_batch(&lines, &markers)
    }

    /// Parse crash header (Python-exposed method)
    #[pyo3(name = "parse_crash_header")]
    pub fn py_parse_crash_header(&self, lines: Vec<String>) -> PyResult<HashMap<String, String>> {
        self.inner
            .parse_crash_header(&lines)
            .map_err(crate::to_pyerr)
    }

    /// Get specific section by name (commonly used sections)
    #[pyo3(name = "get_section")]
    pub fn get_section(&self, lines: Vec<String>, section_name: String) -> Option<Vec<String>> {
        self.inner.get_section(&lines, &section_name)
    }

    /// Parse and extract all important sections at once
    #[pyo3(name = "parse_all_sections")]
    pub fn parse_all_sections(&self, lines: Vec<String>) -> HashMap<String, Vec<String>> {
        self.inner.parse_all_sections(&lines)
    }

    /// Optimized batch operation: complete log analysis in single FFI call
    #[pyo3(name = "parse_complete")]
    pub fn parse_complete(
        &self,
        lines: Vec<String>,
        segment_boundaries: Vec<(String, String)>,
        xse_acronym: String,
    ) -> PyResult<(String, String, String, Vec<Vec<String>>)> {
        self.inner
            .parse_complete(&lines, &segment_boundaries, &xse_acronym)
            .map_err(crate::to_pyerr)
    }

    /// Count lines in each segment for analysis
    #[pyo3(name = "get_segment_sizes")]
    pub fn get_segment_sizes(&self, lines: Vec<String>) -> HashMap<String, usize> {
        self.inner.get_segment_sizes(&lines)
    }

    /// Get performance statistics
    pub fn get_stats(&self) -> HashMap<String, usize> {
        self.inner.get_stats()
    }

    /// Find all FormIDs in the log using optimized pattern matching
    #[pyo3(name = "extract_formids")]
    pub fn extract_formids(&self, lines: Vec<String>) -> Vec<String> {
        self.inner.extract_formids(&lines)
    }

    /// Find all plugins mentioned in the log
    #[pyo3(name = "extract_plugins")]
    pub fn extract_plugins(&self, lines: Vec<String>) -> Vec<(String, String)> {
        self.inner.extract_plugins(&lines)
    }

    /// Find all memory addresses in the log
    #[pyo3(name = "extract_addresses")]
    pub fn extract_addresses(&self, lines: Vec<String>) -> Vec<String> {
        self.inner.extract_addresses(&lines)
    }

    /// Find error and exception patterns
    #[pyo3(name = "find_errors")]
    pub fn find_errors(&self, lines: Vec<String>) -> Vec<(usize, String)> {
        self.inner.find_errors(&lines)
    }

    /// Benchmark parsing performance on given data
    #[pyo3(name = "benchmark")]
    pub fn benchmark(&self, lines: Vec<String>, iterations: usize) -> HashMap<String, f64> {
        let arc_lines = to_arc_str_vec(&lines);
        self.inner.benchmark(&arc_lines, iterations)
    }
}
