//! Metrics tracking for async bridge operations.
//!
//! This module provides high-performance metrics collection for the AsyncBridge,
//! tracking operation counts, timings, and success/failure rates.

use dashmap::DashMap;
use once_cell::sync::Lazy;

/// Types of bridge operations that can be tracked.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum BridgeOperation {
    /// run_async() calls
    RunAsync,
    /// run_async_with_timeout() calls
    RunAsyncWithTimeout,
    /// Loop creation/initialization
    LoopCreation,
    /// Loop cleanup
    LoopCleanup,
}

/// Aggregated metrics for all bridge operations.
#[derive(Debug, Clone, Default)]
pub struct BridgeMetrics {
    // run_async operations
    /// Total run_async calls
    pub run_async_count: u64,
    /// Successful run_async calls
    pub run_async_success: u64,
    /// Failed run_async calls
    pub run_async_failure: u64,
    /// Total time spent in run_async (seconds)
    pub run_async_total_time: f64,

    // run_async_with_timeout operations
    /// Total run_async_with_timeout calls
    pub timeout_count: u64,
    /// Successful timeout calls
    pub timeout_success: u64,
    /// Failed timeout calls
    pub timeout_failure: u64,
    /// Total time spent in timeout operations (seconds)
    pub timeout_total_time: f64,

    // Loop lifecycle
    /// Number of loops created
    pub loops_created: u64,
    /// Number of loops cleaned up
    pub loops_cleaned: u64,
}

/// Statistics for a single operation type.
#[derive(Debug, Clone, Default)]
struct OperationStats {
    /// Total count
    count: u64,
    /// Successful operations
    success: u64,
    /// Failed operations
    failure: u64,
    /// Total time (seconds)
    total_time: f64,
}

/// Global metrics storage.
static METRICS: Lazy<DashMap<BridgeOperation, OperationStats>> = Lazy::new(DashMap::new);

/// Record a bridge operation.
///
/// This function records metrics for async bridge operations, tracking
/// counts, success/failure rates, and timing information.
///
/// # Arguments
///
/// * `operation` - The type of operation being recorded
/// * `duration_secs` - Duration of the operation in seconds
/// * `success` - Whether the operation succeeded
///
/// # Examples
///
/// ```ignore
/// use classic_pybridge::{record_bridge_operation, BridgeOperation};
///
/// record_bridge_operation(BridgeOperation::RunAsync, 0.123, true);
/// ```
pub fn record_bridge_operation(operation: BridgeOperation, duration_secs: f64, success: bool) {
    // `entry().or_default()` returns a `RefMut` that holds the DashMap shard lock for its
    // entire lifetime. All field updates below are collectively atomic per call — two
    // threads recording the same operation will serialize on the shard lock rather than
    // racing. This differs from the `Arc<AtomicU64>` approach in pool_sqlx.rs; both are
    // correct, but the locking here is implicit rather than explicit.
    let mut stats = METRICS.entry(operation).or_default();

    stats.count += 1;
    if success {
        stats.success += 1;
    } else {
        stats.failure += 1;
    }
    stats.total_time += duration_secs;
}

/// Get aggregated bridge metrics.
///
/// Returns a snapshot of all bridge operation metrics.
///
/// # Returns
///
/// A `BridgeMetrics` struct containing aggregated statistics.
///
/// # Examples
///
/// ```ignore
/// use classic_pybridge::get_bridge_metrics;
///
/// let metrics = get_bridge_metrics();
/// println!("Total run_async calls: {}", metrics.run_async_count);
/// ```
pub fn get_bridge_metrics() -> BridgeMetrics {
    let mut result = BridgeMetrics::default();

    // Aggregate run_async stats
    if let Some(stats) = METRICS.get(&BridgeOperation::RunAsync) {
        result.run_async_count = stats.count;
        result.run_async_success = stats.success;
        result.run_async_failure = stats.failure;
        result.run_async_total_time = stats.total_time;
    }

    // Aggregate timeout stats
    if let Some(stats) = METRICS.get(&BridgeOperation::RunAsyncWithTimeout) {
        result.timeout_count = stats.count;
        result.timeout_success = stats.success;
        result.timeout_failure = stats.failure;
        result.timeout_total_time = stats.total_time;
    }

    // Aggregate loop creation stats
    if let Some(stats) = METRICS.get(&BridgeOperation::LoopCreation) {
        result.loops_created = stats.count;
    }

    // Aggregate loop cleanup stats
    if let Some(stats) = METRICS.get(&BridgeOperation::LoopCleanup) {
        result.loops_cleaned = stats.count;
    }

    result
}

