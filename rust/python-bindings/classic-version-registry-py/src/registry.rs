//! Python bindings for the VersionRegistry singleton.

use classic_version_registry_core as core;
use pyo3::prelude::*;

use crate::matching::PyMatchResult;
use crate::models::{PyCrashgenConfig, PyUnknownVersionHandling, PyVersionInfo};

/// Singleton version registry for game version metadata.
///
/// The registry is automatically initialized on first access and loads
/// version data from YAML configuration with fallback to hardcoded defaults.
///
/// All methods delegate to the Rust singleton via OnceLock, ensuring
/// thread-safe, zero-copy access to version metadata.
///
/// Example:
///     >>> import classic_version_registry
///     >>> registry = classic_version_registry.VersionRegistry()
///     >>> og = registry.get_by_id("FO4_OG")
///     >>> print(og.display_name)
///     Fallout 4 Original
///     >>>
///     >>> result = registry.match_version("1.10.500.0", "Fallout4", False)
///     >>> print(result.confidence)
///     nearest
#[pyclass(name = "VersionRegistry")]
pub struct PyVersionRegistry;

#[pymethods]
impl PyVersionRegistry {
    /// Create a VersionRegistry instance.
    ///
    /// This is a lightweight handle to the Rust singleton -- no data is
    /// copied. Multiple instances share the same underlying registry.
    #[new]
    fn new() -> Self {
        Self
    }

    // === Lookup API ===

    /// Get version info by ID.
    ///
    /// Args:
    ///     version_id: The version ID (e.g., "FO4_OG", "FO4_NG", "FO4_VR").
    ///
    /// Returns:
    ///     The VersionInfo, or None if not found.
    ///
    /// Example:
    ///     >>> og = registry.get_by_id("FO4_OG")
    ///     >>> print(og.version)
    ///     1.10.163.0
    fn get_by_id(&self, version_id: &str) -> Option<PyVersionInfo> {
        core::get_version_registry()
            .get_by_id(version_id)
            .cloned()
            .map(PyVersionInfo::from)
    }

