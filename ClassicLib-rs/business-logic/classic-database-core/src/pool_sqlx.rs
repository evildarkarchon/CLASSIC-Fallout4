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
use std::collections::HashMap;
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
pub const DEFAULT_QUERY_CACHE_CAPACITY: usize = 10_000;

/// Minimum allowed query cache capacity.
pub const MIN_QUERY_CACHE_CAPACITY: usize = 1;

/// Maximum allowed query cache capacity.
pub const MAX_QUERY_CACHE_CAPACITY: usize = 1_000_000;

/// Default number of lookup operations before proactive cleanup is considered.
pub const DEFAULT_CACHE_CLEANUP_OP_THRESHOLD: u64 = 256;

/// Minimum allowed cleanup operation threshold.
pub const MIN_CACHE_CLEANUP_OP_THRESHOLD: u64 = 1;

/// Maximum allowed cleanup operation threshold.
pub const MAX_CACHE_CLEANUP_OP_THRESHOLD: u64 = 100_000;

/// Default minimum cleanup interval in seconds.
pub const DEFAULT_CACHE_CLEANUP_INTERVAL_SECS: u64 = 5;

/// Minimum allowed proactive cleanup interval in seconds.
pub const MIN_CACHE_CLEANUP_INTERVAL_SECS: u64 = 1;

/// Maximum allowed proactive cleanup interval in seconds.
pub const MAX_CACHE_CLEANUP_INTERVAL_SECS: u64 = 300;

/// Type alias for batch query results: Vec of (formid, plugin, entry) tuples.
type BatchQueryResult = Result<Vec<(String, String, String)>, DatabaseError>;
const STABLE_BATCH_BUCKETS: [usize; 8] = [8, 16, 32, 64, 128, 256, 512, 1024];
const MAX_STABLE_BATCH_BUCKET: usize = 1024;

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

/// Database pool with sqlx - true async support
///
/// Provides high-performance asynchronous database access with connection pooling,
/// query caching, and FormID lookup optimization.
#[derive(Clone)]
pub struct DatabasePool {
    /// Map of database paths to sqlx connection pools
    pools: Arc<DashMap<PathBuf, SqlitePool>>,
    /// Query result cache with TTL-based expiration
    query_cache: Arc<DashMap<CacheKey, CacheEntry>>,
    /// Reusable query templates keyed by (table, stable bucket size)
    query_template_cache: Arc<DashMap<(String, usize), String>>,
    /// Maximum number of entries allowed in query cache
    cache_capacity: Arc<AtomicUsize>,
    /// Number of lookup operations before cleanup is considered
    cache_cleanup_threshold: Arc<AtomicU64>,
    /// Minimum duration between proactive cleanup runs
    cache_cleanup_interval: Arc<RwLock<Duration>>,
    /// Number of lookup operations since the last cleanup run
    cache_ops_since_cleanup: Arc<AtomicU64>,
    /// Timestamp of last proactive cleanup run
    last_cleanup_at: Arc<RwLock<Instant>>,
    /// Time-to-live duration for cached queries
    cache_ttl: Arc<RwLock<Duration>>,
    /// Maximum number of connections per pool
    max_connections: Arc<RwLock<Option<usize>>>,
    /// Effective per-database allocations for the currently active pools
    pool_allocations: Arc<RwLock<HashMap<PathBuf, usize>>>,
    /// Total number of queries executed
    stat_total_queries: Arc<AtomicU64>,
    /// Number of queries served from cache
    stat_cache_hits: Arc<AtomicU64>,
    /// Number of queries that required database access
    stat_cache_misses: Arc<AtomicU64>,
    /// Total number of connections created
    stat_total_connections: Arc<AtomicU64>,
    /// Number of currently active connections
    stat_active_connections: Arc<AtomicU64>,
    /// Number of cache entries evicted due to capacity pressure
    stat_cache_evictions: Arc<AtomicU64>,
    /// Number of proactive cleanup runs performed
    stat_cleanup_runs: Arc<AtomicU64>,
    /// Number of entries removed by proactive cleanup
    stat_cleanup_removed: Arc<AtomicU64>,
    /// Number of stable-shape bucket selections in batch path
    stat_stable_shape_selections: Arc<AtomicU64>,
    /// Number of padded pair slots used to satisfy stable shapes
    stat_stable_shape_padding_pairs: Arc<AtomicU64>,
    /// Stable bucket usage counters
    stat_stable_shape_bucket_8: Arc<AtomicU64>,
    stat_stable_shape_bucket_16: Arc<AtomicU64>,
    stat_stable_shape_bucket_32: Arc<AtomicU64>,
    stat_stable_shape_bucket_64: Arc<AtomicU64>,
    stat_stable_shape_bucket_128: Arc<AtomicU64>,
    stat_stable_shape_bucket_256: Arc<AtomicU64>,
    stat_stable_shape_bucket_512: Arc<AtomicU64>,
    stat_stable_shape_bucket_1024: Arc<AtomicU64>,
    /// Active game table name (e.g., "Fallout4", "Skyrim")
    game_table: Arc<RwLock<String>>,
    /// List of database file paths currently loaded
    db_paths: Arc<RwLock<Vec<PathBuf>>>,
}

impl DatabasePool {
    /// Calculate optimal pool size based on CPU cores
    fn calculate_max_connections() -> usize {
        let cpus = num_cpus::get();
        let optimal = cpus * 4; // 4 connections per CPU core for async I/O
        optimal.clamp(8, 64) // Higher bounds for async operations
    }

