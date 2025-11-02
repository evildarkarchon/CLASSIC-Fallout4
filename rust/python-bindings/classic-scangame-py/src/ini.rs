//! PyO3 bindings for INI file validation

use classic_scangame_core::{IniValidator, IssueSeverity};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::path::PathBuf;

/// Python wrapper for IssueSeverity
#[pyclass(name = "IssueSeverity")]
#[derive(Clone)]
pub enum PyIssueSeverity {
    /// Informational issue
    Info,
    /// Warning level issue
    Warning,
    /// Error level issue
    Error,
}

/// Python wrapper for ConfigIssue
#[pyclass(name = "ConfigIssue")]
#[derive(Clone)]
pub struct PyConfigIssue {
    /// Path to the configuration file
    #[pyo3(get)]
    pub file_path: PathBuf,
    /// Section name in the INI file
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
    pub severity: PyIssueSeverity,
}

#[pymethods]
impl PyConfigIssue {
    fn __repr__(&self) -> String {
        format!(
            "ConfigIssue(file='{}', setting='{}', description='{}')",
            self.file_path.display(),
            self.setting,
            self.description
        )
    }
}

/// Python wrapper for IniValidator
///
/// Validates game configuration INI files for common issues.
///
/// Example:
///     >>> validator = IniValidator("Fallout4")
///     >>> config_files = {
///     ...     "fallout4.ini": Path("/path/to/fallout4.ini"),
///     ...     "fallout4prefs.ini": Path("/path/to/fallout4prefs.ini"),
///     ... }
///     >>> validator.load_files(config_files)
///     >>> issues = validator.detect_all_issues(config_files)
///     >>> for issue in issues:
///     ...     print(f"{issue.file_path}: {issue.description}")
#[pyclass(name = "IniValidator")]
pub struct PyIniValidator {
    inner: IniValidator,
}

#[pymethods]
impl PyIniValidator {
    #[new]
    #[pyo3(signature = (game_name))]
    fn new(game_name: String) -> Self {
        Self {
            inner: IniValidator::new(game_name),
        }
    }

    /// Validate INI files in a game directory
    ///
    /// Args:
    ///     game_root: Root directory of the game installation
    ///
    /// Returns:
    ///     Formatted validation report string
    fn validate_inis(&mut self, game_root: PathBuf) -> PyResult<String> {
        let report = self.inner.validate_inis(&game_root).map_err(crate::to_pyerr)?;
        Ok(report)
    }

    /// Detect all known configuration issues from a config files dict
    ///
    /// Args:
    ///     config_files: Dictionary mapping lowercase filenames to file paths
    ///
    /// Returns:
    ///     List of ConfigIssue objects describing detected issues
    fn detect_all_issues(&self, _py: Python<'_>, config_files: &Bound<'_, PyDict>) -> Vec<PyConfigIssue> {
        // Convert PyDict to HashMap<String, PathBuf>
        let mut config_map = HashMap::new();
        for (key, value) in config_files.iter() {
            if let (Ok(k), Ok(v)) = (key.extract::<String>(), value.extract::<PathBuf>()) {
                config_map.insert(k, v);
            }
        }

        let issues = self.inner.detect_all_issues(&config_map);

        // Convert to Python types
        issues
            .into_iter()
            .map(|issue| PyConfigIssue {
                file_path: issue.file_path,
                section: issue.section,
                setting: issue.setting,
                current_value: issue.current_value,
                recommended_value: issue.recommended_value,
                description: issue.description,
                severity: match issue.severity {
                    IssueSeverity::Info => PyIssueSeverity::Info,
                    IssueSeverity::Warning => PyIssueSeverity::Warning,
                    IssueSeverity::Error => PyIssueSeverity::Error,
                },
            })
            .collect()
    }

    fn __repr__(&self) -> String {
        "IniValidator(...)".to_string()
    }
}

/// Register ini module functions with Python module
pub fn register_ini(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyIniValidator>()?;
    m.add_class::<PyConfigIssue>()?;
    m.add_class::<PyIssueSeverity>()?;
    Ok(())
}
