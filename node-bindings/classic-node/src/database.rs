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

use crate::runtime::spawn_result;
use classic_database_core::{
    BATCH_CACHE_TTL_SECS,
    DEFAULT_CACHE_CLEANUP_INTERVAL_SECS as CORE_DEFAULT_CACHE_CLEANUP_INTERVAL_SECS,
    DEFAULT_CACHE_CLEANUP_OP_THRESHOLD as CORE_DEFAULT_CACHE_CLEANUP_OP_THRESHOLD,
    DEFAULT_CACHE_TTL_SECS, DEFAULT_QUERY_CACHE_CAPACITY as CORE_DEFAULT_QUERY_CACHE_CAPACITY,
    DatabasePool, FormIdValueLookup as CoreFormIdValueLookup, FormIdValueLookupEntry,
    FormIdValueLookupError, FormIdValueLookupInMemoryReply, FormIdValueLookupOutcome,
    MAX_CACHE_TTL_SECS,
};
use napi::bindgen_prelude::{JsObjectValue, ToNapiValue, *};
use napi::{Env, JsError, JsValue, Status, Task};
use std::collections::HashMap;
use std::convert::Infallible;
use std::future::Future;
use std::path::PathBuf;
use std::sync::Arc;
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

/// Default query cache capacity.
#[napi]
pub const DEFAULT_QUERY_CACHE_CAPACITY: u32 = CORE_DEFAULT_QUERY_CACHE_CAPACITY as u32;

/// Default proactive cleanup operation threshold.
#[napi]
pub const DEFAULT_CACHE_CLEANUP_THRESHOLD: u32 = CORE_DEFAULT_CACHE_CLEANUP_OP_THRESHOLD as u32;

/// Default proactive cleanup interval in seconds.
#[napi]
pub const DEFAULT_CACHE_CLEANUP_INTERVAL: u32 = CORE_DEFAULT_CACHE_CLEANUP_INTERVAL_SECS as u32;

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

/// Get default query cache capacity.
#[napi]
pub fn get_default_query_cache_capacity() -> u32 {
    CORE_DEFAULT_QUERY_CACHE_CAPACITY as u32
}

/// Get default proactive cleanup threshold (operations).
#[napi]
pub fn get_default_cache_cleanup_threshold() -> u32 {
    CORE_DEFAULT_CACHE_CLEANUP_OP_THRESHOLD as u32
}

/// Get default proactive cleanup interval in seconds.
#[napi]
pub fn get_default_cache_cleanup_interval() -> u32 {
    CORE_DEFAULT_CACHE_CLEANUP_INTERVAL_SECS as u32
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
    /// Number of cache entries evicted due to capacity pressure
    pub cache_evictions: u32,
    /// Number of proactive cleanup runs performed
    pub cleanup_runs: u32,
    /// Number of entries removed by proactive cleanup
    pub cleanup_removed: u32,
    /// Configured global connection budget
    pub configured_connection_budget: u32,
    /// Effective global budget after allocation/clamp policy
    pub effective_connection_budget: u32,
    /// Number of active pools in the allocation plan
    pub active_pool_count: u32,
    /// Minimum per-pool allocation
    pub min_pool_allocation: u32,
    /// Maximum per-pool allocation
    pub max_pool_allocation: u32,
    /// Difference between max/min per-pool allocation
    pub allocation_spread: u32,
    /// Current cache capacity
    pub cache_capacity: u32,
    /// Current proactive cleanup threshold (operation count)
    pub cleanup_threshold: u32,
    /// Current proactive cleanup interval in seconds
    pub cleanup_interval_seconds: u32,
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

/// One owned reply used to configure a deterministic in-memory FormID lookup.
///
/// Omit both optional fields for a successful miss. Set `value` for a hit
/// (including a blank value when testing malformed adapter data), or set
/// `operationalFailure` for a deterministic hard failure.
#[derive(Clone)]
#[napi(object)]
pub struct JsFormIdValueLookupEntry {
    /// The FormID suffix to match.
    pub formid: String,
    /// The plugin name to match case-insensitively.
    pub plugin: String,
    /// Successful owned value, or `undefined` for a configured miss.
    pub value: Option<String>,
    /// Deterministic operational failure detail.
    pub operational_failure: Option<String>,
}

/// Stable semantic category returned by a successful strict lookup.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsFormIdValueLookupOutcomeKind {
    /// Lookup was explicitly disabled.
    #[napi(value = "disabled")]
    Disabled,
    /// Lookup completed successfully without a value.
    #[napi(value = "missing")]
    Missing,
    /// Lookup completed successfully with an owned value.
    #[napi(value = "found")]
    Found,
}

