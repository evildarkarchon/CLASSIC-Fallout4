//! File I/O module - High-performance file operations with encoding detection

use pyo3::prelude::*;
use std::path::PathBuf;
use tokio::fs;
use encoding_rs::Encoding;
use anyhow::Result;

pub mod core;
pub mod encoding;

pub use core::RustFileIOCore;
pub use encoding::EncodingDetector;

/// Register the file_io module with Python
pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustFileIOCore>()?;
    m.add_class::<EncodingDetector>()?;
    Ok(())
}
