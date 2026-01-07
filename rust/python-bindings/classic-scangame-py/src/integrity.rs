//! Python bindings for game integrity checking

use classic_scangame_core::integrity::{
    CheckType, GameIntegrityChecker, IntegrityCheckResult, IntegrityConfig, IntegrityError,
};
use pyo3::exceptions::{PyFileNotFoundError, PyIOError, PyRuntimeError};
use pyo3::prelude::*;
use std::path::PathBuf;

/// Python wrapper for CheckType
#[pyclass(name = "CheckType")]
#[derive(Clone)]
pub struct PyCheckType {
    inner: CheckType,
}

#[pymethods]
impl PyCheckType {
    /// Create ExecutableVersion check type
    #[staticmethod]
    fn executable_version() -> Self {
        Self {
            inner: CheckType::ExecutableVersion,
        }
    }

    /// Create InstallationLocation check type
    #[staticmethod]
    fn installation_location() -> Self {
        Self {
            inner: CheckType::InstallationLocation,
        }
    }

    /// Check if this is an ExecutableVersion check
    fn is_executable_version(&self) -> bool {
        matches!(self.inner, CheckType::ExecutableVersion)
    }

    /// Check if this is an InstallationLocation check
    fn is_installation_location(&self) -> bool {
        matches!(self.inner, CheckType::InstallationLocation)
    }

    fn __repr__(&self) -> String {
        match self.inner {
            CheckType::ExecutableVersion => "CheckType.ExecutableVersion".to_string(),
            CheckType::InstallationLocation => "CheckType.InstallationLocation".to_string(),
        }
    }

    fn __str__(&self) -> String {
        match self.inner {
            CheckType::ExecutableVersion => "ExecutableVersion".to_string(),
            CheckType::InstallationLocation => "InstallationLocation".to_string(),
        }
    }
}

/// Python wrapper for IntegrityCheckResult
#[pyclass(name = "IntegrityCheckResult")]
pub struct PyIntegrityCheckResult {
    inner: IntegrityCheckResult,
}

#[pymethods]
impl PyIntegrityCheckResult {
    /// Whether the check passed
    #[getter]
    fn is_valid(&self) -> bool {
        self.inner.is_valid
    }

    /// Message describing the check result
    #[getter]
    fn message(&self) -> String {
        self.inner.message.clone()
    }

    /// Type of check performed
    #[getter]
    fn check_type(&self) -> PyCheckType {
        PyCheckType {
            inner: self.inner.check_type,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "IntegrityCheckResult(is_valid={}, check_type={}, message='{}')",
            self.inner.is_valid,
            match self.inner.check_type {
                CheckType::ExecutableVersion => "ExecutableVersion",
                CheckType::InstallationLocation => "InstallationLocation",
            },
            self.inner.message.lines().next().unwrap_or("")
        )
    }
}

impl From<IntegrityCheckResult> for PyIntegrityCheckResult {
    fn from(result: IntegrityCheckResult) -> Self {
        Self { inner: result }
    }
}

/// Python wrapper for IntegrityConfig
#[pyclass(name = "IntegrityConfig")]
pub struct PyIntegrityConfig {
    inner: IntegrityConfig,
}

#[pymethods]
impl PyIntegrityConfig {
    /// Create a new integrity configuration
    ///
    /// Args:
    ///     game_exe_path: Path to the game executable
    ///     valid_exe_hashes: List of valid SHA256 hashes for known game versions
    ///     root_name: Game root name (e.g., "Fallout 4", "Skyrim")
    #[new]
    fn new(game_exe_path: PathBuf, valid_exe_hashes: Vec<String>, root_name: String) -> Self {
        Self {
            inner: IntegrityConfig::new(game_exe_path, valid_exe_hashes, root_name),
        }
    }

    /// Set the Steam INI path
    ///
    /// Args:
    ///     steam_ini_path: Path to Steam INI file
    ///
    /// Returns:
    ///     Self for method chaining
    fn with_steam_ini(mut slf: PyRefMut<'_, Self>, steam_ini_path: PathBuf) -> PyRefMut<'_, Self> {
        slf.inner = std::mem::take(&mut slf.inner).with_steam_ini(steam_ini_path);
        slf
    }

    /// Set the root warning message
    ///
    /// Args:
    ///     root_warn: Warning message for Program Files installation
    ///
    /// Returns:
    ///     Self for method chaining
    fn with_root_warn(mut slf: PyRefMut<'_, Self>, root_warn: String) -> PyRefMut<'_, Self> {
        slf.inner = std::mem::take(&mut slf.inner).with_root_warn(root_warn);
        slf
    }

    /// Get the game executable path
    #[getter]
    fn game_exe_path(&self) -> PathBuf {
        self.inner.game_exe_path.clone()
    }

    /// Get the valid exe hashes
    #[getter]
    fn valid_exe_hashes(&self) -> Vec<String> {
        self.inner.valid_exe_hashes.clone()
    }

    /// Get the game root name
    #[getter]
    fn root_name(&self) -> String {
        self.inner.root_name.clone()
    }

    /// Get the Steam INI path
    #[getter]
    fn steam_ini_path(&self) -> Option<PathBuf> {
        self.inner.steam_ini_path.clone()
    }

    /// Get the root warning message
    #[getter]
    fn root_warn(&self) -> Option<String> {
        self.inner.root_warn.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "IntegrityConfig(game_exe_path='{}', root_name='{}')",
            self.inner.game_exe_path.display(),
            self.inner.root_name
        )
    }
}

/// Python wrapper for GameIntegrityChecker
#[pyclass(name = "GameIntegrityChecker")]
pub struct PyGameIntegrityChecker {
    inner: GameIntegrityChecker,
}

#[pymethods]
impl PyGameIntegrityChecker {
    /// Create a new game integrity checker
    ///
    /// Args:
    ///     config: Integrity checking configuration
    #[new]
    fn new(config: &PyIntegrityConfig) -> Self {
        Self {
            inner: GameIntegrityChecker::new(config.inner.clone()),
        }
    }

