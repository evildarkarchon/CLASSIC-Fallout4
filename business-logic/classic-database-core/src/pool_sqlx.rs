//! Database connection pool with sqlx (Pure Rust Async)
//!
//! High-performance TRUE ASYNC database operations with:
//! - Built-in connection pooling with sqlx
//! - WAL mode for concurrent reads
//! - TTL-based smart caching with optimized key generation
//! - Batch query optimization using UNION ALL pattern
//! - Parallel database queries across multiple database files
//! - FormID-specific operations
//! - Multiple database file support (Main and Local)
//! - Dynamic table name support for different games

use dashmap::DashMap;
use futures::future::join_all;
use log::{debug, error, info, warn};
use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions, SqliteSynchronous};
use sqlx::{Row, SqlitePool};
use std::collections::{HashMap, HashSet};
use std::hash::{Hash, Hasher};
use std::path::PathBuf;
use std::str::FromStr;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, RwLock};
use std::time::{Duration, Instant};
use thiserror::Error;

/// Default cache TTL for single log scanning (5 minutes).
/// Use this when scanning individual logs or when memory is constrained.
pub const DEFAULT_CACHE_TTL_SECS: u64 = 300;

/// Extended cache TTL for batch log scanning (30 minutes).
/// Use this when scanning multiple logs in sequence to maximize cache hits
/// across logs that reference the same FormIDs.
pub const BATCH_CACHE_TTL_SECS: u64 = 1800;

/// Maximum recommended cache TTL (60 minutes).
/// Useful for very large batch operations with 50+ logs.
pub const MAX_CACHE_TTL_SECS: u64 = 3600;

/// Default maximum number of entries allowed in query cache.
pub const DEFAULT_QUERY_CACHE_CAPACITY: usize = 20_000;

/// Minimum allowed query cache capacity.
pub const MIN_QUERY_CACHE_CAPACITY: usize = 1;

/// Maximum allowed query cache capacity.
pub const MAX_QUERY_CACHE_CAPACITY: usize = 1_000_000;

/// Default number of lookup operations before proactive cleanup is considered.
pub const DEFAULT_CACHE_CLEANUP_OP_THRESHOLD: u64 = 2048;

/// Minimum allowed cleanup operation threshold.
pub const MIN_CACHE_CLEANUP_OP_THRESHOLD: u64 = 1;

/// Maximum allowed cleanup operation threshold.
pub const MAX_CACHE_CLEANUP_OP_THRESHOLD: u64 = 100_000;

/// Default minimum cleanup interval in seconds.
pub const DEFAULT_CACHE_CLEANUP_INTERVAL_SECS: u64 = 30;

/// Minimum allowed proactive cleanup interval in seconds.
pub const MIN_CACHE_CLEANUP_INTERVAL_SECS: u64 = 1;

/// Maximum allowed proactive cleanup interval in seconds.
pub const MAX_CACHE_CLEANUP_INTERVAL_SECS: u64 = 300;

const STABLE_BATCH_BUCKETS: [usize; 8] = [8, 16, 32, 64, 128, 256, 512, 1024];
const MAX_STABLE_BATCH_BUCKET: usize = 1024;
const BULK_EVICTION_MIN_CAPACITY: usize = 4_096;
const BULK_EVICTION_DIVISOR: usize = 16;
const BULK_EVICTION_MIN_BATCH: usize = 256;
const BULK_EVICTION_MAX_BATCH: usize = 4_096;

/// Represents various errors that can occur when working with a database.
#[derive(Debug, Error)]
pub enum DatabaseError {
    /// Failed to open or initialize a database connection
    #[error("Failed to open database: {0}")]
    OpenError(String),

    /// Query execution encountered an error
    #[error("Query execution failed: {0}")]
    QueryError(String),

    /// Database file does not exist at the specified path
    #[error("Database file not found: {0}")]
    NotFound(String),

    /// I/O error occurred during file operations
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    /// SQLx library error occurred
    #[error("Sqlx error: {0}")]
    SqlxError(#[from] sqlx::Error),
}

/// Cache entry with TTL support
#[derive(Clone, Debug)]
pub struct CacheEntry {
    /// Cached value (typically a database query result)
    pub value: String,
    /// Timestamp when this cache entry was created
    pub created_at: Instant,
    /// Expiration timestamp for this cache entry
    pub expires_at: Instant,
}

impl CacheEntry {
    /// Create a new cache entry with the given value and time-to-live duration
    pub fn new(value: String, ttl: Duration) -> Self {
        let now = Instant::now();
        Self {
            value,
            created_at: now,
            expires_at: now + ttl,
        }
    }

    /// Check if this cache entry has expired
    pub fn is_expired(&self) -> bool {
        Instant::now() > self.expires_at
    }
}

/// Optimized cache key using pre-computed hash for faster lookups.
///
/// Instead of allocating a new String for each cache key, we use a tuple-based
/// key that can be hashed efficiently. This reduces allocations in hot paths.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CacheKey {
    /// Pre-computed hash of (game_table, formid, plugin)
    hash: u64,
    /// Game table name for collision resolution
    game_table: String,
    /// FormID for collision resolution
    formid: String,
    /// Plugin name for collision resolution
    plugin: String,
}

impl CacheKey {
    fn build_hash(game_table: &str, formid: &str, normalized_plugin: &str) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        let mut hasher = DefaultHasher::new();
        game_table.hash(&mut hasher);
        formid.hash(&mut hasher);
        normalized_plugin.hash(&mut hasher);
        hasher.finish()
    }

    /// Normalize plugin names for case-insensitive cache matching.
    pub fn normalize_plugin(plugin: &str) -> String {
        plugin.to_lowercase()
    }

    /// Create a key when the plugin component is already normalized.
    pub fn from_normalized_plugin(game_table: &str, formid: &str, normalized_plugin: &str) -> Self {
        Self {
            hash: Self::build_hash(game_table, formid, normalized_plugin),
            game_table: game_table.to_string(),
            formid: formid.to_string(),
            plugin: normalized_plugin.to_string(),
        }
    }

    /// Create a new cache key from components
    pub fn new(game_table: &str, formid: &str, plugin: &str) -> Self {
        let normalized_plugin = Self::normalize_plugin(plugin);
        Self::from_normalized_plugin(game_table, formid, &normalized_plugin)
    }

    fn tie_break_key(&self) -> (&str, &str, &str) {
        (&self.game_table, &self.formid, &self.plugin)
    }
}

impl Hash for CacheKey {
    fn hash<H: Hasher>(&self, state: &mut H) {
        // Use pre-computed hash for efficiency
        self.hash.hash(state);
    }
}

