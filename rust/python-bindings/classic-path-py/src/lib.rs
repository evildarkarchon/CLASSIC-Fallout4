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

/// Python wrapper for game path detection.
///
/// Provides multi-strategy game path detection using registry queries,
/// XSE log parsing, and cached paths.
///
/// # Python Examples
///
/// ```python
/// from classic_path import GamePathFinder
///
/// # Create finder for Fallout 4
/// finder = GamePathFinder.new(
///     "Fallout4.exe",
///     "f4se_loader.exe",
///     "Fallout4",
///     False  # not VR
/// )
///
/// # Find game path (tries cache, registry, XSE log)
/// game_path = finder.find_game_path(cached_path=None, xse_log_path=None)
///
/// # Parse XSE log to find game path
/// game_path = GamePathFinder.parse_xse_log("C:\\Users\\...\\F4SE\\f4se.log")
/// ```
#[pyclass]
pub struct GamePathFinder {
    inner: classic_path_core::GamePathFinder,
}

#[pymethods]
impl GamePathFinder {
    /// Create a new GamePathFinder.
    ///
    /// # Arguments
    ///
    /// * `game_exe` - The game executable name (e.g., "Fallout4.exe")
    /// * `xse_loader` - Optional XSE loader name (e.g., "f4se_loader.exe", or None)
    /// * `game_name` - Game name for registry queries (e.g., "Fallout4")
    /// * `is_vr` - Whether this is a VR version
    ///
    /// # Returns
    ///
    /// A new GamePathFinder instance.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import GamePathFinder
    ///
    /// # Standard Fallout 4
    /// finder = GamePathFinder.new("Fallout4.exe", "f4se_loader.exe", "Fallout4", False)
    ///
    /// # Fallout 4 VR
    /// finder_vr = GamePathFinder.new("Fallout4VR.exe", None, "Fallout4", True)
    /// ```
    #[new]
    fn new(
        game_exe: String,
        xse_loader: Option<String>,
        game_name: String,
        is_vr: bool,
    ) -> Self {
        Self {
            inner: classic_path_core::GamePathFinder::new(game_exe, xse_loader, game_name, is_vr),
        }
    }

