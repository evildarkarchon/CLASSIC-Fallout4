//! PyO3 bindings for GameScanOrchestrator (G-01/G-02)
//!
//! Wraps the async game scan orchestrator for Python consumption,
//! using `get_runtime().block_on()` with GIL release for sync API.

use classic_file_io_core::dds::GameTarget;
use classic_scangame_core::orchestrator::{
    GameScanConfig, GameScanOrchestrator, GameScanResult, ModScanResult,
};
use classic_scangame_core::xse::GameVersion;
use classic_shared::without_gil;
use classic_shared_core::get_runtime;
use pyo3::prelude::*;
use pyo3::types::PyAny;
use std::collections::HashMap;
use std::path::PathBuf;

use crate::crashgen_rules::parse_settings_rules;
use crate::ini::{PyConfigIssue, PyIssueSeverity};
use crate::xse::PyGameVersion;

/// Python wrapper for CheckResult
#[pyclass(name = "CheckResult")]
#[derive(Clone)]
pub struct PyCheckResult {
    /// Name of the check
    #[pyo3(get)]
    pub name: String,
    /// Formatted output text
    #[pyo3(get)]
    pub output: String,
}

#[pymethods]
impl PyCheckResult {
    fn __repr__(&self) -> String {
        format!(
            "CheckResult(name='{}', output_len={})",
            self.name,
            self.output.len()
        )
    }
}

/// Python wrapper for GameScanResult
#[pyclass(name = "GameScanResult")]
#[derive(Clone)]
pub struct PyGameScanResult {
    /// Formatted report text from all checks
    #[pyo3(get)]
    pub report: String,
    /// Individual check results
    #[pyo3(get)]
    pub check_results: Vec<PyCheckResult>,
    /// Any errors from failed checks (non-fatal)
    #[pyo3(get)]
    pub errors: Vec<String>,
    /// Config issues stored internally for property access
    config_issues: Vec<PyConfigIssue>,
}

#[pymethods]
impl PyGameScanResult {
    /// Detected configuration issues
    #[getter]
    fn config_issues(&self) -> Vec<PyConfigIssue> {
        self.config_issues.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "GameScanResult(checks={}, issues={}, errors={})",
            self.check_results.len(),
            self.config_issues.len(),
            self.errors.len()
        )
    }
}

/// Python wrapper for ModScanResult
#[pyclass(name = "ModScanResult")]
#[derive(Clone)]
pub struct PyModScanResult {
    /// Formatted report text
    #[pyo3(get)]
    pub report: String,
    /// Unpacked issues found
    #[pyo3(get)]
    pub unpacked_issue_count: usize,
    /// Archived issues found
    #[pyo3(get)]
    pub archived_issue_count: usize,
    /// Any errors from scanning
    #[pyo3(get)]
    pub errors: Vec<String>,
}

#[pymethods]
impl PyModScanResult {
    fn __repr__(&self) -> String {
        format!(
            "ModScanResult(unpacked={}, archived={}, errors={})",
            self.unpacked_issue_count,
            self.archived_issue_count,
            self.errors.len()
        )
    }
}

/// Python wrapper for GameScanConfig
///
/// Configuration for a game scan operation. All paths and settings
/// are provided by the Python/GUI layer.
///
/// Example:
///     >>> config = GameScanConfig(
///     ...     game_path="C:/Games/Fallout4",
///     ...     xse_acronym="F4SE",
///     ...     crashgen_name="Buffout4",
///     ...     game_name="Fallout4",
///     ... )
///     >>> orchestrator = GameScanOrchestrator(config)
///     >>> result = orchestrator.run_game_checks()
#[pyclass(name = "GameScanConfig")]
#[derive(Clone)]
pub struct PyGameScanConfig {
    inner: GameScanConfig,
}

