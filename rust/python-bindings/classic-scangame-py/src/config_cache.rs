//! PyO3 bindings for ConfigFileCache (G-03) and ModIniScanner (G-04)

use classic_scangame_core::config_cache::ConfigFileCache;
use classic_scangame_core::mod_ini::{ModIniScanResult, ModIniScanner};
use pyo3::prelude::*;
use std::collections::HashMap;
use std::path::PathBuf;

/// Python wrapper for VsyncEntry
#[pyclass(name = "VsyncEntry")]
#[derive(Clone)]
pub struct PyVsyncEntry {
    /// Path to the config file
    #[pyo3(get)]
    pub file_path: PathBuf,

    /// Setting name that has VSync enabled
    #[pyo3(get)]
    pub setting: String,
}

#[pymethods]
impl PyVsyncEntry {
    fn __repr__(&self) -> String {
        format!(
            "VsyncEntry(file='{}', setting='{}')",
            self.file_path.display(),
            self.setting
        )
    }
}

/// Python wrapper for DuplicateEntry
#[pyclass(name = "DuplicateEntry")]
#[derive(Clone)]
pub struct PyDuplicateEntry {
    /// Lowercase filename
    #[pyo3(get)]
    pub file_name: String,

    /// All paths where this file was found
    #[pyo3(get)]
    pub paths: Vec<PathBuf>,
}

#[pymethods]
impl PyDuplicateEntry {
    fn __repr__(&self) -> String {
        format!(
            "DuplicateEntry(file='{}', count={})",
            self.file_name,
            self.paths.len()
        )
    }
}

/// Python wrapper for ModIniScanResult
#[pyclass(name = "ModIniScanResult")]
#[derive(Clone)]
pub struct PyModIniScanResult {
    /// Formatted report message
    #[pyo3(get)]
    pub message: String,

    /// Structured configuration issues detected
    #[pyo3(get)]
    pub issues: Vec<crate::ini::PyConfigIssue>,

    /// List of files with VSync enabled
    #[pyo3(get)]
    pub vsync_files: Vec<PyVsyncEntry>,

    /// Duplicate files detected
    #[pyo3(get)]
    pub duplicates: Vec<PyDuplicateEntry>,
}

#[pymethods]
impl PyModIniScanResult {
    fn __repr__(&self) -> String {
        format!(
            "ModIniScanResult(issues={}, vsync={}, duplicates={})",
            self.issues.len(),
            self.vsync_files.len(),
            self.duplicates.len()
        )
    }
}

/// Convert core ModIniScanResult to Python wrapper
fn convert_scan_result(result: ModIniScanResult) -> PyModIniScanResult {
    let issues = result
        .issues
        .into_iter()
        .map(|ci| crate::ini::PyConfigIssue {
            file_path: ci.file_path,
            section: ci.section,
            setting: ci.setting,
            current_value: ci.current_value,
            recommended_value: ci.recommended_value,
            description: ci.description,
            severity: match ci.severity {
                classic_scangame_core::IssueSeverity::Info => crate::ini::PyIssueSeverity::Info,
                classic_scangame_core::IssueSeverity::Warning => {
                    crate::ini::PyIssueSeverity::Warning
                }
                classic_scangame_core::IssueSeverity::Error => crate::ini::PyIssueSeverity::Error,
            },
        })
        .collect();

    let vsync_files = result
        .vsync_files
        .into_iter()
        .map(|v| PyVsyncEntry {
            file_path: v.file_path,
            setting: v.setting,
        })
        .collect();

    let duplicates = result
        .duplicates
        .into_iter()
        .map(|d| PyDuplicateEntry {
            file_name: d.file_name,
            paths: d.paths,
        })
        .collect();

    PyModIniScanResult {
        message: result.message,
        issues,
        vsync_files,
        duplicates,
    }
}

/// Python wrapper for ConfigFileCache
///
/// Encoding-aware INI/CONF file cache that scans a game directory,
/// detects duplicates, and provides typed getters.
///
/// Example:
///     >>> cache = ConfigFileCache("C:/Games/Fallout4", ["F4EE"])
///     >>> if cache.contains("enblocal.ini"):
///     ...     val = cache.get_bool("enblocal.ini", "ENGINE", "ForceVSync")
///     ...     print(f"VSync: {val}")
#[pyclass(name = "RustConfigFileCache")]
pub struct PyConfigFileCache {
    inner: ConfigFileCache,
}

