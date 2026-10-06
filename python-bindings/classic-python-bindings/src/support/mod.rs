//! Shared PyO3 helpers for every facade of the CLASSIC Python adapter.
//!
//! This module is the former `classic-shared-py` helper library. It holds no
//! business rules; it converts errors, releases the GIL, resolves the Python
//! entry directory, and attaches PyO3 coroutines to the one shared Tokio
//! runtime. The `classic_shared` Python facade lives in [`crate::classic_shared`].
//!
//! # Exception Patterns
//!
//! - [`define_exceptions!`](crate::define_exceptions) - Create the standard 3-tier exception hierarchy
//! - [`register_exceptions!`](crate::register_exceptions) - Register exceptions in a Python module
//! - [`ToPyErr`] - Trait for converting errors to PyErr
//! - [`ResultExt`] - Extension trait for Result error conversion
//!
//! See [`exceptions`] and [`error_convert`] modules for details.

use pyo3::exceptions::{
    PyFileNotFoundError, PyIOError, PyPermissionError, PyRuntimeError, PyTimeoutError, PyValueError,
};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyModule};
use std::future::Future;
use std::path::{Path, PathBuf};

// Module declarations
pub mod error_convert;
pub mod exceptions;
pub mod indexmap_utils;
pub mod path;

// Re-export for Rust usage
pub use indexmap_utils::{
    pyany_to_indexmap_str, pyany_to_indexmap_vecstr, pydict_to_indexmap_str,
    pydict_to_indexmap_str_optional, pydict_to_indexmap_vecstr,
};
pub use path::PathLike;

// Re-export error conversion traits
pub use error_convert::{ResultExt, ToPyErr};

// `#[macro_export]` places the exception macros at the crate root; re-export
// them here so facades import every shared helper from one path.
pub use crate::{define_exceptions, register_exceptions};

// Re-export core types for convenience
pub use classic_shared_core::{ClassicError, ClassicResult, get_runtime};

/// Make Python stdout/stderr tolerate Unicode that legacy encodings cannot render.
///
/// The Python bindings preserve valid UTF-8 returned by Rust. On Windows or other
/// legacy environments, writing those strings to `sys.stdout` can still raise
/// `UnicodeEncodeError` when the stream uses a non-UTF-8 codec with strict error
/// handling. This best-effort import-time guard keeps the Unicode data intact in
/// Python and only changes stream error handling to Python's standard
/// `backslashreplace` fallback when the stream explicitly supports
/// `reconfigure()`.
pub fn configure_python_stdio(py: Python<'_>) {
    let Ok(sys) = PyModule::import(py, "sys") else {
        return;
    };

    for stream_name in ["stdout", "stderr"] {
        if let Ok(stream) = sys.getattr(stream_name) {
            configure_python_text_stream(&stream);
        }
    }
}

fn configure_python_text_stream(stream: &Bound<'_, PyAny>) {
    let Some(errors) = stream
        .getattr("errors")
        .ok()
        .and_then(|value| value.extract::<String>().ok())
    else {
        return;
    };
    if errors != "strict" {
        return;
    }

    let Ok(reconfigure) = stream.getattr("reconfigure") else {
        return;
    };
    let kwargs = PyDict::new(stream.py());
    if kwargs.set_item("errors", "backslashreplace").is_err() {
        return;
    }
    let _ = reconfigure.call((), Some(&kwargs));
}

// Implement ToPyErr for ClassicError so it can be used with map_pyerr()
impl ToPyErr for ClassicError {
    type BaseException = PyRuntimeError;
    type IOException = PyIOError;
    type ParseException = PyValueError;

    fn to_pyerr(self) -> PyErr {
        to_py_err(self)
    }
}

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

