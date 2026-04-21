//! PyO3 bindings for DDSAnalyzer (G-08 DDS Pipeline)
//!
//! Wraps the game-specific DDS texture validation from classic-file-io-core
//! for Python consumption.

use classic_file_io_core::dds::{DDSAnalyzer, GameTarget};
use classic_shared::without_gil;
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for DDSAnalyzer
///
/// Validates DDS texture files against game-specific rules.
///
/// Example:
///     >>> from classic_file_io import DDSAnalyzer
///     >>> analyzer = DDSAnalyzer("fallout4")
///     >>> issues = analyzer.validate_file("texture.dds")
///     >>> for issue in issues:
///     ...     print(issue)
///     >>> batch_results = analyzer.validate_batch(["tex1.dds", "tex2.dds"])
///     >>> for path, issues in batch_results:
///     ...     print(f"{path}: {len(issues)} issues")
#[pyclass(name = "DDSAnalyzer")]
pub struct PyDDSAnalyzer {
    inner: DDSAnalyzer,
}

#[pymethods]
impl PyDDSAnalyzer {
    /// Create a new analyzer targeting a specific game.
    ///
    /// Args:
    ///     game_target: Game to validate against ("fallout4" or "skyrimse").
    ///                  Defaults to "fallout4" for unknown values.
    #[new]
    #[pyo3(signature = (game_target="fallout4"))]
    fn new(game_target: &str) -> Self {
        let target = match game_target.to_lowercase().as_str() {
            "skyrimse" | "skyrim_se" | "skyrim" => GameTarget::SkyrimSE,
            _ => GameTarget::Fallout4,
        };
        Self {
            inner: DDSAnalyzer::new(target),
        }
    }

    /// Validate a single DDS file by reading its header from disk.
    ///
    /// Returns a list of issue description strings. An empty list means
    /// the file is valid. Releases the GIL during file I/O.
    ///
    /// Args:
    ///     path: Path to the DDS file
    ///
    /// Returns:
    ///     List of issue description strings
    ///
    /// Example:
    ///     >>> issues = analyzer.validate_file("texture.dds")
    ///     >>> if issues:
    ///     ...     for issue in issues:
    ///     ...         print(f"  Issue: {issue}")
    fn validate_file(&self, py: Python<'_>, path: &str) -> Vec<String> {
        let path = PathBuf::from(path);
        let inner = &self.inner;
        without_gil(py, || {
            inner
                .validate_file(&path)
                .into_iter()
                .map(|i| i.message)
                .collect()
        })
    }

    /// Validate multiple DDS files in parallel using Rayon.
    ///
    /// Returns a list of (path, issues) tuples for files that had issues.
    /// Files with no issues are omitted. Releases the GIL during processing.
    ///
    /// Args:
    ///     paths: List of paths to DDS files
    ///
    /// Returns:
    ///     List of (path_str, issue_strings) tuples for files with issues
    ///
    /// Example:
    ///     >>> results = analyzer.validate_batch(["tex1.dds", "tex2.dds"])
    ///     >>> for path, issues in results:
    ///     ...     print(f"{path}: {len(issues)} issues")
    fn validate_batch(&self, py: Python<'_>, paths: Vec<String>) -> Vec<(String, Vec<String>)> {
        let pathbufs: Vec<PathBuf> = paths.into_iter().map(PathBuf::from).collect();
        let inner = &self.inner;
        without_gil(py, || {
            inner
                .validate_batch(&pathbufs)
                .into_iter()
                .map(|(path, issues)| {
                    (
                        path.display().to_string(),
                        issues.into_iter().map(|i| i.message).collect(),
                    )
                })
                .collect()
        })
    }

    /// Validate DDS dimensions (width, height) without reading a file.
    ///
    /// This is a static method that checks if dimensions are even and
    /// within reasonable bounds. Useful as a quick pre-filter.
    ///
    /// Args:
    ///     width: Texture width in pixels
    ///     height: Texture height in pixels
    ///
    /// Returns:
    ///     List of issue description strings
    ///
    /// Example:
    ///     >>> issues = DDSAnalyzer.validate_dimensions(1023, 512)
    ///     >>> # ["Non-even dimensions: 1023x512"]
    #[staticmethod]
    fn validate_dimensions(width: u32, height: u32) -> Vec<String> {
        DDSAnalyzer::validate_dimensions(width, height)
            .into_iter()
            .map(|i| i.message)
            .collect()
    }

    fn __repr__(&self) -> String {
        "DDSAnalyzer(...)".to_string()
    }
}

/// Register DDS analyzer with the Python module
pub fn register_dds_analyzer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDDSAnalyzer>()?;
    Ok(())
}