/// Owned semantic result of one strict FormID lookup.
#[derive(Clone)]
#[napi(object)]
pub struct JsFormIdValueLookupOutcome {
    /// Stable success category.
    pub kind: JsFormIdValueLookupOutcomeKind,
    /// Owned value for `found`; `undefined` for `disabled` and `missing`.
    pub value: Option<String>,
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
    /// @param maxConnections - Optional global connection budget across active pools
    ///                         (auto-calculated if omitted).
    /// @param cacheTtlSeconds - Optional cache TTL in seconds (defaults to 1800 / 30 min for batch ops).
    #[napi(constructor)]
    pub fn new(
        game_table: String,
        max_connections: Option<u32>,
        cache_ttl_seconds: Option<u32>,
        cache_capacity: Option<u32>,
        cleanup_threshold: Option<u32>,
        cleanup_interval_seconds: Option<u32>,
    ) -> Self {
        let ttl = Duration::from_secs(
            cache_ttl_seconds
                .map(|s| s as u64)
                .unwrap_or(BATCH_CACHE_TTL_SECS),
        );
        let max_conn = max_connections.map(|c| c as usize);
        let inner = DatabasePool::new(max_conn, ttl, game_table);

        if let Some(capacity) = cache_capacity {
            inner.set_cache_capacity(capacity as usize);
        }
        if let Some(threshold) = cleanup_threshold {
            inner.set_cache_cleanup_threshold(threshold as u64);
        }
        if let Some(interval) = cleanup_interval_seconds {
            inner.set_cache_cleanup_interval(Duration::from_secs(interval as u64));
        }

        Self { inner }
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

        spawn_result(
            async move { inner.initialize(paths).await },
            |error| to_napi_err(format!("Runtime error: {error}")),
            to_napi_err,
        )
        .await
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

        spawn_result(
            async move { inner.get_entry(&form_id, &plugin, table.as_deref()).await },
            |error| to_napi_err(format!("Runtime error: {error}")),
            to_napi_err,
        )
        .await
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

        spawn_result(
            async move {
                inner
                    .get_entries_batch(typed_pairs, table.as_deref(), batch_sz)
                    .await
            },
            |error| to_napi_err(format!("Runtime error: {error}")),
            to_napi_err,
        )
        .await
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

        let results = spawn_result(
            async move {
                inner
                    .get_entries_batch(typed_pairs, table.as_deref(), 100)
                    .await
            },
            |error| to_napi_err(format!("Runtime error: {error}")),
            to_napi_err,
        )
        .await?;

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

    /// Get configured cache capacity.
    #[napi]
    pub fn get_cache_capacity(&self) -> u32 {
        self.inner.get_cache_capacity() as u32
    }

    /// Set cache capacity.
    #[napi]
    pub fn set_cache_capacity(&self, capacity: u32) {
        self.inner.set_cache_capacity(capacity as usize);
    }

    /// Get proactive cleanup threshold (operation count).
    #[napi]
    pub fn get_cache_cleanup_threshold(&self) -> u32 {
        self.inner.get_cache_cleanup_threshold() as u32
    }

    /// Set proactive cleanup threshold (operation count).
    #[napi]
    pub fn set_cache_cleanup_threshold(&self, threshold: u32) {
        self.inner.set_cache_cleanup_threshold(threshold as u64);
    }

    /// Get proactive cleanup interval in seconds.
    #[napi]
    pub fn get_cache_cleanup_interval(&self) -> u32 {
        self.inner.get_cache_cleanup_interval().as_secs() as u32
    }

    /// Set proactive cleanup interval in seconds.
    #[napi]
    pub fn set_cache_cleanup_interval(&self, seconds: u32) {
        self.inner
            .set_cache_cleanup_interval(Duration::from_secs(seconds as u64));
    }

    /// Get the current number of entries in the query cache.
    #[napi]
    pub fn cache_size(&self) -> u32 {
        self.inner.cache_size() as u32
    }

    /// Get the configured global connection budget.
    ///
    /// Returns `undefined` if not configured (should not happen after construction).
    #[napi]
    pub fn get_max_connections(&self) -> Option<u32> {
        self.inner.get_max_connections().map(|c| c as u32)
    }

    /// Set the global connection budget (config-only).
    ///
    /// Existing pools are not rebuilt automatically. Call `rebalanceConnections()`
    /// to apply immediately.
    ///
    /// @param maxConnections - New global connection budget.
    #[napi]
    pub fn set_max_connections(&self, max_connections: u32) {
        self.inner.set_max_connections(max_connections as usize);
    }

    /// Recalculate optimal global connection budget based on current CPU cores.
    ///
    /// Sets the configured budget to `CPU_cores * 4`, clamped to 8-64.
    #[napi]
    pub fn recalculate_max_connections(&self) {
        self.inner.recalculate_max_connections();
    }

    /// Explicitly rebuild active pools using the current global budget.
    #[napi]
    pub async fn rebalance_connections(&self) -> Result<()> {
        let inner = self.inner.clone();

        spawn_result(
            async move { inner.rebalance_connections().await },
            |error| to_napi_err(format!("Runtime error: {error}")),
            to_napi_err,
        )
        .await
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
            cache_evictions: stats.cache_evictions as u32,
            cleanup_runs: stats.cleanup_runs as u32,
            cleanup_removed: stats.cleanup_removed as u32,
            configured_connection_budget: stats.configured_connection_budget as u32,
            effective_connection_budget: stats.effective_connection_budget as u32,
            active_pool_count: stats.active_pool_count as u32,
            min_pool_allocation: stats.min_pool_allocation as u32,
            max_pool_allocation: stats.max_pool_allocation as u32,
            allocation_spread: stats.allocation_spread as u32,
            cache_capacity: self.inner.get_cache_capacity() as u32,
            cleanup_threshold: self.inner.get_cache_cleanup_threshold() as u32,
            cleanup_interval_seconds: self.inner.get_cache_cleanup_interval().as_secs() as u32,
            cache_hit_rate,
        })
    }

    /// Run ANALYZE on all connected databases for query optimization.
    ///
    /// This is a lightweight operation safe for read-only databases.
    #[napi]
    pub async fn optimize(&self) -> Result<()> {
        let inner = self.inner.clone();

        spawn_result(
            async move { inner.optimize().await },
            |error| to_napi_err(format!("Runtime error: {error}")),
            to_napi_err,
        )
        .await
    }

    /// Close all database connections and clear caches.
    ///
    /// Should be called before application exit to ensure proper cleanup of
    /// SQLite connections and WAL checkpointing.
    #[napi]
    pub async fn close(&self) -> Result<()> {
        let inner = self.inner.clone();

        spawn_result(
            async move { inner.close().await },
            |error| to_napi_err(format!("Runtime error: {error}")),
            to_napi_err,
        )
        .await
    }
}