    /// Get version info by exact version string.
    ///
    /// Args:
    ///     version_str: The exact game version string (e.g., "1.10.163.0").
    ///
    /// Returns:
    ///     The VersionInfo, or None if not found.
    ///
    /// Raises:
    ///     ValueError: If the version string is invalid.
    fn get_by_version(&self, version_str: &str) -> PyResult<Option<PyVersionInfo>> {
        let v = core::GameVersion::parse(version_str).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid version: {e}"))
        })?;
        Ok(core::get_version_registry()
            .get_by_version(&v)
            .cloned()
            .map(PyVersionInfo::from))
    }

    /// Get version info by short name.
    ///
    /// Args:
    ///     short_name: The short name (e.g., "OG", "NG", "VR").
    ///
    /// Returns:
    ///     The VersionInfo, or None if not found.
    fn get_by_short_name(&self, short_name: &str) -> Option<PyVersionInfo> {
        core::get_version_registry()
            .get_by_short_name(short_name)
            .cloned()
            .map(PyVersionInfo::from)
    }

    // === Filtering API ===

    /// Get all registered versions, sorted by priority (descending).
    ///
    /// Returns:
    ///     List of VersionInfo objects.
    fn get_all(&self) -> Vec<PyVersionInfo> {
        core::get_version_registry()
            .get_all()
            .into_iter()
            .cloned()
            .map(PyVersionInfo::from)
            .collect()
    }

    /// Get all versions for a specific game.
    ///
    /// Args:
    ///     game: Game identifier (e.g., "Fallout4").
    ///     is_vr: Optional VR filter. If None, returns all versions.
    ///
    /// Returns:
    ///     List of matching VersionInfo objects, sorted by priority (descending).
    #[pyo3(signature = (game, is_vr=None))]
    fn get_all_for_game(&self, game: &str, is_vr: Option<bool>) -> Vec<PyVersionInfo> {
        core::get_version_registry()
            .get_all_for_game(game, is_vr)
            .into_iter()
            .cloned()
            .map(PyVersionInfo::from)
            .collect()
    }

    /// Get correct versions for current mode (VR or non-VR).
    ///
    /// Args:
    ///     is_vr: Whether VR mode is active.
    ///
    /// Returns:
    ///     List of versions matching the VR mode.
    fn get_correct_versions(&self, is_vr: bool) -> Vec<PyVersionInfo> {
        core::get_version_registry()
            .get_correct_versions(is_vr)
            .into_iter()
            .cloned()
            .map(PyVersionInfo::from)
            .collect()
    }

    /// Get wrong versions for current mode (opposite of is_vr).
    ///
    /// Args:
    ///     is_vr: Whether VR mode is active.
    ///
    /// Returns:
    ///     List of versions NOT matching the VR mode.
    fn get_wrong_versions(&self, is_vr: bool) -> Vec<PyVersionInfo> {
        core::get_version_registry()
            .get_wrong_versions(is_vr)
            .into_iter()
            .cloned()
            .map(PyVersionInfo::from)
            .collect()
    }

    // === Matching API ===

    /// Match a detected version string to the registry.
    ///
    /// Uses intelligent matching with fallback:
    /// 1. Exact match
    /// 2. Compatible range match
    /// 3. Nearest match (same major version)
    /// 4. Default fallback
    ///
    /// Args:
    ///     version_str: Detected game version string (e.g., "1.10.163.0").
    ///     game: Game identifier (default: "Fallout4").
    ///     is_vr: Whether VR mode is active (default: False).
    ///
    /// Returns:
    ///     MatchResult with matched version and confidence level.
    ///
    /// Raises:
    ///     ValueError: If the version string is invalid.
    ///
    /// Example:
    ///     >>> result = registry.match_version("1.10.163.0", "Fallout4", False)
    ///     >>> result.is_exact
    ///     True
    #[pyo3(signature = (version_str, game="Fallout4", is_vr=false))]
    fn match_version(&self, version_str: &str, game: &str, is_vr: bool) -> PyResult<PyMatchResult> {
        let detected = core::GameVersion::parse(version_str).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid version: {e}"))
        })?;
        let result = core::get_version_registry().match_version(&detected, game, is_vr);
        Ok(PyMatchResult::from(result))
    }

    /// Get Address Library filename for a version.
    ///
    /// Args:
    ///     version_str: Game version string.
    ///     is_vr: Whether VR mode is active (default: False).
    ///
    /// Returns:
    ///     The Address Library filename, or None.
    ///
    /// Raises:
    ///     ValueError: If the version string is invalid.
    #[pyo3(signature = (version_str, is_vr=false))]
    fn get_address_library_filename(
        &self,
        version_str: &str,
        is_vr: bool,
    ) -> PyResult<Option<String>> {
        let v = core::GameVersion::parse(version_str).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid version: {e}"))
        })?;
        Ok(core::get_version_registry().get_address_library_filename(&v, is_vr))
    }

    // === Crashgen API ===

    /// Get crash generator configurations for a version ID.
    ///
    /// Args:
    ///     version_id: The version ID (e.g., "FO4_OG").
    ///
    /// Returns:
    ///     List of CrashgenConfig objects.
    fn get_crashgen_configs(&self, version_id: &str) -> Vec<PyCrashgenConfig> {
        core::get_version_registry()
            .get_crashgen_versions(version_id)
            .into_iter()
            .cloned()
            .map(PyCrashgenConfig::from)
            .collect()
    }

    /// Get crash generator versions as simple version strings.
    ///
    /// Args:
    ///     version_id: The version ID (e.g., "FO4_OG").
    ///
    /// Returns:
    ///     List of version strings.
    fn get_crashgen_versions(&self, version_id: &str) -> Vec<String> {
        core::get_version_registry()
            .get_crashgen_version_strings(version_id)
            .into_iter()
            .map(String::from)
            .collect()
    }

    /// Get a specific crash generator by version ID and crashgen version.
    ///
    /// Args:
    ///     version_id: The version ID (e.g., "FO4_OG").
    ///     crashgen_version: The crash generator version (e.g., "1.28.6").
    ///
    /// Returns:
    ///     The CrashgenConfig, or None if not found.
    fn get_crashgen_for_version(
        &self,
        version_id: &str,
        crashgen_version: &str,
    ) -> Option<PyCrashgenConfig> {
        core::get_version_registry()
            .get_crashgen_for_version(version_id, crashgen_version)
            .cloned()
            .map(PyCrashgenConfig::from)
    }

    // === Hash API (exe_hash and script_hashes) ===

    /// Get all known exe hashes for a game.
    ///
    /// Args:
    ///     game: Game identifier (default: "Fallout4").
    ///     is_vr: Optional VR filter. If None, returns all versions.
    ///
    /// Returns:
    ///     Set of valid SHA-256 hashes.
    #[pyo3(signature = (game="Fallout4", is_vr=None))]
    fn get_all_exe_hashes(
        &self,
        game: &str,
        is_vr: Option<bool>,
    ) -> std::collections::HashSet<String> {
        let registry = core::get_version_registry();
        registry
            .get_all_for_game(game, is_vr)
            .into_iter()
            .filter_map(|v| v.exe_hash.clone())
            .collect()
    }

    /// Get all valid script hashes for all versions of a game.
    ///
    /// Returns ALL valid hashes for each script file across all versions.
    ///
    /// Args:
    ///     game: Game identifier (default: "Fallout4").
    ///     is_vr: Optional VR filter. If None, returns all versions.
    ///
    /// Returns:
    ///     Dictionary mapping script filenames to sets of valid SHA-256 hashes.
    #[pyo3(signature = (game="Fallout4", is_vr=None))]
    fn get_all_script_hashes(
        &self,
        game: &str,
        is_vr: Option<bool>,
    ) -> std::collections::HashMap<String, std::collections::HashSet<String>> {
        let registry = core::get_version_registry();
        let mut result: std::collections::HashMap<String, std::collections::HashSet<String>> =
            std::collections::HashMap::new();
        for version in registry.get_all_for_game(game, is_vr) {
            if let Some(xse) = &version.xse {
                for (script, hash_val) in &xse.script_hashes {
                    result
                        .entry(script.clone())
                        .or_default()
                        .insert(hash_val.clone());
                }
            }
        }
        result
    }

    /// Get script hashes for a specific version.
    ///
    /// Args:
    ///     version_id: The version ID (e.g., "FO4_OG").
    ///
    /// Returns:
    ///     Dictionary mapping script filenames to expected SHA-256 hashes.
    ///     Empty dict if version not found or has no script hashes.
    fn get_script_hashes_for_version(
        &self,
        version_id: &str,
    ) -> std::collections::HashMap<String, String> {
        let registry = core::get_version_registry();
        registry
            .get_by_id(version_id)
            .and_then(|v| v.xse.as_ref())
            .map(|xse| xse.script_hashes.iter().cloned().collect())
            .unwrap_or_default()
    }

    // === Unknown Version Handling ===

    /// Gets the unknown version handling configuration.
    #[getter]
    fn unknown_version_handling(&self) -> PyUnknownVersionHandling {
        PyUnknownVersionHandling::from(
            core::get_version_registry()
                .unknown_version_handling()
                .clone(),
        )
    }

    /// String representation.
    fn __repr__(&self) -> String {
        let count = core::get_version_registry().get_all().len();
        format!("VersionRegistry({count} versions)")
    }
}

