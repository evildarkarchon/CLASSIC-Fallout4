//! PyO3 bindings for Game Setup Intake.
//!
//! The Python surface is a thin adapter over `classic-scangame-core`: it
//! collects caller inputs, delegates all setup resolution and validation to
//! Rust core, then exposes the rendered report and typed diagnostics.

use classic_scangame_core::{
    GameSetupCheck, GameSetupIntake, GameSetupIntakeResult, game_setup_needs_path_detection,
    normalize_game_setup_version_selection,
};
use classic_shared::without_gil;
use classic_shared_core::GameId;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::path::PathBuf;
use std::str::FromStr;

/// Python wrapper for a Game Setup Intake request.
///
/// The request is read-only. Running it may discover paths the caller could
/// persist later, but this binding does not write settings files.
#[pyclass(name = "GameSetupIntake", from_py_object)]
#[derive(Clone)]
pub struct PyGameSetupIntake {
    inner: GameSetupIntake,
}

#[pymethods]
impl PyGameSetupIntake {
    /// Create a new Game Setup Intake request.
    ///
    /// Args:
    ///     game_id: Stable game identifier, such as "Fallout4".
    ///     game_version: Selected version mode, or "auto" for executable detection.
    ///     game_root: Optional game installation root.
    ///     docs_root: Optional documents root.
    ///     xse_log_path: Optional XSE log path used as a detection hint.
    ///     game_exe_path: Optional game executable path.
    #[new]
    #[pyo3(signature = (game_id, game_version="auto".to_string(), game_root=None, docs_root=None, xse_log_path=None, game_exe_path=None))]
    fn new(
        game_id: String,
        game_version: String,
        game_root: Option<PathBuf>,
        docs_root: Option<PathBuf>,
        xse_log_path: Option<PathBuf>,
        game_exe_path: Option<PathBuf>,
    ) -> PyResult<Self> {
        let parsed_game_id = GameId::from_str(&game_id).map_err(PyValueError::new_err)?;
        let mut intake = GameSetupIntake::new(parsed_game_id, game_version);
        if let Some(path) = game_root {
            intake = intake.with_game_root(path);
        }
        if let Some(path) = game_exe_path {
            intake = intake.with_game_exe_path(path);
        }
        if let Some(path) = docs_root {
            intake = intake.with_docs_root(path);
        }
        if let Some(path) = xse_log_path {
            intake = intake.with_xse_log_path(path);
        }
        Ok(Self { inner: intake })
    }

    /// Stable game identifier for this intake request.
    #[getter]
    fn game_id(&self) -> String {
        self.inner.game_id.as_str().to_string()
    }

    /// Selected game version for this intake request.
    #[getter]
    fn game_version(&self) -> String {
        self.inner.selected_game_version.clone()
    }

    /// Saved or caller-provided game root.
    #[getter]
    fn game_root(&self) -> Option<String> {
        self.inner
            .game_root
            .as_ref()
            .map(|path| path.to_string_lossy().into_owned())
    }

    /// Saved or caller-provided game executable path.
    #[getter]
    fn game_exe_path(&self) -> Option<String> {
        self.inner
            .game_exe_path
            .as_ref()
            .map(|path| path.to_string_lossy().into_owned())
    }

    /// Saved or caller-provided documents root.
    #[getter]
    fn docs_root(&self) -> Option<String> {
        self.inner
            .docs_root
            .as_ref()
            .map(|path| path.to_string_lossy().into_owned())
    }

    /// Optional XSE log path used as a detection hint.
    #[getter]
    fn xse_log_path(&self) -> Option<String> {
        self.inner
            .xse_log_path
            .as_ref()
            .map(|path| path.to_string_lossy().into_owned())
    }

    fn __repr__(&self) -> String {
        format!(
            "GameSetupIntake(game_id='{}', game_version='{}')",
            self.inner.game_id, self.inner.selected_game_version
        )
    }
}

/// Python wrapper for one typed Game Setup Check.
#[pyclass(name = "GameSetupCheck", from_py_object)]
#[derive(Clone)]
pub struct PyGameSetupCheck {
    /// Stable check kind identifier.
    #[pyo3(get)]
    pub kind: String,
    /// Stable check state identifier.
    #[pyo3(get)]
    pub state: String,
    /// Human-readable summary.
    #[pyo3(get)]
    pub message: String,
    /// Additional detail lines.
    #[pyo3(get)]
    pub details: Vec<String>,
}