/// Helper to run a function without the GIL (PyO3 0.27 compatible)
///
/// This provides a convenient way to release the GIL during CPU-intensive or blocking operations.
///
/// # Examples
///
/// ```rust,ignore
/// use crate::support::without_gil;
/// use pyo3::prelude::*;
///
/// pub fn expensive_operation(py: Python<'_>, data: Vec<u8>) -> PyResult<String> {
///     // Release GIL during long-running computation
///     without_gil(py, || {
///         // This code runs without holding the GIL
///         process_data(data)  // Your custom function here
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
    // PyO3 0.28: detach() takes a closure and releases the GIL while it runs.
    py.detach(f)
}

/// Helper to run async Rust from a synchronous Python API while detached from the GIL.
///
/// Use this only for synchronous Python methods that must block until async Rust
/// work completes. Extract all Python-owned data before calling this helper. For
/// true Python async APIs, return a coroutine with `future_into_py(...)` instead.
#[inline]
pub fn without_gil_block_on<F, Fut, R>(py: Python<'_>, f: F) -> R
where
    F: FnOnce() -> Fut + Send,
    Fut: Future<Output = R>,
    R: Send,
{
    without_gil(py, || get_runtime().block_on(f()))
}

fn parent_dir_from_python_path(candidate: &str) -> Option<PathBuf> {
    let trimmed = candidate.trim();
    if trimmed.is_empty() || trimmed == "-c" || trimmed == "-" || trimmed == "<stdin>" {
        return None;
    }

    let path = PathBuf::from(trimmed);
    let resolved = if path.is_absolute() {
        path
    } else {
        std::env::current_dir().ok()?.join(path)
    };

    resolved.parent().map(Path::to_path_buf)
}

/// Resolve the application directory from Python execution state.
///
/// Prefers the directory of the executed Python file and falls back to the
/// process working directory when Python is running without a real script file
/// (for example `python -c` or an interactive shell).
pub fn resolve_python_entry_dir(py: Python<'_>) -> Option<PathBuf> {
    if let Ok(main) = PyModule::import(py, "__main__")
        && let Ok(file) = main.getattr("__file__")
        && let Ok(path) = file.extract::<String>()
        && let Some(dir) = parent_dir_from_python_path(&path)
    {
        return Some(dir);
    }

    if let Ok(sys) = PyModule::import(py, "sys")
        && let Ok(argv) = sys.getattr("argv")
        && let Ok(argv) = argv.extract::<Vec<String>>()
        && let Some(first) = argv.first()
        && let Some(dir) = parent_dir_from_python_path(first)
    {
        return Some(dir);
    }

    std::env::current_dir().ok()
}

/// Connects PyO3 coroutine scheduling to CLASSIC's process-wide Tokio runtime.
///
/// Called once, before any facade is registered, so every native async entry
/// point (`classic_database`, `classic_file_io`, `classic_settings`,
/// `classic_update`, ...) schedules its futures on
/// `classic_shared_core::get_runtime()` instead of a runtime that
/// `pyo3-async-runtimes` would otherwise build lazily. Import fails if PyO3's
/// scheduling was previously attached to a different runtime, because silently
/// accepting that state would violate the one-runtime contract.
pub fn initialize_async_runtime() -> PyResult<()> {
    let shared_runtime = get_runtime();
    match pyo3_async_runtimes::tokio::init_with_runtime(shared_runtime) {
        Ok(()) => Ok(()),
        Err(()) if shares_classic_runtime() => Ok(()),
        Err(()) => Err(PyRuntimeError::new_err(
            "CLASSIC async scheduling was already attached to a different Tokio runtime",
        )),
    }
}

/// Reports whether PyO3 coroutine scheduling runs on CLASSIC's shared runtime.
///
/// Exposed privately as `_classic_native._native._shares_classic_runtime()` so
/// the Python probes can check runtime identity structurally: successful
/// awaits alone cannot tell two runtimes apart.
#[pyfunction(name = "_shares_classic_runtime")]
pub fn shares_classic_runtime() -> bool {
    std::ptr::eq(pyo3_async_runtimes::tokio::get_runtime(), get_runtime())
}
