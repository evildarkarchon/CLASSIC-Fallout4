//! Database pool Python bindings (Thin PyO3 Adapter)
//!
//! This module provides Python bindings for the pure Rust DatabasePool.
//! All business logic is delegated to classic-database-core.
//!
//! ## Cache TTL Constants
//!
//! - `DEFAULT_CACHE_TTL_SECS` (300): For single log scanning
//! - `BATCH_CACHE_TTL_SECS` (1800): For batch log scanning (30 minutes)
//! - `MAX_CACHE_TTL_SECS` (3600): For very large batches (60 minutes)

use classic_database_core::{
    BATCH_CACHE_TTL_SECS, DEFAULT_CACHE_CLEANUP_INTERVAL_SECS, DEFAULT_CACHE_CLEANUP_OP_THRESHOLD,
    DEFAULT_CACHE_TTL_SECS, DEFAULT_QUERY_CACHE_CAPACITY, DatabasePool, FormIdValueLookup,
    FormIdValueLookupEntry, FormIdValueLookupError as CoreFormIdValueLookupError,
    FormIdValueLookupInMemoryReply, FormIdValueLookupOutcome, MAX_CACHE_TTL_SECS,
};
use pyo3::prelude::*;
use pyo3::types::PyList;
use pyo3_async_runtimes::tokio::future_into_py;
use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Duration;

// Use the error conversion function from lib.rs
use crate::{FormIdValueLookupError, to_pyerr};

/// One owned deterministic reply used to construct an in-memory lookup facade.
#[pyclass(name = "FormIdValueLookupEntry", frozen, get_all, skip_from_py_object)]
#[derive(Clone)]
pub struct PyFormIdValueLookupEntry {
    /// FormID suffix to match exactly.
    pub formid: String,
    /// Plugin to match case-insensitively.
    pub plugin: String,
    /// Successful value; `None` represents a miss when no failure is supplied.
    pub value: Option<String>,
    /// Deterministic operational failure message.
    pub operational_failure: Option<String>,
}

#[pymethods]
impl PyFormIdValueLookupEntry {
    /// Creates one fully owned in-memory lookup reply.
    #[new]
    #[pyo3(signature = (formid, plugin, value=None, operational_failure=None))]
    pub fn new(
        formid: String,
        plugin: String,
        value: Option<String>,
        operational_failure: Option<String>,
    ) -> PyResult<Self> {
        if value.is_some() && operational_failure.is_some() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "value and operational_failure are mutually exclusive",
            ));
        }
        Ok(Self {
            formid,
            plugin,
            value,
            operational_failure,
        })
    }
}

impl PyFormIdValueLookupEntry {
    fn to_core(&self) -> FormIdValueLookupEntry {
        let reply = self.operational_failure.as_ref().map_or_else(
            || FormIdValueLookupInMemoryReply::Value(self.value.clone()),
            |message| FormIdValueLookupInMemoryReply::OperationalFailure(message.clone()),
        );
        FormIdValueLookupEntry::new(&self.formid, &self.plugin, reply)
    }
}

/// One successful semantic FormID Value Lookup result.
#[pyclass(name = "FormIdValueLookupOutcome", frozen, get_all)]
pub struct PyFormIdValueLookupOutcome {
    /// Stable outcome kind: `disabled`, `missing`, or `found`.
    pub kind: String,
    /// Owned value for `found`; otherwise `None`.
    pub value: Option<String>,
}

impl From<FormIdValueLookupOutcome> for PyFormIdValueLookupOutcome {
    fn from(outcome: FormIdValueLookupOutcome) -> Self {
        match outcome {
            FormIdValueLookupOutcome::Disabled => Self {
                kind: "disabled".to_string(),
                value: None,
            },
            FormIdValueLookupOutcome::Missing => Self {
                kind: "missing".to_string(),
                value: None,
            },
            FormIdValueLookupOutcome::Found(value) => Self {
                kind: "found".to_string(),
                value: Some(value),
            },
        }
    }
}

/// Opaque callback-free FormID Value Lookup facade.
#[pyclass(name = "FormIdValueLookup", frozen)]
pub struct PyFormIdValueLookup {
    inner: FormIdValueLookup,
}

