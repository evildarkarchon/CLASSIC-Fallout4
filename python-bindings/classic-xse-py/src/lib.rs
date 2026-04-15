//! Python bindings for classic-xse-core.
//!
//! This module provides Python access to Script Extender (XSE) utilities,
//! including detection, version checking, and status information.

use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use std::path::PathBuf;

/// XSE type enumeration for Python.
#[pyclass(module = "classic_xse", name = "XseType", from_py_object)]
#[derive(Clone)]
pub struct PyXseType {
    inner: classic_xse_core::XseType,
}

#[pymethods]
impl PyXseType {
    /// Get the XSE type name as a string.
    ///
    /// # Examples
    ///
    /// ```python
    /// import classic_xse
    ///
    /// xse = classic_xse.XseType.f4se()
    /// assert xse.as_str() == "F4SE"
    /// ```
    fn as_str(&self) -> &str {
        self.inner.as_str()
    }

    /// Get the loader executable name.
    ///
    /// # Examples
    ///
    /// ```python
    /// import classic_xse
    ///
    /// xse = classic_xse.XseType.f4se()
    /// assert xse.loader_name() == "f4se_loader.exe"
    /// ```
    fn loader_name(&self) -> &str {
        self.inner.loader_name()
    }

    /// Get the DLL prefix for this XSE type.
    ///
    /// # Examples
    ///
    /// ```python
    /// import classic_xse
    ///
    /// xse = classic_xse.XseType.f4se()
    /// assert xse.dll_prefix() == "f4se_"
    /// ```
    fn dll_prefix(&self) -> &str {
        self.inner.dll_prefix()
    }

    /// Create an F4SE type.
    #[staticmethod]
    fn f4se() -> Self {
        Self {
            inner: classic_xse_core::XseType::F4SE,
        }
    }

    /// Create an F4SEVR type.
    #[staticmethod]
    fn f4sevr() -> Self {
        Self {
            inner: classic_xse_core::XseType::F4SEVR,
        }
    }

    /// Create an SKSE type.
    #[staticmethod]
    fn skse() -> Self {
        Self {
            inner: classic_xse_core::XseType::SKSE,
        }
    }

    /// Create an SKSE64 type.
    #[staticmethod]
    fn skse64() -> Self {
        Self {
            inner: classic_xse_core::XseType::SKSE64,
        }
    }

    /// Create an SKSEVR type.
    #[staticmethod]
    fn sksevr() -> Self {
        Self {
            inner: classic_xse_core::XseType::SKSEVR,
        }
    }

    /// Create an SFSE type.
    #[staticmethod]
    fn sfse() -> Self {
        Self {
            inner: classic_xse_core::XseType::SFSE,
        }
    }

    /// Compare XSE types for equality.
    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    /// String representation.
    fn __str__(&self) -> String {
        self.inner.as_str().to_string()
    }

    /// Debug representation.
    fn __repr__(&self) -> String {
        format!("XseType.{}()", self.inner.as_str().to_lowercase())
    }
}

/// XSE installation information for Python.
#[pyclass(module = "classic_xse", name = "XseInfo", from_py_object)]
#[derive(Clone)]
pub struct PyXseInfo {
    inner: classic_xse_core::XseInfo,
}

#[pymethods]
impl PyXseInfo {
    /// Create a new XseInfo.
    ///
    /// # Arguments
    ///
    /// * `xse_type` - The XSE type
    /// * `path` - The installation path
    ///
    /// # Examples
    ///
    /// ```python
    /// import classic_xse
    ///
    /// info = classic_xse.XseInfo(classic_xse.XseType.f4se(), "C:\\Games\\Fallout4")
    /// assert info.xse_type().as_str() == "F4SE"
    /// ```
    #[new]
    fn new(xse_type: PyXseType, path: String) -> Self {
        Self {
            inner: classic_xse_core::XseInfo::new(xse_type.inner, PathBuf::from(path)),
        }
    }

    /// Get the XSE type.
    fn xse_type(&self) -> PyXseType {
        PyXseType {
            inner: self.inner.xse_type,
        }
    }

    /// Get the installation path.
    fn path(&self) -> String {
        self.inner.path.display().to_string()
    }

    /// Get the detected version.
    ///
    /// # Returns
    ///
    /// A tuple of (major, minor, patch) if version was detected, None otherwise.
    fn version(&self) -> Option<(u64, u64, u64)> {
        self.inner
            .version
            .as_ref()
            .map(|v| (v.major, v.minor, v.patch))
    }

    /// Check if XSE is installed.
    fn installed(&self) -> bool {
        self.inner.installed
    }

    /// Check if the XSE loader executable exists.
    fn check_installed(&self) -> bool {
        self.inner.check_installed()
    }

