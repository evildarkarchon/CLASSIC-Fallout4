//! Database connection pool with async support

use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use rusqlite::{Connection, params};
use dashmap::DashMap;
use std::sync::Arc;
use std::path::PathBuf;
use tokio::sync::RwLock;
use anyhow::{Result, Context};

/// High-performance database pool with caching
#[pyclass]
pub struct RustDatabasePool {
    connections: Arc<DashMap<PathBuf, Arc<RwLock<Connection>>>>,
    query_cache: Arc<DashMap<(String, String), String>>,
}

#[pymethods]
impl RustDatabasePool {
    #[new]
    pub fn new() -> Self {
        Self {
            connections: Arc::new(DashMap::new()),
            query_cache: Arc::new(DashMap::new()),
        }
    }

    /// Get or create a connection to a database
    #[pyo3(name = "get_connection")]
    pub fn py_get_connection<'py>(&self, py: Python<'py>, db_path: String) -> PyResult<Bound<'py, PyAny>> {
        let connections = self.connections.clone();
        let path = PathBuf::from(db_path.clone());

        future_into_py(py, async move {
            // Check if connection exists
            if !connections.contains_key(&path) {
                let conn = Connection::open(&path)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

                // Set pragmas for performance
                conn.pragma_update(None, "journal_mode", "WAL")
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
                conn.pragma_update(None, "synchronous", "NORMAL")
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

                connections.insert(path.clone(), Arc::new(RwLock::new(conn)));
            }

            Ok(db_path)
        })
    }

    /// Execute a batch lookup query
    #[pyo3(name = "batch_lookup")]
    pub fn py_batch_lookup<'py>(
        &self,
        py: Python<'py>,
        db_path: String,
        table: String,
        keys: Vec<String>
    ) -> PyResult<Bound<'py, PyAny>> {
        let connections = self.connections.clone();
        let query_cache = self.query_cache.clone();
        let path = PathBuf::from(db_path);

        future_into_py(py, async move {
            let mut results = Vec::with_capacity(keys.len());

            // Ensure connection exists
            if !connections.contains_key(&path) {
                return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>("Database not connected"));
            }

            let conn_arc = connections.get(&path).unwrap();
            let conn = conn_arc.read().await;

            for key in keys {
                let cache_key = (table.clone(), key.clone());

                // Check cache first
                if let Some(cached) = query_cache.get(&cache_key) {
                    results.push(Some(cached.value().clone()));
                    continue;
                }

                // Execute query
                let query = format!("SELECT value FROM {} WHERE key = ?1", table);
                let result: Result<String, _> = conn.query_row(
                    &query,
                    params![key],
                    |row| row.get(0)
                );

                match result {
                    Ok(value) => {
                        query_cache.insert(cache_key, value.clone());
                        results.push(Some(value));
                    }
                    Err(_) => results.push(None),
                }
            }

            Ok(results)
        })
    }

    /// Clear all caches
    pub fn clear_cache(&self) {
        self.query_cache.clear();
    }

    /// Get pool statistics
    pub fn get_stats(&self) -> (usize, usize) {
        (self.connections.len(), self.query_cache.len())
    }

    /// Close all connections
    #[pyo3(name = "close_all")]
    pub fn py_close_all<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let connections = self.connections.clone();

        future_into_py(py, async move {
            connections.clear();
            Ok(())
        })
    }
}
