//! High-performance path handling utilities with caching
//!
//! This module provides path operations optimized for the CLASSIC application.
//! It caches path lookups and provides efficient path validation without hardcoding
//! any game paths. All game paths are discovered at runtime through Python.

use pyo3::prelude::*;
use pyo3::exceptions::PyIOError;
use dashmap::DashMap;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};
use rayon::prelude::*;

/// Cache entry for path operations
#[derive(Clone, Debug)]
struct PathCacheEntry {
    value: PathBuf,
    timestamp: Instant,
    hit_count: u32,
}

/// Path handler with caching and validation
#[pyclass]
pub struct PathHandler {
    /// Cache for resolved paths with TTL
    path_cache: Arc<DashMap<String, PathCacheEntry>>,
    /// Cache for validation results
    validation_cache: Arc<DashMap<PathBuf, (bool, String, Instant)>>,
    /// Cache TTL in seconds
    cache_ttl: Duration,
}

#[pymethods]
impl PathHandler {
    #[new]
    #[pyo3(signature = (cache_ttl_seconds=300))]
    pub fn new(cache_ttl_seconds: u64) -> Self {
        Self {
            path_cache: Arc::new(DashMap::new()),
            validation_cache: Arc::new(DashMap::new()),
            cache_ttl: Duration::from_secs(cache_ttl_seconds),
        }
    }

    /// Normalize a path (resolve .. and ., convert to absolute)
    pub fn normalize_path(&self, path: String) -> PyResult<String> {
        // Check cache first
        if let Some(entry) = self.path_cache.get(&path) {
            if entry.timestamp.elapsed() < self.cache_ttl {
                // Clone the value we need before dropping the guard
                let result = entry.value.to_string_lossy().to_string();
                let mut updated_entry = entry.clone();
                updated_entry.hit_count += 1;
                // Drop the guard before inserting
                drop(entry);
                // Update hit count
                self.path_cache.insert(path.clone(), updated_entry);
                return Ok(result);
            }
        }

        // Normalize the path
        let path_buf = PathBuf::from(&path);
        let normalized = match path_buf.canonicalize() {
            Ok(p) => p,
            Err(_) => {
                // If canonicalize fails, just clean up the path
                let cleaned = self.clean_path(&path_buf)?;
                cleaned
            }
        };

        // Cache the result
        let entry = PathCacheEntry {
            value: normalized.clone(),
            timestamp: Instant::now(),
            hit_count: 1,
        };
        self.path_cache.insert(path, entry);

        Ok(normalized.to_string_lossy().to_string())
    }

    /// Clear all caches
    pub fn clear_cache(&self) {
        self.path_cache.clear();
        self.validation_cache.clear();
    }

    /// Get cache statistics
    pub fn cache_stats(&self) -> (usize, usize) {
        (self.path_cache.len(), self.validation_cache.len())
    }

    /// Remove expired entries from cache
    pub fn cleanup_cache(&self) {
        let now = Instant::now();

        // Clean path cache
        self.path_cache.retain(|_, entry| {
            now.duration_since(entry.timestamp) < self.cache_ttl
        });

        // Clean validation cache
        self.validation_cache.retain(|_, (_, _, timestamp)| {
            now.duration_since(*timestamp) < self.cache_ttl
        });
    }
}

// Internal helper methods (not exposed to Python)
impl PathHandler {
    /// Clean a path without requiring it to exist
    fn clean_path(&self, path: &PathBuf) -> PyResult<PathBuf> {
        let mut components = vec![];
        for component in path.components() {
            match component {
                std::path::Component::ParentDir => {
                    components.pop();
                }
                std::path::Component::CurDir => {
                    // Skip
                }
                c => components.push(c),
            }
        }

        let mut result = PathBuf::new();
        for component in components {
            result.push(component);
        }
        Ok(result)
    }

