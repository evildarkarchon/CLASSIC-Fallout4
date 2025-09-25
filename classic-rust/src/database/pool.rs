//! Database connection pool with async support
//!
//! Phase 4 Implementation: High-performance database operations with:
//! - Connection pooling with rusqlite
//! - TTL-based smart caching
//! - Prepared statement reuse
//! - Batch query optimization
//! - FormID-specific operations
//! - Multiple database file support (Main and Local)
//! - Dynamic table name support for different games
//! - Comprehensive error logging

use pyo3::prelude::*;
use pyo3::types::PyList;
use rusqlite::{Connection, params, ToSql};
use dashmap::DashMap;
use std::sync::{Arc, Mutex, RwLock};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};
use std::collections::HashMap;
use tokio::runtime::Runtime;
use once_cell::sync::Lazy;
use anyhow::{Result, Context};
use log::{debug, error, warn, info};

/// Global tokio runtime for async operations
static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    Runtime::new().expect("Failed to create Tokio runtime")
});

/// Cache entry with TTL support
#[derive(Clone, Debug)]
struct CacheEntry {
    value: String,
    expires_at: Instant,
}

impl CacheEntry {
    fn new(value: String, ttl: Duration) -> Self {
        Self {
            value,
            expires_at: Instant::now() + ttl,
        }
    }

    fn is_expired(&self) -> bool {
        Instant::now() > self.expires_at
    }
}

/// Connection wrapper (without statement cache for thread safety)
struct ConnectionWrapper {
    conn: Connection,
}

impl ConnectionWrapper {
    fn new(path: &Path) -> Result<Self> {
        let conn = Connection::open(path)
            .with_context(|| format!("Failed to open database: {:?}", path))?;

        // Set pragmas for performance
        conn.pragma_update(None, "journal_mode", "WAL")?;
        conn.pragma_update(None, "synchronous", "NORMAL")?;
        conn.pragma_update(None, "cache_size", 10000)?;
        conn.pragma_update(None, "temp_store", "MEMORY")?;
        conn.pragma_update(None, "mmap_size", 30000000)?;

        Ok(Self { conn })
    }
}

/// High-performance database pool with TTL caching
/// Phase 4 implementation for CLASSIC Rust migration
#[pyclass(unsendable)]  // Mark as unsendable due to rusqlite limitations
pub struct RustDatabasePool {
    connections: Arc<DashMap<PathBuf, Arc<Mutex<ConnectionWrapper>>>>,
    query_cache: Arc<DashMap<String, CacheEntry>>,
    cache_ttl: Arc<RwLock<Duration>>,
    max_connections: usize,
    stats: Arc<RwLock<PoolStatistics>>,
    game_table: Arc<RwLock<String>>,  // Dynamic table name support
    db_paths: Arc<RwLock<Vec<PathBuf>>>,  // Support multiple database files
}

/// Statistics for monitoring pool performance
#[derive(Default, Debug, Clone)]
struct PoolStatistics {
    total_queries: u64,
    cache_hits: u64,
    cache_misses: u64,
    total_connections: u64,
    active_connections: u64,
}

