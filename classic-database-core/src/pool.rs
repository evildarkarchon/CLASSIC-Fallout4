//! Database connection pool with async support (Pure Rust)
//!
//! High-performance database operations with:
//! - Connection pooling with rusqlite
//! - TTL-based smart caching
//! - Prepared statement reuse
//! - Batch query optimization
//! - FormID-specific operations
//! - Multiple database file support (Main and Local)
//! - Dynamic table name support for different games

use dashmap::DashMap;
use log::{debug, error, info, warn};
use rusqlite::{params, Connection, ToSql};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};
use std::time::{Duration, Instant};
use thiserror::Error;

/// Database errors
#[derive(Debug, Error)]
pub enum DatabaseError {
    #[error("Failed to open database: {0}")]
    OpenError(String),

    #[error("Query execution failed: {0}")]
    QueryError(String),

    #[error("Database file not found: {0}")]
    NotFound(String),

    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Rusqlite error: {0}")]
    RusqliteError(#[from] rusqlite::Error),

    #[error("Task join error: {0}")]
    JoinError(String),
}

/// Cache entry with TTL support
#[derive(Clone, Debug)]
pub struct CacheEntry {
    pub value: String,
    pub expires_at: Instant,
}

impl CacheEntry {
    pub fn new(value: String, ttl: Duration) -> Self {
        Self {
            value,
            expires_at: Instant::now() + ttl,
        }
    }

    pub fn is_expired(&self) -> bool {
        Instant::now() > self.expires_at
    }
}

/// Connection wrapper (without statement cache for thread safety)
struct ConnectionWrapper {
    conn: Connection,
}

impl ConnectionWrapper {
    fn new(path: &Path) -> Result<Self, DatabaseError> {
        // Open database in read-only mode with SQLITE_OPEN_READ_ONLY flag
        let conn = Connection::open_with_flags(path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .map_err(|e| DatabaseError::OpenError(format!("{:?}: {}", path, e)))?;

        // Read-only optimizations (non-modifying PRAGMAs)
        conn.pragma_update(None, "cache_size", 10000)?;
        conn.pragma_update(None, "temp_store", "MEMORY")?;
        conn.pragma_update(None, "mmap_size", 30000000)?;

        Ok(Self { conn })
    }
}

/// Statistics for monitoring pool performance
#[derive(Default, Debug, Clone)]
pub struct PoolStatistics {
    pub total_queries: u64,
    pub cache_hits: u64,
    pub cache_misses: u64,
    pub total_connections: u64,
    pub active_connections: u64,
}

/// High-performance database pool with TTL caching (Pure Rust)
pub struct DatabasePool {
    connections: Arc<DashMap<PathBuf, Arc<Mutex<ConnectionWrapper>>>>,
    query_cache: Arc<DashMap<String, CacheEntry>>,
    cache_ttl: Arc<RwLock<Duration>>,
    max_connections: Arc<RwLock<Option<usize>>>,
    stats: Arc<RwLock<PoolStatistics>>,
    game_table: Arc<RwLock<String>>,
    db_paths: Arc<RwLock<Vec<PathBuf>>>,
}

impl DatabasePool {
    /// Calculate optimal max_connections based on system resources
    fn calculate_max_connections() -> usize {
        // Base on available CPU cores with reasonable bounds
        let cpus = num_cpus::get();
        let optimal = cpus * 2; // 2 connections per CPU core

        // Clamp between 4 and 32 to avoid extremes
        optimal.clamp(4, 32)
    }

