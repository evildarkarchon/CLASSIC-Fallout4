//! Python bindings for FileIOCore (thin PyO3 adapter)
//!
//! This module provides THIN adapters that delegate all business logic to classic-file-io-core.
//! It ONLY handles Python ↔ Rust type conversions and async runtime bridging.

use classic_file_io_core::FileIOCore;
use classic_shared::{without_gil, PathLike};
use classic_shared_core::get_runtime;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pyo3_async_runtimes::tokio::future_into_py;
use std::collections::HashMap;
use std::path::PathBuf;

// Use the error conversion function from lib.rs
use crate::stream::{PyLineStreamer, PySyncLineStreamer};
use crate::to_pyerr;

/// Python wrapper for FileIOCore - THIN ADAPTER ONLY
#[pyclass(name = "FileIOCore")]
pub struct PyFileIOCore {
    inner: FileIOCore,
}

#[pymethods]
impl PyFileIOCore {
    /// Create a new PyFileIOCore instance with specified configuration
    ///
    /// This is a thin adapter that delegates all business logic to classic-file-io-core.
    /// It only handles Python ↔ Rust type conversions and async runtime bridging.
    ///
    /// # Arguments
    ///
    /// * `encoding` - Default text encoding for file operations (default: "utf-8")
    /// * `errors` - Error handling strategy for encoding issues (default: "ignore")
    /// * `cache_size` - Maximum number of cached file contents (default: 100)
    /// * `max_concurrent_io` - Maximum concurrent I/O operations (default: 50)
    ///
    /// # Returns
    ///
    /// A new `PyFileIOCore` instance configured with the specified parameters
    ///
    /// # Example
    ///
    /// ```python
    /// # Create with defaults
    /// file_io = FileIOCore()
    ///
    /// # Create with custom settings
    /// file_io = FileIOCore(
    ///     encoding="utf-8",
    ///     errors="strict",
    ///     cache_size=200,
    ///     max_concurrent_io=100
    /// )
    /// ```
    #[new]
    #[pyo3(signature = (encoding="utf-8", errors="ignore", cache_size=100, max_concurrent_io=50))]
    pub fn new(encoding: &str, errors: &str, cache_size: usize, max_concurrent_io: usize) -> Self {
        Self {
            inner: FileIOCore::new(encoding, errors, cache_size, max_concurrent_io),
        }
    }

