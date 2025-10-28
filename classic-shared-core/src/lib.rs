//! CLASSIC Shared Core - Pure Rust foundation for CLASSIC extensions
//!
//! This crate provides the pure Rust business logic foundation used by all CLASSIC crates,
//! including the global runtime (ONE RUNTIME RULE), error types, and common utilities.
//!
//! # Architecture
//!
//! This is the **-core** layer containing pure Rust business logic with NO PyO3 dependencies.
//! Python bindings are provided separately in `classic-shared-py`.
//!
//! # The ONE RUNTIME RULE
//!
//! All CLASSIC crates MUST use the shared runtime via [`get_runtime()`] to avoid deadlocks.
//! Creating additional runtimes will cause nested runtime errors and deadlocks.

use once_cell::sync::Lazy;
use tokio::runtime::Runtime;

// Module declarations
pub mod errors;
pub mod path_core;
pub mod performance_core;
pub mod strings_core;

// GUI bridge module (optional, enabled with "gui-bridge" feature)
#[cfg(feature = "gui-bridge")]
pub mod async_bridge;

// Re-export key types
pub use errors::{ClassicError, ClassicResult, IntoClassicError};

#[cfg(feature = "gui-bridge")]
pub use async_bridge::AsyncBridge;

/// Shared tokio runtime for all async operations (ONE RUNTIME RULE)
///
/// This is the ONLY runtime that should exist in the entire application.
/// All CLASSIC crates MUST use this runtime via [`get_runtime()`] to avoid deadlocks.
///
/// # Architecture
///
/// - Single multi-threaded runtime shared across all crates
/// - Worker threads = available parallelism (or 4 as fallback)
/// - Enables all features (IO, time, fs, net, etc.)
/// - Prevents deadlocks from multiple runtimes
///
/// # Usage
///
/// ```rust
/// use classic_shared_core::get_runtime;
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
///
/// ```rust,no_run
/// use classic_shared_core::get_runtime;
///
/// // Use the shared runtime for async operations
/// pub fn read_file(path: String) -> Result<String, std::io::Error> {
///     get_runtime().block_on(async move {
///         tokio::fs::read_to_string(path).await
///     })
/// }
/// ```
///
/// # The ONE RUNTIME RULE
///
/// Never create your own runtime with `Runtime::new()` or `tokio::runtime::Builder`.
/// Always use this function to get the shared runtime.
pub fn get_runtime() -> &'static Runtime {
    &RUNTIME
}
