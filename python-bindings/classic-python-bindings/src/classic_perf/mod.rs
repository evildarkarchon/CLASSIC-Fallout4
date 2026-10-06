//! Python bindings for performance monitoring.
//!
//! This crate provides Python bindings for the seconds view of
//! `classic_shared_core::performance_core`, allowing Python code to use
//! high-precision timing and metrics collection. The
//! metrics live in this extension's shared-core default store; invalid
//! samples raise `ValueError` and leave that store unchanged.
//!
//! The Rust bindings provide the core metrics storage and statistics
//! calculation, while Python decorators and context managers are
//! implemented in the Python wrapper layer.

use classic_shared_core::performance_core;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::HashMap;

/// Convert a rejected timing record into `ValueError("<code>: <message>")`.
fn timing_error_to_py(error: performance_core::TimingError) -> PyErr {
    PyValueError::new_err(error.coded_message())
}

/// Summary statistics for a performance metric.
///
/// This class contains aggregated statistics for a single metric,
/// including count, total time, average, minimum, and maximum.
///
/// Attributes:
///     count: Number of samples recorded
///     total: Total time in seconds
///     average: Average time per sample in seconds
///     min: Minimum time in seconds
///     max: Maximum time in seconds
#[pyclass(from_py_object)]
#[derive(Clone, Debug)]
pub struct MetricsSummary {
    /// Number of samples recorded
    #[pyo3(get)]
    pub count: usize,
    /// Total time in seconds
    #[pyo3(get)]
    pub total: f64,
    /// Average time per sample in seconds
    #[pyo3(get)]
    pub average: f64,
    /// Minimum time in seconds
    #[pyo3(get)]
    pub min: f64,
    /// Maximum time in seconds
    #[pyo3(get)]
    pub max: f64,
}

#[pymethods]
impl MetricsSummary {
    fn __repr__(&self) -> String {
        format!(
            "MetricsSummary(count={}, total={:.3}s, average={:.3}s, min={:.3}s, max={:.3}s)",
            self.count, self.total, self.average, self.min, self.max
        )
    }
}

impl From<&performance_core::MetricsSummary> for MetricsSummary {
    fn from(rust_summary: &performance_core::MetricsSummary) -> Self {
        Self {
            count: rust_summary.count,
            total: rust_summary.total,
            average: rust_summary.average,
            min: rust_summary.min,
            max: rust_summary.max,
        }
    }
}

/// Record a timing measurement.
///
/// This function stores a single timing sample for the given operation name.
/// Multiple samples can be recorded for the same operation, and statistics
/// will be computed across all samples.
///
/// The duration must be finite and nonnegative (``-0.0`` counts as zero) and
/// is rounded once to the nearest nanosecond.
///
/// Args:
///     name: The operation name
///     duration_secs: The duration in seconds
///
/// Raises:
///     ValueError: If the duration is negative, NaN, infinite, too large, or
///         would overflow the operation's accumulated total. The message
///         starts with a stable token such as ``timing_sample_negative``.
///         No metric changes when it is raised.
///
/// Example:
///     >>> from classic_core import perf
///     >>> perf.record_timing("my_operation", 0.123)
#[pyfunction]
fn record_timing(name: String, duration_secs: f64) -> PyResult<()> {
    performance_core::record_timing(&name, duration_secs).map_err(timing_error_to_py)
}

/// Get summary statistics for all recorded metrics.
///
/// Returns a dictionary mapping operation names to MetricsSummary objects
/// containing count, total, average, min, and max statistics.
///
/// Returns:
///     Dict[str, MetricsSummary]: Statistics for each operation
///
/// Example:
///     >>> from classic_core import perf
///     >>> perf.record_timing("op1", 0.1)
///     >>> perf.record_timing("op1", 0.2)
///     >>> summary = perf.get_summary()
///     >>> summary["op1"].average
///     0.15
#[pyfunction]
fn get_summary() -> HashMap<String, MetricsSummary> {
    performance_core::get_summary()
        .iter()
        .map(|(k, v)| (k.clone(), MetricsSummary::from(v)))
        .collect()
}

