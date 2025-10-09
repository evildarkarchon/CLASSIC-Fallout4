//! File I/O module - High-performance file operations with encoding detection
//!
//! Phase 3 of Rust migration - File I/O Core implementation
//! Provides:
//! - Async file operations with Tokio
//! - Memory-mapped file support for large files
//! - DDS header parsing with zero-copy operations
//! - Parallel directory traversal
//! - Multi-level caching (content, paths, metadata)
//! - Encoding detection for text files

use pyo3::prelude::*;

pub mod core;
pub mod dds;
pub mod encoding;

pub use core::RustFileIOCore;
pub use dds::DDSHeader;
pub use encoding::EncodingDetector;

/// Register the file_io module with Python
pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustFileIOCore>()?;
    m.add_class::<EncodingDetector>()?;
    Ok(())
}