/// Statistics for monitoring pool performance
#[derive(Default, Debug, Clone)]
pub struct PoolStatistics {
    /// Total number of queries executed
    pub total_queries: u64,
    /// Number of queries served from cache
    pub cache_hits: u64,
    /// Number of queries that required database access
    pub cache_misses: u64,
    /// Total number of connections created
    pub total_connections: u64,
    /// Number of currently active connections
    pub active_connections: u64,
    /// Number of cache entries evicted to enforce capacity
    pub cache_evictions: u64,
    /// Number of proactive cleanup runs executed
    pub cleanup_runs: u64,
    /// Total number of expired entries removed by proactive cleanup
    pub cleanup_removed: u64,
    /// Total elapsed nanoseconds spent running proactive cleanup sweeps
    pub cleanup_elapsed_total_ns: u64,
    /// Maximum elapsed nanoseconds observed for a single proactive cleanup run
    pub cleanup_elapsed_max_ns: u64,
    /// Total elapsed nanoseconds spent in eviction maintenance
    pub eviction_elapsed_total_ns: u64,
    /// Maximum elapsed nanoseconds observed for a single eviction maintenance pass
    pub eviction_elapsed_max_ns: u64,
    /// Configured global connection budget (set via constructor/set_max_connections)
    pub configured_connection_budget: u64,
    /// Effective global budget applied to active pools after low-budget clamp
    pub effective_connection_budget: u64,
    /// Number of active database pools participating in the allocation
    pub active_pool_count: u64,
    /// Smallest per-pool allocation in the current plan
    pub min_pool_allocation: u64,
    /// Largest per-pool allocation in the current plan
    pub max_pool_allocation: u64,
    /// Difference between largest and smallest pool allocations
    pub allocation_spread: u64,
    /// Number of stable-shape bucket selections in batch path
    pub stable_shape_selections: u64,
    /// Total number of padded pair slots used to satisfy stable shapes
    pub stable_shape_padding_pairs: u64,
    /// Number of times the 8-slot bucket was selected
    pub stable_shape_bucket_8: u64,
    /// Number of times the 16-slot bucket was selected
    pub stable_shape_bucket_16: u64,
    /// Number of times the 32-slot bucket was selected
    pub stable_shape_bucket_32: u64,
    /// Number of times the 64-slot bucket was selected
    pub stable_shape_bucket_64: u64,
    /// Number of times the 128-slot bucket was selected
    pub stable_shape_bucket_128: u64,
    /// Number of times the 256-slot bucket was selected
    pub stable_shape_bucket_256: u64,
    /// Number of times the 512-slot bucket was selected
    pub stable_shape_bucket_512: u64,
    /// Number of times the 1024-slot bucket was selected
    pub stable_shape_bucket_1024: u64,
}

#[derive(Debug, Clone)]
struct ConnectionAllocationPlan {
    configured_budget: usize,
    effective_budget: usize,
    allocations: Vec<(PathBuf, usize)>,
}

struct ConnectionAllocator;

impl ConnectionAllocator {
    fn calculate_max_connections() -> usize {
        let cpus = num_cpus::get();
        let optimal = cpus * 4; // 4 connections per CPU core for async I/O
        optimal.clamp(8, 64) // Higher bounds for async operations
    }

    fn derive_allocation(
        configured_budget: usize,
        db_paths: &[PathBuf],
    ) -> ConnectionAllocationPlan {
        if db_paths.is_empty() {
            return ConnectionAllocationPlan {
                configured_budget,
                effective_budget: 0,
                allocations: Vec::new(),
            };
        }

        let mut ordered_paths = db_paths.to_vec();
        ordered_paths.sort();
        ordered_paths.dedup();

        let active_count = ordered_paths.len();
        let effective_budget = configured_budget.max(active_count);
        let base = effective_budget / active_count;
        let remainder = effective_budget % active_count;

        let allocations = ordered_paths
            .into_iter()
            .enumerate()
            .map(|(idx, path)| {
                let allocation = base + usize::from(idx < remainder);
                (path, allocation)
            })
            .collect();

        ConnectionAllocationPlan {
            configured_budget,
            effective_budget,
            allocations,
        }
    }
}

#[derive(Clone)]
struct PoolStats {
    total_queries: Arc<AtomicU64>,
    cache_hits: Arc<AtomicU64>,
    cache_misses: Arc<AtomicU64>,
    total_connections: Arc<AtomicU64>,
    active_connections: Arc<AtomicU64>,
    cache_evictions: Arc<AtomicU64>,
    cleanup_runs: Arc<AtomicU64>,
    cleanup_removed: Arc<AtomicU64>,
    cleanup_elapsed_total_ns: Arc<AtomicU64>,
    cleanup_elapsed_max_ns: Arc<AtomicU64>,
    eviction_elapsed_total_ns: Arc<AtomicU64>,
    eviction_elapsed_max_ns: Arc<AtomicU64>,
    stable_shape_selections: Arc<AtomicU64>,
    stable_shape_padding_pairs: Arc<AtomicU64>,
    stable_shape_bucket_8: Arc<AtomicU64>,
    stable_shape_bucket_16: Arc<AtomicU64>,
    stable_shape_bucket_32: Arc<AtomicU64>,
    stable_shape_bucket_64: Arc<AtomicU64>,
    stable_shape_bucket_128: Arc<AtomicU64>,
    stable_shape_bucket_256: Arc<AtomicU64>,
    stable_shape_bucket_512: Arc<AtomicU64>,
    stable_shape_bucket_1024: Arc<AtomicU64>,
}

impl PoolStats {
    fn new() -> Self {
        Self {
            total_queries: Arc::new(AtomicU64::new(0)),
            cache_hits: Arc::new(AtomicU64::new(0)),
            cache_misses: Arc::new(AtomicU64::new(0)),
            total_connections: Arc::new(AtomicU64::new(0)),
            active_connections: Arc::new(AtomicU64::new(0)),
            cache_evictions: Arc::new(AtomicU64::new(0)),
            cleanup_runs: Arc::new(AtomicU64::new(0)),
            cleanup_removed: Arc::new(AtomicU64::new(0)),
            cleanup_elapsed_total_ns: Arc::new(AtomicU64::new(0)),
            cleanup_elapsed_max_ns: Arc::new(AtomicU64::new(0)),
            eviction_elapsed_total_ns: Arc::new(AtomicU64::new(0)),
            eviction_elapsed_max_ns: Arc::new(AtomicU64::new(0)),
            stable_shape_selections: Arc::new(AtomicU64::new(0)),
            stable_shape_padding_pairs: Arc::new(AtomicU64::new(0)),
            stable_shape_bucket_8: Arc::new(AtomicU64::new(0)),
            stable_shape_bucket_16: Arc::new(AtomicU64::new(0)),
            stable_shape_bucket_32: Arc::new(AtomicU64::new(0)),
            stable_shape_bucket_64: Arc::new(AtomicU64::new(0)),
            stable_shape_bucket_128: Arc::new(AtomicU64::new(0)),
            stable_shape_bucket_256: Arc::new(AtomicU64::new(0)),
            stable_shape_bucket_512: Arc::new(AtomicU64::new(0)),
            stable_shape_bucket_1024: Arc::new(AtomicU64::new(0)),
        }
    }

    fn increment_total_queries(&self, count: u64) {
        self.total_queries.fetch_add(count, Ordering::Relaxed);
    }

    fn increment_cache_hits(&self, count: u64) {
        self.cache_hits.fetch_add(count, Ordering::Relaxed);
    }

    fn increment_cache_misses(&self, count: u64) {
        self.cache_misses.fetch_add(count, Ordering::Relaxed);
    }

    fn record_connection_created(&self) {
        self.total_connections.fetch_add(1, Ordering::Relaxed);
    }

    fn set_active_connections(&self, count: u64) {
        self.active_connections.store(count, Ordering::Relaxed);
    }

    fn active_connections(&self) -> u64 {
        self.active_connections.load(Ordering::Relaxed)
    }

    fn total_queries(&self) -> u64 {
        self.total_queries.load(Ordering::Relaxed)
    }

    fn record_elapsed_ns(total: &AtomicU64, max: &AtomicU64, elapsed: Duration) {
        let elapsed_ns = elapsed.as_nanos().min(u64::MAX as u128) as u64;
        total.fetch_add(elapsed_ns, Ordering::Relaxed);
        max.fetch_max(elapsed_ns, Ordering::Relaxed);
    }

    fn record_eviction_pass(&self, evicted: u64, elapsed: Duration) {
        if evicted > 0 {
            self.cache_evictions.fetch_add(evicted, Ordering::Relaxed);
        }
        Self::record_elapsed_ns(
            &self.eviction_elapsed_total_ns,
            &self.eviction_elapsed_max_ns,
            elapsed,
        );
    }

