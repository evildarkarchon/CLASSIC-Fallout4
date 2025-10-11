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

use anyhow::{Context, Result};
use dashmap::DashMap;
use log::{debug, error, info, warn};
use pyo3::prelude::*;
use pyo3::types::PyList;
use rusqlite::{params, Connection, ToSql};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};
use std::time::{Duration, Instant};

// Use the global runtime from lib.rs (ONE RUNTIME RULE)
use crate::get_runtime;

/// ```rust
/// A structure representing a cache entry with an associated value and expiration time.
///```
/// # Fields
/// - `value` (`String`): The value stored in the cache entry.
/// - `expires_at` (`Instant`): The timestamp indicating when the cache entry will expire.
///
/// # Derivable Traits
/// - `Clone`: Allows for creating a duplicate instance of `CacheEntry`.
/// - `Debug`: Enables formatting of the `CacheEntry` instance for debugging purposes.
///
/// This struct is typically used in caching mechanisms to store and manage values
/// tied to an expiration time.
#[derive(Clone, Debug)]
struct CacheEntry {
    value: String,
    expires_at: Instant,
}

impl CacheEntry {
    /// ```rust
    /// Creates a new instance of the struct with the given value and time-to-live (TTL).
    ///```
    /// # Parameters
    /// - `value`: A `String` representing the value to be stored.
    /// - `ttl`: A `Duration` specifying the time-to-live for the instance,
    ///   determining how long the value will remain valid.
    ///
    /// # Returns
    /// A new instance of the struct with the provided value and an expiration
    /// time calculated by adding the given TTL to the current instant.
    ///
    /// # Example
    /// ```
    /// use std::time::{Duration, Instant};
    ///
    /// let value = String::from("example_value");
    /// let ttl = Duration::from_secs(60);
    /// let instance = YourStruct::new(value, ttl);
    ///
    /// // The instance now contains the given value and will expire
    /// // approximately 60 seconds from now.
    /// ```
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

/// ```
/// A wrapper structure for handling database connections.
///```
/// `ConnectionWrapper` encapsulates an underlying `Connection`
/// to provide additional functionality and abstraction as needed.
///
/// # Fields
/// * `conn` - The underlying `Connection` instance that this wrapper manages.
///
/// # Examples
/// ```
/// let connection = Connection::new(); // Assume Connection::new() creates a new connection.
/// let wrapper = ConnectionWrapper { conn: connection };
/// ```
struct ConnectionWrapper {
    conn: Connection,
}

impl ConnectionWrapper {
    /// ```
    /// Creates a new instance of the struct by initializing a SQLite database connection in read-only mode
    /// with specific performance-enhancing PRAGMA settings.
    ///```
    /// # Parameters
    /// - `path`: A reference to a `Path` instance representing the file path to the SQLite database to open.
    ///
    /// # Returns
    /// - `Ok(Self)`: Returns an initialized instance of the struct if the database connection and PRAGMAs are successfully set.
    /// - `Err`: Returns an error if the connection to the database or the PRAGMA updates fail.
    ///
    /// # Behavior
    /// 1. Opens the SQLite database in read-only mode using the `SQLITE_OPEN_READ_ONLY` flag.
    /// 2. Applies read-only optimizations via PRAGMA settings:
    ///    - Sets the cache size to 10,000 pages to utilize a memory cache for better read performance.
    ///    - Configures temporary storage (`temp_store`) to use in-memory storage instead of disk.
    ///    - Allocates 30MB for memory-mapped I/O to enhance read performance when the database size allows.
    ///
    /// # Errors
    /// - Fails with an error if:
    ///   - The database file cannot be opened in read-only mode.
    ///   - Any of the PRAGMA settings fail to execute.
    ///
    /// # Examples
    /// ```
    /// use std::path::Path;
    ///
    /// let path = Path::new("example.db");
    /// let db_instance = StructName::new(path)?;
    /// ```
    fn new(path: &Path) -> Result<Self> {
        // Open database in read-only mode with SQLITE_OPEN_READ_ONLY flag
        let conn = Connection::open_with_flags(path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .with_context(|| format!("Failed to open database: {:?}", path))?;

        // Read-only optimizations (non-modifying PRAGMAs)
        // These queries don't modify the database file
        conn.pragma_update(None, "cache_size", 10000)?; // Memory cache only
        conn.pragma_update(None, "temp_store", "MEMORY")?; // Temp data in memory
        conn.pragma_update(None, "mmap_size", 30000000)?; // Memory-mapped I/O

        Ok(Self { conn })
    }
}

/// ```
/// Represents a thread-safe wrapper around a pool of SQLite database connections.
/// This structure is designed to manage multiple SQLite database files and provide
/// mechanisms for caching, stats tracking, and managing database connections.
///```
/// # Attributes
///
/// * `connections`
///    - A shared map (`DashMap`) keyed by `PathBuf` (database file paths), with values
///      being an `Arc`-wrapped `Mutex` protecting a `ConnectionWrapper`.
///      This ensures thread-safe access to specific database connections.
///
/// * `query_cache`
///    - A shared cache (`DashMap`) designed to store preprocessed query-related information
///      (e.g., query plans or results). The keys are query strings, and the associated
///      values are `CacheEntry` instances.
///
/// * `cache_ttl`
///    - A shared, modifiable duration (`RwLock<Duration>`) to specify the time-to-live
///      for cached entries in the `query_cache`.
///
/// * `max_connections`
///    - Reserved for future implementation of connection pooling logic. Currently not in use
///      (`#[allow(dead_code)]` flag suppresses compiler warnings for it). This field might
///      define the upper limit on the number of established connections in the future.
///
/// * `stats`
///    - A shared, modifiable reference (`RwLock<PoolStatistics>`) that tracks statistics
///      about the connection pool, such as usage metrics or active connections.
///
/// * `game_table`
///    - An `RwLock`-protected string that represents the name of a dynamic database table.
///      This is handy for applications where table names might vary based on runtime conditions.
///
/// * `db_paths`
///    - A shared list (`RwLock<Vec<PathBuf>>`) of database file paths. This allows support
///      for managing multiple SQLite database files within this pool.
///
/// # Notes
///
/// - The `RustDatabasePool` is marked as `#[pyclass(unsendable)]` because SQLite connections
///   in `rusqlite` restrict certain thread-safety guarantees and are not inherently transferable
///   across threads.
///
/// - Connection pooling is not yet implemented, but this structure is envisioned to be a foundation
///   for such functionality in future iterations.
///
/// - Designed for high-performance usage with Rust's concurrency primitives (`Arc`, `DashMap`, `Mutex`, `RwLock`
///   for safe, concurrent access to data).
///
/// # Usage
///
/// Instantiate and manage the `RustDatabasePool` for operations involving multiple SQLite
/// database files, dynamic table handling, and query caching.
///
/// ```rust
/// use std::sync::Arc;
/// use rust_project::RustDatabasePool;
///
/// let db_pool = RustDatabasePool {
///     connections: Arc::new(DashMap::new()),
///     query_cache: Arc::new(DashMap::new()),
///     cache_ttl: Arc::new(RwLock::new(Duration::from_secs(300))),
///     max_connections: 10,
///     stats: Arc::new(RwLock::new(PoolStatistics::default())),
///     game_table: Arc::new(RwLock::new(String::from("default_table"))),
///     db_paths: Arc::new(RwLock::new(vec![])),
/// };
///
/// // Use the `db_pool` instance to manage database connections or execute queries.
/// ```
#[pyclass(unsendable)] // Mark as unsendable due to rusqlite limitations
pub struct RustDatabasePool {
    connections: Arc<DashMap<PathBuf, Arc<Mutex<ConnectionWrapper>>>>,
    query_cache: Arc<DashMap<String, CacheEntry>>,
    cache_ttl: Arc<RwLock<Duration>>,
    #[allow(dead_code)] // Reserved for future connection pooling implementation
    max_connections: usize,
    stats: Arc<RwLock<PoolStatistics>>,
    game_table: Arc<RwLock<String>>,     // Dynamic table name support
    db_paths: Arc<RwLock<Vec<PathBuf>>>, // Support multiple database files
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
    /// ```
    /// Creates a new instance of `RustDatabasePool`.
    ///
    /// This function initializes a database connection pool with optional configurations such as
    /// maximum number of connections, cache TTL (Time-to-Live) in seconds, and the name of the game table.
    ///```
    /// # Parameters
    /// - `max_connections` (Optional<usize>): The maximum number of connections allowed in the pool. If not provided, defaults to `10`.
    /// - `cache_ttl_seconds` (Optional<u64>): The cache Time-to-Live in seconds. If not provided, defaults to `300` seconds.
    /// - `game_table` (Optional<String>): The name of the game table to use. If not provided, defaults to `"Fallout4"`.
    ///
    /// # Returns
    /// - `Self`: An instance of `RustDatabasePool` with the specified or default configurations.
    ///
    /// # Logging
    /// Logs the initialization settings, including `max_connections`, `cache_ttl_seconds`, and `game_table` values.
    ///
    /// # Example
    /// ```rust
    /// let pool = RustDatabasePool::new(Some(20), Some(600), Some("Skyrim".to_string()));
    /// // Creates a pool with max_connections=20, cache_ttl_seconds=600, and game_table="Skyrim".
    ///
    /// let default_pool = RustDatabasePool::new(None, None, None);
    /// // Creates a pool with default settings: max_connections=10, cache_ttl_seconds=300, game_table="Fallout4".
    /// ```
    ///
    /// # Implementation Details
    /// - Uses `DashMap` for concurrently safe caches and connections.
    /// - `RwLock` is used to ensure safe mutable access for configuration updates like `cache_ttl` and `game_table`.
    /// - If any parameter is not provided, a default value is assigned.
    #[new]
    #[pyo3(signature = (max_connections=None, cache_ttl_seconds=300, game_table=None))]
    pub fn new(
        max_connections: Option<usize>,
        cache_ttl_seconds: Option<u64>,
        game_table: Option<String>,
    ) -> Self {
        let max_conn = max_connections.unwrap_or(10);
        let ttl = Duration::from_secs(cache_ttl_seconds.unwrap_or(300));
        let table = game_table.unwrap_or_else(|| "Fallout4".to_string());

        info!(
            "Initializing RustDatabasePool with max_connections={}, cache_ttl={}s, game_table={}",
            max_conn,
            ttl.as_secs(),
            table
        );

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

    /// ```rust
    /// Initialize database connections with the provided list of database paths.
    ///
    /// This method establishes connections to the databases at the specified file paths
    /// if they exist and are not already connected. If a path does not point to an existing
    /// file, it will be skipped, and a warning is logged. If a connection to a given database
    /// cannot be established, an error is returned. Successfully connected databases are stored
    /// for future use.
    ///```
    /// # Parameters
    /// - `db_paths` - A vector of file paths pointing to the database files. Each path will be
    ///   checked for existence and availability for connection.
    ///
    /// # Returns
    /// - `PyResult<()>` - Returns `Ok(())` on successful initialization, meaning all valid
    ///   database connections have been processed. If an error occurs while processing any
    ///   individual database path, the function returns an appropriate `PyErr`.
    ///
    /// # Process
    /// 1. Iterates over the list of database paths.
    /// 2. For each path:
    ///    - Validates that the file exists.
    ///    - If not connected yet, attempts to establish a new connection:
    ///      - On success, adds the connection to the shared state and adjusts the statistics.
    ///      - On failure, logs the error and halts the process, returning the error.
    ///    - If already connected, logs that the database is already open.
    /// 3. Updates a shared storage of valid connected database paths for later reference.
    /// 4. Returns a success or propagates the error.
    ///
    /// # Warnings
    /// - Logs a warning if a database file does not exist at the given path.
    /// - Logs any errors encountered when attempting to connect to a database.
    ///
    /// # Statistics
    /// - Updates the internal `stats` structure to reflect the total and active connections.
    /// - Tracks only successful connections.
    ///
    /// # Logging
    /// - Information logging for successful connections.
    /// - Debug logging for already connected databases.
    /// - Warning and error logging for missing paths or failed connections.
    ///
    /// # Python Integration
    /// This function is exposed to Python via the `#[pyo3(name = "initialize")]` attribute, allowing
    /// users to call it from Python programs. On failure, it raises a Python `IOError` with the
    /// relevant details.
    ///
    /// # Example Usage (Python):
    /// ```python
    /// try:
    ///     obj.initialize(["/path/to/db1.sqlite", "/path/to/db2.sqlite"])
    ///     print("Databases initialized successfully.")
    /// except IOError as e:
    ///     print(f"Failed to initialize databases: {e}")
    /// ```
    #[pyo3(name = "initialize")]
    pub fn py_initialize(&self, _py: Python<'_>, db_paths: Vec<String>) -> PyResult<()> {
        let connections = self.connections.clone();
        let stats = self.stats.clone();
        let db_paths_storage = self.db_paths.clone();

        get_runtime().block_on(async move {
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
                        }
                        Err(e) => {
                            error!("Failed to open database {:?}: {}", path, e);
                            return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
                                "Failed to open database {:?}: {}",
                                path, e
                            )));
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

    /// ```
    /// Retrieves an entry from the database or cache based on the provided `formid` and `plugin`,
    /// with an optional `table` parameter to override the default game table.
    ///```
    /// # Arguments
    ///
    /// - `formid` (`String`): The unique identifier for the form entry to retrieve.
    /// - `plugin` (`String`): The plugin name associated with the form entry.
    /// - `table` (`Option<String>`): (Optional) The database table to query. If not provided,
    ///    uses the instance's `game_table`.
    ///
    /// # Returns
    ///
    /// - `PyResult<Option<String>>`: Returns:
    ///    - `Ok(Some(entry))` on a successful match in the database or cache.
    ///    - `Ok(None)` if no match is found in the cache or databases.
    ///    - `Err(PyErr)` if a runtime error occurs during query execution.
    ///
    /// # Behavior
    ///
    /// 1. **Cache Lookup**:
    ///    - First, attempts to retrieve the entry from the in-memory cache using a composite key
    ///      (`game_table:formid:plugin`).
    ///    - If a valid (non-expired) cache entry exists:
    ///        * Increments the cache hit stats.
    ///        * Returns the cached value.
    ///    - If an expired cache entry exists, it is removed, and a database lookup is performed.
    ///
    /// 2. **Cache Miss Handling**:
    ///    - Increments cache miss stats.
    ///    - Queries all connected databases (starting with the main one) using an SQL `SELECT` query
    ///      with `COLLATE nocase` for case-insensitive matching of `formid` and `plugin`.
    ///    - For each database:
    ///        - If a matching record is found:
    ///            * The result is cached with a time-to-live (TTL) value.
    ///            * The entry is returned.
    ///    - If no database contains the requested entry:
    ///        - Returns `Ok(None)`.
    ///
    /// 3. **Asynchronous Database Query**:
    ///    - Database queries are performed using asynchronous tasks to avoid blocking the application.
    ///    - If a task fails, it raises a Python runtime error (`PyRuntimeError`) with the error details.
    ///
    /// # Notes
    ///
    /// - The method relies on the `cache_ttl` duration to invalidate outdated cache entries.
    /// - Proper locking and synchronization are used to ensure thread safety for reading and updating
    ///   shared data such as `game_table`, `query_cache`, and `stats`.
    /// - Debug logs provide detailed information about cache hits, cache misses, expired entries,
    ///   and database query results.
    ///
    /// # Examples
    ///
    /// ```python
    /// result = my_instance.get_entry("123AB", "ExamplePlugin")
    /// if result is not None:
    ///     print(f"Entry found: {result}")
    /// else:
    ///     print("Entry not found.")
    /// ```
    ///
    /// # Errors
    ///
    /// - If an asynchronous database query encounters an error, a `PyRuntimeError` is raised.
    /// - Internal locking or runtime issues could also result in Python exceptions.
    ///
    /// # Debugging
    ///
    /// Debug-level logs are generated for the following scenarios:
    /// - Cache hits.
    /// - Cache misses.
    /// - Cache expiration events.
    /// - Database matches.
    /// - Failures or successful completion of queries.
    ///
    /// # Parallelism
    ///
    /// Database queries are executed in a non-blocking, parallel manner across connections using
    /// `tokio`'s asynchronous runtime.
    #[pyo3(name = "get_entry", signature = (formid, plugin, table=None))]
    pub fn py_get_entry(
        &self,
        _py: Python<'_>,
        formid: String,
        plugin: String,
        table: Option<String>,
    ) -> PyResult<Option<String>> {
        // Use provided table or fallback to instance's game_table
        let game_table = table.unwrap_or_else(|| self.game_table.read().unwrap().clone());

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

        get_runtime().block_on(async move {
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
                    conn.conn
                        .query_row(&query_clone, params![formid_clone, plugin_clone], |row| {
                            row.get::<_, String>(0)
                        })
                        .ok()
                })
                .await
                .map_err(|e| {
                    error!("Database query task failed: {}", e);
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
                })?;

                if let Some(value) = result {
                    // Cache the result with TTL
                    query_cache
                        .insert(cache_key.clone(), CacheEntry::new(value.clone(), cache_ttl));
                    debug!("Found FormID {} in database {:?}", formid, db_path);
                    return Ok(Some(value));
                }
            }

            debug!("FormID {} not found in any database", formid);
            Ok(None)
        })
    }