#[pymethods]
impl PyConfigFileCache {
    #[new]
    #[pyo3(signature = (game_root, duplicate_whitelist=None))]
    fn new(game_root: PathBuf, duplicate_whitelist: Option<Vec<String>>) -> PyResult<Self> {
        let whitelist = duplicate_whitelist.unwrap_or_default();
        let whitelist_refs: Vec<&str> = whitelist.iter().map(|s| s.as_str()).collect();

        let cache = ConfigFileCache::new(&game_root, &whitelist_refs).map_err(crate::to_pyerr)?;

        Ok(Self { inner: cache })
    }

    /// Check if a file is in the cache
    fn contains(&self, file_name_lower: &str) -> bool {
        self.inner.contains(file_name_lower)
    }

    /// Get the path for a file
    fn get_path(&self, file_name_lower: &str) -> Option<PathBuf> {
        self.inner
            .get_path(file_name_lower)
            .map(|p| p.to_path_buf())
    }

    /// Get a string value
    fn get_str(&mut self, file_name_lower: &str, section: &str, setting: &str) -> Option<String> {
        self.inner.get_str(file_name_lower, section, setting)
    }

    /// Get a boolean value
    fn get_bool(&mut self, file_name_lower: &str, section: &str, setting: &str) -> Option<bool> {
        self.inner.get_bool(file_name_lower, section, setting)
    }

    /// Get an integer value
    fn get_int(&mut self, file_name_lower: &str, section: &str, setting: &str) -> Option<i64> {
        self.inner.get_int(file_name_lower, section, setting)
    }

    /// Get a float value
    fn get_float(&mut self, file_name_lower: &str, section: &str, setting: &str) -> Option<f64> {
        self.inner.get_float(file_name_lower, section, setting)
    }

    /// Check if a setting exists
    fn has_setting(&mut self, file_name_lower: &str, section: &str, setting: &str) -> bool {
        self.inner.has_setting(file_name_lower, section, setting)
    }

    /// Get all config files as a dict of name -> path
    fn config_files(&self) -> HashMap<String, PathBuf> {
        self.inner
            .config_files()
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect()
    }

    /// Get duplicate files as a dict of name -> list of paths
    fn get_duplicates(&self) -> HashMap<String, Vec<PathBuf>> {
        self.inner.duplicate_files.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "RustConfigFileCache(files={})",
            self.inner.config_files().len()
        )
    }
}

/// Python wrapper for ModIniScanner
///
/// Scans mod INI files for configuration issues, VSync settings, and duplicates.
///
/// Example:
///     >>> result = ModIniScanner.scan("C:/Games/Fallout4", "Fallout4")
///     >>> print(result.message)
///     >>> for vsync in result.vsync_files:
///     ...     print(f"VSync: {vsync.file_path} -> {vsync.setting}")
#[pyclass(name = "RustModIniScanner")]
pub struct PyModIniScanner;

#[pymethods]
impl PyModIniScanner {
    #[new]
    fn new() -> Self {
        Self
    }

    /// Scan mod INI files and produce a report
    ///
    /// Args:
    ///     game_root: Root directory of the game installation
    ///     game_name: Game name (e.g., "Fallout4")
    ///
    /// Returns:
    ///     ModIniScanResult with message, VSync entries, and duplicates
    #[staticmethod]
    fn scan(game_root: PathBuf, game_name: &str) -> PyResult<PyModIniScanResult> {
        let result = ModIniScanner::scan(&game_root, game_name).map_err(crate::to_pyerr)?;
        Ok(convert_scan_result(result))
    }

    fn __repr__(&self) -> String {
        "RustModIniScanner()".to_string()
    }
}

/// Convenience function: scan mod INIs without creating scanner instance
///
/// Args:
///     game_root: Root directory of the game installation
///     game_name: Game name (e.g., "Fallout4")
///
/// Returns:
///     Formatted scan result message
#[pyfunction]
#[pyo3(signature = (game_root, game_name))]
pub fn scan_mod_inis(game_root: PathBuf, game_name: &str) -> PyResult<String> {
    let result = ModIniScanner::scan(&game_root, game_name).map_err(crate::to_pyerr)?;
    Ok(result.message)
}

/// Register config cache module functions with Python module
pub fn register_config_cache(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyConfigFileCache>()?;
    m.add_class::<PyModIniScanner>()?;
    m.add_class::<PyModIniScanResult>()?;
    m.add_class::<PyVsyncEntry>()?;
    m.add_class::<PyDuplicateEntry>()?;
    m.add_function(wrap_pyfunction!(scan_mod_inis, m)?)?;
    Ok(())
}
