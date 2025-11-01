//! Python bindings for classic-path-core.
//!
//! This crate provides Python bindings for all path management functionality,
//! including game path detection, documents path management, path validation,
//! backup operations, and configuration checking.
//!
//! # Python Usage
//!
//! ```python
//! from classic_path import PathValidator
//!
//! # Validate a path
//! if PathValidator.is_valid_path("C:\\Games\\Fallout4"):
//!     print("Path exists!")
//!
//! # Check if path is restricted
//! if not PathValidator.is_restricted_path("C:\\Users\\Downloads\\Mods"):
//!     print("Safe for custom scan")
//! ```

use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for path validation utilities.
///
/// Provides static methods for path validation operations.
///
/// # Python Examples
///
/// ```python
/// from classic_path import PathValidator
///
/// # Check if path exists
/// exists = PathValidator.is_valid_path("C:\\Games\\Fallout4")
///
/// # Check if path is restricted for custom scans
/// restricted = PathValidator.is_restricted_path("C:\\Windows")
///
/// # Validate a custom scan path
/// try:
///     PathValidator.validate_custom_scan_path("C:\\Users\\Downloads\\Mods")
///     print("Path is valid for scanning")
/// except Exception as e:
///     print(f"Validation failed: {e}")
/// ```
#[pyclass]
pub struct PathValidator;

#[pymethods]
impl PathValidator {
    /// Check if a path exists in the filesystem.
    ///
    /// # Arguments
    ///
    /// * `path` - The path to check (string or PathLike)
    ///
    /// # Returns
    ///
    /// `True` if the path exists, `False` otherwise.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import PathValidator
    ///
    /// if PathValidator.is_valid_path("C:\\Games\\Fallout4"):
    ///     print("Game directory exists")
    /// ```
    #[staticmethod]
    fn is_valid_path(path: String) -> bool {
        classic_path_core::is_valid_path(&PathBuf::from(path))
    }

    /// Check if a path is restricted for custom scans.
    ///
    /// Restricted paths include system directories, root directories,
    /// and the game installation directory.
    ///
    /// # Arguments
    ///
    /// * `path` - The path to check (string or PathLike)
    ///
    /// # Returns
    ///
    /// `True` if the path is restricted, `False` if it's safe for custom scans.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import PathValidator
    ///
    /// if PathValidator.is_restricted_path("C:\\Windows"):
    ///     print("Cannot scan Windows directory")
    /// ```
    #[staticmethod]
    fn is_restricted_path(path: String) -> bool {
        classic_path_core::is_restricted_path(&PathBuf::from(path))
    }

    /// Validate a custom scan path.
    ///
    /// Ensures the path exists, is a directory, and is not restricted.
    ///
    /// # Arguments
    ///
    /// * `path` - The path to validate for custom scanning
    ///
    /// # Raises
    ///
    /// * `ValueError` - If the path is invalid or restricted
    /// * `FileNotFoundError` - If the path does not exist
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import PathValidator
    ///
    /// try:
    ///     PathValidator.validate_custom_scan_path("C:\\Users\\Downloads\\Mods")
    ///     print("Path validated successfully")
    /// except ValueError as e:
    ///     print(f"Validation failed: {e}")
    /// ```
    #[staticmethod]
    fn validate_custom_scan_path(path: String) -> PyResult<()> {
        classic_path_core::validate_custom_scan_path(&PathBuf::from(path))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    /// Validate that required files exist in a directory.
    ///
    /// # Arguments
    ///
    /// * `directory` - The directory to check
    /// * `required_files` - List of file names that must exist
    ///
    /// # Raises
    ///
    /// * `FileNotFoundError` - If directory or any required file does not exist
    /// * `ValueError` - If the path is not a directory
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import PathValidator
    ///
    /// try:
    ///     PathValidator.validate_required_files(
    ///         "C:\\Games\\Fallout4",
    ///         ["Fallout4.exe", "Data"]
    ///     )
    ///     print("All required files found")
    /// except FileNotFoundError as e:
    ///     print(f"Missing file: {e}")
    /// ```
    #[staticmethod]
    fn validate_required_files(directory: String, required_files: Vec<String>) -> PyResult<()> {
        classic_path_core::validate_required_files(
            &PathBuf::from(directory),
            &required_files,
        )
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(e.to_string()))
    }

    /// Validate a settings path with optional required files.
    ///
    /// # Arguments
    ///
    /// * `path` - The path to validate
    /// * `setting_name` - Name of the setting (for error messages)
    /// * `required_files` - Optional list of required file names
    ///
    /// # Raises
    ///
    /// * `ValueError` - If validation fails
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import PathValidator
    ///
    /// try:
    ///     PathValidator.validate_settings_path(
    ///         "C:\\Games\\Fallout4",
    ///         "Game Path",
    ///         ["Fallout4.exe"]
    ///     )
    /// except ValueError as e:
    ///     print(f"Invalid setting: {e}")
    /// ```
    #[staticmethod]
    fn validate_settings_path(
        path: String,
        setting_name: String,
        required_files: Option<Vec<String>>,
    ) -> PyResult<()> {
        classic_path_core::validate_settings_path(
            &PathBuf::from(path),
            &setting_name,
            required_files.as_deref(),
        )
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    /// Validate all common settings paths.
    ///
    /// # Arguments
    ///
    /// * `game_path` - Game installation path to validate
    /// * `docs_path` - Documents folder path to validate
    /// * `custom_scan_path` - Optional custom scan path
    /// * `game_exe` - Game executable name (e.g., "Fallout4.exe")
    ///
    /// # Raises
    ///
    /// * `ValueError` - If any validation fails
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import PathValidator
    ///
    /// try:
    ///     PathValidator.validate_settings_paths(
    ///         "C:\\Games\\Fallout4",
    ///         "C:\\Users\\Name\\Documents\\My Games\\Fallout4",
    ///         None,
    ///         "Fallout4.exe"
    ///     )
    ///     print("All paths validated")
    /// except ValueError as e:
    ///     print(f"Validation failed: {e}")
    /// ```
    #[staticmethod]
    fn validate_settings_paths(
        game_path: String,
        docs_path: String,
        custom_scan_path: Option<String>,
        game_exe: String,
    ) -> PyResult<()> {
        let game_path_buf = PathBuf::from(game_path);
        let docs_path_buf = PathBuf::from(docs_path);
        let custom_scan_path_buf = custom_scan_path.map(PathBuf::from);

        classic_path_core::validate_settings_paths(
            &game_path_buf,
            &docs_path_buf,
            custom_scan_path_buf.as_deref(),
            &game_exe,
        )
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }
}

/// Python module for path management.
///
/// This module provides unified path management functionality for CLASSIC:
/// - Path validation (PathValidator)
/// - Game path detection (coming soon)
/// - Documents path management (coming soon)
/// - Backup operations (coming soon)
///
/// # Examples
///
/// ```python
/// import classic_path
///
/// # Validate a path
/// if classic_path.PathValidator.is_valid_path("C:\\Games\\Fallout4"):
///     print("Path exists")
///
/// # Check restrictions
/// if not classic_path.PathValidator.is_restricted_path("C:\\Users\\Downloads"):
///     print("Safe for custom scan")
/// ```
#[pymodule]
fn classic_path(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add the PathValidator class
    m.add_class::<PathValidator>()?;

    // Module metadata
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__doc__", "Python bindings for CLASSIC path management")?;

    Ok(())
}
