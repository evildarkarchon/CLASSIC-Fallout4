//! Thread-safe YAML settings cache with dual sync/async API.

use crate::error::Result;
use crate::loader::{load_yaml_async, load_yaml_batch_async, load_yaml_batch_sync, load_yaml_sync};
use quick_cache::sync::Cache;
use serde::Serialize;
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, LazyLock};
use tracing::trace;
use yaml_rust2::Yaml;

/// Global settings cache storage.
///
/// Uses quick_cache for bounded concurrent access to cached YAML settings.
/// Each cache entry stores the parsed YAML documents for a file.
static SETTINGS_CACHE: LazyLock<Cache<String, Arc<Vec<Yaml>>>> = LazyLock::new(|| Cache::new(64));

/// Global counter for cache hits.
static CACHE_HITS: AtomicU64 = AtomicU64::new(0);

/// Global counter for cache misses.
static CACHE_MISSES: AtomicU64 = AtomicU64::new(0);

/// Cache performance statistics.
///
/// Provides insight into cache effectiveness via hit/miss tracking.
/// Use `cache_stats()` to retrieve current statistics.
///
/// # Example
///
/// ```rust
/// use classic_settings_core::cache_stats;
///
/// let stats = cache_stats();
/// println!("Hit rate: {:.2}%", stats.hit_rate * 100.0);
/// ```
#[derive(Debug, Clone, Serialize)]
pub struct CacheStats {
    /// Number of cache hits since last reset.
    pub hits: u64,
    /// Number of cache misses since last reset.
    pub misses: u64,
    /// Hit rate as a fraction (0.0 to 1.0).
    pub hit_rate: f64,
    /// Current number of entries in the cache.
    pub size: usize,
    /// Maximum bounded cache capacity.
    pub capacity: usize,
}

