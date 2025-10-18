//! Python bindings for FileIOCore (thin PyO3 adapter)
//!
//! This module provides THIN adapters that delegate all business logic to classic-file-io-core.
//! It ONLY handles Python ↔ Rust type conversions and async runtime bridging.

use classic_file_io_core::FileIOCore;
use classic_shared::{get_runtime, without_gil};
use pyo3::exceptions::{PyIOError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::path::PathBuf;

/// Convert FileIOError to PyErr
fn to_pyerr(err: classic_file_io_core::FileIOError) -> PyErr {
    match err {
        classic_file_io_core::FileIOError::IoError(e) => PyIOError::new_err(e.to_string()),
        classic_file_io_core::FileIOError::NotFound(s) => {
            PyIOError::new_err(format!("File not found: {}", s))
        }
        classic_file_io_core::FileIOError::InvalidPath(s) => PyValueError::new_err(s),
        classic_file_io_core::FileIOError::EncodingError(s) => {
            PyRuntimeError::new_err(format!("Encoding error: {}", s))
        }
        classic_file_io_core::FileIOError::DDSError(s) => {
            PyRuntimeError::new_err(format!("DDS error: {}", s))
        }
        classic_file_io_core::FileIOError::JoinError(s) => {
            PyRuntimeError::new_err(format!("Task error: {}", s))
        }
        classic_file_io_core::FileIOError::CacheError(s) => {
            PyRuntimeError::new_err(format!("Cache error: {}", s))
        }
        classic_file_io_core::FileIOError::Io(s) => {
            PyIOError::new_err(format!("I/O error: {}", s))
        }
    }
}

/// Python wrapper for FileIOCore - THIN ADAPTER ONLY
#[pyclass(name = "RustFileIOCore")]
pub struct PyFileIOCore {
    inner: FileIOCore,
}

#[pymethods]
impl PyFileIOCore {
    #[new]
    #[pyo3(signature = (encoding="utf-8", errors="ignore", cache_size=100, max_concurrent_io=50))]
    pub fn new(encoding: &str, errors: &str, cache_size: usize, max_concurrent_io: usize) -> Self {
        Self {
            inner: FileIOCore::new(encoding, errors, cache_size, max_concurrent_io),
        }
    }

    /// Read a file with encoding detection
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    #[pyo3(name = "read_file")]
    pub fn py_read_file(&self, py: Python<'_>, path: String) -> PyResult<String> {
        let path_buf = PathBuf::from(path);

        // Release GIL during I/O operation for better Python concurrency
        without_gil(py, || {
            get_runtime().block_on(async {
                self.inner.read_file(&path_buf).await.map_err(to_pyerr)
            })
        })
    }

    /// Write a file
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    #[pyo3(name = "write_file")]
    pub fn py_write_file(&self, py: Python<'_>, path: String, content: String) -> PyResult<()> {
        let path_buf = PathBuf::from(path);

        // Release GIL during I/O operation
        without_gil(py, || {
            get_runtime().block_on(async {
                self.inner
                    .write_file(&path_buf, &content)
                    .await
                    .map_err(to_pyerr)
            })
        })
    }

    /// Read file lines with automatic encoding detection
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    #[pyo3(name = "read_lines")]
    pub fn py_read_lines(&self, py: Python<'_>, path: String) -> PyResult<Vec<String>> {
        let path_buf = PathBuf::from(path);

        // Release GIL during I/O operation
        without_gil(py, || {
            get_runtime().block_on(async {
                self.inner.read_lines(&path_buf).await.map_err(to_pyerr)
            })
        })
    }

    /// Read file as bytes
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    #[pyo3(name = "read_bytes")]
    pub fn py_read_bytes(&self, py: Python<'_>, path: String) -> PyResult<Vec<u8>> {
        let path_buf = PathBuf::from(path);

        // Release GIL during I/O operation
        without_gil(py, || {
            get_runtime().block_on(async {
                self.inner.read_bytes(&path_buf).await.map_err(to_pyerr)
            })
        })
    }

    /// Write lines to file
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    #[pyo3(name = "write_lines")]
    pub fn py_write_lines(
        &self,
        py: Python<'_>,
        path: String,
        lines: Vec<String>,
    ) -> PyResult<()> {
        let path_buf = PathBuf::from(path);

        // Release GIL during I/O operation
        without_gil(py, || {
            get_runtime().block_on(async {
                self.inner
                    .write_lines(&path_buf, lines)
                    .await
                    .map_err(to_pyerr)
            })
        })
    }

    /// Write bytes to file
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    #[pyo3(name = "write_bytes")]
    pub fn py_write_bytes(&self, py: Python<'_>, path: String, content: Vec<u8>) -> PyResult<()> {
        let path_buf = PathBuf::from(path);

        // Release GIL during I/O operation
        without_gil(py, || {
            get_runtime().block_on(async {
                self.inner
                    .write_bytes(&path_buf, content)
                    .await
                    .map_err(to_pyerr)
            })
        })
    }

    /// Append content to file
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    #[pyo3(name = "append_file")]
    pub fn py_append_file(&self, py: Python<'_>, path: String, content: String) -> PyResult<()> {
        let path_buf = PathBuf::from(path);

        // Release GIL during I/O operation
        without_gil(py, || {
            get_runtime().block_on(async {
                self.inner
                    .append_file(&path_buf, &content)
                    .await
                    .map_err(to_pyerr)
            })
        })
    }

    /// Clear all caches
    pub fn clear_cache(&self, _py: Python<'_>) -> PyResult<()> {
        get_runtime().block_on(async {
            self.inner.clear_cache().await;
            Ok(())
        })
    }

    /// Check if file exists (fast, non-blocking)
    pub fn file_exists(&self, _py: Python<'_>, path: String) -> bool {
        let path_buf = PathBuf::from(path);
        self.inner.file_exists(&path_buf)
    }

    /// Get file size in bytes
    pub fn get_file_size(&self, _py: Python<'_>, path: String) -> i64 {
        let path_buf = PathBuf::from(path);
        self.inner
            .get_file_size(&path_buf)
            .map(|s| s as i64)
            .unwrap_or(-1)
    }

    /// Parse DDS header with zero-copy operations
    pub fn read_dds_header(&self, _py: Python<'_>, path: String) -> PyResult<Option<(u32, u32)>> {
        let path_buf = PathBuf::from(path);
        get_runtime().block_on(async {
            match self.inner.read_dds_header(&path_buf).await {
                Ok(Some(header)) => Ok(Some((header.width, header.height))),
                Ok(None) => Ok(None),
                Err(e) => Err(to_pyerr(e)),
            }
        })
    }

    /// Batch DDS header reading with parallel processing
    pub fn read_dds_headers_batch(
        &self,
        py: Python<'_>,
        paths: Vec<String>,
    ) -> PyResult<Py<PyDict>> {
        let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
        let results = self.inner.read_dds_headers_batch(path_bufs);

        // Convert to Python dict
        let dict = PyDict::new(py);
        for (path, header_opt) in results {
            let path_str = path.to_string_lossy().to_string();
            if let Some(header) = header_opt {
                dict.set_item(path_str, (header.width, header.height))?;
            } else {
                dict.set_item(path_str, py.None())?;
            }
        }

        Ok(dict.unbind())
    }

    /// Parallel directory traversal
    pub fn py_walk_directory(
        &self,
        py: Python<'_>,
        path: String,
        pattern: Option<String>,
        max_depth: Option<usize>,
    ) -> PyResult<Py<PyList>> {
        let path_buf = PathBuf::from(path);
        let files = self
            .inner
            .walk_directory(&path_buf, pattern.as_deref(), max_depth)
            .map_err(to_pyerr)?;

        // Convert to Python list
        let file_strings: Vec<String> = files
            .iter()
            .map(|p| p.to_string_lossy().to_string())
            .collect();
        let list = PyList::new(py, file_strings)?;
        Ok(list.unbind())
    }

    /// Batch file reading with concurrency control
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    pub fn py_read_multiple_files(
        &self,
        py: Python<'_>,
        paths: Vec<String>,
    ) -> PyResult<Py<PyDict>> {
        let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();

        // Release GIL during batch I/O operation
        let results = without_gil(py, || {
            get_runtime().block_on(async { self.inner.read_multiple_files(path_bufs).await })
        });

        // Convert to Python dict (requires GIL)
        let dict = PyDict::new(py);
        for (path, result) in results {
            let path_str = path.to_string_lossy().to_string();
            match result {
                Ok(content) => dict.set_item(path_str, content)?,
                Err(e) => {
                    log::error!("Error reading {}: {}", path_str, e);
                    dict.set_item(path_str, "")?;
                }
            }
        }

        Ok(dict.unbind())
    }

    /// Write multiple files with concurrency control
    ///
    /// This operation releases the GIL to allow other Python threads to run concurrently.
    pub fn py_write_multiple_files(
        &self,
        py: Python<'_>,
        files: HashMap<String, String>,
    ) -> PyResult<()> {
        let file_pairs: Vec<(PathBuf, String)> = files
            .into_iter()
            .map(|(path, content)| (PathBuf::from(path), content))
            .collect();

        // Release GIL during batch I/O operation
        without_gil(py, || {
            get_runtime().block_on(async {
                let results = self.inner.write_multiple_files(file_pairs).await;

                // Check for errors
                for (path, result) in results {
                    if let Err(e) = result {
                        return Err(PyIOError::new_err(format!(
                            "Failed to write {}: {}",
                            path.display(),
                            e
                        )));
                    }
                }

                Ok(())
            })
        })
    }
}