    fn record_cleanup_run(&self, removed: u64, elapsed: Duration) {
        Self::record_elapsed_ns(
            &self.cleanup_elapsed_total_ns,
            &self.cleanup_elapsed_max_ns,
            elapsed,
        );
        self.cleanup_runs.fetch_add(1, Ordering::Relaxed);
        self.cleanup_removed.fetch_add(removed, Ordering::Relaxed);
    }

    fn record_stable_shape_selection(&self, bucket_len: usize, padded_pairs: usize) {
        self.stable_shape_selections.fetch_add(1, Ordering::Relaxed);
        if padded_pairs > 0 {
            self.stable_shape_padding_pairs
                .fetch_add(padded_pairs as u64, Ordering::Relaxed);
        }

        let bucket_counter = match bucket_len {
            8 => &self.stable_shape_bucket_8,
            16 => &self.stable_shape_bucket_16,
            32 => &self.stable_shape_bucket_32,
            64 => &self.stable_shape_bucket_64,
            128 => &self.stable_shape_bucket_128,
            256 => &self.stable_shape_bucket_256,
            512 => &self.stable_shape_bucket_512,
            1024 => &self.stable_shape_bucket_1024,
            _ => return,
        };

        bucket_counter.fetch_add(1, Ordering::Relaxed);
    }

    fn maintenance_snapshot(&self) -> (u64, u64, u64, u64, u64) {
        (
            self.cleanup_runs.load(Ordering::Relaxed),
            self.cleanup_elapsed_total_ns.load(Ordering::Relaxed),
            self.cleanup_elapsed_max_ns.load(Ordering::Relaxed),
            self.eviction_elapsed_total_ns.load(Ordering::Relaxed),
            self.eviction_elapsed_max_ns.load(Ordering::Relaxed),
        )
    }

    fn snapshot(
        &self,
        configured_budget: u64,
        allocations_snapshot: &HashMap<PathBuf, usize>,
    ) -> PoolStatistics {
        let active_pool_count = allocations_snapshot.len() as u64;
        let effective_connection_budget: u64 = allocations_snapshot
            .values()
            .copied()
            .map(|value| value as u64)
            .sum();
        let min_pool_allocation = allocations_snapshot
            .values()
            .copied()
            .min()
            .map_or(0_u64, |value| value as u64);
        let max_pool_allocation = allocations_snapshot
            .values()
            .copied()
            .max()
            .map_or(0_u64, |value| value as u64);
        let allocation_spread = max_pool_allocation.saturating_sub(min_pool_allocation);

        PoolStatistics {
            total_queries: self.total_queries.load(Ordering::Relaxed),
            cache_hits: self.cache_hits.load(Ordering::Relaxed),
            cache_misses: self.cache_misses.load(Ordering::Relaxed),
            total_connections: self.total_connections.load(Ordering::Relaxed),
            active_connections: self.active_connections.load(Ordering::Relaxed),
            cache_evictions: self.cache_evictions.load(Ordering::Relaxed),
            cleanup_runs: self.cleanup_runs.load(Ordering::Relaxed),
            cleanup_removed: self.cleanup_removed.load(Ordering::Relaxed),
            cleanup_elapsed_total_ns: self.cleanup_elapsed_total_ns.load(Ordering::Relaxed),
            cleanup_elapsed_max_ns: self.cleanup_elapsed_max_ns.load(Ordering::Relaxed),
            eviction_elapsed_total_ns: self.eviction_elapsed_total_ns.load(Ordering::Relaxed),
            eviction_elapsed_max_ns: self.eviction_elapsed_max_ns.load(Ordering::Relaxed),
            configured_connection_budget: configured_budget,
            effective_connection_budget,
            active_pool_count,
            min_pool_allocation,
            max_pool_allocation,
            allocation_spread,
            stable_shape_selections: self.stable_shape_selections.load(Ordering::Relaxed),
            stable_shape_padding_pairs: self.stable_shape_padding_pairs.load(Ordering::Relaxed),
            stable_shape_bucket_8: self.stable_shape_bucket_8.load(Ordering::Relaxed),
            stable_shape_bucket_16: self.stable_shape_bucket_16.load(Ordering::Relaxed),
            stable_shape_bucket_32: self.stable_shape_bucket_32.load(Ordering::Relaxed),
            stable_shape_bucket_64: self.stable_shape_bucket_64.load(Ordering::Relaxed),
            stable_shape_bucket_128: self.stable_shape_bucket_128.load(Ordering::Relaxed),
            stable_shape_bucket_256: self.stable_shape_bucket_256.load(Ordering::Relaxed),
            stable_shape_bucket_512: self.stable_shape_bucket_512.load(Ordering::Relaxed),
            stable_shape_bucket_1024: self.stable_shape_bucket_1024.load(Ordering::Relaxed),
        }
    }
}

#[derive(Clone)]
struct QueryCache {
    entries: Arc<DashMap<CacheKey, CacheEntry>>,
    templates: Arc<DashMap<(String, usize, bool), String>>,
    capacity: Arc<AtomicUsize>,
    cleanup_threshold: Arc<AtomicU64>,
    cleanup_interval: Arc<RwLock<Duration>>,
    ops_since_cleanup: Arc<AtomicU64>,
    last_cleanup_at: Arc<RwLock<Instant>>,
    ttl: Arc<RwLock<Duration>>,
}

impl QueryCache {
    fn new(cache_ttl: Duration) -> Self {
        Self {
            entries: Arc::new(DashMap::new()),
            templates: Arc::new(DashMap::new()),
            capacity: Arc::new(AtomicUsize::new(DEFAULT_QUERY_CACHE_CAPACITY)),
            cleanup_threshold: Arc::new(AtomicU64::new(DEFAULT_CACHE_CLEANUP_OP_THRESHOLD)),
            cleanup_interval: Arc::new(RwLock::new(Duration::from_secs(
                DEFAULT_CACHE_CLEANUP_INTERVAL_SECS,
            ))),
            ops_since_cleanup: Arc::new(AtomicU64::new(0)),
            last_cleanup_at: Arc::new(RwLock::new(Instant::now())),
            ttl: Arc::new(RwLock::new(cache_ttl)),
        }
    }

    fn clamp_capacity(capacity: usize) -> usize {
        capacity.clamp(MIN_QUERY_CACHE_CAPACITY, MAX_QUERY_CACHE_CAPACITY)
    }

    fn clamp_cleanup_threshold(threshold: u64) -> u64 {
        threshold.clamp(
            MIN_CACHE_CLEANUP_OP_THRESHOLD,
            MAX_CACHE_CLEANUP_OP_THRESHOLD,
        )
    }

    fn clamp_cleanup_interval(interval: Duration) -> Duration {
        interval.clamp(
            Duration::from_secs(MIN_CACHE_CLEANUP_INTERVAL_SECS),
            Duration::from_secs(MAX_CACHE_CLEANUP_INTERVAL_SECS),
        )
    }

    fn len(&self) -> usize {
        self.entries.len()
    }

    fn clear_entries(&self) {
        self.entries.clear();
    }

    fn get_entry(&self, cache_key: &CacheKey) -> Option<CacheEntry> {
        self.entries.get(cache_key).map(|entry| entry.clone())
    }

    fn remove_entry(&self, cache_key: &CacheKey) {
        self.entries.remove(cache_key);
    }

    #[cfg(test)]
    fn insert_entry(&self, cache_key: CacheKey, entry: CacheEntry) {
        self.entries.insert(cache_key, entry);
    }

    #[cfg(test)]
    fn contains_key(&self, cache_key: &CacheKey) -> bool {
        self.entries.contains_key(cache_key)
    }

    #[cfg(test)]
    fn template_count(&self) -> usize {
        self.templates.len()
    }

    fn current_ttl(&self) -> Duration {
        *self.ttl.read().unwrap_or_else(|poisoned| {
            warn!("cache_ttl lock was poisoned - recovering");
            poisoned.into_inner()
        })
    }

