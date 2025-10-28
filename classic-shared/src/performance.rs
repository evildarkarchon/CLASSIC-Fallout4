//! Performance monitoring integration for Rust extensions
//!
//! This module provides performance tracking that integrates with
//! Python's PerformanceMonitor for unified metrics collection.

use dashmap::DashMap;
use once_cell::sync::Lazy;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

/// Global performance metrics collector
static METRICS: Lazy<Arc<PerformanceMetrics>> = Lazy::new(|| Arc::new(PerformanceMetrics::new()));

/// Global reference instant for timer measurements
/// Used to convert Instant to f64 for Python interop
static TIMER_START: Lazy<Instant> = Lazy::new(Instant::now);

/// Performance metrics storage
///
/// Thread-safe storage for tracking operation timings, counts, and bytes processed.
/// Uses `DashMap` for lock-free concurrent access across multiple threads.
pub struct PerformanceMetrics {
    /// Operation timings: name -> list of durations
    ///
    /// Stores all individual timing measurements for each operation type.
    timings: DashMap<String, Vec<Duration>>,

    /// Operation counts
    ///
    /// Tracks how many times each operation has been performed.
    counts: DashMap<String, AtomicUsize>,

    /// Total bytes processed by operation
    ///
    /// Accumulates the total bytes processed for throughput calculations.
    bytes_processed: DashMap<String, AtomicU64>,
}

impl Default for PerformanceMetrics {
    fn default() -> Self {
        Self::new()
    }
}

impl PerformanceMetrics {
    /// Creates a new `PerformanceMetrics` instance with empty metrics.
    ///
    /// This is equivalent to `Default::default()`.
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
        // Use saturating conversion to prevent overflow/panic if count > u32::MAX
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

/// Performance timer for measuring operation duration
///
/// Automatically records timing metrics when dropped or explicitly stopped.
/// Use the `start()` method to begin timing, optionally set bytes with `set_bytes()`,
/// and either call `stop()` explicitly or let it drop to auto-record.
///
/// # Examples
/// ```rust
/// use classic_shared::performance::Timer;
///
/// let timer = Timer::start("file_processing");
/// // Do work...
/// timer.stop(); // Explicitly stop and record
///
/// // Or let it auto-stop on drop:
/// {
///     let timer = Timer::start("auto_operation");
///     // Do work...
/// } // Timer drops here and auto-records
/// ```
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
    ///
    /// Returns a `Timer` that will automatically record metrics when dropped
    /// or when `stop()` is called explicitly.
    ///
    /// # Examples
    /// ```rust
    /// use classic_shared::performance::Timer;
    ///
    /// let timer = Timer::start("database_query");
    /// // Perform database query...
    /// timer.stop();
    /// ```
    #[must_use = "Timer should be stored and stopped or dropped to record metrics"]
    pub fn start(operation: impl Into<String>) -> Self {
        Self {
            operation: Some(operation.into()),
            start: Instant::now(),
            bytes: None,
        }
    }

    /// Set the number of bytes processed during this operation
    ///
    /// This is used to calculate throughput metrics (bytes/sec).
    ///
    /// # Examples
    /// ```rust
    /// use classic_shared::performance::Timer;
    ///
    /// let mut timer = Timer::start("file_read");
    /// let data = vec![0u8; 1024]; // Read 1KB
    /// timer.set_bytes(data.len() as u64);
    /// timer.stop();
    /// ```
    pub fn set_bytes(&mut self, bytes: u64) {
        self.bytes = Some(bytes);
    }

    /// Stop the timer and record metrics
    ///
    /// Consumes the timer to prevent double-recording via the Drop implementation.
    /// If you don't call this method, the timer will auto-record when dropped.
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
        let _timer = $crate::performance::Timer::start($name);
        $block
    }};
}

/// Python-exposed performance monitor
#[pyclass]
pub struct RustPerformanceMonitor;

#[pymethods]
impl RustPerformanceMonitor {
    /// Creates a new `RustPerformanceMonitor` instance.
    #[new]
    pub fn new() -> Self {
        Self
    }

    /// Start timing an operation
    ///
    /// Returns a dictionary containing the operation name and start time (as f64 seconds).
    /// Pass this dictionary to `stop_timer()` to record the elapsed time.
    ///
    /// # Examples
    /// ```python
    /// monitor = RustPerformanceMonitor()
    /// timer = monitor.start_timer("my_operation")
    /// # ... do work ...
    /// monitor.stop_timer(timer)
    /// ```
    #[pyo3(signature = (operation))]
    pub fn start_timer(&self, py: Python, operation: String) -> PyResult<Py<PyAny>> {
        let timer_dict = PyDict::new(py);
        timer_dict.set_item("operation", operation.clone())?;
        // Store elapsed seconds from global reference instant for accurate timing
        let start_time = TIMER_START.elapsed().as_secs_f64();
        timer_dict.set_item("start_time", start_time)?;

        Ok(timer_dict.unbind().into())
    }

