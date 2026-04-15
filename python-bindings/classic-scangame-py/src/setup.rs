//! PyO3 bindings for Setup Coordinator (G-18)
//!
//! Wraps the Rust setup coordination functions for Python consumption.
//! These are stateless utility functions, exposed as module-level functions.

use classic_scangame_core::integrity::IntegrityConfig;
use classic_scangame_core::setup::{
    SetupCheckConfig, SetupCheckResults, needs_path_detection, resolve_effective_game_version,
    run_combined_checks,
};
use classic_shared::without_gil;
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for SetupCheckConfig
///
/// Configuration for running combined setup checks including
/// integrity validation and document folder verification.
///
/// Example:
///     >>> config = SetupCheckConfig(
///     ...     game_exe_path="C:/Games/Fallout4/Fallout4.exe",
///     ...     valid_exe_hashes=["abc123"],
///     ...     root_name="Fallout 4",
///     ...     game_name="Fallout4",
///     ... )
///     >>> results = run_setup_checks(config)
#[pyclass(name = "SetupCheckConfig", from_py_object)]
#[derive(Clone)]
pub struct PySetupCheckConfig {
    inner: SetupCheckConfig,
}

#[pymethods]
impl PySetupCheckConfig {
    /// Create a new setup check configuration
    ///
    /// Args:
    ///     game_exe_path: Path to the game executable
    ///     valid_exe_hashes: List of valid SHA256 hashes for known game versions
    ///     root_name: Game root name (e.g., "Fallout 4")
    ///     game_name: Game name for document checking (e.g., "Fallout4")
    ///     docs_path: Optional documents folder path
    ///     xse_hashes: Optional list of (plugin_name, expected_hash) pairs
    #[new]
    #[pyo3(signature = (game_exe_path, valid_exe_hashes, root_name, game_name, docs_path=None, xse_hashes=None))]
    fn new(
        game_exe_path: PathBuf,
        valid_exe_hashes: Vec<String>,
        root_name: String,
        game_name: String,
        docs_path: Option<String>,
        xse_hashes: Option<Vec<(String, String)>>,
    ) -> Self {
        Self {
            inner: SetupCheckConfig {
                integrity: IntegrityConfig::new(game_exe_path, valid_exe_hashes, root_name),
                game_name,
                docs_path,
                xse_hashes: xse_hashes.unwrap_or_default(),
            },
        }
    }

    /// Get the game name
    #[getter]
    fn game_name(&self) -> String {
        self.inner.game_name.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "SetupCheckConfig(game_name='{}', exe='{}')",
            self.inner.game_name,
            self.inner.integrity.game_exe_path.display()
        )
    }
}

/// Python wrapper for SetupCheckResults
///
/// Contains results from all combined setup checks.
#[pyclass(name = "SetupCheckResults", from_py_object)]
#[derive(Clone)]
pub struct PySetupCheckResults {
    /// Results from game integrity checks
    #[pyo3(get)]
    pub integrity_results: Vec<String>,
    /// Results from XSE checks
    #[pyo3(get)]
    pub xse_results: Vec<String>,
    /// Results from document folder checks
    #[pyo3(get)]
    pub docs_results: Vec<String>,
    /// Any errors encountered (non-fatal)
    #[pyo3(get)]
    pub errors: Vec<String>,
}

#[pymethods]
impl PySetupCheckResults {
    /// Combine all results into a single string
    fn combined(&self) -> String {
        let mut parts = Vec::new();
        parts.extend(self.integrity_results.iter().cloned());
        parts.extend(self.xse_results.iter().cloned());
        parts.extend(self.docs_results.iter().cloned());
        parts.join("")
    }

    /// Check if any errors were encountered
    fn has_errors(&self) -> bool {
        !self.errors.is_empty()
    }

    /// Get the total number of check results
    fn total_checks(&self) -> usize {
        self.integrity_results.len() + self.xse_results.len() + self.docs_results.len()
    }

    fn __repr__(&self) -> String {
        format!(
            "SetupCheckResults(checks={}, errors={})",
            self.integrity_results.len() + self.xse_results.len() + self.docs_results.len(),
            self.errors.len()
        )
    }
}

