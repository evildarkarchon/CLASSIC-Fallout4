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

use pyo3::prelude::*;

mod pool;

pub use pool::PyDatabasePool;

/// Python module initialization
#[pymodule]
fn classic_database(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDatabasePool>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
