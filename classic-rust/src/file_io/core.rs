//! Core file I/O implementation with async support

use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::fs;
use tokio::sync::RwLock;
use lru::LruCache;
use anyhow::{Result, Context};
use encoding_rs::Encoding;
use std::num::NonZeroUsize;

use super::encoding::EncodingDetector;

/// High-performance file I/O core with caching and encoding detection
#[pyclass]
pub struct RustFileIOCore {
    encoding_detector: Arc<EncodingDetector>,
    read_cache: Arc<RwLock<LruCache<PathBuf, String>>>,
}

#[pymethods]
impl RustFileIOCore {
    #[new]
    pub fn new() -> PyResult<Self> {
        let cache_size = NonZeroUsize::new(100).unwrap();
        Ok(Self {
            encoding_detector: Arc::new(EncodingDetector::new()),
            read_cache: Arc::new(RwLock::new(LruCache::new(cache_size))),
        })
    }

    /// Read a file asynchronously with encoding detection
    #[pyo3(name = "read_file")]
    pub fn py_read_file<'py>(&self, py: Python<'py>, path: String) -> PyResult<Bound<'py, PyAny>> {
        let encoding_detector = self.encoding_detector.clone();
        let cache = self.read_cache.clone();

        future_into_py(py, async move {
            let path = PathBuf::from(path);

            // Check cache first
            {
                let mut cache_guard = cache.read().await;
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

    /// Write a file asynchronously
    #[pyo3(name = "write_file")]
    pub fn py_write_file<'py>(&self, py: Python<'py>, path: String, content: String) -> PyResult<Bound<'py, PyAny>> {
        future_into_py(py, async move {
            fs::write(&path, content.as_bytes()).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
            Ok(())
        })
    }

    /// Clear the read cache
    pub fn clear_cache<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let cache = self.read_cache.clone();
        future_into_py(py, async move {
            let mut cache_guard = cache.write().await;
            cache_guard.clear();
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
