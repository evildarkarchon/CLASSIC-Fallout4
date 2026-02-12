//! Python bindings for classic-version-core.
//!
//! This module provides Python access to version detection and parsing utilities.
//! All version handling functionality from the core crate is exposed through
//! Python-friendly wrapper functions.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use semver::Version;
use std::cmp::Ordering;

/// Parse a version string into a semantic version.
///
/// Accepts various formats:
/// - "1.10.163.0" -> Version { major: 1, minor: 10, patch: 163 }
/// - "1.10.163" -> Version { major: 1, minor: 10, patch: 163 }
/// - "1.10" -> Version { major: 1, minor: 10, patch: 0 }
/// - "v1.10.163" -> Version { major: 1, minor: 10, patch: 163 }
///
/// # Arguments
///
/// * `version_str` - The version string to parse
///
/// # Returns
///
/// A tuple of (major, minor, patch) representing the semantic version.
///
/// # Raises
///
/// * `ValueError` - If the version string cannot be parsed
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// version = classic_version.parse_version("1.10.163.0")
/// assert version == (1, 10, 163)
///
/// version = classic_version.parse_version("v1.2.3")
/// assert version == (1, 2, 3)
/// ```
#[pyfunction]
fn parse_version(version_str: &str) -> PyResult<(u64, u64, u64)> {
    classic_version_core::parse_version(version_str)
        .map(|v| (v.major, v.minor, v.patch))
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Try to parse a version string, returning None if parsing fails.
///
/// This is a non-throwing version of `parse_version()` that returns None
/// instead of raising an exception when parsing fails.
///
/// # Arguments
///
/// * `version_str` - The version string to parse
///
/// # Returns
///
/// A tuple of (major, minor, patch) if successful, None otherwise.
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// version = classic_version.try_parse_version("1.10.163.0")
/// assert version == (1, 10, 163)
///
/// version = classic_version.try_parse_version("invalid")
/// assert version is None
/// ```
#[pyfunction]
fn try_parse_version(version_str: &str) -> Option<(u64, u64, u64)> {
    classic_version_core::try_parse_version(version_str).map(|v| (v.major, v.minor, v.patch))
}

/// Compare two semantic versions.
///
/// # Arguments
///
/// * `v1` - First version tuple (major, minor, patch)
/// * `v2` - Second version tuple (major, minor, patch)
///
/// # Returns
///
/// * `-1` if v1 < v2
/// * `0` if v1 == v2
/// * `1` if v1 > v2
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// result = classic_version.compare_versions((1, 10, 163), (1, 10, 984))
/// assert result == -1  # 1.10.163 < 1.10.984
///
/// result = classic_version.compare_versions((1, 10, 163), (1, 10, 163))
/// assert result == 0
///
/// result = classic_version.compare_versions((1, 10, 984), (1, 10, 163))
/// assert result == 1
/// ```
#[pyfunction]
fn compare_versions(v1: (u64, u64, u64), v2: (u64, u64, u64)) -> i32 {
    let version1 = Version::new(v1.0, v1.1, v1.2);
    let version2 = Version::new(v2.0, v2.1, v2.2);

    match classic_version_core::compare_versions(&version1, &version2) {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    }
}

/// Check if a version is a known Fallout 4 version.
///
/// # Arguments
///
/// * `version` - Version tuple (major, minor, patch)
///
/// # Returns
///
/// True if the version is in the known Fallout 4 versions list.
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// assert classic_version.is_known_fallout4_version((1, 10, 163))
/// assert classic_version.is_known_fallout4_version((1, 10, 984))
/// assert not classic_version.is_known_fallout4_version((9, 9, 9))
/// ```
#[pyfunction]
fn is_known_fallout4_version(version: (u64, u64, u64)) -> bool {
    let v = Version::new(version.0, version.1, version.2);
    classic_version_core::is_known_fallout4_version(&v)
}

/// Check if a version is a known F4SE version.
///
/// # Arguments
///
/// * `version` - Version tuple (major, minor, patch)
///
/// # Returns
///
/// True if the version is in the known F4SE versions list.
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// assert classic_version.is_known_f4se_version((0, 6, 23))
/// assert classic_version.is_known_f4se_version((0, 7, 2))
/// assert not classic_version.is_known_f4se_version((9, 9, 9))
/// ```
#[pyfunction]
fn is_known_f4se_version(version: (u64, u64, u64)) -> bool {
    let v = Version::new(version.0, version.1, version.2);
    classic_version_core::is_known_f4se_version(&v)
}

/// Extract a version from a filename.
///
/// Looks for version patterns like:
/// - "MyMod-v1.2.3.esp"
/// - "SomeMod_1.2.3.ba2"
/// - "Plugin-1.2.esp"
///
/// # Arguments
///
/// * `filename` - The filename to extract version from
///
/// # Returns
///
/// A tuple of (major, minor, patch) if a version is found, None otherwise.
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// version = classic_version.extract_version_from_filename("MyMod-v1.2.3.esp")
/// assert version == (1, 2, 3)
///
/// version = classic_version.extract_version_from_filename("SomeMod_1.2.esp")
/// assert version == (1, 2, 0)
///
/// version = classic_version.extract_version_from_filename("NoVersion.esp")
/// assert version is None
/// ```
#[pyfunction]
fn extract_version_from_filename(filename: &str) -> Option<(u64, u64, u64)> {
    classic_version_core::extract_version_from_filename(filename)
        .map(|v| (v.major, v.minor, v.patch))
}

/// Extract a version from log content.
///
/// Searches for version patterns in log file content, typically looking
/// for patterns like "Version: 1.10.163.0" or similar.
///
/// # Arguments
///
/// * `log_content` - The log file content to search
///
/// # Returns
///
/// A tuple of (major, minor, patch) if a version is found, None otherwise.
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// log = "Game Version: 1.10.163.0\\nOther info..."
/// version = classic_version.extract_version_from_log(log)
/// assert version == (1, 10, 163)
/// ```
#[pyfunction]
fn extract_version_from_log(log_content: &str) -> Option<(u64, u64, u64)> {
    classic_version_core::extract_version_from_log(log_content).map(|v| (v.major, v.minor, v.patch))
}

/// Extract all versions from a text content.
///
/// Finds all version patterns in the given text and returns them as a list.
///
/// # Arguments
///
/// * `content` - The text content to search for versions
///
/// # Returns
///
/// A list of version tuples (major, minor, patch).
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// content = "Version 1.2.3 and version 4.5.6 found"
/// versions = classic_version.extract_all_versions(content)
/// assert versions == [(1, 2, 3), (4, 5, 6)]
/// ```
#[pyfunction]
fn extract_all_versions(content: &str) -> Vec<(u64, u64, u64)> {
    classic_version_core::extract_all_versions(content)
        .into_iter()
        .map(|v| (v.major, v.minor, v.patch))
        .collect()
}

/// Format a version with optional prefix.
///
/// # Arguments
///
/// * `version` - Version tuple (major, minor, patch)
/// * `prefix` - Optional prefix string (default: "v"). Use empty string "" for no prefix.
///
/// # Returns
///
/// Formatted version string like "v1.10.163".
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// formatted = classic_version.format_version((1, 10, 163))
/// assert formatted == "v1.10.163"
///
/// formatted = classic_version.format_version((1, 10, 163), prefix="Version ")
/// assert formatted == "Version 1.10.163"
///
/// formatted = classic_version.format_version((1, 10, 163), prefix="")
/// assert formatted == "1.10.163"
/// ```
#[pyfunction]
#[pyo3(signature = (version, prefix=None))]
fn format_version(version: (u64, u64, u64), prefix: Option<&str>) -> String {
    let v = Version::new(version.0, version.1, version.2);
    // Default to "v" prefix if None is provided
    let actual_prefix = match prefix {
        None => Some("v"),
        Some("") => None, // Empty string means no prefix
        Some(p) => Some(p),
    };
    classic_version_core::format_version(&v, actual_prefix)
}

/// Extract the file version from a PE executable (.exe or .dll).
///
/// Reads the VS_VERSIONINFO resource from a Windows PE file and returns
/// the file version as a 4-part tuple (major, minor, patch, build).
///
/// # Arguments
///
/// * `path` - Path to the PE file (.exe or .dll)
///
/// # Returns
///
/// A tuple of (major, minor, patch, build) version components.
///
/// # Raises
///
/// * `ValueError` - If the file is not a valid PE file or has no version info
/// * `FileNotFoundError` - If the file doesn't exist or has wrong extension
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// version = classic_version.extract_pe_version("C:\\Windows\\System32\\kernel32.dll")
/// print(f"Version: {version[0]}.{version[1]}.{version[2]}.{version[3]}")
/// ```
#[pyfunction]
fn extract_pe_version(path: &str) -> PyResult<(u16, u16, u16, u16)> {
    use classic_version_core::pe_version;

    pe_version::extract_pe_version(std::path::Path::new(path)).map_err(|e| match &e {
        pe_version::PeVersionError::InvalidPath(_) | pe_version::PeVersionError::IoError { .. } => {
            PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(e.to_string())
        }
        _ => PyValueError::new_err(e.to_string()),
    })
}

/// Check if a path points to a valid executable or DLL file.
///
/// Validates that the path exists, is a file, and has .exe or .dll extension.
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// True if the path is a valid executable or DLL.
///
/// # Examples
///
/// ```python
/// import classic_version
///
/// assert classic_version.is_valid_pe_path("C:\\Windows\\System32\\kernel32.dll")
/// assert not classic_version.is_valid_pe_path("readme.txt")
/// ```
#[pyfunction]
fn is_valid_pe_path(path: &str) -> bool {
    classic_version_core::pe_version::is_valid_executable_path(std::path::Path::new(path))
}

/// Python module for version utilities.
///
/// This module provides comprehensive version handling for CLASSIC, including:
/// - Version parsing from strings
/// - Version comparison
/// - Version extraction from filenames and logs
/// - Version validation against known versions
/// - PE file version extraction
#[pymodule]
fn classic_version(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Version parsing
    m.add_function(wrap_pyfunction!(parse_version, m)?)?;
    m.add_function(wrap_pyfunction!(try_parse_version, m)?)?;

    // Version comparison
    m.add_function(wrap_pyfunction!(compare_versions, m)?)?;
    m.add_function(wrap_pyfunction!(is_known_fallout4_version, m)?)?;
    m.add_function(wrap_pyfunction!(is_known_f4se_version, m)?)?;

    // Version extraction
    m.add_function(wrap_pyfunction!(extract_version_from_filename, m)?)?;
    m.add_function(wrap_pyfunction!(extract_version_from_log, m)?)?;
    m.add_function(wrap_pyfunction!(extract_all_versions, m)?)?;

    // Version formatting
    m.add_function(wrap_pyfunction!(format_version, m)?)?;

    // PE version extraction
    m.add_function(wrap_pyfunction!(extract_pe_version, m)?)?;
    m.add_function(wrap_pyfunction!(is_valid_pe_path, m)?)?;

    // Module metadata
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add(
        "__doc__",
        "Version detection and parsing utilities for CLASSIC",
    )?;

    Ok(())
}