/// Get current cache statistics.
///
/// Returns the current hit/miss counts and derived hit rate.
///
/// # Example
///
/// ```rust
/// use classic_settings_core::cache_stats;
///
/// let stats = cache_stats();
/// println!("Hits: {}, Misses: {}", stats.hits, stats.misses);
/// println!("Hit rate: {:.1}%", stats.hit_rate * 100.0);
/// ```
pub fn cache_stats() -> CacheStats {
    let hits = CACHE_HITS.load(Ordering::Relaxed);
    let misses = CACHE_MISSES.load(Ordering::Relaxed);
    let total = hits + misses;

    CacheStats {
        hits,
        misses,
        hit_rate: if total > 0 {
            hits as f64 / total as f64
        } else {
            0.0
        },
        size: SETTINGS_CACHE.len(),
        capacity: SETTINGS_CACHE.capacity() as usize,
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
/// use classic_settings_core::{reset_cache_stats, cache_stats};
///
/// reset_cache_stats();
/// let stats = cache_stats();
/// assert_eq!(stats.hits, 0);
/// assert_eq!(stats.misses, 0);
/// ```
pub fn reset_cache_stats() {
    CACHE_HITS.store(0, Ordering::Relaxed);
    CACHE_MISSES.store(0, Ordering::Relaxed);
}

/// Load and cache YAML settings synchronously.
///
/// Loads a YAML file, caches it with the given key, and returns the parsed documents.
/// If the key already exists in the cache, it will be replaced.
///
/// # Arguments
///
/// * `key` - Cache key (typically the file path or a logical name)
/// * `path` - Path to the YAML file
///
/// # Returns
///
/// The parsed YAML documents.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_settings_sync;
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let docs = load_settings_sync("game_config", Path::new("config.yaml"))?;
/// # Ok(())
/// # }
/// ```
pub fn load_settings_sync(key: &str, path: &Path) -> Result<Arc<Vec<Yaml>>> {
    let docs = load_yaml_sync(path)?;
    let arc_docs = Arc::new(docs);
    SETTINGS_CACHE.insert(key.to_string(), arc_docs.clone());
    Ok(arc_docs)
}

/// Load and cache YAML settings asynchronously.
///
/// Loads a YAML file asynchronously, caches it with the given key, and returns the parsed documents.
/// If the key already exists in the cache, it will be replaced.
///
/// # Arguments
///
/// * `key` - Cache key (typically the file path or a logical name)
/// * `path` - Path to the YAML file
///
/// # Returns
///
/// The parsed YAML documents.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_settings_async;
/// use std::path::Path;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let docs = load_settings_async("game_config", Path::new("config.yaml")).await?;
/// # Ok(())
/// # }
/// ```
pub async fn load_settings_async(key: &str, path: &Path) -> Result<Arc<Vec<Yaml>>> {
    let docs = load_yaml_async(path).await?;
    let arc_docs = Arc::new(docs);
    SETTINGS_CACHE.insert(key.to_string(), arc_docs.clone());
    Ok(arc_docs)
}

/// Load multiple YAML settings in batch (synchronous).
///
/// Loads multiple YAML files and caches them. Each path becomes its own cache key.
///
/// # Arguments
///
/// * `paths` - Slice of paths to load
///
/// # Returns
///
/// Number of files successfully loaded and cached.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_batch_sync;
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let paths = vec![Path::new("config1.yaml"), Path::new("config2.yaml")];
/// let count = load_batch_sync(&paths)?;
/// # Ok(())
/// # }
/// ```
pub fn load_batch_sync(paths: &[&Path]) -> Result<usize> {
    let results = load_yaml_batch_sync(paths)?;

    for (path_str, docs) in results {
        SETTINGS_CACHE.insert(path_str, Arc::new(docs));
    }

    Ok(paths.len())
}

/// Load multiple YAML settings in batch (asynchronous).
///
/// Loads multiple YAML files concurrently and caches them. Each path becomes its own cache key.
///
/// # Arguments
///
/// * `paths` - Slice of paths to load
///
/// # Returns
///
/// Number of files successfully loaded and cached.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_batch_async;
/// use std::path::Path;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let paths = vec![Path::new("config1.yaml"), Path::new("config2.yaml")];
/// let count = load_batch_async(&paths).await?;
/// # Ok(())
/// # }
/// ```
pub async fn load_batch_async(paths: &[&Path]) -> Result<usize> {
    let results = load_yaml_batch_async(paths).await?;

    for (path_str, docs) in results {
        SETTINGS_CACHE.insert(path_str, Arc::new(docs));
    }

    Ok(paths.len())
}

/// Get cached settings by key.
///
/// Retrieves cached YAML documents by key. Returns None if the key is not in the cache.
/// Tracks cache hits and misses for performance monitoring.
///
/// # Arguments
///
/// * `key` - Cache key to look up
///
/// # Returns
///
/// The cached YAML documents, or None if not found.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{get_cached, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// let docs = get_cached("game_config");
/// assert!(docs.is_some());
/// # Ok(())
/// # }
/// ```
pub fn get_cached(key: &str) -> Option<Arc<Vec<Yaml>>> {
    match SETTINGS_CACHE.get(key) {
        Some(entry) => {
            CACHE_HITS.fetch_add(1, Ordering::Relaxed);
            trace!(cache = "settings", key = %key, "cache hit");
            Some(entry)
        }
        None => {
            CACHE_MISSES.fetch_add(1, Ordering::Relaxed);
            trace!(cache = "settings", key = %key, "cache miss");
            None
        }
    }
}

/// Check if a key exists in the cache.
///
/// # Arguments
///
/// * `key` - Cache key to check
///
/// # Returns
///
/// `true` if the key exists, `false` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{is_cached, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// assert!(is_cached("game_config"));
/// # Ok(())
/// # }
/// ```
pub fn is_cached(key: &str) -> bool {
    SETTINGS_CACHE.contains_key(key)
}

/// Invalidate (remove) a cached entry.
///
/// Removes a key from the cache. Returns `true` if the key existed and was removed.
///
/// # Arguments
///
/// * `key` - Cache key to invalidate
///
/// # Returns
///
/// `true` if the key was removed, `false` if it didn't exist.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{invalidate, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// let removed = invalidate("game_config");
/// assert!(removed);
/// # Ok(())
/// # }
/// ```
pub fn invalidate(key: &str) -> bool {
    SETTINGS_CACHE.remove(key).is_some()
}

/// Clear all cached settings.
///
/// Removes all entries from the cache.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::clear_cache;
///
/// clear_cache();
/// ```
pub fn clear_cache() {
    SETTINGS_CACHE.clear();
}

/// Get the number of cached entries.
///
/// # Returns
///
/// The number of entries currently in the cache.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{cache_size, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// assert_eq!(cache_size(), 1);
/// # Ok(())
/// # }
/// ```
pub fn cache_size() -> usize {
    SETTINGS_CACHE.len()
}

/// Get all cache keys.
///
/// Returns a vector of all keys currently in the cache.
///
/// # Returns
///
/// Vector of cache keys.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{cache_keys, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("config1", Path::new("config1.yaml"))?;
/// load_settings_sync("config2", Path::new("config2.yaml"))?;
/// let keys = cache_keys();
/// assert_eq!(keys.len(), 2);
/// # Ok(())
/// # }
/// ```
pub fn cache_keys() -> Vec<String> {
    SETTINGS_CACHE.iter().map(|(key, _)| key).collect()
}

#[cfg(test)]
#[path = "cache_tests.rs"]
mod tests;
