//! PyO3 bindings for performance monitoring

use classic_shared_core::performance_core::{self, TimingError};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Convert a rejected timing record into `ValueError("<code>: <message>")`.
fn timing_error_to_py(error: TimingError) -> PyErr {
    PyValueError::new_err(error.coded_message())
}

/// Performance monitor for Python (Python wrapper)
///
/// This class provides Python access to the Rust performance monitoring system.
/// Every instance views this extension's shared-core default metrics store, so
/// clearing through one instance clears timing and byte state for all of them.
#[pyclass(name = "RustPerformanceMonitor")]
pub struct PyRustPerformanceMonitor;

impl Default for PyRustPerformanceMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyRustPerformanceMonitor {
    /// Creates a new `RustPerformanceMonitor` instance.
    #[new]
    pub fn new() -> Self {
        Self
    }

    /// Start timing an operation.
    ///
    /// Returns a dictionary containing the operation name and start time.
    /// Pass this dictionary to `stop_timer()` to record the elapsed time.
    ///
    /// # Arguments
    /// * `operation` - Name of the operation to time
    ///
    /// # Returns
    /// Dictionary with "operation" and "start_time" keys
    #[pyo3(signature = (operation))]
    pub fn start_timer(&self, py: Python, operation: String) -> PyResult<Py<PyAny>> {
        let timer_dict = PyDict::new(py);
        timer_dict.set_item("operation", operation.clone())?;

        // Store elapsed seconds from global reference instant
        let start_time = performance_core::get_timer_start().elapsed().as_secs_f64();
        timer_dict.set_item("start_time", start_time)?;

        Ok(timer_dict.unbind().into())
    }

    /// Stop timing an operation and record metrics.
    ///
    /// # Arguments
    /// * `timer_info` - Dictionary returned from `start_timer()`
    /// * `bytes_processed` - Optional number of bytes processed
    ///
    /// # Errors
    /// Raises `ValueError` when the elapsed time derived from `start_time` is
    /// negative or not finite (for example a forged start time), or when the
    /// timing or byte totals would overflow. Nothing is recorded in that case.
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

        // Calculate actual elapsed time. `start_time` comes from Python and may
        // be forged, so the difference goes through the validating conversion
        // instead of `Duration::from_secs_f64`, which would panic.
        let current_time = performance_core::get_timer_start().elapsed().as_secs_f64();
        let duration = performance_core::duration_from_secs_f64(current_time - start_time)
            .map_err(timing_error_to_py)?;

        performance_core::get_global_metrics()
            .record_timing_with_bytes(&operation, duration, bytes_processed)
            .map_err(timing_error_to_py)
    }

    /// Get performance statistics for all operations.
    ///
    /// # Returns
    /// Dictionary mapping operation names to their statistics
    pub fn get_all_stats(&self, py: Python) -> PyResult<Py<PyDict>> {
        let stats_dict = PyDict::new(py);
        let metrics = performance_core::get_global_metrics();

        for operation in metrics.get_operations() {
            if let Some(stats) = metrics.get_stats(&operation) {
                let op_dict = PyDict::new(py);
                op_dict.set_item("count", stats.count)?;
                op_dict.set_item("total_ms", stats.total.as_millis() as u64)?;
                op_dict.set_item("avg_ms", stats.average.as_millis() as u64)?;
                op_dict.set_item("min_ms", stats.min.as_millis() as u64)?;
                op_dict.set_item("max_ms", stats.max.as_millis() as u64)?;
                op_dict.set_item("bytes_processed", stats.bytes_processed)?;

                // Calculate throughput if bytes were processed
                if let Some(throughput) = stats.throughput() {
                    op_dict.set_item("throughput_bytes_per_sec", throughput)?;
                }

                stats_dict.set_item(operation.clone(), op_dict)?;
            }
        }

        Ok(stats_dict.unbind())
    }

    /// Get statistics for a specific operation.
    ///
    /// # Arguments
    /// * `operation` - Name of the operation
    ///
    /// # Returns
    /// Dictionary with statistics, or None if not found
    pub fn get_operation_stats(
        &self,
        py: Python,
        operation: String,
    ) -> PyResult<Option<Py<PyDict>>> {
        let metrics = performance_core::get_global_metrics();

        match metrics.get_stats(&operation) {
            Some(stats) => {
                let op_dict = PyDict::new(py);
                op_dict.set_item("count", stats.count)?;
                op_dict.set_item("total_ms", stats.total.as_millis() as u64)?;
                op_dict.set_item("avg_ms", stats.average.as_millis() as u64)?;
                op_dict.set_item("min_ms", stats.min.as_millis() as u64)?;
                op_dict.set_item("max_ms", stats.max.as_millis() as u64)?;
                op_dict.set_item("bytes_processed", stats.bytes_processed)?;

                if let Some(throughput) = stats.throughput() {
                    op_dict.set_item("throughput_bytes_per_sec", throughput)?;
                }

                Ok(Some(op_dict.unbind()))
            }
            None => Ok(None),
        }
    }

    /// Clear all performance metrics.
    pub fn clear_metrics(&self) {
        let metrics = performance_core::get_global_metrics();
        metrics.clear();
    }

    /// Record a custom metric.
    ///
    /// # Arguments
    /// * `operation` - Operation name
    /// * `duration_ms` - Duration in whole milliseconds
    /// * `bytes_processed` - Optional bytes processed
    ///
    /// # Errors
    /// Raises `ValueError` when `duration_ms` is negative, too large to hold
    /// in nanoseconds, or when the timing or byte totals would overflow.
    /// Nothing is recorded in that case.
    #[pyo3(signature = (operation, duration_ms, bytes_processed=None))]
    pub fn record_metric(
        &self,
        operation: String,
        duration_ms: &Bound<'_, PyAny>,
        bytes_processed: Option<u64>,
    ) -> PyResult<()> {
        // Taken as a Python object rather than `u64` so negative and huge ints
        // reach the shared core validation and raise ValueError instead of
        // PyO3's OverflowError. An int beyond i128 is far outside the sample
        // range, so only its sign matters.
        let millis = match duration_ms.extract::<i128>() {
            Ok(millis) => millis,
            Err(_) if duration_ms.is_instance_of::<pyo3::types::PyInt>() => {
                if duration_ms.lt(0)? {
                    i128::MIN
                } else {
                    i128::MAX
                }
            }
            Err(error) => return Err(error),
        };
        let duration =
            performance_core::duration_from_millis_i128(millis).map_err(timing_error_to_py)?;

        performance_core::get_global_metrics()
            .record_timing_with_bytes(&operation, duration, bytes_processed)
            .map_err(timing_error_to_py)
    }
}