    fn set_ttl(&self, ttl: Duration) {
        if let Ok(mut t) = self.ttl.write() {
            *t = ttl;
        }
    }

    fn capacity(&self) -> usize {
        self.capacity.load(Ordering::Relaxed)
    }

    fn set_capacity(&self, capacity: usize, stats: &PoolStats) {
        self.capacity
            .store(Self::clamp_capacity(capacity), Ordering::Relaxed);
        self.evict_to_capacity(stats);
    }

    fn cleanup_threshold(&self) -> u64 {
        self.cleanup_threshold.load(Ordering::Relaxed)
    }

    fn set_cleanup_threshold(&self, threshold: u64) {
        self.cleanup_threshold
            .store(Self::clamp_cleanup_threshold(threshold), Ordering::Relaxed);
    }

    fn cleanup_interval(&self) -> Duration {
        *self.cleanup_interval.read().unwrap_or_else(|poisoned| {
            warn!("cache_cleanup_interval lock was poisoned - recovering");
            poisoned.into_inner()
        })
    }

    fn set_cleanup_interval(&self, interval: Duration) {
        if let Ok(mut i) = self.cleanup_interval.write() {
            *i = Self::clamp_cleanup_interval(interval);
        }
    }

    fn preferred_eviction_target(capacity: usize) -> usize {
        if capacity < BULK_EVICTION_MIN_CAPACITY {
            return capacity;
        }

        let bulk_window = (capacity / BULK_EVICTION_DIVISOR)
            .clamp(BULK_EVICTION_MIN_BATCH, BULK_EVICTION_MAX_BATCH);
        capacity.saturating_sub(bulk_window)
    }

    fn insert_with_eviction(
        &self,
        cache_key: CacheKey,
        value: String,
        cache_ttl: Duration,
        stats: &PoolStats,
    ) {
        self.entries
            .insert(cache_key, CacheEntry::new(value, cache_ttl));

        let capacity = self.capacity.load(Ordering::Relaxed);
        if self.entries.len() <= capacity {
            return;
        }

        self.evict_to_target(Self::preferred_eviction_target(capacity), stats);
    }

    fn insert_many_with_eviction(
        &self,
        entries: Vec<(CacheKey, String)>,
        cache_ttl: Duration,
        stats: &PoolStats,
    ) {
        if entries.is_empty() {
            return;
        }

        for (cache_key, value) in entries {
            self.entries
                .insert(cache_key, CacheEntry::new(value, cache_ttl));
        }

        let capacity = self.capacity.load(Ordering::Relaxed);
        if self.entries.len() <= capacity {
            return;
        }

        self.evict_to_target(Self::preferred_eviction_target(capacity), stats);
    }

    fn evict_to_capacity(&self, stats: &PoolStats) {
        let capacity = self.capacity.load(Ordering::Relaxed);
        self.evict_to_target(capacity, stats);
    }

    fn evict_to_target(&self, target_size: usize, stats: &PoolStats) {
        if self.entries.len() <= target_size {
            return;
        }

        let maintenance_start = Instant::now();
        let mut total_evicted = 0_u64;

        // Policy step 1: purge expired entries first in one pass.
        let before_expired_clear = self.entries.len();
        self.entries.retain(|_, value| !value.is_expired());
        let after_expired_clear = self.entries.len();
        total_evicted = total_evicted
            .saturating_add(before_expired_clear.saturating_sub(after_expired_clear) as u64);

        // Policy step 2: if still over target, evict oldest entries in bulk.
        while self.entries.len() > target_size {
            let overflow_count = self.entries.len().saturating_sub(target_size);
            if overflow_count == 0 {
                break;
            }

            // Tie-break by cache key for deterministic behavior.
            let mut eviction_candidates: Vec<(Instant, CacheKey)> = self
                .entries
                .iter()
                .map(|entry| (entry.value().created_at, entry.key().clone()))
                .collect();

            if eviction_candidates.is_empty() {
                break;
            }

            eviction_candidates.sort_unstable_by(|(left_at, left_key), (right_at, right_key)| {
                left_at
                    .cmp(right_at)
                    .then_with(|| left_key.tie_break_key().cmp(&right_key.tie_break_key()))
            });

            let mut removed_in_pass = 0_u64;
            for (_, key) in eviction_candidates.into_iter().take(overflow_count) {
                if self.entries.remove(&key).is_some() {
                    removed_in_pass += 1;
                }
            }

            if removed_in_pass == 0 {
                break;
            }

            total_evicted = total_evicted.saturating_add(removed_in_pass);
        }

        stats.record_eviction_pass(total_evicted, maintenance_start.elapsed());
    }

    fn maybe_run_proactive_cleanup(&self, operation_count: u64, stats: &PoolStats) {
        let updated_ops = self
            .ops_since_cleanup
            .fetch_add(operation_count, Ordering::Relaxed)
            .saturating_add(operation_count);

        let threshold = self.cleanup_threshold.load(Ordering::Relaxed);
        if updated_ops < threshold {
            return;
        }

        let interval = *self.cleanup_interval.read().unwrap_or_else(|poisoned| {
            warn!("cache_cleanup_interval lock was poisoned - recovering");
            poisoned.into_inner()
        });

        let elapsed_ok = {
            let last_cleanup = self.last_cleanup_at.read().unwrap_or_else(|poisoned| {
                warn!("last_cleanup_at lock was poisoned - recovering");
                poisoned.into_inner()
            });
            last_cleanup.elapsed() >= interval
        };

        if !elapsed_ok {
            return;
        }

        let cleanup_start = Instant::now();
        let removed = self.clear(true) as u64;
        stats.record_cleanup_run(removed, cleanup_start.elapsed());
        self.ops_since_cleanup.store(0, Ordering::Relaxed);

        if let Ok(mut last_cleanup) = self.last_cleanup_at.write() {
            *last_cleanup = Instant::now();
        }
    }

    fn clear(&self, expired_only: bool) -> usize {
        let initial_size = self.entries.len();
        if expired_only {
            self.entries.retain(|_, v| !v.is_expired());
        } else {
            self.entries.clear();
        }
        initial_size - self.entries.len()
    }

    fn get_or_build_template(
        &self,
        game_table: &str,
        bucket_len: usize,
        case_insensitive: bool,
    ) -> String {
        let template_key = (game_table.to_string(), bucket_len, case_insensitive);

        if let Some(existing) = self.templates.get(&template_key) {
            return existing.clone();
        }

        let template =
            DatabasePool::build_union_all_query(game_table, bucket_len, case_insensitive);
        self.templates.insert(template_key, template.clone());
        template
    }
}

#[derive(Clone)]
struct PoolRegistry {
    pools: Arc<DashMap<PathBuf, SqlitePool>>,
    max_connections: Arc<RwLock<Option<usize>>>,
    allocations: Arc<RwLock<HashMap<PathBuf, usize>>>,
    db_paths: Arc<RwLock<Vec<PathBuf>>>,
}

impl PoolRegistry {
    fn new(max_connections: usize) -> Self {
        Self {
            pools: Arc::new(DashMap::new()),
            max_connections: Arc::new(RwLock::new(Some(max_connections))),
            allocations: Arc::new(RwLock::new(HashMap::new())),
            db_paths: Arc::new(RwLock::new(Vec::new())),
        }
    }

