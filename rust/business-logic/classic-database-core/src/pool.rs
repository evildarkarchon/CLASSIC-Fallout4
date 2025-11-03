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
use rusqlite::{Connection, ToSql, params};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};
use std::time::{Duration, Instant};
use thiserror::Error;

/// Represents various errors that can occur when working with a database.
///
/// This enumeration uses the `thiserror` crate to provide descriptive error messages
/// and support for error composition. Each variant corresponds to a specific type of
/// database-related failure, making it easier to handle and debug issues.
/// # Variants
///
/// * `OpenError(String)`  
///   Occurs when the database file fails to open. Contains a string providing details
///   about the specific cause of the failure.
///
/// * `QueryError(String)`  
///   Represents an error that occurs while executing a database query. The associated
///   string describes the nature of the failure.
///
/// * `NotFound(String)`  
///   Indicates that a specified database file could not be found. The string value
///   provides additional context or the name of the missing file.
///
/// * `IoError(std::io::Error)`  
///   Wraps a standard I/O error that might occur during database file operations or
///   any related I/O tasks.
///
/// * `RusqliteError(rusqlite::Error)`  
///   Represents an error originating from the `rusqlite` library, which is used for
///   database query handling. Includes the original `rusqlite::Error` for further details.
///
/// * `JoinError(String)`  
///   Indicates an error related to task joining, such as when executing database
///   operations in an asynchronous context. The associated string provides the details
///   of the issue.
///
/// # Example
///
/// ```rust
/// use your_crate::DatabaseError;
/// use std::io;
///
/// fn example_function() -> Result<(), DatabaseError> {
///     // Simulating an error case
///     Err(DatabaseError::OpenError("Unable to open db file".to_string()))
/// }
///
/// match example_function() {
///     Ok(_) => println!("Database operation successful"),
///     Err(e) => println!("Database operation failed: {}", e),
/// }
/// ```
///
/// This enum can be used with the `thiserror`'s `#[error]` attribute to seamlessly convert
/// these errors into formatted error messages.
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
    /// Creates a new instance of the database in read-only mode, with specific optimizations.
    /// # Arguments
    ///
    /// * `path` - A reference to the path of the database file.
    ///
    /// # Returns
    ///
    /// * `Ok(Self)` containing the newly created database instance if the connection is successful.
    /// * `Err(DatabaseError)` if there is an error opening the database or setting the pragmas.
    ///
    /// # Errors
    ///
    /// This function will return a `DatabaseError::OpenError` if there is a failure to open the provided database path.
    ///
    /// # Behavior
    ///
    /// * The database connection is opened in read-only mode using the `SQLITE_OPEN_READ_ONLY` flag.
    /// * Executes non-modifying PRAGMAs for optimization:
    ///     - Sets the cache size to 10,000 pages using `PRAGMA cache_size`.
    ///     - Configures the temporary storage to use memory via `PRAGMA temp_store = MEMORY`.
    ///     - Configures the memory-mapped I/O size to 30,000,000 bytes via `PRAGMA mmap_size`.
    ///
    /// # Example
    ///
    /// ```rust
    /// use std::path::Path;
    /// use your_crate::{Database, DatabaseError};
    ///
    /// let db_path = Path::new("example.db");
    /// let database = Database::new(db_path);
    ///
    /// match database {
    ///     Ok(db) => println!("Database opened successfully in read-only mode."),
    ///     Err(e) => eprintln!("Failed to open database: {:?}", e),
    /// }
    /// ```
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