// ============================================================================
// 5. Strict FormID Value Lookup Class
// ============================================================================

/// Opaque owned facade for strict callback-free FormID Value Lookup adapters.
///
/// Construct instances through `disabled`, `inMemory`, `sqlite`, or
/// `fromSharedPool`. Successful operations keep disabled, missing, and found
/// outcomes distinct; malformed adapter data and operational failures reject
/// with stable error metadata.
#[napi]
pub struct JsFormIdValueLookup {
    inner: CoreFormIdValueLookup,
}

#[napi]
impl JsFormIdValueLookup {
    /// Creates a lookup that explicitly performs no value resolution.
    #[napi(factory)]
    pub fn disabled() -> Self {
        Self {
            inner: CoreFormIdValueLookup::disabled(),
        }
    }

    /// Creates a deterministic lookup from fully owned entries.
    ///
    /// Each entry must set at most one of `value` and `operationalFailure`.
    /// Omitting both configures a successful miss for that key.
    ///
    /// @param entries - Owned deterministic replies keyed by FormID and plugin.
    #[napi(factory)]
    pub fn in_memory(entries: Vec<JsFormIdValueLookupEntry>) -> Result<Self> {
        let entries = entries
            .into_iter()
            .map(formid_lookup_entry_to_core)
            .collect::<Result<Vec<_>>>()?;
        Ok(Self {
            inner: CoreFormIdValueLookup::in_memory(entries),
        })
    }

