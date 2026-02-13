//! Classic Database Python Bindings
//!
//! This crate provides PyO3 bindings for classic-database-core.
//! It wraps the pure Rust database operations for Python consumption.
//!
//! ## Architecture
//! This is a THIN ADAPTER layer that:
//! - Delegates all business logic to classic-database-core
//! - Only handles Python ↔ Rust type conversions
//! - Maintains API compatibility with existing Python code
//!
//! ## Complete Usage Example
//!
//! ```python
//! from classic_core import database
//! import asyncio
//!
//! async def main():
//!     # Create database pool with dynamic sizing based on CPU cores
//!     pool = database.PyDatabasePool.new("path/to/database.db")
//!
//!     # Lookup FormID entries asynchronously
//!     entry = await pool.get_entry("012345", "Skyrim.esm", "WEAP")
//!     if entry:
//!         print(f"Found weapon: {entry}")
//!     else:
//!         print("FormID not found in database")
//!
//!     # Batch lookup multiple FormIDs (more efficient)
//!     formids = ["012345", "012346", "012347"]
//!     results = await pool.get_entries_batch(formids, "Skyrim.esm", "WEAP")
//!     for formid, entry in zip(formids, results):
//!         if entry:
//!             print(f"{formid}: {entry}")
//!
//!     # Get all entries for a plugin (useful for caching)
//!     all_entries = await pool.get_entries_for_plugin("Skyrim.esm", "WEAP")
//!     print(f"Found {len(all_entries)} weapon entries")
//!
//!     # Check if database is available
//!     if pool.is_available():
//!         print("Database is ready for queries")
//!
//! # Run async code from synchronous context
//! asyncio.run(main())
//! ```
//!
//! ## Performance Characteristics
//!
//! - **Connection pooling**: Dynamic pool size based on CPU cores (default: CPU count + 4)
//! - **Async I/O**: Non-blocking database queries for concurrent operations
//! - **Batch lookups**: 5-10x faster than individual queries for multiple FormIDs
//! - **Query performance**: ~1-5ms per lookup with warm connection pool
//! - **Memory efficient**: Connections shared across Python threads
//!
//! ## Thread Safety
//!
//! The PyDatabasePool is thread-safe and async-safe. It uses Arc internally for safe
//! sharing across Python threads and async tasks.
//!
//! ```python
//! from classic_core import database
//! import asyncio
//! from concurrent.futures import ThreadPoolExecutor
//!
//! pool = database.PyDatabasePool.new("database.db")
//!
//! async def worker(formid):
//!     # Safe to call from multiple async tasks
//!     return await pool.get_entry(formid, "Skyrim.esm", "WEAP")
//!
//! async def main():
//!     # Concurrent database lookups
//!     tasks = [worker(f"0{i:05d}") for i in range(100)]
//!     results = await asyncio.gather(*tasks)
//!     print(f"Processed {len(results)} lookups concurrently")
//!
//! asyncio.run(main())
//! ```

use classic_shared::{define_exceptions, register_exceptions};
use pyo3::prelude::*;

// Define the standard 3-tier exception hierarchy using the shared macro
// Note: third parameter is called "parse" in macro but we use QueryError for database
define_exceptions!(
    module: classic_database,
    base: RustDatabaseError,
    io: RustDatabaseIOError,
    parse: RustDatabaseQueryError
);

mod pool;

pub use pool::{
    PyDatabasePool, py_get_batch_cache_ttl, py_get_default_cache_ttl, py_get_max_cache_ttl,
};

/// Convert DatabaseError to PyErr using custom exception types
///
/// Maps Rust DatabaseError variants to Python exception types from
/// ClassicLib.integration.exceptions for better error handling.
pub fn to_pyerr(err: classic_database_core::DatabaseError) -> PyErr {
    use classic_database_core::DatabaseError;

    match err {
        // I/O errors map to RustDatabaseIOError
        DatabaseError::OpenError(msg) => {
            RustDatabaseIOError::new_err(format!("Failed to open database: {}", msg))
        }
        DatabaseError::NotFound(msg) => {
            RustDatabaseIOError::new_err(format!("Database file not found: {}", msg))
        }
        DatabaseError::IoError(e) => RustDatabaseIOError::new_err(format!("I/O error: {}", e)),

        // Query errors map to RustDatabaseQueryError
        DatabaseError::QueryError(msg) => {
            RustDatabaseQueryError::new_err(format!("Query error: {}", msg))
        }
        DatabaseError::SqlxError(e) => {
            RustDatabaseQueryError::new_err(format!("Database error: {}", e))
        }
    }
}

/// Python module initialization
#[pymodule]
fn classic_database(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDatabasePool>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Add cache TTL helper functions
    m.add_function(wrap_pyfunction!(py_get_default_cache_ttl, m)?)?;
    m.add_function(wrap_pyfunction!(py_get_batch_cache_ttl, m)?)?;
    m.add_function(wrap_pyfunction!(py_get_max_cache_ttl, m)?)?;

    // Add cache TTL constants as module attributes for convenience
    m.add(
        "DEFAULT_CACHE_TTL",
        classic_database_core::DEFAULT_CACHE_TTL_SECS,
    )?;
    m.add(
        "BATCH_CACHE_TTL",
        classic_database_core::BATCH_CACHE_TTL_SECS,
    )?;
    m.add("MAX_CACHE_TTL", classic_database_core::MAX_CACHE_TTL_SECS)?;

    // Register custom exception types using the shared macro
    register_exceptions!(
        m,
        RustDatabaseError,
        RustDatabaseIOError,
        RustDatabaseQueryError
    );

    Ok(())
}