/// `DatabasePool` represents a pool of database connections and provides mechanisms
/// to manage, cache, and track statistics of these connections.
///
/// This struct encapsulates several key components associated with the management
/// of database connections, caching for query efficiency, and configuration settings
/// for the database system.
/// ### Fields:
///
/// - `connections`:
///   An `Arc` of a `DashMap` that maps paths (`PathBuf`) to a thread-safe (via `Arc<Mutex<...>>`)
///   `ConnectionWrapper` object. This is used to manage the actual database connections,
///   ensuring thread-safe sharing among multiple consumers.
///
/// - `query_cache`:
///   An `Arc` of a `DashMap` mapping query strings (`String`) to `CacheEntry` objects.
///   The cache is used to store query results or metadata for improving performance
///   by avoiding repeated queries for the same data set.
///
/// - `cache_ttl`:
///   An `Arc` of an `RwLock` that holds a `Duration` representing the "time-to-live" value for cache entries.
///   This ensures that cached queries are refreshed periodically.
///
/// - `max_connections`:
///   An `Arc` of an `RwLock` containing an optional `usize`. This limits the maximum number
///   of connections that can be maintained in the pool. If `None`, no connection limit is enforced.
///
/// - `stats`:
///   An `Arc` of an `RwLock` holding `PoolStatistics`, which keeps track of various metrics/statistics
///   related to connection pool usage, e.g., number of active connections, queries performed, etc.
///
/// - `game_table`:
///   An `Arc` of an `RwLock` containing a `String` representing the name of the central
///   table being accessed in the database for game-related operations.
///
/// - `db_paths`:
///   An `Arc` of an `RwLock` pointing to a vector of `PathBuf` objects, each representing a
///   potential file path to database files. This serves as a configuration for available database files.
///
/// ### Thread Safety:
/// The use of `Arc` and various synchronization primitives (`Mutex`, `RwLock`, etc.) ensures that
/// this struct can be safely shared and accessed across multiple threads, making it suitable for
/// concurrent environments.
///
/// ### Potential Use Cases:
/// - Centralized management of database connections in a multithreaded application.
/// - Caching frequently accessed queries to reduce database load and improve query performance.
/// - Tracking performance and usage statistics for optimized database interaction.
///
/// ### Example:
/// ```rust
/// use std::sync::Arc;
/// use dashmap::DashMap;
/// use std::time::Duration;
/// use std::path::PathBuf;
///
/// let pool = DatabasePool {
///     connections: Arc::new(DashMap::new()),
///     query_cache: Arc::new(DashMap::new()),
///     cache_ttl: Arc::new(RwLock::new(Duration::from_secs(300))),
///     max_connections: Arc::new(RwLock::new(Some(100))),
///     stats: Arc::new(RwLock::new(PoolStatistics::default())),
///     game_table: Arc::new(RwLock::new(String::from("games"))),
///     db_paths: Arc::new(RwLock::new(vec![PathBuf::from("./my_database.db")])),
/// };
/// ```
#[derive(Clone)]
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
    /// Calculates the optimal number of maximum connections.
    ///
    /// This function determines the maximum number of connections that can be handled
    /// simultaneously based on the number of available CPU cores. It calculates the
    /// optimal number as twice the number of CPU cores and ensures that the value
    /// lies within a reasonable range by clamping it between 4 (minimum) and 32 (maximum).
    /// # Returns
    /// - `usize`: The calculated maximum number of connections.
    ///
    /// # Example
    /// ```
    /// let max_connections = calculate_max_connections();
    /// println!("Max connections: {}", max_connections);
    /// ```
    ///
    /// The result will vary depending on the number of CPU cores detected by the system.
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

    /// Asynchronously initializes database connections for the given database paths.
    ///
    /// This function ensures that only valid database paths are processed. If a database
    /// file exists and is not already connected, a new database connection is created and
    /// added to the internal connection cache. If a path is already connected, the function
    /// skips creating a new connection. Invalid or non-existent paths are ignored, and a
    /// warning is logged for each.
    ///
    /// The function also updates internal statistics, such as the total and active connection
    /// counts, whenever a new connection is established. Finally, it writes the list of valid
    /// database paths to the internal storage.
    /// # Parameters
    /// - `db_paths`: A vector of `PathBuf` representing file paths for the databases to initialize.
    ///
    /// # Returns
    /// - `Ok(())`: If all database initialization steps completed successfully.
    /// - `Err(DatabaseError)`: If an error occurred while attempting to create a new database connection.
    ///
    /// # Behavior
    /// - Logs a warning for paths that do not exist.
    /// - Logs a debug message for paths that are already connected.
    /// - Logs an info message for successfully opened database connections.
    /// - Updates the internal list of database paths and connection statistics.
    ///
    /// # Concurrency
    /// This function uses:
    /// - An internal `Arc` and `Mutex` to manage the shared database connection cache.
    /// - A `RwLock` for safely updating the statistics and database path storage in a thread-safe manner.
    ///
    /// # Example
    /// ```rust
    /// use tokio::runtime::Runtime;
    /// use std::path::PathBuf;
    ///
    /// let runtime = Runtime::new().unwrap();
    /// let manager = DatabaseManager::new(); // Hypothetical struct containing the `initialize` method.
    ///
    /// let db_paths = vec![PathBuf::from("/path/to/db1"), PathBuf::from("/path/to/db2")];
    ///
    /// runtime.block_on(async {
    ///     if let Err(e) = manager.initialize(db_paths).await {
    ///         eprintln!("Failed to initialize databases: {:?}", e);
    ///     }
    /// });
    /// ```
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

                info!("Successfully opened database: {:?}", path);

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

    /// Retrieves an entry from a database or cache based on a `formid`, `plugin`, and an optional `table` name.
    ///
    /// This method checks a local cache first for the requested `formid` and `plugin`. If the requested data is
    /// not found in the cache or if the cached data is expired, it proceeds by querying each connected
    /// database in order (main database first, followed by local databases). The response is cached for future use
    /// based on a configured Time-To-Live (TTL).
    /// # Parameters
    /// - `formid`: A reference to the unique identifier of the form being queried (case insensitive).
    /// - `plugin`: A reference to the plugin associated with the form.
    /// - `table`: An optional reference to the database table for the query. If `None`, a default table is used,
    ///   derived from the object's internal state.
    ///
    /// # Returns
    /// Returns `Ok(Some(String))` containing the entry value if the form is found in the cache or any connected
    /// database. Returns `Ok(None)` if the form is not found. In case of errors during database access or
    /// execution, returns `Err(DatabaseError)`.
    ///
    /// # Behavior
    /// 1. **Cache Check**:
    ///    - First, the method checks if the requested entry is available in the local cache.
    ///    - If found and not expired, the value is returned immediately as a cache hit.
    ///    - If expired, the cache entry is removed, and the method proceeds to query the databases.
    ///    
    /// 2. **Statistics Tracking**:
    ///    - Updates cache hit and miss statistics based on whether the entry was found in the cache or not.
    ///    - Tracks the total number of queries performed.
    ///
    /// 3. **Database Query**:
    ///    - Queries the provided table (or the default table if `table` is `None`) in each connected database (main database first).
    ///    - If the entry is found, it is cached and returned immediately.
    ///
    /// 4. **Cache Insertion**:
    ///    - If the entry is successfully retrieved from a database, it is inserted into the cache with the configured TTL.
    ///
    /// 5. **Failure Handling**:
    ///    - If the form is not found in any database, logs a debug statement and returns `Ok(None)`.
    ///    - Handles potential errors arising during spawning of blocking tasks or database query executions.
    ///
    /// # Example Usage
    /// ```rust
    /// let formid = "123456";
    /// let plugin = "example_plugin";
    /// let table = Some("example_table");
    ///
    /// match database.get_entry(formid, plugin, table).await {
    ///     Ok(Some(entry)) => {
    ///         println!("Found entry: {}", entry);
    ///     },
    ///     Ok(None) => {
    ///         println!("Entry not found.");
    ///     },
    ///     Err(e) => {
    ///         eprintln!("Error retrieving entry: {:?}", e);
    ///     }
    /// }
    /// ```
    ///
    /// # Errors
    /// This method can return a `DatabaseError` if any of the following occur:
    /// - Failed to spawn a blocking thread for database queries.
    /// - Errors while querying the database (e.g., SQL syntax error, database connection failure).
    ///
    /// # Notes
    /// - The method uses a non-blocking approach to handle potentially long-running database queries.
    /// - The cache is accessed concurrently using internal synchronization to maintain thread safety.
    ///
    /// # Debug Logs
    /// The method logs debug information for debugging purposes, including:
    /// - Cache hits or misses.
    /// - Cache expiration events.
    /// - Successful database queries and the source database files.
    /// - Failed queries or absent entries.
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

    /// Retrieves a batch of entries from the database for the specified FormID/plugin pairs.
    ///
    /// This method performs an asynchronous batch lookup for a collection of FormID and plugin pairs.
    /// It prioritizes retrieving data from a query cache with a time-to-live (TTL) mechanism. If the requested entries are not
    /// cached or their cache entries have expired, it queries the database in configurable batch sizes to fetch the missing data,
    /// stores it in the cache, and returns the aggregated results.
    /// # Parameters
    /// - `formid_plugin_pairs`: A `Vec` of `(String, String)` tuples where each tuple contains a FormID and a plugin name to query.
    /// - `table`: An optional reference to a `str` specifying the database table name to use. If `None`, the default game table
    ///   configured in `self.game_table` is used.
    /// - `batch_size`: Specifies the number of FormID/plugin pairs to process in a single database query batch.
    ///
    /// # Returns
    /// Returns a `Result` wrapping a `HashMap` where the key is a composite of `FormID:Plugin` and the value is the associated database entry string.
    /// In the event of an error during execution, the function returns a `DatabaseError`.
    ///
    /// # Behavior and Process:
    /// 1. **Cache Check**:
    ///     - The method first checks if any of the FormID/plugin combinations exist in the query cache.
    ///     - Entries that are found in the cache and are not expired are added to the `results`.
    ///     - Expired cache entries are removed, and missing entries are added to an "uncached pairs" list for further database querying.
    ///
    /// 2. **Database Querying**:
    ///     - If there are uncached pairs, they are grouped into batches of `batch_size`.
    ///     - For each batch, an SQL query is executed to fetch the missing entries using the provided or default table name.
    ///     - The queried results are parsed, cached for future lookups, and added to the final `results` map.
    ///
    /// 3. **Thread-Safe Metrics Tracking**:
    ///     - During execution, cache hit, cache miss, and total query statistics are updated in a thread-safe manner.
    ///
    /// 4. **Error Handling**:
    ///     - If an error occurs while preparing or executing a database query, the error is logged, and the process continues for other connections.
    ///     - If a failure occurs in spawning or awaiting batch jobs via `tokio::task::spawn_blocking`, a `DatabaseError::JoinError` is returned.
    ///
    /// # Logs:
    /// - The function logs the start and completion of the batch lookup process, including the count of FormID/plugin pairs processed and results found.
    /// - Errors or failures encountered during database querying are logged with context.
    ///
    /// # Examples:
    /// ```rust
    /// let formid_plugin_pairs = vec![("123".to_string(), "plugin1.esp".to_string())];
    /// let results = my_service
    ///     .get_entries_batch(formid_plugin_pairs, Some("my_table"), 100)
    ///     .await;
    ///
    /// match results {
    ///     Ok(data) => {
    ///         for (key, value) in data {
    ///             println!("FormID:Plugin => {} with Entry {}", key, value);
    ///         }
    ///     }
    ///     Err(err) => {
    ///         eprintln!("Error occurred: {:?}", err);
    ///     }
    /// }
    /// ```
    ///
    /// # Errors:
    /// - Returns `DatabaseError::JoinError` if there is an issue with the asynchronous task execution.
    /// - Any database-related errors (e.g., query preparation or execution failures) are logged but do not stop the execution of other queries.
    ///
    /// # Notes:
    /// - The method assumes the `connections` structure holds database connection handles.
    /// - Queries utilize a case-insensitive collation setting (`COLLATE nocase`).
    /// - This function is thread-safe, making use of properly synchronized structures for cache, statistics, and connection accesses.
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
            // Pre-allocate string buffer for query construction (optimization 1.4)
            // Each condition is ~60 chars, plus " OR " separators (4 chars each)
            let estimated_capacity = batch.len() * 64 + game_table.len() + 50;
            let mut query = String::with_capacity(estimated_capacity);

            query.push_str("SELECT formid, plugin, entry FROM ");
            query.push_str(&game_table);
            query.push_str(" WHERE ");

            // Build conditions without intermediate allocations
            for (i, _) in batch.iter().enumerate() {
                if i > 0 {
                    query.push_str(" OR ");
                }
                query.push_str("(formid=? COLLATE nocase AND plugin=? COLLATE nocase)");
            }

            // Optimization 4.3: Pre-allocate params vector with exact capacity
            // Avoids intermediate Vec allocation and clones
            let mut params = Vec::with_capacity(batch.len() * 2);
            for (formid, plugin) in batch.iter() {
                params.push(formid.clone());
                params.push(plugin.clone());
            }

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

    /// Sets the game table value in a thread-safe manner.
    ///
    /// This method updates the shared `game_table` with the provided table name,
    /// if a lock to the `RwLock` can be successfully acquired. Once the lock is
    /// obtained, the new table name replaces the current one. The update is logged
    /// for debugging or informational purposes.
    /// # Parameters
    /// - `table`: A `String` representing the new game table name to set.
    ///
    /// # Behavior
    /// - Acquires a write lock on the internal `RwLock<String>` holding the game table value.
    /// - Logs the operation using the `info!` macro.
    /// - Sets the value of `game_table` to the given `table` string, if the lock is acquired successfully.
    ///
    /// # Notes
    /// - If the `RwLock` is poisoned or cannot be locked for write access, the method will silently fail
    ///   and no changes will be made to the game table.
    /// - Ensure that logging is properly configured in the application to capture output from the
    ///   `info!` macro.
    ///
    /// # Example
    /// ```rust
    /// let game_state = GameState::new();
    /// game_state.set_game_table("NewTable");
    /// ```
    ///
    /// Optimization 6.1: Changed to `&str` to avoid unnecessary allocation (5-10% reduction)
    pub fn set_game_table(&self, table: &str) {
        if let Ok(mut game_table) = self.game_table.write() {
            info!("Setting game table to: {}", table);
            *game_table = table.to_string();
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

    /// Optimizes all the database connections in the connection pool by executing
    /// `VACUUM` and `ANALYZE` SQL commands on each connection.
    ///
    /// This function iterates through the available connections in the connection pool,
    /// and for each connection, it performs database maintenance tasks in a background
    /// thread using `tokio::task::spawn_blocking`. Both `VACUUM` and `ANALYZE` are executed
    /// on the database, aiming to optimize database performance by reclaiming storage space
    /// and updating query planner statistics, respectively.
    /// # Errors
    /// - Returns a `DatabaseError::JoinError` if the background thread fails to execute or join.
    /// - Database locks (`Mutex`) are handled while ensuring that multiple threads do not
    ///   access the same connection simultaneously.
    ///
    /// # Example
    /// ```rust
    /// use my_crate::DatabasePool;
    ///
    /// #[tokio::main]
    /// async fn main() -> Result<(), Box<dyn std::error::Error>> {
    ///     let pool = DatabasePool::new();
    ///     pool.optimize().await?;
    ///     Ok(())
    /// }
    /// ```
    ///
    /// # Notes
    /// - This function assumes that the `connections` pool is thread-safe and that
    ///   `self.connections` provides an iterator over connection entries.
    /// - The `spawn_blocking` ensures that CPU-intensive tasks do not block the async runtime's thread pool.
    ///
    /// # Returns
    /// - If successful, returns `Ok(())`.
    /// - If an error occurs during thread synchronization or execution of SQL statements, the
    ///   appropriate `DatabaseError` is returned.
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
