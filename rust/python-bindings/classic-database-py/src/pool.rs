//! Database pool Python bindings (Thin PyO3 Adapter)
//!
//! This module provides Python bindings for the pure Rust DatabasePool.
//! All business logic is delegated to classic-database-core.

use classic_database_core::DatabasePool;
use pyo3::prelude::*;
use pyo3::types::PyList;
use pyo3_async_runtimes::tokio::future_into_py;
use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Duration;

// Use the error conversion function from lib.rs
use crate::to_pyerr;

/// Python-facing database pool wrapper
///
/// This wrapper is Send-safe because the inner DatabasePool uses Arc, DashMap,
/// Mutex, and RwLock - all of which are Send + Sync. Removing `unsendable`
/// allows Python's GC to safely drop this object on any thread.
#[pyclass(name = "RustDatabasePool")]
pub struct PyDatabasePool {
    inner: DatabasePool,
}

#[pymethods]
impl PyDatabasePool {
    /// Create a new PyDatabasePool instance
    ///
    /// # Arguments
    ///
    /// * `max_connections` - Optional maximum number of database connections (defaults to auto-calculated)
    /// * `cache_ttl_seconds` - Optional cache TTL in seconds (defaults to 300)
    /// * `game_table` - Optional game table name (defaults to "Fallout4")
    ///
    /// # Returns
    ///
    /// A new `PyDatabasePool` instance with the specified configuration
    ///
    /// # Example
    ///
    /// ```python
    /// # Create with defaults
    /// pool = RustDatabasePool()
    ///
    /// # Create with custom settings
    /// pool = RustDatabasePool(max_connections=50, cache_ttl_seconds=600, game_table="Skyrim")
    /// ```
    #[new]
    #[pyo3(signature = (max_connections=None, cache_ttl_seconds=300, game_table=None))]
    pub fn new(
        max_connections: Option<usize>,
        cache_ttl_seconds: Option<u64>,
        game_table: Option<String>,
    ) -> Self {
        let ttl = Duration::from_secs(cache_ttl_seconds.unwrap_or(300));
        let table = game_table.unwrap_or_else(|| "Fallout4".to_string());

        Self {
            inner: DatabasePool::new(max_connections, ttl, table),
        }
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

    /// Alternative batch lookup method (for backward compatibility)
    ///
    /// Returns a Python coroutine - use with await in Python.
    #[pyo3(name = "batch_lookup", signature = (formid_plugin_pairs, table=None))]
    pub fn py_batch_lookup<'py>(
        &self,
        py: Python<'py>,
        formid_plugin_pairs: &Bound<'_, PyList>,
        table: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();

        // Parse Python list of tuples (requires GIL)
        let len = formid_plugin_pairs.len();
        let mut pairs: Vec<(String, String)> = Vec::with_capacity(len);
        for item in formid_plugin_pairs.iter() {
            let tuple = item.extract::<(String, String)>()?;
            pairs.push(tuple);
        }

        // Returns Python coroutine immediately - no blocking!
        future_into_py(py, async move {
            let result = inner
                .get_entries_batch(pairs, table.as_deref(), 100)
                .await
                .map_err(to_pyerr)?;

            // Convert format from "formid:plugin" -> (formid, plugin)
            let mut converted_result = HashMap::new();
            for (key, value) in result {
                let parts: Vec<&str> = key.split(':').collect();
                if parts.len() == 2 {
                    converted_result.insert((parts[0].to_string(), parts[1].to_string()), value);
                }
            }

            Ok(converted_result)
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

    /// Get current max_connections setting
    #[pyo3(name = "get_max_connections")]
    pub fn py_get_max_connections(&self) -> Option<usize> {
        self.inner.get_max_connections()
    }

    /// Set max_connections (for runtime adjustment)
    #[pyo3(name = "set_max_connections")]
    pub fn py_set_max_connections(&self, max_connections: usize) {
        self.inner.set_max_connections(max_connections);
    }

    /// Recalculate max_connections based on current system resources
    #[pyo3(name = "recalculate_max_connections")]
    pub fn py_recalculate_max_connections(&self) {
        self.inner.recalculate_max_connections();
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

        if stats.total_queries > 0 {
            let hit_rate = (stats.cache_hits as f64 / stats.total_queries as f64) * 100.0;
            result.insert("cache_hit_rate".to_string(), hit_rate as u64);
        } else {
            result.insert("cache_hit_rate".to_string(), 0);
        }

        Ok(result)
    }
}