#[pymethods]
impl RustDatabasePool {
    #[new]
    #[pyo3(signature = (max_connections=10, cache_ttl_seconds=300, game_table=None))]
    pub fn new(max_connections: Option<usize>, cache_ttl_seconds: Option<u64>, game_table: Option<String>) -> Self {
        let max_conn = max_connections.unwrap_or(10);
        let ttl = Duration::from_secs(cache_ttl_seconds.unwrap_or(300));
        let table = game_table.unwrap_or_else(|| "Fallout4".to_string());

        info!("Initializing RustDatabasePool with max_connections={}, cache_ttl={}s, game_table={}",
              max_conn, cache_ttl_seconds.unwrap_or(300), table);

        Self {
            connections: Arc::new(DashMap::new()),
            query_cache: Arc::new(DashMap::new()),
            cache_ttl: Arc::new(RwLock::new(ttl)),
            max_connections: max_conn,
            stats: Arc::new(RwLock::new(PoolStatistics::default())),
            game_table: Arc::new(RwLock::new(table)),
            db_paths: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Initialize database connections for given paths
    /// Supports multiple database files (e.g., Main and Local databases)
    #[pyo3(name = "initialize")]
    pub fn py_initialize(&self, _py: Python<'_>, db_paths: Vec<String>) -> PyResult<()> {
        let connections = self.connections.clone();
        let stats = self.stats.clone();
        let db_paths_storage = self.db_paths.clone();

        RUNTIME.block_on(async move {
            let mut valid_paths = Vec::new();

            for db_path in db_paths {
                let path = PathBuf::from(&db_path);
                if !path.exists() {
                    warn!("Database file not found: {:?}", path);
                    continue;
                }

                if !connections.contains_key(&path) {
                    match ConnectionWrapper::new(&path) {
                        Ok(conn) => {
                            connections.insert(path.clone(), Arc::new(Mutex::new(conn)));
                            valid_paths.push(path.clone());
                            info!("Successfully opened database connection: {:?}", path);

                            if let Ok(mut s) = stats.write() {
                                s.total_connections += 1;
                                s.active_connections += 1;
                            }
                        },
                        Err(e) => {
                            error!("Failed to open database {:?}: {}", path, e);
                            return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(
                                format!("Failed to open database {:?}: {}", path, e)
                            ));
                        }
                    }
                } else {
                    valid_paths.push(path.clone());
                    debug!("Database already connected: {:?}", path);
                }
            }

            // Store the valid database paths for later use
            if let Ok(mut paths) = db_paths_storage.write() {
                *paths = valid_paths;
            }

            Ok(())
        })
    }

    /// Get FormID entry from database (optimized for CLASSIC's use case)
    #[pyo3(name = "get_entry", signature = (formid, plugin, table=None))]
    pub fn py_get_entry(
        &self,
        _py: Python<'_>,
        formid: String,
        plugin: String,
        table: Option<String>
    ) -> PyResult<Option<String>> {
        // Use provided table or fallback to instance's game_table
        let game_table = table.unwrap_or_else(|| {
            self.game_table.read().unwrap().clone()
        });

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
                // Remove expired entry
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

        RUNTIME.block_on(async move {
            // IMPORTANT: Use COLLATE nocase for case-insensitive matching
            let query = format!(
                "SELECT entry FROM {} WHERE formid=? AND plugin=? COLLATE nocase",
                game_table
            );

            // Try each database in order (Main first, then Local)
            for entry in connections.iter() {
                let db_path = entry.key().clone();
                let conn_arc = entry.value().clone();
                let query_clone = query.clone();
                let formid_clone = formid.clone();
                let plugin_clone = plugin.clone();

                let result = tokio::task::spawn_blocking(move || {
                    let conn = conn_arc.lock().unwrap();
                    conn.conn.query_row(
                        &query_clone,
                        params![formid_clone, plugin_clone],
                        |row| row.get::<_, String>(0)
                    ).ok()
                }).await.map_err(|e| {
                    error!("Database query task failed: {}", e);
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
                })?;

                if let Some(value) = result {
                    // Cache the result with TTL
                    query_cache.insert(
                        cache_key.clone(),
                        CacheEntry::new(value.clone(), cache_ttl)
                    );
                    debug!("Found FormID {} in database {:?}", formid, db_path);
                    return Ok(Some(value));
                }
            }

            debug!("FormID {} not found in any database", formid);
            Ok(None)
        })
    }

    /// Batch lookup for FormID entries (optimized for high throughput)
    /// This method matches Python's batch_lookup performance characteristics
    #[pyo3(name = "get_entries_batch", signature = (formid_plugin_pairs, table=None, batch_size=None))]
    pub fn py_get_entries_batch(
        &self,
        _py: Python<'_>,
        formid_plugin_pairs: &Bound<'_, PyList>,
        table: Option<String>,
        batch_size: Option<usize>
    ) -> PyResult<HashMap<String, String>> {
        let batch_size = batch_size.unwrap_or(100);
        let game_table = table.unwrap_or_else(|| {
            self.game_table.read().unwrap().clone()
        });

        // Parse Python list of tuples
        let mut pairs: Vec<(String, String)> = Vec::new();
        for item in formid_plugin_pairs.iter() {
            let tuple = item.extract::<(String, String)>()?;
            pairs.push(tuple);
        }

        info!("Starting batch lookup for {} FormID/plugin pairs", pairs.len());

        let connections = self.connections.clone();
        let query_cache = self.query_cache.clone();
        let cache_ttl = *self.cache_ttl.read().unwrap();
        let stats = self.stats.clone();

        RUNTIME.block_on(async move {
            let mut results: HashMap<String, String> = HashMap::new();
            let mut uncached_pairs: Vec<(String, String)> = Vec::new();

            // Check cache first
            for (formid, plugin) in &pairs {
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
                s.total_queries += pairs.len() as u64;
            }

            if uncached_pairs.is_empty() {
                return Ok(results);
            }

            // Process uncached pairs in batches
            for batch in uncached_pairs.chunks(batch_size) {
                // Build optimized batch query with COLLATE nocase for each field
                let conditions = batch.iter()
                    .map(|_| "(formid=? COLLATE nocase AND plugin=? COLLATE nocase)")
                    .collect::<Vec<_>>()
                    .join(" OR ");

                // IMPORTANT: COLLATE nocase must be applied per comparison, not to the entire WHERE clause
                let query = format!(
                    "SELECT formid, plugin, entry FROM {} WHERE {}",
                    game_table, conditions
                );

                // Flatten parameters
                let params: Vec<String> = batch.iter()
                    .flat_map(|(f, p)| vec![f.clone(), p.clone()])
                    .collect();

                // Query all databases (try Main first, then Local)
                for entry in connections.iter() {
                    let db_path = entry.key().clone();
                    let conn_arc = entry.value().clone();
                    let query_clone = query.clone();
                    let params_clone = params.clone();

                    let batch_results = tokio::task::spawn_blocking(move || {
                        let conn = conn_arc.lock().unwrap();
                        let mut batch_res: HashMap<String, String> = HashMap::new();

                        // Execute query directly (no statement caching for thread safety)
                        match conn.conn.prepare(&query_clone) {
                            Ok(mut stmt) => {
                                let param_refs: Vec<&dyn ToSql> = params_clone.iter()
                                    .map(|s| s as &dyn ToSql)
                                    .collect();

                                match stmt.query(&param_refs[..]) {
                                    Ok(mut rows) => {
                                        while let Ok(Some(row)) = rows.next() {
                                            if let (Ok(formid), Ok(plugin), Ok(entry)) = (
                                                row.get::<_, String>(0),
                                                row.get::<_, String>(1),
                                                row.get::<_, String>(2)
                                            ) {
                                                let key = format!("{}:{}", formid, plugin);
                                                batch_res.insert(key, entry);
                                            }
                                        }
                                    },
                                    Err(e) => {
                                        error!("Batch query execution error in {:?}: {}", db_path, e);
                                    }
                                }
                            },
                            Err(e) => {
                                error!("Failed to prepare batch query in {:?}: {}", db_path, e);
                            }
                        }
                        batch_res
                    }).await.unwrap_or_else(|e| {
                        error!("Batch query task panicked: {}", e);
                        HashMap::new()
                    });

                    // Cache and collect results
                    for (key, value) in batch_results {
                        let parts: Vec<&str> = key.split(':').collect();
                        if parts.len() == 2 {
                            let cache_key = format!("{}:{}:{}", game_table, parts[0], parts[1]);
                            query_cache.insert(
                                cache_key,
                                CacheEntry::new(value.clone(), cache_ttl)
                            );
                            results.insert(key, value);
                        }
                    }
                }
            }

            info!("Batch lookup completed: {} results found", results.len());
            Ok(results)
        })
    }

    /// Alternative batch lookup method that accepts a list of tuples directly
    /// This provides better compatibility with Python's API expectations
    #[pyo3(name = "batch_lookup", signature = (formid_plugin_pairs, table=None))]
    pub fn py_batch_lookup(
        &self,
        py: Python<'_>,
        formid_plugin_pairs: &Bound<'_, PyList>,
        table: Option<String>
    ) -> PyResult<HashMap<(String, String), String>> {
        // Convert to the format expected by get_entries_batch
        let result = self.py_get_entries_batch(py, formid_plugin_pairs, table, Some(100))?;

        // Convert the result format from "formid:plugin" -> value to (formid, plugin) -> value
        let mut converted_result = HashMap::new();
        for (key, value) in result {
            let parts: Vec<&str> = key.split(':').collect();
            if parts.len() == 2 {
                converted_result.insert((parts[0].to_string(), parts[1].to_string()), value);
            }
        }

        Ok(converted_result)
    }

    /// Set the game table name dynamically
    #[pyo3(name = "set_game_table")]
    pub fn py_set_game_table(&self, table: String) {
        if let Ok(mut game_table) = self.game_table.write() {
            info!("Setting game table to: {}", table);
            *game_table = table;
        }
    }

    /// Get the current game table name
    #[pyo3(name = "get_game_table")]
    pub fn py_get_game_table(&self) -> String {
        self.game_table.read().unwrap().clone()
    }

    /// Clear cache entries (with optional TTL-based cleanup)
    #[pyo3(name = "clear_cache", signature = (expired_only=None))]
    pub fn py_clear_cache(&self, expired_only: Option<bool>) -> usize {
        let expired = expired_only.unwrap_or(false);
        let query_cache = self.query_cache.clone();

        if expired {
            // Remove only expired entries
            let mut removed = 0;
            query_cache.retain(|_, entry| {
                if entry.is_expired() {
                    removed += 1;
                    false
                } else {
                    true
                }
            });
            removed
        } else {
            let size = query_cache.len();
            query_cache.clear();
            size
        }
    }

    /// Set cache TTL in seconds
    #[pyo3(name = "set_cache_ttl")]
    pub fn py_set_cache_ttl(&self, seconds: u64) {
        if let Ok(mut ttl) = self.cache_ttl.write() {
            *ttl = Duration::from_secs(seconds);
        }
    }

    /// Get pool statistics as a dictionary
    #[pyo3(name = "get_stats")]
    pub fn py_get_stats(&self) -> PyResult<HashMap<String, u64>> {
        let stats = self.stats.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        let mut result = HashMap::new();
        result.insert("total_queries".to_string(), stats.total_queries);
        result.insert("cache_hits".to_string(), stats.cache_hits);
        result.insert("cache_misses".to_string(), stats.cache_misses);
        result.insert("total_connections".to_string(), stats.total_connections);
        result.insert("active_connections".to_string(), stats.active_connections);
        result.insert("cache_size".to_string(), self.query_cache.len() as u64);

        if stats.total_queries > 0 {
            let hit_rate = (stats.cache_hits as f64 / stats.total_queries as f64) * 100.0;
            result.insert("cache_hit_rate".to_string(), hit_rate as u64);
        } else {
            result.insert("cache_hit_rate".to_string(), 0);
        }

        Ok(result)
    }

    /// Close all connections and clear caches
    #[pyo3(name = "close")]
    pub fn py_close(&self, _py: Python<'_>) -> PyResult<()> {
        let connections = self.connections.clone();
        let stats = self.stats.clone();

        RUNTIME.block_on(async move {
            // Clear all connections
            connections.clear();

            // Clear cache
            self.query_cache.clear();

            // Update stats
            if let Ok(mut s) = stats.write() {
                s.active_connections = 0;
            }

            Ok(())
        })
    }

    /// Optimize database connections (VACUUM and ANALYZE)
    #[pyo3(name = "optimize")]
    pub fn py_optimize(&self, _py: Python<'_>) -> PyResult<()> {
        let connections = self.connections.clone();

        RUNTIME.block_on(async move {
            for entry in connections.iter() {
                let conn_arc = entry.value().clone();

                tokio::task::spawn_blocking(move || {
                    if let Ok(conn) = conn_arc.lock() {
                        let _ = conn.conn.execute("VACUUM", []);
                        let _ = conn.conn.execute("ANALYZE", []);
                    }
                }).await.map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
                })?;
            }
            Ok(())
        })
    }
}