    /// Find the game installation path using multiple strategies.
    ///
    /// Attempts to find the game path in this order:
    /// 1. Use cached path if provided and valid
    /// 2. Query Windows registry (Windows only)
    /// 3. Parse XSE log file if path provided
    /// 4. Return error if all strategies fail
    ///
    /// # Arguments
    ///
    /// * `cached_path` - Optional cached path from settings (None if not cached)
    /// * `xse_log_path` - Optional path to XSE log file (None to skip)
    ///
    /// # Returns
    ///
    /// The validated game installation path as a string.
    ///
    /// # Raises
    ///
    /// * `FileNotFoundError` - If game not found by any method
    /// * `ValueError` - If path validation fails
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import GamePathFinder
    ///
    /// finder = GamePathFinder.new("Fallout4.exe", None, "Fallout4", False)
    ///
    /// # Try with cached path
    /// try:
    ///     path = finder.find_game_path(cached_path="C:\\Games\\Fallout4")
    ///     print(f"Game found at: {path}")
    /// except FileNotFoundError:
    ///     print("Game not found")
    /// ```
    fn find_game_path(
        &self,
        cached_path: Option<String>,
        xse_log_path: Option<String>,
    ) -> PyResult<String> {
        let cached = cached_path.as_ref().map(|s| PathBuf::from(s));
        let xse_log = xse_log_path.as_ref().map(|s| PathBuf::from(s));

        self.inner
            .find_game_path(cached.as_deref(), xse_log.as_deref())
            .map(|p| p.display().to_string())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(e.to_string()))
    }

    /// Validate that a path is a valid game installation directory.
    ///
    /// Checks that:
    /// 1. The path exists and is a directory
    /// 2. The game executable exists
    /// 3. The XSE loader exists (if configured)
    ///
    /// # Arguments
    ///
    /// * `path` - The path to validate (string or PathLike)
    ///
    /// # Raises
    ///
    /// * `ValueError` - If validation fails
    /// * `FileNotFoundError` - If path or required files don't exist
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import GamePathFinder
    ///
    /// finder = GamePathFinder.new("Fallout4.exe", None, "Fallout4", False)
    ///
    /// try:
    ///     finder.validate_game_path("C:\\Games\\Fallout4")
    ///     print("Path is valid")
    /// except ValueError as e:
    ///     print(f"Validation failed: {e}")
    /// ```
    fn validate_game_path(&self, path: String) -> PyResult<()> {
        self.inner
            .validate_game_path(&PathBuf::from(path))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    /// Get the name of the game executable.
    ///
    /// # Returns
    ///
    /// The game executable name (e.g., "Fallout4.exe").
    #[getter]
    fn game_exe(&self) -> String {
        self.inner.game_exe().to_string()
    }

    /// Get the name of the XSE loader executable.
    ///
    /// # Returns
    ///
    /// The XSE loader name if configured, or None.
    #[getter]
    fn xse_loader(&self) -> Option<String> {
        self.inner.xse_loader().map(|s| s.to_string())
    }

    /// Check if this is a VR version of the game.
    ///
    /// # Returns
    ///
    /// True if this is a VR version, False otherwise.
    #[getter]
    fn is_vr(&self) -> bool {
        self.inner.is_vr()
    }

    /// Parse XSE log file to extract game installation path.
    ///
    /// This is a static method that can be called without creating a GamePathFinder instance.
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the XSE log file (e.g., "f4se.log")
    ///
    /// # Returns
    ///
    /// The game installation path extracted from the log.
    ///
    /// # Raises
    ///
    /// * `FileNotFoundError` - If log file doesn't exist or can't be read
    /// * `ValueError` - If log doesn't contain plugin directory line
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import GamePathFinder
    ///
    /// log_path = "C:\\Users\\Name\\Documents\\My Games\\Fallout4\\F4SE\\f4se.log"
    /// try:
    ///     game_path = GamePathFinder.parse_xse_log(log_path)
    ///     print(f"Game installed at: {game_path}")
    /// except ValueError:
    ///     print("Could not parse XSE log")
    /// ```
    #[staticmethod]
    fn parse_xse_log(log_path: String) -> PyResult<String> {
        classic_path_core::parse_xse_log(&PathBuf::from(log_path))
            .map(|p| p.display().to_string())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }
}

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

/// Python wrapper for documents path detection.
///
/// Provides multi-strategy documents path detection using registry queries,
/// home directories, and cached paths.
///
/// # Python Examples
///
/// ```python
/// from classic_path import DocsPathFinder
///
/// # Create finder for Fallout 4
/// finder = DocsPathFinder.new("My Games\\Fallout4")
///
/// # Find documents path (tries cache, registry, etc.)
/// docs_path = finder.find_docs_path(cached_path=None)
///
/// # Validate required INI files
/// finder.validate_ini_files(docs_path, ["Fallout4.ini", "Fallout4Prefs.ini"])
/// ```
#[pyclass]
pub struct DocsPathFinder {
    inner: classic_path_core::DocsPathFinder,
}

#[pymethods]
impl DocsPathFinder {
    /// Create a new DocsPathFinder.
    ///
    /// # Arguments
    ///
    /// * `relative_path` - Path relative to documents folder (e.g., "My Games\\Fallout4")
    ///
    /// # Returns
    ///
    /// A new DocsPathFinder instance.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import DocsPathFinder
    ///
    /// # For Fallout 4
    /// finder = DocsPathFinder.new("My Games\\Fallout4")
    ///
    /// # For Skyrim
    /// finder_skyrim = DocsPathFinder.new("My Games\\Skyrim")
    /// ```
    #[new]
    fn new(relative_path: String) -> Self {
        Self {
            inner: classic_path_core::DocsPathFinder::new(relative_path),
        }
    }