    /// Stop timing an operation
    ///
    /// Calculates the elapsed time since `start_timer()` was called and records
    /// the timing metrics.
    ///
    /// # Arguments
    /// * `timer_info` - Dictionary returned from `start_timer()`
    /// * `bytes_processed` - Optional number of bytes processed during the operation
    ///
    /// # Examples
    /// ```python
    /// monitor = RustPerformanceMonitor()
    /// timer = monitor.start_timer("file_read")
    /// data = read_file(path)
    /// monitor.stop_timer(timer, bytes_processed=len(data))
    /// ```
    #[pyo3(signature = (timer_info, bytes_processed=None))]
    pub fn stop_timer(
        &self,
        timer_info: &Bound<'_, PyDict>,
        bytes_processed: Option<u64>,
    ) -> PyResult<()> {
        let operation: String = timer_info
            .get_item("operation")?
            .ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'operation' key")
            })?
            .extract()?;

        let start_time: f64 = timer_info
            .get_item("start_time")?
            .ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'start_time' key")
            })?
            .extract()?;

        // Calculate actual elapsed time from global reference
        let current_time = TIMER_START.elapsed().as_secs_f64();
        let duration = Duration::from_secs_f64(current_time - start_time);

        METRICS.record_timing(&operation, duration);

        if let Some(bytes) = bytes_processed {
            METRICS.record_bytes(&operation, bytes);
        }

        Ok(())
    }

    /// Get performance statistics for all operations
    pub fn get_all_stats(&self, py: Python) -> PyResult<Py<PyDict>> {
        let stats_dict = PyDict::new(py);

        for entry in METRICS.timings.iter() {
            let operation = entry.key();
            if let Some(stats) = METRICS.get_stats(operation) {
                let op_dict = PyDict::new(py);
                op_dict.set_item("count", stats.count)?;
                op_dict.set_item("total_ms", stats.total.as_millis() as u64)?;
                op_dict.set_item("avg_ms", stats.average.as_millis() as u64)?;
                op_dict.set_item("min_ms", stats.min.as_millis() as u64)?;
                op_dict.set_item("max_ms", stats.max.as_millis() as u64)?;
                op_dict.set_item("bytes_processed", stats.bytes_processed)?;

                // Calculate throughput if bytes were processed
                if stats.bytes_processed > 0 && stats.total.as_secs() > 0 {
                    let throughput = stats.bytes_processed as f64 / stats.total.as_secs_f64();
                    op_dict.set_item("throughput_bytes_per_sec", throughput)?;
                }

                stats_dict.set_item(operation.clone(), op_dict)?;
            }
        }

        Ok(stats_dict.unbind())
    }

    /// Get statistics for a specific operation
    pub fn get_operation_stats(
        &self,
        py: Python,
        operation: String,
    ) -> PyResult<Option<Py<PyDict>>> {
        match METRICS.get_stats(&operation) {
            Some(stats) => {
                let op_dict = PyDict::new(py);
                op_dict.set_item("count", stats.count)?;
                op_dict.set_item("total_ms", stats.total.as_millis() as u64)?;
                op_dict.set_item("avg_ms", stats.average.as_millis() as u64)?;
                op_dict.set_item("min_ms", stats.min.as_millis() as u64)?;
                op_dict.set_item("max_ms", stats.max.as_millis() as u64)?;
                op_dict.set_item("bytes_processed", stats.bytes_processed)?;

                if stats.bytes_processed > 0 && stats.total.as_secs() > 0 {
                    let throughput = stats.bytes_processed as f64 / stats.total.as_secs_f64();
                    op_dict.set_item("throughput_bytes_per_sec", throughput)?;
                }

                Ok(Some(op_dict.unbind()))
            }
            None => Ok(None),
        }
    }

    /// Clear all performance metrics
    pub fn clear_metrics(&self) {
        METRICS.clear();
    }

    /// Record a custom metric
    #[pyo3(signature = (operation, duration_ms, bytes_processed=None))]
    pub fn record_metric(&self, operation: String, duration_ms: u64, bytes_processed: Option<u64>) {
        let duration = Duration::from_millis(duration_ms);
        METRICS.record_timing(&operation, duration);

        if let Some(bytes) = bytes_processed {
            METRICS.record_bytes(&operation, bytes);
        }
    }
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn test_timer() {
        // Clear any previous metrics for this test
        METRICS.clear();

        let timer = Timer::start("test_operation");
        thread::sleep(Duration::from_millis(10));
        timer.stop();

        // Now the timer.stop() takes ownership and prevents Drop from recording again
        let stats = METRICS.get_stats("test_operation").unwrap();
        assert_eq!(stats.count, 1); // Exactly 1 recording
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