#[pymethods]
impl PyGameScanConfig {
    /// Create a new GameScanConfig.
    ///
    /// Args:
    ///     game_path: Path to the game root directory
    ///     xse_acronym: Script extender name (e.g., "F4SE", "SKSE")
    ///     crashgen_name: Crashgen plugin name (e.g., "Buffout4")
    ///     game_name: Game name string (e.g., "Fallout4")
    ///     docs_path: Optional path to docs folder
    ///     mods_path: Optional path to mods folder
    ///     xse_scriptfiles: XSE script file patterns -> expected hashes
    ///     plugins_path: Optional path to F4SE/SKSE plugins directory
    ///     is_vr: Whether in VR mode
    ///     game_version: Detected game version
    ///     wrye_warnings: Wrye Bash warning patterns
    ///     log_catch_errors: Log error catch patterns
    ///     log_exclude_files: Log file exclude patterns
    ///     log_exclude_errors: Log error exclude patterns
    ///     game_target: Game target for DDS validation ("fallout4" or "skyrimse")
    #[new]
    #[pyo3(signature = (
        game_path,
        xse_acronym,
        crashgen_name,
        game_name,
        docs_path = None,
        mods_path = None,
        xse_scriptfiles = None,
        plugins_path = None,
        is_vr = false,
        game_version = None,
        wrye_warnings = None,
        log_catch_errors = None,
        log_exclude_files = None,
        log_exclude_errors = None,
        crashgen_settings_rules = None,
        game_target = None,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        game_path: PathBuf,
        xse_acronym: String,
        crashgen_name: String,
        game_name: String,
        docs_path: Option<PathBuf>,
        mods_path: Option<PathBuf>,
        xse_scriptfiles: Option<HashMap<String, Vec<String>>>,
        plugins_path: Option<PathBuf>,
        is_vr: bool,
        game_version: Option<&PyGameVersion>,
        wrye_warnings: Option<HashMap<String, String>>,
        log_catch_errors: Option<Vec<String>>,
        log_exclude_files: Option<Vec<String>>,
        log_exclude_errors: Option<Vec<String>>,
        crashgen_settings_rules: Option<&Bound<'_, PyAny>>,
        game_target: Option<&str>,
    ) -> Self {
        let gv = match game_version {
            Some(PyGameVersion::Null) => GameVersion::Null,
            Some(PyGameVersion::Original) => GameVersion::Original,
            Some(PyGameVersion::NextGen) => GameVersion::NextGen,
            Some(PyGameVersion::AnniversaryEdition) => GameVersion::AnniversaryEdition,
            Some(PyGameVersion::Vr) => GameVersion::Vr,
            None => GameVersion::Original,
        };

        let gt = match game_target {
            Some("skyrimse") | Some("SkyrimSE") => GameTarget::SkyrimSE,
            _ => GameTarget::Fallout4,
        };

        Self {
            inner: GameScanConfig {
                game_path,
                docs_path,
                mods_path,
                xse_acronym,
                xse_scriptfiles: xse_scriptfiles.unwrap_or_default(),
                plugins_path,
                is_vr,
                game_version: gv,
                crashgen_name,
                crashgen_settings_rules: crashgen_settings_rules.and_then(parse_settings_rules),
                wrye_warnings: wrye_warnings.unwrap_or_default(),
                log_catch_errors: log_catch_errors.unwrap_or_default(),
                log_exclude_files: log_exclude_files.unwrap_or_default(),
                log_exclude_errors: log_exclude_errors.unwrap_or_default(),
                game_target: gt,
                game_name,
            },
        }
    }

    /// Get the game path
    #[getter]
    fn game_path(&self) -> PathBuf {
        self.inner.game_path.clone()
    }

    /// Get the XSE acronym
    #[getter]
    fn xse_acronym(&self) -> String {
        self.inner.xse_acronym.clone()
    }

    /// Get the game name
    #[getter]
    fn game_name(&self) -> String {
        self.inner.game_name.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "GameScanConfig(game_path='{}', game_name='{}')",
            self.inner.game_path.display(),
            self.inner.game_name
        )
    }
}

/// Python wrapper for GameScanOrchestrator
///
/// Coordinates concurrent execution of game integrity checks and mod scans.
/// All checks run as independent tasks -- individual failures are captured
/// without aborting the entire operation.
///
/// Example:
///     >>> config = GameScanConfig(game_path="C:/Games/Fallout4", ...)
///     >>> orchestrator = GameScanOrchestrator(config)
///     >>> game_result = orchestrator.run_game_checks()  # Releases GIL
///     >>> mod_result = orchestrator.run_mod_scans()      # Releases GIL
///     >>> print(game_result.report)
#[pyclass(name = "GameScanOrchestrator")]
pub struct PyGameScanOrchestrator {
    config: GameScanConfig,
}

