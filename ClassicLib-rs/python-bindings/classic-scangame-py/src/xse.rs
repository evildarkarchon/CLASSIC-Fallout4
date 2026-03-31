//! PyO3 bindings for XSE (F4SE/SKSE) plugin validation

use classic_scangame_core::{AddressLibInfo, GameVersion, ValidationResult, XseChecker};
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for GameVersion
#[pyclass(name = "GameVersion")]
#[derive(Clone, Debug)]
pub enum PyGameVersion {
    /// Null/unknown game version
    Null,
    /// Original game version
    Original,
    /// Next-gen/updated game version
    NextGen,
    /// Anniversary Edition game version
    AnniversaryEdition,
    /// VR game version
    Vr,
}

/// Python wrapper for ValidationResult
#[pyclass(name = "ValidationResult")]
#[derive(Clone)]
pub enum PyValidationResult {
    /// XSE plugin version matches game version
    CorrectVersion,
    /// XSE plugin version does not match game version
    WrongVersion,
    /// XSE plugin not found
    NotFound,
    /// Could not detect XSE plugin version
    VersionNotDetected,
    /// F4SE/SKSE plugins directory not found
    PluginsPathNotFound,
}

/// Python wrapper for AddressLibInfo
#[pyclass(name = "AddressLibInfo")]
#[derive(Clone)]
pub struct PyAddressLibInfo {
    /// Version constant
    #[pyo3(get)]
    pub version: PyGameVersion,
    /// Filename of the Address Library file
    #[pyo3(get)]
    pub filename: String,
    /// Human-readable description
    #[pyo3(get)]
    pub description: String,
    /// Nexus Mods URL for download
    #[pyo3(get)]
    pub url: String,
}

#[pymethods]
impl PyAddressLibInfo {
    #[staticmethod]
    fn vr() -> Self {
        let info = AddressLibInfo::vr();
        Self {
            version: PyGameVersion::Vr,
            filename: info.filename,
            description: info.description,
            url: info.url,
        }
    }

    #[staticmethod]
    fn original() -> Self {
        let info = AddressLibInfo::original();
        Self {
            version: PyGameVersion::Original,
            filename: info.filename,
            description: info.description,
            url: info.url,
        }
    }

    #[staticmethod]
    fn next_gen() -> Self {
        let info = AddressLibInfo::next_gen();
        Self {
            version: PyGameVersion::NextGen,
            filename: info.filename,
            description: info.description,
            url: info.url,
        }
    }

    #[staticmethod]
    fn anniversary_edition() -> Self {
        let info = AddressLibInfo::anniversary_edition();
        Self {
            version: PyGameVersion::AnniversaryEdition,
            filename: info.filename,
            description: info.description,
            url: info.url,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "AddressLibInfo(version={:?}, filename='{}')",
            self.version, self.filename
        )
    }
}

/// Python wrapper for XseChecker
///
/// Validates Address Library installation for F4SE/SKSE plugins.
///
/// Example:
///     >>> # Simplest usage (defaults to Original mode)
///     >>> checker = XseChecker("/path/to/plugins")
///     >>> result = checker.check()
///     >>> message = checker.validate()
///     >>> print(message)
///     >>>
///     >>> # Or specify game version explicitly
///     >>> checker = XseChecker(
///     ...     "/path/to/plugins",
///     ...     game_version=GameVersion.NextGen
///     ... )
#[pyclass(name = "XseChecker")]
pub struct PyXseChecker {
    inner: XseChecker,
}

fn to_core_game_version(game_version: PyGameVersion) -> GameVersion {
    match game_version {
        PyGameVersion::Null => GameVersion::Null,
        PyGameVersion::Original => GameVersion::Original,
        PyGameVersion::NextGen => GameVersion::NextGen,
        PyGameVersion::AnniversaryEdition => GameVersion::AnniversaryEdition,
        PyGameVersion::Vr => GameVersion::Vr,
    }
}

#[pymethods]
impl PyXseChecker {
    #[new]
    #[pyo3(signature = (plugins_path, game_version=PyGameVersion::Original))]
    fn new(plugins_path: PathBuf, game_version: PyGameVersion) -> PyResult<Self> {
        let version = to_core_game_version(game_version);
        let checker = XseChecker::new(plugins_path, version).map_err(crate::to_pyerr)?;

        Ok(Self { inner: checker })
    }

    /// Perform the validation check
    ///
    /// Returns:
    ///     ValidationResult indicating the status of the Address Library installation
    fn check(&self) -> PyValidationResult {
        match self.inner.check() {
            ValidationResult::CorrectVersion => PyValidationResult::CorrectVersion,
            ValidationResult::WrongVersion => PyValidationResult::WrongVersion,
            ValidationResult::NotFound => PyValidationResult::NotFound,
            ValidationResult::VersionNotDetected => PyValidationResult::VersionNotDetected,
            ValidationResult::PluginsPathNotFound => PyValidationResult::PluginsPathNotFound,
        }
    }

    /// Perform validation and return formatted message
    ///
    /// Returns:
    ///     Formatted message string with validation result
    fn validate(&self) -> String {
        self.inner.validate()
    }

    fn __repr__(&self) -> String {
        "XseChecker(...)".to_string()
    }
}

/// Convenience function to validate XSE plugins without creating checker instance
///
/// Args:
///     plugins_path: Path to F4SE/SKSE plugins directory
///     game_version: Detected game version
///
/// Returns:
///     Formatted validation message
#[pyfunction]
#[pyo3(signature = (plugins_path, game_version))]
pub fn check_xse_plugins(plugins_path: PathBuf, game_version: PyGameVersion) -> PyResult<String> {
    let checker = PyXseChecker::new(plugins_path, game_version)?;
    Ok(checker.validate())
}

/// Register xse module functions with Python module
pub fn register_xse(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyXseChecker>()?;
    m.add_class::<PyGameVersion>()?;
    m.add_class::<PyValidationResult>()?;
    m.add_class::<PyAddressLibInfo>()?;
    m.add_function(wrap_pyfunction!(check_xse_plugins, m)?)?;
    Ok(())
}
