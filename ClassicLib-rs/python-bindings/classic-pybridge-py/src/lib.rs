//! Python bindings for async bridge utilities.
//!
//! This module provides Python access to the Rust-accelerated async bridge
//! metrics and runtime coordination helpers.

use pyo3::prelude::*;

mod metrics;
mod runtime;

/// Bridge operation type for metrics tracking.
#[pyclass]
#[derive(Clone)]
pub enum BridgeOperationType {
    /// run_async() operation
    RunAsync,
    /// run_async_with_timeout() operation
    RunAsyncWithTimeout,
    /// Event loop creation
    LoopCreation,
    /// Event loop cleanup
    LoopCleanup,
}

impl From<BridgeOperationType> for metrics::BridgeOperation {
    fn from(op: BridgeOperationType) -> Self {
        match op {
            BridgeOperationType::RunAsync => metrics::BridgeOperation::RunAsync,
            BridgeOperationType::RunAsyncWithTimeout => {
                metrics::BridgeOperation::RunAsyncWithTimeout
            }
            BridgeOperationType::LoopCreation => metrics::BridgeOperation::LoopCreation,
            BridgeOperationType::LoopCleanup => metrics::BridgeOperation::LoopCleanup,
        }
    }
}

/// Bridge metrics summary.
#[pyclass]
#[derive(Clone)]
pub struct BridgeMetrics {
    /// Total run_async calls
    #[pyo3(get)]
    pub run_async_count: u64,
    /// Successful run_async calls
    #[pyo3(get)]
    pub run_async_success: u64,
    /// Failed run_async calls
    #[pyo3(get)]
    pub run_async_failure: u64,
    /// Total run_async time (seconds)
    #[pyo3(get)]
    pub run_async_total_time: f64,

    /// Total timeout calls
    #[pyo3(get)]
    pub timeout_count: u64,
    /// Successful timeout calls
    #[pyo3(get)]
    pub timeout_success: u64,
    /// Failed timeout calls
    #[pyo3(get)]
    pub timeout_failure: u64,
    /// Total timeout time (seconds)
    #[pyo3(get)]
    pub timeout_total_time: f64,

    /// Loops created
    #[pyo3(get)]
    pub loops_created: u64,
    /// Loops cleaned up
    #[pyo3(get)]
    pub loops_cleaned: u64,
}

#[pymethods]
impl BridgeMetrics {
    fn __repr__(&self) -> String {
        format!(
            "BridgeMetrics(run_async={}/{}, timeout={}/{}, loops={}/{})",
            self.run_async_success,
            self.run_async_count,
            self.timeout_success,
            self.timeout_count,
            self.loops_cleaned,
            self.loops_created
        )
    }
}

/// Record a bridge operation for metrics.
///
/// This function records timing and success/failure information for
/// async bridge operations.
///
/// Args:
///     operation: The type of operation (BridgeOperationType enum)
///     duration_secs: Duration of the operation in seconds
///     success: Whether the operation succeeded
///
/// Example:
///     >>> import classic_pybridge
///     >>> classic_pybridge.record_operation(
///     ...     classic_pybridge.BridgeOperationType.RunAsync,
///     ...     0.123,
///     ...     True
///     ... )
#[pyfunction]
fn record_operation(operation: BridgeOperationType, duration_secs: f64, success: bool) {
    metrics::record_bridge_operation(operation.into(), duration_secs, success);
}

/// Get bridge metrics summary.
///
/// Returns aggregated statistics for all bridge operations including
/// counts, success/failure rates, and timing information.
///
/// Returns:
///     BridgeMetrics: Summary of all bridge operation metrics
///
/// Example:
///     >>> import classic_pybridge
///     >>> metrics = classic_pybridge.get_metrics()
///     >>> print(f"Total operations: {metrics.run_async_count}")
///     >>> print(f"Success rate: {metrics.run_async_success}/{metrics.run_async_count}")
#[pyfunction]
fn get_metrics() -> BridgeMetrics {
    let metrics = metrics::get_bridge_metrics();

    BridgeMetrics {
        run_async_count: metrics.run_async_count,
        run_async_success: metrics.run_async_success,
        run_async_failure: metrics.run_async_failure,
        run_async_total_time: metrics.run_async_total_time,
        timeout_count: metrics.timeout_count,
        timeout_success: metrics.timeout_success,
        timeout_failure: metrics.timeout_failure,
        timeout_total_time: metrics.timeout_total_time,
        loops_created: metrics.loops_created,
        loops_cleaned: metrics.loops_cleaned,
    }
}

