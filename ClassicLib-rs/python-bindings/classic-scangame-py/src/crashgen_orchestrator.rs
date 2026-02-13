//! PyO3 bindings for CrashgenCheckOrchestrator (high-level crashgen validation)

use classic_scangame_core::crashgen_orchestrator::{CrashgenCheckOrchestrator, CrashgenReport};
use pyo3::prelude::*;
use std::path::PathBuf;

use crate::toml_check::PyTomlConfigIssue;
use crate::toml_check::PyTomlIssueSeverity;
use classic_scangame_core::TomlIssueSeverity;

/// Python wrapper for CrashgenReport
#[pyclass(name = "CrashgenReport")]
#[derive(Clone)]
pub struct PyCrashgenReport {
    /// Formatted message string
    #[pyo3(get)]
    pub message: String,

    /// Structured list of configuration issues detected
    #[pyo3(get)]
    pub issues: Vec<PyTomlConfigIssue>,

    /// Name of the crash generator being checked
    #[pyo3(get)]
    pub crashgen_name: String,

    /// Path to the configuration file that was checked (if found)
    #[pyo3(get)]
    pub config_path: Option<PathBuf>,

    /// Set of installed plugin DLL names (lowercase)
    #[pyo3(get)]
    pub installed_plugins: Vec<String>,
}

#[pymethods]
impl PyCrashgenReport {
    fn __repr__(&self) -> String {
        format!(
            "CrashgenReport(crashgen='{}', issues={}, plugins={})",
            self.crashgen_name,
            self.issues.len(),
            self.installed_plugins.len()
        )
    }
}

/// Convert a core CrashgenReport to its Python wrapper
fn convert_report(report: CrashgenReport) -> PyCrashgenReport {
    let issues = report
        .issues
        .into_iter()
        .map(|issue| PyTomlConfigIssue {
            file_path: issue.file_path,
            section: issue.section,
            setting: issue.setting,
            current_value: issue.current_value,
            recommended_value: issue.recommended_value,
            description: issue.description,
            severity: match issue.severity {
                TomlIssueSeverity::Info => PyTomlIssueSeverity::Info,
                TomlIssueSeverity::Warning => PyTomlIssueSeverity::Warning,
                TomlIssueSeverity::Error => PyTomlIssueSeverity::Error,
            },
        })
        .collect();

    PyCrashgenReport {
        message: report.message,
        issues,
        crashgen_name: report.crashgen_name,
        config_path: report.config_path,
        installed_plugins: report.installed_plugins,
    }
}

/// Python wrapper for CrashgenCheckOrchestrator
///
/// High-level orchestrator for crash generator (Buffout4) configuration checks.
/// Handles path resolution, plugin detection, settings validation, and report generation.
///
/// Example:
///     >>> report = CrashgenCheckOrchestrator.check("/path/to/plugins", "Buffout4")
///     >>> print(report.message)
///     >>> for issue in report.issues:
///     ...     print(f"{issue.setting} = {issue.current_value}")
#[pyclass(name = "CrashgenCheckOrchestrator")]
pub struct PyCrashgenCheckOrchestrator;

#[pymethods]
impl PyCrashgenCheckOrchestrator {
    #[new]
    fn new() -> Self {
        Self
    }

    /// Run the full crash generator check
    ///
    /// Args:
    ///     plugins_path: Path to the game's plugin directory (e.g., Data/F4SE/Plugins)
    ///     crashgen_name: Name of the crash generator (e.g., "Buffout4")
    ///
    /// Returns:
    ///     CrashgenReport with message, issues, and metadata
    #[staticmethod]
    fn check(plugins_path: PathBuf, crashgen_name: &str) -> PyResult<PyCrashgenReport> {
        let report = CrashgenCheckOrchestrator::check(&plugins_path, crashgen_name)
            .map_err(crate::to_pyerr)?;
        Ok(convert_report(report))
    }

    /// Scan a plugins directory and return installed DLL names (lowercase)
    ///
    /// Args:
    ///     plugins_path: Path to scan for DLL files
    ///
    /// Returns:
    ///     List of lowercase filenames
    #[staticmethod]
    fn detect_plugins(plugins_path: PathBuf) -> PyResult<Vec<String>> {
        CrashgenCheckOrchestrator::detect_plugins(&plugins_path).map_err(crate::to_pyerr)
    }

    /// Resolve the crashgen TOML config file path
    ///
    /// Args:
    ///     plugins_path: Path to the game's plugin directory
    ///
    /// Returns:
    ///     Config file path if found, None otherwise
    #[staticmethod]
    fn resolve_config_path(plugins_path: PathBuf) -> Option<PathBuf> {
        CrashgenCheckOrchestrator::resolve_config_path(&plugins_path)
    }

    fn __repr__(&self) -> String {
        "CrashgenCheckOrchestrator()".to_string()
    }
}

/// Convenience function: run full crashgen check without creating orchestrator
///
/// Args:
///     plugins_path: Path to F4SE/SKSE plugins directory
///     crashgen_name: Name of crash generator (e.g., "Buffout4")
///
/// Returns:
///     Tuple of (message_string, list of TomlConfigIssue objects)
#[pyfunction]
#[pyo3(signature = (plugins_path, crashgen_name))]
pub fn check_crashgen_settings(
    plugins_path: PathBuf,
    crashgen_name: &str,
) -> PyResult<(String, Vec<PyTomlConfigIssue>)> {
    let report =
        CrashgenCheckOrchestrator::check(&plugins_path, crashgen_name).map_err(crate::to_pyerr)?;

    let py_issues = report
        .issues
        .into_iter()
        .map(|issue| PyTomlConfigIssue {
            file_path: issue.file_path,
            section: issue.section,
            setting: issue.setting,
            current_value: issue.current_value,
            recommended_value: issue.recommended_value,
            description: issue.description,
            severity: match issue.severity {
                TomlIssueSeverity::Info => PyTomlIssueSeverity::Info,
                TomlIssueSeverity::Warning => PyTomlIssueSeverity::Warning,
                TomlIssueSeverity::Error => PyTomlIssueSeverity::Error,
            },
        })
        .collect();

    Ok((report.message, py_issues))
}

/// Register crashgen orchestrator functions with Python module
pub fn register_crashgen_orchestrator(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCrashgenCheckOrchestrator>()?;
    m.add_class::<PyCrashgenReport>()?;
    m.add_function(wrap_pyfunction!(check_crashgen_settings, m)?)?;
    Ok(())
}
