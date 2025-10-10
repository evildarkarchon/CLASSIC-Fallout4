//! Classic File I/O Python Bindings
//!
//! This crate provides PyO3 bindings for classic-file-io-core.
//! It wraps the pure Rust file I/O operations for Python consumption.
//!
//! This is a THIN ADAPTER LAYER - all business logic is in classic-file-io-core.

use pyo3::prelude::*;

mod core;
mod dds;
mod encoding;

pub use core::PyFileIOCore;
pub use encoding::PyEncodingDetector;

/// Python module for file I/O operations
#[pymodule]
fn classic_file_io(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyFileIOCore>()?;
    m.add_class::<PyEncodingDetector>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
