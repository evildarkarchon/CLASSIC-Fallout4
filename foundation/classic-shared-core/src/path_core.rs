//! High-performance path handling utilities with caching (Pure Rust)
//!
//! This module provides path operations optimized for the CLASSIC application.
//! It caches path lookups and provides efficient path validation.

use dashmap::DashMap;
use rayon::prelude::*;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
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
///
/// # Performance Optimization
/// The cache implements LRU eviction with configurable size limits to prevent unbounded growth.
/// This ensures O(1) lookups while maintaining bounded memory usage.
pub struct PathHandler {
    /// Cache for resolved paths with TTL
    path_cache: Arc<DashMap<String, PathCacheEntry>>,
    /// Cache for validation results
    validation_cache: Arc<DashMap<PathBuf, (bool, String, Instant)>>,
    /// Cache TTL duration
    cache_ttl: Duration,
    /// Maximum cache size (0 = unlimited)
    max_cache_size: usize,
    /// Cache hit counter
    cache_hits: AtomicUsize,
    /// Cache miss counter
    cache_misses: AtomicUsize,
}

impl PathHandler {
    /// Creates a new `PathHandler` with the specified cache TTL (unlimited size).
    ///
    /// # Arguments
    /// * `cache_ttl_seconds` - The duration (in seconds) for which cached items remain valid
    pub fn new(cache_ttl_seconds: u64) -> Self {
        Self::new_with_limits(cache_ttl_seconds, 0) // 0 = unlimited
    }

    /// Creates a new `PathHandler` with specified cache TTL and size limit.
    ///
    /// # Arguments
    /// * `cache_ttl_seconds` - The duration (in seconds) for which cached items remain valid
    /// * `max_cache_size` - Maximum number of entries in cache (0 = unlimited, recommended: 10000)
    ///
    /// # Performance
    /// Using a bounded cache prevents memory leaks in long-running applications.
    /// When the cache reaches max_cache_size, the LRU (least recently used) entries are evicted.
    pub fn new_with_limits(cache_ttl_seconds: u64, max_cache_size: usize) -> Self {
        Self {
            path_cache: Arc::new(DashMap::new()),
            validation_cache: Arc::new(DashMap::new()),
            cache_ttl: Duration::from_secs(cache_ttl_seconds),
            max_cache_size,
            cache_hits: AtomicUsize::new(0),
            cache_misses: AtomicUsize::new(0),
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
                self.cache_hits.fetch_add(1, Ordering::Relaxed);
                return Ok(entry.value.to_string_lossy().to_string());
            }
        }

        // Cache miss
        self.cache_misses.fetch_add(1, Ordering::Relaxed);

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

        // Evict LRU entries if cache is full
        self.evict_lru_if_needed();

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

    /// Returns cache hit/miss statistics
    ///
    /// Returns a tuple containing:
    /// - Number of cache hits
    /// - Number of cache misses
    /// - Hit rate (0.0 to 1.0)
    pub fn cache_metrics(&self) -> (usize, usize, f64) {
        let hits = self.cache_hits.load(Ordering::Relaxed);
        let misses = self.cache_misses.load(Ordering::Relaxed);
        let total = hits + misses;
        let hit_rate = if total > 0 {
            hits as f64 / total as f64
        } else {
            0.0
        };
        (hits, misses, hit_rate)
    }

    /// Evicts LRU entries if cache exceeds max_cache_size
    ///
    /// This method is called automatically when inserting new entries.
    /// It removes the least-used 20% of entries to avoid thrashing.
    fn evict_lru_if_needed(&self) {
        // Skip if no size limit or cache is not full
        if self.max_cache_size == 0 || self.path_cache.len() < self.max_cache_size {
            return;
        }

        // Collect all entries with their hit counts
        let mut entries: Vec<(String, u32)> = self
            .path_cache
            .iter()
            .map(|e| (e.key().clone(), e.value().hit_count))
            .collect();

        // Sort by hit count (ascending - least used first)
        entries.sort_by_key(|(_, hits)| *hits);

        // Remove bottom 20% to avoid frequent evictions
        let to_remove = (self.max_cache_size / 5).max(1);
        for (key, _) in entries.iter().take(to_remove) {
            self.path_cache.remove(key);
        }

        log::debug!(
            "Evicted {} LRU entries from path cache (size: {} -> {})",
            to_remove,
            self.path_cache.len() + to_remove,
            self.path_cache.len()
        );
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
        for (i, component) in first_components.iter().enumerate() {
            if path_bufs
                .iter()
                .all(|p| p.components().nth(i) == Some(*component))
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

#[cfg(test)]
#[path = "path_core_tests.rs"]
mod tests;