    /// Check if game executable is up to date
    ///
    /// This function:
    /// 1. Calculates the SHA256 hash of the game executable
    /// 2. Compares it against known old and new versions
    /// 3. Checks for Steam INI presence (indicates outdated version)
    ///
    /// Returns:
    ///     IntegrityCheckResult: Result containing check status and message
    ///
    /// Raises:
    ///     FileNotFoundError: If executable file doesn't exist
    ///     IOError: If failed to read the executable
    ///     RuntimeError: If hash calculation fails
    fn check_executable_version(&self) -> PyResult<PyIntegrityCheckResult> {
        self.inner
            .check_executable_version()
            .map(PyIntegrityCheckResult::from)
            .map_err(convert_integrity_error)
    }

    /// Verify game is installed in recommended location
    ///
    /// Checks if the game is installed outside of Program Files,
    /// which is recommended to avoid permission issues.
    ///
    /// Returns:
    ///     IntegrityCheckResult: Result containing check status and message
    fn check_installation_location(&self) -> PyResult<PyIntegrityCheckResult> {
        self.inner
            .check_installation_location()
            .map(PyIntegrityCheckResult::from)
            .map_err(convert_integrity_error)
    }

    /// Run all integrity checks and return combined results
    ///
    /// Performs the following checks:
    /// 1. Game executable version validation
    /// 2. Installation location verification
    ///
    /// Returns:
    ///     list[IntegrityCheckResult]: Vector of all check results
    ///
    /// Raises:
    ///     FileNotFoundError: If executable file doesn't exist
    ///     IOError: If failed to read files
    ///     RuntimeError: If hash calculation fails
    fn run_all_checks(&self) -> PyResult<Vec<PyIntegrityCheckResult>> {
        self.inner
            .run_all_checks()
            .map(|results| {
                results
                    .into_iter()
                    .map(PyIntegrityCheckResult::from)
                    .collect()
            })
            .map_err(convert_integrity_error)
    }

    /// Run all checks and return combined message string
    ///
    /// This is a convenience method that matches the Python API.
    ///
    /// Returns:
    ///     str: Combined message string from all checks
    ///
    /// Raises:
    ///     FileNotFoundError: If executable file doesn't exist
    ///     IOError: If failed to read files
    ///     RuntimeError: If hash calculation fails
    ///
    /// Example:
    ///     >>> from classic_scangame import GameIntegrityChecker, IntegrityConfig
    ///     >>> config = IntegrityConfig("/path/to/game.exe", "old_hash", "new_hash", "Fallout 4")
    ///     >>> checker = GameIntegrityChecker(config)
    ///     >>> message = checker.run_full_check()
    ///     >>> print(message)
    fn run_full_check(&self) -> PyResult<String> {
        self.inner.run_full_check().map_err(convert_integrity_error)
    }

    /// Get the configuration
    fn config(&self) -> PyIntegrityConfig {
        PyIntegrityConfig {
            inner: self.inner.config().clone(),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "GameIntegrityChecker(game_exe_path='{}', root_name='{}')",
            self.inner.config().game_exe_path.display(),
            self.inner.config().root_name
        )
    }
}

/// Convert IntegrityError to PyErr
fn convert_integrity_error(err: IntegrityError) -> PyErr {
    match err {
        IntegrityError::IoError(io_err) => PyIOError::new_err(io_err.to_string()),
        IntegrityError::FileNotFound(path) => {
            PyFileNotFoundError::new_err(format!("File not found: {}", path.display()))
        }
        IntegrityError::HashError(msg) => PyRuntimeError::new_err(format!("Hash error: {}", msg)),
    }
}

/// Register integrity types with the Python module
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCheckType>()?;
    m.add_class::<PyIntegrityCheckResult>()?;
    m.add_class::<PyIntegrityConfig>()?;
    m.add_class::<PyGameIntegrityChecker>()?;
    Ok(())
}
