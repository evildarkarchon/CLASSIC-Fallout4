//! Core file I/O implementation with async support
//!
//! This module provides high-performance file I/O operations with:
//! - Async file operations with Tokio
//! - Memory-mapped file support for large files
//! - Parallel directory traversal
//! - DDS header parsing with zero-copy operations
//! - Multi-level caching (content, paths, metadata)
//! - Encoding detection for text files

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use pyo3::types::{PyDict, PyList};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::fs;
use tokio::sync::{RwLock, Semaphore};
use lru::LruCache;
use anyhow::{Result, Context};
use std::num::NonZeroUsize;
use dashmap::DashMap;
use memmap2::Mmap;
use rayon::prelude::*;
use walkdir::WalkDir;
use std::fs::File;
use std::io::Read;

use super::encoding::EncodingDetector;
use super::dds::DDSHeader;

// Use the global runtime from lib.rs (ONE RUNTIME RULE)
use crate::get_runtime;

/// High-performance file I/O core with caching and encoding detection
#[pyclass]
pub struct RustFileIOCore {
    encoding_detector: Arc<EncodingDetector>,
    // Multi-level caching
    read_cache: Arc<RwLock<LruCache<PathBuf, String>>>,        // Text file content cache
    path_cache: Arc<DashMap<String, PathBuf>>,                 // Path string to PathBuf cache
    metadata_cache: Arc<DashMap<PathBuf, FileMetadata>>,       // File metadata cache
    dds_cache: Arc<RwLock<LruCache<PathBuf, DDSHeader>>>,      // DDS header cache
    // Concurrency control
    io_semaphore: Arc<Semaphore>,                              // Limit concurrent I/O operations
    // Configuration
    default_encoding: String,
    #[allow(dead_code)] // Reserved for future error handling modes
    default_errors: String,
}

#[derive(Clone, Debug)]
#[allow(dead_code)] // Reserved for future metadata operations
struct FileMetadata {
    size: u64,
    is_file: bool,
    is_dir: bool,
}

#[pymethods]
impl RustFileIOCore {
    #[new]
    #[pyo3(signature = (encoding="utf-8", errors="ignore", cache_size=100, max_concurrent_io=50))]
    pub fn new(encoding: &str, errors: &str, cache_size: usize, max_concurrent_io: usize) -> PyResult<Self> {
        let cache_size = NonZeroUsize::new(cache_size.max(1)).unwrap();
        let dds_cache_size = NonZeroUsize::new(1000).unwrap(); // Larger cache for DDS headers

        Ok(Self {
            encoding_detector: Arc::new(EncodingDetector::new()),
            read_cache: Arc::new(RwLock::new(LruCache::new(cache_size))),
            path_cache: Arc::new(DashMap::new()),
            metadata_cache: Arc::new(DashMap::new()),
            dds_cache: Arc::new(RwLock::new(LruCache::new(dds_cache_size))),
            io_semaphore: Arc::new(Semaphore::new(max_concurrent_io)),
            default_encoding: encoding.to_string(),
            default_errors: errors.to_string(),
        })
    }

    /// Read a file with encoding detection (sync wrapper for async implementation)
    #[pyo3(name = "read_file")]
    pub fn py_read_file(&self, _py: Python<'_>, path: String) -> PyResult<String> {
        let encoding_detector = self.encoding_detector.clone();
        let cache = self.read_cache.clone();

        get_runtime().block_on(async move {
            let path = PathBuf::from(path);

            // Check cache first (need write lock for LRU get which updates access order)
            {
                let mut cache_guard = cache.write().await;
                if let Some(cached) = cache_guard.get(&path) {
                    return Ok(cached.clone());
                }
            }

            // Read file with encoding detection
            let content = read_file_with_encoding(&path, &encoding_detector).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

            // Update cache
            {
                let mut cache_guard = cache.write().await;
                cache_guard.put(path, content.clone());
            }

            Ok(content)
        })
    }

    /// Write a file (sync wrapper for async implementation)
    #[pyo3(name = "write_file")]
    pub fn py_write_file(&self, _py: Python<'_>, path: String, content: String) -> PyResult<()> {
        get_runtime().block_on(async move {
            fs::write(&path, content.as_bytes()).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            Ok(())
        })
    }

    /// Read file lines with automatic encoding detection
    #[pyo3(name = "read_lines")]
    pub fn py_read_lines(&self, _py: Python<'_>, path: String) -> PyResult<Vec<String>> {
        let content = self.py_read_file(_py, path)?;
        Ok(content.lines().map(|s| s.to_string()).collect())
    }

    /// Read file as bytes
    #[pyo3(name = "read_bytes")]
    pub fn py_read_bytes(&self, _py: Python<'_>, path: String) -> PyResult<Vec<u8>> {
        get_runtime().block_on(async move {
            let path = PathBuf::from(path);
            fs::read(&path).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
        })
    }

    /// Write lines to file
    #[pyo3(name = "write_lines")]
    pub fn py_write_lines(&self, _py: Python<'_>, path: String, lines: Vec<String>) -> PyResult<()> {
        let mut content = lines.join("\n");
        if !content.ends_with('\n') {
            content.push('\n');
        }
        self.py_write_file(_py, path, content)
    }