    /// Find the documents folder path using multiple strategies.
    ///
    /// Attempts to find the documents path in this order:
    /// 1. Use cached path if provided and valid
    /// 2. Query Windows registry (Windows only)
    /// 3. Use home directory (Linux)
    /// 4. Return error if all strategies fail
    ///
    /// # Arguments
    ///
    /// * `cached_path` - Optional cached path from settings (None if not cached)
    ///
    /// # Returns
    ///
    /// The validated documents folder path as a string.
    ///
    /// # Raises
    ///
    /// * `FileNotFoundError` - If documents folder not found by any method
    /// * `ValueError` - If path validation fails
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import DocsPathFinder
    ///
    /// finder = DocsPathFinder.new("My Games\\Fallout4")
    ///
    /// # Try with cached path
    /// try:
    ///     path = finder.find_docs_path(cached_path="C:\\Users\\Name\\Documents\\My Games\\Fallout4")
    ///     print(f"Documents found at: {path}")
    /// except FileNotFoundError:
    ///     print("Documents folder not found")
    /// ```
    fn find_docs_path(&self, cached_path: Option<String>) -> PyResult<String> {
        self.inner
            .find_docs_path(cached_path.as_deref())
            .map(|p| p.display().to_string())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(e.to_string()))
    }

    /// Validate that a documents path exists and is a directory.
    ///
    /// # Arguments
    ///
    /// * `path` - The path to validate (string or PathLike)
    ///
    /// # Raises
    ///
    /// * `ValueError` - If validation fails
    /// * `FileNotFoundError` - If path doesn't exist
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import DocsPathFinder
    ///
    /// finder = DocsPathFinder.new("My Games\\Fallout4")
    ///
    /// try:
    ///     finder.validate_docs_path("C:\\Users\\Name\\Documents\\My Games\\Fallout4")
    ///     print("Path is valid")
    /// except ValueError as e:
    ///     print(f"Validation failed: {e}")
    /// ```
    fn validate_docs_path(&self, path: String) -> PyResult<()> {
        self.inner
            .validate_docs_path(&PathBuf::from(path))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    /// Validate that required INI files exist in the documents path.
    ///
    /// # Arguments
    ///
    /// * `docs_path` - The documents folder path
    /// * `required_inis` - List of INI file names that must exist
    ///
    /// # Raises
    ///
    /// * `FileNotFoundError` - If any required INI file is missing
    /// * `ValueError` - If INI file cannot be parsed
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import DocsPathFinder
    ///
    /// finder = DocsPathFinder.new("My Games\\Fallout4")
    /// docs_path = "C:\\Users\\Name\\Documents\\My Games\\Fallout4"
    ///
    /// try:
    ///     finder.validate_ini_files(docs_path, ["Fallout4.ini", "Fallout4Prefs.ini"])
    ///     print("All INI files valid")
    /// except FileNotFoundError as e:
    ///     print(f"Missing INI file: {e}")
    /// ```
    fn validate_ini_files(&self, docs_path: String, required_inis: Vec<String>) -> PyResult<()> {
        let ini_refs: Vec<&str> = required_inis.iter().map(|s| s.as_str()).collect();
        self.inner
            .validate_ini_files(&PathBuf::from(docs_path), &ini_refs)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(e.to_string()))
    }

    /// Get the relative path within documents folder.
    ///
    /// # Returns
    ///
    /// The relative path (e.g., "My Games\\Fallout4").
    #[getter]
    fn relative_path(&self) -> String {
        self.inner.relative_path().to_string()
    }
}

/// Python wrapper for backup management.
///
/// Provides version-aware backup creation with XSE version extraction.
///
/// # Python Examples
///
/// ```python
/// from classic_path import BackupManager, XseVersion
///
/// # Create backup manager
/// manager = BackupManager.new("Backups")
///
/// # Extract version from XSE log
/// version = manager.extract_version_from_xse_log("f4se.log")
/// print(f"Version: {version.full_version()}")
///
/// # Create backup
/// backup_path = manager.create_backup("Fallout4.ini", version)
/// ```
#[pyclass]
pub struct BackupManager {
    inner: classic_path_core::BackupManager,
}

#[pymethods]
impl BackupManager {
    /// Create a new BackupManager.
    ///
    /// # Arguments
    ///
    /// * `backup_root` - Root directory where backups will be stored
    ///
    /// # Returns
    ///
    /// A new BackupManager instance.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import BackupManager
    ///
    /// manager = BackupManager.new("Backups")
    /// ```
    #[new]
    fn new(backup_root: String) -> Self {
        Self {
            inner: classic_path_core::BackupManager::new(backup_root),
        }
    }