/// Clear all bridge metrics.
///
/// Removes all recorded metrics. Useful for testing or resetting
/// between measurement sessions.
///
/// Example:
///     >>> import classic_pybridge
///     >>> classic_pybridge.clear_metrics()
///     >>> metrics = classic_pybridge.get_metrics()
///     >>> metrics.run_async_count
///     0
#[pyfunction]
fn clear_metrics() {
    metrics::clear_bridge_metrics();
}

/// Check if runtime is available.
///
/// Returns:
///     bool: True if the Tokio runtime is available
///
/// Example:
///     >>> import classic_pybridge
///     >>> classic_pybridge.is_runtime_available()
///     True
#[pyfunction]
fn is_runtime_available() -> bool {
    runtime::is_runtime_available()
}

/// Runtime information.
#[pyclass]
#[derive(Clone)]
pub struct RuntimeInfo {
    /// Whether the runtime is available
    #[pyo3(get)]
    pub available: bool,
    /// Number of worker threads
    #[pyo3(get)]
    pub worker_threads: usize,
}

#[pymethods]
impl RuntimeInfo {
    fn __repr__(&self) -> String {
        format!(
            "RuntimeInfo(available={}, worker_threads={})",
            self.available, self.worker_threads
        )
    }
}

/// Get runtime information.
///
/// Returns:
///     RuntimeInfo: Information about the Tokio runtime
///
/// Example:
///     >>> import classic_pybridge
///     >>> info = classic_pybridge.get_runtime_info()
///     >>> info.worker_threads
///     8
#[pyfunction]
fn get_runtime_info() -> RuntimeInfo {
    let runtime_info = runtime::get_runtime_info();

    RuntimeInfo {
        available: runtime_info.available,
        worker_threads: runtime_info.worker_threads,
    }
}

/// Python module for async bridge utilities.
///
/// This module provides Rust-accelerated metrics tracking and runtime
/// coordination for the AsyncBridge. It integrates with the ONE RUNTIME RULE
/// to ensure all async operations use the shared global Tokio runtime.
///
/// Core Functions:
///     record_operation(operation, duration_secs, success): Record metrics
///     get_metrics(): Get bridge metrics summary
///     clear_metrics(): Clear all metrics
///     is_runtime_available(): Check if runtime is available
///     get_runtime_info(): Get runtime information
///
/// Classes:
///     BridgeOperationType: Enum for operation types
///     BridgeMetrics: Metrics summary
///     RuntimeInfo: Runtime information
///
/// Example:
///     >>> import classic_pybridge
///     >>> # Record an operation
///     >>> classic_pybridge.record_operation(
///     ...     classic_pybridge.BridgeOperationType.RunAsync,
///     ...     0.123,
///     ...     True
///     ... )
///     >>> # Get metrics
///     >>> metrics = classic_pybridge.get_metrics()
///     >>> metrics.run_async_count
///     1
#[pymodule]
fn classic_pybridge(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add enums and classes
    m.add_class::<BridgeOperationType>()?;
    m.add_class::<BridgeMetrics>()?;
    m.add_class::<RuntimeInfo>()?;

    // Add functions
    m.add_function(wrap_pyfunction!(record_operation, m)?)?;
    m.add_function(wrap_pyfunction!(get_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(clear_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(is_runtime_available, m)?)?;
    m.add_function(wrap_pyfunction!(get_runtime_info, m)?)?;

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    #[test]
    #[serial]
    fn test_basic_metrics() {
        metrics::clear_bridge_metrics();

        metrics::record_bridge_operation(metrics::BridgeOperation::RunAsync, 0.1, true);
        metrics::record_bridge_operation(metrics::BridgeOperation::RunAsync, 0.2, true);
        metrics::record_bridge_operation(metrics::BridgeOperation::RunAsync, 0.15, false);

        let metrics = metrics::get_bridge_metrics();
        assert_eq!(metrics.run_async_count, 3);
        assert_eq!(metrics.run_async_success, 2);
        assert_eq!(metrics.run_async_failure, 1);
    }

    #[test]
    fn test_runtime_available() {
        let available = runtime::is_runtime_available();
        assert!(available);
    }
}
