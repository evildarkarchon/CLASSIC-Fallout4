//! Database bindings (classic-database-core)
//!
//! Exposes DatabasePool class with async query methods, caching, and statistics
//! to JavaScript/TypeScript.
//!
//! ## Architecture
//! This is a THIN ADAPTER layer that:
//! - Delegates all business logic to classic-database-core
//! - Only handles JavaScript <-> Rust type conversions
//! - Respects the ONE RUNTIME RULE via `classic_shared_core::get_runtime()`
//!
//! ## Usage
//! ```typescript
//! import { DatabasePool, DEFAULT_CACHE_TTL, BATCH_CACHE_TTL } from "../index.js";
//!
//! const pool = new DatabasePool("Fallout4");
//! await pool.initialize(["path/to/main.db", "path/to/local.db"]);
//!
//! const entry = await pool.getEntry("012345", "Skyrim.esm");
//! if (entry !== undefined) {
//!   console.log(`Found: ${entry}`);
//! }
//!
//! const stats = pool.getStats();
//! console.log(`Queries: ${stats.totalQueries}, Hit rate: ${stats.cacheHitRate}%`);
//!
//! await pool.close();
//! ```

use classic_database_core::{
    BATCH_CACHE_TTL_SECS, DEFAULT_CACHE_TTL_SECS, DatabasePool, MAX_CACHE_TTL_SECS,
};
use napi::bindgen_prelude::*;
use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Duration;

/// Convert any Display error to a napi::Error
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

// ============================================================================
// 1. Cache TTL Constants
// ============================================================================

/// Default cache TTL for single log scanning (300 seconds / 5 minutes).
#[napi]
pub const DEFAULT_CACHE_TTL: u32 = DEFAULT_CACHE_TTL_SECS as u32;

/// Extended cache TTL for batch log scanning (1800 seconds / 30 minutes).
#[napi]
pub const BATCH_CACHE_TTL: u32 = BATCH_CACHE_TTL_SECS as u32;

/// Maximum recommended cache TTL (3600 seconds / 60 minutes).
#[napi]
pub const MAX_CACHE_TTL: u32 = MAX_CACHE_TTL_SECS as u32;

// ============================================================================
// 2. Cache TTL Helper Functions
// ============================================================================

/// Get the default cache TTL for single log operations (300 seconds).
#[napi]
pub fn get_default_cache_ttl() -> u32 {
    DEFAULT_CACHE_TTL_SECS as u32
}

/// Get the recommended cache TTL for batch log operations (1800 seconds / 30 min).
#[napi]
pub fn get_batch_cache_ttl() -> u32 {
    BATCH_CACHE_TTL_SECS as u32
}

/// Get the maximum recommended cache TTL (3600 seconds / 60 min).
#[napi]
pub fn get_max_cache_ttl() -> u32 {
    MAX_CACHE_TTL_SECS as u32
}

// ============================================================================
// 3. DTO Structs
// ============================================================================

/// Pool performance statistics.
///
/// Returned by `DatabasePool.getStats()`.
#[napi(object)]
pub struct JsPoolStatistics {
    /// Total number of queries executed
    pub total_queries: u32,
    /// Number of queries served from cache
    pub cache_hits: u32,
    /// Number of queries that required database access
    pub cache_misses: u32,
    /// Total number of connections created
    pub total_connections: u32,
    /// Number of currently active connections
    pub active_connections: u32,
    /// Cache hit rate as a percentage (0-100)
    pub cache_hit_rate: f64,
}

/// A single entry from a batch query result.
///
/// Used in the structured batch lookup return type.
#[napi(object)]
pub struct JsBatchEntry {
    /// The FormID that was queried
    pub form_id: String,
    /// The plugin name that was queried
    pub plugin: String,
    /// The database entry text (undefined if not found)
    pub entry: Option<String>,
}

// ============================================================================
// 4. DatabasePool Class
// ============================================================================

/// Async SQLite database pool for FormID lookups.
///
/// Wraps `classic-database-core::DatabasePool` with connection pooling,
/// WAL mode, TTL-based caching, and batch query optimization.
///
/// ## Lifecycle
/// 1. Create with `new DatabasePool(gameTable, options?)`
/// 2. Initialize with `await pool.initialize(dbPaths)`
/// 3. Query with `await pool.getEntry(...)` or `await pool.getEntriesBatch(...)`
/// 4. Close with `await pool.close()` before application exit
#[napi]
pub struct JsDatabasePool {
    inner: DatabasePool,
}

