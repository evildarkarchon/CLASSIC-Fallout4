//! PyO3 bindings for TOML configuration validation (CheckCrashgen)

use classic_scangame_core::{CrashgenChecker, TomlIssueSeverity};
use pyo3::prelude::*;
use pyo3::types::PyAny;
use std::path::PathBuf;

use crate::crashgen_rules::parse_settings_rules;

/// Python wrapper for TomlIssueSeverity
#[pyclass(name = "TomlIssueSeverity", from_py_object)]
#[derive(Clone)]
pub enum PyTomlIssueSeverity {
    /// Informational issue
    Info,
    /// Warning level issue
    Warning,
    /// Error level issue
    Error,
}

/// Python wrapper for TomlConfigIssue
#[pyclass(name = "TomlConfigIssue", from_py_object)]
#[derive(Clone)]
pub struct PyTomlConfigIssue {
    /// Path to the TOML configuration file
    #[pyo3(get)]
    pub file_path: PathBuf,
    /// Section name in the TOML file
    #[pyo3(get)]
    pub section: String,
    /// Setting name
    #[pyo3(get)]
    pub setting: String,
    /// Current value of the setting
    #[pyo3(get)]
    pub current_value: String,
    /// Recommended value to fix the issue
    #[pyo3(get)]
    pub recommended_value: String,
    /// Description of the issue
    #[pyo3(get)]
    pub description: String,
    /// Severity level
    #[pyo3(get)]
    pub severity: PyTomlIssueSeverity,
}

#[pymethods]
impl PyTomlConfigIssue {
    fn __repr__(&self) -> String {
        format!(
            "TomlConfigIssue(file='{}', setting='{}', description='{}')",
            self.file_path.display(),
            self.setting,
            self.description
        )
    }
}

/// Python wrapper for CrashgenChecker
///
/// Validates Buffout4/crash generator TOML configuration files.
///
/// Example:
///     >>> checker = CrashgenChecker("/path/to/plugins", "Buffout4")
///     >>> message, issues = checker.check()
///     >>> print(message)
///     >>> for issue in issues:
///     ...     print(f"{issue.description}")
#[pyclass(name = "CrashgenChecker")]
pub struct PyCrashgenChecker {
    inner: CrashgenChecker,
}

#[pymethods]
impl PyCrashgenChecker {
    #[new]
    #[pyo3(signature = (plugins_path, crashgen_name, settings_rules = None))]
    fn new(
        plugins_path: PathBuf,
        crashgen_name: String,
        settings_rules: Option<&Bound<'_, PyAny>>,
    ) -> Self {
        Self {
            inner: CrashgenChecker::new_with_rules(
                &plugins_path,
                crashgen_name,
                settings_rules.and_then(parse_settings_rules),
            ),
        }
    }

    /// Check TOML configuration for issues
    ///
    /// Returns:
    ///     Tuple of (message_string, list of TomlConfigIssue objects)
    fn check(&mut self) -> PyResult<(String, Vec<PyTomlConfigIssue>)> {
        let (message, issues) = self.inner.check().map_err(crate::to_pyerr)?;

        // Convert to Python types
        let py_issues = issues
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

        Ok((message, py_issues))
    }

    fn __repr__(&self) -> String {
        "CrashgenChecker(...)".to_string()
    }
}

/// Convenience function to check crashgen config without creating checker instance
///
/// Args:
///     plugins_path: Path to F4SE/SKSE plugins directory
///     crashgen_name: Name of crash generator (e.g., "Buffout4")
///
/// Returns:
///     Tuple of (message_string, list of TomlConfigIssue objects)
#[pyfunction]
#[pyo3(signature = (plugins_path, crashgen_name, settings_rules = None))]
pub fn check_crashgen_config(
    plugins_path: PathBuf,
    crashgen_name: String,
    settings_rules: Option<&Bound<'_, PyAny>>,
) -> PyResult<(String, Vec<PyTomlConfigIssue>)> {
    let mut checker = PyCrashgenChecker::new(plugins_path, crashgen_name, settings_rules);
    checker.check()
}

/// Register toml_check module functions with Python module
pub fn register_toml(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCrashgenChecker>()?;
    m.add_class::<PyTomlConfigIssue>()?;
    m.add_class::<PyTomlIssueSeverity>()?;
    m.add_function(wrap_pyfunction!(check_crashgen_config, m)?)?;
    Ok(())
}
