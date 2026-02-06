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

use std::sync::LazyLock;
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
pub use async_bridge::{AsyncBridge, BridgeError, EventLoopDispatcher, SlintDispatcher, set_dispatcher};

/// Configuration for the global Tokio runtime
///
/// This allows tuning the runtime behavior for different workload characteristics.
/// The default configuration is suitable for most use cases.
///
/// # Examples
///
/// ```rust
/// use classic_shared_core::RuntimeConfig;
///
/// // Use default configuration
/// let config = RuntimeConfig::default();
///
/// // Custom configuration for I/O-heavy workload
/// let config = RuntimeConfig {
///     worker_threads: Some(4),
///     enable_io: true,
///     enable_time: true,
///     thread_name: "classic-io".to_string(),
///     ..Default::default()
/// };
/// ```
#[derive(Clone, Debug)]
pub struct RuntimeConfig {
    /// Number of worker threads (None = available parallelism)
    pub worker_threads: Option<usize>,
    /// Enable I/O driver (required for file/network operations)
    pub enable_io: bool,
    /// Enable time driver (required for timeouts/intervals)
    pub enable_time: bool,
    /// Thread stack size in bytes (None = default 2MB)
    pub stack_size: Option<usize>,
    /// Thread name prefix
    pub thread_name: String,
}

impl Default for RuntimeConfig {
    fn default() -> Self {
        Self {
            worker_threads: None, // Use available parallelism
            enable_io: true,
            enable_time: true,
            stack_size: None, // Use tokio default (2MB)
            thread_name: "tokio-worker".to_string(),
        }
    }
}

impl RuntimeConfig {
    /// Create a configuration optimized for I/O-heavy workloads
    ///
    /// This configuration uses fewer threads and enables all I/O features.
    pub fn io_optimized() -> Self {
        Self {
            worker_threads: Some(4),
            thread_name: "classic-io".to_string(),
            ..Default::default()
        }
    }

    /// Create a configuration optimized for CPU-heavy workloads
    ///
    /// This configuration uses all available cores for maximum parallelism.
    pub fn cpu_optimized() -> Self {
        Self {
            worker_threads: None, // Use all available cores
            thread_name: "classic-cpu".to_string(),
            ..Default::default()
        }
    }

    /// Create a minimal configuration for resource-constrained environments
    ///
    /// Uses 2 worker threads and reduced stack size.
    pub fn minimal() -> Self {
        Self {
            worker_threads: Some(2),
            stack_size: Some(1024 * 1024), // 1MB stack
            thread_name: "classic-min".to_string(),
            ..Default::default()
        }
    }

    /// Apply this configuration to a runtime builder
    ///
    /// This is used internally but provided for advanced customization.
    pub fn apply_to_builder(
        &self,
        mut builder: tokio::runtime::Builder,
    ) -> tokio::runtime::Builder {
        let worker_threads = self.worker_threads.unwrap_or_else(|| {
            std::thread::available_parallelism()
                .map(|n| n.get())
                .unwrap_or(4)
        });

        builder.worker_threads(worker_threads);

        if self.enable_io {
            builder.enable_io();
        }
        if self.enable_time {
            builder.enable_time();
        }

        if let Some(size) = self.stack_size {
            builder.thread_stack_size(size);
        }

        builder.thread_name(&self.thread_name);

        builder
    }
}

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
/// - Configured via [`RuntimeConfig`] with default settings
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
pub(crate) static RUNTIME: LazyLock<Runtime> = LazyLock::new(|| {
    let config = RuntimeConfig::default();

    // Build runtime with configuration
    let builder = tokio::runtime::Builder::new_multi_thread();
    let mut builder = config.apply_to_builder(builder);

    builder.build().expect("Failed to create Tokio runtime")
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
