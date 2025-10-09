//! CLASSIC File I/O - High-performance file operations
//!
//! This crate provides optimized file I/O with:
//! - Async file operations with Tokio
//! - Memory-mapped file support
//! - DDS header parsing
//! - Parallel directory traversal
//! - Multi-level caching
//! - Encoding detection

use pyo3::prelude::*;

pub mod core;
pub mod dds;
pub mod encoding;

pub use core::RustFileIOCore;
pub use dds::DDSHeader;
pub use encoding::EncodingDetector;

/// Python module initialization
#[pymodule]
fn classic_file_io(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustFileIOCore>()?;
    m.add_class::<EncodingDetector>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
