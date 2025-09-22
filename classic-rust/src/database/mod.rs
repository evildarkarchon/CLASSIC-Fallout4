//! Database module - High-performance SQLite operations with connection pooling

use pyo3::prelude::*;

pub mod pool;

pub use pool::RustDatabasePool;

/// Register the database module with Python
pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustDatabasePool>()?;
    Ok(())
}
