//! Thread-safe YAML settings cache with dual sync/async API.
//!
//! Entries are keyed by caller-chosen logical names. A scope holds at most 64
//! entries, never checks file freshness (a key is refreshed only by loading
//! it again), counts hits and misses only on `get_cached`, and keeps entry
//! eviction (`clear_cache`, `invalidate`) separate from counter resets
//! (`reset_cache_stats`).
//!
//! # Scopes
//!
//! Every store lives behind a [`LogicalKeyCacheScope`] handle. The unscoped
//! free functions in this module use one lazily created process default
//! scope, which is what Rust, CXX, and Node callers have always observed. A
//! binding adapter that links several former extension images into one
//! library (the merged Python extension) creates
//! [`LogicalKeyCacheScope::new_isolated`] handles so each facade keeps its own
//! entries and counters. This cache stays distinct from the path/mtime-aware
//! YAML-file cache; neither scope type reaches the other's store.

use crate::yaml::error::Result;
use crate::yaml::loader::{
    load_yaml_async, load_yaml_batch_async, load_yaml_batch_sync, load_yaml_sync,
};
use quick_cache::sync::Cache;
use serde::Serialize;
use std::fmt;
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, LazyLock};
use tracing::trace;
use yaml_rust2::Yaml;

/// Number of logical keys one settings cache scope retains.
const LOGICAL_KEY_CACHE_CAPACITY: usize = 64;

/// One logical-key cache store: its entries plus the `get_cached` hit/miss
/// counters that describe them. A scope handle owns exactly one of these.
struct LogicalKeyCacheStore {
    /// Uses quick_cache for bounded concurrent access to cached YAML settings.
    /// Each cache entry stores the parsed YAML documents for a file.
    entries: Cache<String, Arc<Vec<Yaml>>>,
    /// `get_cached` hits since the last counter reset.
    hits: AtomicU64,
    /// `get_cached` misses since the last counter reset.
    misses: AtomicU64,
}

impl LogicalKeyCacheStore {
    fn new() -> Self {
        Self {
            entries: Cache::new(LOGICAL_KEY_CACHE_CAPACITY),
            hits: AtomicU64::new(0),
            misses: AtomicU64::new(0),
        }
    }
}

/// Process default settings cache scope used by the unscoped functions.
static DEFAULT_SCOPE: LazyLock<LogicalKeyCacheScope> = LazyLock::new(|| LogicalKeyCacheScope {
    store: Arc::new(LogicalKeyCacheStore::new()),
});

/// Opaque handle to one logical-key settings cache store.
///
/// Cloning a handle shares the same store; two handles compare equal exactly
/// when they name the same store. [`LogicalKeyCacheScope::default_scope`] is
/// the store behind this module's unscoped functions
/// ([`load_settings_sync`], [`get_cached`], [`cache_stats`], ...).
/// [`LogicalKeyCacheScope::new_isolated`] creates a fresh store with the same
/// 64-entry capacity, freshness, counter, and clear rules that shares nothing
/// with any other scope. Each method behaves exactly like the free function of
/// the same name, applied to this scope's store.
///
/// # Example
///
/// ```rust
/// use classic_shared_core::yaml::{LogicalKeyCacheScope, is_cached};
/// # use std::io::Write;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let mut file = tempfile::NamedTempFile::new()?;
/// # file.write_all(b"game: Fallout4\n")?;
/// let scope = LogicalKeyCacheScope::new_isolated();
/// scope.load_settings_sync("game_config", file.path())?;
/// assert!(scope.is_cached("game_config"));
/// assert!(!is_cached("game_config"));
/// # Ok(())
/// # }
/// # example().unwrap();
/// ```
#[derive(Clone)]
pub struct LogicalKeyCacheScope {
    store: Arc<LogicalKeyCacheStore>,
}

impl LogicalKeyCacheScope {
    /// Return a handle to the process default scope used by the unscoped
    /// functions in this module.
    #[must_use]
    pub fn default_scope() -> Self {
        DEFAULT_SCOPE.clone()
    }

    /// Create a new, empty scope that shares no entries or counters with any
    /// other scope, including the default one.
    #[must_use]
    pub fn new_isolated() -> Self {
        Self {
            store: Arc::new(LogicalKeyCacheStore::new()),
        }
    }

    /// Return this scope's `get_cached` hit/miss counters, entry count, and
    /// capacity. See [`cache_stats`].
    #[must_use]
    pub fn cache_stats(&self) -> CacheStats {
        let hits = self.store.hits.load(Ordering::Relaxed);
        let misses = self.store.misses.load(Ordering::Relaxed);
        let total = hits + misses;

        CacheStats {
            hits,
            misses,
            hit_rate: if total > 0 {
                hits as f64 / total as f64
            } else {
                0.0
            },
            size: self.store.entries.len(),
            capacity: self.store.entries.capacity() as usize,
        }
    }

