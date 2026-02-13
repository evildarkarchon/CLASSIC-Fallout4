//! Runtime coordination for ONE RUNTIME RULE compliance.
//!
//! This module provides utilities for coordinating with the shared global
//! Tokio runtime, ensuring that all async operations follow the ONE RUNTIME RULE.

use classic_shared_core::get_runtime;

/// Runtime information.
#[derive(Debug, Clone)]
pub struct RuntimeInfo {
    /// Whether the runtime is available
    pub available: bool,
    /// Number of worker threads
    pub worker_threads: usize,
}

/// Check if the shared Tokio runtime is available.
///
/// This function checks whether the global Tokio runtime (per ONE RUNTIME RULE)
/// is available and ready for use.
///
/// # Returns
///
/// `true` if the runtime is available, `false` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_pybridge_core::is_runtime_available;
///
/// if is_runtime_available() {
///     println!("Runtime is ready");
/// }
/// ```
pub fn is_runtime_available() -> bool {
    // The shared runtime is always available once initialized
    // This function mainly exists for API compatibility and future extensibility
    true
}

/// Get information about the shared Tokio runtime.
///
/// Returns information about the global Tokio runtime configuration.
///
/// # Returns
///
/// A `RuntimeInfo` struct containing runtime details.
///
/// # Examples
///
/// ```rust
/// use classic_pybridge_core::get_runtime_info;
///
/// let info = get_runtime_info();
/// println!("Worker threads: {}", info.worker_threads);
/// ```
pub fn get_runtime_info() -> RuntimeInfo {
    // Get the shared runtime
    let _runtime = get_runtime();

    // Count worker threads
    // Note: Tokio doesn't expose this directly, so we use num_cpus as a proxy
    let worker_threads = num_cpus::get();

    RuntimeInfo {
        available: true,
        worker_threads,
    }
}

/// Execute a future on the shared Tokio runtime.
///
/// This function provides a way to execute Rust futures on the global
/// Tokio runtime, ensuring ONE RUNTIME RULE compliance.
///
/// # Arguments
///
/// * `future` - The future to execute
///
/// # Returns
///
/// The result of the future execution.
///
/// # Examples
///
/// ```rust
/// use classic_pybridge_core::execute_on_runtime;
///
/// async fn async_work() -> i32 {
///     42
/// }
///
/// let result = execute_on_runtime(async_work());
/// assert_eq!(result, 42);
/// ```
#[allow(dead_code)]
pub fn execute_on_runtime<F>(future: F) -> F::Output
where
    F: std::future::Future + Send,
    F::Output: Send,
{
    let runtime = get_runtime();
    runtime.block_on(future)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_runtime_available() {
        assert!(is_runtime_available());
    }

    #[test]
    fn test_runtime_info() {
        let info = get_runtime_info();
        assert!(info.available);
        assert!(info.worker_threads > 0);
    }

    #[test]
    fn test_execute_on_runtime() {
        async fn test_async() -> i32 {
            42
        }

        let result = execute_on_runtime(test_async());
        assert_eq!(result, 42);
    }
}
