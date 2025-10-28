//! Performance monitoring integration for Rust extensions (Pure Rust)
//!
//! This module provides performance tracking for unified metrics collection.
//! Python bindings are in `classic-shared-py`.

use dashmap::DashMap;
use once_cell::sync::Lazy;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

/// Global performance metrics collector
static METRICS: Lazy<Arc<PerformanceMetrics>> = Lazy::new(|| Arc::new(PerformanceMetrics::new()));

/// Global reference instant for timer measurements
static TIMER_START: Lazy<Instant> = Lazy::new(Instant::now);

/// Performance metrics storage
///
/// Thread-safe storage for tracking operation timings, counts, and bytes processed.
pub struct PerformanceMetrics {
    /// Operation timings: name -> list of durations
    timings: DashMap<String, Vec<Duration>>,
    /// Operation counts
    counts: DashMap<String, AtomicUsize>,
    /// Total bytes processed by operation
    bytes_processed: DashMap<String, AtomicU64>,
}

impl Default for PerformanceMetrics {
    fn default() -> Self {
        Self::new()
    }
}

impl PerformanceMetrics {
    /// Creates a new `PerformanceMetrics` instance with empty metrics.
    pub fn new() -> Self {
        Self {
            timings: DashMap::new(),
            counts: DashMap::new(),
            bytes_processed: DashMap::new(),
        }
    }

    /// Record a timing for an operation
    pub fn record_timing(&self, operation: &str, duration: Duration) {
        self.timings
            .entry(operation.to_string())
            .or_insert_with(Vec::new)
            .push(duration);

        self.counts
            .entry(operation.to_string())
            .or_insert_with(|| AtomicUsize::new(0))
            .fetch_add(1, Ordering::Relaxed);
    }

    /// Record bytes processed
    pub fn record_bytes(&self, operation: &str, bytes: u64) {
        self.bytes_processed
            .entry(operation.to_string())
            .or_insert_with(|| AtomicU64::new(0))
            .fetch_add(bytes, Ordering::Relaxed);
    }

    /// Get statistics for an operation
    pub fn get_stats(&self, operation: &str) -> Option<OperationStats> {
        let timings = self.timings.get(operation)?;
        let count = self.counts.get(operation)?.load(Ordering::Relaxed);
        let bytes = self
            .bytes_processed
            .get(operation)
            .map(|b| b.load(Ordering::Relaxed))
            .unwrap_or(0);

        if timings.is_empty() {
            return None;
        }

        let total: Duration = timings.iter().sum();
        let avg = if count > 0 {
            total / count.try_into().unwrap_or(u32::MAX)
        } else {
            Duration::ZERO
        };
        let min = *timings.iter().min()?;
        let max = *timings.iter().max()?;

        Some(OperationStats {
            count,
            total,
            average: avg,
            min,
            max,
            bytes_processed: bytes,
        })
    }

    /// Get all operation names with recorded metrics
    pub fn get_operations(&self) -> Vec<String> {
        self.timings.iter().map(|entry| entry.key().clone()).collect()
    }

    /// Clear all metrics
    pub fn clear(&self) {
        self.timings.clear();
        self.counts.clear();
        self.bytes_processed.clear();
    }
}

/// Statistics for a single operation type
#[derive(Clone, Debug)]
pub struct OperationStats {
    /// Number of times this operation was executed
    pub count: usize,
    /// Total time spent on this operation
    pub total: Duration,
    /// Average time per operation
    pub average: Duration,
    /// Minimum time for a single operation
    pub min: Duration,
    /// Maximum time for a single operation
    pub max: Duration,
    /// Total bytes processed by this operation
    pub bytes_processed: u64,
}

impl OperationStats {
    /// Calculate throughput in bytes per second
    pub fn throughput(&self) -> Option<f64> {
        if self.bytes_processed > 0 && self.total.as_secs() > 0 {
            Some(self.bytes_processed as f64 / self.total.as_secs_f64())
        } else {
            None
        }
    }
}

/// Performance timer for measuring operation duration
///
/// Automatically records timing metrics when dropped or explicitly stopped.
#[must_use = "Timer should be stored and stopped or dropped to record metrics"]
pub struct Timer {
    /// Operation name (None if already stopped)
    operation: Option<String>,
    /// Start time of the operation
    start: Instant,
    /// Optional bytes processed during operation
    bytes: Option<u64>,
}

impl Timer {
    /// Start a new timer for the given operation
    pub fn start(operation: impl Into<String>) -> Self {
        Self {
            operation: Some(operation.into()),
            start: Instant::now(),
            bytes: None,
        }
    }

    /// Set the number of bytes processed during this operation
    pub fn set_bytes(&mut self, bytes: u64) {
        self.bytes = Some(bytes);
    }

    /// Stop the timer and record metrics
    pub fn stop(mut self) {
        if let Some(operation) = self.operation.take() {
            let duration = self.start.elapsed();
            METRICS.record_timing(&operation, duration);

            if let Some(bytes) = self.bytes {
                METRICS.record_bytes(&operation, bytes);
            }
        }
    }
}

impl Drop for Timer {
    fn drop(&mut self) {
        // Auto-stop if not explicitly stopped
        if let Some(ref operation) = self.operation {
            let duration = self.start.elapsed();
            METRICS.record_timing(operation, duration);

            if let Some(bytes) = self.bytes {
                METRICS.record_bytes(operation, bytes);
            }
        }
    }
}

/// Macro for timing a block of code
#[macro_export]
macro_rules! timed {
    ($name:expr, $block:block) => {{
        let _timer = $crate::performance_core::Timer::start($name);
        $block
    }};
}

/// Helper function to time async operations
pub async fn time_async<F, T>(operation: impl Into<String>, future: F) -> T
where
    F: std::future::Future<Output = T>,
{
    let operation = operation.into();
    let start = Instant::now();

    let result = future.await;

    let duration = start.elapsed();
    METRICS.record_timing(&operation, duration);

    result
}

/// Helper function to time sync operations with result
pub fn time_operation<F, T>(operation: impl Into<String>, f: F) -> T
where
    F: FnOnce() -> T,
{
    let timer = Timer::start(operation);
    let result = f();
    timer.stop();
    result
}

/// Helper function to time operations that process bytes
pub fn time_with_bytes<F, T>(operation: impl Into<String>, bytes: u64, f: F) -> T
where
    F: FnOnce() -> T,
{
    let mut timer = Timer::start(operation);
    timer.set_bytes(bytes);
    let result = f();
    timer.stop();
    result
}

/// Get a reference to the global metrics collector
pub fn get_global_metrics() -> &'static Arc<PerformanceMetrics> {
    &METRICS
}

/// Get the global timer start instant
pub fn get_timer_start() -> Instant {
    *TIMER_START
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn test_timer() {
        METRICS.clear();

        let timer = Timer::start("test_operation");
        thread::sleep(Duration::from_millis(10));
        timer.stop();

        let stats = METRICS.get_stats("test_operation").unwrap();
        assert_eq!(stats.count, 1);
        assert!(stats.total >= Duration::from_millis(10));
    }

    #[test]
    fn test_timed_macro() {
        timed!("macro_test", {
            thread::sleep(Duration::from_millis(5));
        });

        let stats = METRICS.get_stats("macro_test").unwrap();
        assert_eq!(stats.count, 1);
    }
}