    /// Validate multiple paths in parallel
    pub fn validate_paths_batch(&self, paths: Vec<String>) -> Vec<(String, bool, String)> {
        paths.par_iter()
            .map(|path| {
                let path_buf = PathBuf::from(path);

                // Check validation cache
                if let Some(cached) = self.validation_cache.get(&path_buf) {
                    let (is_valid, msg, timestamp) = cached.clone();
                    if timestamp.elapsed() < self.cache_ttl {
                        return (path.clone(), is_valid, msg);
                    }
                }

                // Perform validation
                let (is_valid, msg) = self.validate_single_path(&path_buf);

                // Cache result
                self.validation_cache.insert(
                    path_buf.clone(),
                    (is_valid, msg.clone(), Instant::now())
                );

                (path.clone(), is_valid, msg)
            })
            .collect()
    }

    /// Validate a single path
    fn validate_single_path(&self, path: &PathBuf) -> (bool, String) {
        if !path.exists() {
            return (false, format!("Path does not exist: {}", path.display()));
        }

        // Check if readable
        if let Err(e) = std::fs::metadata(path) {
            return (false, format!("Cannot read metadata: {}", e));
        }

        (true, String::new())
    }

    /// Join multiple path components efficiently
    pub fn join_paths(&self, base: String, components: Vec<String>) -> String {
        let mut path = PathBuf::from(base);
        for component in components {
            path.push(component);
        }
        path.to_string_lossy().to_string()
    }

    /// Split a path into components
    pub fn split_path(&self, path: String) -> Vec<String> {
        let path_buf = PathBuf::from(path);
        path_buf.components()
            .map(|c| c.as_os_str().to_string_lossy().to_string())
            .collect()
    }

    /// Get file name from path
    pub fn get_filename(&self, path: String) -> PyResult<Option<String>> {
        let path_buf = PathBuf::from(path);
        Ok(path_buf.file_name()
            .map(|name| name.to_string_lossy().to_string()))
    }

    /// Get file extension
    pub fn get_extension(&self, path: String) -> PyResult<Option<String>> {
        let path_buf = PathBuf::from(path);
        Ok(path_buf.extension()
            .map(|ext| ext.to_string_lossy().to_string()))
    }

    /// Get parent directory
    pub fn get_parent(&self, path: String) -> PyResult<Option<String>> {
        let path_buf = PathBuf::from(path);
        Ok(path_buf.parent()
            .map(|p| p.to_string_lossy().to_string()))
    }

    /// Check if path is absolute
    pub fn is_absolute(&self, path: String) -> bool {
        PathBuf::from(path).is_absolute()
    }

    /// Convert to absolute path (without requiring existence)
    pub fn to_absolute(&self, path: String, base: Option<String>) -> PyResult<String> {
        let path_buf = PathBuf::from(&path);

        let absolute = if path_buf.is_absolute() {
            path_buf
        } else {
            match base {
                Some(b) => PathBuf::from(b).join(path_buf),
                None => {
                    std::env::current_dir()
                        .map_err(|e| PyIOError::new_err(e.to_string()))?
                        .join(path_buf)
                }
            }
        };

        Ok(absolute.to_string_lossy().to_string())
    }

    /// Find common prefix of multiple paths
    pub fn common_prefix(&self, paths: Vec<String>) -> Option<String> {
        if paths.is_empty() {
            return None;
        }

        let path_bufs: Vec<PathBuf> = paths.iter().map(|p| PathBuf::from(p)).collect();
        let first_components: Vec<_> = path_bufs[0].components().collect();

        let mut common_len = 0;
        for i in 0..first_components.len() {
            if path_bufs.iter().all(|p| {
                p.components().nth(i) == Some(first_components[i])
            }) {
                common_len = i + 1;
            } else {
                break;
            }
        }

        if common_len == 0 {
            return None;
        }

        let mut result = PathBuf::new();
        for component in first_components.iter().take(common_len) {
            result.push(component);
        }

        Some(result.to_string_lossy().to_string())
    }
}