    /// Extract version information from an XSE log file.
    ///
    /// # Arguments
    ///
    /// * `xse_log_path` - Path to the XSE log file (e.g., "f4se.log")
    ///
    /// # Returns
    ///
    /// The extracted version information.
    ///
    /// # Raises
    ///
    /// * `FileNotFoundError` - If log file doesn't exist
    /// * `ValueError` - If version string not found or invalid
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import BackupManager
    ///
    /// manager = BackupManager.new("Backups")
    /// version = manager.extract_version_from_xse_log("f4se.log")
    /// print(f"Version: {version.full_version()}")
    /// ```
    fn extract_version_from_xse_log(&self, xse_log_path: String) -> PyResult<XseVersion> {
        self.inner
            .extract_version_from_xse_log(&PathBuf::from(xse_log_path))
            .map(|v| XseVersion { inner: v })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(e.to_string()))
    }

    /// Create a backup of a file with version metadata.
    ///
    /// # Arguments
    ///
    /// * `source_file` - Path to the file to back up
    /// * `version` - Version information for organizing the backup
    ///
    /// # Returns
    ///
    /// Path to the created backup file.
    ///
    /// # Raises
    ///
    /// * `FileNotFoundError` - If source file doesn't exist
    /// * `IOError` - If backup directory can't be created or file copy fails
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import BackupManager, XseVersion
    ///
    /// manager = BackupManager.new("Backups")
    /// version = XseVersion.new("1.10.163.0")
    ///
    /// backup_path = manager.create_backup("Fallout4.ini", version)
    /// print(f"Backup created: {backup_path}")
    /// ```
    fn create_backup(&self, source_file: String, version: &XseVersion) -> PyResult<String> {
        self.inner
            .create_backup(&PathBuf::from(source_file), &version.inner)
            .map(|p| p.display().to_string())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }

    /// Get the backup root directory.
    ///
    /// # Returns
    ///
    /// The backup root path as a string.
    #[getter]
    fn backup_root(&self) -> String {
        self.inner.backup_root().display().to_string()
    }

    /// List all version directories in the backup root.
    ///
    /// # Returns
    ///
    /// List of version directory names.
    ///
    /// # Raises
    ///
    /// * `IOError` - If backup directory can't be read
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import BackupManager
    ///
    /// manager = BackupManager.new("Backups")
    /// for version in manager.list_versions():
    ///     print(f"Backup version: {version}")
    /// ```
    fn list_versions(&self) -> PyResult<Vec<String>> {
        self.inner
            .list_versions()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }

    /// Get the path to a specific version's backup directory.
    ///
    /// # Arguments
    ///
    /// * `version` - The version to get the path for
    ///
    /// # Returns
    ///
    /// Path to the version's backup directory.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import BackupManager, XseVersion
    ///
    /// manager = BackupManager.new("Backups")
    /// version = XseVersion.new("1.10.163.0")
    /// version_dir = manager.get_version_path(version)
    /// ```
    fn get_version_path(&self, version: &XseVersion) -> String {
        self.inner.get_version_path(&version.inner).display().to_string()
    }
}

/// Python wrapper for XSE version information.
///
/// Contains version string extracted from XSE logs.
///
/// # Python Examples
///
/// ```python
/// from classic_path import XseVersion
///
/// version = XseVersion.new("1.10.163.0")
/// print(version.full_version())      # "1.10.163.0"
/// print(version.sanitized())         # "1_10_163_0"
/// ```
#[pyclass]
pub struct XseVersion {
    inner: classic_path_core::XseVersion,
}

#[pymethods]
impl XseVersion {
    /// Create a new XseVersion from a version string.
    ///
    /// # Arguments
    ///
    /// * `version` - The full version string (e.g., "1.10.163.0")
    ///
    /// # Returns
    ///
    /// A new XseVersion instance.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import XseVersion
    ///
    /// version = XseVersion.new("1.10.163.0")
    /// ```
    #[new]
    fn new(version: String) -> Self {
        Self {
            inner: classic_path_core::XseVersion::new(version),
        }
    }

    /// Get the full version string.
    ///
    /// # Returns
    ///
    /// The complete version string (e.g., "1.10.163.0").
    fn full_version(&self) -> String {
        self.inner.full_version().to_string()
    }