    fn configured_connection_budget(&self) -> usize {
        self.max_connections
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("max_connections lock was poisoned - recovering");
                poisoned.into_inner()
            })
            .unwrap_or_else(ConnectionAllocator::calculate_max_connections)
    }

    fn get_max_connections(&self) -> Option<usize> {
        *self.max_connections.read().unwrap_or_else(|poisoned| {
            warn!("max_connections lock was poisoned - recovering");
            poisoned.into_inner()
        })
    }

    fn set_max_connections(&self, max_connections: usize) {
        if let Ok(mut m) = self.max_connections.write() {
            *m = Some(max_connections);
        }
    }

    fn tracked_paths(&self) -> Vec<PathBuf> {
        self.db_paths
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("db_paths lock was poisoned - recovering");
                poisoned.into_inner()
            })
            .clone()
    }

    fn allocations_snapshot(&self) -> HashMap<PathBuf, usize> {
        self.allocations
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("pool_allocations lock was poisoned - recovering");
                poisoned.into_inner()
            })
            .clone()
    }

    fn pool_snapshots(&self) -> Vec<(PathBuf, SqlitePool)> {
        self.pools
            .iter()
            .map(|entry| (entry.key().clone(), entry.value().clone()))
            .collect()
    }

    fn len(&self) -> usize {
        self.pools.len()
    }

    fn is_available(&self) -> bool {
        !self.pools.is_empty()
    }

    #[cfg(test)]
    fn pool_arc_strong_count(&self) -> usize {
        Arc::strong_count(&self.pools)
    }

    #[cfg(test)]
    fn shares_pool_storage_with(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.pools, &other.pools)
    }

    fn is_last_handle_with_open_pools(&self) -> bool {
        Arc::strong_count(&self.pools) == 1 && !self.pools.is_empty()
    }

    async fn close_active_pools(&self, stats: &PoolStats) {
        let existing_pools = self.pool_snapshots();

        for (db_path, pool) in existing_pools {
            pool.close().await;
            debug!("Closed connection pool for {:?}", db_path);
        }

        self.pools.clear();
        stats.set_active_connections(0);
    }

    fn clear_tracking(&self) {
        if let Ok(mut paths) = self.db_paths.write() {
            paths.clear();
        }
        if let Ok(mut allocations) = self.allocations.write() {
            allocations.clear();
        }
    }

    fn set_tracking(&self, paths: Vec<PathBuf>, allocations: HashMap<PathBuf, usize>) {
        if let Ok(mut tracked_paths) = self.db_paths.write() {
            *tracked_paths = paths;
        }
        if let Ok(mut tracked_allocations) = self.allocations.write() {
            *tracked_allocations = allocations;
        }
    }

    async fn rebuild_allocated_pools(
        &self,
        db_paths: Vec<PathBuf>,
        query_cache: &QueryCache,
        stats: &PoolStats,
    ) -> Result<(), DatabaseError> {
        let configured_budget = self.configured_connection_budget();
        let plan = ConnectionAllocator::derive_allocation(configured_budget, &db_paths);

        info!(
            "Applying global connection budget: configured={}, effective={}, active_pools={}",
            plan.configured_budget,
            plan.effective_budget,
            plan.allocations.len()
        );

        self.close_active_pools(stats).await;
        query_cache.clear_entries();

        if plan.allocations.is_empty() {
            self.clear_tracking();
            return Ok(());
        }

        let mut applied_paths = Vec::with_capacity(plan.allocations.len());
        let mut applied_allocations = HashMap::with_capacity(plan.allocations.len());

        for (path, allocation) in &plan.allocations {
            let opts = SqliteConnectOptions::from_str(&format!("sqlite://{}", path.display()))
                .map_err(|e| DatabaseError::OpenError(format!("{:?}: {}", path, e)))?
                .synchronous(SqliteSynchronous::Normal)
                .read_only(true)
                .pragma("cache_size", "10000")
                .pragma("temp_store", "MEMORY")
                .pragma("mmap_size", "30000000");

            let pool = SqlitePoolOptions::new()
                .max_connections(*allocation as u32)
                .min_connections(1)
                .acquire_timeout(Duration::from_secs(30))
                .connect_with(opts)
                .await
                .map_err(|e| DatabaseError::OpenError(format!("{:?}: {}", path, e)))?;

            self.pools.insert(path.clone(), pool);
            applied_paths.push(path.clone());
            applied_allocations.insert(path.clone(), *allocation);

            info!(
                "Created sqlx pool for {:?} with allocation {} (global budget mode)",
                path, allocation
            );
            stats.record_connection_created();
        }

        stats.set_active_connections(applied_paths.len() as u64);
        self.set_tracking(applied_paths, applied_allocations);

        Ok(())
    }
}

#[derive(Clone)]
struct ActiveGameTable {
    name: Arc<RwLock<String>>,
}

impl ActiveGameTable {
    fn new(name: String) -> Self {
        Self {
            name: Arc::new(RwLock::new(name)),
        }
    }

    fn set(&self, table: &str) {
        if let Ok(mut t) = self.name.write() {
            *t = table.to_string();
        }
    }

    fn get(&self) -> String {
        self.name
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("game_table lock was poisoned - recovering");
                poisoned.into_inner()
            })
            .clone()
    }

    fn resolve(&self, table: Option<&str>) -> String {
        table.map_or_else(|| self.get(), str::to_string)
    }
}

/// Database pool with sqlx - true async support
///
/// Provides high-performance asynchronous database access with connection pooling,
/// query caching, and FormID lookup optimization.
#[derive(Clone)]
pub struct DatabasePool {
    /// Connection pools, allocation policy, and tracked database paths.
    registry: PoolRegistry,
    /// Query result cache, stable query templates, and cache policy.
    query_cache: QueryCache,
    /// Shared counters used for public pool statistics and close diagnostics.
    stats: PoolStats,
    /// Active game table name (e.g., "Fallout4", "Skyrim").
    game_table: ActiveGameTable,
}

impl DatabasePool {
    /// Calculate optimal pool size based on CPU cores
    fn calculate_max_connections() -> usize {
        ConnectionAllocator::calculate_max_connections()
    }

    fn configured_connection_budget(&self) -> usize {
        self.registry.configured_connection_budget()
    }

    async fn close_active_pools(&self) {
        self.registry.close_active_pools(&self.stats).await;
    }

    async fn rebuild_allocated_pools(&self, db_paths: Vec<PathBuf>) -> Result<(), DatabaseError> {
        self.registry
            .rebuild_allocated_pools(db_paths, &self.query_cache, &self.stats)
            .await
    }

    fn insert_with_eviction(&self, cache_key: CacheKey, value: String, cache_ttl: Duration) {
        self.query_cache
            .insert_with_eviction(cache_key, value, cache_ttl, &self.stats);
    }

    fn insert_many_with_eviction(&self, entries: Vec<(CacheKey, String)>, cache_ttl: Duration) {
        self.query_cache
            .insert_many_with_eviction(entries, cache_ttl, &self.stats);
    }

    #[cfg(test)]
    fn preferred_eviction_target(capacity: usize) -> usize {
        QueryCache::preferred_eviction_target(capacity)
    }

    fn maybe_run_proactive_cleanup(&self, operation_count: u64) {
        self.query_cache
            .maybe_run_proactive_cleanup(operation_count, &self.stats);
    }

    #[cfg(test)]
    fn pool_registry_strong_count(&self) -> usize {
        self.registry.pool_arc_strong_count()
    }

    #[cfg(test)]
    fn shares_pool_registry_with(&self, other: &Self) -> bool {
        self.registry.shares_pool_storage_with(&other.registry)
    }

    #[cfg(test)]
    fn insert_cache_entry(&self, cache_key: CacheKey, entry: CacheEntry) {
        self.query_cache.insert_entry(cache_key, entry);
    }

    #[cfg(test)]
    fn cache_contains_key(&self, cache_key: &CacheKey) -> bool {
        self.query_cache.contains_key(cache_key)
    }

    #[cfg(test)]
    fn query_template_cache_size(&self) -> usize {
        self.query_cache.template_count()
    }

