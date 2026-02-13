//! PyO3 bindings for log file processing

use classic_scangame_core::LogProcessor;
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for LogErrorEntry
#[pyclass(name = "LogErrorEntry")]
#[derive(Clone)]
pub struct PyLogErrorEntry {
    /// Path to the log file
    #[pyo3(get)]
    pub file_path: PathBuf,
    /// Error lines found in the log (limited to last 50)
    #[pyo3(get)]
    pub errors: Vec<String>,
    /// Total number of errors found (before truncation)
    #[pyo3(get)]
    pub total_errors: usize,
}

#[pymethods]
impl PyLogErrorEntry {
    fn __repr__(&self) -> String {
        format!(
            "LogErrorEntry(file_path='{}', errors={}, total={})",
            self.file_path.display(),
            self.errors.len(),
            self.total_errors
        )
    }
}

/// Python wrapper for LogProcessor
///
/// Scans directories for log files and detects errors based on configurable patterns.
///
/// Example:
///     >>> processor = LogProcessor(
///     ...     catch_errors=["error", "fatal", "crash"],
///     ...     ignore_files=["debug.log"],
///     ...     ignore_errors=["ignored error"]
///     ... )
///     >>> report = processor.process_logs("/path/to/logs")
///     >>> print(report)
#[pyclass(name = "LogProcessor")]
pub struct PyLogProcessor {
    inner: LogProcessor,
}

#[pymethods]
impl PyLogProcessor {
    #[new]
    #[pyo3(signature = (catch_errors, ignore_files, ignore_errors))]
    fn new(
        catch_errors: Vec<String>,
        ignore_files: Vec<String>,
        ignore_errors: Vec<String>,
    ) -> PyResult<Self> {
        let processor = LogProcessor::new(catch_errors, ignore_files, ignore_errors)
            .map_err(crate::to_pyerr)?;
        Ok(Self { inner: processor })
    }

    /// Process log files in the specified directory and return formatted error report
    ///
    /// Args:
    ///     log_dir: Directory containing log files to scan
    ///
    /// Returns:
    ///     Formatted error report as string
    fn process_logs(&self, log_dir: PathBuf) -> PyResult<String> {
        let report = self.inner.process_logs(&log_dir).map_err(crate::to_pyerr)?;
        Ok(report)
    }

    fn __repr__(&self) -> String {
        "LogProcessor(...)".to_string()
    }
}

/// Convenience function to process logs without creating processor instance
///
/// Args:
///     log_dir: Directory containing log files
///     catch_errors: List of error patterns to catch
///     ignore_files: List of file patterns to ignore
///     ignore_errors: List of error patterns to ignore
///
/// Returns:
///     Formatted error report as string
#[pyfunction]
#[pyo3(signature = (log_dir, catch_errors, ignore_files, ignore_errors))]
pub fn process_logs(
    log_dir: PathBuf,
    catch_errors: Vec<String>,
    ignore_files: Vec<String>,
    ignore_errors: Vec<String>,
) -> PyResult<String> {
    let processor = PyLogProcessor::new(catch_errors, ignore_files, ignore_errors)?;
    processor.process_logs(log_dir)
}

/// Register logs module functions with Python module
pub fn register_logs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyLogProcessor>()?;
    m.add_class::<PyLogErrorEntry>()?;
    m.add_function(wrap_pyfunction!(process_logs, m)?)?;
    Ok(())
}
