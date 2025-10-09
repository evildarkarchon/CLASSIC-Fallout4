//! Database pool Python bindings (Thin PyO3 Adapter)
//!
//! This module provides Python bindings for the pure Rust DatabasePool.
//! All business logic is delegated to classic-database-core.

use classic_database_core::{DatabasePool, DatabaseError};
use pyo3::prelude::*;
use pyo3::types::PyList;
use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Duration;

// Use the global runtime from classic-shared (ONE RUNTIME RULE)
use classic_shared::get_runtime;

/// Python-facing database pool wrapper
#[pyclass(name = "RustDatabasePool", unsendable)]
pub struct PyDatabasePool {
    inner: DatabasePool,
}

#[pymethods]
impl PyDatabasePool {
    #[new]
    #[pyo3(signature = (max_connections=10, cache_ttl_seconds=300, game_table=None))]
    pub fn new(
        max_connections: Option<usize>,
        cache_ttl_seconds: Option<u64>,
        game_table: Option<String>
    ) -> Self {
        let max_conn = max_connections.unwrap_or(10);
        let ttl = Duration::from_secs(cache_ttl_seconds.unwrap_or(300));
        let table = game_table.unwrap_or_else(|| "Fallout4".to_string());

        Self {
            inner: DatabasePool::new(max_conn, ttl, table),
        }
    }

    /// Initialize database connections for given paths
    #[pyo3(name = "initialize")]
    pub fn py_initialize(&self, _py: Python<'_>, db_paths: Vec<String>) -> PyResult<()> {
        let paths: Vec<PathBuf> = db_paths.into_iter().map(PathBuf::from).collect();

        get_runtime().block_on(async {
            self.inner.initialize(paths).await.map_err(to_pyerr)
        })
    }

    /// Get FormID entry from database
    #[pyo3(name = "get_entry", signature = (formid, plugin, table=None))]
    pub fn py_get_entry(
        &self,
        _py: Python<'_>,
        formid: String,
        plugin: String,
        table: Option<String>
    ) -> PyResult<Option<String>> {
        get_runtime().block_on(async {
            self.inner
                .get_entry(&formid, &plugin, table.as_deref())
                .await
                .map_err(to_pyerr)
        })
    }

    /// Batch lookup for FormID entries
    #[pyo3(name = "get_entries_batch", signature = (formid_plugin_pairs, table=None, batch_size=None))]
    pub fn py_get_entries_batch(
        &self,
        _py: Python<'_>,
        formid_plugin_pairs: &Bound<'_, PyList>,
        table: Option<String>,
        batch_size: Option<usize>
    ) -> PyResult<HashMap<String, String>> {
        // Parse Python list of tuples
        let mut pairs: Vec<(String, String)> = Vec::new();
        for item in formid_plugin_pairs.iter() {
            let tuple = item.extract::<(String, String)>()?;
            pairs.push(tuple);
        }

        let batch_sz = batch_size.unwrap_or(100);

        get_runtime().block_on(async {
            self.inner
                .get_entries_batch(pairs, table.as_deref(), batch_sz)
                .await
                .map_err(to_pyerr)
        })
    }

    /// Alternative batch lookup method (for backward compatibility)
    #[pyo3(name = "batch_lookup", signature = (formid_plugin_pairs, table=None))]
    pub fn py_batch_lookup(
        &self,
        py: Python<'_>,
        formid_plugin_pairs: &Bound<'_, PyList>,
        table: Option<String>
    ) -> PyResult<HashMap<(String, String), String>> {
        let result = self.py_get_entries_batch(py, formid_plugin_pairs, table, Some(100))?;

        // Convert format
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
        self.inner.set_game_table(table);
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
        result.insert("cache_size".to_string(), self.inner.cache_size() as u64);

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
        get_runtime().block_on(async {
            self.inner.close().await.map_err(to_pyerr)
        })
    }

    /// Optimize database connections (VACUUM and ANALYZE)
    #[pyo3(name = "optimize")]
    pub fn py_optimize(&self, _py: Python<'_>) -> PyResult<()> {
        get_runtime().block_on(async {
            self.inner.optimize().await.map_err(to_pyerr)
        })
    }
}

/// Convert DatabaseError to PyErr
fn to_pyerr(err: DatabaseError) -> PyErr {
    match err {
        DatabaseError::OpenError(msg) => {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to open database: {}", msg))
        }
        DatabaseError::QueryError(msg) => {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Query error: {}", msg))
        }
        DatabaseError::NotFound(msg) => {
            PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(msg)
        }
        DatabaseError::IoError(e) => {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())
        }
        DatabaseError::RusqliteError(e) => {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Database error: {}", e))
        }
        DatabaseError::JoinError(msg) => {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Task error: {}", msg))
        }
    }
}
