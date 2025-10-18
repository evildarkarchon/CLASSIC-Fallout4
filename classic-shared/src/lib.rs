//! CLASSIC Shared - Foundation utilities for CLASSIC Rust extensions
//!
//! This crate provides shared infrastructure used by all other CLASSIC Rust modules,
//! including the global runtime (ONE RUNTIME RULE), error types, and common utilities.

use once_cell::sync::Lazy;
use pyo3::prelude::*;
use tokio::runtime::Runtime;

// Module declarations
pub mod errors;
pub mod path;
pub mod performance;
pub mod strings;

// GUI bridge module (optional, enabled with "gui-bridge" feature)
#[cfg(feature = "gui-bridge")]
pub mod async_bridge;

// Re-export key types
pub use errors::{ClassicError, ClassicResult, IntoClassicError};
pub use path::PathHandler;
pub use performance::RustPerformanceMonitor;
pub use strings::StringProcessor;

#[cfg(feature = "gui-bridge")]
pub use async_bridge::AsyncBridge;

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

/// Helper to run a function without the GIL (PyO3 0.26 compatible)
///
/// This provides a convenient way to release the GIL during CPU-intensive or blocking operations.
/// In PyO3 0.26, `Python::detach()` itself takes a closure and handles GIL release/reacquire.
///
/// # Examples
/// ```rust,no_run
/// use classic_shared::without_gil;
/// use pyo3::prelude::*;
///
/// pub fn expensive_operation(py: Python<'_>, data: Vec<u8>) -> PyResult<String> {
///     // Release GIL during long-running computation
///     without_gil(py, || {
///         // This code runs without holding the GIL
///         process_data(data)
///     })
/// }
/// ```
///
/// # When to use
/// - I/O operations (file reading, network, database queries)
/// - CPU-intensive calculations
/// - Blocking operations that don't need Python access
/// - Any operation that takes > 1ms
///
/// # When NOT to use
/// - Operations that need to call Python code
/// - Very fast operations (< 1ms) where overhead isn't worth it
/// - When you need to access Python objects during execution
#[inline]
pub fn without_gil<F, R>(py: Python<'_>, f: F) -> R
where
    F: FnOnce() -> R + Send,
    R: Send,
{
    // PyO3 0.26: detach() takes a closure
    py.detach(f)
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