#[napi]
impl JsDatabasePool {
    /// Create a new database pool.
    ///
    /// @param gameTable - The game table name (e.g., "Fallout4", "Skyrim").
    /// @param maxConnections - Optional maximum connections per pool (auto-calculated if omitted).
    /// @param cacheTtlSeconds - Optional cache TTL in seconds (defaults to 1800 / 30 min for batch ops).
    #[napi(constructor)]
    pub fn new(
        game_table: String,
        max_connections: Option<u32>,
        cache_ttl_seconds: Option<u32>,
    ) -> Self {
        let ttl = Duration::from_secs(
            cache_ttl_seconds
                .map(|s| s as u64)
                .unwrap_or(BATCH_CACHE_TTL_SECS),
        );
        let max_conn = max_connections.map(|c| c as usize);

        Self {
            inner: DatabasePool::new(max_conn, ttl, game_table),
        }
    }

    /// Initialize database connections for the given file paths.
    ///
    /// Skips paths that do not exist (logs a warning). Creates connection pools
    /// with WAL mode and read-only access for each valid database file.
    ///
    /// @param dbPaths - Array of filesystem paths to SQLite database files.
    #[napi]
    pub async fn initialize(&self, db_paths: Vec<String>) -> Result<()> {
        let inner = self.inner.clone();
        let paths: Vec<PathBuf> = db_paths.into_iter().map(PathBuf::from).collect();

        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.initialize(paths).await })
            .await
            .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
            .map_err(to_napi_err)
    }

    /// Look up a single FormID entry in the database.
    ///
    /// Searches all initialized database files. Results are cached with TTL.
    /// Returns `undefined` if the FormID/plugin combination is not found.
    ///
    /// @param formId - The FormID to look up (e.g., "012345").
    /// @param plugin - The plugin name (e.g., "Skyrim.esm"). Case-insensitive matching.
    /// @param table - Optional table name override (uses the pool's game table if omitted).
    #[napi]
    pub async fn get_entry(
        &self,
        form_id: String,
        plugin: String,
        table: Option<String>,
    ) -> Result<Option<String>> {
        let inner = self.inner.clone();

        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.get_entry(&form_id, &plugin, table.as_deref()).await })
            .await
            .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
            .map_err(to_napi_err)
    }

    /// Batch lookup for multiple FormID/plugin pairs.
    ///
    /// Uses UNION ALL queries and parallel execution across all database files
    /// for optimal performance. Results are cached with TTL.
    ///
    /// Returns an object mapping `"formId:plugin"` keys to entry strings.
    /// Missing entries are omitted from the result (not set to undefined).
    ///
    /// @param pairs - Array of `[formId, plugin]` tuples.
    /// @param table - Optional table name override.
    /// @param batchSize - Maximum pairs per query batch (default: 100).
    #[napi]
    pub async fn get_entries_batch(
        &self,
        pairs: Vec<Vec<String>>,
        table: Option<String>,
        batch_size: Option<u32>,
    ) -> Result<HashMap<String, String>> {
        let inner = self.inner.clone();

        // Convert Vec<Vec<String>> (JS array of arrays) to Vec<(String, String)>
        let mut typed_pairs: Vec<(String, String)> = Vec::with_capacity(pairs.len());
        for pair in &pairs {
            if pair.len() != 2 {
                return Err(napi::Error::from_reason(
                    "Each pair must be an array of exactly [formId, plugin]",
                ));
            }
            typed_pairs.push((pair[0].clone(), pair[1].clone()));
        }

        let batch_sz = batch_size.map(|s| s as usize).unwrap_or(100);

        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move {
                inner
                    .get_entries_batch(typed_pairs, table.as_deref(), batch_sz)
                    .await
            })
            .await
            .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
            .map_err(to_napi_err)
    }

    /// Batch lookup returning structured results with found/not-found status.
    ///
    /// Unlike `getEntriesBatch` which returns a flat map, this method returns
    /// an array of `JsBatchEntry` objects, one per input pair, with `entry`
    /// set to `undefined` for missing results.
    ///
    /// @param pairs - Array of `[formId, plugin]` tuples.
    /// @param table - Optional table name override.
    #[napi]
    pub async fn batch_lookup(
        &self,
        pairs: Vec<Vec<String>>,
        table: Option<String>,
    ) -> Result<Vec<JsBatchEntry>> {
        let inner = self.inner.clone();

        // Convert Vec<Vec<String>> to Vec<(String, String)>
        let mut typed_pairs: Vec<(String, String)> = Vec::with_capacity(pairs.len());
        for pair in &pairs {
            if pair.len() != 2 {
                return Err(napi::Error::from_reason(
                    "Each pair must be an array of exactly [formId, plugin]",
                ));
            }
            typed_pairs.push((pair[0].clone(), pair[1].clone()));
        }

        // Keep a copy for building results
        let input_pairs = typed_pairs.clone();

        let handle = classic_shared_core::get_runtime().handle().clone();
        let results = handle
            .spawn(async move {
                inner
                    .get_entries_batch(typed_pairs, table.as_deref(), 100)
                    .await
            })
            .await
            .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
            .map_err(to_napi_err)?;

        // Build structured result preserving input order
        let entries = input_pairs
            .into_iter()
            .map(|(form_id, plugin)| {
                let key = format!("{}:{}", form_id, plugin);
                let entry = results.get(&key).cloned();
                JsBatchEntry {
                    form_id,
                    plugin,
                    entry,
                }
            })
            .collect();

        Ok(entries)
    }

    /// Set the active game table name.
    ///
    /// @param table - Table name (e.g., "Fallout4", "Skyrim").
    #[napi]
    pub fn set_game_table(&self, table: String) {
        self.inner.set_game_table(&table);
    }

    /// Get the current game table name.
    #[napi]
    pub fn get_game_table(&self) -> String {
        self.inner.get_game_table()
    }

    /// Clear cache entries.
    ///
    /// @param expiredOnly - If true, only remove expired entries; if false, clear all.
    /// @returns Number of cache entries removed.
    #[napi]
    pub fn clear_cache(&self, expired_only: Option<bool>) -> u32 {
        self.inner.clear_cache(expired_only.unwrap_or(false)) as u32
    }

    /// Set the cache time-to-live in seconds.
    ///
    /// New cache entries will use this TTL. Existing entries keep their original TTL.
    ///
    /// @param seconds - TTL in seconds.
    #[napi]
    pub fn set_cache_ttl(&self, seconds: u32) {
        self.inner
            .set_cache_ttl(Duration::from_secs(seconds as u64));
    }

    /// Get the current number of entries in the query cache.
    #[napi]
    pub fn cache_size(&self) -> u32 {
        self.inner.cache_size() as u32
    }

    /// Get the maximum number of connections per pool.
    ///
    /// Returns `undefined` if not configured (should not happen after construction).
    #[napi]
    pub fn get_max_connections(&self) -> Option<u32> {
        self.inner.get_max_connections().map(|c| c as u32)
    }

    /// Set the maximum number of connections per pool.
    ///
    /// Only affects pools created after this call; existing pools keep their size.
    ///
    /// @param maxConnections - New maximum connection count.
    #[napi]
    pub fn set_max_connections(&self, max_connections: u32) {
        self.inner.set_max_connections(max_connections as usize);
    }

    /// Recalculate optimal connection count based on current CPU cores.
    ///
    /// Sets max_connections to `CPU_cores * 4`, clamped to 8-64.
    #[napi]
    pub fn recalculate_max_connections(&self) {
        self.inner.recalculate_max_connections();
    }

    /// Check if any database pools are available.
    ///
    /// Returns true if the pool has been initialized and has at least one connection.
    #[napi]
    pub fn is_available(&self) -> bool {
        self.inner.is_available()
    }

    /// Get pool performance statistics.
    ///
    /// Returns an object with query counts, cache metrics, and hit rate.
    #[napi]
    pub fn get_stats(&self) -> Result<JsPoolStatistics> {
        let stats = self.inner.get_stats().map_err(to_napi_err)?;

        let cache_hit_rate = if stats.total_queries > 0 {
            (stats.cache_hits as f64 / stats.total_queries as f64) * 100.0
        } else {
            0.0
        };

        Ok(JsPoolStatistics {
            total_queries: stats.total_queries as u32,
            cache_hits: stats.cache_hits as u32,
            cache_misses: stats.cache_misses as u32,
            total_connections: stats.total_connections as u32,
            active_connections: stats.active_connections as u32,
            cache_hit_rate,
        })
    }

    /// Run ANALYZE on all connected databases for query optimization.
    ///
    /// This is a lightweight operation safe for read-only databases.
    #[napi]
    pub async fn optimize(&self) -> Result<()> {
        let inner = self.inner.clone();

        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.optimize().await })
            .await
            .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
            .map_err(to_napi_err)
    }

    /// Close all database connections and clear caches.
    ///
    /// Should be called before application exit to ensure proper cleanup of
    /// SQLite connections and WAL checkpointing.
    #[napi]
    pub async fn close(&self) -> Result<()> {
        let inner = self.inner.clone();

        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.close().await })
            .await
            .map_err(|e| to_napi_err(format!("Runtime error: {e}")))?
            .map_err(to_napi_err)
    }
}