    /// Create a new database pool
    pub fn new(max_connections: Option<usize>, cache_ttl: Duration, game_table: String) -> Self {
        let max_conn = max_connections.unwrap_or_else(Self::calculate_max_connections);

        info!(
            "Initializing async DatabasePool (sqlx) with max_connections={}, cache_ttl={:?}, game_table={}",
            max_conn, cache_ttl, game_table
        );

        Self {
            registry: PoolRegistry::new(max_conn),
            query_cache: QueryCache::new(cache_ttl),
            stats: PoolStats::new(),
            game_table: ActiveGameTable::new(game_table),
        }
    }

    /// Initialize database connections for given paths
    pub async fn initialize(&self, db_paths: Vec<PathBuf>) -> Result<(), DatabaseError> {
        info!(
            "Initializing sqlx pools for {} requested database files",
            db_paths.len()
        );

        let mut valid_paths = Vec::new();
        for path in db_paths {
            if path.exists() {
                valid_paths.push(path);
            } else {
                warn!("Database file not found: {:?}", path);
            }
        }

        self.rebuild_allocated_pools(valid_paths).await
    }

    /// Get FormID entry from database
    pub async fn get_entry(
        &self,
        formid: &str,
        plugin: &str,
        table: Option<&str>,
    ) -> Result<Option<String>, DatabaseError> {
        self.maybe_run_proactive_cleanup(1);

        let game_table = self.game_table.resolve(table);

        let cache_key = CacheKey::new(&game_table, formid, plugin);

        // Check cache first
        if let Some(entry) = self.query_cache.get_entry(&cache_key) {
            if !entry.is_expired() {
                self.stats.increment_cache_hits(1);
                self.stats.increment_total_queries(1);
                debug!("Cache hit for FormID: {} Plugin: {}", formid, plugin);
                return Ok(Some(entry.value));
            } else {
                // Expired entry: evict and fall through — counted as a cache miss below.
                self.query_cache.remove_entry(&cache_key);
                debug!("Cache expired for FormID: {} Plugin: {}", formid, plugin);
            }
        }

        // Covers both cold-miss and expired-miss paths.
        self.stats.increment_cache_misses(1);
        self.stats.increment_total_queries(1);

        // Query databases using sqlx (TRUE ASYNC - no spawn_blocking!).
        // Stage 1: exact-case plugin match for full composite-index utilization.
        // Stage 2: case-insensitive fallback for compatibility with mismatched plugin casing.
        let exact_query = format!(
            "SELECT entry FROM {} WHERE formid=? AND plugin=?",
            game_table
        );
        let nocase_query = format!(
            "SELECT entry FROM {} WHERE formid=? AND plugin=? COLLATE nocase",
            game_table
        );

        for (query_label, query) in [("exact", &exact_query), ("nocase", &nocase_query)] {
            for (db_path, pool) in self.registry.pool_snapshots() {
                // TRUE ASYNC QUERY - no blocking!
                match sqlx::query(query)
                    .bind(formid)
                    .bind(plugin)
                    .fetch_optional(&pool)
                    .await
                {
                    Ok(Some(row)) => {
                        let value: String = row.try_get(0)?;
                        let cache_ttl = self.query_cache.current_ttl();
                        self.insert_with_eviction(cache_key.clone(), value.clone(), cache_ttl);
                        debug!(
                            "Found FormID {} in database {:?} via {} query",
                            formid, db_path, query_label
                        );
                        return Ok(Some(value));
                    }
                    Ok(None) => {
                        // Not found in this database, try next one
                        continue;
                    }
                    Err(e) => {
                        error!("Query error in {:?} ({}) : {}", db_path, query_label, e);
                        continue;
                    }
                }
            }
        }

        debug!("FormID {} not found in any database", formid);
        Ok(None)
    }

    /// Build a UNION ALL query for better index utilization.
    ///
    /// SQLite's optimizer handles UNION ALL queries more efficiently than
    /// OR-based conditions, especially when an index is available.
    ///
    /// # Arguments
    /// * `game_table` - The table name to query
    /// * `batch_len` - Number of (formid, plugin) pairs represented by the query
    ///
    /// # Returns
    /// A SQL query string using UNION ALL pattern
    fn build_union_all_query(game_table: &str, batch_len: usize, case_insensitive: bool) -> String {
        if batch_len == 0 {
            return String::new();
        }

        // Pre-allocate with estimated size:
        // Each SELECT is ~80 chars + table name
        let per_select_size = 80 + game_table.len();
        let union_size = 11; // " UNION ALL "
        let estimated_size = batch_len * per_select_size + (batch_len - 1) * union_size;

        let mut query = String::with_capacity(estimated_size);

        for i in 0..batch_len {
            if i > 0 {
                query.push_str(" UNION ALL ");
            }
            query.push_str("SELECT formid, plugin, entry FROM ");
            query.push_str(game_table);
            query.push_str(" WHERE formid=? AND plugin=?");
            if case_insensitive {
                query.push_str(" COLLATE nocase");
            }
        }

        query
    }

    fn select_stable_bucket_len(actual_len: usize) -> usize {
        if actual_len == 0 {
            return 0;
        }

        for bucket in STABLE_BATCH_BUCKETS {
            if actual_len <= bucket {
                return bucket;
            }
        }

        MAX_STABLE_BATCH_BUCKET
    }

    fn pad_batch_to_bucket(
        batch: &[(String, String, String)],
        bucket_len: usize,
    ) -> Vec<(String, String, String)> {
        if batch.is_empty() || batch.len() >= bucket_len {
            return batch.to_vec();
        }

        let mut padded = Vec::with_capacity(bucket_len);
        padded.extend(batch.iter().cloned());

        let pad_needed = bucket_len.saturating_sub(batch.len());
        let Some(pad_source) = batch.last().cloned() else {
            return batch.to_vec();
        };
        for _ in 0..pad_needed {
            padded.push(pad_source.clone());
        }

        padded
    }

    fn get_or_build_stable_query_template(
        &self,
        game_table: &str,
        bucket_len: usize,
        case_insensitive: bool,
    ) -> String {
        self.query_cache
            .get_or_build_template(game_table, bucket_len, case_insensitive)
    }

    fn record_stable_shape_selection(&self, bucket_len: usize, padded_pairs: usize) {
        self.stats
            .record_stable_shape_selection(bucket_len, padded_pairs);
    }

    async fn execute_parallel_batch_query(
        &self,
        query: &str,
        bindings: &[(String, String)],
    ) -> Vec<(String, String, String)> {
        // Collect all pools for parallel querying
        let pool_entries = self.registry.pool_snapshots();

        // Create futures for parallel database queries
        let query_futures: Vec<_> = pool_entries
            .into_iter()
            .map(|(db_path, pool)| {
                let query_clone = query.to_string();
                let bindings_clone = bindings.to_vec();

                async move {
                    // Build query with bindings
                    let mut sqlx_query = sqlx::query(&query_clone);
                    for (formid, plugin) in &bindings_clone {
                        sqlx_query = sqlx_query.bind(formid).bind(plugin);
                    }

                    // Execute async query
                    match sqlx_query.fetch_all(&pool).await {
                        Ok(rows) => {
                            let mut batch_results = Vec::with_capacity(rows.len());
                            for row in rows {
                                if let (Ok(formid), Ok(plugin), Ok(entry_val)) = (
                                    row.try_get::<String, _>(0),
                                    row.try_get::<String, _>(1),
                                    row.try_get::<String, _>(2),
                                ) {
                                    batch_results.push((formid, plugin, entry_val));
                                }
                            }
                            batch_results
                        }
                        Err(e) => {
                            error!("Batch query error in {:?}: {}", db_path, e);
                            Vec::new() // Return empty on error, don't fail entire batch
                        }
                    }
                }
            })
            .collect();

        let mut merged_results = Vec::new();
        for mut per_db_results in join_all(query_futures).await {
            merged_results.append(&mut per_db_results);
        }

        merged_results
    }