#[pymethods]
impl PyFormIdValueLookup {
    /// Creates an explicitly disabled lookup facade.
    #[staticmethod]
    pub fn disabled() -> Self {
        Self {
            inner: FormIdValueLookup::disabled(),
        }
    }

    /// Creates a deterministic facade from owned replies without callbacks.
    #[staticmethod]
    pub fn in_memory(py: Python<'_>, entries: Vec<Py<PyFormIdValueLookupEntry>>) -> PyResult<Self> {
        let entries = entries
            .iter()
            .map(|entry| entry.borrow(py).to_core())
            .collect();
        Ok(Self {
            inner: FormIdValueLookup::in_memory(entries),
        })
    }

    /// Opens one owned SQLite adapter on CLASSIC's shared Tokio runtime.
    #[staticmethod]
    pub fn sqlite<'py>(
        py: Python<'py>,
        database_path: String,
        game_table: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        future_into_py(py, async move {
            FormIdValueLookup::sqlite(PathBuf::from(database_path), game_table)
                .await
                .map(|inner| Self { inner })
                .map_err(formid_value_lookup_error_to_pyerr)
        })
    }

    /// Creates a facade over an existing shared database pool.
    #[staticmethod]
    pub fn from_shared_pool(pool: &PyDatabasePool) -> Self {
        Self {
            inner: FormIdValueLookup::shared_pool(std::sync::Arc::new(pool.inner.clone())),
        }
    }

    /// Looks up one FormID/plugin pair asynchronously.
    pub fn lookup<'py>(
        &self,
        py: Python<'py>,
        formid: String,
        plugin: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let lookup = self.inner.clone();
        future_into_py(py, async move {
            lookup
                .lookup(&formid, &plugin)
                .await
                .map(PyFormIdValueLookupOutcome::from)
                .map_err(formid_value_lookup_error_to_pyerr)
        })
    }

    /// Looks up an owned batch and returns one positional outcome per pair.
    pub fn lookup_batch<'py>(
        &self,
        py: Python<'py>,
        pairs: Vec<(String, String)>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let lookup = self.inner.clone();
        future_into_py(py, async move {
            lookup
                .lookup_batch(pairs)
                .await
                .map(|outcomes| {
                    outcomes
                        .into_iter()
                        .map(PyFormIdValueLookupOutcome::from)
                        .collect::<Vec<_>>()
                })
                .map_err(formid_value_lookup_error_to_pyerr)
        })
    }
}

/// Converts a strict lookup error while retaining its stable typed attributes.
fn formid_value_lookup_error_to_pyerr(error: CoreFormIdValueLookupError) -> PyErr {
    let py_error = FormIdValueLookupError::new_err(error.message().to_string());
    Python::attach(|py| {
        let value = py_error.value(py);
        // These attributes keep malformed replies distinct from operational failures.
        let _ = value.setattr("code", error.code());
        let _ = value.setattr("formid", error.formid());
        let _ = value.setattr("plugin", error.plugin());
        let _ = value.setattr("message", error.message());
    });
    py_error
}

/// Get the default cache TTL for single log operations (300 seconds).
#[pyfunction]
#[pyo3(name = "get_default_cache_ttl")]
pub fn py_get_default_cache_ttl() -> u64 {
    DEFAULT_CACHE_TTL_SECS
}

/// Get the recommended cache TTL for batch log operations (1800 seconds / 30 min).
#[pyfunction]
#[pyo3(name = "get_batch_cache_ttl")]
pub fn py_get_batch_cache_ttl() -> u64 {
    BATCH_CACHE_TTL_SECS
}

/// Get the maximum recommended cache TTL (3600 seconds / 60 min).
#[pyfunction]
#[pyo3(name = "get_max_cache_ttl")]
pub fn py_get_max_cache_ttl() -> u64 {
    MAX_CACHE_TTL_SECS
}

/// Get the default query cache capacity.
#[pyfunction]
#[pyo3(name = "get_default_query_cache_capacity")]
pub fn py_get_default_query_cache_capacity() -> usize {
    DEFAULT_QUERY_CACHE_CAPACITY
}

