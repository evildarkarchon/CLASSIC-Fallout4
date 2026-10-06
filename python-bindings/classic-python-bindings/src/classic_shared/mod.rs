//! `classic_shared` facade: Python bindings for the domain-neutral utilities in
//! `classic-shared-core` (game identity, string processing, path validation,
//! the rolling performance monitor, and shared-runtime diagnostics).
//!
//! The PyO3 helper library every facade uses lives in [`crate::support`].

use pyo3::prelude::*;
use pyo3::types::PyModule;

use classic_shared_core::get_runtime;

/// Python bindings for the shared `GameId` enum.
pub mod game_id;
pub mod path_py;
pub mod performance_py;
pub mod strings_py;

pub use path_py::PyPathHandler;
pub use performance_py::PyRustPerformanceMonitor;
pub use strings_py::PyStringProcessor;

/// Runtime statistics from Tokio
///
/// Provides visibility into the Tokio runtime state for diagnostics and monitoring.
#[pyclass(skip_from_py_object)]
#[derive(Clone)]
pub struct RuntimeStats {
    /// Number of worker threads in the runtime
    #[pyo3(get)]
    pub worker_threads: usize,

    /// Whether runtime appears healthy
    #[pyo3(get)]
    pub is_healthy: bool,
}

#[pymethods]
impl RuntimeStats {
    fn __repr__(&self) -> String {
        format!(
            "RuntimeStats(worker_threads={}, is_healthy={})",
            self.worker_threads, self.is_healthy
        )
    }
}

/// Get Tokio runtime statistics
///
/// Returns basic diagnostic information about the shared Tokio runtime.
/// Useful for detecting runtime issues in production.
///
/// # Examples
///
/// ```python
/// import classic_shared
///
/// stats = classic_shared.get_runtime_stats()
/// print(f"Worker threads: {stats.worker_threads}")
/// print(f"Healthy: {stats.is_healthy}")
/// ```
#[pyfunction]
pub fn get_runtime_stats() -> RuntimeStats {
    // Get the global runtime
    let runtime = get_runtime();

    // Get metrics from the runtime
    let metrics = runtime.metrics();

    RuntimeStats {
        worker_threads: metrics.num_workers(),
        is_healthy: true, // Simplified check - runtime exists means healthy
    }
}

/// Check if Tokio runtime is healthy
///
/// Returns `True` if the runtime appears to be functioning normally.
/// This is a simplified health check - more sophisticated checks could be added.
///
/// # Examples
///
/// ```python
/// import classic_shared
///
/// if not classic_shared.is_runtime_healthy():
///     print("Warning: Runtime may have issues!")
/// ```
#[pyfunction]
pub fn is_runtime_healthy() -> bool {
    // Simple health check - runtime exists and can provide metrics
    let runtime = get_runtime();
    runtime.metrics().num_workers() > 0
}

/// Registers the `classic_shared` facade exports on its native submodule.
pub(crate) fn register_facade(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add utility classes
    game_id::register(m)?;
    m.add_class::<PyStringProcessor>()?;
    m.add_class::<PyPathHandler>()?;
    m.add_class::<PyRustPerformanceMonitor>()?;

    // Add runtime diagnostics
    m.add_class::<RuntimeStats>()?;
    m.add_function(wrap_pyfunction!(get_runtime_stats, m)?)?;
    m.add_function(wrap_pyfunction!(is_runtime_healthy, m)?)?;

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
