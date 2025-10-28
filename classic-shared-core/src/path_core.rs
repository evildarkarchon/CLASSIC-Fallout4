//! High-performance path handling utilities with caching (Pure Rust)
//!
//! This module provides path operations optimized for the CLASSIC application.
//! It caches path lookups and provides efficient path validation.

use dashmap::DashMap;
use rayon::prelude::*;
use std::path::{PathBuf, Path};
use std::sync::Arc;
use std::time::{Duration, Instant};

use crate::{ClassicError, ClassicResult};

/// A structure representing an entry in a path cache.
#[derive(Clone, Debug)]
struct PathCacheEntry {
    /// The cached path value
    value: PathBuf,
    /// The time when this entry was created or last updated
    timestamp: Instant,
    /// The number of times this entry has been accessed
    hit_count: u32,
}

/// A structure to handle and manage paths with caching for resolved paths and validation results.
///
/// This struct provides functionality to cache resolved paths and their validation results
/// for a specified Time-To-Live (TTL) duration.
pub struct PathHandler {
    /// Cache for resolved paths with TTL
    path_cache: Arc<DashMap<String, PathCacheEntry>>,
    /// Cache for validation results
    validation_cache: Arc<DashMap<PathBuf, (bool, String, Instant)>>,
    /// Cache TTL duration
    cache_ttl: Duration,
}

impl PathHandler {
    /// Creates a new `PathHandler` with the specified cache TTL.
    ///
    /// # Arguments
    /// * `cache_ttl_seconds` - The duration (in seconds) for which cached items remain valid
    pub fn new(cache_ttl_seconds: u64) -> Self {
        Self {
            path_cache: Arc::new(DashMap::new()),
            validation_cache: Arc::new(DashMap::new()),
            cache_ttl: Duration::from_secs(cache_ttl_seconds),
        }
    }

    /// Normalizes a file path, resolving symbolic links and cleaning up any redundant components.
    ///
    /// This function checks for a cached result first to improve efficiency.
    pub fn normalize_path(&self, path: &str) -> ClassicResult<String> {
        // Check cache first - use get_mut() to update in-place
        if let Some(mut entry) = self.path_cache.get_mut(path) {
            if entry.timestamp.elapsed() < self.cache_ttl {
                entry.hit_count += 1;
                return Ok(entry.value.to_string_lossy().to_string());
            }
        }

        // Normalize the path
        let path_buf = PathBuf::from(path);
        let normalized = match path_buf.canonicalize() {
            Ok(p) => p,
            Err(e) => {
                log::debug!(
                    "Failed to canonicalize path '{}': {}. Using cleaned path instead.",
                    path,
                    e
                );
                self.clean_path(&path_buf)
            }
        };

        // Cache the result
        let entry = PathCacheEntry {
            value: normalized.clone(),
            timestamp: Instant::now(),
            hit_count: 1,
        };
        self.path_cache.insert(path.to_string(), entry);

        Ok(normalized.to_string_lossy().to_string())
    }

    /// Clear all caches
    pub fn clear_cache(&self) {
        self.path_cache.clear();
        self.validation_cache.clear();
    }

    /// Returns the current statistics of the internal caches.
    ///
    /// Returns a tuple containing:
    /// - The number of entries in the path_cache
    /// - The number of entries in the validation_cache
    pub fn cache_stats(&self) -> (usize, usize) {
        (self.path_cache.len(), self.validation_cache.len())
    }

    /// Cleans up expired items from both caches based on the configured cache TTL.
    pub fn cleanup_cache(&self) {
        let now = Instant::now();

        self.path_cache
            .retain(|_, entry| now.duration_since(entry.timestamp) < self.cache_ttl);

        self.validation_cache
            .retain(|_, (_, _, timestamp)| now.duration_since(*timestamp) < self.cache_ttl);
    }

    /// Validates a batch of file paths and caches the results.
    pub fn validate_paths_batch(&self, paths: &[String]) -> Vec<(String, bool, String)> {
        paths
            .par_iter()
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
                self.validation_cache
                    .insert(path_buf.clone(), (is_valid, msg.clone(), Instant::now()));

                (path.clone(), is_valid, msg)
            })
            .collect()
    }

    /// Join a base path with path components
    pub fn join_paths(&self, base: &str, components: &[String]) -> String {
        let mut path = PathBuf::from(base);
        for component in components {
            path.push(component);
        }
        path.to_string_lossy().to_string()
    }

    /// Split a path into its individual components
    pub fn split_path(&self, path: &str) -> Vec<String> {
        let path_buf = PathBuf::from(path);
        path_buf
            .components()
            .map(|c| c.as_os_str().to_string_lossy().to_string())
            .collect()
    }

    /// Get the filename from a path
    pub fn get_filename(&self, path: &str) -> Option<String> {
        let path_buf = PathBuf::from(path);
        path_buf
            .file_name()
            .map(|name| name.to_string_lossy().to_string())
    }

    /// Get the file extension from a path
    pub fn get_extension(&self, path: &str) -> Option<String> {
        let path_buf = PathBuf::from(path);
        path_buf
            .extension()
            .map(|ext| ext.to_string_lossy().to_string())
    }

    /// Get the parent directory from a path
    pub fn get_parent(&self, path: &str) -> Option<String> {
        let path_buf = PathBuf::from(path);
        path_buf.parent().map(|p| p.to_string_lossy().to_string())
    }

    /// Check if a path is absolute
    pub fn is_absolute(&self, path: &str) -> bool {
        PathBuf::from(path).is_absolute()
    }

    /// Convert a path to absolute
    pub fn to_absolute(&self, path: &str, base: Option<&str>) -> ClassicResult<String> {
        let path_buf = PathBuf::from(path);

        let absolute = if path_buf.is_absolute() {
            path_buf
        } else {
            match base {
                Some(b) => PathBuf::from(b).join(path_buf),
                None => std::env::current_dir()
                    .map_err(|e| ClassicError::io(e.to_string(), Some(e)))?
                    .join(path_buf),
            }
        };

        Ok(absolute.to_string_lossy().to_string())
    }

    /// Find the common prefix of multiple paths
    pub fn common_prefix(&self, paths: &[String]) -> Option<String> {
        if paths.is_empty() {
            return None;
        }

        let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
        let first_components: Vec<_> = path_bufs[0].components().collect();

        let mut common_len = 0;
        for i in 0..first_components.len() {
            if path_bufs
                .iter()
                .all(|p| p.components().nth(i) == Some(first_components[i]))
            {
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

    // Internal helper methods

    /// Cleans a path by resolving redundant components
    fn clean_path(&self, path: &Path) -> PathBuf {
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
        result
    }

    /// Validates a single file system path
    fn validate_single_path(&self, path: &Path) -> (bool, String) {
        if !path.exists() {
            return (false, format!("Path does not exist: {}", path.display()));
        }

        // Check if readable
        if let Err(e) = std::fs::metadata(path) {
            return (false, format!("Cannot read metadata: {}", e));
        }

        (true, String::new())
    }
}

impl Default for PathHandler {
    fn default() -> Self {
        Self::new(300) // Default 5 minutes TTL
    }
}