    /// Create a new database pool with optional max_connections
    /// If max_connections is None, it will be calculated dynamically based on CPU cores
    pub fn new(max_connections: Option<usize>, cache_ttl: Duration, game_table: String) -> Self {
        let max_conn = max_connections.unwrap_or_else(Self::calculate_max_connections);

        info!(
            "Initializing DatabasePool with max_connections={} ({}), cache_ttl={:?}, game_table={}",
            max_conn,
            if max_connections.is_some() {
                "explicit"
            } else {
                "auto-calculated"
            },
            cache_ttl,
            game_table
        );

        Self {
            connections: Arc::new(DashMap::new()),
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
        let connections = self.connections.clone();
        let stats = self.stats.clone();
        let db_paths_storage = self.db_paths.clone();

        let mut valid_paths = Vec::new();

        for path in db_paths {
            if !path.exists() {
                warn!("Database file not found: {:?}", path);
                continue;
            }

            if !connections.contains_key(&path) {
                let conn = ConnectionWrapper::new(&path)?;
                connections.insert(path.clone(), Arc::new(Mutex::new(conn)));
                valid_paths.push(path.clone());
                info!("Successfully opened database connection: {:?}", path);

                if let Ok(mut s) = stats.write() {
                    s.total_connections += 1;
                    s.active_connections += 1;
                }
            } else {
                valid_paths.push(path.clone());
                debug!("Database already connected: {:?}", path);
            }
        }

        if let Ok(mut paths) = db_paths_storage.write() {
            *paths = valid_paths;
        }

        Ok(())
    }

    /// Get FormID entry from database (optimized for CLASSIC's use case)
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

        // Check cache first with TTL
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

        // Query all connected databases
        let connections = self.connections.clone();
        let query_cache = self.query_cache.clone();
        let cache_ttl = *self.cache_ttl.read().unwrap();

        let query = format!(
            "SELECT entry FROM {} WHERE formid=? AND plugin=? COLLATE nocase",
            game_table
        );

        let formid = formid.to_string();
        let plugin = plugin.to_string();

        // Try each database in order (Main first, then Local)
        for entry in connections.iter() {
            let db_path = entry.key().clone();
            let conn_arc = entry.value().clone();
            let query_clone = query.clone();
            let formid_clone = formid.clone();
            let plugin_clone = plugin.clone();

            let result = tokio::task::spawn_blocking(move || {
                let conn = conn_arc.lock().unwrap();
                conn.conn
                    .query_row(&query_clone, params![formid_clone, plugin_clone], |row| {
                        row.get::<_, String>(0)
                    })
                    .ok()
            })
            .await
            .map_err(|e| DatabaseError::JoinError(e.to_string()))?;

            if let Some(value) = result {
                query_cache.insert(cache_key.clone(), CacheEntry::new(value.clone(), cache_ttl));
                debug!("Found FormID {} in database {:?}", formid, db_path);
                return Ok(Some(value));
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
            "Starting batch lookup for {} FormID/plugin pairs",
            formid_plugin_pairs.len()
        );

        let connections = self.connections.clone();
        let query_cache = self.query_cache.clone();
        let cache_ttl = *self.cache_ttl.read().unwrap();
        let stats = self.stats.clone();

        let mut results: HashMap<String, String> = HashMap::new();
        let mut uncached_pairs: Vec<(String, String)> = Vec::new();

        // Check cache first
        for (formid, plugin) in &formid_plugin_pairs {
            let cache_key = format!("{}:{}:{}", game_table, formid, plugin);

            if let Some(entry) = query_cache.get(&cache_key) {
                if !entry.is_expired() {
                    let result_key = format!("{}:{}", formid, plugin);
                    results.insert(result_key, entry.value.clone());
                    if let Ok(mut s) = stats.write() {
                        s.cache_hits += 1;
                    }
                    continue;
                } else {
                    query_cache.remove(&cache_key);
                }
            }

            uncached_pairs.push((formid.clone(), plugin.clone()));
            if let Ok(mut s) = stats.write() {
                s.cache_misses += 1;
            }
        }

        if let Ok(mut s) = stats.write() {
            s.total_queries += formid_plugin_pairs.len() as u64;
        }

        if uncached_pairs.is_empty() {
            return Ok(results);
        }

        // Process uncached pairs in batches
        for batch in uncached_pairs.chunks(batch_size) {
            let conditions = batch
                .iter()
                .map(|_| "(formid=? COLLATE nocase AND plugin=? COLLATE nocase)")
                .collect::<Vec<_>>()
                .join(" OR ");

            let query = format!(
                "SELECT formid, plugin, entry FROM {} WHERE {}",
                game_table, conditions
            );

            let params: Vec<String> = batch
                .iter()
                .flat_map(|(f, p)| vec![f.clone(), p.clone()])
                .collect();

            for entry in connections.iter() {
                let db_path = entry.key().clone();
                let conn_arc = entry.value().clone();
                let query_clone = query.clone();
                let params_clone = params.clone();

                let batch_results = tokio::task::spawn_blocking(move || {
                    let conn = conn_arc.lock().unwrap();
                    let mut batch_res: HashMap<String, String> = HashMap::new();

                    match conn.conn.prepare(&query_clone) {
                        Ok(mut stmt) => {
                            let param_refs: Vec<&dyn ToSql> =
                                params_clone.iter().map(|s| s as &dyn ToSql).collect();

                            match stmt.query(&param_refs[..]) {
                                Ok(mut rows) => {
                                    while let Ok(Some(row)) = rows.next() {
                                        if let (Ok(formid), Ok(plugin), Ok(entry)) = (
                                            row.get::<_, String>(0),
                                            row.get::<_, String>(1),
                                            row.get::<_, String>(2),
                                        ) {
                                            let key = format!("{}:{}", formid, plugin);
                                            batch_res.insert(key, entry);
                                        }
                                    }
                                }
                                Err(e) => {
                                    error!("Batch query execution error in {:?}: {}", db_path, e);
                                }
                            }
                        }
                        Err(e) => {
                            error!("Failed to prepare batch query in {:?}: {}", db_path, e);
                        }
                    }
                    batch_res
                })
                .await
                .map_err(|e| DatabaseError::JoinError(e.to_string()))?;

                // Cache and collect results
                for (key, value) in batch_results {
                    let parts: Vec<&str> = key.split(':').collect();
                    if parts.len() == 2 {
                        let cache_key = format!("{}:{}:{}", game_table, parts[0], parts[1]);
                        query_cache.insert(cache_key, CacheEntry::new(value.clone(), cache_ttl));
                        results.insert(key, value);
                    }
                }
            }
        }

        info!("Batch lookup completed: {} results found", results.len());
        Ok(results)
    }

    /// Set the game table name dynamically
    pub fn set_game_table(&self, table: String) {
        if let Ok(mut game_table) = self.game_table.write() {
            info!("Setting game table to: {}", table);
            *game_table = table;
        }
    }

    /// Get the current game table name
    pub fn get_game_table(&self) -> String {
        self.game_table.read().unwrap().clone()
    }

    /// Clear cache entries (with optional TTL-based cleanup)
    pub fn clear_cache(&self, expired_only: bool) -> usize {
        if expired_only {
            let mut removed = 0;
            self.query_cache.retain(|_, entry| {
                if entry.is_expired() {
                    removed += 1;
                    false
                } else {
                    true
                }
            });
            removed
        } else {
            let size = self.query_cache.len();
            self.query_cache.clear();
            size
        }
    }

    /// Set cache TTL
    pub fn set_cache_ttl(&self, ttl: Duration) {
        if let Ok(mut cache_ttl) = self.cache_ttl.write() {
            *cache_ttl = ttl;
        }
    }

    /// Get current max_connections setting
    pub fn get_max_connections(&self) -> Option<usize> {
        self.max_connections.read().ok().and_then(|guard| *guard)
    }

    /// Set max_connections (for runtime adjustment)
    pub fn set_max_connections(&self, max_conn: usize) {
        if let Ok(mut max_connections) = self.max_connections.write() {
            info!("Updating max_connections to: {}", max_conn);
            *max_connections = Some(max_conn);
        }
    }

    /// Recalculate max_connections based on current system resources
    pub fn recalculate_max_connections(&self) {
        let new_max = Self::calculate_max_connections();
        self.set_max_connections(new_max);
    }

    /// Get pool statistics
    pub fn get_stats(&self) -> Result<PoolStatistics, DatabaseError> {
        let stats = self
            .stats
            .read()
            .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
        Ok(stats.clone())
    }

    /// Get cache size
    pub fn cache_size(&self) -> usize {
        self.query_cache.len()
    }

    /// Close all connections and clear caches
    pub async fn close(&self) -> Result<(), DatabaseError> {
        self.connections.clear();
        self.query_cache.clear();

        if let Ok(mut s) = self.stats.write() {
            s.active_connections = 0;
        }

        Ok(())
    }

    /// Optimize database connections (VACUUM and ANALYZE)
    pub async fn optimize(&self) -> Result<(), DatabaseError> {
        for entry in self.connections.iter() {
            let conn_arc = entry.value().clone();

            tokio::task::spawn_blocking(move || {
                if let Ok(conn) = conn_arc.lock() {
                    let _ = conn.conn.execute("VACUUM", []);
                    let _ = conn.conn.execute("ANALYZE", []);
                }
            })
            .await
            .map_err(|e| DatabaseError::JoinError(e.to_string()))?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn test_cache_entry_expiry() {
        let entry = CacheEntry::new("test".to_string(), Duration::from_millis(10));
        assert!(!entry.is_expired());

        std::thread::sleep(Duration::from_millis(20));
        assert!(entry.is_expired());
    }

    #[test]
    fn test_pool_creation() {
        let pool = DatabasePool::new(Some(10), Duration::from_secs(300), "Fallout4".to_string());

        assert_eq!(pool.get_game_table(), "Fallout4");
        assert_eq!(pool.cache_size(), 0);
    }

    #[test]
    fn test_pool_auto_max_connections() {
        let pool = DatabasePool::new(None, Duration::from_secs(300), "Fallout4".to_string());

        assert_eq!(pool.get_game_table(), "Fallout4");
        assert_eq!(pool.cache_size(), 0);

        // Verify max_connections was calculated
        let max_conn = pool.max_connections.read().unwrap();
        assert!(max_conn.is_some());
        let conn = max_conn.unwrap();
        assert!(
            conn >= 4 && conn <= 32,
            "max_connections should be between 4 and 32, got {}",
            conn
        );
    }
}
