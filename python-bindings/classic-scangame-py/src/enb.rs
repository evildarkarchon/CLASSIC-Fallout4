//! PyO3 bindings for ENB detection
//!
//! This module provides Python bindings for the ENB detection functionality
//! in classic-scangame-core.

use classic_scangame_core::{EnbChecker, EnbConfigResult, EnbResult, EnbValidationResult};
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for EnbResult
#[pyclass(name = "EnbResult")]
#[derive(Clone, Debug)]
pub enum PyEnbResult {
    /// ENB fully installed
    Present,
    /// Partial ENB installation
    Partial,
    /// ENB not installed
    NotInstalled,
}

/// Python wrapper for EnbConfigResult
#[pyclass(name = "EnbConfigResult")]
#[derive(Clone, Debug)]
pub enum PyEnbConfigResult {
    /// Config valid and readable
    Valid,
    /// Config not found
    NotFound,
    /// Config exists but unreadable
    Unreadable,
}

/// Python wrapper for EnbValidationResult
#[pyclass(name = "EnbValidationResult")]
#[derive(Clone)]
pub struct PyEnbValidationResult {
    /// Whether ENB binaries are present
    #[pyo3(get)]
    pub binaries: PyEnbResult,
    /// Whether ENB config is valid
    #[pyo3(get)]
    pub config: PyEnbConfigResult,
}

#[pymethods]
impl PyEnbValidationResult {
    /// Check if ENB is present (binaries exist).
    fn is_present(&self) -> bool {
        matches!(self.binaries, PyEnbResult::Present | PyEnbResult::Partial)
    }

    /// Check if ENB is fully configured (binaries + config).
    fn is_fully_configured(&self) -> bool {
        matches!(self.binaries, PyEnbResult::Present)
            && matches!(self.config, PyEnbConfigResult::Valid)
    }

    fn __repr__(&self) -> String {
        format!(
            "EnbValidationResult(binaries={:?}, config={:?})",
            self.binaries, self.config
        )
    }
}

/// Python wrapper for EnbChecker
///
/// Example:
///     >>> checker = EnbChecker("C:/Games/Fallout4")
///     >>> result = checker.validate()
///     >>> if result.is_present():
///     ...     print("ENB detected")
#[pyclass(name = "EnbChecker")]
pub struct PyEnbChecker {
    inner: EnbChecker,
}

#[pymethods]
impl PyEnbChecker {
    #[new]
    fn new(game_path: PathBuf) -> Self {
        Self {
            inner: EnbChecker::new(game_path),
        }
    }

    /// Check if ENB binaries exist.
    fn check_binaries(&self) -> PyEnbResult {
        match self.inner.check_binaries() {
            EnbResult::Present => PyEnbResult::Present,
            EnbResult::Partial => PyEnbResult::Partial,
            EnbResult::NotInstalled => PyEnbResult::NotInstalled,
        }
    }

    /// Check if ENB config exists.
    fn check_config(&self) -> PyEnbConfigResult {
        match self.inner.check_config() {
            EnbConfigResult::Valid => PyEnbConfigResult::Valid,
            EnbConfigResult::NotFound => PyEnbConfigResult::NotFound,
            EnbConfigResult::Unreadable => PyEnbConfigResult::Unreadable,
        }
    }

    /// Perform combined validation.
    fn validate(&self) -> PyEnbValidationResult {
        let result = self.inner.validate();
        PyEnbValidationResult {
            binaries: match result.binaries {
                EnbResult::Present => PyEnbResult::Present,
                EnbResult::Partial => PyEnbResult::Partial,
                EnbResult::NotInstalled => PyEnbResult::NotInstalled,
            },
            config: match result.config {
                EnbConfigResult::Valid => PyEnbConfigResult::Valid,
                EnbConfigResult::NotFound => PyEnbConfigResult::NotFound,
                EnbConfigResult::Unreadable => PyEnbConfigResult::Unreadable,
            },
        }
    }

    /// Format a user-friendly message.
    fn format_message(&self, result: &PyEnbValidationResult) -> String {
        let rust_result = EnbValidationResult {
            binaries: match result.binaries {
                PyEnbResult::Present => EnbResult::Present,
                PyEnbResult::Partial => EnbResult::Partial,
                PyEnbResult::NotInstalled => EnbResult::NotInstalled,
            },
            config: match result.config {
                PyEnbConfigResult::Valid => EnbConfigResult::Valid,
                PyEnbConfigResult::NotFound => EnbConfigResult::NotFound,
                PyEnbConfigResult::Unreadable => EnbConfigResult::Unreadable,
            },
        };
        self.inner.format_message(&rust_result)
    }

    fn __repr__(&self) -> String {
        "EnbChecker(...)".to_string()
    }
}

/// Convenience function to check ENB installation.
#[pyfunction]
pub fn check_enb(game_path: PathBuf) -> PyEnbValidationResult {
    let checker = PyEnbChecker::new(game_path);
    checker.validate()
}

/// Register ENB module functions with Python module.
pub fn register_enb(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyEnbChecker>()?;
    m.add_class::<PyEnbResult>()?;
    m.add_class::<PyEnbConfigResult>()?;
    m.add_class::<PyEnbValidationResult>()?;
    m.add_function(wrap_pyfunction!(check_enb, m)?)?;
    Ok(())
}