#[pymethods]
impl PyGameSetupCheck {
    fn __repr__(&self) -> String {
        format!(
            "GameSetupCheck(kind='{}', state='{}', message='{}')",
            self.kind, self.state, self.message
        )
    }
}

/// Python wrapper for a Game Setup Intake result.
#[pyclass(name = "GameSetupIntakeResult", from_py_object)]
#[derive(Clone)]
pub struct PyGameSetupIntakeResult {
    /// Rust-rendered report for display surfaces.
    #[pyo3(get)]
    pub rendered_report: String,
    /// Top-level intake status.
    #[pyo3(get)]
    pub status: String,
    /// Whether any diagnostic checks failed.
    #[pyo3(get)]
    pub has_errors: bool,
    /// Number of intake checks.
    #[pyo3(get)]
    pub total_checks: usize,
    /// Number of failed intake checks.
    #[pyo3(get)]
    pub failed_checks: usize,
    /// Number of user actions required before all checks can run.
    #[pyo3(get)]
    pub action_count: usize,
    /// Number of detected paths that callers may persist.
    #[pyo3(get)]
    pub path_update_count: usize,
    /// Resolved game root, when known.
    #[pyo3(get)]
    pub game_root: Option<String>,
    /// Resolved documents root, when known.
    #[pyo3(get)]
    pub docs_root: Option<String>,
    /// Typed check diagnostics.
    #[pyo3(get)]
    pub checks: Vec<PyGameSetupCheck>,
}

#[pymethods]
impl PyGameSetupIntakeResult {
    /// Return the Rust-rendered report.
    fn combined(&self) -> String {
        self.rendered_report.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "GameSetupIntakeResult(status='{}', checks={}, failed={})",
            self.status, self.total_checks, self.failed_checks
        )
    }
}

fn convert_check(check: GameSetupCheck) -> PyGameSetupCheck {
    PyGameSetupCheck {
        kind: check.kind.as_str().to_string(),
        state: check.state.as_str().to_string(),
        message: check.message,
        details: check.details,
    }
}

fn convert_result(result: GameSetupIntakeResult) -> PyGameSetupIntakeResult {
    let has_errors = result.has_errors();
    let total_checks = result.total_checks();
    let failed_checks = result.failed_checks();
    PyGameSetupIntakeResult {
        rendered_report: result.rendered_report,
        status: result.status.as_str().to_string(),
        has_errors,
        total_checks,
        failed_checks,
        action_count: result.actions.len(),
        path_update_count: result.path_updates.len(),
        game_root: result
            .paths
            .game_root
            .map(|path| path.to_string_lossy().into_owned()),
        docs_root: result
            .paths
            .docs_root
            .map(|path| path.to_string_lossy().into_owned()),
        checks: result.checks.into_iter().map(convert_check).collect(),
    }
}

/// Run Game Setup Intake and return rendered plus typed diagnostics.
///
/// Releases the GIL while Rust core performs filesystem and metadata checks.
#[pyfunction]
fn run_game_setup_intake(py: Python<'_>, intake: &PyGameSetupIntake) -> PyGameSetupIntakeResult {
    let core_intake = intake.inner.clone();
    let result = without_gil(py, || core_intake.run());
    convert_result(result)
}

/// Normalize a raw Game Setup Intake version selection.
#[pyfunction]
#[pyo3(name = "normalize_game_setup_version_selection")]
#[pyo3(signature = (game_version=None))]
fn normalize_game_setup_version_selection_py(game_version: Option<&str>) -> String {
    normalize_game_setup_version_selection(game_version.unwrap_or(""))
}

/// Check if game and documents paths need Game Setup Intake auto-detection.
#[pyfunction]
#[pyo3(name = "game_setup_needs_path_detection")]
#[pyo3(signature = (game_path=None, docs_path=None))]
fn game_setup_needs_path_detection_py(
    game_path: Option<&str>,
    docs_path: Option<&str>,
) -> (bool, bool) {
    game_setup_needs_path_detection(game_path, docs_path)
}

/// Register Game Setup Intake functions with the Python module.
pub fn register_setup(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyGameSetupIntake>()?;
    m.add_class::<PyGameSetupCheck>()?;
    m.add_class::<PyGameSetupIntakeResult>()?;
    m.add_function(wrap_pyfunction!(run_game_setup_intake, m)?)?;
    m.add_function(wrap_pyfunction!(
        normalize_game_setup_version_selection_py,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(game_setup_needs_path_detection_py, m)?)?;
    Ok(())
}
