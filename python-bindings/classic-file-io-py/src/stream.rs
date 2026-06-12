use pyo3::prelude::*;
use std::sync::Arc;
use tokio::fs::File;
use tokio::io::{BufReader, Lines};
use tokio::sync::Mutex;

/// Python iterator for streaming lines from a file asynchronously.
///
/// This struct wraps a Tokio `Lines` stream and exposes it as an async iterator
/// in Python. This allows for memory-efficient line-by-line processing of large files.
#[pyclass]
pub struct PyLineStreamer {
    inner: Arc<Mutex<Lines<BufReader<File>>>>,
}

impl PyLineStreamer {
    /// Create a new PyLineStreamer from a Tokio Lines stream.
    pub fn new(lines: Lines<BufReader<File>>) -> Self {
        Self {
            inner: Arc::new(Mutex::new(lines)),
        }
    }
}

#[pymethods]
impl PyLineStreamer {
    fn __aiter__(slf: Py<Self>) -> Py<Self> {
        slf
    }

    fn __anext__<'py>(slf: Py<Self>, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let inner = slf.borrow(py).inner.clone();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let mut lines_guard = inner.lock().await;
            match lines_guard.next_line().await {
                Ok(Some(line)) => Ok(line),
                Ok(None) => Err(pyo3::exceptions::PyStopAsyncIteration::new_err("")),
                Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
            }
        })
    }
}

/// Python iterator for streaming lines from a file synchronously.
///
/// This struct wraps a `std::io::Lines` stream and exposes it as a standard iterator
/// in Python. This allows for memory-efficient line-by-line processing of large files
/// in synchronous code (like PapyrusLog.py).
#[pyclass]
pub struct PySyncLineStreamer {
    // We wrap in Arc<Mutex> because PyO3 requires thread safety for the iterator,
    // even though Python iterators are usually single-threaded.
    inner: std::sync::Arc<std::sync::Mutex<std::io::Lines<std::io::BufReader<std::fs::File>>>>,
}

impl PySyncLineStreamer {
    /// Create a new PySyncLineStreamer from a std::io Lines stream.
    pub fn new(lines: std::io::Lines<std::io::BufReader<std::fs::File>>) -> Self {
        Self {
            inner: std::sync::Arc::new(std::sync::Mutex::new(lines)),
        }
    }
}

#[pymethods]
impl PySyncLineStreamer {
    fn __iter__(slf: Py<Self>) -> Py<Self> {
        slf
    }

    fn __next__(&mut self) -> PyResult<Option<String>> {
        let mut lines = self.inner.lock().map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Mutex poisoned: {}", e))
        })?;

        match lines.next() {
            Some(Ok(line)) => Ok(Some(line)),
            Some(Err(e)) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
            None => Ok(None),
        }
    }
}
