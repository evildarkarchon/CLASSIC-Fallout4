//! Python bindings for Papyrus log analysis

use classic_scanlog_core::papyrus::{PapyrusAnalyzer, PapyrusStats};
use pyo3::exceptions::{PyFileNotFoundError, PyIOError, PyRuntimeError};
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for PapyrusStats
#[pyclass(name = "PapyrusStats")]
pub struct PyPapyrusStats {
    inner: PapyrusStats,
}

#[pymethods]
impl PyPapyrusStats {
    /// Create a new empty statistics instance
    #[new]
    fn new() -> Self {
        Self {
            inner: PapyrusStats::new(),
        }
    }

    /// Number of "Dumping Stacks" entries (plural)
    #[getter]
    fn dumps(&self) -> usize {
        self.inner.dumps
    }

    /// Number of "Dumping Stack" entries (singular)
    #[getter]
    fn stacks(&self) -> usize {
        self.inner.stacks
    }

    /// Number of warning messages
    #[getter]
    fn warnings(&self) -> usize {
        self.inner.warnings
    }

    /// Number of error messages
    #[getter]
    fn errors(&self) -> usize {
        self.inner.errors
    }

    /// Total lines processed
    #[getter]
    fn lines_processed(&self) -> usize {
        self.inner.lines_processed
    }

    /// Calculate the dumps to stacks ratio
    ///
    /// Returns 0.0 if there are no dumps or stacks
    fn dumps_to_stacks_ratio(&self) -> f64 {
        self.inner.dumps_to_stacks_ratio()
    }

    /// Get the total number of issues (warnings + errors)
    fn total_issues(&self) -> usize {
        self.inner.total_issues()
    }

    /// Calculate the error to warning ratio
    ///
    /// Returns 0.0 if there are no warnings
    fn error_to_warning_ratio(&self) -> f64 {
        self.inner.error_to_warning_ratio()
    }

    /// Determine the severity level based on error/warning counts
    ///
    /// Returns:
    /// - "OK" if no errors, or errors are less than 25% of warnings
    /// - "Warning" if errors are between 25-100% of warnings
    /// - "Critical" if errors exceed warnings
    fn severity_level(&self) -> &'static str {
        self.inner.severity_level()
    }

    /// String representation of statistics
    fn __repr__(&self) -> String {
        format!(
            "PapyrusStats(dumps={}, stacks={}, warnings={}, errors={}, lines={})",
            self.inner.dumps,
            self.inner.stacks,
            self.inner.warnings,
            self.inner.errors,
            self.inner.lines_processed
        )
    }
}

impl From<PapyrusStats> for PyPapyrusStats {
    fn from(stats: PapyrusStats) -> Self {
        Self { inner: stats }
    }
}

/// Python wrapper for PapyrusAnalyzer
#[pyclass(name = "PapyrusAnalyzer")]
pub struct PyPapyrusAnalyzer {
    inner: PapyrusAnalyzer,
}

#[pymethods]
impl PyPapyrusAnalyzer {
    /// Create a new Papyrus analyzer for the given log file
    ///
    /// Args:
    ///     log_path: Path to the Papyrus.0.log file
    #[new]
    fn new(log_path: PathBuf) -> Self {
        Self {
            inner: PapyrusAnalyzer::new(log_path),
        }
    }

    /// Check if the log file exists
    fn log_exists(&self) -> bool {
        self.inner.log_exists()
    }

    /// Get the log file path
    fn log_path(&self) -> PathBuf {
        self.inner.log_path().to_path_buf()
    }

    /// Get current statistics
    fn stats(&self) -> PyPapyrusStats {
        PyPapyrusStats {
            inner: self.inner.stats().clone(),
        }
    }

    /// Reset statistics and position (start monitoring from beginning)
    fn reset(&mut self) {
        self.inner.reset();
    }

