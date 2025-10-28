//! PyO3 bindings for string processing utilities

use classic_shared_core::strings_core::{StringProcessor as CoreStringProcessor, StringOperation};
use pyo3::prelude::*;

/// String processor with interning and parallel operations (Python wrapper)
///
/// This class provides Python access to the high-performance string processing
/// utilities implemented in Rust.
#[pyclass(name = "StringProcessor")]
pub struct PyStringProcessor {
    /// Core string processor implementation
    inner: CoreStringProcessor,
}

#[pymethods]
impl PyStringProcessor {
    /// Creates a new `StringProcessor`.
    #[new]
    pub fn new() -> Self {
        Self {
            inner: CoreStringProcessor::new(),
        }
    }

    /// Intern a string for memory efficiency
    ///
    /// # Arguments
    /// * `s` - The string to intern
    ///
    /// # Returns
    /// The interned string
    pub fn intern(&self, s: String) -> String {
        self.inner.intern(&s)
    }

    /// Process multiple strings in parallel
    ///
    /// # Arguments
    /// * `strings` - List of strings to process
    /// * `operation` - Operation to perform ("upper", "lower", "trim", "normalize")
    ///
    /// # Returns
    /// List of processed strings
    pub fn process_batch(&self, strings: Vec<String>, operation: String) -> Vec<String> {
        let op = StringOperation::from_str(&operation).unwrap_or(StringOperation::Trim);
        let string_refs: Vec<&str> = strings.iter().map(|s| s.as_str()).collect();
        self.inner.process_batch(&string_refs, op)
    }

    /// Find common prefix of multiple strings
    ///
    /// # Arguments
    /// * `strings` - List of strings to compare
    ///
    /// # Returns
    /// The common prefix, or empty string if none
    pub fn common_prefix(&self, strings: Vec<String>) -> String {
        let string_refs: Vec<&str> = strings.iter().map(|s| s.as_str()).collect();
        self.inner.common_prefix(&string_refs)
    }

    /// Split text into lines efficiently
    ///
    /// # Arguments
    /// * `text` - The text to split
    ///
    /// # Returns
    /// List of lines
    pub fn split_lines(&self, text: String) -> Vec<String> {
        self.inner.split_lines(&text)
    }

    /// Join lines with a separator
    ///
    /// # Arguments
    /// * `lines` - List of lines to join
    /// * `separator` - Separator string
    ///
    /// # Returns
    /// The joined string
    pub fn join_lines(&self, lines: Vec<String>, separator: String) -> String {
        self.inner.join_lines(&lines, &separator)
    }

    /// Get string pool statistics
    ///
    /// # Returns
    /// Number of interned strings
    pub fn pool_stats(&self) -> usize {
        self.inner.pool_stats()
    }

    /// Clear the string pool
    pub fn clear_pool(&self) {
        self.inner.clear_pool();
    }
}