    /// Reset this scope's hit and miss counters without evicting entries.
    /// See [`reset_cache_stats`].
    pub fn reset_cache_stats(&self) {
        self.store.hits.store(0, Ordering::Relaxed);
        self.store.misses.store(0, Ordering::Relaxed);
    }

    /// Load `path` and cache its documents under `key` in this scope,
    /// replacing any previous entry. See [`load_settings_sync`].
    ///
    /// # Errors
    ///
    /// Returns the loader's [`SettingsError`](crate::yaml::SettingsError) if
    /// the file cannot be read or parsed; the scope is left unchanged.
    pub fn load_settings_sync(&self, key: &str, path: &Path) -> Result<Arc<Vec<Yaml>>> {
        let docs = load_yaml_sync(path)?;
        let arc_docs = Arc::new(docs);
        self.store.entries.insert(key.to_string(), arc_docs.clone());
        Ok(arc_docs)
    }

    /// Asynchronously load `path` and cache its documents under `key` in this
    /// scope. See [`load_settings_async`].
    ///
    /// The scope is captured by reference for the whole await, so the entry
    /// lands in this scope regardless of which runtime thread resumes it.
    ///
    /// # Errors
    ///
    /// Returns the loader's [`SettingsError`](crate::yaml::SettingsError) if
    /// the file cannot be read or parsed; the scope is left unchanged.
    pub async fn load_settings_async(&self, key: &str, path: &Path) -> Result<Arc<Vec<Yaml>>> {
        let docs = load_yaml_async(path).await?;
        let arc_docs = Arc::new(docs);
        self.store.entries.insert(key.to_string(), arc_docs.clone());
        Ok(arc_docs)
    }

    /// Load every path and cache each under its own path string in this
    /// scope. See [`load_batch_sync`].
    ///
    /// # Errors
    ///
    /// Returns the batch loader's error if any file fails; nothing from the
    /// batch is cached in that case.
    pub fn load_batch_sync(&self, paths: &[&Path]) -> Result<usize> {
        let results = load_yaml_batch_sync(paths)?;

        for (path_str, docs) in results {
            self.store.entries.insert(path_str, Arc::new(docs));
        }

        Ok(paths.len())
    }

    /// Concurrently load every path and cache each under its own path string
    /// in this scope. See [`load_batch_async`].
    ///
    /// # Errors
    ///
    /// Returns the batch loader's error if any file fails; nothing from the
    /// batch is cached in that case.
    pub async fn load_batch_async(&self, paths: &[&Path]) -> Result<usize> {
        let results = load_yaml_batch_async(paths).await?;

        for (path_str, docs) in results {
            self.store.entries.insert(path_str, Arc::new(docs));
        }

        Ok(paths.len())
    }

    /// Return the documents cached under `key` in this scope, counting a hit
    /// or miss on this scope. See [`get_cached`].
    pub fn get_cached(&self, key: &str) -> Option<Arc<Vec<Yaml>>> {
        match self.store.entries.get(key) {
            Some(entry) => {
                self.store.hits.fetch_add(1, Ordering::Relaxed);
                trace!(cache = "settings", key = %key, "cache hit");
                Some(entry)
            }
            None => {
                self.store.misses.fetch_add(1, Ordering::Relaxed);
                trace!(cache = "settings", key = %key, "cache miss");
                None
            }
        }
    }

    /// Return whether `key` is cached in this scope without touching the
    /// counters. See [`is_cached`].
    pub fn is_cached(&self, key: &str) -> bool {
        self.store.entries.contains_key(key)
    }

    /// Remove `key` from this scope, returning whether it was present.
    /// See [`invalidate`].
    pub fn invalidate(&self, key: &str) -> bool {
        self.store.entries.remove(key).is_some()
    }

    /// Evict every entry in this scope without resetting its counters.
    /// See [`clear_cache`].
    pub fn clear_cache(&self) {
        self.store.entries.clear();
    }

    /// Return the number of entries in this scope. See [`cache_size`].
    pub fn cache_size(&self) -> usize {
        self.store.entries.len()
    }

    /// Return every key cached in this scope. See [`cache_keys`].
    pub fn cache_keys(&self) -> Vec<String> {
        self.store.entries.iter().map(|(key, _)| key).collect()
    }
}

impl PartialEq for LogicalKeyCacheScope {
    /// Two handles are equal when they name the same store.
    fn eq(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.store, &other.store)
    }
}

