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
mod tests {
    use super::*;
    use serial_test::serial;
    use std::io::Write;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::thread;
    use tempfile::NamedTempFile;

    fn create_test_yaml(content: &str) -> NamedTempFile {
        let mut file = NamedTempFile::new().unwrap();
        file.write_all(content.as_bytes()).unwrap();
        file.flush().unwrap();
        file
    }

    fn reset_cache_state() {
        clear_cache();
        reset_cache_stats();
    }

    #[test]
    #[serial]
    fn test_load_settings_sync() {
        reset_cache_state();

        let yaml_content = "key: value\nnumber: 42\n";
        let file = create_test_yaml(yaml_content);

        let result = load_settings_sync("test", file.path());
        assert!(result.is_ok());

        let cached = get_cached("test");
        assert!(cached.is_some());
    }

    #[tokio::test]
    #[serial]
    async fn test_load_settings_async() {
        reset_cache_state();

        let yaml_content = "key: value\nnumber: 42\n";
        let file = create_test_yaml(yaml_content);

        let result = load_settings_async("test_async", file.path()).await;
        assert!(result.is_ok());

        let cached = get_cached("test_async");
        assert!(cached.is_some());
    }

    #[test]
    #[serial]
    fn test_load_batch_sync() {
        reset_cache_state();

        let yaml1 = create_test_yaml("key1: value1\n");
        let yaml2 = create_test_yaml("key2: value2\n");

        let paths = vec![yaml1.path(), yaml2.path()];
        let result = load_batch_sync(&paths);

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 2);
        assert_eq!(cache_size(), 2);
    }

    #[tokio::test]
    #[serial]
    async fn test_load_batch_async() {
        reset_cache_state();

        let yaml1 = create_test_yaml("key1: value1\n");
        let yaml2 = create_test_yaml("key2: value2\n");

        let paths = vec![yaml1.path(), yaml2.path()];
        let result = load_batch_async(&paths).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 2);
        assert_eq!(cache_size(), 2);
    }

    #[test]
    #[serial]
    fn test_cache_operations() {
        reset_cache_state();

        let yaml_content = "key: value\n";
        let file = create_test_yaml(yaml_content);

        // Load and check
        load_settings_sync("test_key", file.path()).unwrap();
        assert!(is_cached("test_key"));
        assert_eq!(cache_size(), 1);

        // Get keys
        let keys = cache_keys();
        assert_eq!(keys.len(), 1);
        assert!(keys.contains(&"test_key".to_string()));

        let stats = cache_stats();
        assert_eq!(stats.size, 1);
        assert_eq!(stats.capacity, 64);

        // Invalidate
        let removed = invalidate("test_key");
        assert!(removed);
        assert!(!is_cached("test_key"));
        assert_eq!(cache_size(), 0);
    }

    #[test]
    #[serial]
    fn test_clear_cache() {
        reset_cache_state();

        let yaml1 = create_test_yaml("key1: value1\n");
        let yaml2 = create_test_yaml("key2: value2\n");

        load_settings_sync("key1", yaml1.path()).unwrap();
        load_settings_sync("key2", yaml2.path()).unwrap();

        assert_eq!(cache_size(), 2);

        clear_cache();
        assert_eq!(cache_size(), 0);
    }

    // ========================================================================
    // Additional Tests for Improved Coverage
    // ========================================================================

    #[test]
    #[serial]
    fn test_concurrent_read_access() {
        reset_cache_state();

        // Pre-populate cache
        let yaml_content = "concurrent: test\n";
        let file = create_test_yaml(yaml_content);
        load_settings_sync("concurrent_read", file.path()).unwrap();

        let success_count = AtomicUsize::new(0);

        // Spawn multiple threads to read concurrently
        thread::scope(|s| {
            for _ in 0..20 {
                s.spawn(|| {
                    for _ in 0..100 {
                        let cached = get_cached("concurrent_read");
                        if cached.is_some() {
                            success_count.fetch_add(1, Ordering::Relaxed);
                        }
                    }
                });
            }
        });

        // All reads should succeed
        assert_eq!(success_count.load(Ordering::Relaxed), 2000);
    }

    #[test]
    #[serial]
    fn test_concurrent_write_access() {
        reset_cache_state();

        let yaml_content = "write: test\n";
        let file = create_test_yaml(yaml_content);
        let path = file.path().to_path_buf();

        // Spawn multiple threads to write concurrently
        thread::scope(|s| {
            for i in 0..10 {
                let path = path.clone();
                s.spawn(move || {
                    let key = format!("concurrent_write_{}", i);
                    let _ = load_settings_sync(&key, &path);
                });
            }
        });

        // All writes should succeed
        assert_eq!(cache_size(), 10);
    }

    #[test]
    #[serial]
    fn test_concurrent_read_write() {
        reset_cache_state();

        let yaml_content = "mixed: access\n";
        let file = create_test_yaml(yaml_content);
        let path = file.path().to_path_buf();

        // Pre-populate
        load_settings_sync("mixed_key", &path).unwrap();

        thread::scope(|s| {
            // Readers
            for _ in 0..5 {
                s.spawn(|| {
                    for _ in 0..50 {
                        let _ = get_cached("mixed_key");
                        let _ = is_cached("mixed_key");
                        let _ = cache_keys();
                    }
                });
            }

            // Writers
            for i in 0..5 {
                let path = path.clone();
                s.spawn(move || {
                    for j in 0..10 {
                        let key = format!("writer_{}_{}", i, j);
                        let _ = load_settings_sync(&key, &path);
                    }
                });
            }
        });

        // All writer keys plus original key
        assert!(cache_size() >= 1);
    }

    #[test]
    #[serial]
    fn test_is_cached_on_empty_cache() {
        reset_cache_state();

        assert!(!is_cached("nonexistent"));
        assert!(!is_cached(""));
        assert!(!is_cached("   "));
    }

    #[test]
    #[serial]
    fn test_get_cached_on_empty_cache() {
        reset_cache_state();

        assert!(get_cached("nonexistent").is_none());
        assert!(get_cached("").is_none());
    }

    #[test]
    #[serial]
    fn test_invalidate_nonexistent_key() {
        reset_cache_state();

        assert!(!invalidate("never_added"));
        assert!(!invalidate(""));
    }

    #[test]
    #[serial]
    fn test_cache_keys_empty() {
        reset_cache_state();

        let keys = cache_keys();
        assert!(keys.is_empty());
    }

    #[test]
    #[serial]
    fn test_cache_size_empty() {
        reset_cache_state();

        assert_eq!(cache_size(), 0);
    }

    #[test]
    #[serial]
    fn test_clear_empty_cache() {
        reset_cache_state();

        // Should not panic on empty cache
        clear_cache();
        assert_eq!(cache_size(), 0);
    }

    #[test]
    #[serial]
    fn test_reload_same_key_updates_value() {
        reset_cache_state();

        let yaml1 = create_test_yaml("version: 1\n");
        let yaml2 = create_test_yaml("version: 2\n");

        load_settings_sync("version_key", yaml1.path()).unwrap();
        let cached1 = get_cached("version_key").unwrap();
        assert_eq!(cached1[0]["version"].as_i64(), Some(1));

        load_settings_sync("version_key", yaml2.path()).unwrap();
        let cached2 = get_cached("version_key").unwrap();
        assert_eq!(cached2[0]["version"].as_i64(), Some(2));

        // Cache size should still be 1
        assert_eq!(cache_size(), 1);
    }

    #[tokio::test]
    #[serial]
    async fn test_async_reload_same_key_updates_value() {
        reset_cache_state();

        let yaml1 = create_test_yaml("async_version: 1\n");
        let yaml2 = create_test_yaml("async_version: 2\n");

        load_settings_async("async_version_key", yaml1.path())
            .await
            .unwrap();
        let cached1 = get_cached("async_version_key").unwrap();
        assert_eq!(cached1[0]["async_version"].as_i64(), Some(1));

        load_settings_async("async_version_key", yaml2.path())
            .await
            .unwrap();
        let cached2 = get_cached("async_version_key").unwrap();
        assert_eq!(cached2[0]["async_version"].as_i64(), Some(2));
    }

    #[test]
    #[serial]
    fn test_arc_cloning_preserves_reference() {
        reset_cache_state();

        let yaml_content = "arc: test\n";
        let file = create_test_yaml(yaml_content);

        let result = load_settings_sync("arc_key", file.path()).unwrap();

        // Get from cache
        let cached = get_cached("arc_key").unwrap();

        // Both should be same Arc
        assert!(Arc::ptr_eq(&result, &cached));
    }

    #[test]
    #[serial]
    fn test_load_batch_sync_empty_paths() {
        reset_cache_state();

        let paths: Vec<&Path> = vec![];
        let result = load_batch_sync(&paths);

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 0);
        assert_eq!(cache_size(), 0);
    }

    #[tokio::test]
    #[serial]
    async fn test_load_batch_async_empty_paths() {
        reset_cache_state();

        let paths: Vec<&Path> = vec![];
        let result = load_batch_async(&paths).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 0);
        assert_eq!(cache_size(), 0);
    }

    #[test]
    #[serial]
    fn test_special_key_characters() {
        reset_cache_state();

        let yaml_content = "key: value\n";
        let file = create_test_yaml(yaml_content);

        // Test keys with special characters
        let special_keys = [
            "key with spaces",
            "key/with/slashes",
            "key\\with\\backslashes",
            "key:with:colons",
            "key.with.dots",
            "key-with-dashes",
            "key_with_underscores",
            "中文键",
            "キー",
            "🔑",
        ];

        for key in special_keys {
            load_settings_sync(key, file.path()).unwrap();
            assert!(is_cached(key), "Key '{}' should be cached", key);
        }

        assert_eq!(cache_size(), special_keys.len());
    }

    #[test]
    #[serial]
    fn test_batch_uses_path_as_key() {
        reset_cache_state();

        let yaml1 = create_test_yaml("batch: one\n");
        let yaml2 = create_test_yaml("batch: two\n");

        let path1_str = yaml1.path().display().to_string();
        let path2_str = yaml2.path().display().to_string();

        let paths = vec![yaml1.path(), yaml2.path()];
        load_batch_sync(&paths).unwrap();

        // Keys should be the path strings
        let keys = cache_keys();
        assert!(keys.contains(&path1_str));
        assert!(keys.contains(&path2_str));
    }

    #[tokio::test]
    #[serial]
    async fn test_async_batch_uses_path_as_key() {
        reset_cache_state();

        let yaml1 = create_test_yaml("async_batch: one\n");
        let yaml2 = create_test_yaml("async_batch: two\n");

        let path1_str = yaml1.path().display().to_string();
        let path2_str = yaml2.path().display().to_string();

        let paths = vec![yaml1.path(), yaml2.path()];
        load_batch_async(&paths).await.unwrap();

        let keys = cache_keys();
        assert!(keys.contains(&path1_str));
        assert!(keys.contains(&path2_str));
    }

    #[test]
    #[serial]
    fn test_invalidate_during_reads() {
        reset_cache_state();

        let yaml_content = "invalidate: test\n";
        let file = create_test_yaml(yaml_content);

        load_settings_sync("inv_key", file.path()).unwrap();

        thread::scope(|s| {
            // Readers
            for _ in 0..5 {
                s.spawn(|| {
                    for _ in 0..100 {
                        // These may or may not find the key depending on timing
                        let _ = get_cached("inv_key");
                    }
                });
            }

            // Invalidator
            s.spawn(|| {
                std::thread::sleep(std::time::Duration::from_millis(1));
                let _ = invalidate("inv_key");
            });
        });

        // After all threads complete, key should be invalidated
        assert!(!is_cached("inv_key"));
    }

    #[test]
    #[serial]
    fn test_cache_hit_and_miss_stats_follow_get_cached_behavior() {
        reset_cache_state();

        let yaml_content = "many: entries\n";
        let file = create_test_yaml(yaml_content);

        load_settings_sync("tracked_key", file.path()).unwrap();

        assert!(get_cached("tracked_key").is_some());
        assert!(get_cached("missing_key").is_none());

        let stats = cache_stats();
        assert_eq!(stats.hits, 1);
        assert_eq!(stats.misses, 1);
        assert_eq!(stats.hit_rate, 0.5);
    }

    #[test]
    #[serial]
    fn test_cache_stats_reports_canonical_capacity_fields() {
        reset_cache_state();

        let CacheStats {
            hits,
            misses,
            hit_rate,
            size,
            capacity,
        } = cache_stats();

        assert_eq!(hits, 0);
        assert_eq!(misses, 0);
        assert_eq!(hit_rate, 0.0);
        assert_eq!(size, 0);
        assert_eq!(capacity, 64);
    }

    #[test]
    #[serial]
    fn test_bounded_cache_never_exceeds_capacity_without_asserting_victim_order() {
        reset_cache_state();

        let yaml_content = "many: entries\n";
        let file = create_test_yaml(yaml_content);

        for i in 0..128 {
            let key = format!("entry_{}", i);
            load_settings_sync(&key, file.path()).unwrap();
        }

        assert!(cache_size() <= 64);

        let stats = cache_stats();
        assert!(stats.size <= 64);
        assert_eq!(stats.capacity, 64);

        clear_cache();
        assert_eq!(cache_size(), 0);
    }
}
