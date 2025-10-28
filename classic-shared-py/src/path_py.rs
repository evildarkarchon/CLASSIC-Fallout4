//! PyO3 bindings for path handling utilities

use classic_shared_core::path_core::PathHandler as CorePathHandler;
use pyo3::prelude::*;

/// High-performance path handler with caching (Python wrapper)
///
/// This class provides Python access to the high-performance path handling
/// utilities implemented in Rust.
#[pyclass(name = "PathHandler")]
pub struct PyPathHandler {
    /// Core path handler implementation
    inner: CorePathHandler,
}

#[pymethods]
impl PyPathHandler {
    /// Creates a new `PathHandler` with optional cache TTL.
    ///
    /// # Arguments
    /// * `cache_ttl_seconds` - Cache time-to-live in seconds (default: 300)
    #[new]
    #[pyo3(signature = (cache_ttl_seconds=300))]
    pub fn new(cache_ttl_seconds: u64) -> Self {
        Self {
            inner: CorePathHandler::new(cache_ttl_seconds),
        }
    }

    /// Normalizes a file path.
    ///
    /// # Arguments
    /// * `path` - The path to normalize
    ///
    /// # Returns
    /// The normalized path
    pub fn normalize_path(&self, path: String) -> PyResult<String> {
        self.inner.normalize_path(&path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())
        })
    }

    /// Clear all caches
    pub fn clear_cache(&self) {
        self.inner.clear_cache();
    }

    /// Returns cache statistics.
    ///
    /// # Returns
    /// Tuple of (path_cache_size, validation_cache_size)
    pub fn cache_stats(&self) -> (usize, usize) {
        self.inner.cache_stats()
    }

    /// Clean up expired cache entries
    pub fn cleanup_cache(&self) {
        self.inner.cleanup_cache();
    }

    /// Validate multiple paths in batch.
    ///
    /// # Arguments
    /// * `paths` - List of paths to validate
    ///
    /// # Returns
    /// List of tuples: (path, is_valid, message)
    pub fn validate_paths_batch(&self, paths: Vec<String>) -> Vec<(String, bool, String)> {
        self.inner.validate_paths_batch(&paths)
    }

    /// Join a base path with path components.
    ///
    /// # Arguments
    /// * `base` - Base path
    /// * `components` - List of path components to join
    ///
    /// # Returns
    /// The joined path
    pub fn join_paths(&self, base: String, components: Vec<String>) -> String {
        self.inner.join_paths(&base, &components)
    }

    /// Split a path into its components.
    ///
    /// # Arguments
    /// * `path` - The path to split
    ///
    /// # Returns
    /// List of path components
    pub fn split_path(&self, path: String) -> Vec<String> {
        self.inner.split_path(&path)
    }

    /// Get the filename from a path.
    ///
    /// # Arguments
    /// * `path` - The path
    ///
    /// # Returns
    /// The filename, or None if not present
    pub fn get_filename(&self, path: String) -> Option<String> {
        self.inner.get_filename(&path)
    }

    /// Get the file extension from a path.
    ///
    /// # Arguments
    /// * `path` - The path
    ///
    /// # Returns
    /// The extension, or None if not present
    pub fn get_extension(&self, path: String) -> Option<String> {
        self.inner.get_extension(&path)
    }

    /// Get the parent directory from a path.
    ///
    /// # Arguments
    /// * `path` - The path
    ///
    /// # Returns
    /// The parent directory, or None if at root
    pub fn get_parent(&self, path: String) -> Option<String> {
        self.inner.get_parent(&path)
    }

    /// Check if a path is absolute.
    ///
    /// # Arguments
    /// * `path` - The path to check
    ///
    /// # Returns
    /// True if absolute, false otherwise
    pub fn is_absolute(&self, path: String) -> bool {
        self.inner.is_absolute(&path)
    }

    /// Convert a path to absolute.
    ///
    /// # Arguments
    /// * `path` - The path to convert
    /// * `base` - Optional base directory (uses current directory if None)
    ///
    /// # Returns
    /// The absolute path
    pub fn to_absolute(&self, path: String, base: Option<String>) -> PyResult<String> {
        self.inner.to_absolute(&path, base.as_deref()).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())
        })
    }

    /// Find the common prefix of multiple paths.
    ///
    /// # Arguments
    /// * `paths` - List of paths to compare
    ///
    /// # Returns
    /// The common prefix, or None if there isn't one
    pub fn common_prefix(&self, paths: Vec<String>) -> Option<String> {
        self.inner.common_prefix(&paths)
    }
}