    /// Perform a full analysis of the log file from the beginning
    ///
    /// This reads the entire file and calculates statistics.
    ///
    /// Returns:
    ///     PapyrusStats: The collected statistics
    ///
    /// Raises:
    ///     FileNotFoundError: If log file doesn't exist
    ///     IOError: If failed to read the file
    fn analyze_full(&mut self) -> PyResult<PyPapyrusStats> {
        self.inner
            .analyze_full()
            .map(PyPapyrusStats::from)
            .map_err(|e| match e {
                classic_scanlog_core::papyrus::PapyrusError::LogNotFound(path) => {
                    PyFileNotFoundError::new_err(format!("Log file not found: {}", path.display()))
                }
                classic_scanlog_core::papyrus::PapyrusError::IoError(io_err) => {
                    PyIOError::new_err(io_err.to_string())
                }
                classic_scanlog_core::papyrus::PapyrusError::EncodingError => {
                    PyRuntimeError::new_err("Failed to detect file encoding")
                }
            })
    }

    /// Analyze the log file and return formatted summary text
    ///
    /// Returns:
    ///     str: Formatted string with statistics, or error message if log not found
    fn analyze_to_string(&mut self) -> String {
        self.inner.analyze_to_string()
    }

    /// Start monitoring from the END of the file (ignore prior history)
    ///
    /// This positions the analyzer at the end of the current file so that
    /// only NEW lines added after this point will be tracked.
    /// This implements true "tail -f" behavior for monitoring sessions.
    ///
    /// Raises:
    ///     FileNotFoundError: If file doesn't exist
    ///     IOError: If can't read file metadata
    fn start_monitoring(&mut self) -> PyResult<()> {
        self.inner.start_monitoring().map_err(|e| match e {
            classic_scanlog_core::papyrus::PapyrusError::LogNotFound(path) => {
                PyFileNotFoundError::new_err(format!("Log file not found: {}", path.display()))
            }
            classic_scanlog_core::papyrus::PapyrusError::IoError(io_err) => {
                PyIOError::new_err(io_err.to_string())
            }
            classic_scanlog_core::papyrus::PapyrusError::EncodingError => {
                PyRuntimeError::new_err("Failed to detect file encoding")
            }
        })
    }

    /// Read and process only new lines added since last check (tail -f behavior)
    ///
    /// This implements incremental monitoring by only reading new content
    /// that has been appended to the file since the last read.
    ///
    /// Returns:
    ///     Optional[tuple[list[str], PapyrusStats]]: Tuple of (new lines, updated statistics),
    ///     or None if no changes
    ///
    /// Raises:
    ///     IOError: If failed to read the file or file was truncated
    fn check_for_updates(&mut self) -> PyResult<Option<(Vec<String>, PyPapyrusStats)>> {
        self.inner
            .check_for_updates()
            .map(|opt| opt.map(|(lines, stats)| (lines, PyPapyrusStats::from(stats))))
            .map_err(|e| match e {
                classic_scanlog_core::papyrus::PapyrusError::LogNotFound(path) => {
                    PyFileNotFoundError::new_err(format!("Log file not found: {}", path.display()))
                }
                classic_scanlog_core::papyrus::PapyrusError::IoError(io_err) => {
                    PyIOError::new_err(io_err.to_string())
                }
                classic_scanlog_core::papyrus::PapyrusError::EncodingError => {
                    PyRuntimeError::new_err("Failed to detect file encoding")
                }
            })
    }

    /// String representation
    fn __repr__(&self) -> String {
        format!(
            "PapyrusAnalyzer(log_path='{}')",
            self.inner.log_path().display()
        )
    }
}

/// Convenience function to analyze a Papyrus log file
///
/// This is equivalent to the original Python `papyrus_logging()` function.
///
/// Args:
///     log_path: Path to the Papyrus.0.log file
///
/// Returns:
///     tuple[str, int]: A tuple containing a formatted string with log analysis
///     details and the total count of dumps extracted from the log.
///
/// Example:
///     >>> from classic_scanlog import papyrus_logging
///     >>> summary, dumps_count = papyrus_logging("/path/to/Papyrus.0.log")
///     >>> print(summary)
///     >>> print(f"Total dumps: {dumps_count}")
#[pyfunction]
pub fn papyrus_logging(log_path: PathBuf) -> (String, usize) {
    let mut analyzer = PapyrusAnalyzer::new(log_path);
    let summary = analyzer.analyze_to_string();

    // Get dumps count from stats
    let dumps_count = analyzer.stats().dumps;

    (summary, dumps_count)
}

/// Register Papyrus types with the Python module
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPapyrusStats>()?;
    m.add_class::<PyPapyrusAnalyzer>()?;
    m.add_function(wrap_pyfunction!(papyrus_logging, m)?)?;
    Ok(())
}