/// Get the default proactive cleanup operation threshold.
#[pyfunction]
#[pyo3(name = "get_default_cache_cleanup_threshold")]
pub fn py_get_default_cache_cleanup_threshold() -> u64 {
    DEFAULT_CACHE_CLEANUP_OP_THRESHOLD
}

/// Get the default proactive cleanup interval in seconds.
#[pyfunction]
#[pyo3(name = "get_default_cache_cleanup_interval")]
pub fn py_get_default_cache_cleanup_interval() -> u64 {
    DEFAULT_CACHE_CLEANUP_INTERVAL_SECS
}

/// Python-facing database pool wrapper
///
/// This wrapper is Send-safe because the inner DatabasePool uses Arc, DashMap,
/// Mutex, and RwLock - all of which are Send + Sync. Removing `unsendable`
/// allows Python's GC to safely drop this object on any thread.
#[pyclass(name = "DatabasePool")]
pub struct PyDatabasePool {
    inner: DatabasePool,
}

#[pymethods]
impl PyDatabasePool {
    /// Create a new PyDatabasePool instance
    ///
    /// # Arguments
    ///
    /// * `max_connections` - Optional global connection budget across active database pools
    /// * `cache_ttl_seconds` - Optional cache TTL in seconds (defaults to 1800 / 30 min for batch operations)
    /// * `game_table` - Optional game table name (defaults to "Fallout4")
    ///
    /// # Returns
    ///
    /// A new `PyDatabasePool` instance with the specified configuration
    ///
    /// # Example
    ///
    /// ```python
    /// # Create with defaults (uses batch TTL of 30 minutes)
    /// pool = DatabasePool()
    ///
    /// # Create with custom settings
    /// pool = DatabasePool(max_connections=50, cache_ttl_seconds=600, game_table="Skyrim")
    ///
    /// # Use TTL constants
    /// from classic_database import get_default_cache_ttl, get_batch_cache_ttl
    /// pool = DatabasePool(cache_ttl_seconds=get_batch_cache_ttl())
    /// ```
    #[new]
    #[pyo3(signature = (max_connections=None, cache_ttl_seconds=None, game_table=None, cache_capacity=None, cleanup_threshold=None, cleanup_interval_seconds=None))]
    pub fn new(
        max_connections: Option<usize>,
        cache_ttl_seconds: Option<u64>,
        game_table: Option<String>,
        cache_capacity: Option<usize>,
        cleanup_threshold: Option<u64>,
        cleanup_interval_seconds: Option<u64>,
    ) -> Self {
        // Default to batch TTL (30 min) for better cross-log cache performance
        let ttl = Duration::from_secs(cache_ttl_seconds.unwrap_or(BATCH_CACHE_TTL_SECS));
        let table = game_table.unwrap_or_else(|| "Fallout4".to_string());
        let inner = DatabasePool::new(max_connections, ttl, table);

        if let Some(capacity) = cache_capacity {
            inner.set_cache_capacity(capacity);
        }
        if let Some(threshold) = cleanup_threshold {
            inner.set_cache_cleanup_threshold(threshold);
        }
        if let Some(interval) = cleanup_interval_seconds {
            inner.set_cache_cleanup_interval(Duration::from_secs(interval));
        }

        Self { inner }
    }