    /// Write bytes to file
    #[pyo3(name = "write_bytes")]
    pub fn py_write_bytes(&self, _py: Python<'_>, path: String, content: Vec<u8>) -> PyResult<()> {
        get_runtime().block_on(async move {
            let path = PathBuf::from(path);
            // Ensure parent directory exists
            if let Some(parent) = path.parent() {
                fs::create_dir_all(parent).await
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }
            fs::write(&path, content).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
        })
    }

    /// Append content to file
    #[pyo3(name = "append_file")]
    pub fn py_append_file(&self, _py: Python<'_>, path: String, content: String) -> PyResult<()> {
        get_runtime().block_on(async move {
            use tokio::fs::OpenOptions;
            use tokio::io::AsyncWriteExt;

            let path = PathBuf::from(path);
            // Ensure parent directory exists
            if let Some(parent) = path.parent() {
                fs::create_dir_all(parent).await
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            }

            let mut file = OpenOptions::new()
                .create(true)
                .append(true)
                .open(&path)
                .await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

            file.write_all(content.as_bytes()).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

            Ok(())
        })
    }

    /// Clear all caches
    pub fn clear_cache(&self, _py: Python<'_>) -> PyResult<()> {
        let read_cache = self.read_cache.clone();
        let dds_cache = self.dds_cache.clone();
        let path_cache = self.path_cache.clone();
        let metadata_cache = self.metadata_cache.clone();

        get_runtime().block_on(async move {
            let mut read_guard = read_cache.write().await;
            read_guard.clear();
            let mut dds_guard = dds_cache.write().await;
            dds_guard.clear();
            path_cache.clear();
            metadata_cache.clear();
            Ok(())
        })
    }

    /// Check if file exists (fast, non-blocking)
    pub fn file_exists(&self, _py: Python<'_>, path: String) -> bool {
        let path = self.ensure_path(path);
        path.exists()
    }

    /// Get file size in bytes
    pub fn get_file_size(&self, _py: Python<'_>, path: String) -> i64 {
        let path = self.ensure_path(path);
        match std::fs::metadata(&path) {
            Ok(metadata) => metadata.len() as i64,
            Err(_) => -1,
        }
    }

    /// Parse DDS header with zero-copy operations
    pub fn read_dds_header(&self, _py: Python<'_>, path: String) -> PyResult<Option<(u32, u32)>> {
        let path = PathBuf::from(&path);

        // Parse DDS header
        let header = read_dds_header_impl(&path)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        if let Some(h) = header {
            Ok(Some((h.width, h.height)))
        } else {
            Ok(None)
        }
    }

    /// Batch DDS header reading with parallel processing
    pub fn read_dds_headers_batch(&self, py: Python<'_>, paths: Vec<String>) -> PyResult<Py<PyDict>> {
        let results: Vec<(String, Option<(u32, u32)>)> = paths
            .into_par_iter()
            .map(|path| {
                let path_buf = PathBuf::from(&path);
                let header = read_dds_header_impl(&path_buf).ok().flatten();
                let dimensions = header.map(|h| (h.width, h.height));
                (path, dimensions)
            })
            .collect();

        // Convert to Python dict
        let dict = PyDict::new(py);
        for (path, dims) in results {
            if let Some((width, height)) = dims {
                dict.set_item(path, (width, height))?;
            } else {
                dict.set_item(path, py.None())?;
            }
        }

        Ok(dict.unbind())
    }
}

// Advanced I/O Operations
impl RustFileIOCore {
    /// Internal: Convert string path to PathBuf with caching
    fn ensure_path(&self, path: String) -> PathBuf {
        if let Some(cached) = self.path_cache.get(&path) {
            return cached.clone();
        }
        let path_buf = PathBuf::from(&path);
        self.path_cache.insert(path, path_buf.clone());
        path_buf
    }