/// Clear all bridge metrics.
///
/// This removes all recorded metrics. Useful for testing or resetting
/// between measurement sessions.
///
/// # Examples
///
/// ```ignore
/// use classic_pybridge::clear_bridge_metrics;
///
/// clear_bridge_metrics();
/// ```
pub fn clear_bridge_metrics() {
    METRICS.clear();
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    #[test]
    #[serial]
    fn test_record_and_retrieve() {
        clear_bridge_metrics();

        record_bridge_operation(BridgeOperation::RunAsync, 0.1, true);
        record_bridge_operation(BridgeOperation::RunAsync, 0.2, true);
        record_bridge_operation(BridgeOperation::RunAsync, 0.15, false);

        let metrics = get_bridge_metrics();
        assert_eq!(metrics.run_async_count, 3);
        assert_eq!(metrics.run_async_success, 2);
        assert_eq!(metrics.run_async_failure, 1);
        assert!((metrics.run_async_total_time - 0.45).abs() < 0.01);
    }

    #[test]
    #[serial]
    fn test_timeout_operations() {
        clear_bridge_metrics();

        record_bridge_operation(BridgeOperation::RunAsyncWithTimeout, 0.5, true);
        record_bridge_operation(BridgeOperation::RunAsyncWithTimeout, 1.0, false);

        let metrics = get_bridge_metrics();
        assert_eq!(metrics.timeout_count, 2);
        assert_eq!(metrics.timeout_success, 1);
        assert_eq!(metrics.timeout_failure, 1);
        assert!((metrics.timeout_total_time - 1.5).abs() < 0.01);
    }

    #[test]
    #[serial]
    fn test_loop_lifecycle() {
        clear_bridge_metrics();

        record_bridge_operation(BridgeOperation::LoopCreation, 0.001, true);
        record_bridge_operation(BridgeOperation::LoopCreation, 0.001, true);
        record_bridge_operation(BridgeOperation::LoopCleanup, 0.001, true);

        let metrics = get_bridge_metrics();
        assert_eq!(metrics.loops_created, 2);
        assert_eq!(metrics.loops_cleaned, 1);
    }

    #[test]
    #[serial]
    fn test_clear_metrics() {
        clear_bridge_metrics();

        record_bridge_operation(BridgeOperation::RunAsync, 0.1, true);
        assert_eq!(get_bridge_metrics().run_async_count, 1);

        clear_bridge_metrics();
        assert_eq!(get_bridge_metrics().run_async_count, 0);
    }

    #[test]
    #[serial]
    fn test_concurrent_recording() {
        use std::thread;

        clear_bridge_metrics();

        let handles: Vec<_> = (0..10)
            .map(|i| {
                thread::spawn(move || {
                    for _ in 0..10 {
                        record_bridge_operation(BridgeOperation::RunAsync, 0.001, i % 2 == 0);
                    }
                })
            })
            .collect();

        for handle in handles {
            handle.join().unwrap();
        }

        let metrics = get_bridge_metrics();
        assert_eq!(metrics.run_async_count, 100);
        assert_eq!(metrics.run_async_success, 50);
        assert_eq!(metrics.run_async_failure, 50);
    }
}