/// Convert core results to Python wrapper
fn convert_results(results: SetupCheckResults) -> PySetupCheckResults {
    PySetupCheckResults {
        integrity_results: results.integrity_results,
        xse_results: results.xse_results,
        docs_results: results.docs_results,
        errors: results.errors,
    }
}

/// Run combined integrity, XSE, and document checks.
///
/// This is the main entry point for setup validation. Releases the GIL
/// during execution since it performs file I/O and hashing.
///
/// Args:
///     config: SetupCheckConfig with all check parameters
///
/// Returns:
///     SetupCheckResults with all check outputs
///
/// Example:
///     >>> config = SetupCheckConfig(
///     ...     game_exe_path="C:/Games/Fallout4/Fallout4.exe",
///     ...     valid_exe_hashes=["abc123"],
///     ...     root_name="Fallout 4",
///     ...     game_name="Fallout4",
///     ... )
///     >>> results = run_setup_checks(config)
///     >>> print(results.combined())
#[pyfunction]
fn run_setup_checks(py: Python<'_>, config: &PySetupCheckConfig) -> PySetupCheckResults {
    let cfg = config.inner.clone();
    let results = without_gil(py, || run_combined_checks(&cfg));
    convert_results(results)
}

/// Normalize a Game Version setting value.
///
/// Args:
///     game_version: Current Game Version setting value (or None)
///
/// Returns:
///     Resolved game version string, or None if no game version is provided
///
/// Example:
///     >>> migrate_game_version_setting_py("VR")
///     'VR'
///     >>> migrate_game_version_setting_py("Original")
///     'Original'
#[pyfunction]
#[pyo3(name = "migrate_game_version_setting")]
#[pyo3(signature = (game_version=None))]
fn migrate_game_version_setting_py(game_version: Option<&str>) -> Option<String> {
    game_version.map(|version| resolve_effective_game_version(Some(version)).to_string())
}

/// Resolve the effective game version from a raw setting value.
///
/// Maps the raw Game Version setting to one of the known values,
/// defaulting to "auto" for unknown or missing values.
///
/// Args:
///     game_version: Raw Game Version setting value (or None)
///
/// Returns:
///     One of: "Original", "NextGen", "AnniversaryEdition", "VR", or "auto"
///
/// Example:
///     >>> resolve_effective_game_version_py("VR")
///     'VR'
///     >>> resolve_effective_game_version_py("invalid")
///     'auto'
#[pyfunction]
#[pyo3(name = "resolve_effective_game_version")]
#[pyo3(signature = (game_version=None))]
fn resolve_effective_game_version_py(game_version: Option<&str>) -> &'static str {
    resolve_effective_game_version(game_version)
}

/// Check if game and documents paths need auto-detection.
///
/// Args:
///     game_path: Current game path setting (or None)
///     docs_path: Current documents path setting (or None)
///
/// Returns:
///     Tuple of (needs_game_path, needs_docs_path)
///
/// Example:
///     >>> needs_path_detection_py(None, None)
///     (True, True)
///     >>> needs_path_detection_py("C:/Games/FO4", None)
///     (False, True)
#[pyfunction]
#[pyo3(name = "needs_path_detection")]
#[pyo3(signature = (game_path=None, docs_path=None))]
fn needs_path_detection_py(game_path: Option<&str>, docs_path: Option<&str>) -> (bool, bool) {
    needs_path_detection(game_path, docs_path)
}

/// Register setup functions with the Python module
pub fn register_setup(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySetupCheckConfig>()?;
    m.add_class::<PySetupCheckResults>()?;
    m.add_function(wrap_pyfunction!(run_setup_checks, m)?)?;
    m.add_function(wrap_pyfunction!(migrate_game_version_setting_py, m)?)?;
    m.add_function(wrap_pyfunction!(resolve_effective_game_version_py, m)?)?;
    m.add_function(wrap_pyfunction!(needs_path_detection_py, m)?)?;
    Ok(())
}