    /// Read a file with encoding detection
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "read_file")]
    pub fn py_read_file<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner.read_file(&path_buf).await.map_err(to_pyerr)
        })
    }

    /// Write a file
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "write_file")]
    pub fn py_write_file<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
        content: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner
                .write_file(&path_buf, &content)
                .await
                .map_err(to_pyerr)
        })
    }

    /// Read file lines with automatic encoding detection
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "read_lines")]
    pub fn py_read_lines<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner.read_lines(&path_buf).await.map_err(to_pyerr)
        })
    }

    /// Stream lines from a file asynchronously
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a Python coroutine that resolves to an async iterator.
    ///
    /// Usage:
    ///     stream = await io.stream_lines(path)
    ///     async for line in stream:
    ///         print(line)
    #[pyo3(name = "stream_lines")]
    pub fn py_stream_lines<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        future_into_py(py, async move {
            match inner.stream_lines(&path_buf).await {
                Ok(lines) => Ok(PyLineStreamer::new(lines)),
                Err(e) => Err(to_pyerr(e)),
            }
        })
    }

    /// Stream lines from a file synchronously
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a standard Python iterator.
    ///
    /// Usage:
    ///     stream = io.stream_lines_sync(path)
    ///     for line in stream:
    ///         print(line)
    #[pyo3(name = "stream_lines_sync")]
    pub fn py_stream_lines_sync(&self, path: PathLike) -> PyResult<PySyncLineStreamer> {
        let path_buf: PathBuf = path.into();
        match self.inner.stream_lines_sync(&path_buf) {
            Ok(lines) => Ok(PySyncLineStreamer::new(lines)),
            Err(e) => Err(to_pyerr(e)),
        }
    }

    /// Read file as bytes
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "read_bytes")]
    pub fn py_read_bytes<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner.read_bytes(&path_buf).await.map_err(to_pyerr)
        })
    }

    /// Write lines to file
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "write_lines")]
    pub fn py_write_lines<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
        lines: Vec<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner.write_lines(&path_buf, lines).await.map_err(to_pyerr)
        })
    }

    /// Write bytes to file
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "write_bytes")]
    pub fn py_write_bytes<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
        content: Vec<u8>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner
                .write_bytes(&path_buf, content)
                .await
                .map_err(to_pyerr)
        })
    }

    /// Append content to file
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "append_file")]
    pub fn py_append_file<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
        content: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner
                .append_file(&path_buf, &content)
                .await
                .map_err(to_pyerr)
        })
    }

    /// Clear all caches
    pub fn clear_cache(&self, py: Python<'_>) -> PyResult<()> {
        // Release GIL during blocking cache clear operation
        without_gil(py, || {
            get_runtime().block_on(async {
                self.inner.clear_cache().await;
            });
        });
        Ok(())
    }

    /// Check if file exists (fast, non-blocking)
    ///
    /// Accepts both string paths and pathlib.Path objects.
    pub fn file_exists(&self, _py: Python<'_>, path: PathLike) -> bool {
        let path_buf: PathBuf = path.into();
        self.inner.file_exists(&path_buf)
    }

    /// Get file information (size, timestamps)
    ///
    /// Accepts both string paths and pathlib.Path objects.
    /// Returns a dict with 'size', 'created', 'modified', or 'error'.
    pub fn get_file_info(&self, py: Python<'_>, path: PathLike) -> PyResult<Py<PyDict>> {
        let path_buf: PathBuf = path.into();
        let dict = PyDict::new(py);

        // Use cached metadata if available (implied by inner cache access if we had it exposed)
        // Since we don't have direct access to inner cache via pub API, we just use std::fs::metadata
        // But we should check cache through inner methods if possible.
        // inner.get_file_size uses cache.

        match std::fs::metadata(&path_buf) {
            Ok(metadata) => {
                dict.set_item("size", metadata.len())?;
                if let Ok(created) = metadata.created() {
                    if let Ok(duration) = created.duration_since(std::time::UNIX_EPOCH) {
                        dict.set_item("created", duration.as_secs_f64())?;
                    }
                }
                if let Ok(modified) = metadata.modified() {
                    if let Ok(duration) = modified.duration_since(std::time::UNIX_EPOCH) {
                        dict.set_item("modified", duration.as_secs_f64())?;
                    }
                }
            }
            Err(e) => {
                dict.set_item("error", e.to_string())?;
            }
        }

        Ok(dict.unbind())
    }

    /// Get file size in bytes
    ///
    /// Accepts both string paths and pathlib.Path objects.
    pub fn get_file_size(&self, _py: Python<'_>, path: PathLike) -> i64 {
        let path_buf: PathBuf = path.into();
        self.inner
            .get_file_size(&path_buf)
            .map(|s| s as i64)
            .unwrap_or(-1)
    }

    /// Read a file using memory mapping (optimized for large files)
    #[pyo3(name = "read_file_mmap")]
    pub fn py_read_file_mmap<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        future_into_py(py, async move {
            inner.read_file_mmap(&path_buf).await.map_err(to_pyerr)
        })
    }

    /// Read a file with a specific encoding
    #[pyo3(name = "read_file_with_encoding")]
    pub fn py_read_file_with_encoding<'py>(
        &self,
        py: Python<'py>,
        path: PathLike,
        encoding: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_buf: PathBuf = path.into();

        future_into_py(py, async move {
            let bytes = inner.read_bytes(&path_buf).await.map_err(to_pyerr)?;

            // Use Python's decoder for compatibility
            Python::attach(|py| {
                let py_bytes = pyo3::types::PyBytes::new(py, &bytes);
                let decoded = py_bytes.call_method1("decode", (encoding, "ignore"))?;
                decoded.extract::<String>()
            })
        })
    }

    /// Parse DDS header with zero-copy operations
    ///
    /// Accepts both string paths and pathlib.Path objects.
    pub fn read_dds_header(&self, py: Python<'_>, path: PathLike) -> PyResult<Option<(u32, u32)>> {
        let path_buf: PathBuf = path.into();
        // Release GIL during blocking file I/O operation
        without_gil(py, || {
            get_runtime().block_on(async {
                match self.inner.read_dds_header(&path_buf).await {
                    Ok(Some(header)) => Ok(Some((header.width, header.height))),
                    Ok(None) => Ok(None),
                    Err(e) => Err(to_pyerr(e)),
                }
            })
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
    ///
    /// Accepts both string paths and pathlib.Path objects for the directory path.
    pub fn py_walk_directory(
        &self,
        py: Python<'_>,
        path: PathLike,
        pattern: Option<String>,
        max_depth: Option<usize>,
    ) -> PyResult<Py<PyList>> {
        let path_buf: PathBuf = path.into();
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
    /// Returns a Python coroutine - use with await in Python.
    pub fn py_read_multiple_files<'py>(
        &self,
        py: Python<'py>,
        paths: Vec<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            let results = inner.read_multiple_files(path_bufs).await;

            // Convert to HashMap for Python (PyO3 handles the conversion)
            let mut result_map = HashMap::new();
            for (path, result) in results {
                let path_str = path.to_string_lossy().to_string();
                match result {
                    Ok(content) => {
                        result_map.insert(path_str, content);
                    }
                    Err(e) => {
                        log::error!("Error reading {}: {}", path_str, e);
                        result_map.insert(path_str, String::new());
                    }
                }
            }

            Ok(result_map)
        })
    }

    /// Write multiple files with concurrency control
    ///
    /// Returns a Python coroutine - use with await in Python.
    pub fn py_write_multiple_files<'py>(
        &self,
        py: Python<'py>,
        files: HashMap<String, String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let file_pairs: Vec<(PathBuf, String)> = files
            .into_iter()
            .map(|(path, content)| (PathBuf::from(path), content))
            .collect();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            let results = inner.write_multiple_files(file_pairs).await;

            // Check for errors
            for (_path, result) in results {
                if let Err(e) = result {
                    return Err(to_pyerr(e));
                }
            }

            Ok(())
        })
    }
}