    /// Opens one owned SQLite lookup adapter on the shared CLASSIC runtime.
    ///
    /// @param databasePath - Existing SQLite database file.
    /// @param gameTable - Game table name such as `Fallout4`.
    /// @throws an error with stable `code`, `formid`, `plugin`, and `message`
    /// metadata when adapter initialization fails.
    #[napi(factory)]
    pub fn sqlite(database_path: String, game_table: String) -> napi::Result<Self, String> {
        let result = classic_shared_core::get_runtime()
            .block_on(spawn_result(
                async move {
                    Ok::<_, Infallible>(
                        CoreFormIdValueLookup::sqlite(PathBuf::from(database_path), game_table)
                            .await,
                    )
                },
                |error| to_napi_err(format!("Runtime error: {error}")),
                |never| match never {},
            ))
            .map_err(|error| {
                napi::Error::new(
                    "operational_failure".to_string(),
                    format!(
                        "FormID Value Lookup runtime dispatch failed: {}",
                        error.reason
                    ),
                )
            })?;
        let inner = result.map_err(|error| {
            napi::Error::new(error.code().to_string(), error.message().to_string())
        })?;
        Ok(Self { inner })
    }

    /// Creates an adapter over an existing shared database pool.
    ///
    /// The facade retains a clone of the pool's shared state, so no callback or
    /// additional runtime crosses the JavaScript boundary.
    ///
    /// @param pool - Existing Node database pool to share.
    #[napi(factory)]
    pub fn from_shared_pool(pool: &JsDatabasePool) -> Self {
        Self {
            inner: CoreFormIdValueLookup::shared_pool(Arc::new(pool.inner.clone())),
        }
    }

    /// Looks up one FormID/plugin pair on the shared CLASSIC runtime.
    ///
    /// @param formid - FormID suffix to resolve.
    /// @param plugin - Plugin name, matched case-insensitively.
    /// @throws an error with stable `code`, `formid`, `plugin`, and `message`
    /// metadata for malformed results and operational failures.
    #[napi(ts_return_type = "Promise<JsFormIdValueLookupOutcome>")]
    pub fn lookup(
        &self,
        formid: String,
        plugin: String,
    ) -> Result<AsyncTask<FormIdValueLookupTask>> {
        Ok(AsyncTask::new(FormIdValueLookupTask {
            inner: self.inner.clone(),
            formid,
            plugin,
        }))
    }

    /// Looks up an owned batch with one positional outcome per input pair.
    ///
    /// Any malformed reply or operational failure rejects the whole operation,
    /// so a partial batch cannot be mistaken for a completed result.
    ///
    /// @param pairs - Array of exact `[formid, plugin]` pairs.
    /// @throws an error with stable `code`, `formid`, `plugin`, and `message`
    /// metadata for malformed results and operational failures.
    #[napi(ts_return_type = "Promise<JsFormIdValueLookupOutcome[]>")]
    pub fn lookup_batch(
        &self,
        pairs: Vec<Vec<String>>,
    ) -> Result<AsyncTask<FormIdValueLookupBatchTask>> {
        let pairs = parse_formid_lookup_pairs(pairs)?;
        Ok(AsyncTask::new(FormIdValueLookupBatchTask {
            inner: self.inner.clone(),
            pairs,
        }))
    }
}

/// Internal success-or-domain-failure result retained until JavaScript-thread resolution.
pub enum FormIdValueLookupTaskOutput<T> {
    /// Successful core operation.
    Success(T),
    /// Typed domain or runtime failure awaiting Node error projection.
    Failure(FormIdValueLookupTaskFailure),
}

/// Internal strict failure retained until JavaScript-thread resolution.
pub enum FormIdValueLookupTaskFailure {
    /// Failure produced by the core lookup adapter.
    Core(FormIdValueLookupError),
    /// Failure dispatching work through the shared runtime.
    Runtime {
        /// Human-readable runtime failure detail.
        message: String,
        /// FormID context when one lookup key was available.
        formid: Option<String>,
        /// Plugin context when one lookup key was available.
        plugin: Option<String>,
    },
}

/// Background task for one strict FormID Value Lookup operation.
pub struct FormIdValueLookupTask {
    inner: CoreFormIdValueLookup,
    formid: String,
    plugin: String,
}

