//! PyO3 bindings for BA2 archive handling

use classic_scangame_core::BA2Scanner;
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for BA2Issues
#[pyclass(name = "BA2Issues")]
#[derive(Clone)]
pub struct PyBA2Issues {
    /// Texture dimension issues (odd-numbered dimensions)
    #[pyo3(get)]
    pub tex_dims: Vec<String>,
    /// Texture format issues (non-DDS textures)
    #[pyo3(get)]
    pub tex_frmt: Vec<String>,
    /// Sound format issues (MP3/M4A instead of XWM)
    #[pyo3(get)]
    pub snd_frmt: Vec<String>,
    /// XSE script files detected
    #[pyo3(get)]
    pub xse_file: Vec<String>,
}

#[pymethods]
impl PyBA2Issues {
    fn __repr__(&self) -> String {
        format!(
            "BA2Issues(tex_dims={}, tex_frmt={}, snd_frmt={}, xse_file={})",
            self.tex_dims.len(),
            self.tex_frmt.len(),
            self.snd_frmt.len(),
            self.xse_file.len()
        )
    }

    /// Check if any issues were found
    fn has_issues(&self) -> bool {
        !self.tex_dims.is_empty()
            || !self.tex_frmt.is_empty()
            || !self.snd_frmt.is_empty()
            || !self.xse_file.is_empty()
    }

    /// Get total count of all issues
    fn total_count(&self) -> usize {
        self.tex_dims.len() + self.tex_frmt.len() + self.snd_frmt.len() + self.xse_file.len()
    }
}

/// Python wrapper for BA2Scanner
///
/// Scans BA2 archive files for issues and validates their contents.
///
/// Example:
///     >>> scanner = BA2Scanner()
///     >>> ba2_files = scanner.find_ba2_files("/path/to/game/Data")
///     >>> for ba2_file in ba2_files:
///     ...     issues = scanner.scan_archive(ba2_file)
///     ...     if issues.has_issues():
///     ...         print(f"Issues in {ba2_file}")
#[pyclass(name = "BA2Scanner")]
pub struct PyBA2Scanner {
    inner: BA2Scanner,
}

#[pymethods]
impl PyBA2Scanner {
    #[new]
    fn new() -> Self {
        Self {
            inner: BA2Scanner::new(),
        }
    }

    /// Find all BA2 archive files in a directory
    ///
    /// Args:
    ///     root_path: Root directory to search (typically game Data folder)
    ///
    /// Returns:
    ///     List of BA2 archive file paths
    fn find_ba2_files(&self, root_path: PathBuf) -> Vec<PathBuf> {
        self.inner.find_ba2_files(&root_path)
    }

    /// Scan a single BA2 archive for issues
    ///
    /// Args:
    ///     archive_path: Path to BA2 archive file
    ///
    /// Returns:
    ///     BA2Issues object containing lists of problematic entries
    fn scan_archive(&self, archive_path: PathBuf) -> PyResult<PyBA2Issues> {
        let issues = self
            .inner
            .scan_archive(&archive_path)
            .map_err(crate::to_pyerr)?;

        Ok(PyBA2Issues {
            tex_dims: issues.tex_dims,
            tex_frmt: issues.tex_frmt,
            snd_frmt: issues.snd_frmt,
            xse_file: issues.xse_file,
        })
    }

    /// Scan multiple BA2 archives in batch
    ///
    /// Args:
    ///     archive_paths: List of BA2 archive paths
    ///
    /// Returns:
    ///     List of tuples (archive_path, BA2Issues) for successful scans
    fn scan_archives_batch(
        &self,
        archive_paths: Vec<PathBuf>,
    ) -> PyResult<Vec<(PathBuf, PyBA2Issues)>> {
        let results = self.inner.scan_archives_batch(&archive_paths);

        let mut output = Vec::new();
        for (path, result) in archive_paths.into_iter().zip(results) {
            match result {
                Ok(issues) => {
                    output.push((
                        path,
                        PyBA2Issues {
                            tex_dims: issues.tex_dims,
                            tex_frmt: issues.tex_frmt,
                            snd_frmt: issues.snd_frmt,
                            xse_file: issues.xse_file,
                        },
                    ));
                }
                Err(e) => return Err(crate::to_pyerr(e)),
            }
        }

        Ok(output)
    }

    fn __repr__(&self) -> String {
        "BA2Scanner()".to_string()
    }
}

/// Convenience function to find and scan all BA2 archives in a directory
///
/// Args:
///     root_path: Root directory to search
///
/// Returns:
///     List of tuples (archive_path, BA2Issues) for all BA2 files found
#[pyfunction]
#[pyo3(signature = (root_path))]
pub fn scan_all_ba2_archives(root_path: PathBuf) -> PyResult<Vec<(PathBuf, PyBA2Issues)>> {
    let scanner = PyBA2Scanner::new();
    let ba2_files = scanner.find_ba2_files(root_path);
    scanner.scan_archives_batch(ba2_files)
}

/// Register ba2 module functions with Python module
pub fn register_ba2(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyBA2Scanner>()?;
    m.add_class::<PyBA2Issues>()?;
    m.add_function(wrap_pyfunction!(scan_all_ba2_archives, m)?)?;
    Ok(())
}
