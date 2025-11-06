//! Classic File I/O Python Bindings
//!
//! This crate provides PyO3 bindings for classic-file-io-core.
//! It wraps the pure Rust file I/O operations for Python consumption.
//!
//! This is a THIN ADAPTER LAYER - all business logic is in classic-file-io-core.
//!
//! ## Complete Usage Example
//!
//! ```python
//! from classic_core import file_io
//! import asyncio
//!
//! async def main():
//!     # Create file I/O handler with UTF-8 encoding
//!     io_core = file_io.PyFileIOCore.new(
//!         default_encoding="utf-8",
//!         error_handling="ignore",
//!         cache_capacity=100,
//!         max_cache_age_secs=50
//!     )
//!
//!     # Read file with automatic encoding detection (10x faster than Python)
//!     content = await io_core.read_file("crash.log")
//!     print(f"Read {len(content)} characters")
//!
//!     # Write file asynchronously
//!     lines = ["Line 1", "Line 2", "Line 3"]
//!     await io_core.write_lines("output.txt", lines)
//!
//!     # Read DDS texture header for validation (returns tuple)
//!     header = await io_core.read_dds_header("texture.dds")
//!     print(f"Texture size: {header[0]}x{header[1]}")
//!
//!     # Or use DDSHeader class for detailed analysis
//!     from classic_file_io import DDSHeader
//!     with open("texture.dds", "rb") as f:
//!         header = DDSHeader.from_bytes(f.read())
//!         if header:
//!             print(f"Size: {header.width}x{header.height}")
//!             print(f"Format: {header.format}, Mipmaps: {header.mipmap_count}")
//!             if header.is_bc_compressed() and not header.has_valid_bc_dimensions():
//!                 print("ERROR: Invalid BC compression dimensions")
//!
//!     # Batch process DDS headers (40x faster with parallelism)
//!     dds_files = ["tex1.dds", "tex2.dds", "tex3.dds"]
//!     headers = await io_core.read_dds_headers_batch(dds_files)
//!     for file, (width, height) in headers.items():
//!         if width:
//!             print(f"{file}: {width}x{height}")
//!
//!     # Check file existence (cached for performance)
//!     if io_core.file_exists("config.yaml"):
//!         size = io_core.get_file_size("config.yaml")
//!         print(f"Config file size: {size} bytes")
//!
//!     # Clear metadata cache when needed
//!     io_core.clear_cache()
//!
//! asyncio.run(main())
//! ```
//!
//! ## Performance Characteristics
//!
//! - **File reading**: 10x faster than Python with encoding detection
//! - **DDS processing**: 40x faster with parallel batch operations
//! - **Metadata caching**: 100x faster for repeated file_exists/get_file_size calls
//! - **Memory-mapped I/O**: Available for large files (5-10x speedup)
//! - **Async I/O**: Non-blocking operations for concurrent file access
//!
//! ## Thread Safety
//!
//! All file I/O operations are thread-safe and can be called from multiple Python threads
//! or async tasks. Internal caches use DashMap for lock-free concurrent access.
//!
//! ```python
//! from classic_core import file_io
//! import asyncio
//!
//! io_core = file_io.PyFileIOCore.new("utf-8", "ignore", 100, 50)
//!
//! async def worker(filename):
//!     # Safe to call from multiple async tasks
//!     return await io_core.read_file(filename)
//!
//! async def main():
//!     # Concurrent file reading
//!     tasks = [worker(f"log{i}.txt") for i in range(10)]
//!     results = await asyncio.gather(*tasks)
//!     print(f"Read {len(results)} files concurrently")
//!
//! asyncio.run(main())
//! ```

use pyo3::prelude::*;
use pyo3::{create_exception, exceptions::PyException};

// Custom exception types matching Python ClassicLib.integration.exceptions
create_exception!(classic_file_io, RustFileIOError, PyException, "Base for File I/O Rust errors");
create_exception!(classic_file_io, RustFileIOIOError, RustFileIOError, "File I/O errors");
create_exception!(classic_file_io, RustFileIOParseError, RustFileIOError, "File parsing errors (DDS, encoding)");

mod core;
mod dds;
mod encoding;
mod generation;
mod hash;
mod log_collector;

pub use core::PyFileIOCore;
pub use dds::PyDDSHeader;
pub use encoding::PyEncodingDetector;
pub use generation::{
    PyFileGenerator, PyFileGeneratorConfig, generate_ignore_file_async, generate_local_yaml_async,
};
pub use hash::PyFileHasher;
pub use log_collector::PyLogCollector;

/// Python module for file I/O operations
#[pymodule]
fn classic_file_io(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_file_io_module(m)?;
    Ok(())
}

/// Convert FileIOError to PyErr using custom exception types
///
/// Maps Rust FileIOError variants to Python exception types from
/// ClassicLib.integration.exceptions for better error handling.
pub fn to_pyerr(err: classic_file_io_core::FileIOError) -> PyErr {
    use classic_file_io_core::FileIOError;

    match err {
        // I/O errors map to RustFileIOIOError
        FileIOError::IoError(e) => RustFileIOIOError::new_err(format!("I/O error: {}", e)),
        FileIOError::NotFound(s) => RustFileIOIOError::new_err(format!("File not found: {}", s)),
        FileIOError::Io(s) => RustFileIOIOError::new_err(format!("I/O error: {}", s)),
        FileIOError::WriteError { path, source } => {
            RustFileIOIOError::new_err(format!("Failed to write file {}: {}", path.display(), source))
        }
        FileIOError::CreateDirectoryError { path, source } => {
            RustFileIOIOError::new_err(format!("Failed to create directory {}: {}", path.display(), source))
        }

        // Parse/format errors map to RustFileIOParseError
        FileIOError::EncodingError(s) => {
            RustFileIOParseError::new_err(format!("Encoding error: {}", s))
        }
        FileIOError::DDSError(s) => {
            RustFileIOParseError::new_err(format!("DDS error: {}", s))
        }
        FileIOError::InvalidPath(s) => {
            RustFileIOParseError::new_err(format!("Invalid path: {}", s))
        }

        // Generic errors map to base RustFileIOError
        FileIOError::JoinError(s) => {
            RustFileIOError::new_err(format!("Task error: {}", s))
        }
        FileIOError::CacheError(s) => {
            RustFileIOError::new_err(format!("Cache error: {}", s))
        }
    }
}

/// Public registration function for use by facade modules
/// This allows classic-core to include all file_io components in its submodule
pub fn register_file_io_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add version and debug marker
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__debug_registered__", true)?;

    // Add all classes - CRITICAL: PyLogCollector must be added!
    m.add_class::<PyFileIOCore>()?;
    m.add_class::<PyDDSHeader>()?;
    m.add_class::<PyEncodingDetector>()?;
    m.add_class::<PyFileHasher>()?;
    m.add_class::<PyLogCollector>()?; // This MUST add PyLogCollector to the module

    // Phase 5 - File generation
    generation::register(m)?;

    // Register custom exception types
    m.add("RustFileIOError", m.py().get_type::<RustFileIOError>())?;
    m.add("RustFileIOIOError", m.py().get_type::<RustFileIOIOError>())?;
    m.add("RustFileIOParseError", m.py().get_type::<RustFileIOParseError>())?;

    Ok(())
}
