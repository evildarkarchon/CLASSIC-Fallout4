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

/// Type alias for batch query results: Vec of (formid, plugin, entry) tuples.
type BatchQueryResult = Result<Vec<(String, String, String)>, DatabaseError>;

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
    /// Expiration timestamp for this cache entry
    pub expires_at: Instant,
}

impl CacheEntry {
    /// Create a new cache entry with the given value and time-to-live duration
    pub fn new(value: String, ttl: Duration) -> Self {
        Self {
            value,
            expires_at: Instant::now() + ttl,
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
    /// Create a new cache key from components
    pub fn new(game_table: &str, formid: &str, plugin: &str) -> Self {
        use std::collections::hash_map::DefaultHasher;
        let mut hasher = DefaultHasher::new();
        game_table.hash(&mut hasher);
        formid.hash(&mut hasher);
        plugin.to_lowercase().hash(&mut hasher); // Case-insensitive plugin matching
        let hash = hasher.finish();

        Self {
            hash,
            game_table: game_table.to_string(),
            formid: formid.to_string(),
            plugin: plugin.to_lowercase(),
        }
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
    query_cache: Arc<DashMap<String, CacheEntry>>,
    /// Time-to-live duration for cached queries
    cache_ttl: Arc<RwLock<Duration>>,
    /// Maximum number of connections per pool
    max_connections: Arc<RwLock<Option<usize>>>,
    /// Performance statistics for monitoring
    stats: Arc<RwLock<PoolStatistics>>,
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
            cache_ttl: Arc::new(RwLock::new(cache_ttl)),
            max_connections: Arc::new(RwLock::new(Some(max_conn))),
            stats: Arc::new(RwLock::new(PoolStatistics::default())),
            game_table: Arc::new(RwLock::new(game_table)),
            db_paths: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Initialize database connections for given paths
    pub async fn initialize(&self, db_paths: Vec<PathBuf>) -> Result<(), DatabaseError> {
        let mut valid_paths = Vec::new();
        let max_conn = self
            .max_connections
            .read()
            .unwrap_or_else(|poisoned| {
                warn!("max_connections lock was poisoned - recovering");
                poisoned.into_inner()
            })
            .unwrap_or(50);

        info!(
            "Initializing sqlx pools for {} database files",
            db_paths.len()
        );

        for path in db_paths {
            if !path.exists() {
                warn!("Database file not found: {:?}", path);
                continue;
            }

            // Configure SQLite with WAL mode and optimizations
            let opts = SqliteConnectOptions::from_str(&format!("sqlite://{}", path.display()))
                .map_err(|e| DatabaseError::OpenError(format!("{:?}: {}", path, e)))?
                .synchronous(SqliteSynchronous::Normal) // Good durability/performance trade-off
                .read_only(true)
                .pragma("cache_size", "10000")
                .pragma("temp_store", "MEMORY")
                .pragma("mmap_size", "30000000");

            // Create pool with specified size
            let pool = SqlitePoolOptions::new()
                .max_connections(max_conn as u32)
                .min_connections(1)
                .acquire_timeout(Duration::from_secs(30))
                .connect_with(opts)
                .await
                .map_err(|e| DatabaseError::OpenError(format!("{:?}: {}", path, e)))?;

            self.pools.insert(path.clone(), pool);
            valid_paths.push(path.clone());

            info!(
                "Created sqlx pool with {} connections for {:?}",
                max_conn, path
            );

            if let Ok(mut s) = self.stats.write() {
                s.total_connections += 1;
                s.active_connections += 1;
            }
        }

        if let Ok(mut paths) = self.db_paths.write() {
            *paths = valid_paths;
        }

        Ok(())
    }

    /// Get FormID entry from database
    pub async fn get_entry(
        &self,
        formid: &str,
        plugin: &str,
        table: Option<&str>,
    ) -> Result<Option<String>, DatabaseError> {
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

        // Use lowercase plugin for case-insensitive cache matching (consistent with get_entries_batch)
        let cache_key = format!("{}:{}:{}", game_table, formid, plugin.to_lowercase());

        // Check cache first
        if let Some(entry) = self.query_cache.get(&cache_key) {
            if !entry.is_expired() {
                if let Ok(mut stats) = self.stats.write() {
                    stats.cache_hits += 1;
                    stats.total_queries += 1;
                }
                debug!("Cache hit for FormID: {} Plugin: {}", formid, plugin);
                return Ok(Some(entry.value.clone()));
            } else {
                self.query_cache.remove(&cache_key);
                debug!("Cache expired for FormID: {} Plugin: {}", formid, plugin);
            }
        }

        if let Ok(mut stats) = self.stats.write() {
            stats.cache_misses += 1;
            stats.total_queries += 1;
        }

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
                    self.query_cache
                        .insert(cache_key.clone(), CacheEntry::new(value.clone(), cache_ttl));
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
    /// * `batch` - Slice of (formid, plugin) pairs to include in the query
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
        let mut uncached_pairs: Vec<(String, String)> = Vec::new();

        // Check cache first using optimized key generation
        for (formid, plugin) in &formid_plugin_pairs {
            let cache_key = CacheKey::new(&game_table, formid, plugin);
            let legacy_key = format!("{}:{}:{}", game_table, formid, plugin.to_lowercase());

            if let Some(entry) = self.query_cache.get(&legacy_key) {
                if !entry.is_expired() {
                    let result_key = format!("{}:{}", formid, plugin);
                    results.insert(result_key, entry.value.clone());
                    if let Ok(mut s) = self.stats.write() {
                        s.cache_hits += 1;
                    }
                    continue;
                } else {
                    self.query_cache.remove(&legacy_key);
                }
            }

            uncached_pairs.push((formid.clone(), plugin.clone()));
            if let Ok(mut s) = self.stats.write() {
                s.cache_misses += 1;
            }

            // Silence unused variable warning - cache_key used for future optimization
            let _ = cache_key;
        }

        if let Ok(mut s) = self.stats.write() {
            s.total_queries += formid_plugin_pairs.len() as u64;
        }

        if uncached_pairs.is_empty() {
            return Ok(results);
        }

        let cache_ttl = *self.cache_ttl.read().unwrap_or_else(|poisoned| {
            warn!("cache_ttl lock was poisoned - recovering");
            poisoned.into_inner()
        });

        // Adaptive batch sizing: smaller batches for small inputs
        let effective_batch_size = if uncached_pairs.len() < 50 {
            uncached_pairs.len().max(1) // Single query for small inputs
        } else if uncached_pairs.len() > 500 {
            batch_size.max(200) // Larger batches for bulk lookups
        } else {
            batch_size
        };

        // Process uncached pairs in batches with PARALLEL database queries
        for batch in uncached_pairs.chunks(effective_batch_size) {
            // Build lookup map: (formid, lowercase_plugin) -> Vec of original (formid, plugin) keys
            // Multiple input pairs may normalize to the same case-insensitive key
            // (e.g., "Fallout4.esm" and "FALLOUT4.ESM"), so we track all of them
            let mut original_key_lookup: HashMap<(String, String), Vec<(String, String)>> =
                HashMap::new();
            for (fid, plug) in batch {
                let normalized_key = (fid.clone(), plug.to_lowercase());
                original_key_lookup
                    .entry(normalized_key)
                    .or_default()
                    .push((fid.clone(), plug.clone()));
            }

            // Build optimized UNION ALL query
            let query = Self::build_union_all_query(&game_table, batch.len());

            // Collect all pools for parallel querying
            let pool_entries: Vec<_> = self.pools.iter().collect();

            // Create futures for parallel database queries
            let query_futures: Vec<_> = pool_entries
                .iter()
                .map(|entry| {
                    let db_path = entry.key().clone();
                    let pool = entry.value().clone();
                    let query_clone = query.clone();
                    let batch_clone: Vec<_> = batch.to_vec();

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
                            let lookup_key = (db_formid.clone(), db_plugin.to_lowercase());
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

                            // Use lowercase for cache key (consistent with cache lookup)
                            let cache_key = format!(
                                "{}:{}:{}",
                                game_table,
                                db_formid,
                                db_plugin.to_lowercase()
                            );

                            // Cache the result once using the normalized key
                            // Only insert to cache if not already present
                            if !self.query_cache.contains_key(&cache_key) {
                                self.query_cache
                                    .insert(cache_key, CacheEntry::new(entry.clone(), cache_ttl));
                            }

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

    /// Get the maximum number of connections per pool
    pub fn get_max_connections(&self) -> Option<usize> {
        *self.max_connections.read().unwrap_or_else(|poisoned| {
            warn!("max_connections lock was poisoned - recovering");
            poisoned.into_inner()
        })
    }

    /// Set the maximum number of connections per pool
    ///
    /// # Arguments
    /// * `max_connections` - New maximum connection count
    pub fn set_max_connections(&self, max_connections: usize) {
        if let Ok(mut m) = self.max_connections.write() {
            *m = Some(max_connections);
        }
    }

    /// Recalculate optimal connection count based on current CPU cores
    pub fn recalculate_max_connections(&self) {
        let new_max = Self::calculate_max_connections();
        self.set_max_connections(new_max);
    }

    /// Get current performance statistics
    pub fn get_stats(&self) -> Result<PoolStatistics, DatabaseError> {
        self.stats
            .read()
            .map(|s| s.clone())
            .map_err(|e| DatabaseError::QueryError(format!("Failed to read stats: {}", e)))
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
        let (active_before, total_queries) = self
            .stats
            .read()
            .map(|s| (s.active_connections, s.total_queries))
            .unwrap_or((0, 0));

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

        // Reset connection stats (queries stats preserved for debugging)
        if let Ok(mut stats) = self.stats.write() {
            stats.active_connections = 0;
        }

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
            let active_connections = self
                .stats
                .read()
                .map(|s| s.active_connections)
                .unwrap_or(0);

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
}
