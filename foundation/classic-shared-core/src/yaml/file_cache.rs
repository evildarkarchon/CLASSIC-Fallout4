//! Path/mtime-aware YAML-file cache and its scope handles.
//!
//! This cache backs [`YamlOperations::load_yaml_file`](super::YamlOperations::load_yaml_file).
//! It is keyed by file path, holds at most 128 parsed documents, and treats an
//! entry as fresh only while the file's modification time is no newer than the
//! cached one. Hits and misses are counted on every `load_yaml_file` call, and
//! clearing entries ([`clear_global_yaml_cache`]) stays separate from
//! resetting counters ([`reset_yaml_cache_stats`]).
//!
//! It is deliberately distinct from the logical-key settings cache in
//! `logical_key_cache`: the two have different keys, capacities, freshness,
//! and counter rules, and clearing one never touches the other.
//!
//! # Scopes
//!
//! Every store lives behind a [`YamlFileCacheScope`] handle. The unscoped free
//! functions and [`YamlOperations::new`](super::YamlOperations::new) use one
//! lazily created process default scope, which is what Rust, CXX, and Node
//! callers have always observed. A binding adapter that links several former
//! extension images into one library (the merged Python extension) creates
//! [`YamlFileCacheScope::new_isolated`] handles instead, so each facade keeps
//! its own entries and counters exactly as when it was a separate image.

use quick_cache::sync::Cache;
use serde::Serialize;
use std::fmt;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, LazyLock};
use std::time::SystemTime;
use yaml_rust2::Yaml;

/// Number of parsed documents one YAML-file cache scope retains.
const YAML_FILE_CACHE_CAPACITY: usize = 128;

/// One YAML-file cache store: its entries plus the hit/miss counters that
/// describe them. A scope handle owns exactly one of these.
pub(super) struct YamlFileCacheStore {
    /// Parsed documents keyed by the path they were loaded from.
    pub(super) entries: Cache<PathBuf, CachedYaml>,
    /// Cache hits since the last counter reset.
    pub(super) hits: AtomicU64,
    /// Cache misses (including cache-disabled reads) since the last reset.
    pub(super) misses: AtomicU64,
}

impl YamlFileCacheStore {
    fn new() -> Self {
        Self {
            entries: Cache::new(YAML_FILE_CACHE_CAPACITY),
            hits: AtomicU64::new(0),
            misses: AtomicU64::new(0),
        }
    }
}

/// Process default YAML-file cache scope.
///
/// NOTE: This is lazily initialized on first use to avoid deadlocks during module import.
/// The cache is thread-safe and uses `quick_cache` with a fixed 128-entry capacity.
static DEFAULT_SCOPE: LazyLock<YamlFileCacheScope> = LazyLock::new(|| YamlFileCacheScope {
    store: Arc::new(YamlFileCacheStore::new()),
});

/// Opaque handle to one path/mtime-aware YAML-file cache store.
///
/// Cloning a handle shares the same store; two handles compare equal exactly
/// when they name the same store. [`YamlFileCacheScope::default_scope`] is the
/// store used by the unscoped functions and
/// [`YamlOperations::new`](super::YamlOperations::new).
/// [`YamlFileCacheScope::new_isolated`] creates a fresh store with the same
/// capacity, freshness, counter, and clear rules that shares nothing with any
/// other scope.
///
/// # Example
///
/// ```rust
/// use classic_shared_core::yaml::{YamlFileCacheScope, YamlOperations};
///
/// let scope = YamlFileCacheScope::new_isolated();
/// let ops = YamlOperations::with_cache_scope(scope.clone());
/// assert_eq!(ops.cache_scope(), &scope);
/// assert_ne!(scope, YamlFileCacheScope::default_scope());
/// assert_eq!(scope.stats().size, 0);
/// ```
#[derive(Clone)]
pub struct YamlFileCacheScope {
    store: Arc<YamlFileCacheStore>,
}

impl YamlFileCacheScope {
    /// Return a handle to the process default scope.
    ///
    /// This is the store the unscoped [`yaml_cache_stats`],
    /// [`clear_global_yaml_cache`], and [`reset_yaml_cache_stats`] functions
    /// and every [`YamlOperations::new`](super::YamlOperations::new) object use.
    #[must_use]
    pub fn default_scope() -> Self {
        DEFAULT_SCOPE.clone()
    }

