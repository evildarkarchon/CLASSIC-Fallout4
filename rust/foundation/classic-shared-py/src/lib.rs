//! CLASSIC Shared Python Bindings - PyO3 wrappers for classic-shared-core
//!
//! This crate provides Python bindings for the pure Rust utilities in `classic-shared-core`.
//!
//! # Architecture
//!
//! This is the **-py** layer containing PyO3 bindings for Python integration.
//! Pure Rust business logic is in `classic-shared-core`.

use pyo3::exceptions::{
    PyFileNotFoundError, PyIOError, PyPermissionError, PyRuntimeError, PyTimeoutError, PyValueError,
};
use pyo3::prelude::*;

// Module declarations
pub mod path;
pub mod path_py;
pub mod performance_py;
pub mod strings_py;

// Re-export for Rust usage
pub use path::PathLike;
pub use path_py::PyPathHandler;
pub use performance_py::PyRustPerformanceMonitor;
pub use strings_py::PyStringProcessor;

// Re-export core types for convenience
pub use classic_shared_core::{ClassicError, ClassicResult, get_runtime};

/// Convert ClassicError to PyErr
///
/// Helper function to convert Rust errors to Python exceptions.
/// This cannot be implemented as `From` due to orphan rules.
pub fn to_py_err(err: ClassicError) -> PyErr {
    match err {
        ClassicError::Io { message, .. } => PyIOError::new_err(message),
        ClassicError::Path { message, path } => {
            let msg = match path {
                Some(p) => format!("{}: {}", message, p),
                None => message,
            };
            PyIOError::new_err(msg)
        }
        ClassicError::Validation { message, field } => {
            let msg = match field {
                Some(f) => format!("{}: field '{}'", message, f),
                None => message,
            };
            PyValueError::new_err(msg)
        }
        ClassicError::Parse {
            message,
            position,
            context,
        } => {
            let msg = match (position, context) {
                (Some(pos), Some(ctx)) => format!("{} at position {} in: {}", message, pos, ctx),
                (Some(pos), None) => format!("{} at position {}", message, pos),
                (None, Some(ctx)) => format!("{} in: {}", message, ctx),
                (None, None) => message,
            };
            PyValueError::new_err(msg)
        }
        ClassicError::Database { message, query } => {
            let msg = match query {
                Some(q) => format!("{} | Query: {}", message, q),
                None => message,
            };
            PyRuntimeError::new_err(msg)
        }
        ClassicError::Cache { message } => PyRuntimeError::new_err(message),
        ClassicError::Encoding { message, encoding } => {
            let msg = match encoding {
                Some(e) => format!("{}: {}", message, e),
                None => message,
            };
            PyValueError::new_err(msg)
        }
        ClassicError::Timeout {
            operation,
            duration_ms,
        } => PyTimeoutError::new_err(format!(
            "Operation '{}' timed out after {}ms",
            operation, duration_ms
        )),
        ClassicError::Permission { message, resource } => {
            let msg = match resource {
                Some(r) => format!("{}: {}", message, r),
                None => message,
            };
            PyPermissionError::new_err(msg)
        }
        ClassicError::Configuration { message, key } => {
            let msg = match key {
                Some(k) => format!("{}: key '{}'", message, k),
                None => message,
            };
            PyValueError::new_err(msg)
        }
        ClassicError::Processing { message, stage } => {
            let msg = match stage {
                Some(s) => format!("{} in stage: {}", message, s),
                None => message,
            };
            PyRuntimeError::new_err(msg)
        }
        ClassicError::NotFound { resource } => {
            PyFileNotFoundError::new_err(format!("Resource not found: {}", resource))
        }
        ClassicError::InvalidState {
            message,
            expected,
            actual,
        } => {
            let msg = match (expected, actual) {
                (Some(exp), Some(act)) => {
                    format!("{} | Expected: {}, Actual: {}", message, exp, act)
                }
                _ => message,
            };
            PyRuntimeError::new_err(msg)
        }
        ClassicError::Generic { message, details } => {
            let msg = match details {
                Some(d) => format!("{} | Details: {}", message, d),
                None => message,
            };
            PyRuntimeError::new_err(msg)
        }
    }
}

/// Helper to run a function without the GIL (PyO3 0.26 compatible)
///
/// This provides a convenient way to release the GIL during CPU-intensive or blocking operations.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_shared_py::without_gil;
/// use pyo3::prelude::*;
///
/// pub fn expensive_operation(py: Python<'_>, data: Vec<u8>) -> PyResult<String> {
///     // Release GIL during long-running computation
///     without_gil(py, || {
///         // This code runs without holding the GIL
///         process_data(data)
///     })
/// }
/// ```
///
/// # When to use
///
/// - I/O operations (file reading, network, database queries)
/// - CPU-intensive calculations
/// - Blocking operations that don't need Python access
/// - Any operation that takes > 1ms
///
/// # When NOT to use
///
/// - Operations that need to call Python code
/// - Very fast operations (< 1ms) where overhead isn't worth it
/// - When you need to access Python objects during execution
#[inline]
pub fn without_gil<F, R>(py: Python<'_>, f: F) -> R
where
    F: FnOnce() -> R + Send,
    R: Send,
{
    // PyO3 0.26: detach() takes a closure
    py.detach(f)
}

/// Runtime statistics from Tokio
///
/// Provides visibility into the Tokio runtime state for diagnostics and monitoring.
#[pyclass]
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
fn get_runtime_stats() -> RuntimeStats {
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
fn is_runtime_healthy() -> bool {
    // Simple health check - runtime exists and can provide metrics
    let runtime = get_runtime();
    runtime.metrics().num_workers() > 0
}

/// Python module initialization
#[pymodule]
fn classic_shared(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add utility classes
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