impl Task for FormIdValueLookupTask {
    type Output = FormIdValueLookupTaskOutput<JsFormIdValueLookupOutcome>;
    type JsValue = JsFormIdValueLookupOutcome;

    /// Dispatches one lookup onto the process-wide Tokio runtime.
    fn compute(&mut self) -> Result<Self::Output> {
        let inner = self.inner.clone();
        let formid = self.formid.clone();
        let plugin = self.plugin.clone();
        let error_formid = formid.clone();
        let error_plugin = plugin.clone();
        Ok(
            match run_formid_lookup_future(async move { inner.lookup(&formid, &plugin).await }) {
                Ok(Ok(outcome)) => {
                    FormIdValueLookupTaskOutput::Success(formid_lookup_outcome_to_js(outcome))
                }
                Ok(Err(error)) => {
                    FormIdValueLookupTaskOutput::Failure(FormIdValueLookupTaskFailure::Core(error))
                }
                Err(error) => {
                    FormIdValueLookupTaskOutput::Failure(FormIdValueLookupTaskFailure::Runtime {
                        message: format!(
                            "FormID Value Lookup runtime dispatch failed: {}",
                            error.reason
                        ),
                        formid: Some(error_formid),
                        plugin: Some(error_plugin),
                    })
                }
            },
        )
    }

    /// Resolves the outcome or rejects with complete typed lookup error metadata.
    fn resolve(&mut self, env: Env, output: Self::Output) -> Result<Self::JsValue> {
        match output {
            FormIdValueLookupTaskOutput::Success(outcome) => Ok(outcome),
            FormIdValueLookupTaskOutput::Failure(error) => {
                Err(formid_lookup_task_failure_to_napi(env, error))
            }
        }
    }
}

/// Background task for one positional strict FormID lookup batch.
pub struct FormIdValueLookupBatchTask {
    inner: CoreFormIdValueLookup,
    pairs: Vec<(String, String)>,
}

impl Task for FormIdValueLookupBatchTask {
    type Output = FormIdValueLookupTaskOutput<Vec<JsFormIdValueLookupOutcome>>;
    type JsValue = Vec<JsFormIdValueLookupOutcome>;

    /// Dispatches one positional batch onto the process-wide Tokio runtime.
    fn compute(&mut self) -> Result<Self::Output> {
        let inner = self.inner.clone();
        let pairs = self.pairs.clone();
        let error_key = pairs.first().cloned();
        Ok(
            match run_formid_lookup_future(async move { inner.lookup_batch(pairs).await }) {
                Ok(Ok(outcomes)) => FormIdValueLookupTaskOutput::Success(
                    outcomes
                        .into_iter()
                        .map(formid_lookup_outcome_to_js)
                        .collect(),
                ),
                Ok(Err(error)) => {
                    FormIdValueLookupTaskOutput::Failure(FormIdValueLookupTaskFailure::Core(error))
                }
                Err(error) => {
                    FormIdValueLookupTaskOutput::Failure(FormIdValueLookupTaskFailure::Runtime {
                        message: format!(
                            "FormID Value Lookup runtime dispatch failed: {}",
                            error.reason
                        ),
                        formid: error_key.as_ref().map(|key| key.0.clone()),
                        plugin: error_key.map(|key| key.1),
                    })
                }
            },
        )
    }

    /// Resolves the outcomes or rejects with complete typed lookup error metadata.
    fn resolve(&mut self, env: Env, output: Self::Output) -> Result<Self::JsValue> {
        match output {
            FormIdValueLookupTaskOutput::Success(outcomes) => Ok(outcomes),
            FormIdValueLookupTaskOutput::Failure(error) => {
                Err(formid_lookup_task_failure_to_napi(env, error))
            }
        }
    }
}

/// Runs one lookup future through the standard shared-runtime spawn adapter.
fn run_formid_lookup_future<F, T>(
    future: F,
) -> Result<std::result::Result<T, FormIdValueLookupError>>
where
    F: Future<Output = std::result::Result<T, FormIdValueLookupError>> + Send + 'static,
    T: Send + 'static,
{
    classic_shared_core::get_runtime().block_on(spawn_result(
        async move { Ok::<_, Infallible>(future.await) },
        |error| to_napi_err(format!("Runtime error: {error}")),
        |never| match never {},
    ))
}