    /// Create a new, empty scope that shares no entries or counters with any
    /// other scope, including the default one.
    #[must_use]
    pub fn new_isolated() -> Self {
        Self {
            store: Arc::new(YamlFileCacheStore::new()),
        }
    }

    /// Return this scope's hit/miss counters, entry count, and capacity.
    #[must_use]
    pub fn stats(&self) -> YamlCacheStats {
        let hits = self.store.hits.load(Ordering::Relaxed);
        let misses = self.store.misses.load(Ordering::Relaxed);
        let total = hits + misses;

        YamlCacheStats {
            hits,
            misses,
            hit_rate: if total > 0 {
                hits as f64 / total as f64
            } else {
                0.0
            },
            size: self.store.entries.len(),
            capacity: usize::try_from(self.store.entries.capacity()).unwrap_or(usize::MAX),
        }
    }

    /// Evict every entry in this scope without resetting its counters.
    pub fn clear(&self) {
        self.store.entries.clear();
    }

    /// Reset this scope's hit and miss counters without evicting entries.
    pub fn reset_stats(&self) {
        self.store.hits.store(0, Ordering::Relaxed);
        self.store.misses.store(0, Ordering::Relaxed);
    }

    /// Borrow the store this handle names.
    pub(super) fn store(&self) -> &YamlFileCacheStore {
        &self.store
    }

    /// Total raw YAML text bytes retained by this scope's entries.
    pub(super) fn total_cached_bytes(&self) -> usize {
        self.store
            .entries
            .iter()
            .map(|(_, cached)| cached.raw_content.as_ref().map_or(0, String::len))
            .sum()
    }
}

impl PartialEq for YamlFileCacheScope {
    /// Two handles are equal when they name the same store.
    fn eq(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.store, &other.store)
    }
}

impl Eq for YamlFileCacheScope {}

impl fmt::Debug for YamlFileCacheScope {
    // Report identity and occupancy only; dumping cached documents would be
    // noisy and could leak file contents into logs.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("YamlFileCacheScope")
            .field("is_default", &(*self == *DEFAULT_SCOPE))
            .field("size", &self.store.entries.len())
            .finish()
    }
}

/// Cache performance statistics.
///
/// Provides insight into cache effectiveness via hit/miss tracking.
/// Use `yaml_cache_stats()` to retrieve current statistics.
///
/// # Example
///
/// ```rust
/// use classic_shared_core::yaml::yaml_cache_stats;
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

/// Get current cache statistics.
///
/// Returns the current hit/miss counts and derived hit rate of the process
/// default scope; use [`YamlFileCacheScope::stats`] for another scope.
///
/// # Example
///
/// ```rust
/// use classic_shared_core::yaml::yaml_cache_stats;
///
/// let stats = yaml_cache_stats();
/// println!("Hits: {}, Misses: {}", stats.hits, stats.misses);
/// println!("Hit rate: {:.1}%", stats.hit_rate * 100.0);
/// ```
pub fn yaml_cache_stats() -> YamlCacheStats {
    DEFAULT_SCOPE.stats()
}

/// Reset cache statistics.
///
/// Resets hit and miss counters to zero. Useful for testing or
/// starting fresh measurements. Acts on the process default scope only and
/// never evicts entries.
///
/// # Example
///
/// ```rust
/// use classic_shared_core::yaml::{reset_yaml_cache_stats, yaml_cache_stats};
///
/// reset_yaml_cache_stats();
/// let stats = yaml_cache_stats();
/// assert_eq!(stats.hits, 0);
/// assert_eq!(stats.misses, 0);
/// ```
pub fn reset_yaml_cache_stats() {
    DEFAULT_SCOPE.reset_stats();
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
/// testing to ensure clean state between test runs. It evicts the process
/// default scope's entries only, leaves isolated scopes untouched, and does
/// not reset hit/miss counters.
///
/// # Example
/// ```rust,no_run
/// use classic_shared_core::yaml::clear_global_yaml_cache;
///
/// // Clear all cached YAML files
/// clear_global_yaml_cache();
/// ```
pub fn clear_global_yaml_cache() {
    DEFAULT_SCOPE.clear();
}

#[cfg(test)]
#[path = "file_cache_tests.rs"]
mod tests;
