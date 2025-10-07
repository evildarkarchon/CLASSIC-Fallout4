//! CLASSIC Shared - Foundation utilities for CLASSIC Rust extensions
//!
//! This crate provides shared infrastructure used by all other CLASSIC Rust modules,
//! including the global runtime (ONE RUNTIME RULE), error types, and common utilities.

use pyo3::prelude::*;
use tokio::runtime::Runtime;
use once_cell::sync::Lazy;

// Module declarations
pub mod errors;
pub mod path;
pub mod performance;
pub mod strings;

// Re-export key types
pub use errors::{ClassicError, ClassicResult, IntoClassicError};
pub use path::PathHandler;
pub use performance::RustPerformanceMonitor;
pub use strings::StringProcessor;

/// Shared tokio runtime for all async operations (ONE RUNTIME RULE)
///
/// This is the ONLY runtime that should exist in the entire application.
/// All CLASSIC crates MUST use this runtime via get_runtime() to avoid deadlocks.
///
/// # Architecture
/// - Single multi-threaded runtime shared across all crates
/// - Worker threads = available parallelism (or 4 as fallback)
/// - Enables all features (IO, time, fs, net, etc.)
/// - Prevents deadlocks from multiple runtimes
///
/// # Usage
/// ```rust
/// use classic_shared::get_runtime;
///
/// let result = get_runtime().block_on(async {
///     // Your async code here
///     tokio::fs::read_to_string("file.txt").await
/// });
/// ```
pub(crate) static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    let worker_threads = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);

    tokio::runtime::Builder::new_multi_thread()
        .worker_threads(worker_threads)
        .enable_all()
        .build()
        .expect("Failed to create Tokio runtime")
});

/// Get a reference to the global runtime
///
/// Use this function in all CLASSIC crates instead of creating new runtimes.
///
/// # Examples
/// ```rust,no_run
/// use classic_shared::get_runtime;
/// use pyo3::prelude::*;
///
/// // Sync API to Python, async internally
/// pub fn read_file(path: String) -> PyResult<String> {
///     get_runtime().block_on(async move {
///         tokio::fs::read_to_string(path).await
///     }).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
/// }
/// ```
pub fn get_runtime() -> &'static Runtime {
    &RUNTIME
}

/// Python module initialization
#[pymodule]
fn classic_shared(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add utility classes
    m.add_class::<StringProcessor>()?;
    m.add_class::<PathHandler>()?;
    m.add_class::<RustPerformanceMonitor>()?;

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
