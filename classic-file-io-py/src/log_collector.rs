//! Python bindings for LogCollector (thin PyO3 adapter)
//!
//! This module provides THIN adapters that delegate all business logic to classic-file-io-core.
//! It ONLY handles Python ↔ Rust type conversions and async runtime bridging.

use classic_file_io_core::LogCollector;
use classic_shared::get_runtime;
use pyo3::exceptions::PyIOError;
use pyo3::prelude::*;
use std::path::PathBuf;

/// Convert FileIOError to PyErr
fn to_pyerr(err: classic_file_io_core::FileIOError) -> PyErr {
    PyIOError::new_err(err.to_string())
}

/// Python wrapper for LogCollector - THIN ADAPTER ONLY
///
/// Organizes crash logs from multiple locations:
/// - Copies logs from XSE folder (My Games) to Crash Logs
/// - Moves logs from working directory to Crash Logs
/// - Collects logs from custom scan directories
///
/// # Example
///
/// ```python
/// from classic_core import file_io
/// import asyncio
///
/// async def main():
///     # Create log collector
///     collector = file_io.PyLogCollector.new(
///         base_folder=".",
///         xse_folder=r"C:\Users\Username\Documents\My Games\Fallout4\F4SE",
///         custom_folder=None
///     )
///
///     # Collect all crash logs
///     log_paths = await collector.collect_all()
///     print(f"Found {len(log_paths)} crash logs")
///
///     # Get organized directory
///     crash_logs_dir = collector.crash_logs_dir()
///     print(f"Logs organized in: {crash_logs_dir}")
///
/// asyncio.run(main())
/// ```
#[pyclass(name = "PyLogCollector")]
pub struct PyLogCollector {
    inner: LogCollector,
}

#[pymethods]
impl PyLogCollector {
    /// Create a new LogCollector
    ///
    /// Args:
    ///     base_folder: Working directory where Crash Logs folder will be created
    ///     xse_folder: Optional path to game's XSE folder (e.g., My Games/Fallout4/F4SE)
    ///     custom_folder: Optional path to custom scan directory
    ///
    /// Returns:
    ///     New PyLogCollector instance
    #[new]
    #[pyo3(signature = (base_folder, xse_folder=None, custom_folder=None))]
    pub fn new(
        base_folder: String,
        xse_folder: Option<String>,
        custom_folder: Option<String>,
    ) -> Self {
        let base = PathBuf::from(base_folder);
        let xse = xse_folder.map(PathBuf::from);
        let custom = custom_folder.map(PathBuf::from);

        Self {
            inner: LogCollector::new(base, xse, custom),
        }
    }

    /// Execute full log collection workflow
    ///
    /// This performs all log collection steps in order:
    /// 1. Ensure directory structure exists
    /// 2. Move logs from base folder to Crash Logs
    /// 3. Copy logs from XSE folder to Crash Logs
    /// 4. Collect all crash log paths for processing
    ///
    /// Returns:
    ///     List of paths to all crash log files ready for processing
    #[pyo3(name = "collect_all")]
    pub fn py_collect_all(&self, _py: Python<'_>) -> PyResult<Vec<String>> {
        get_runtime().block_on(async {
            let paths = self.inner.collect_all().await.map_err(to_pyerr)?;
            Ok(paths
                .into_iter()
                .map(|p| p.to_string_lossy().to_string())
                .collect())
        })
    }

    /// Move crash logs and AUTOSCAN reports from base folder to Crash Logs directory
    ///
    /// Returns:
    ///     Number of files moved
    #[pyo3(name = "move_from_base_folder")]
    pub fn py_move_from_base_folder(&self, _py: Python<'_>) -> PyResult<usize> {
        get_runtime().block_on(async { self.inner.move_from_base_folder().await.map_err(to_pyerr) })
    }

    /// Copy crash logs from game's XSE folder (My Games directory) to Crash Logs
    ///
    /// This is where the game stores crash logs. We copy (not move) them to preserve
    /// the originals in case the user wants to reference them.
    ///
    /// Returns:
    ///     Number of files copied
    #[pyo3(name = "copy_from_xse_folder")]
    pub fn py_copy_from_xse_folder(&self, _py: Python<'_>) -> PyResult<usize> {
        get_runtime().block_on(async { self.inner.copy_from_xse_folder().await.map_err(to_pyerr) })
    }

    /// Collect all crash log file paths for processing
    ///
    /// This searches for crash-*.log files in:
    /// - Crash Logs directory (after moving/copying operations)
    /// - Custom scan folder (if configured)
    ///
    /// Returns:
    ///     List of paths to all crash log files found
    #[pyo3(name = "collect_crash_logs")]
    pub fn py_collect_crash_logs(&self, _py: Python<'_>) -> PyResult<Vec<String>> {
        get_runtime().block_on(async {
            let paths = self.inner.collect_crash_logs().await.map_err(to_pyerr)?;
            Ok(paths
                .into_iter()
                .map(|p| p.to_string_lossy().to_string())
                .collect())
        })
    }

    /// Get the path to the Crash Logs directory
    ///
    /// Returns:
    ///     Path to Crash Logs directory as a string
    #[pyo3(name = "crash_logs_dir")]
    pub fn py_crash_logs_dir(&self, _py: Python<'_>) -> String {
        self.inner.crash_logs_dir().to_string_lossy().to_string()
    }

    /// Get the path to the Pastebin subdirectory
    ///
    /// Returns:
    ///     Path to Pastebin directory as a string
    #[pyo3(name = "pastebin_dir")]
    pub fn py_pastebin_dir(&self, _py: Python<'_>) -> String {
        self.inner.pastebin_dir().to_string_lossy().to_string()
    }

    /// String representation for debugging
    fn __repr__(&self) -> String {
        format!(
            "PyLogCollector(crash_logs_dir={:?})",
            self.inner.crash_logs_dir()
        )
    }
}
