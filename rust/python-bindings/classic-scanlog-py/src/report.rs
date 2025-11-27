//! Python bindings for report generation - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::{ReportComposer, ReportFragment, ReportGenerator, StringPool};
use pyo3::prelude::*;

/// Python wrapper for StringPool
#[pyclass(name = "StringPool")]
#[derive(Clone)]
pub struct PyStringPool {
    inner: StringPool,
}

impl Default for PyStringPool {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyStringPool {
    /// Create a new string pool for string interning
    #[new]
    pub fn new() -> Self {
        Self {
            inner: StringPool::new(),
        }
    }

    /// Intern a string
    pub fn intern(&self, s: String) -> String {
        self.inner.intern(&s)
    }

    /// Intern multiple strings in parallel
    pub fn intern_batch(&self, strings: Vec<String>) -> Vec<String> {
        self.inner.intern_batch(&strings)
    }

    /// Get pool statistics
    pub fn get_stats(&self) -> (usize, usize, usize, usize) {
        self.inner.get_stats()
    }

    /// Clear the pool
    pub fn clear(&self) {
        self.inner.clear();
    }
}

/// Python wrapper for ReportFragment
#[pyclass(name = "ReportFragment")]
#[derive(Clone)]
pub struct PyReportFragment {
    inner: ReportFragment,
}

#[pymethods]
impl PyReportFragment {
    /// Create a new report fragment, optionally with initial lines
    #[new]
    #[pyo3(signature = (lines=None))]
    pub fn new(lines: Option<Vec<String>>) -> Self {
        let inner = if let Some(lines) = lines {
            ReportFragment::from_lines(lines)
        } else {
            ReportFragment::empty()
        };
        Self { inner }
    }

    /// Create an empty report fragment
    #[staticmethod]
    pub fn empty() -> Self {
        Self {
            inner: ReportFragment::empty(),
        }
    }

    /// Create a report fragment from a list of lines
    #[staticmethod]
    pub fn from_lines(lines: Vec<String>) -> Self {
        Self {
            inner: ReportFragment::from_lines(lines),
        }
    }

    /// Add a header to this fragment
    pub fn with_header(&self, header_lines: Vec<String>) -> Self {
        Self {
            inner: self.inner.with_header(header_lines),
        }
    }

    /// Combine two fragments
    pub fn combine(&self, other: &PyReportFragment) -> Self {
        Self {
            inner: self.inner.combine(&other.inner),
        }
    }

    /// Convert to a list of strings
    pub fn to_list(&self) -> Vec<String> {
        self.inner.to_list()
    }

    /// Get the number of lines
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

/// Python wrapper for ReportComposer
#[pyclass(name = "ReportComposer")]
pub struct PyReportComposer {
    inner: ReportComposer,
}

impl Default for PyReportComposer {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyReportComposer {
    /// Create a new report composer for assembling report fragments
    #[new]
    pub fn new() -> Self {
        Self {
            inner: ReportComposer::new(),
        }
    }

    /// Add a fragment to the composer
    pub fn add(&mut self, fragment: PyReportFragment) {
        self.inner.add(fragment.inner);
    }

    /// Add multiple fragments
    pub fn add_many(&mut self, fragments: Vec<PyReportFragment>) {
        let inner_fragments = fragments.into_iter().map(|f| f.inner).collect::<Vec<_>>();
        self.inner.add_many(inner_fragments);
    }

    /// Compose all fragments into final report
    pub fn compose(&self) -> Vec<String> {
        self.inner.compose().to_list()
    }

    /// Compose all fragments with optimization
    pub fn compose_optimized(&self) -> Vec<String> {
        self.inner.compose_optimized().to_list()
    }

    /// Build as a single string
    pub fn build_string(&self) -> String {
        self.inner.build_string()
    }

    /// Get number of fragments
    pub fn fragment_count(&self) -> usize {
        self.inner.fragment_count()
    }

    /// Get pool statistics (size, lookups, hits, insertions)
    pub fn pool_stats(&self) -> (usize, usize, usize, usize) {
        self.inner.get_pool_stats()
    }
}

/// Python wrapper for ReportGenerator
#[pyclass(name = "ReportGenerator")]
pub struct PyReportGenerator {
    inner: ReportGenerator,
}

impl Default for PyReportGenerator {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyReportGenerator {
    /// Create a new report generator for creating standardized report sections
    #[new]
    pub fn new() -> Self {
        Self {
            inner: ReportGenerator::new(),
        }
    }

    /// Generate header fragment
    pub fn generate_header(&self, filename: String, version: String) -> PyReportFragment {
        PyReportFragment {
            inner: self.inner.generate_header(&filename, &version),
        }
    }

    /// Generate error section
    pub fn generate_error_section(
        &self,
        main_error: String,
        crashgen_version: String,
        crashgen_name: String,
        is_latest: bool,
        warn_outdated: String,
    ) -> PyReportFragment {
        PyReportFragment {
            inner: self.inner.generate_error_section(
                &main_error,
                &crashgen_version,
                &crashgen_name,
                is_latest,
                &warn_outdated,
            ),
        }
    }

    /// Generate suspect section
    pub fn generate_suspect_section(&self, found_suspects: Vec<String>) -> PyReportFragment {
        PyReportFragment {
            inner: self.inner.generate_suspect_section(found_suspects),
        }
    }
}

/// Python wrapper for ParallelReportProcessor
#[pyclass(name = "ParallelReportProcessor")]
pub struct PyParallelReportProcessor;

impl Default for PyParallelReportProcessor {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyParallelReportProcessor {
    /// Create a new parallel report processor instance
    #[new]
    pub fn new() -> Self {
        Self
    }

    #[staticmethod]
    /// Process multiple reports in parallel
    pub fn process_batch(
        reports: Vec<Vec<String>>,
        _processor_fn: Py<PyAny>,
    ) -> PyResult<Vec<Vec<String>>> {
        // For now, just return the reports as-is since we can't call Python functions from Rust easily
        // This would need more complex PyO3 integration to work properly
        Ok(reports)
    }

    #[staticmethod]
    /// Combine multiple report fragments in parallel
    pub fn combine_fragments(fragments: Vec<PyReportFragment>) -> PyReportFragment {
        // Combine fragments by folding them together
        let mut result = ReportFragment::empty();
        for fragment in fragments {
            result = result.combine(&fragment.inner);
        }
        PyReportFragment { inner: result }
    }
}
