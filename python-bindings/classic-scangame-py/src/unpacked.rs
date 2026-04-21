//! PyO3 bindings for unpacked file scanning

use classic_scangame_core::UnpackedScanner;
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for UnpackedIssues
#[pyclass(name = "UnpackedIssues", from_py_object)]
#[derive(Clone)]
pub struct PyUnpackedIssues {
    /// Animation data directories detected
    #[pyo3(get)]
    pub animdata: Vec<String>,
    /// Texture format issues (TGA/PNG instead of DDS)
    #[pyo3(get)]
    pub tex_frmt: Vec<String>,
    /// Sound format issues (MP3/M4A instead of XWM)
    #[pyo3(get)]
    pub snd_frmt: Vec<String>,
    /// XSE script files detected
    #[pyo3(get)]
    pub xse_file: Vec<String>,
    /// Previs/Precombine files detected
    #[pyo3(get)]
    pub previs: Vec<String>,
    /// DDS files found (for batch dimension checking)
    #[pyo3(get)]
    pub dds_files: Vec<PathBuf>,
}

#[pymethods]
impl PyUnpackedIssues {
    fn __repr__(&self) -> String {
        format!(
            "UnpackedIssues(animdata={}, tex_frmt={}, snd_frmt={}, xse_file={}, previs={}, dds_files={})",
            self.animdata.len(),
            self.tex_frmt.len(),
            self.snd_frmt.len(),
            self.xse_file.len(),
            self.previs.len(),
            self.dds_files.len()
        )
    }

    /// Check if any issues were found
    fn has_issues(&self) -> bool {
        !self.animdata.is_empty()
            || !self.tex_frmt.is_empty()
            || !self.snd_frmt.is_empty()
            || !self.xse_file.is_empty()
            || !self.previs.is_empty()
    }

    /// Get total count of all issues
    fn total_count(&self) -> usize {
        self.animdata.len()
            + self.tex_frmt.len()
            + self.snd_frmt.len()
            + self.xse_file.len()
            + self.previs.len()
    }
}

/// Python wrapper for UnpackedScanner
///
/// Scans directories for unpacked files that should be in BA2 archives.
///
/// Example:
///     >>> scanner = UnpackedScanner()
///     >>> issues = scanner.scan_directory("/path/to/game/Data")
///     >>> if issues.has_issues():
///     ...     print(f"Found {issues.total_count()} issues")
///     ...     for file in issues.meshes_should_be_in_ba2:
///     ...         print(f"  Mesh: {file}")
#[pyclass(name = "UnpackedScanner")]
pub struct PyUnpackedScanner {
    inner: UnpackedScanner,
}

#[pymethods]
impl PyUnpackedScanner {
    #[new]
    fn new() -> Self {
        Self {
            inner: UnpackedScanner::new(),
        }
    }

    /// Scan a directory for unpacked file issues
    ///
    /// Args:
    ///     root_path: Root directory to scan (typically game Data folder)
    ///     xse_scriptfiles: List of XSE script filenames to detect (e.g., ["f4se.dll"])
    ///
    /// Returns:
    ///     UnpackedIssues object containing lists of problematic files
    fn scan_directory(
        &self,
        root_path: PathBuf,
        xse_scriptfiles: Vec<String>,
    ) -> PyResult<PyUnpackedIssues> {
        let issues = self
            .inner
            .scan_directory(&root_path, &xse_scriptfiles)
            .map_err(crate::to_pyerr)?;

        Ok(PyUnpackedIssues {
            animdata: issues.animdata.into_iter().collect(),
            tex_frmt: issues.tex_frmt.into_iter().collect(),
            snd_frmt: issues.snd_frmt.into_iter().collect(),
            xse_file: issues.xse_file.into_iter().collect(),
            previs: issues.previs.into_iter().collect(),
            dds_files: issues.dds_files,
        })
    }

    fn __repr__(&self) -> String {
        "UnpackedScanner()".to_string()
    }
}

/// Convenience function to scan for unpacked files without creating scanner instance
///
/// Args:
///     root_path: Root directory to scan
///     xse_scriptfiles: List of XSE script filenames to detect
///
/// Returns:
///     UnpackedIssues object
#[pyfunction]
#[pyo3(signature = (root_path, xse_scriptfiles))]
pub fn scan_unpacked_files(
    root_path: PathBuf,
    xse_scriptfiles: Vec<String>,
) -> PyResult<PyUnpackedIssues> {
    let scanner = PyUnpackedScanner::new();
    scanner.scan_directory(root_path, xse_scriptfiles)
}

/// Register unpacked module functions with Python module
pub fn register_unpacked(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyUnpackedScanner>()?;
    m.add_class::<PyUnpackedIssues>()?;
    m.add_function(wrap_pyfunction!(scan_unpacked_files, m)?)?;
    Ok(())
}