    fn clamp_cache_capacity(capacity: usize) -> usize {
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

    fn configured_connection_budget(&self) -> usize {
        self.max_connections
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("max_connections lock was poisoned - recovering");
                poisoned.into_inner()
            })
            .unwrap_or_else(Self::calculate_max_connections)
    }

    fn derive_connection_allocation(
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

    async fn close_active_pools(&self) {
        let existing_pools: Vec<(PathBuf, SqlitePool)> = self
            .pools
            .iter()
            .map(|entry| (entry.key().clone(), entry.value().clone()))
            .collect();

        for (db_path, pool) in existing_pools {
            pool.close().await;
            debug!("Closed connection pool for {:?}", db_path);
        }

        self.pools.clear();
        self.stat_active_connections.store(0, Ordering::Relaxed);
    }

    async fn rebuild_allocated_pools(&self, db_paths: Vec<PathBuf>) -> Result<(), DatabaseError> {
        let configured_budget = self.configured_connection_budget();
        let plan = Self::derive_connection_allocation(configured_budget, &db_paths);

        info!(
            "Applying global connection budget: configured={}, effective={}, active_pools={}",
            plan.configured_budget,
            plan.effective_budget,
            plan.allocations.len()
        );

        self.close_active_pools().await;
        self.query_cache.clear();

        if plan.allocations.is_empty() {
            if let Ok(mut paths) = self.db_paths.write() {
                paths.clear();
            }
            if let Ok(mut allocations) = self.pool_allocations.write() {
                allocations.clear();
            }
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
            self.stat_total_connections.fetch_add(1, Ordering::Relaxed);
        }

        self.stat_active_connections
            .store(applied_paths.len() as u64, Ordering::Relaxed);

        if let Ok(mut paths) = self.db_paths.write() {
            *paths = applied_paths;
        }
        if let Ok(mut allocations) = self.pool_allocations.write() {
            *allocations = applied_allocations;
        }

        Ok(())
    }

    fn insert_with_eviction(&self, cache_key: CacheKey, value: String, cache_ttl: Duration) {
        self.query_cache
            .insert(cache_key, CacheEntry::new(value, cache_ttl));
        self.evict_to_capacity();
    }

    fn evict_to_capacity(&self) {
        let mut total_evicted = 0_u64;

        loop {
            let capacity = self.cache_capacity.load(Ordering::Relaxed);
            if self.query_cache.len() <= capacity {
                break;
            }

            // Policy step 1: always purge expired entries first.
            let expired_keys: Vec<CacheKey> = self
                .query_cache
                .iter()
                .filter(|entry| entry.value().is_expired())
                .map(|entry| entry.key().clone())
                .collect();

            if !expired_keys.is_empty() {
                let mut expired_removed = 0_u64;
                for key in expired_keys {
                    if self.query_cache.remove(&key).is_some() {
                        expired_removed += 1;
                    }
                    if self.query_cache.len() <= capacity {
                        break;
                    }
                }
                total_evicted += expired_removed;
                continue;
            }

            // Policy step 2: if still over cap, evict the oldest entry.
            // Tie-break by cache key for deterministic behavior.
            let mut oldest_candidate: Option<(Instant, CacheKey)> = None;
            for entry in self.query_cache.iter() {
                let candidate = (entry.value().created_at, entry.key().clone());
                match &oldest_candidate {
                    None => oldest_candidate = Some(candidate),
                    Some((oldest_at, oldest_key)) => {
                        if candidate.0 < *oldest_at
                            || (candidate.0 == *oldest_at
                                && candidate.1.tie_break_key() < oldest_key.tie_break_key())
                        {
                            oldest_candidate = Some(candidate);
                        }
                    }
                }
            }

            let Some((_, oldest_key)) = oldest_candidate else {
                break;
            };

            if self.query_cache.remove(&oldest_key).is_some() {
                total_evicted += 1;
            } else {
                break;
            }
        }

        if total_evicted > 0 {
            self.stat_cache_evictions
                .fetch_add(total_evicted, Ordering::Relaxed);
        }
    }

    fn maybe_run_proactive_cleanup(&self, operation_count: u64) {
        let updated_ops = self
            .cache_ops_since_cleanup
            .fetch_add(operation_count, Ordering::Relaxed)
            .saturating_add(operation_count);

        let threshold = self.cache_cleanup_threshold.load(Ordering::Relaxed);
        if updated_ops < threshold {
            return;
        }

        let interval = *self
            .cache_cleanup_interval
            .read()
            .unwrap_or_else(|poisoned| {
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

        let removed = self.clear_cache(true) as u64;
        self.stat_cleanup_runs.fetch_add(1, Ordering::Relaxed);
        self.stat_cleanup_removed
            .fetch_add(removed, Ordering::Relaxed);
        self.cache_ops_since_cleanup.store(0, Ordering::Relaxed);

        if let Ok(mut last_cleanup) = self.last_cleanup_at.write() {
            *last_cleanup = Instant::now();
        }
    }

    /// Create a new database pool
    pub fn new(max_connections: Option<usize>, cache_ttl: Duration, game_table: String) -> Self {
        let max_conn = max_connections.unwrap_or_else(Self::calculate_max_connections);

        info!(
            "Initializing async DatabasePool (sqlx) with max_connections={}, cache_ttl={:?}, game_table={}",
            max_conn, cache_ttl, game_table
        );

        Self {
            pools: Arc::new(DashMap::new()),
            query_cache: Arc::new(DashMap::new()),
            query_template_cache: Arc::new(DashMap::new()),
            cache_capacity: Arc::new(AtomicUsize::new(DEFAULT_QUERY_CACHE_CAPACITY)),
            cache_cleanup_threshold: Arc::new(AtomicU64::new(DEFAULT_CACHE_CLEANUP_OP_THRESHOLD)),
            cache_cleanup_interval: Arc::new(RwLock::new(Duration::from_secs(
                DEFAULT_CACHE_CLEANUP_INTERVAL_SECS,
            ))),
            cache_ops_since_cleanup: Arc::new(AtomicU64::new(0)),
            last_cleanup_at: Arc::new(RwLock::new(Instant::now())),
            cache_ttl: Arc::new(RwLock::new(cache_ttl)),
            max_connections: Arc::new(RwLock::new(Some(max_conn))),
            pool_allocations: Arc::new(RwLock::new(HashMap::new())),
            stat_total_queries: Arc::new(AtomicU64::new(0)),
            stat_cache_hits: Arc::new(AtomicU64::new(0)),
            stat_cache_misses: Arc::new(AtomicU64::new(0)),
            stat_total_connections: Arc::new(AtomicU64::new(0)),
            stat_active_connections: Arc::new(AtomicU64::new(0)),
            stat_cache_evictions: Arc::new(AtomicU64::new(0)),
            stat_cleanup_runs: Arc::new(AtomicU64::new(0)),
            stat_cleanup_removed: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_selections: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_padding_pairs: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_bucket_8: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_bucket_16: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_bucket_32: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_bucket_64: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_bucket_128: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_bucket_256: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_bucket_512: Arc::new(AtomicU64::new(0)),
            stat_stable_shape_bucket_1024: Arc::new(AtomicU64::new(0)),
            game_table: Arc::new(RwLock::new(game_table)),
            db_paths: Arc::new(RwLock::new(Vec::new())),
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

        let game_table = match table {
            Some(t) => t.to_string(),
            None => self
                .game_table
                .read()
                .unwrap_or_else(|poisoned| {
                    warn!("game_table lock was poisoned - recovering");
                    poisoned.into_inner()
                })
                .clone(),
        };

        let cache_key = CacheKey::new(&game_table, formid, plugin);

        // Check cache first
        if let Some(entry) = self.query_cache.get(&cache_key) {
            if !entry.is_expired() {
                self.stat_cache_hits.fetch_add(1, Ordering::Relaxed);
                self.stat_total_queries.fetch_add(1, Ordering::Relaxed);
                debug!("Cache hit for FormID: {} Plugin: {}", formid, plugin);
                return Ok(Some(entry.value.clone()));
            } else {
                // Expired entry: evict and fall through — counted as a cache miss below.
                self.query_cache.remove(&cache_key);
                debug!("Cache expired for FormID: {} Plugin: {}", formid, plugin);
            }
        }

        // Covers both cold-miss and expired-miss paths.
        self.stat_cache_misses.fetch_add(1, Ordering::Relaxed);
        self.stat_total_queries.fetch_add(1, Ordering::Relaxed);

        // Query databases using sqlx (TRUE ASYNC - no spawn_blocking!)
        let query_str = format!(
            "SELECT entry FROM {} WHERE formid=? AND plugin=? COLLATE nocase",
            game_table
        );

        for entry in self.pools.iter() {
            let db_path = entry.key().clone();
            let pool = entry.value();

            // TRUE ASYNC QUERY - no blocking!
            match sqlx::query(&query_str)
                .bind(formid)
                .bind(plugin)
                .fetch_optional(pool)
                .await
            {
                Ok(Some(row)) => {
                    let value: String = row.try_get(0)?;
                    let cache_ttl = *self.cache_ttl.read().unwrap_or_else(|poisoned| {
                        warn!("cache_ttl lock was poisoned - recovering");
                        poisoned.into_inner()
                    });
                    self.insert_with_eviction(cache_key.clone(), value.clone(), cache_ttl);
                    debug!("Found FormID {} in database {:?}", formid, db_path);
                    return Ok(Some(value));
                }
                Ok(None) => {
                    // Not found in this database, try next one
                    continue;
                }
                Err(e) => {
                    error!("Query error in {:?}: {}", db_path, e);
                    continue;
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
    fn build_union_all_query(game_table: &str, batch_len: usize) -> String {
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
            query.push_str(" WHERE formid=? AND plugin=? COLLATE nocase");
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
        let pad_source = batch
            .last()
            .expect("batch.is_empty() is handled before padding")
            .clone();
        for _ in 0..pad_needed {
            padded.push(pad_source.clone());
        }

        padded
    }

    fn get_or_build_stable_query_template(&self, game_table: &str, bucket_len: usize) -> String {
        let template_key = (game_table.to_string(), bucket_len);

        if let Some(existing) = self.query_template_cache.get(&template_key) {
            return existing.clone();
        }

        let template = Self::build_union_all_query(game_table, bucket_len);
        self.query_template_cache
            .insert(template_key, template.clone());
        template
    }

    fn record_stable_shape_selection(&self, bucket_len: usize, padded_pairs: usize) {
        self.stat_stable_shape_selections
            .fetch_add(1, Ordering::Relaxed);
        if padded_pairs > 0 {
            self.stat_stable_shape_padding_pairs
                .fetch_add(padded_pairs as u64, Ordering::Relaxed);
        }

        let bucket_counter = match bucket_len {
            8 => &self.stat_stable_shape_bucket_8,
            16 => &self.stat_stable_shape_bucket_16,
            32 => &self.stat_stable_shape_bucket_32,
            64 => &self.stat_stable_shape_bucket_64,
            128 => &self.stat_stable_shape_bucket_128,
            256 => &self.stat_stable_shape_bucket_256,
            512 => &self.stat_stable_shape_bucket_512,
            1024 => &self.stat_stable_shape_bucket_1024,
            _ => return,
        };

        bucket_counter.fetch_add(1, Ordering::Relaxed);
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

        let game_table = match table {
            Some(t) => t.to_string(),
            None => self
                .game_table
                .read()
                .unwrap_or_else(|poisoned| {
                    warn!("game_table lock was poisoned - recovering");
                    poisoned.into_inner()
                })
                .clone(),
        };

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

            if let Some(entry) = self.query_cache.get(&cache_key) {
                if !entry.is_expired() {
                    let result_key = format!("{}:{}", formid, plugin);
                    results.insert(result_key, entry.value.clone());
                    self.stat_cache_hits.fetch_add(1, Ordering::Relaxed);
                    continue;
                } else {
                    // Expired entry: evict and fall through — counted as a cache miss below.
                    self.query_cache.remove(&cache_key);
                }
            }

            uncached_pairs.push((formid.clone(), plugin.clone(), normalized_plugin));
            // Covers both cold-miss and expired-miss paths.
            self.stat_cache_misses.fetch_add(1, Ordering::Relaxed);
        }

        // stat_total_queries counts every pair in the batch regardless of cache status,
        // so total = cache_hits + cache_misses = formid_plugin_pairs.len().
        self.stat_total_queries
            .fetch_add(formid_plugin_pairs.len() as u64, Ordering::Relaxed);

        if uncached_pairs.is_empty() {
            return Ok(results);
        }

        let cache_ttl = *self.cache_ttl.read().unwrap_or_else(|poisoned| {
            warn!("cache_ttl lock was poisoned - recovering");
            poisoned.into_inner()
        });

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

            // Build/reuse optimized UNION ALL query for a stable bucket shape.
            let query = self.get_or_build_stable_query_template(&game_table, bucket_len);

            // Collect all pools for parallel querying
            let pool_entries: Vec<_> = self.pools.iter().collect();

            // Create futures for parallel database queries
            let query_futures: Vec<_> = pool_entries
                .iter()
                .map(|entry| {
                    let db_path = entry.key().clone();
                    let pool = entry.value().clone();
                    let query_clone = query.clone();
                    let batch_clone: Vec<(String, String)> = padded_batch
                        .iter()
                        .map(|(formid, plugin, _)| (formid.clone(), plugin.clone()))
                        .collect();

                    async move {
                        // Build query with bindings
                        let mut sqlx_query = sqlx::query(&query_clone);
                        for (formid, plugin) in &batch_clone {
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
                                Ok(batch_results)
                            }
                            Err(e) => {
                                error!("Batch query error in {:?}: {}", db_path, e);
                                Ok(Vec::new()) // Return empty on error, don't fail entire batch
                            }
                        }
                    }
                })
                .collect();

            // Execute all database queries in parallel
            let all_results: Vec<BatchQueryResult> = join_all(query_futures).await;

            // Merge results from all databases
            for db_result in all_results {
                match db_result {
                    Ok(entries) => {
                        for (db_formid, db_plugin, entry) in entries {
                            // Look up all original caller's keys using case-insensitive match
                            let lookup_key =
                                (db_formid.clone(), CacheKey::normalize_plugin(&db_plugin));
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

                            let cache_key = CacheKey::new(&game_table, &db_formid, &db_plugin);

                            // Cache the result once using the normalized key
                            self.insert_with_eviction(cache_key, entry.clone(), cache_ttl);

                            // Insert result for ALL original keys that normalized to this lookup key
                            for original_pair in original_pairs {
                                let result_key = format!("{}:{}", original_pair.0, original_pair.1);

                                // Only insert if not already found (first match wins)
                                if let std::collections::hash_map::Entry::Vacant(e) =
                                    results.entry(result_key)
                                {
                                    e.insert(entry.clone());
                                }
                            }
                        }
                    }
                    Err(e) => {
                        warn!("Database query batch failed: {}", e);
                    }
                }
            }
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
        if let Ok(mut t) = self.game_table.write() {
            *t = table.to_string();
        }
    }

    /// Get the current game table name
    pub fn get_game_table(&self) -> String {
        self.game_table
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("game_table lock was poisoned - recovering");
                poisoned.into_inner()
            })
            .clone()
    }

    /// Clear the query cache
    ///
    /// # Arguments
    /// * `expired_only` - If true, only remove expired entries; if false, clear all
    ///
    /// # Returns
    /// Number of cache entries removed
    pub fn clear_cache(&self, expired_only: bool) -> usize {
        let initial_size = self.query_cache.len();
        if expired_only {
            self.query_cache.retain(|_, v| !v.is_expired());
        } else {
            self.query_cache.clear();
        }
        initial_size - self.query_cache.len()
    }

    /// Set the cache time-to-live duration
    ///
    /// # Arguments
    /// * `ttl` - New TTL duration for cached queries
    pub fn set_cache_ttl(&self, ttl: Duration) {
        if let Ok(mut t) = self.cache_ttl.write() {
            *t = ttl;
        }
    }

    /// Get the maximum number of cache entries allowed.
    pub fn get_cache_capacity(&self) -> usize {
        self.cache_capacity.load(Ordering::Relaxed)
    }

    /// Set the maximum number of cache entries allowed.
    ///
    /// Value is clamped to configured min/max bounds.
    pub fn set_cache_capacity(&self, capacity: usize) {
        self.cache_capacity
            .store(Self::clamp_cache_capacity(capacity), Ordering::Relaxed);
        self.evict_to_capacity();
    }

    /// Get proactive cleanup operation threshold.
    pub fn get_cache_cleanup_threshold(&self) -> u64 {
        self.cache_cleanup_threshold.load(Ordering::Relaxed)
    }

    /// Set proactive cleanup operation threshold.
    ///
    /// Value is clamped to configured min/max bounds.
    pub fn set_cache_cleanup_threshold(&self, threshold: u64) {
        self.cache_cleanup_threshold
            .store(Self::clamp_cleanup_threshold(threshold), Ordering::Relaxed);
    }

    /// Get proactive cleanup interval.
    pub fn get_cache_cleanup_interval(&self) -> Duration {
        *self
            .cache_cleanup_interval
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("cache_cleanup_interval lock was poisoned - recovering");
                poisoned.into_inner()
            })
    }

    /// Set proactive cleanup interval.
    ///
    /// Value is clamped to configured min/max bounds.
    pub fn set_cache_cleanup_interval(&self, interval: Duration) {
        if let Ok(mut i) = self.cache_cleanup_interval.write() {
            *i = Self::clamp_cleanup_interval(interval);
        }
    }

    /// Get the configured global connection budget.
    pub fn get_max_connections(&self) -> Option<usize> {
        *self.max_connections.read().unwrap_or_else(|poisoned| {
            warn!("max_connections lock was poisoned - recovering");
            poisoned.into_inner()
        })
    }

    /// Set the configured global connection budget.
    ///
    /// This updates configuration for the next `initialize()` or explicit
    /// `rebalance_connections()` call. Existing pools are not rebuilt implicitly.
    pub fn set_max_connections(&self, max_connections: usize) {
        if let Ok(mut m) = self.max_connections.write() {
            *m = Some(max_connections);
        }
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
        let tracked_paths = self
            .db_paths
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("db_paths lock was poisoned - recovering");
                poisoned.into_inner()
            })
            .clone();
        self.initialize(tracked_paths).await
    }

    /// Get current performance statistics
    pub fn get_stats(&self) -> Result<PoolStatistics, DatabaseError> {
        let configured_budget = self.configured_connection_budget() as u64;
        let allocations_snapshot = self
            .pool_allocations
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("pool_allocations lock was poisoned - recovering");
                poisoned.into_inner()
            })
            .clone();
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

        Ok(PoolStatistics {
            total_queries: self.stat_total_queries.load(Ordering::Relaxed),
            cache_hits: self.stat_cache_hits.load(Ordering::Relaxed),
            cache_misses: self.stat_cache_misses.load(Ordering::Relaxed),
            total_connections: self.stat_total_connections.load(Ordering::Relaxed),
            active_connections: self.stat_active_connections.load(Ordering::Relaxed),
            cache_evictions: self.stat_cache_evictions.load(Ordering::Relaxed),
            cleanup_runs: self.stat_cleanup_runs.load(Ordering::Relaxed),
            cleanup_removed: self.stat_cleanup_removed.load(Ordering::Relaxed),
            configured_connection_budget: configured_budget,
            effective_connection_budget,
            active_pool_count,
            min_pool_allocation,
            max_pool_allocation,
            allocation_spread,
            stable_shape_selections: self.stat_stable_shape_selections.load(Ordering::Relaxed),
            stable_shape_padding_pairs: self
                .stat_stable_shape_padding_pairs
                .load(Ordering::Relaxed),
            stable_shape_bucket_8: self.stat_stable_shape_bucket_8.load(Ordering::Relaxed),
            stable_shape_bucket_16: self.stat_stable_shape_bucket_16.load(Ordering::Relaxed),
            stable_shape_bucket_32: self.stat_stable_shape_bucket_32.load(Ordering::Relaxed),
            stable_shape_bucket_64: self.stat_stable_shape_bucket_64.load(Ordering::Relaxed),
            stable_shape_bucket_128: self.stat_stable_shape_bucket_128.load(Ordering::Relaxed),
            stable_shape_bucket_256: self.stat_stable_shape_bucket_256.load(Ordering::Relaxed),
            stable_shape_bucket_512: self.stat_stable_shape_bucket_512.load(Ordering::Relaxed),
            stable_shape_bucket_1024: self.stat_stable_shape_bucket_1024.load(Ordering::Relaxed),
        })
    }

    /// Check if any database pools are available
    pub fn is_available(&self) -> bool {
        !self.pools.is_empty()
    }

    /// Get the current number of entries in the query cache
    pub fn cache_size(&self) -> usize {
        self.query_cache.len()
    }

    /// Close all connections and clear caches
    pub async fn close(&self) -> Result<(), DatabaseError> {
        let pool_count = self.pools.len();
        let cache_size = self.query_cache.len();

        // Capture current stats before closing for logging
        let active_before = self.stat_active_connections.load(Ordering::Relaxed);
        let total_queries = self.stat_total_queries.load(Ordering::Relaxed);

        info!(
            "Closing all database connections: {} pool(s), {} cached queries, {} active connection(s)",
            pool_count, cache_size, active_before
        );

        // Clear caches
        self.query_cache.clear();

        // Close all pools
        for entry in self.pools.iter() {
            let db_path = entry.key().clone();
            let pool = entry.value();
            pool.close().await;
            debug!("Closed connection pool for {:?}", db_path);
        }

        self.pools.clear();
        if let Ok(mut paths) = self.db_paths.write() {
            paths.clear();
        }
        if let Ok(mut allocations) = self.pool_allocations.write() {
            allocations.clear();
        }

        // Reset connection stats (queries stats preserved for debugging)
        self.stat_active_connections.store(0, Ordering::Relaxed);

        info!(
            "Database pool closed successfully. Total queries processed: {}",
            total_queries
        );

        Ok(())
    }

    /// Optimize database connections (VACUUM and ANALYZE)
    pub async fn optimize(&self) -> Result<(), DatabaseError> {
        info!("Optimizing database connections");

        for entry in self.pools.iter() {
            let db_path = entry.key().clone();
            let pool = entry.value();

            // Note: VACUUM cannot be run on read-only databases
            // We'll just run ANALYZE which is allowed in read-only mode
            match sqlx::query("ANALYZE").execute(pool).await {
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
        if Arc::strong_count(&self.pools) == 1 && !self.pools.is_empty() {
            let pool_count = self.pools.len();
            let active_connections = self.stat_active_connections.load(Ordering::Relaxed);

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
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    // =========================================================================
    // Test Helper Functions
    // =========================================================================

    /// Create a temporary SQLite database with test table and sample data.
    ///
    /// Returns the temp file handle (which keeps the file alive) and the path.
    async fn create_test_database(
        table_name: &str,
        entries: &[(&str, &str, &str)], // (formid, plugin, entry)
    ) -> Result<(NamedTempFile, PathBuf), DatabaseError> {
        let temp_file = NamedTempFile::with_suffix(".db").map_err(DatabaseError::IoError)?;
        let db_path = temp_file.path().to_path_buf();

        // Create database with test table
        let conn_str = format!("sqlite://{}?mode=rwc", db_path.display());
        let pool = SqlitePoolOptions::new()
            .max_connections(1)
            .connect(&conn_str)
            .await
            .map_err(|e| DatabaseError::OpenError(e.to_string()))?;

        // Create table
        let create_table_sql = format!(
            "CREATE TABLE IF NOT EXISTS {} (
                formid TEXT NOT NULL,
                plugin TEXT NOT NULL,
                entry TEXT NOT NULL,
                PRIMARY KEY (formid, plugin)
            )",
            table_name
        );
        sqlx::query(&create_table_sql)
            .execute(&pool)
            .await
            .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

        // Insert test data
        for (formid, plugin, entry) in entries {
            let insert_sql = format!(
                "INSERT OR REPLACE INTO {} (formid, plugin, entry) VALUES (?, ?, ?)",
                table_name
            );
            sqlx::query(&insert_sql)
                .bind(*formid)
                .bind(*plugin)
                .bind(*entry)
                .execute(&pool)
                .await
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
        }

        pool.close().await;
        Ok((temp_file, db_path))
    }

    // =========================================================================
    // Pool Lifecycle Tests
    // =========================================================================

    /// Test that Arc::strong_count correctly tracks clones of DatabasePool.
    ///
    /// This validates the Drop implementation's clone-safety logic:
    /// - When multiple clones exist, dropping one should not trigger the warning
    /// - Only when the last reference is dropped should the warning fire
    #[test]
    fn test_database_pool_clone_arc_count() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());

        // Initially, strong count should be 1
        assert_eq!(
            Arc::strong_count(&pool.pools),
            1,
            "Initial pool should have strong_count of 1"
        );

        // After cloning, strong count should be 2
        let clone1 = pool.clone();
        assert_eq!(
            Arc::strong_count(&pool.pools),
            2,
            "After cloning, strong_count should be 2"
        );

        // Both references point to the same Arc
        assert!(
            Arc::ptr_eq(&pool.pools, &clone1.pools),
            "Clones should share the same underlying Arc"
        );

        // After another clone, strong count should be 3
        let clone2 = pool.clone();
        assert_eq!(
            Arc::strong_count(&pool.pools),
            3,
            "After second clone, strong_count should be 3"
        );

        // Drop one clone - strong count should decrease to 2
        drop(clone1);
        assert_eq!(
            Arc::strong_count(&pool.pools),
            2,
            "After dropping one clone, strong_count should be 2"
        );

        // The warning condition should be false when other clones exist
        // (strong_count > 1, so condition is false regardless of pools.is_empty())
        assert!(
            Arc::strong_count(&pool.pools) > 1,
            "With remaining clones, strong_count should be > 1"
        );

        // Drop another clone - strong count should decrease to 1
        drop(clone2);
        assert_eq!(
            Arc::strong_count(&pool.pools),
            1,
            "After dropping all clones, strong_count should be 1"
        );
    }

    /// Test that the warning condition is correctly evaluated.
    ///
    /// The warning should only fire when:
    /// 1. This is the last Arc reference (strong_count == 1)
    /// 2. AND pools are not empty
    #[test]
    fn test_drop_warning_condition_logic() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());

        // With no pools initialized, the warning condition should be false
        // even when this is the last reference
        let should_warn_empty = Arc::strong_count(&pool.pools) == 1 && !pool.pools.is_empty();
        assert!(
            !should_warn_empty,
            "Should not warn when pools are empty (even if last reference)"
        );

        // Clone and verify warning condition is false for non-last references
        let clone = pool.clone();
        let should_warn_with_clone = Arc::strong_count(&pool.pools) == 1 && !pool.pools.is_empty();
        assert!(
            !should_warn_with_clone,
            "Should not warn when other clones exist"
        );

        // Drop the clone
        drop(clone);

        // Now it's the last reference, but pools are still empty
        let should_warn_last_empty = Arc::strong_count(&pool.pools) == 1 && !pool.pools.is_empty();
        assert!(
            !should_warn_last_empty,
            "Should not warn when pools are empty"
        );

        // Note: We can't easily test the case where pools are non-empty without
        // actually connecting to a database, but the logic is validated above.
    }

    /// Test pool creation with default max connections.
    #[test]
    fn test_pool_creation_default_connections() {
        let pool = DatabasePool::new(None, Duration::from_secs(300), "Fallout4".to_string());

        // Should use calculated max connections (based on CPU cores)
        let max_conn = pool.get_max_connections();
        assert!(max_conn.is_some(), "max_connections should be set");
        let value = max_conn.unwrap();
        assert!(
            (8..=64).contains(&value),
            "max_connections should be clamped between 8 and 64, got {}",
            value
        );
    }

    /// Test pool creation with custom max connections.
    #[test]
    fn test_pool_creation_custom_connections() {
        let pool = DatabasePool::new(Some(16), Duration::from_secs(600), "Skyrim".to_string());

        assert_eq!(pool.get_max_connections(), Some(16));
        assert_eq!(pool.get_game_table(), "Skyrim");
    }

    /// Test pool creation with in-memory cache initialization.
    #[test]
    fn test_pool_creation_cache_initialized() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());

        // Cache should be empty initially
        assert_eq!(pool.cache_size(), 0, "Cache should be empty on creation");
        assert!(
            !pool.is_available(),
            "Pool should have no connections initially"
        );
    }

    /// Test pool initialization with valid database file.
    #[tokio::test]
    async fn test_pool_initialization_with_file() {
        let table_name = "TestTable";
        let entries = [("12345678", "TestPlugin.esp", "Test Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        let result = pool.initialize(vec![db_path]).await;

        assert!(
            result.is_ok(),
            "Initialization should succeed: {:?}",
            result.err()
        );
        assert!(
            pool.is_available(),
            "Pool should be available after initialization"
        );
    }

    /// Test pool statistics tracking.
    #[tokio::test]
    async fn test_pool_statistics_tracking() {
        let table_name = "StatsTable";
        let entries = [("AABBCCDD", "Stats.esp", "Stats Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // Initial stats
        let stats = pool.get_stats().unwrap();
        assert_eq!(stats.total_queries, 0, "Initial queries should be 0");
        assert_eq!(stats.cache_hits, 0, "Initial cache hits should be 0");
        assert_eq!(stats.cache_misses, 0, "Initial cache misses should be 0");
        assert_eq!(stats.cache_evictions, 0, "Initial evictions should be 0");
        assert_eq!(stats.cleanup_runs, 0, "Initial cleanup runs should be 0");
        assert_eq!(
            stats.cleanup_removed, 0,
            "Initial cleanup removed should be 0"
        );

        // Perform a query
        let _ = pool.get_entry("AABBCCDD", "Stats.esp", None).await;

        // Stats should be updated
        let stats_after = pool.get_stats().unwrap();
        assert_eq!(stats_after.total_queries, 1, "Should have 1 query");
        assert_eq!(
            stats_after.cache_misses, 1,
            "First query should be a cache miss"
        );
        assert_eq!(stats_after.cache_evictions, 0);
        assert_eq!(stats_after.cleanup_runs, 0);
        assert_eq!(stats_after.cleanup_removed, 0);

        pool.close().await.unwrap();
    }

    /// Test pool close and cleanup.
    #[tokio::test]
    async fn test_pool_close_and_cleanup() {
        let table_name = "CloseTable";
        let entries = [("11111111", "Close.esp", "Close Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // Add something to cache
        let _ = pool.get_entry("11111111", "Close.esp", None).await;
        assert!(pool.cache_size() > 0, "Cache should have entries");

        // Close the pool
        let result = pool.close().await;
        assert!(result.is_ok(), "Close should succeed");
        assert!(
            !pool.is_available(),
            "Pool should not be available after close"
        );
        assert_eq!(pool.cache_size(), 0, "Cache should be cleared after close");
    }

    /// Test max connections recalculation.
    #[test]
    fn test_recalculate_max_connections() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());
        assert_eq!(pool.get_max_connections(), Some(4));

        pool.recalculate_max_connections();

        let new_max = pool.get_max_connections().unwrap();
        // Should be recalculated based on CPU cores (clamped 8-64)
        assert!(
            (8..=64).contains(&new_max),
            "Recalculated max should be clamped"
        );
    }

    /// Test set_max_connections updates the value.
    #[test]
    fn test_set_max_connections() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestGame".to_string());
        assert_eq!(pool.get_max_connections(), Some(4));

        pool.set_max_connections(32);
        assert_eq!(pool.get_max_connections(), Some(32));
    }

    /// Test global budget distribution with deterministic split.
    #[tokio::test]
    async fn test_global_budget_distribution_multi_db() {
        let table_name = "BudgetTable";
        let entries = [("BUDGET01", "Budget.esp", "Budget Entry")];
        let (_temp_file1, db_path1) = create_test_database(table_name, &entries).await.unwrap();
        let (_temp_file2, db_path2) = create_test_database(table_name, &entries).await.unwrap();
        let (_temp_file3, db_path3) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(8), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path1, db_path2, db_path3])
            .await
            .unwrap();

        let stats = pool.get_stats().unwrap();
        assert_eq!(stats.configured_connection_budget, 8);
        assert_eq!(stats.effective_connection_budget, 8);
        assert_eq!(stats.active_pool_count, 3);
        assert_eq!(stats.min_pool_allocation, 2);
        assert_eq!(stats.max_pool_allocation, 3);
        assert_eq!(stats.allocation_spread, 1);
    }

    /// Test low-budget clamp keeps allocations non-zero per active DB.
    #[tokio::test]
    async fn test_low_budget_clamp_distribution() {
        let table_name = "LowBudgetTable";
        let entries = [("LOWBUD01", "Budget.esp", "Budget Entry")];
        let (_temp_file1, db_path1) = create_test_database(table_name, &entries).await.unwrap();
        let (_temp_file2, db_path2) = create_test_database(table_name, &entries).await.unwrap();
        let (_temp_file3, db_path3) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(2), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path1, db_path2, db_path3])
            .await
            .unwrap();

        let stats = pool.get_stats().unwrap();
        assert_eq!(stats.configured_connection_budget, 2);
        assert_eq!(stats.effective_connection_budget, 3);
        assert_eq!(stats.active_pool_count, 3);
        assert_eq!(stats.min_pool_allocation, 1);
        assert_eq!(stats.max_pool_allocation, 1);
        assert_eq!(stats.allocation_spread, 0);
    }

    /// Test set_max_connections is config-only until explicit rebalance.
    #[tokio::test]
    async fn test_set_max_connections_requires_explicit_rebalance() {
        let table_name = "RebalanceTable";
        let entries = [("REBAL001", "Budget.esp", "Budget Entry")];
        let (_temp_file1, db_path1) = create_test_database(table_name, &entries).await.unwrap();
        let (_temp_file2, db_path2) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(6), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path1, db_path2]).await.unwrap();

        let before = pool.get_stats().unwrap();
        assert_eq!(before.effective_connection_budget, 6);
        assert_eq!(before.min_pool_allocation, 3);
        assert_eq!(before.max_pool_allocation, 3);

        pool.set_max_connections(10);
        let after_set_only = pool.get_stats().unwrap();
        assert_eq!(
            after_set_only.effective_connection_budget, 6,
            "set_max_connections should not immediately rebuild active pools"
        );
        assert_eq!(after_set_only.min_pool_allocation, 3);
        assert_eq!(after_set_only.max_pool_allocation, 3);

        pool.rebalance_connections().await.unwrap();
        let after_rebalance = pool.get_stats().unwrap();
        assert_eq!(after_rebalance.configured_connection_budget, 10);
        assert_eq!(after_rebalance.effective_connection_budget, 10);
        assert_eq!(after_rebalance.min_pool_allocation, 5);
        assert_eq!(after_rebalance.max_pool_allocation, 5);
    }

    // =========================================================================
    // Caching Tests
    // =========================================================================

    /// Test CacheEntry creation and expiration.
    #[test]
    fn test_cache_entry_creation() {
        let entry = CacheEntry::new("test_value".to_string(), Duration::from_secs(60));
        assert_eq!(entry.value, "test_value");
        assert!(!entry.is_expired(), "Fresh entry should not be expired");
    }

    /// Test CacheEntry expiration after TTL.
    #[test]
    fn test_cache_entry_expiration() {
        // Create entry with very short TTL
        let entry = CacheEntry::new("test_value".to_string(), Duration::from_millis(1));

        // Wait for expiration
        std::thread::sleep(Duration::from_millis(10));

        assert!(entry.is_expired(), "Entry should be expired after TTL");
    }

    /// Test CacheKey creation and hashing.
    #[test]
    fn test_cache_key_creation() {
        let key = CacheKey::new("Fallout4", "12345678", "TestMod.esp");

        assert_eq!(key.game_table, "Fallout4");
        assert_eq!(key.formid, "12345678");
        assert_eq!(key.plugin, "testmod.esp"); // Should be lowercase
    }

    /// Test CacheKey case-insensitive plugin matching.
    #[test]
    fn test_cache_key_case_insensitive_plugin() {
        let key1 = CacheKey::new("Fallout4", "12345678", "TestMod.ESP");
        let key2 = CacheKey::new("Fallout4", "12345678", "testmod.esp");
        let key3 = CacheKey::new("Fallout4", "12345678", "TESTMOD.ESP");

        // All should have same plugin (lowercase)
        assert_eq!(key1.plugin, key2.plugin);
        assert_eq!(key2.plugin, key3.plugin);

        // All should have same hash
        assert_eq!(key1.hash, key2.hash);
        assert_eq!(key2.hash, key3.hash);

        // Fully equivalent keys should compare equal
        assert_eq!(key1, key2);
        assert_eq!(key2, key3);
    }

    /// Test CacheKey distinctness for non-equivalent components.
    #[test]
    fn test_cache_key_distinct_components_are_not_equal() {
        let base = CacheKey::new("Fallout4", "12345678", "TestMod.esp");
        let different_table = CacheKey::new("Skyrim", "12345678", "TestMod.esp");
        let different_formid = CacheKey::new("Fallout4", "87654321", "TestMod.esp");
        let different_plugin = CacheKey::new("Fallout4", "12345678", "OtherMod.esp");

        assert_ne!(base, different_table);
        assert_ne!(base, different_formid);
        assert_ne!(base, different_plugin);
    }

    /// Test cache hit on second lookup.
    #[tokio::test]
    async fn test_cache_hit_on_second_lookup() {
        let table_name = "CacheHitTable";
        let entries = [("DEADBEEF", "CacheTest.esp", "Cache Test Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // First lookup - cache miss
        let result1 = pool
            .get_entry("DEADBEEF", "CacheTest.esp", None)
            .await
            .unwrap();
        assert_eq!(result1, Some("Cache Test Entry".to_string()));

        let stats1 = pool.get_stats().unwrap();
        assert_eq!(stats1.cache_misses, 1);
        assert_eq!(stats1.cache_hits, 0);

        // Second lookup - cache hit
        let result2 = pool
            .get_entry("DEADBEEF", "CacheTest.esp", None)
            .await
            .unwrap();
        assert_eq!(result2, Some("Cache Test Entry".to_string()));

        let stats2 = pool.get_stats().unwrap();
        assert_eq!(stats2.cache_hits, 1);

        pool.close().await.unwrap();
    }

    /// Verify equivalent hit/miss behavior between single and batch lookups.
    #[tokio::test]
    async fn test_single_and_batch_cache_hit_miss_parity() {
        let table_name = "SingleBatchParityTable";
        let entries = [("PARITY01", "ParityCase.esp", "Parity Value")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let single_pool =
            DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        single_pool.initialize(vec![db_path.clone()]).await.unwrap();
        assert_eq!(
            single_pool
                .get_entry("PARITY01", "ParityCase.esp", None)
                .await
                .unwrap(),
            Some("Parity Value".to_string())
        );
        assert_eq!(
            single_pool
                .get_entry("PARITY01", "PARITYCASE.ESP", None)
                .await
                .unwrap(),
            Some("Parity Value".to_string())
        );

        let single_stats = single_pool.get_stats().unwrap();
        assert_eq!(single_stats.cache_misses, 1);
        assert_eq!(single_stats.cache_hits, 1);
        single_pool.close().await.unwrap();

        let batch_pool =
            DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        batch_pool.initialize(vec![db_path]).await.unwrap();

        let first_batch = batch_pool
            .get_entries_batch(
                vec![("PARITY01".to_string(), "ParityCase.esp".to_string())],
                None,
                100,
            )
            .await
            .unwrap();
        assert_eq!(
            first_batch.get("PARITY01:ParityCase.esp"),
            Some(&"Parity Value".to_string())
        );

        let second_batch = batch_pool
            .get_entries_batch(
                vec![("PARITY01".to_string(), "PARITYCASE.ESP".to_string())],
                None,
                100,
            )
            .await
            .unwrap();
        assert_eq!(
            second_batch.get("PARITY01:PARITYCASE.ESP"),
            Some(&"Parity Value".to_string())
        );

        let batch_stats = batch_pool.get_stats().unwrap();
        assert_eq!(batch_stats.cache_misses, 1);
        assert_eq!(batch_stats.cache_hits, 1);
        batch_pool.close().await.unwrap();
    }

    /// Test cache clear with expired_only=false.
    #[tokio::test]
    async fn test_cache_clear_all() {
        let table_name = "ClearAllTable";
        let entries = [
            ("00000001", "Test1.esp", "Entry 1"),
            ("00000002", "Test2.esp", "Entry 2"),
        ];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // Populate cache
        let _ = pool.get_entry("00000001", "Test1.esp", None).await;
        let _ = pool.get_entry("00000002", "Test2.esp", None).await;
        assert!(pool.cache_size() >= 2, "Cache should have entries");

        // Clear all
        let removed = pool.clear_cache(false);
        assert!(removed >= 2, "Should have removed at least 2 entries");
        assert_eq!(pool.cache_size(), 0, "Cache should be empty");

        pool.close().await.unwrap();
    }

    /// Test cache clear with expired_only=true.
    #[tokio::test]
    async fn test_cache_clear_expired_only() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), "TestTable".to_string());

        // Manually insert entries with different TTLs
        let expired_key = CacheKey::new("TestTable", "expired", "plugin");
        let fresh_key = CacheKey::new("TestTable", "fresh", "plugin");

        pool.query_cache.insert(
            expired_key,
            CacheEntry::new("expired_value".to_string(), Duration::from_millis(1)),
        );
        pool.query_cache.insert(
            fresh_key.clone(),
            CacheEntry::new("fresh_value".to_string(), Duration::from_secs(300)),
        );

        // Wait for expiration
        std::thread::sleep(Duration::from_millis(10));

        assert_eq!(pool.cache_size(), 2, "Should have 2 entries before clear");

        // Clear expired only
        let removed = pool.clear_cache(true);
        assert_eq!(removed, 1, "Should have removed 1 expired entry");
        assert_eq!(pool.cache_size(), 1, "Should have 1 entry remaining");

        // Verify fresh entry is still there
        assert!(
            pool.query_cache.contains_key(&fresh_key),
            "Fresh entry should remain"
        );
    }

    /// Test set_cache_ttl updates TTL for new entries.
    #[tokio::test]
    async fn test_set_cache_ttl() {
        let table_name = "TtlTable";
        let entries = [("TTLTEST1", "Ttl.esp", "TTL Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // Change TTL to very short
        pool.set_cache_ttl(Duration::from_millis(10));

        // Lookup to populate cache
        let _ = pool.get_entry("TTLTEST1", "Ttl.esp", None).await;
        assert_eq!(pool.cache_size(), 1);

        // Wait for expiration
        std::thread::sleep(Duration::from_millis(20));

        // Clear expired
        let removed = pool.clear_cache(true);
        assert_eq!(removed, 1, "Entry should have expired with new TTL");

        pool.close().await.unwrap();
    }

    /// Test deterministic eviction order when cache exceeds capacity.
    #[test]
    fn test_cache_eviction_deterministic_oldest_first() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), "TestTable".to_string());
        pool.set_cache_capacity(2);

        pool.insert_with_eviction(
            CacheKey::new("TestTable", "00000001", "plugin.esp"),
            "Entry 1".to_string(),
            Duration::from_secs(300),
        );
        pool.insert_with_eviction(
            CacheKey::new("TestTable", "00000002", "plugin.esp"),
            "Entry 2".to_string(),
            Duration::from_secs(300),
        );
        pool.insert_with_eviction(
            CacheKey::new("TestTable", "00000003", "plugin.esp"),
            "Entry 3".to_string(),
            Duration::from_secs(300),
        );

        assert_eq!(
            pool.cache_size(),
            2,
            "Cache size must respect configured cap"
        );
        assert!(
            !pool
                .query_cache
                .contains_key(&CacheKey::new("TestTable", "00000001", "plugin.esp")),
            "Oldest key should be evicted first"
        );
        assert!(pool.query_cache.contains_key(&CacheKey::new(
            "TestTable",
            "00000002",
            "plugin.esp"
        )));
        assert!(pool.query_cache.contains_key(&CacheKey::new(
            "TestTable",
            "00000003",
            "plugin.esp"
        )));

        let stats = pool.get_stats().unwrap();
        assert_eq!(stats.cache_evictions, 1, "Should record one eviction");
    }

    /// Test capacity bound enforcement under sustained inserts.
    #[tokio::test]
    async fn test_cache_capacity_bound_under_sustained_inserts() {
        let table_name = "CapacityTable";
        let entries: Vec<_> = (0..20)
            .map(|i| {
                (
                    format!("CAP{:06}", i),
                    "Cap.esp".to_string(),
                    format!("Entry {}", i),
                )
            })
            .collect();
        let entries_refs: Vec<(&str, &str, &str)> = entries
            .iter()
            .map(|(a, b, c)| (a.as_str(), b.as_str(), c.as_str()))
            .collect();
        let (_temp_file, db_path) = create_test_database(table_name, &entries_refs)
            .await
            .unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), table_name.to_string());
        pool.set_cache_capacity(5);
        pool.initialize(vec![db_path]).await.unwrap();

        for (formid, plugin, _) in &entries {
            let _ = pool.get_entry(formid, plugin, None).await.unwrap();
        }

        assert!(
            pool.cache_size() <= 5,
            "Cache should stay within configured capacity"
        );

        let stats = pool.get_stats().unwrap();
        assert!(
            stats.cache_evictions >= 15,
            "Eviction count should increase under sustained inserts"
        );

        pool.close().await.unwrap();
    }

    /// Test hybrid proactive cleanup trigger uses threshold and interval gate.
    #[test]
    fn test_hybrid_proactive_cleanup_threshold_and_interval() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(300), "TestTable".to_string());
        pool.set_cache_cleanup_threshold(3);
        pool.set_cache_cleanup_interval(Duration::from_secs(1));

        pool.query_cache.insert(
            CacheKey::new("TestTable", "expired1", "plugin"),
            CacheEntry::new("expired1".to_string(), Duration::from_millis(1)),
        );
        pool.query_cache.insert(
            CacheKey::new("TestTable", "expired2", "plugin"),
            CacheEntry::new("expired2".to_string(), Duration::from_millis(1)),
        );
        std::thread::sleep(Duration::from_millis(10));

        // Below threshold: should not run.
        pool.maybe_run_proactive_cleanup(2);
        let stats_before = pool.get_stats().unwrap();
        assert_eq!(stats_before.cleanup_runs, 0);

        // Meets threshold but interval gate has not elapsed yet.
        pool.maybe_run_proactive_cleanup(1);
        let stats_interval_blocked = pool.get_stats().unwrap();
        assert_eq!(stats_interval_blocked.cleanup_runs, 0);

        // Once interval elapsed, cleanup should execute and remove expired entries.
        std::thread::sleep(Duration::from_millis(1_100));
        pool.maybe_run_proactive_cleanup(1);
        let stats_after = pool.get_stats().unwrap();
        assert_eq!(stats_after.cleanup_runs, 1);
        assert!(
            stats_after.cleanup_removed >= 2,
            "Cleanup should remove expired entries"
        );
    }

    // =========================================================================
    // Query Tests
    // =========================================================================

    /// Test get_entry returns correct value for existing FormID.
    #[tokio::test]
    async fn test_formid_lookup_hit() {
        let table_name = "LookupTable";
        let entries = [(
            "ABCD1234",
            "TestMod.esp",
            "This is a test entry for FormID lookup",
        )];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        let result = pool
            .get_entry("ABCD1234", "TestMod.esp", None)
            .await
            .unwrap();
        assert_eq!(
            result,
            Some("This is a test entry for FormID lookup".to_string())
        );

        pool.close().await.unwrap();
    }

    /// Test get_entry returns None for non-existent FormID.
    #[tokio::test]
    async fn test_formid_lookup_miss() {
        let table_name = "MissTable";
        let entries = [("11111111", "Existing.esp", "Existing Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        let result = pool
            .get_entry("99999999", "NonExistent.esp", None)
            .await
            .unwrap();
        assert_eq!(result, None);

        pool.close().await.unwrap();
    }

    /// Test get_entry with table override.
    #[tokio::test]
    async fn test_get_entry_with_table_override() {
        let table_name = "OverrideTable";
        let entries = [("OVERRIDE1", "Override.esp", "Override Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        // Create pool with different default table
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "WrongTable".to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // Use table override to query correct table
        let result = pool
            .get_entry("OVERRIDE1", "Override.esp", Some(table_name))
            .await
            .unwrap();
        assert_eq!(result, Some("Override Entry".to_string()));

        pool.close().await.unwrap();
    }

    /// Test batch FormID query.
    #[tokio::test]
    async fn test_batch_formid_query() {
        let table_name = "BatchTable";
        let entries = [
            ("BATCH001", "Batch.esp", "Entry 1"),
            ("BATCH002", "Batch.esp", "Entry 2"),
            ("BATCH003", "Batch.esp", "Entry 3"),
            ("BATCH004", "OtherMod.esp", "Entry 4"),
        ];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        let pairs = vec![
            ("BATCH001".to_string(), "Batch.esp".to_string()),
            ("BATCH002".to_string(), "Batch.esp".to_string()),
            ("BATCH003".to_string(), "Batch.esp".to_string()),
            ("BATCH004".to_string(), "OtherMod.esp".to_string()),
            ("NOTEXIST".to_string(), "Missing.esp".to_string()),
        ];

        let results = pool.get_entries_batch(pairs, None, 100).await.unwrap();

        assert_eq!(results.len(), 4, "Should find 4 entries");
        assert_eq!(
            results.get("BATCH001:Batch.esp"),
            Some(&"Entry 1".to_string())
        );
        assert_eq!(
            results.get("BATCH002:Batch.esp"),
            Some(&"Entry 2".to_string())
        );
        assert_eq!(
            results.get("BATCH003:Batch.esp"),
            Some(&"Entry 3".to_string())
        );
        assert_eq!(
            results.get("BATCH004:OtherMod.esp"),
            Some(&"Entry 4".to_string())
        );
        assert_eq!(results.get("NOTEXIST:Missing.esp"), None);

        pool.close().await.unwrap();
    }

    /// Test batch query with case-insensitive plugin matching.
    #[tokio::test]
    async fn test_batch_query_case_insensitive_plugin() {
        let table_name = "CaseTable";
        let entries = [("CASE0001", "TestMod.esp", "Case Test Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // Query with different case
        let pairs = vec![("CASE0001".to_string(), "TESTMOD.ESP".to_string())];

        let results = pool.get_entries_batch(pairs, None, 100).await.unwrap();

        // Should find entry despite case difference
        assert_eq!(results.len(), 1, "Should find entry with different case");
        assert_eq!(
            results.get("CASE0001:TESTMOD.ESP"),
            Some(&"Case Test Entry".to_string())
        );

        pool.close().await.unwrap();
    }

    /// Test batch query with empty input.
    #[tokio::test]
    async fn test_batch_query_empty_input() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestTable".to_string());

        let results = pool.get_entries_batch(vec![], None, 100).await.unwrap();
        assert!(
            results.is_empty(),
            "Empty input should return empty results"
        );
    }

    /// Test batch query adaptive batch sizing.
    #[tokio::test]
    async fn test_batch_query_adaptive_sizing() {
        let table_name = "AdaptiveTable";
        let mut entries = Vec::new();
        for i in 0..10 {
            entries.push((
                format!("ADAPT{:03}", i),
                "Adaptive.esp".to_string(),
                format!("Entry {}", i),
            ));
        }

        let entries_refs: Vec<(&str, &str, &str)> = entries
            .iter()
            .map(|(a, b, c)| (a.as_str(), b.as_str(), c.as_str()))
            .collect();
        let (_temp_file, db_path) = create_test_database(table_name, &entries_refs)
            .await
            .unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // Small batch - should use adaptive sizing
        let pairs: Vec<(String, String)> = entries
            .iter()
            .map(|(f, p, _)| (f.clone(), p.clone()))
            .collect();

        let results = pool.get_entries_batch(pairs, None, 100).await.unwrap();
        assert_eq!(results.len(), 10, "Should find all 10 entries");

        pool.close().await.unwrap();
    }

    /// Test stable-shape padding for partial/final chunks.
    #[tokio::test]
    async fn test_batch_query_partial_final_chunk_padding_stats() {
        let table_name = "StablePaddingTable";
        let entries: Vec<_> = (0..17)
            .map(|i| {
                (
                    format!("PAD{:04}", i),
                    "Stable.esp".to_string(),
                    format!("Stable Entry {}", i),
                )
            })
            .collect();
        let entries_refs: Vec<(&str, &str, &str)> = entries
            .iter()
            .map(|(a, b, c)| (a.as_str(), b.as_str(), c.as_str()))
            .collect();
        let (_temp_file, db_path) = create_test_database(table_name, &entries_refs)
            .await
            .unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        let pairs: Vec<(String, String)> = entries
            .iter()
            .map(|(formid, plugin, _)| (formid.clone(), plugin.clone()))
            .collect();
        let results = pool.get_entries_batch(pairs, None, 10).await.unwrap();
        assert_eq!(results.len(), 17, "all entries should be returned");

        let stats = pool.get_stats().unwrap();
        assert_eq!(stats.stable_shape_selections, 2);
        assert_eq!(
            stats.stable_shape_bucket_16, 1,
            "first 10-item chunk -> 16 bucket"
        );
        assert_eq!(
            stats.stable_shape_bucket_8, 1,
            "final 7-item chunk -> 8 bucket"
        );
        assert_eq!(
            stats.stable_shape_padding_pairs, 7,
            "10->16 pads 6 plus 7->8 pads 1"
        );

        pool.close().await.unwrap();
    }

    /// Test mixed hit/miss mapping preserves caller-visible output keys.
    #[tokio::test]
    async fn test_batch_query_mixed_hit_miss_preserves_output_keys() {
        let table_name = "MixedMappingTable";
        let entries = [("MIX0001", "Mix.esp", "Mixed Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        let pairs = vec![
            ("MIX0001".to_string(), "MIX.ESP".to_string()),
            ("MIX0001".to_string(), "mix.esp".to_string()),
            ("MISSING".to_string(), "Mix.esp".to_string()),
        ];
        let results = pool.get_entries_batch(pairs, None, 10).await.unwrap();

        assert_eq!(results.len(), 2, "only hit keys should be present");
        assert_eq!(
            results.get("MIX0001:MIX.ESP"),
            Some(&"Mixed Entry".to_string())
        );
        assert_eq!(
            results.get("MIX0001:mix.esp"),
            Some(&"Mixed Entry".to_string())
        );
        assert!(
            !results.contains_key("MISSING:Mix.esp"),
            "miss key should remain absent"
        );

        pool.close().await.unwrap();
    }

    /// Test UNION ALL query builder.
    #[test]
    fn test_build_union_all_query() {
        // Empty batch
        let query_empty = DatabasePool::build_union_all_query("TestTable", 0);
        assert!(
            query_empty.is_empty(),
            "Empty batch should produce empty query"
        );

        // Single item
        let query_single = DatabasePool::build_union_all_query("Fallout4", 1);
        assert!(query_single.contains("SELECT formid, plugin, entry FROM Fallout4"));
        assert!(
            !query_single.contains("UNION ALL"),
            "Single item should not have UNION ALL"
        );

        // Multiple items
        let query_multi = DatabasePool::build_union_all_query("Skyrim", 3);
        let union_count = query_multi.matches("UNION ALL").count();
        assert_eq!(union_count, 2, "3 items should have 2 UNION ALL clauses");
        assert!(query_multi.contains("SELECT formid, plugin, entry FROM Skyrim"));
    }

    #[test]
    fn test_select_stable_bucket_len_boundaries() {
        assert_eq!(DatabasePool::select_stable_bucket_len(0), 0);
        assert_eq!(DatabasePool::select_stable_bucket_len(7), 8);
        assert_eq!(DatabasePool::select_stable_bucket_len(8), 8);
        assert_eq!(DatabasePool::select_stable_bucket_len(9), 16);
        assert_eq!(DatabasePool::select_stable_bucket_len(15), 16);
        assert_eq!(DatabasePool::select_stable_bucket_len(16), 16);
        assert_eq!(DatabasePool::select_stable_bucket_len(17), 32);
        assert_eq!(DatabasePool::select_stable_bucket_len(31), 32);
        assert_eq!(DatabasePool::select_stable_bucket_len(32), 32);
        assert_eq!(DatabasePool::select_stable_bucket_len(33), 64);
        assert_eq!(DatabasePool::select_stable_bucket_len(63), 64);
        assert_eq!(DatabasePool::select_stable_bucket_len(64), 64);
        assert_eq!(DatabasePool::select_stable_bucket_len(65), 128);
        assert_eq!(DatabasePool::select_stable_bucket_len(127), 128);
        assert_eq!(DatabasePool::select_stable_bucket_len(128), 128);
        assert_eq!(DatabasePool::select_stable_bucket_len(129), 256);
        assert_eq!(DatabasePool::select_stable_bucket_len(255), 256);
        assert_eq!(DatabasePool::select_stable_bucket_len(256), 256);
        assert_eq!(DatabasePool::select_stable_bucket_len(257), 512);
        assert_eq!(DatabasePool::select_stable_bucket_len(511), 512);
        assert_eq!(DatabasePool::select_stable_bucket_len(512), 512);
        assert_eq!(DatabasePool::select_stable_bucket_len(513), 1024);
        assert_eq!(DatabasePool::select_stable_bucket_len(1023), 1024);
        assert_eq!(DatabasePool::select_stable_bucket_len(1024), 1024);
        assert_eq!(DatabasePool::select_stable_bucket_len(1025), 1024);
    }

    #[test]
    fn test_pad_batch_to_bucket_partial_chunk() {
        let batch = vec![
            (
                "PAD0001".to_string(),
                "Pad.esp".to_string(),
                "pad.esp".to_string(),
            ),
            (
                "PAD0002".to_string(),
                "Pad.esp".to_string(),
                "pad.esp".to_string(),
            ),
            (
                "PAD0003".to_string(),
                "Pad.esp".to_string(),
                "pad.esp".to_string(),
            ),
        ];

        let padded = DatabasePool::pad_batch_to_bucket(&batch, 8);
        assert_eq!(padded.len(), 8);
        assert_eq!(padded[0], batch[0]);
        assert_eq!(padded[1], batch[1]);
        assert_eq!(padded[2], batch[2]);
        assert_eq!(
            padded.last(),
            Some(&batch[2]),
            "Padding should duplicate the last real pair"
        );
    }

    #[test]
    fn test_query_template_reuse_by_bucket_and_table() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestTable".to_string());
        let first = pool.get_or_build_stable_query_template("Fallout4", 16);
        let second = pool.get_or_build_stable_query_template("Fallout4", 16);
        let third = pool.get_or_build_stable_query_template("Skyrim", 16);

        assert_eq!(first, second, "same table + bucket should reuse query text");
        assert_ne!(
            first, third,
            "different table should produce different query text"
        );
        assert_eq!(
            pool.query_template_cache.len(),
            2,
            "cache should contain one template per (table, bucket)"
        );
    }

    // =========================================================================
    // Error Handling Tests
    // =========================================================================

    /// Test initialization with missing database file.
    #[tokio::test]
    async fn test_init_missing_database_file() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestTable".to_string());
        let result = pool
            .initialize(vec![PathBuf::from("/nonexistent/path/database.db")])
            .await;

        // Should succeed but with no pools added (missing file is warned, not errored)
        assert!(result.is_ok(), "Should not error on missing file");
        assert!(
            !pool.is_available(),
            "Pool should not be available with missing file"
        );
    }

    /// Test get_entry on uninitialized pool.
    #[tokio::test]
    async fn test_query_on_uninitialized_pool() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestTable".to_string());

        // Query without initialization
        let result = pool.get_entry("12345678", "Test.esp", None).await;

        // Should return Ok(None) - no pools to query
        assert!(result.is_ok(), "Should not error on uninitialized pool");
        assert_eq!(result.unwrap(), None, "Should return None");
    }

    /// Test query after pool close.
    #[tokio::test]
    async fn test_query_on_closed_pool() {
        let table_name = "ClosedTable";
        let entries = [("CLOSED01", "Closed.esp", "Closed Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // Close the pool
        pool.close().await.unwrap();

        // Query after close - should return None (no pools available)
        let result = pool.get_entry("CLOSED01", "Closed.esp", None).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), None);
    }

    // =========================================================================
    // Game Table Tests
    // =========================================================================

    /// Test set_game_table and get_game_table.
    #[test]
    fn test_set_get_game_table() {
        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "Fallout4".to_string());
        assert_eq!(pool.get_game_table(), "Fallout4");

        pool.set_game_table("Skyrim");
        assert_eq!(pool.get_game_table(), "Skyrim");

        pool.set_game_table("FalloutNewVegas");
        assert_eq!(pool.get_game_table(), "FalloutNewVegas");
    }

    // =========================================================================
    // Database Optimization Tests
    // =========================================================================

    /// Test optimize on database.
    #[tokio::test]
    async fn test_database_optimize() {
        let table_name = "OptTable";
        let entries = [("OPT00001", "Optimize.esp", "Optimize Entry")];
        let (_temp_file, db_path) = create_test_database(table_name, &entries).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path]).await.unwrap();

        // Optimize should succeed (runs ANALYZE)
        let result = pool.optimize().await;
        assert!(
            result.is_ok(),
            "Optimize should succeed: {:?}",
            result.err()
        );

        pool.close().await.unwrap();
    }

    // =========================================================================
    // TTL Constants Tests
    // =========================================================================

    /// Test TTL constant values.
    #[test]
    fn test_ttl_constants() {
        assert_eq!(
            DEFAULT_CACHE_TTL_SECS, 300,
            "Default TTL should be 5 minutes"
        );
        assert_eq!(BATCH_CACHE_TTL_SECS, 1800, "Batch TTL should be 30 minutes");
        assert_eq!(MAX_CACHE_TTL_SECS, 3600, "Max TTL should be 60 minutes");
        assert_eq!(DEFAULT_QUERY_CACHE_CAPACITY, 10_000);
        assert_eq!(MIN_QUERY_CACHE_CAPACITY, 1);
        assert_eq!(DEFAULT_CACHE_CLEANUP_OP_THRESHOLD, 256);
        assert_eq!(DEFAULT_CACHE_CLEANUP_INTERVAL_SECS, 5);

        // Verify ordering (compile-time assertions)
        const _: () = assert!(DEFAULT_CACHE_TTL_SECS < BATCH_CACHE_TTL_SECS);
        const _: () = assert!(BATCH_CACHE_TTL_SECS < MAX_CACHE_TTL_SECS);
        const _: () = assert!(MIN_QUERY_CACHE_CAPACITY < DEFAULT_QUERY_CACHE_CAPACITY);
        const _: () = assert!(DEFAULT_QUERY_CACHE_CAPACITY < MAX_QUERY_CACHE_CAPACITY);
        const _: () = assert!(MIN_CACHE_CLEANUP_OP_THRESHOLD < DEFAULT_CACHE_CLEANUP_OP_THRESHOLD);
        const _: () = assert!(DEFAULT_CACHE_CLEANUP_OP_THRESHOLD < MAX_CACHE_CLEANUP_OP_THRESHOLD);
        const _: () =
            assert!(MIN_CACHE_CLEANUP_INTERVAL_SECS < DEFAULT_CACHE_CLEANUP_INTERVAL_SECS);
        const _: () =
            assert!(DEFAULT_CACHE_CLEANUP_INTERVAL_SECS < MAX_CACHE_CLEANUP_INTERVAL_SECS);
    }

    // =========================================================================
    // Error Type Tests
    // =========================================================================

    /// Test DatabaseError variants.
    #[test]
    fn test_database_error_display() {
        let open_err = DatabaseError::OpenError("connection failed".to_string());
        assert!(open_err.to_string().contains("Failed to open database"));

        let query_err = DatabaseError::QueryError("syntax error".to_string());
        assert!(query_err.to_string().contains("Query execution failed"));

        let not_found = DatabaseError::NotFound("/path/to/db.sqlite".to_string());
        assert!(not_found.to_string().contains("Database file not found"));
    }

    // =========================================================================
    // PoolStatistics Tests
    // =========================================================================

    /// Test PoolStatistics default values.
    #[test]
    fn test_pool_statistics_default() {
        let stats = PoolStatistics::default();
        assert_eq!(stats.total_queries, 0);
        assert_eq!(stats.cache_hits, 0);
        assert_eq!(stats.cache_misses, 0);
        assert_eq!(stats.total_connections, 0);
        assert_eq!(stats.active_connections, 0);
        assert_eq!(stats.cache_evictions, 0);
        assert_eq!(stats.cleanup_runs, 0);
        assert_eq!(stats.cleanup_removed, 0);
        assert_eq!(stats.configured_connection_budget, 0);
        assert_eq!(stats.effective_connection_budget, 0);
        assert_eq!(stats.active_pool_count, 0);
        assert_eq!(stats.min_pool_allocation, 0);
        assert_eq!(stats.max_pool_allocation, 0);
        assert_eq!(stats.allocation_spread, 0);
        assert_eq!(stats.stable_shape_selections, 0);
        assert_eq!(stats.stable_shape_padding_pairs, 0);
        assert_eq!(stats.stable_shape_bucket_8, 0);
        assert_eq!(stats.stable_shape_bucket_16, 0);
        assert_eq!(stats.stable_shape_bucket_32, 0);
        assert_eq!(stats.stable_shape_bucket_64, 0);
        assert_eq!(stats.stable_shape_bucket_128, 0);
        assert_eq!(stats.stable_shape_bucket_256, 0);
        assert_eq!(stats.stable_shape_bucket_512, 0);
        assert_eq!(stats.stable_shape_bucket_1024, 0);
    }

    /// Test PoolStatistics clone.
    #[test]
    fn test_pool_statistics_clone() {
        let stats = PoolStatistics {
            total_queries: 100,
            cache_hits: 75,
            cache_evictions: 2,
            ..Default::default()
        };

        let cloned = stats.clone();
        assert_eq!(cloned.total_queries, 100);
        assert_eq!(cloned.cache_hits, 75);
        assert_eq!(cloned.cache_evictions, 2);
    }

    // =========================================================================
    // Multi-Database Tests
    // =========================================================================

    /// Test querying across multiple database files.
    #[tokio::test]
    async fn test_multi_database_query() {
        let table_name = "MultiTable";

        // Create first database with some entries
        let entries1 = [
            ("MULTI001", "Multi.esp", "Entry from DB1"),
            ("MULTI002", "Multi.esp", "Entry 2 from DB1"),
        ];
        let (_temp_file1, db_path1) = create_test_database(table_name, &entries1).await.unwrap();

        // Create second database with different entries
        let entries2 = [
            ("MULTI003", "Multi.esp", "Entry from DB2"),
            ("MULTI004", "Multi.esp", "Entry 2 from DB2"),
        ];
        let (_temp_file2, db_path2) = create_test_database(table_name, &entries2).await.unwrap();

        let pool = DatabasePool::new(Some(4), Duration::from_secs(60), table_name.to_string());
        pool.initialize(vec![db_path1, db_path2]).await.unwrap();

        // Should find entries from both databases
        let result1 = pool.get_entry("MULTI001", "Multi.esp", None).await.unwrap();
        assert_eq!(result1, Some("Entry from DB1".to_string()));

        let result2 = pool.get_entry("MULTI003", "Multi.esp", None).await.unwrap();
        assert_eq!(result2, Some("Entry from DB2".to_string()));

        pool.close().await.unwrap();
    }
}