/// Converts one owned Node fixture entry into the core callback-free reply.
fn formid_lookup_entry_to_core(entry: JsFormIdValueLookupEntry) -> Result<FormIdValueLookupEntry> {
    let reply = match (entry.value, entry.operational_failure) {
        (Some(_), Some(_)) => {
            return Err(napi::Error::new(
                Status::InvalidArg,
                format!(
                    "FormID Value Lookup entry {}:{} cannot set both value and operationalFailure",
                    entry.formid, entry.plugin
                ),
            ));
        }
        (value, None) => FormIdValueLookupInMemoryReply::Value(value),
        (None, Some(message)) => FormIdValueLookupInMemoryReply::OperationalFailure(message),
    };
    Ok(FormIdValueLookupEntry::new(
        entry.formid,
        entry.plugin,
        reply,
    ))
}

/// Validates and owns JavaScript lookup pairs before asynchronous dispatch.
fn parse_formid_lookup_pairs(pairs: Vec<Vec<String>>) -> Result<Vec<(String, String)>> {
    pairs
        .into_iter()
        .map(|pair| match pair.as_slice() {
            [formid, plugin] => Ok((formid.clone(), plugin.clone())),
            _ => Err(napi::Error::new(
                Status::InvalidArg,
                "Each pair must be an array of exactly [formid, plugin]".to_string(),
            )),
        })
        .collect()
}

/// Converts one core success value into the stable owned Node outcome shape.
fn formid_lookup_outcome_to_js(outcome: FormIdValueLookupOutcome) -> JsFormIdValueLookupOutcome {
    match outcome {
        FormIdValueLookupOutcome::Disabled => JsFormIdValueLookupOutcome {
            kind: JsFormIdValueLookupOutcomeKind::Disabled,
            value: None,
        },
        FormIdValueLookupOutcome::Missing => JsFormIdValueLookupOutcome {
            kind: JsFormIdValueLookupOutcomeKind::Missing,
            value: None,
        },
        FormIdValueLookupOutcome::Found(value) => JsFormIdValueLookupOutcome {
            kind: JsFormIdValueLookupOutcomeKind::Found,
            value: Some(value),
        },
    }
}

/// Preserves stable core lookup error metadata on the rejected JavaScript error.
fn formid_lookup_error_to_napi(env: Env, error: FormIdValueLookupError) -> napi::Error {
    formid_lookup_error_fields_to_napi(
        env,
        error.code().to_string(),
        error.message().to_string(),
        error.formid().map(str::to_string),
        error.plugin().map(str::to_string),
    )
}

/// Projects either core or runtime failures through the same strict Node contract.
fn formid_lookup_task_failure_to_napi(
    env: Env,
    failure: FormIdValueLookupTaskFailure,
) -> napi::Error {
    match failure {
        FormIdValueLookupTaskFailure::Core(error) => formid_lookup_error_to_napi(env, error),
        FormIdValueLookupTaskFailure::Runtime {
            message,
            formid,
            plugin,
        } => formid_lookup_error_fields_to_napi(
            env,
            "operational_failure".to_string(),
            message,
            formid,
            plugin,
        ),
    }
}

/// Attaches the stable strict error fields to one rejected JavaScript error.
fn formid_lookup_error_fields_to_napi(
    env: Env,
    code: String,
    message: String,
    formid: Option<String>,
    plugin: Option<String>,
) -> napi::Error {
    let raw_error =
        JsError::from(napi::Error::new(code.clone(), message.clone())).into_unknown(env);

    let Ok(mut object) = raw_error.coerce_to_object() else {
        return base_formid_lookup_error(env, code, message);
    };
    if let Some(formid) = formid
        && object.set_named_property("formid", formid).is_err()
    {
        return base_formid_lookup_error(env, code, message);
    }
    if let Some(plugin) = plugin
        && object.set_named_property("plugin", plugin).is_err()
    {
        return base_formid_lookup_error(env, code, message);
    }

    object
        .into_unknown(&env)
        .map(napi::Error::from)
        .unwrap_or_else(|_| base_formid_lookup_error(env, code, message))
}

/// Rebuilds the ordinary code/message error when custom fields cannot be attached.
fn base_formid_lookup_error(env: Env, code: String, message: String) -> napi::Error {
    napi::Error::from(JsError::from(napi::Error::new(code, message)).into_unknown(env))
}