    /// Get a sanitized version suitable for directory names.
    ///
    /// Replaces dots with underscores to create valid directory names.
    ///
    /// # Returns
    ///
    /// A sanitized version string (e.g., "1_10_163_0").
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import XseVersion
    ///
    /// version = XseVersion.new("1.10.163.0")
    /// print(version.sanitized())  # "1_10_163_0"
    /// ```
    fn sanitized(&self) -> String {
        self.inner.sanitized()
    }

    /// String representation of the version.
    fn __repr__(&self) -> String {
        format!("XseVersion('{}')", self.inner.full_version())
    }

    /// String conversion.
    fn __str__(&self) -> String {
        self.inner.full_version().to_string()
    }
}

/// Python wrapper for INI check result.
///
/// Contains information about the validation status of an INI file.
#[pyclass]
pub struct IniCheckResult {
    inner: classic_path_core::IniCheckResult,
}

#[pymethods]
impl IniCheckResult {
    /// Get the INI file name.
    ///
    /// # Returns
    ///
    /// The name of the INI file that was checked.
    #[getter]
    fn ini_name(&self) -> String {
        self.inner.ini_name.clone()
    }

    /// Check if the INI file exists.
    ///
    /// # Returns
    ///
    /// `True` if the file exists, `False` otherwise.
    #[getter]
    fn exists(&self) -> bool {
        self.inner.exists
    }

    /// Check if the INI file is valid.
    ///
    /// # Returns
    ///
    /// `True` if the file is parseable and valid, `False` otherwise.
    #[getter]
    fn is_valid(&self) -> bool {
        self.inner.is_valid
    }

    /// Get the validation message.
    ///
    /// # Returns
    ///
    /// A human-readable message describing the check result.
    #[getter]
    fn message(&self) -> String {
        self.inner.message.clone()
    }

    /// Get the issue type if any.
    ///
    /// # Returns
    ///
    /// Optional issue identifier (e.g., "missing", "corrupted", "missing_archive_section"),
    /// or `None` if there's no issue.
    #[getter]
    fn issue(&self) -> Option<String> {
        self.inner.issue.clone()
    }

    /// Check if this result indicates a problem.
    ///
    /// # Returns
    ///
    /// `True` if there's an issue, `False` otherwise.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import DocumentsChecker
    ///
    /// checker = DocumentsChecker("Fallout4")
    /// result = checker.validate_ini_file("C:\\Users\\Name\\Documents\\My Games\\Fallout4", "Fallout4.ini")
    /// if result.has_issue():
    ///     print(f"Problem: {result.issue}")
    /// ```
    fn has_issue(&self) -> bool {
        self.inner.has_issue()
    }

    fn __repr__(&self) -> String {
        format!(
            "IniCheckResult(ini_name='{}', exists={}, is_valid={}, has_issue={})",
            self.inner.ini_name,
            self.inner.exists,
            self.inner.is_valid,
            self.inner.has_issue()
        )
    }

    fn __str__(&self) -> String {
        self.inner.message.clone()
    }
}

/// Python wrapper for documents configuration checker.
///
/// Provides read-only checking of documents folder configuration and INI files.
///
/// # Examples
///
/// ```python
/// from classic_path import DocumentsChecker
///
/// checker = DocumentsChecker("Fallout4")
/// docs_path = "C:\\Users\\Name\\Documents\\My Games\\Fallout4"
///
/// # Check for OneDrive
/// if warning := checker.check_onedrive_in_path(docs_path):
///     print(warning)
///
/// # Validate INI file
/// result = checker.validate_ini_file(docs_path, "Fallout4.ini")
/// print(result.message)
/// ```
#[pyclass]
pub struct DocumentsChecker {
    inner: classic_path_core::DocumentsChecker,
}

#[pymethods]
impl DocumentsChecker {
    /// Create a new DocumentsChecker.
    ///
    /// # Arguments
    ///
    /// * `game_name` - Name of the game (e.g., "Fallout4")
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import DocumentsChecker
    ///
    /// checker = DocumentsChecker("Fallout4")
    /// ```
    #[new]
    fn new(game_name: String) -> Self {
        Self {
            inner: classic_path_core::DocumentsChecker::new(game_name),
        }
    }