#[pymethods]
impl PyGameScanOrchestrator {
    /// Create a new orchestrator with the given configuration
    #[new]
    fn new(config: &PyGameScanConfig) -> Self {
        Self {
            config: config.inner.clone(),
        }
    }

    /// Run all game integrity checks concurrently.
    ///
    /// Executes XSE validation, crashgen checking, ENB detection,
    /// log error scanning, Wrye Bash analysis, and mod INI scanning
    /// as concurrent tasks. Releases the GIL during execution.
    ///
    /// Returns:
    ///     GameScanResult with report text, config issues, and any errors
    ///
    /// Raises:
    ///     RuntimeError: If orchestration fails fatally
    fn run_game_checks(&self, py: Python<'_>) -> PyResult<PyGameScanResult> {
        let config = self.config.clone();
        without_gil(py, || {
            get_runtime().block_on(async {
                let orch = GameScanOrchestrator::new(config);
                orch.run_game_checks().await
            })
        })
        .map(convert_game_result)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }

    /// Run mod file scans (unpacked + archived) concurrently.
    ///
    /// Scans both loose/unpacked mod files and BA2 archives for issues.
    /// Releases the GIL during execution.
    ///
    /// Returns:
    ///     ModScanResult with report text, issue counts, and any errors
    ///
    /// Raises:
    ///     RuntimeError: If orchestration fails fatally
    fn run_mod_scans(&self, py: Python<'_>) -> PyResult<PyModScanResult> {
        let config = self.config.clone();
        without_gil(py, || {
            get_runtime().block_on(async {
                let orch = GameScanOrchestrator::new(config);
                orch.run_mod_scans().await
            })
        })
        .map(convert_mod_result)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }

    /// Run the full scan pipeline: game checks + mod scans concurrently.
    ///
    /// Returns combined game result and mod result. Releases the GIL
    /// during execution.
    ///
    /// Returns:
    ///     Tuple of (GameScanResult, ModScanResult)
    ///
    /// Raises:
    ///     RuntimeError: If orchestration fails fatally
    fn run_full_scan(&self, py: Python<'_>) -> PyResult<(PyGameScanResult, PyModScanResult)> {
        let config = self.config.clone();
        without_gil(py, || {
            get_runtime().block_on(async {
                let orch = GameScanOrchestrator::new(config);
                orch.run_full_scan().await
            })
        })
        .map(|(game, mods)| (convert_game_result(game), convert_mod_result(mods)))
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }

    fn __repr__(&self) -> String {
        format!(
            "GameScanOrchestrator(game_path='{}', game_name='{}')",
            self.config.game_path.display(),
            self.config.game_name
        )
    }
}

/// Convert core GameScanResult to Python wrapper
fn convert_game_result(result: GameScanResult) -> PyGameScanResult {
    let check_results = result
        .check_results
        .into_iter()
        .map(|cr| PyCheckResult {
            name: cr.name,
            output: cr.output,
        })
        .collect();

    let config_issues = result
        .config_issues
        .into_iter()
        .map(|ci| PyConfigIssue {
            file_path: ci.file_path,
            section: ci.section,
            setting: ci.setting,
            current_value: ci.current_value,
            recommended_value: ci.recommended_value,
            description: ci.description,
            severity: match ci.severity {
                classic_scangame_core::IssueSeverity::Info => PyIssueSeverity::Info,
                classic_scangame_core::IssueSeverity::Warning => PyIssueSeverity::Warning,
                classic_scangame_core::IssueSeverity::Error => PyIssueSeverity::Error,
            },
        })
        .collect();

    PyGameScanResult {
        report: result.report,
        check_results,
        errors: result.errors,
        config_issues,
    }
}

/// Convert core ModScanResult to Python wrapper
fn convert_mod_result(result: ModScanResult) -> PyModScanResult {
    PyModScanResult {
        report: result.report,
        unpacked_issue_count: result.unpacked_issue_count,
        archived_issue_count: result.archived_issue_count,
        errors: result.errors,
    }
}

/// Register orchestrator types with the Python module
pub fn register_orchestrator(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCheckResult>()?;
    m.add_class::<PyGameScanResult>()?;
    m.add_class::<PyModScanResult>()?;
    m.add_class::<PyGameScanConfig>()?;
    m.add_class::<PyGameScanOrchestrator>()?;
    Ok(())
}
