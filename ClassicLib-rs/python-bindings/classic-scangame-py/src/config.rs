//! PyO3 bindings for configuration duplicate detection

use classic_scangame_core::ConfigDuplicateDetector;
use pyo3::prelude::*;
use pyo3::types::PyList;
use std::path::PathBuf;

/// Python wrapper for DuplicateGroup
#[pyclass(name = "DuplicateGroup")]
#[derive(Clone)]
pub struct PyDuplicateGroup {
    /// Original file path
    #[pyo3(get)]
    pub original: PathBuf,
    /// List of duplicate file paths
    #[pyo3(get)]
    pub duplicates: Vec<PathBuf>,
}

#[pymethods]
impl PyDuplicateGroup {
    fn __repr__(&self) -> String {
        format!(
            "DuplicateGroup(original='{}', duplicates={})",
            self.original.display(),
            self.duplicates.len()
        )
    }
}

/// Python wrapper for ConfigDuplicateDetector
///
/// Detects duplicate configuration files in a directory tree.
///
/// Example:
///     >>> detector = ConfigDuplicateDetector()
///     >>> duplicates = detector.detect_duplicates("/path/to/config")
///     >>> for group in duplicates:
///     ...     print(f"Original: {group.original}")
///     ...     for dup in group.duplicates:
///     ...         print(f"  Duplicate: {dup}")
#[pyclass(name = "ConfigDuplicateDetector")]
pub struct PyConfigDuplicateDetector {
    inner: ConfigDuplicateDetector,
}

#[pymethods]
impl PyConfigDuplicateDetector {
    #[new]
    fn new() -> Self {
        Self {
            inner: ConfigDuplicateDetector::new(),
        }
    }

    /// Detect duplicate configuration files in the specified directory
    ///
    /// Args:
    ///     root_path: Root directory path to scan
    ///
    /// Returns:
    ///     List of DuplicateGroup objects containing original and duplicate paths
    fn detect_duplicates(&mut self, root_path: PathBuf) -> PyResult<Vec<PyDuplicateGroup>> {
        // Scan directory to populate internal state
        self.inner
            .scan_directory(&root_path)
            .map_err(crate::to_pyerr)?;

        // Get duplicates from internal state
        let duplicates = self.inner.get_duplicates();

        // Convert to Python types
        let py_duplicates: Vec<PyDuplicateGroup> = duplicates
            .values()
            .map(|group| PyDuplicateGroup {
                original: group.canonical.clone(),
                duplicates: group.duplicates.clone(),
            })
            .collect();

        Ok(py_duplicates)
    }

    /// Get dictionary mapping of lowercase filenames to lists of paths
    ///
    /// Args:
    ///     root_path: Root directory path to scan
    ///
    /// Returns:
    ///     Dictionary where keys are lowercase filenames and values are lists of paths
    fn get_duplicate_map(
        &mut self,
        py: Python<'_>,
        root_path: PathBuf,
    ) -> PyResult<Py<pyo3::types::PyDict>> {
        // Scan directory
        self.inner
            .scan_directory(&root_path)
            .map_err(crate::to_pyerr)?;

        // Get duplicates
        let duplicates = self.inner.get_duplicates();

        // Create Python dictionary
        let dict = pyo3::types::PyDict::new(py);

        for (filename, group) in duplicates {
            // Value is list of all paths (canonical + duplicates)
            let mut all_paths = vec![group.canonical.clone()];
            all_paths.extend(group.duplicates.clone());

            let list = PyList::new(py, all_paths)?;
            dict.set_item(filename, list)?;
        }

        Ok(dict.unbind())
    }

    fn __repr__(&self) -> String {
        "ConfigDuplicateDetector()".to_string()
    }
}

/// Convenience function to detect duplicates without creating detector instance
///
/// Args:
///     root_path: Root directory path to scan
///
/// Returns:
///     List of DuplicateGroup objects
#[pyfunction]
#[pyo3(signature = (root_path))]
pub fn detect_config_duplicates(root_path: PathBuf) -> PyResult<Vec<PyDuplicateGroup>> {
    let mut detector = PyConfigDuplicateDetector::new();
    detector.detect_duplicates(root_path)
}

/// Register config module functions with Python module
pub fn register_config(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyConfigDuplicateDetector>()?;
    m.add_class::<PyDuplicateGroup>()?;
    m.add_function(wrap_pyfunction!(detect_config_duplicates, m)?)?;
    Ok(())
}
