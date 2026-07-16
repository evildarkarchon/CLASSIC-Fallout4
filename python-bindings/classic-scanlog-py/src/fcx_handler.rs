//! Python projection of FCX configuration issues returned by a scan run.

use classic_scanlog_core::ConfigIssue;
use pyo3::prelude::*;

/// Python wrapper for one run-scoped FCX configuration issue.
#[pyclass(name = "ConfigIssue", from_py_object)]
#[derive(Clone)]
pub struct PyConfigIssue {
    inner: ConfigIssue,
}

#[pymethods]
impl PyConfigIssue {
    /// Creates a configuration issue value for Python callers and tests.
    #[new]
    #[pyo3(signature = (file_path, section, setting, current_value, recommended_value, description, severity = "warning".to_string()))]
    pub fn new(
        file_path: String,
        section: Option<String>,
        setting: String,
        current_value: String,
        recommended_value: String,
        description: String,
        severity: String,
    ) -> Self {
        Self {
            inner: ConfigIssue::new(
                file_path,
                section,
                setting,
                current_value,
                recommended_value,
                description,
                severity,
            ),
        }
    }

    /// Returns the path to the configuration file.
    #[getter]
    pub fn file_path(&self) -> String {
        self.inner.file_path.clone()
    }

    /// Returns the INI section name when the file is sectioned.
    #[getter]
    pub fn section(&self) -> Option<String> {
        self.inner.section.clone()
    }

    /// Returns the setting or key name.
    #[getter]
    pub fn setting(&self) -> String {
        self.inner.setting.clone()
    }

    /// Returns the value observed in the file.
    #[getter]
    pub fn current_value(&self) -> String {
        self.inner.current_value.clone()
    }

    /// Returns the recommended replacement value.
    #[getter]
    pub fn recommended_value(&self) -> String {
        self.inner.recommended_value.clone()
    }

    /// Returns the human-readable issue description.
    #[getter]
    pub fn description(&self) -> String {
        self.inner.description.clone()
    }

    /// Returns the stable severity label.
    #[getter]
    pub fn severity(&self) -> String {
        self.inner.severity.clone()
    }

    /// Formats the issue as a human-readable report fragment.
    pub fn format_report(&self) -> String {
        self.inner.format_report()
    }

    /// Returns a compact diagnostic representation.
    pub fn __repr__(&self) -> String {
        format!(
            "ConfigIssue(file='{}', section={:?}, setting='{}', current='{}', recommended='{}')",
            self.inner.file_path,
            self.inner.section,
            self.inner.setting,
            self.inner.current_value,
            self.inner.recommended_value
        )
    }
}

impl From<ConfigIssue> for PyConfigIssue {
    fn from(issue: ConfigIssue) -> Self {
        Self { inner: issue }
    }
}
