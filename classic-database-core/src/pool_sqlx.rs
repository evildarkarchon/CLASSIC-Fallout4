//! Database connection pool with sqlx (Pure Rust Async)
//!
//! High-performance TRUE ASYNC database operations with:
//! - Built-in connection pooling with sqlx
//! - WAL mode for concurrent reads
//! - TTL-based smart caching
//! - Batch query optimization
//! - FormID-specific operations
//! - Multiple database file support (Main and Local)
//! - Dynamic table name support for different games

use dashmap::DashMap;
use log::{debug, error, info, warn};
use sqlx::sqlite::{SqliteConnectOptions, SqliteJournalMode, SqlitePoolOptions, SqliteSynchronous};
use sqlx::{Row, SqlitePool};
use std::collections::HashMap;
use std::path::PathBuf;
use std::str::FromStr;
use std::sync::{Arc, RwLock};
use std::time::{Duration, Instant};
use thiserror::Error;

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
        let max_conn = self.max_connections.read().unwrap().unwrap_or(50);

        info!("Initializing sqlx pools for {} database files", db_paths.len());

        for path in db_paths {
            if !path.exists() {
                warn!("Database file not found: {:?}", path);
                continue;
            }

            // Configure SQLite with WAL mode and optimizations
            let opts = SqliteConnectOptions::from_str(&format!("sqlite://{}", path.display()))
                .map_err(|e| DatabaseError::OpenError(format!("{:?}: {}", path, e)))?
                .journal_mode(SqliteJournalMode::Wal) // Enable WAL mode for concurrent reads
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

            info!("Created sqlx pool with {} connections for {:?}", max_conn, path);

            if let Ok(mut s) = self.stats.write() {
                s.total_connections += max_conn as u64;
                s.active_connections += max_conn as u64;
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
            None => self.game_table.read().unwrap().clone(),
        };

        let cache_key = format!("{}:{}:{}", game_table, formid, plugin);

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
                    let cache_ttl = *self.cache_ttl.read().unwrap();
                    self.query_cache.insert(cache_key.clone(), CacheEntry::new(value.clone(), cache_ttl));
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

    /// Batch lookup for FormID entries
    pub async fn get_entries_batch(
        &self,
        formid_plugin_pairs: Vec<(String, String)>,
        table: Option<&str>,
        batch_size: usize,
    ) -> Result<HashMap<String, String>, DatabaseError> {
        let game_table = match table {
            Some(t) => t.to_string(),
            None => self.game_table.read().unwrap().clone(),
        };

        info!(
            "Starting batch lookup for {} FormID/plugin pairs (sqlx async)",
            formid_plugin_pairs.len()
        );

        let mut results: HashMap<String, String> = HashMap::new();
        let mut uncached_pairs: Vec<(String, String)> = Vec::new();

        // Check cache first
        for (formid, plugin) in &formid_plugin_pairs {
            let cache_key = format!("{}:{}:{}", game_table, formid, plugin);

            if let Some(entry) = self.query_cache.get(&cache_key) {
                if !entry.is_expired() {
                    let result_key = format!("{}:{}", formid, plugin);
                    results.insert(result_key, entry.value.clone());
                    if let Ok(mut s) = self.stats.write() {
                        s.cache_hits += 1;
                    }
                    continue;
                } else {
                    self.query_cache.remove(&cache_key);
                }
            }

            uncached_pairs.push((formid.clone(), plugin.clone()));
            if let Ok(mut s) = self.stats.write() {
                s.cache_misses += 1;
            }
        }

        if let Ok(mut s) = self.stats.write() {
            s.total_queries += formid_plugin_pairs.len() as u64;
        }

        if uncached_pairs.is_empty() {
            return Ok(results);
        }

        let cache_ttl = *self.cache_ttl.read().unwrap();

        // Process uncached pairs in batches (TRUE ASYNC!)
        for batch in uncached_pairs.chunks(batch_size) {
            let mut query = String::with_capacity(batch.len() * 64 + game_table.len() + 50);
            query.push_str("SELECT formid, plugin, entry FROM ");
            query.push_str(&game_table);
            query.push_str(" WHERE ");

            for (i, _) in batch.iter().enumerate() {
                if i > 0 {
                    query.push_str(" OR ");
                }
                query.push_str("(formid=? COLLATE nocase AND plugin=? COLLATE nocase)");
            }

            for entry in self.pools.iter() {
                let db_path = entry.key().clone();
                let pool = entry.value();

                // Build query with bindings
                let mut sqlx_query = sqlx::query(&query);
                for (formid, plugin) in batch.iter() {
                    sqlx_query = sqlx_query.bind(formid).bind(plugin);
                }

                // TRUE ASYNC FETCH - no spawn_blocking!
                match sqlx_query.fetch_all(pool).await {
                    Ok(rows) => {
                        for row in rows {
                            let formid: String = row.try_get(0)?;
                            let plugin: String = row.try_get(1)?;
                            let entry: String = row.try_get(2)?;

                            let result_key = format!("{}:{}", formid, plugin);
                            let cache_key = format!("{}:{}:{}", game_table, formid, plugin);

                            results.insert(result_key, entry.clone());
                            self.query_cache.insert(cache_key, CacheEntry::new(entry, cache_ttl));
                        }
                    }
                    Err(e) => {
                        error!("Batch query error in {:?}: {}", db_path, e);
                        continue;
                    }
                }
            }
        }

        info!(
            "Batch lookup completed: found {}/{} entries",
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
        self.game_table.read().unwrap().clone()
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
        self.max_connections.read().unwrap().clone()
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
        info!("Closing all database connections");

        // Clear caches
        self.query_cache.clear();

        // Close all pools
        for entry in self.pools.iter() {
            let db_path = entry.key().clone();
            let pool = entry.value();
            pool.close().await;
            info!("Closed connection pool for {:?}", db_path);
        }

        self.pools.clear();

        // Reset stats
        if let Ok(mut stats) = self.stats.write() {
            stats.active_connections = 0;
        }

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