    /// Memory-mapped file reading for large files
    pub fn py_read_file_mmap(&self, _py: Python<'_>, path: String, encoding: Option<String>) -> PyResult<String> {
        let path = self.ensure_path(path);
        let encoding_detector = self.encoding_detector.clone();
        let encoding = encoding.unwrap_or_else(|| self.default_encoding.clone());

        // Use memory mapping for files over 10MB
        let metadata = std::fs::metadata(&path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        if metadata.len() > 10_000_000 {
            // Memory-mapped reading
            let file = File::open(&path)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

            unsafe {
                let mmap = Mmap::map(&file)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

                let detected_encoding = if encoding == "auto" {
                    encoding_detector.detect(&mmap)
                } else {
                    encoding_rs::Encoding::for_label(encoding.as_bytes())
                        .unwrap_or(encoding_rs::UTF_8)
                };

                let (content, _, had_errors) = detected_encoding.decode(&mmap);
                if had_errors {
                    log::warn!("Encoding errors in file: {:?}", path);
                }
                Ok(content.into_owned())
            }
        } else {
            // Regular file reading for smaller files
            self.py_read_file(_py, path.to_string_lossy().to_string())
        }
    }

    /// Parallel directory traversal
    pub fn py_walk_directory(
        &self,
        py: Python<'_>,
        path: String,
        pattern: Option<String>,
        max_depth: Option<usize>,
    ) -> PyResult<Py<PyList>> {
        let path = self.ensure_path(path);
        let max_depth = max_depth.unwrap_or(usize::MAX);

        // Use WalkDir for efficient traversal
        let walker = WalkDir::new(&path)
            .max_depth(max_depth)
            .into_iter()
            .filter_map(Result::ok)
            .filter(|e| e.file_type().is_file());

        let files: Vec<String> = if let Some(pattern) = pattern {
            // Filter by pattern
            let pattern = regex::Regex::new(&pattern)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

            walker
                .filter(|e| {
                    e.path()
                        .file_name()
                        .and_then(|n| n.to_str())
                        .map(|n| pattern.is_match(n))
                        .unwrap_or(false)
                })
                .map(|e| e.path().to_string_lossy().to_string())
                .collect()
        } else {
            walker.map(|e| e.path().to_string_lossy().to_string()).collect()
        };

        // Convert to Python list
        let list = PyList::new(py, files)?;
        Ok(list.unbind())
    }

    /// Batch file reading with concurrency control
    pub fn py_read_multiple_files(
        &self,
        py: Python<'_>,
        paths: Vec<String>,
    ) -> PyResult<Py<PyDict>> {
        let encoding_detector = self.encoding_detector.clone();
        let io_semaphore = self.io_semaphore.clone();
        let read_cache = self.read_cache.clone();

        let results = get_runtime().block_on(async move {
            let mut tasks = Vec::new();

            for path in paths {
                let path_buf = PathBuf::from(path.clone());
                let detector = encoding_detector.clone();
                let semaphore = io_semaphore.clone();
                let cache = read_cache.clone();

                let task = tokio::spawn(async move {
                    let _permit = semaphore.acquire().await;

                    // Check cache first
                    {
                        let mut cache_guard = cache.write().await;
                        if let Some(cached) = cache_guard.get(&path_buf) {
                            return (path, Ok(cached.clone()));
                        }
                    }

                    // Read file
                    let result = read_file_with_encoding(&path_buf, &detector).await;

                    // Update cache on success
                    if let Ok(ref content) = result {
                        let mut cache_guard = cache.write().await;
                        cache_guard.put(path_buf, content.clone());
                    }

                    (path, result)
                });

                tasks.push(task);
            }

            futures::future::join_all(tasks).await
        });

        // Convert to Python dict
        let dict = PyDict::new(py);
        for result in results {
            match result {
                Ok((path, Ok(content))) => {
                    dict.set_item(path, content)?;
                }
                Ok((path, Err(e))) => {
                    log::error!("Error reading {}: {}", path, e);
                    dict.set_item(path, "")?;
                }
                Err(e) => {
                    log::error!("Task error: {}", e);
                }
            }
        }

        Ok(dict.unbind())
    }

    /// Write multiple files with concurrency control
    pub fn py_write_multiple_files(
        &self,
        _py: Python<'_>,
        files: std::collections::HashMap<String, String>,
    ) -> PyResult<()> {
        let io_semaphore = self.io_semaphore.clone();

        get_runtime().block_on(async move {
            let mut tasks = Vec::new();

            for (path, content) in files {
                let semaphore = io_semaphore.clone();
                let path_buf = PathBuf::from(path.clone());

                let task = tokio::spawn(async move {
                    let _permit = semaphore.acquire().await;

                    // Ensure parent directory exists
                    if let Some(parent) = path_buf.parent() {
                        if let Err(e) = fs::create_dir_all(parent).await {
                            log::error!("Failed to create directory for {}: {}", path, e);
                            return Err(e);
                        }
                    }

                    fs::write(&path_buf, content.as_bytes()).await
                });

                tasks.push(task);
            }

            let results = futures::future::join_all(tasks).await;

            for result in results {
                match result {
                    Ok(Ok(())) => {},
                    Ok(Err(e)) => {
                        return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()));
                    }
                    Err(e) => {
                        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()));
                    }
                }
            }

            Ok(())
        })
    }
}

/// Internal async function to read file with encoding detection
async fn read_file_with_encoding(path: &Path, detector: &EncodingDetector) -> Result<String> {
    let bytes = fs::read(path).await
        .with_context(|| format!("Failed to read file: {:?}", path))?;

    let encoding = detector.detect(&bytes);
    let (content, _, had_errors) = encoding.decode(&bytes);

    if had_errors {
        log::warn!("Encoding errors detected in file: {:?}", path);
    }

    Ok(content.into_owned())
}

/// Read DDS header from file
fn read_dds_header_impl(path: &Path) -> Result<Option<DDSHeader>> {
    let mut file = File::open(path)
        .with_context(|| format!("Failed to open DDS file: {:?}", path))?;

    // Check file size
    let metadata = file.metadata()?;
    if metadata.len() < 128 {
        return Ok(None);
    }

    // Read header bytes
    let mut header_bytes = [0u8; 128];
    file.read_exact(&mut header_bytes)?;

    // Parse DDS header
    DDSHeader::from_bytes(&header_bytes)
}