    /// Initialize database connections for given paths
    ///
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "initialize")]
    pub fn py_initialize<'py>(
        &self,
        py: Python<'py>,
        db_paths: Vec<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        let paths: Vec<PathBuf> = db_paths.into_iter().map(PathBuf::from).collect();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner.initialize(paths).await.map_err(to_pyerr)
        })
    }

    /// Get FormID entry from database
    ///
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "get_entry", signature = (formid, plugin, table=None))]
    pub fn py_get_entry<'py>(
        &self,
        py: Python<'py>,
        formid: String,
        plugin: String,
        table: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner
                .get_entry(&formid, &plugin, table.as_deref())
                .await
                .map_err(to_pyerr)
        })
    }

    /// Batch lookup for FormID entries
    ///
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "get_entries_batch", signature = (formid_plugin_pairs, table=None, batch_size=None))]
    pub fn py_get_entries_batch<'py>(
        &self,
        py: Python<'py>,
        formid_plugin_pairs: &Bound<'_, PyList>,
        table: Option<String>,
        batch_size: Option<usize>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();

        // Parse Python list of tuples (requires GIL)
        let len = formid_plugin_pairs.len();
        let mut pairs: Vec<(String, String)> = Vec::with_capacity(len);
        for item in formid_plugin_pairs.iter() {
            let tuple = item.extract::<(String, String)>()?;
            pairs.push(tuple);
        }

        let batch_sz = batch_size.unwrap_or(100);

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            inner
                .get_entries_batch(pairs, table.as_deref(), batch_sz)
                .await
                .map_err(to_pyerr)
        })
    }

    /// Set the game table name dynamically
    #[pyo3(name = "set_game_table")]
    pub fn py_set_game_table(&self, table: String) {
        self.inner.set_game_table(&table);
    }

    /// Get the current game table name
    #[pyo3(name = "get_game_table")]
    pub fn py_get_game_table(&self) -> String {
        self.inner.get_game_table()
    }

    /// Clear cache entries
    #[pyo3(name = "clear_cache", signature = (expired_only=None))]
    pub fn py_clear_cache(&self, expired_only: Option<bool>) -> usize {
        self.inner.clear_cache(expired_only.unwrap_or(false))
    }

    /// Set cache TTL in seconds
    #[pyo3(name = "set_cache_ttl")]
    pub fn py_set_cache_ttl(&self, seconds: u64) {
        self.inner.set_cache_ttl(Duration::from_secs(seconds));
    }

    /// Get current cache capacity.
    #[pyo3(name = "get_cache_capacity")]
    pub fn py_get_cache_capacity(&self) -> usize {
        self.inner.get_cache_capacity()
    }

    /// Set cache capacity.
    #[pyo3(name = "set_cache_capacity")]
    pub fn py_set_cache_capacity(&self, capacity: usize) {
        self.inner.set_cache_capacity(capacity);
    }

    /// Get proactive cleanup threshold (operations).
    #[pyo3(name = "get_cache_cleanup_threshold")]
    pub fn py_get_cache_cleanup_threshold(&self) -> u64 {
        self.inner.get_cache_cleanup_threshold()
    }

    /// Set proactive cleanup threshold (operations).
    #[pyo3(name = "set_cache_cleanup_threshold")]
    pub fn py_set_cache_cleanup_threshold(&self, threshold: u64) {
        self.inner.set_cache_cleanup_threshold(threshold);
    }

    /// Get proactive cleanup interval in seconds.
    #[pyo3(name = "get_cache_cleanup_interval")]
    pub fn py_get_cache_cleanup_interval(&self) -> u64 {
        self.inner.get_cache_cleanup_interval().as_secs()
    }

    /// Set proactive cleanup interval in seconds.
    #[pyo3(name = "set_cache_cleanup_interval")]
    pub fn py_set_cache_cleanup_interval(&self, seconds: u64) {
        self.inner
            .set_cache_cleanup_interval(Duration::from_secs(seconds));
    }

    /// Get current global connection budget setting.
    #[pyo3(name = "get_max_connections")]
    pub fn py_get_max_connections(&self) -> Option<usize> {
        self.inner.get_max_connections()
    }

    /// Set global connection budget (config-only).
    ///
    /// Existing pools are not rebuilt automatically. Call `rebalance_connections()`
    /// to apply the updated budget immediately.
    #[pyo3(name = "set_max_connections")]
    pub fn py_set_max_connections(&self, max_connections: usize) {
        self.inner.set_max_connections(max_connections);
    }

    /// Recalculate global connection budget from current system resources.
    #[pyo3(name = "recalculate_max_connections")]
    pub fn py_recalculate_max_connections(&self) {
        self.inner.recalculate_max_connections();
    }

    /// Explicitly rebalance active pools using the current global budget.
    ///
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "rebalance_connections")]
    pub fn py_rebalance_connections<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        future_into_py(py, async move {
            inner.rebalance_connections().await.map_err(to_pyerr)
        })
    }

    /// Get pool statistics as a dictionary
    #[pyo3(name = "get_stats")]
    pub fn py_get_stats(&self) -> PyResult<HashMap<String, u64>> {
        let stats = self.inner.get_stats().map_err(to_pyerr)?;

        let mut result = HashMap::new();
        result.insert("total_queries".to_string(), stats.total_queries);
        result.insert("cache_hits".to_string(), stats.cache_hits);
        result.insert("cache_misses".to_string(), stats.cache_misses);
        result.insert("total_connections".to_string(), stats.total_connections);
        result.insert("active_connections".to_string(), stats.active_connections);
        result.insert("cache_evictions".to_string(), stats.cache_evictions);
        result.insert("cleanup_runs".to_string(), stats.cleanup_runs);
        result.insert("cleanup_removed".to_string(), stats.cleanup_removed);
        result.insert(
            "configured_connection_budget".to_string(),
            stats.configured_connection_budget,
        );
        result.insert(
            "effective_connection_budget".to_string(),
            stats.effective_connection_budget,
        );
        result.insert("active_pool_count".to_string(), stats.active_pool_count);
        result.insert("min_pool_allocation".to_string(), stats.min_pool_allocation);
        result.insert("max_pool_allocation".to_string(), stats.max_pool_allocation);
        result.insert("allocation_spread".to_string(), stats.allocation_spread);
        result.insert(
            "stable_shape_selections".to_string(),
            stats.stable_shape_selections,
        );
        result.insert(
            "stable_shape_padding_pairs".to_string(),
            stats.stable_shape_padding_pairs,
        );
        result.insert(
            "stable_shape_bucket_8".to_string(),
            stats.stable_shape_bucket_8,
        );
        result.insert(
            "stable_shape_bucket_16".to_string(),
            stats.stable_shape_bucket_16,
        );
        result.insert(
            "stable_shape_bucket_32".to_string(),
            stats.stable_shape_bucket_32,
        );
        result.insert(
            "stable_shape_bucket_64".to_string(),
            stats.stable_shape_bucket_64,
        );
        result.insert(
            "stable_shape_bucket_128".to_string(),
            stats.stable_shape_bucket_128,
        );
        result.insert(
            "stable_shape_bucket_256".to_string(),
            stats.stable_shape_bucket_256,
        );
        result.insert(
            "stable_shape_bucket_512".to_string(),
            stats.stable_shape_bucket_512,
        );
        result.insert(
            "stable_shape_bucket_1024".to_string(),
            stats.stable_shape_bucket_1024,
        );
        result.insert(
            "cache_capacity".to_string(),
            self.inner.get_cache_capacity() as u64,
        );
        result.insert(
            "cleanup_threshold".to_string(),
            self.inner.get_cache_cleanup_threshold(),
        );
        result.insert(
            "cleanup_interval_seconds".to_string(),
            self.inner.get_cache_cleanup_interval().as_secs(),
        );

        if stats.total_queries > 0 {
            let hit_rate = (stats.cache_hits as f64 / stats.total_queries as f64) * 100.0;
            result.insert("cache_hit_rate".to_string(), hit_rate as u64);
        } else {
            result.insert("cache_hit_rate".to_string(), 0);
        }

        Ok(result)
    }

    /// Optimize database connections (VACUUM/ANALYZE)
    ///
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "optimize")]
    pub fn py_optimize<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        future_into_py(py, async move { inner.optimize().await.map_err(to_pyerr) })
    }

    /// Close all database connections and clear caches
    ///
    /// This method should be called before application exit to ensure proper
    /// cleanup of SQLite connections. This is especially important when using
    /// WAL mode, as it ensures the WAL file is checkpointed back to the main
    /// database and the .db-wal and .db-shm files are removed.
    ///
    /// Returns a Python coroutine - use with await in Python.
    ///
    /// # Example
    ///
    /// ```python
    /// # Proper cleanup on application exit
    /// await pool.close()
    /// ```
    #[pyo3(name = "close")]
    pub fn py_close<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        future_into_py(py, async move { inner.close().await.map_err(to_pyerr) })
    }

    /// Check if the pool has any active connections
    ///
    /// Returns True if the pool has been initialized and has active connections.
    #[pyo3(name = "is_available")]
    pub fn py_is_available(&self) -> bool {
        self.inner.is_available()
    }
}