    /// Check if OneDrive is detected in the documents path.
    ///
    /// # Arguments
    ///
    /// * `docs_path` - The documents folder path to check
    ///
    /// # Returns
    ///
    /// Warning message if OneDrive is detected, `None` otherwise.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import DocumentsChecker
    ///
    /// checker = DocumentsChecker("Fallout4")
    /// if warning := checker.check_onedrive_in_path("C:\\Users\\Name\\OneDrive\\Documents"):
    ///     print(warning)
    /// ```
    fn check_onedrive_in_path(&self, docs_path: String) -> Option<String> {
        self.inner.check_onedrive_in_path(&PathBuf::from(docs_path))
    }

    /// Validate an INI file in the documents folder.
    ///
    /// # Arguments
    ///
    /// * `docs_path` - The documents folder path
    /// * `ini_name` - Name of the INI file (e.g., "Fallout4.ini")
    ///
    /// # Returns
    ///
    /// An `IniCheckResult` containing the validation status.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import DocumentsChecker
    ///
    /// checker = DocumentsChecker("Fallout4")
    /// result = checker.validate_ini_file(
    ///     "C:\\Users\\Name\\Documents\\My Games\\Fallout4",
    ///     "Fallout4.ini"
    /// )
    /// print(result.message)
    /// ```
    fn validate_ini_file(&self, docs_path: String, ini_name: String) -> PyResult<IniCheckResult> {
        self.inner
            .validate_ini_file(&PathBuf::from(docs_path), &ini_name)
            .map(|result| IniCheckResult { inner: result })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }

    /// Run all document checks for the game.
    ///
    /// This performs:
    /// 1. OneDrive detection check
    /// 2. Validation of main game INI
    /// 3. Validation of Custom INI
    /// 4. Validation of Prefs INI
    ///
    /// # Arguments
    ///
    /// * `docs_path` - The documents folder path
    ///
    /// # Returns
    ///
    /// A list of check result messages (only non-empty results).
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_path import DocumentsChecker
    ///
    /// checker = DocumentsChecker("Fallout4")
    /// messages = checker.run_all_checks("C:\\Users\\Name\\Documents\\My Games\\Fallout4")
    /// for msg in messages:
    ///     print(msg)
    /// ```
    fn run_all_checks(&self, docs_path: String) -> PyResult<Vec<String>> {
        self.inner
            .run_all_checks(&PathBuf::from(docs_path))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }

    /// Get the game name.
    ///
    /// # Returns
    ///
    /// The game name string.
    #[getter]
    fn game_name(&self) -> String {
        self.inner.game_name().to_string()
    }
}

/// Python module for path management.
///
/// This module provides unified path management functionality for CLASSIC:
/// - Path validation (PathValidator)
/// - Game path detection (GamePathFinder)
/// - Documents path management (DocsPathFinder)
/// - Backup operations (BackupManager, XseVersion)
/// - Documents checking (DocumentsChecker, IniCheckResult)
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
///
/// # Find game path
/// finder = classic_path.GamePathFinder("Fallout4.exe", None, "Fallout4", False)
/// game_path = finder.find_game_path(cached_path=None, xse_log_path=None)
///
/// # Find documents path
/// docs_finder = classic_path.DocsPathFinder("My Games\\Fallout4")
/// docs_path = docs_finder.find_docs_path(cached_path=None)
/// ```
#[pymodule]
fn classic_path(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add the PathValidator class
    m.add_class::<PathValidator>()?;

    // Add the GamePathFinder class
    m.add_class::<GamePathFinder>()?;

    // Add the DocsPathFinder class
    m.add_class::<DocsPathFinder>()?;

    // Add the BackupManager class
    m.add_class::<BackupManager>()?;

    // Add the XseVersion class
    m.add_class::<XseVersion>()?;

    // Add the DocumentsChecker class
    m.add_class::<DocumentsChecker>()?;

    // Add the IniCheckResult class
    m.add_class::<IniCheckResult>()?;

    // Module metadata
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__doc__", "Python bindings for CLASSIC path management")?;

    Ok(())
}
