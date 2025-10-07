//! CLASSIC Database - High-performance SQLite operations
//!
//! This crate provides optimized database operations with:
//! - Connection pooling with rusqlite
//! - TTL-based smart caching
//! - Batch query optimization
//! - FormID-specific operations
//! - Multiple database file support

use pyo3::prelude::*;

mod pool;

pub use pool::RustDatabasePool;

/// Python module initialization
#[pymodule]
fn classic_database(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustDatabasePool>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