    fn merge_batch_rows(
        game_table: &str,
        rows: Vec<(String, String, String)>,
        original_key_lookup: &HashMap<(String, String), Vec<(String, String)>>,
        resolved_lookup_keys: &mut HashSet<(String, String)>,
        cache_inserts: &mut Vec<(CacheKey, String)>,
        results: &mut HashMap<String, String>,
    ) {
        for (db_formid, db_plugin, entry) in rows {
            // Look up all original caller's keys using case-insensitive match
            let lookup_key = (db_formid.clone(), CacheKey::normalize_plugin(&db_plugin));
            let original_pairs = match original_key_lookup.get(&lookup_key) {
                Some(pairs) => pairs,
                None => {
                    // Should not happen, but log and skip if it does
                    warn!(
                        "No original key found for database result: {}:{}",
                        db_formid, db_plugin
                    );
                    continue;
                }
            };

            resolved_lookup_keys.insert(lookup_key.clone());
            cache_inserts.push((
                CacheKey::new(game_table, &db_formid, &db_plugin),
                entry.clone(),
            ));

            // Insert result for ALL original keys that normalized to this lookup key
            for original_pair in original_pairs {
                let result_key = format!("{}:{}", original_pair.0, original_pair.1);

                // Only insert if not already found (first match wins)
                if let std::collections::hash_map::Entry::Vacant(e) = results.entry(result_key) {
                    e.insert(entry.clone());
                }
            }
        }
    }

    /// Batch lookup for FormID entries with optimized parallel queries.
    ///
    /// This method uses several optimizations for high-performance lookups:
    /// - UNION ALL queries instead of OR for better index utilization
    /// - Parallel queries across all database files using `join_all`
    /// - TTL-based caching with optimized key generation
    /// - Adaptive batch sizing based on input size
    ///
    /// # Arguments
    /// * `formid_plugin_pairs` - List of (FormID, plugin) tuples to look up
    /// * `table` - Optional table name override (defaults to game_table)
    /// * `batch_size` - Maximum pairs per query batch (default: 100)
    ///
    /// # Returns
    /// HashMap mapping "formid:plugin" to entry text
    pub async fn get_entries_batch(
        &self,
        formid_plugin_pairs: Vec<(String, String)>,
        table: Option<&str>,
        batch_size: usize,
    ) -> Result<HashMap<String, String>, DatabaseError> {
        self.maybe_run_proactive_cleanup(formid_plugin_pairs.len() as u64);

        let game_table = self.game_table.resolve(table);

        info!(
            "Starting optimized batch lookup for {} FormID/plugin pairs (parallel + UNION ALL)",
            formid_plugin_pairs.len()
        );

        let mut results: HashMap<String, String> = HashMap::new();
        let mut uncached_pairs: Vec<(String, String, String)> = Vec::new();

        // Check cache first using optimized key generation
        for (formid, plugin) in &formid_plugin_pairs {
            let normalized_plugin = CacheKey::normalize_plugin(plugin);
            let cache_key =
                CacheKey::from_normalized_plugin(&game_table, formid, &normalized_plugin);

            if let Some(entry) = self.query_cache.get_entry(&cache_key) {
                if !entry.is_expired() {
                    let result_key = format!("{}:{}", formid, plugin);
                    results.insert(result_key, entry.value);
                    self.stats.increment_cache_hits(1);
                    continue;
                } else {
                    // Expired entry: evict and fall through — counted as a cache miss below.
                    self.query_cache.remove_entry(&cache_key);
                }
            }

            uncached_pairs.push((formid.clone(), plugin.clone(), normalized_plugin));
            // Covers both cold-miss and expired-miss paths.
            self.stats.increment_cache_misses(1);
        }

        // total_queries counts every pair in the batch regardless of cache status,
        // so total = cache_hits + cache_misses = formid_plugin_pairs.len().
        self.stats
            .increment_total_queries(formid_plugin_pairs.len() as u64);

        if uncached_pairs.is_empty() {
            return Ok(results);
        }

        let cache_ttl = self.query_cache.current_ttl();

        // Keep caller-provided chunking contract while enforcing stable-shape bounds.
        let effective_batch_size = batch_size.clamp(1, MAX_STABLE_BATCH_BUCKET);

        // Process uncached pairs in batches with PARALLEL database queries
        for batch in uncached_pairs.chunks(effective_batch_size) {
            // Build lookup map: (formid, lowercase_plugin) -> Vec of original (formid, plugin) keys
            // Multiple input pairs may normalize to the same case-insensitive key
            // (e.g., "Fallout4.esm" and "FALLOUT4.ESM"), so we track all of them
            let mut original_key_lookup: HashMap<(String, String), Vec<(String, String)>> =
                HashMap::new();
            for (fid, plug, normalized_plugin) in batch {
                let normalized_key = (fid.clone(), normalized_plugin.clone());
                original_key_lookup
                    .entry(normalized_key)
                    .or_default()
                    .push((fid.clone(), plug.clone()));
            }

            let bucket_len = Self::select_stable_bucket_len(batch.len());
            let padded_batch = Self::pad_batch_to_bucket(batch, bucket_len);
            self.record_stable_shape_selection(bucket_len, bucket_len.saturating_sub(batch.len()));

            // Stage 1: exact-case query to fully leverage (formid, plugin) index shape.
            let exact_query =
                self.get_or_build_stable_query_template(&game_table, bucket_len, false);
            let exact_bindings: Vec<(String, String)> = padded_batch
                .iter()
                .map(|(formid, plugin, _)| (formid.clone(), plugin.clone()))
                .collect();
            let exact_rows = self
                .execute_parallel_batch_query(&exact_query, &exact_bindings)
                .await;

            let mut resolved_lookup_keys: HashSet<(String, String)> = HashSet::new();
            let mut cache_inserts: Vec<(CacheKey, String)> = Vec::new();
            Self::merge_batch_rows(
                &game_table,
                exact_rows,
                &original_key_lookup,
                &mut resolved_lookup_keys,
                &mut cache_inserts,
                &mut results,
            );

            // Stage 2: case-insensitive fallback only for unresolved keys.
            // This preserves behavior while avoiding COLLATE NOCASE for the fast-path.
            if resolved_lookup_keys.len() < original_key_lookup.len() {
                let unresolved_pairs: Vec<(String, String, String)> = original_key_lookup
                    .iter()
                    .filter(|(lookup_key, _)| !resolved_lookup_keys.contains(*lookup_key))
                    .filter_map(|((formid, normalized_plugin), originals)| {
                        originals.first().map(|(_, plugin)| {
                            (formid.clone(), plugin.clone(), normalized_plugin.clone())
                        })
                    })
                    .collect();

                if !unresolved_pairs.is_empty() {
                    let fallback_bucket_len =
                        Self::select_stable_bucket_len(unresolved_pairs.len());
                    let padded_fallback =
                        Self::pad_batch_to_bucket(&unresolved_pairs, fallback_bucket_len);
                    self.record_stable_shape_selection(
                        fallback_bucket_len,
                        fallback_bucket_len.saturating_sub(unresolved_pairs.len()),
                    );

                    let fallback_query = self.get_or_build_stable_query_template(
                        &game_table,
                        fallback_bucket_len,
                        true,
                    );
                    let fallback_bindings: Vec<(String, String)> = padded_fallback
                        .iter()
                        .map(|(formid, plugin, _)| (formid.clone(), plugin.clone()))
                        .collect();
                    let fallback_rows = self
                        .execute_parallel_batch_query(&fallback_query, &fallback_bindings)
                        .await;
                    Self::merge_batch_rows(
                        &game_table,
                        fallback_rows,
                        &original_key_lookup,
                        &mut resolved_lookup_keys,
                        &mut cache_inserts,
                        &mut results,
                    );
                }
            }

            self.insert_many_with_eviction(cache_inserts, cache_ttl);
        }

        info!(
            "Optimized batch lookup completed: found {}/{} entries",
            results.len(),
            formid_plugin_pairs.len()
        );

        Ok(results)
    }

