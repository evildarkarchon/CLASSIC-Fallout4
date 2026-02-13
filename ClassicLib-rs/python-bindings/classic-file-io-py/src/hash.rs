//! Python bindings for file hashing functionality.
//!
//! This module provides SHA256 hashing operations with caching and
//! parallel batch processing capabilities.

use classic_file_io_core::hash::FileHasher;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::path::PathBuf;

/// Python wrapper for file hashing operations.
///
/// Provides SHA256 hashing with caching and parallel batch operations.
///
/// Example:
///     >>> from classic_file_io import PyFileHasher
///     >>>
///     >>> # Single file hash
///     >>> hash_val = PyFileHasher.hash_file("data.bin")
///     >>> print(f"SHA256: {hash_val}")
///     >>>
///     >>> # Batch parallel hashing
///     >>> files = ["file1.bin", "file2.bin", "file3.bin"]
///     >>> hashes = PyFileHasher.hash_files_parallel(files)
///     >>> for path, hash_val in hashes.items():
///     >>>     if hash_val:
///     >>>         print(f"{path}: {hash_val}")
///
#[pyclass(name = "FileHasher", module = "classic_file_io")]
pub struct PyFileHasher;

#[pymethods]
impl PyFileHasher {
    /// Calculate SHA256 hash of a file with caching.
    ///
    /// Args:
    ///     path (str): Path to the file to hash
    ///
    /// Returns:
    ///     str: Lowercase hexadecimal SHA256 hash (64 characters)
    ///
    /// Raises:
    ///     RuntimeError: If file doesn't exist, cannot be read, or I/O error occurs
    ///
    /// Example:
    ///     >>> hash_val = PyFileHasher.hash_file("game.exe")
    ///     >>> print(len(hash_val))  # 64 (SHA256 is 256 bits = 64 hex chars)
    ///     64
    #[staticmethod]
    fn hash_file(path: &str) -> PyResult<String> {
        FileHasher::hash_file(&PathBuf::from(path))
            .map_err(|e| PyRuntimeError::new_err(format!("Hash calculation failed: {}", e)))
    }

    /// Calculate SHA256 hashes for multiple files in parallel.
    ///
    /// Uses Rayon to parallelize hash calculations across available CPU cores.
    /// Files that fail to hash will have `None` values in the result.
    ///
    /// Args:
    ///     paths (list[str]): List of file paths to hash
    ///
    /// Returns:
    ///     dict[str, str | None]: Dictionary mapping paths to hashes.
    ///                            Successful hashes are strings, failures are None.
    ///
    /// Example:
    ///     >>> files = ["file1.bin", "file2.bin", "nonexistent.bin"]
    ///     >>> results = PyFileHasher.hash_files_parallel(files)
    ///     >>> for path, hash_val in results.items():
    ///     >>>     if hash_val:
    ///     >>>         print(f"{path}: {hash_val}")
    ///     >>>     else:
    ///     >>>         print(f"{path}: FAILED")
    #[staticmethod]
    fn hash_files_parallel<'py>(
        py: Python<'py>,
        paths: Vec<String>,
    ) -> PyResult<Bound<'py, PyDict>> {
        // Convert to Path refs
        let path_refs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
        let path_slice: Vec<&std::path::Path> = path_refs.iter().map(|p| p.as_path()).collect();

        // Calculate hashes in parallel
        let results = FileHasher::hash_files_parallel(&path_slice)
            .map_err(|e| PyRuntimeError::new_err(format!("Batch hashing failed: {}", e)))?;

        // Convert to Python dict
        let dict = PyDict::new(py);
        for (path_buf, hash_opt) in results {
            let path_str = path_buf.to_string_lossy().to_string();
            match hash_opt {
                Some(hash) => dict.set_item(path_str, hash)?,
                None => dict.set_item(path_str, py.None())?,
            }
        }

        Ok(dict)
    }

    /// Calculate hashes and return only successful results.
    ///
    /// This is a convenience wrapper that filters out failures and returns
    /// only files that were successfully hashed.
    ///
    /// Args:
    ///     paths (list[str]): List of file paths to hash
    ///
    /// Returns:
    ///     dict[str, str]: Dictionary mapping paths to hashes (failures excluded)
    ///
    /// Example:
    ///     >>> files = ["file1.bin", "file2.bin", "nonexistent.bin"]
    ///     >>> hashes = PyFileHasher.hash_files_to_map(files)
    ///     >>> print(len(hashes))  # Only successful hashes (e.g., 2)
    ///     2
    #[staticmethod]
    fn hash_files_to_map<'py>(py: Python<'py>, paths: Vec<String>) -> PyResult<Bound<'py, PyDict>> {
        // Convert to Path refs
        let path_refs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
        let path_slice: Vec<&std::path::Path> = path_refs.iter().map(|p| p.as_path()).collect();

        // Calculate hashes and get map
        let hash_map = FileHasher::hash_files_to_map(&path_slice)
            .map_err(|e| PyRuntimeError::new_err(format!("Batch hashing failed: {}", e)))?;

        // Convert to Python dict
        let dict = PyDict::new(py);
        for (path_buf, hash) in hash_map {
            let path_str = path_buf.to_string_lossy().to_string();
            dict.set_item(path_str, hash)?;
        }

        Ok(dict)
    }

    /// Clear the hash cache.
    ///
    /// Useful for testing or when files are known to have changed.
    ///
    /// Example:
    ///     >>> PyFileHasher.clear_cache()
    #[staticmethod]
    fn clear_cache() {
        FileHasher::clear_cache();
    }

    /// Get the number of cached hashes.
    ///
    /// Returns:
    ///     int: Number of hashes currently in cache
    ///
    /// Example:
    ///     >>> count = PyFileHasher.cache_size()
    ///     >>> print(f"Cached hashes: {count}")
    #[staticmethod]
    fn cache_size() -> usize {
        FileHasher::cache_size()
    }
}
