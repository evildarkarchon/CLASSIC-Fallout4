//! CLASSIC Core - High-performance Rust extensions for CLASSIC Fallout 4
//!
//! This module provides optimized implementations of performance-critical
//! components for the CLASSIC crash log analyzer.

use pyo3::prelude::*;

pub mod file_io;
pub mod scanlog;
pub mod database;
pub mod utils;

/// Python module initialization
#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register the file I/O module
    let file_io_module = PyModule::new(m.py(), "file_io")?;
    file_io::register_module(&file_io_module)?;
    m.add_submodule(&file_io_module)?;

    // Register the scanlog module
    let scanlog_module = PyModule::new(m.py(), "scanlog")?;
    scanlog::register_module(&scanlog_module)?;
    m.add_submodule(&scanlog_module)?;

    // Register the database module
    let database_module = PyModule::new(m.py(), "database")?;
    database::register_module(&database_module)?;
    m.add_submodule(&database_module)?;

    // Register the utils module
    let utils_module = PyModule::new(m.py(), "utils")?;
    utils::register_module(&utils_module)?;
    m.add_submodule(&utils_module)?;

    // Add version information
    m.add("__version__", "8.0.0")?;

    Ok(())
}