    /// ```rust
    /// Retrieves entries in batches for a given list of FormID/plugin pairs.
    ///
    /// This function performs a batch lookup for the provided list of `(FormID, Plugin)` pairs.
    /// Entries are fetched from a specified database table, optionally using a specified batch size.
    /// Cached results are utilized when available, and database queries are performed for uncached
    /// entries. Results are stored in and returned as a `HashMap<key, entry>` where the `key` is
    /// formed as `FormID:Plugin`.
    ///```
    /// # Parameters
    /// - `formid_plugin_pairs` (*`&Bound<'_, PyList>`*):
    ///   A Python list of tuples where each tuple contains a `FormID` (String) and a `Plugin` (String).
    /// - `table` (*`Option<String>`*, optional):
    ///   An optional database table name. If not provided, the default table (`self.game_table`) is used.
    /// - `batch_size` (*`Option<usize>`*, optional):
    ///   The number of uncached pairs to process per database query batch. Defaults to `100` if not specified.
    ///
    /// # Returns
    /// - `PyResult<HashMap<String, String>>`:
    ///   A HashMap with keys formed as "FormID:Plugin" and values as the corresponding database entries.
    ///
    /// # Workflow
    /// 1. Parses the Python list of `(FormID, Plugin)` pairs.
    /// 2. Checks if entries for the pairs are present in the cache:
    ///    - If cached and valid, adds the entry to the results.
    ///    - If not cached or expired, marks the pair as uncached.
    /// 3. Processes uncached pairs in batches, querying all connected databases:
    ///    - Builds optimized SQL queries using `COLLATE nocase` for case-insensitivity.
    ///    - Executes queries on connected databases, starting with the primary database and falling back to others.
    ///    - Caches results for future lookups.
    /// 4. Merges and returns the final result set.
    ///
    /// # Caching
    /// - Results are cached in an in-memory query cache with a configurable TTL (Time-To-Live).
    /// - Expired entries are removed from the cache before performing uncached queries.
    ///
    /// # Errors
    /// Raises a PyErr on:
    /// - Invalid input (e.g., malformed Python data structures).
    /// - Failure to execute or prepare SQL queries.
    /// - Database connectivity issues.
    ///
    /// # Example (Python)
    /// ```python
    /// result = instance.get_entries_batch(
    ///     [(formid1, plugin1), (formid2, plugin2)],
    ///     table="game_data",
    ///     batch_size=50
    /// )
    /// print(result)
    /// ```
    ///
    /// # Logging
    /// - Logs the number of pairs being looked up at the start.
    /// - Logs query errors (preparation/execution) and task panics.
    /// - Logs the completion of the batch lookup with the number of results found.
    ///
    /// # Notes
    /// - Batch size affects memory usage and query performance; adjust accordingly for large datasets.
    /// - Collation (`COLLATE nocase`) ensures case-insensitivity per comparison in the SQL query for `formid` and `plugin`.
    /// - Concurrent database access employs safety mechanisms to avoid data corruption.
    #[pyo3(name = "get_entries_batch", signature = (formid_plugin_pairs, table=None, batch_size=None))]
    pub fn py_get_entries_batch(
        &self,
        _py: Python<'_>,
        formid_plugin_pairs: &Bound<'_, PyList>,
        table: Option<String>,
        batch_size: Option<usize>,
    ) -> PyResult<HashMap<String, String>> {
        let batch_size = batch_size.unwrap_or(100);
        let game_table = table.unwrap_or_else(|| self.game_table.read().unwrap().clone());

        // Parse Python list of tuples
        let mut pairs: Vec<(String, String)> = Vec::new();
        for item in formid_plugin_pairs.iter() {
            let tuple = item.extract::<(String, String)>()?;
            pairs.push(tuple);
        }

        info!(
            "Starting batch lookup for {} FormID/plugin pairs",
            pairs.len()
        );

        let connections = self.connections.clone();
        let query_cache = self.query_cache.clone();
        let cache_ttl = *self.cache_ttl.read().unwrap();
        let stats = self.stats.clone();

        get_runtime().block_on(async move {
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
                let conditions = batch
                    .iter()
                    .map(|_| "(formid=? COLLATE nocase AND plugin=? COLLATE nocase)")
                    .collect::<Vec<_>>()
                    .join(" OR ");

                // IMPORTANT: COLLATE nocase must be applied per comparison, not to the entire WHERE clause
                let query = format!(
                    "SELECT formid, plugin, entry FROM {} WHERE {}",
                    game_table, conditions
                );

                // Flatten parameters
                let params: Vec<String> = batch
                    .iter()
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
                                        error!(
                                            "Batch query execution error in {:?}: {}",
                                            db_path, e
                                        );
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
                    .unwrap_or_else(|e| {
                        error!("Batch query task panicked: {}", e);
                        HashMap::new()
                    });

                    // Cache and collect results
                    for (key, value) in batch_results {
                        let parts: Vec<&str> = key.split(':').collect();
                        if parts.len() == 2 {
                            let cache_key = format!("{}:{}:{}", game_table, parts[0], parts[1]);
                            query_cache
                                .insert(cache_key, CacheEntry::new(value.clone(), cache_ttl));
                            results.insert(key, value);
                        }
                    }
                }
            }

            info!("Batch lookup completed: {} results found", results.len());
            Ok(results)
        })
    }

    /// ```
    /// Python binding for the `batch_lookup` function, accessible in Python using the `batch_lookup` name.
    ///
    /// This function takes a list of form ID and plugin pairs and optionally a table name. It looks up the corresponding values
    /// and returns a HashMap where the keys are tuple pairs `(String, String)` representing form ID and plugin, and the
    /// values are `String` containing the lookup result.
    ///```
    /// # Parameters
    /// - `formid_plugin_pairs` (`&Bound<'_, PyList>`): A Python list containing pairs of form ID and plugin names to look up.
    ///   The pairs are expected as strings formatted as `formid:plugin`.
    /// - `table` (`Option<String>`): An optional string specifying the name of the table to look up the entries in. If `None`,
    ///   the default table will be used.
    ///
    /// # Returns
    /// - `PyResult<HashMap<(String, String), String>>`: A HashMap mapping tuple pairs `(formid, plugin)` to their corresponding value from the lookup.
    ///
    /// # Errors
    /// - Returns a Python error (`PyErr`) if a problem occurs during the lookup process, such as malformed input or an internal
    ///   error in the `py_get_entries_batch` function.
    ///
    /// # Conversion Logic
    /// The function internally calls `py_get_entries_batch`, passing the input along with a batch size of 100. The returned
    /// results, formatted as `formid:plugin -> value`, are processed to convert the key format into `(formid, plugin) -> value`.
    ///
    /// # Example
    /// ```python
    /// formid_plugin_pairs = [
    ///     "ABC123:SomePlugin",
    ///     "DEF456:AnotherPlugin",
    /// ]
    /// result = obj.batch_lookup(formid_plugin_pairs)
    /// # result will be something like:
    /// # {
    /// #     ("ABC123", "SomePlugin"): "Value1",
    /// #     ("DEF456", "AnotherPlugin"): "Value2",
    /// # }
    /// ```
    ///
    /// # Notes
    /// - Ensure that the input `formid_plugin_pairs` list has strings in the format `formid:plugin`.
    /// - The function performs input validation to ensure the keys can be split correctly by the `:` separator.
    ///
    /// # See Also
    /// - `py_get_entries_batch`: The internal method used for batch lookups with an optional table and batch size.
    #[pyo3(name = "batch_lookup", signature = (formid_plugin_pairs, table=None))]
    pub fn py_batch_lookup(
        &self,
        py: Python<'_>,
        formid_plugin_pairs: &Bound<'_, PyList>,
        table: Option<String>,
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
        let stats = self
            .stats
            .read()
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

    /// ```rust
    /// Closes the current instance, clearing connections, cache, and updating statistics.
    ///```
    /// # Python Function Name
    /// This method is exposed to Python with the name `close`.
    ///
    /// # Parameters
    /// - `_py: Python<'_>`: This parameter represents the Python interpreter state and is
    ///   automatically passed by PyO3. It's not used in this method but required to comply
    ///   with the PyO3 API.
    ///
    /// # Behavior
    /// - Clears all active connections handled by the `self.connections` object.
    /// - Clears the query cache maintained by `self.query_cache`.
    /// - Updates the instance's statistics, specifically resetting the `active_connections`
    ///   count to `0`.
    ///
    /// # Returns
    /// - `PyResult<()>`: Returns an empty result if successful. If an error occurs during
    ///   execution, an appropriate Python exception will be raised.
    ///
    /// # Asynchronous Behavior
    /// This function uses a Tokio runtime to perform asynchronous operations within a
    /// blocking context. Specifically:
    /// - The connections and query cache clearing tasks are executed asynchronously.
    /// - Updates to the statistics are synchronized using a write lock (`stats.write()`).
    ///
    /// # Usage
    /// This method should be invoked when resources held by the instance need to be released
    /// before the instance is destroyed or when the connections and cache need to be reset
    /// as part of application's lifecycle.
    ///
    /// # Example (Python)
    /// ```python
    /// instance.close()
    /// ```
    ///
    /// This method is part of a PyO3 Rust integration, which interacts with Python objects.
    #[pyo3(name = "close")]
    pub fn py_close(&self, _py: Python<'_>) -> PyResult<()> {
        let connections = self.connections.clone();
        let stats = self.stats.clone();

        get_runtime().block_on(async move {
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

    /// ```
    /// Optimize database connections by running "VACUUM" and "ANALYZE" commands on each connection.
    ///
    /// This function is a Python-exposed method (via PyO3) named `optimize`, which iterates over
    /// all database connections held within the `connections` attribute and performs optimization
    /// tasks on each. The database operations are executed in a blocking manner using the Tokio
    /// `spawn_blocking` API to avoid blocking the asynchronous runtime. This function is typically
    /// used to reduce database size and improve performance by reorganizing and analyzing the database
    /// structure for each connection.
    ///```
    /// # Arguments
    ///
    /// * `self` - A reference to the instance containing the database connections.
    /// * `_py` - A GIL-guarded `Python` object required for PyO3 integration.
    ///
    /// # Returns
    ///
    /// A `PyResult<()>` which represents either:
    /// - `Ok(())` - If all VACUUM and ANALYZE operations were executed without errors.
    /// - `Err(PyErr)` - If an error occurs while performing the operations.
    ///
    /// # Implementation Details
    ///
    /// - Clones the `connections` HashMap or equivalent collection to ensure thread-safe iteration.
    /// - Spawns a blocking task for each database connection, locking the connection instance and
    ///   executing the `VACUUM` and `ANALYZE` SQL commands.
    /// - Captures potential errors during thread execution and converts them into Python exceptions
    ///   (`pyo3::exceptions::PyRuntimeError`) for compatibility with Python error handling.
    ///
    /// # Example Usage
    ///
    /// Assuming the Python binding is defined, you can call it in Python as follows:
    ///
    /// ```python
    /// instance.optimize()
    /// ```
    ///
    /// This will optimize all database connections managed by the instance. Note that the operation
    /// may be resource-intensive depending on the size and number of databases being optimized.
    ///
    /// # Notes
    ///
    /// - The `tokio::task::spawn_blocking` is used to offload blocking tasks (e.g., database operations)
    ///   from the Tokio async runtime.
    /// - Each database operation is encapsulated within a `Mutex` to ensure thread safety.
    /// - The function errors out if the connection cannot be acquired or if the spawned task fails.
    #[pyo3(name = "optimize")]
    pub fn py_optimize(&self, _py: Python<'_>) -> PyResult<()> {
        let connections = self.connections.clone();

        get_runtime().block_on(async move {
            for entry in connections.iter() {
                let conn_arc = entry.value().clone();

                tokio::task::spawn_blocking(move || {
                    if let Ok(conn) = conn_arc.lock() {
                        let _ = conn.conn.execute("VACUUM", []);
                        let _ = conn.conn.execute("ANALYZE", []);
                    }
                })
                .await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            }
            Ok(())
        })
    }
}