impl Eq for LogicalKeyCacheScope {}

impl fmt::Debug for LogicalKeyCacheScope {
    // Report identity and occupancy only; cached documents can be large.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("LogicalKeyCacheScope")
            .field("is_default", &(*self == *DEFAULT_SCOPE))
            .field("size", &self.store.entries.len())
            .finish()
    }
}

/// Cache performance statistics.
///
/// Provides insight into cache effectiveness via hit/miss tracking.
/// Use `cache_stats()` to retrieve current statistics.
///
/// # Example
///
/// ```rust
/// use classic_shared_core::yaml::cache_stats;
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
/// Returns the current hit/miss counts and derived hit rate of the process
/// default scope; use [`LogicalKeyCacheScope::cache_stats`] for another scope.
///
/// # Example
///
/// ```rust
/// use classic_shared_core::yaml::cache_stats;
///
/// let stats = cache_stats();
/// println!("Hits: {}, Misses: {}", stats.hits, stats.misses);
/// println!("Hit rate: {:.1}%", stats.hit_rate * 100.0);
/// ```
pub fn cache_stats() -> CacheStats {
    DEFAULT_SCOPE.cache_stats()
}

/// Reset cache statistics.
///
/// Resets hit and miss counters to zero. Useful for testing or
/// starting fresh measurements.
///
/// # Example
///
/// ```rust
/// use classic_shared_core::yaml::{reset_cache_stats, cache_stats};
///
/// reset_cache_stats();
/// let stats = cache_stats();
/// assert_eq!(stats.hits, 0);
/// assert_eq!(stats.misses, 0);
/// ```
pub fn reset_cache_stats() {
    DEFAULT_SCOPE.reset_cache_stats();
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
/// use classic_shared_core::yaml::load_settings_sync;
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let docs = load_settings_sync("game_config", Path::new("config.yaml"))?;
/// # Ok(())
/// # }
/// ```
pub fn load_settings_sync(key: &str, path: &Path) -> Result<Arc<Vec<Yaml>>> {
    DEFAULT_SCOPE.load_settings_sync(key, path)
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
/// use classic_shared_core::yaml::load_settings_async;
/// use std::path::Path;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let docs = load_settings_async("game_config", Path::new("config.yaml")).await?;
/// # Ok(())
/// # }
/// ```
pub async fn load_settings_async(key: &str, path: &Path) -> Result<Arc<Vec<Yaml>>> {
    DEFAULT_SCOPE.load_settings_async(key, path).await
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
/// use classic_shared_core::yaml::load_batch_sync;
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let paths = vec![Path::new("config1.yaml"), Path::new("config2.yaml")];
/// let count = load_batch_sync(&paths)?;
/// # Ok(())
/// # }
/// ```
pub fn load_batch_sync(paths: &[&Path]) -> Result<usize> {
    DEFAULT_SCOPE.load_batch_sync(paths)
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
/// use classic_shared_core::yaml::load_batch_async;
/// use std::path::Path;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let paths = vec![Path::new("config1.yaml"), Path::new("config2.yaml")];
/// let count = load_batch_async(&paths).await?;
/// # Ok(())
/// # }
/// ```
pub async fn load_batch_async(paths: &[&Path]) -> Result<usize> {
    DEFAULT_SCOPE.load_batch_async(paths).await
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
/// use classic_shared_core::yaml::{get_cached, load_settings_sync};
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
    DEFAULT_SCOPE.get_cached(key)
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
/// use classic_shared_core::yaml::{is_cached, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// assert!(is_cached("game_config"));
/// # Ok(())
/// # }
/// ```
pub fn is_cached(key: &str) -> bool {
    DEFAULT_SCOPE.is_cached(key)
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
/// use classic_shared_core::yaml::{invalidate, load_settings_sync};
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
    DEFAULT_SCOPE.invalidate(key)
}

/// Clear all cached settings.
///
/// Removes all entries from the cache.
///
/// # Examples
///
/// ```rust
/// use classic_shared_core::yaml::clear_cache;
///
/// clear_cache();
/// ```
pub fn clear_cache() {
    DEFAULT_SCOPE.clear_cache();
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
/// use classic_shared_core::yaml::{cache_size, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// assert_eq!(cache_size(), 1);
/// # Ok(())
/// # }
/// ```
pub fn cache_size() -> usize {
    DEFAULT_SCOPE.cache_size()
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
/// use classic_shared_core::yaml::{cache_keys, load_settings_sync};
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
    DEFAULT_SCOPE.cache_keys()
}

#[cfg(test)]
#[path = "logical_key_cache_tests.rs"]
mod tests;
