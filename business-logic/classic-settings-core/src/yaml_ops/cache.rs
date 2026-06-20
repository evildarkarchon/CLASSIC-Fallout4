//! Global cache and cache statistics for YAML operations.

use quick_cache::sync::Cache;
use serde::Serialize;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, LazyLock};
use std::time::SystemTime;
use yaml_rust2::Yaml;

/// Global YAML cache for frequently accessed files
///
/// NOTE: This is lazily initialized on first use to avoid deadlocks during module import.
/// The cache is thread-safe and uses `quick_cache` with a fixed 128-entry capacity.
pub(super) static YAML_CACHE: LazyLock<Cache<PathBuf, CachedYaml>> =
    LazyLock::new(|| Cache::new(128));

/// Global counter for cache hits.
pub(super) static CACHE_HITS: AtomicU64 = AtomicU64::new(0);

/// Global counter for cache misses.
pub(super) static CACHE_MISSES: AtomicU64 = AtomicU64::new(0);

/// Cache performance statistics.
///
/// Provides insight into cache effectiveness via hit/miss tracking.
/// Use `yaml_cache_stats()` to retrieve current statistics.
///
/// # Example
///
/// ```rust
/// use classic_settings_core::yaml_cache_stats;
///
/// let stats = yaml_cache_stats();
/// println!("Hit rate: {:.2}%", stats.hit_rate * 100.0);
/// ```
#[derive(Debug, Clone, Serialize)]
pub struct YamlCacheStats {
    /// Number of cache hits since last reset.
    pub hits: u64,
    /// Number of cache misses since last reset.
    pub misses: u64,
    /// Hit rate as a fraction (0.0 to 1.0).
    pub hit_rate: f64,
    /// Current number of entries in the cache.
    pub size: usize,
    /// Maximum number of entries the cache retains before evicting.
    pub capacity: usize,
}

pub(super) fn total_cached_bytes() -> usize {
    YAML_CACHE
        .iter()
        .map(|(_, cached)| cached.raw_content.as_ref().map_or(0, String::len))
        .sum()
}

/// Get current cache statistics.
///
/// Returns the current hit/miss counts and derived hit rate.
///
/// # Example
///
/// ```rust
/// use classic_settings_core::yaml_cache_stats;
///
/// let stats = yaml_cache_stats();
/// println!("Hits: {}, Misses: {}", stats.hits, stats.misses);
/// println!("Hit rate: {:.1}%", stats.hit_rate * 100.0);
/// ```
pub fn yaml_cache_stats() -> YamlCacheStats {
    let hits = CACHE_HITS.load(Ordering::Relaxed);
    let misses = CACHE_MISSES.load(Ordering::Relaxed);
    let total = hits + misses;

    YamlCacheStats {
        hits,
        misses,
        hit_rate: if total > 0 {
            hits as f64 / total as f64
        } else {
            0.0
        },
        size: YAML_CACHE.len(),
        capacity: usize::try_from(YAML_CACHE.capacity()).unwrap_or(usize::MAX),
    }
}

/// Reset cache statistics.
///
/// Resets hit and miss counters to zero. Useful for testing or
/// starting fresh measurements.
///
/// # Example
///
/// ```rust
/// use classic_settings_core::{reset_yaml_cache_stats, yaml_cache_stats};
///
/// reset_yaml_cache_stats();
/// let stats = yaml_cache_stats();
/// assert_eq!(stats.hits, 0);
/// assert_eq!(stats.misses, 0);
/// ```
pub fn reset_yaml_cache_stats() {
    CACHE_HITS.store(0, Ordering::Relaxed);
    CACHE_MISSES.store(0, Ordering::Relaxed);
}

/// A structure representing a cached YAML configuration or data.
///
/// The `CachedYaml` struct is designed to encapsulate YAML data along with metadata
/// regarding the last modification time and optional raw content. This can be useful for
/// scenarios where YAML data needs to be cached and periodically checked for updates.
/// # Fields
///
/// - `data`:
///   A thread-safe, shared reference-counted pointer (`Arc`) to the parsed YAML data.
///   This allows safe shared usage of the YAML data across threads.
///
/// - `modified`:
///   A `SystemTime` instance representing the last time the YAML resource
///   was modified. This can be used to determine whether the cached data
///   is up-to-date with the source.
///
/// - `raw_content`:
///   An optional `String` containing the raw content of the YAML file.
///   This is only present if the raw text representation is required in addition
///   to the parsed YAML data.
///
/// # Derives
///
/// - `Clone`:
///   The `Clone` trait allows creating a duplicate `CachedYaml` instance efficiently.
///   This is made possible due to the usage of `Arc` for the `data` field, which ensures
///   that the cloned instance shares the same underlying data rather than duplicating it.
///
/// # Usage
///
/// This struct is ideal for caching parsed YAML content while retaining flexibility for metadata
/// like the last modified time and raw content. It can support scenarios like file change
/// detection, configuration management, or data consistency checks.
///
/// # Example
///
/// ```rust,ignore
/// use std::sync::Arc;
/// use std::time::SystemTime;
/// use yaml_rust2::Yaml;
///
/// // CachedYaml is a private struct
/// ```
#[derive(Clone)]
pub(super) struct CachedYaml {
    pub(super) data: Arc<Yaml>,
    pub(super) modified: SystemTime,
    pub(super) raw_content: Option<String>,
}

/// Clear the global YAML cache
///
/// This function clears all cached YAML data. It's primarily useful for
/// testing to ensure clean state between test runs.
///
/// # Example
/// ```rust,no_run
/// use classic_settings_core::clear_global_yaml_cache;
///
/// // Clear all cached YAML files
/// clear_global_yaml_cache();
/// ```
pub fn clear_global_yaml_cache() {
    YAML_CACHE.clear();
}

#[cfg(test)]
#[path = "cache_tests.rs"]
mod tests;