    // Utility methods
    /// Set the active game table name
    ///
    /// # Arguments
    /// * `table` - Table name (e.g., "Fallout4", "Skyrim")
    pub fn set_game_table(&self, table: &str) {
        self.game_table.set(table);
    }

    /// Get the current game table name
    pub fn get_game_table(&self) -> String {
        self.game_table.get()
    }

    /// Clear the query cache
    ///
    /// # Arguments
    /// * `expired_only` - If true, only remove expired entries; if false, clear all
    ///
    /// # Returns
    /// Number of cache entries removed
    pub fn clear_cache(&self, expired_only: bool) -> usize {
        self.query_cache.clear(expired_only)
    }

    /// Set the cache time-to-live duration
    ///
    /// # Arguments
    /// * `ttl` - New TTL duration for cached queries
    pub fn set_cache_ttl(&self, ttl: Duration) {
        self.query_cache.set_ttl(ttl);
    }

    /// Get the current cache time-to-live duration.
    pub fn get_cache_ttl(&self) -> Duration {
        self.query_cache.current_ttl()
    }

    /// Get the maximum number of cache entries allowed.
    pub fn get_cache_capacity(&self) -> usize {
        self.query_cache.capacity()
    }

    /// Set the maximum number of cache entries allowed.
    ///
    /// Value is clamped to configured min/max bounds.
    pub fn set_cache_capacity(&self, capacity: usize) {
        self.query_cache.set_capacity(capacity, &self.stats);
    }

    /// Get proactive cleanup operation threshold.
    pub fn get_cache_cleanup_threshold(&self) -> u64 {
        self.query_cache.cleanup_threshold()
    }

    /// Set proactive cleanup operation threshold.
    ///
    /// Value is clamped to configured min/max bounds.
    pub fn set_cache_cleanup_threshold(&self, threshold: u64) {
        self.query_cache.set_cleanup_threshold(threshold);
    }

    /// Get proactive cleanup interval.
    pub fn get_cache_cleanup_interval(&self) -> Duration {
        self.query_cache.cleanup_interval()
    }

    /// Set proactive cleanup interval.
    ///
    /// Value is clamped to configured min/max bounds.
    pub fn set_cache_cleanup_interval(&self, interval: Duration) {
        self.query_cache.set_cleanup_interval(interval);
    }

    /// Get the configured global connection budget.
    pub fn get_max_connections(&self) -> Option<usize> {
        self.registry.get_max_connections()
    }

    /// Set the configured global connection budget.
    ///
    /// This updates configuration for the next `initialize()` or explicit
    /// `rebalance_connections()` call. Existing pools are not rebuilt implicitly.
    pub fn set_max_connections(&self, max_connections: usize) {
        self.registry.set_max_connections(max_connections);
    }

    /// Recalculate optimal global connection budget based on current CPU cores.
    ///
    /// Like `set_max_connections`, this is config-only until the next rebuild.
    pub fn recalculate_max_connections(&self) {
        let new_max = Self::calculate_max_connections();
        self.set_max_connections(new_max);
    }

    /// Rebuild active pools using the current global connection budget.
    ///
    /// This is the explicit runtime path for immediate allocation changes after
    /// `set_max_connections()`/`recalculate_max_connections()`.
    pub async fn rebalance_connections(&self) -> Result<(), DatabaseError> {
        let tracked_paths = self.registry.tracked_paths();
        self.initialize(tracked_paths).await
    }

    /// Get current performance statistics
    pub fn get_stats(&self) -> Result<PoolStatistics, DatabaseError> {
        let configured_budget = self.configured_connection_budget() as u64;
        let allocations_snapshot = self.registry.allocations_snapshot();

        Ok(self
            .stats
            .snapshot(configured_budget, &allocations_snapshot))
    }

    /// Check if any database pools are available
    pub fn is_available(&self) -> bool {
        self.registry.is_available()
    }

    /// Get the current number of entries in the query cache
    pub fn cache_size(&self) -> usize {
        self.query_cache.len()
    }

    /// Close all connections and clear caches
    pub async fn close(&self) -> Result<(), DatabaseError> {
        let pool_count = self.registry.len();
        let cache_size = self.query_cache.len();

        // Capture current stats before closing for logging
        let active_before = self.stats.active_connections();
        let total_queries = self.stats.total_queries();
        let (cleanup_runs, cleanup_ns_total, cleanup_ns_max, eviction_ns_total, eviction_ns_max) =
            self.stats.maintenance_snapshot();

        info!(
            "Closing all database connections: {} pool(s), {} cached queries, {} active connection(s)",
            pool_count, cache_size, active_before
        );

        // Clear query result cache but keep reusable SQL templates.
        self.query_cache.clear_entries();

        // Close all pools and clear tracked connection metadata.
        self.close_active_pools().await;
        self.registry.clear_tracking();

        info!(
            "Database pool closed successfully. Total queries processed: {}",
            total_queries
        );
        info!(
            "Database maintenance timings: cleanup_runs={}, cleanup_total_ms={:.3}, cleanup_max_ms={:.3}, eviction_total_ms={:.3}, eviction_max_ms={:.3}",
            cleanup_runs,
            cleanup_ns_total as f64 / 1_000_000.0,
            cleanup_ns_max as f64 / 1_000_000.0,
            eviction_ns_total as f64 / 1_000_000.0,
            eviction_ns_max as f64 / 1_000_000.0
        );

        Ok(())
    }

    /// Optimize database connections (VACUUM and ANALYZE)
    pub async fn optimize(&self) -> Result<(), DatabaseError> {
        info!("Optimizing database connections");

        for (db_path, pool) in self.registry.pool_snapshots() {
            // Note: VACUUM cannot be run on read-only databases
            // We'll just run ANALYZE which is allowed in read-only mode
            match sqlx::query("ANALYZE").execute(&pool).await {
                Ok(_) => {
                    info!("Analyzed database {:?}", db_path);
                }
                Err(e) => {
                    warn!("Failed to analyze database {:?}: {}", db_path, e);
                    // Continue with other databases
                }
            }
        }

        Ok(())
    }
}

impl Drop for DatabasePool {
    /// Drop handler that warns if pools weren't explicitly closed.
    ///
    /// When `DatabasePool` is dropped without calling `close()`, the underlying
    /// sqlx pools will be cleaned up automatically, but this may result in:
    /// - Unpredictable connection cleanup timing
    /// - No proper WAL checkpointing for SQLite databases
    /// - Potential resource leaks in long-running applications
    ///
    /// For best practices, always call `close()` explicitly before dropping.
    ///
    /// # Clone-safety
    ///
    /// Since `DatabasePool` uses `Arc`-wrapped fields and derives `Clone`, multiple
    /// clones share the same underlying pools. This warning only fires when the
    /// *last* reference is dropped without `close()` being called, avoiding spurious
    /// warnings when other clones still exist and may call `close()` later.
    fn drop(&mut self) {
        // Only warn if this is the last Arc reference AND pools weren't closed.
        // When multiple clones exist, other clones may still call close() later.
        if self.registry.is_last_handle_with_open_pools() {
            let pool_count = self.registry.len();
            let active_connections = self.stats.active_connections();

            warn!(
                "DatabasePool dropped without calling close(). \
                 {} pool(s) with {} tracked connection(s) will be cleaned up by sqlx. \
                 Call close() explicitly for proper WAL checkpointing and resource cleanup.",
                pool_count, active_connections
            );
        }
    }
}

#[cfg(test)]
#[path = "pool_sqlx_tests.rs"]
mod tests;