/// Convenience function: match a version string to the registry.
///
/// This is a module-level function that creates a temporary registry handle
/// and delegates to it. Useful for one-off matching without holding a reference.
///
/// Args:
///     version_str: Detected game version string (e.g., "1.10.163.0").
///     game: Game identifier (default: "Fallout4").
///     is_vr: Whether VR mode is active (default: False).
///
/// Returns:
///     MatchResult with matched version and confidence level.
///
/// Raises:
///     ValueError: If the version string is invalid.
///
/// Example:
///     >>> import classic_version_registry
///     >>> result = classic_version_registry.match_version_string("1.10.163.0", "Fallout4", False)
///     >>> print(result.version_info.display_name)
///     Fallout 4 Original
#[pyfunction]
#[pyo3(signature = (version_str, game="Fallout4", is_vr=false))]
fn match_version_string(version_str: &str, game: &str, is_vr: bool) -> PyResult<PyMatchResult> {
    let detected = core::GameVersion::parse(version_str)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid version: {e}")))?;
    let result = core::get_version_registry().match_version(&detected, game, is_vr);
    Ok(PyMatchResult::from(result))
}

/// Convenience function: get the singleton registry instance.
///
/// Returns:
///     A VersionRegistry instance (lightweight handle to Rust singleton).
///
/// Example:
///     >>> registry = classic_version_registry.get_version_registry()
///     >>> og = registry.get_by_id("FO4_OG")
#[pyfunction]
fn get_version_registry() -> PyVersionRegistry {
    PyVersionRegistry
}

/// Register registry components with the Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyVersionRegistry>()?;
    m.add_function(wrap_pyfunction!(match_version_string, m)?)?;
    m.add_function(wrap_pyfunction!(get_version_registry, m)?)?;
    Ok(())
}