/// Clear all recorded metrics.
///
/// This removes all timing data from the metrics storage. Useful for
/// resetting between test runs or measurement sessions.
///
/// Example:
///     >>> import classic_perf
///     >>> classic_perf.record_timing("op1", 0.1)
///     >>> classic_perf.clear_metrics()
///     >>> classic_perf.get_summary()
///     {}
#[pyfunction]
fn clear_metrics() {
    performance_core::clear_metrics();
}

/// Alias for clear_metrics() for API compatibility.
///
/// This is an alias for `clear_metrics()` to match the Python API.
///
/// Example:
///     >>> import classic_perf
///     >>> classic_perf.record_timing("op1", 0.1)
///     >>> classic_perf.reset_metrics()
///     >>> classic_perf.get_summary()
///     {}
#[pyfunction]
fn reset_metrics() {
    performance_core::clear_metrics();
}

/// RAII timer that automatically records timing on drop.
///
/// This timer starts when created and automatically records its elapsed
/// time when it goes out of scope or when `finish()` is called.
///
/// This is primarily for use in Rust code. Python code should use the
/// higher-level decorators and context managers instead.
///
/// Example:
///     >>> from classic_core import perf
///     >>> timer = perf.Timer("my_operation")
///     >>> # ... do work ...
///     >>> timer.finish()
#[pyclass]
pub struct Timer {
    inner: Option<performance_core::Timer>,
}

#[pymethods]
impl Timer {
    /// Create a new timer with the given operation name.
    ///
    /// Args:
    ///     name: Operation name for metrics tracking
    #[new]
    fn new(name: String) -> Self {
        Self {
            inner: Some(performance_core::Timer::start(name)),
        }
    }

    /// Finish timing and record the measurement.
    ///
    /// This consumes the timer and records the elapsed time.
    /// If the timer is dropped without calling `finish()`, it will
    /// automatically record on drop. A timer records at most once; later
    /// `finish()` calls do nothing.
    ///
    /// Raises:
    ///     ValueError: If recording would overflow the operation's
    ///         accumulated total. The timer is still spent.
    fn finish(&mut self) -> PyResult<()> {
        match self.inner.take() {
            Some(timer) => timer.finish().map_err(timing_error_to_py),
            None => Ok(()),
        }
    }

    /// Get the current elapsed time without finishing the timer.
    ///
    /// Returns:
    ///     float: Elapsed time in seconds
    fn elapsed(&self) -> f64 {
        self.inner
            .as_ref()
            .map(|t| t.elapsed().as_secs_f64())
            .unwrap_or(0.0)
    }

    fn __repr__(&self) -> String {
        format!("Timer(elapsed={:.3}s)", self.elapsed())
    }
}

/// Start a new timer.
///
/// Convenience function that creates and starts a Timer.
///
/// Args:
///     name: Operation name for metrics tracking
///
/// Returns:
///     Timer: A running timer instance
///
/// Example:
///     >>> from classic_core import perf
///     >>> timer = perf.start_timer("my_operation")
///     >>> # ... do work ...
///     >>> timer.finish()
#[pyfunction]
fn start_timer(name: String) -> Timer {
    Timer::new(name)
}

/// Python module for performance monitoring.
///
/// This module provides high-precision timing, metrics collection, and
/// performance analysis tools. The core functionality is implemented in
/// Rust for maximum performance.
///
/// Core Functions:
///     record_timing(name, duration_secs): Record a timing measurement
///     get_summary(): Get statistics for all metrics
///     clear_metrics(): Clear all recorded metrics
///     start_timer(name): Create a new RAII timer
///
/// Classes:
///     Timer: RAII timer for automatic timing
///     MetricsSummary: Statistics summary for a metric
///
/// Example:
///     >>> import classic_perf
///     >>> classic_perf.record_timing("my_operation", 0.123)
///     >>> summary = classic_perf.get_summary()
///     >>> summary["my_operation"].average
///     0.123
pub(crate) fn register_facade(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add core functions
    m.add_function(wrap_pyfunction!(record_timing, m)?)?;
    m.add_function(wrap_pyfunction!(get_summary, m)?)?;
    m.add_function(wrap_pyfunction!(clear_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(reset_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(start_timer, m)?)?;

    // Add classes
    m.add_class::<Timer>()?;
    m.add_class::<MetricsSummary>()?;

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