    /// Get the full path to the loader executable.
    fn loader_path(&self) -> String {
        self.inner.loader_path().display().to_string()
    }

    /// String representation.
    fn __str__(&self) -> String {
        let version_str = self
            .inner
            .version
            .as_ref()
            .map_or("Unknown".to_string(), |v| v.to_string());
        format!(
            "XseInfo(type='{}', installed={}, version='{}')",
            self.inner.xse_type.as_str(),
            self.inner.installed,
            version_str
        )
    }

    /// Debug representation.
    fn __repr__(&self) -> String {
        self.__str__()
    }
}

/// Parse an XSE type from a string.
///
/// # Arguments
///
/// * `type_name` - The XSE type name (case-insensitive)
///
/// # Returns
///
/// The corresponding XseType.
///
/// # Raises
///
/// * `ValueError` - If the type name is invalid
///
/// # Examples
///
/// ```python
/// import classic_xse
///
/// xse = classic_xse.parse_xse_type("f4se")
/// assert xse.as_str() == "F4SE"
///
/// xse = classic_xse.parse_xse_type("SKSE64")
/// assert xse.as_str() == "SKSE64"
/// ```
#[pyfunction]
fn parse_xse_type(type_name: &str) -> PyResult<PyXseType> {
    type_name
        .parse::<classic_xse_core::XseType>()
        .map(|inner| PyXseType { inner })
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Detect XSE version from a loader executable.
///
/// # Arguments
///
/// * `loader_path` - Path to the XSE loader executable
/// * `xse_type` - The XSE type to detect
///
/// # Returns
///
/// The detected version as a tuple of (major, minor, patch).
///
/// # Raises
///
/// * `IOError` - If the loader doesn't exist or version cannot be detected
///
/// # Examples
///
/// ```python
/// import classic_xse
///
/// try:
///     version = classic_xse.detect_xse_version("f4se_loader.exe", classic_xse.XseType.f4se())
///     print(f"F4SE version: {version}")
/// except IOError as e:
///     print(f"Detection failed: {e}")
/// ```
#[pyfunction]
fn detect_xse_version(loader_path: &str, xse_type: PyXseType) -> PyResult<(u64, u64, u64)> {
    classic_xse_core::detect_xse_version(&PathBuf::from(loader_path), xse_type.inner)
        .map(|v| (v.major, v.minor, v.patch))
        .map_err(|e| PyIOError::new_err(e.to_string()))
}

/// Check if XSE is installed in a directory.
///
/// # Arguments
///
/// * `game_path` - The game installation directory
/// * `xse_type` - The XSE type to check
///
/// # Returns
///
/// True if the XSE loader executable exists.
///
/// # Examples
///
/// ```python
/// import classic_xse
///
/// if classic_xse.is_xse_installed("C:\\Games\\Fallout4", classic_xse.XseType.f4se()):
///     print("F4SE is installed")
/// ```
#[pyfunction]
fn is_xse_installed(game_path: &str, xse_type: PyXseType) -> bool {
    classic_xse_core::is_xse_installed(&PathBuf::from(game_path), xse_type.inner)
}

/// Get XSE information for a game directory.
///
/// # Arguments
///
/// * `game_path` - The game installation directory
/// * `xse_type` - The XSE type to check
///
/// # Returns
///
/// XseInfo with installation and version details.
///
/// # Examples
///
/// ```python
/// import classic_xse
///
/// info = classic_xse.get_xse_info("C:\\Games\\Fallout4", classic_xse.XseType.f4se())
/// if info.installed():
///     print(f"F4SE version: {info.version()}")
/// ```
#[pyfunction]
fn get_xse_info(game_path: &str, xse_type: PyXseType) -> PyXseInfo {
    PyXseInfo {
        inner: classic_xse_core::get_xse_info(&PathBuf::from(game_path), xse_type.inner),
    }
}

/// Python module for XSE utilities.
///
/// This module provides comprehensive Script Extender (XSE) handling for
/// Bethesda games, including version detection, file location, and status checking.
#[pymodule]
fn classic_xse(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register classes
    m.add_class::<PyXseType>()?;
    m.add_class::<PyXseInfo>()?;

    // XSE type parsing
    m.add_function(wrap_pyfunction!(parse_xse_type, m)?)?;

    // Version detection
    m.add_function(wrap_pyfunction!(detect_xse_version, m)?)?;

    // Installation checking
    m.add_function(wrap_pyfunction!(is_xse_installed, m)?)?;
    m.add_function(wrap_pyfunction!(get_xse_info, m)?)?;

    // Module metadata
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__doc__", "Script Extender (XSE) utilities for CLASSIC")?;

    Ok(())
}
