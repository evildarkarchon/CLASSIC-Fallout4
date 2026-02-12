//! Python bindings for version registry data models.

use classic_version_registry_core as core;
use pyo3::prelude::*;

/// Address Library configuration for a game version.
///
/// Attributes:
///     filename: Name of the Address Library file (e.g., "version-1-10-163-0.bin").
///     format: File format ("bin" or "csv").
///     nexus_url: Nexus Mods download URL.
///
/// Example:
///     >>> og = registry.get_by_id("FO4_OG")
///     >>> print(og.address_library.filename)
///     version-1-10-163-0.bin
#[pyclass(name = "AddressLibraryConfig")]
#[derive(Clone)]
pub struct PyAddressLibraryConfig {
    inner: core::AddressLibraryConfig,
}

impl From<core::AddressLibraryConfig> for PyAddressLibraryConfig {
    fn from(config: core::AddressLibraryConfig) -> Self {
        Self { inner: config }
    }
}

#[pymethods]
impl PyAddressLibraryConfig {
    /// Gets the filename of the Address Library file.
    #[getter]
    fn filename(&self) -> &str {
        &self.inner.filename
    }

    /// Gets the file format ("bin" or "csv").
    #[getter]
    fn format(&self) -> &'static str {
        self.inner.format.extension()
    }

    /// Gets the Nexus Mods download URL.
    #[getter]
    fn nexus_url(&self) -> &str {
        &self.inner.nexus_url
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "AddressLibraryConfig(filename='{}', format='{}')",
            self.inner.filename,
            self.inner.format.extension()
        )
    }
}

/// Script Extender (XSE) configuration for a game version.
///
/// Attributes:
///     acronym: XSE acronym (e.g., "F4SE", "F4SEVR").
///     compatible_version: Compatible XSE version string (e.g., "0.6.23").
///     loader: Loader executable name (e.g., "f4se_loader.exe").
///     script_hashes: Tuple of (filename, sha256_hash) pairs for XSE script files.
///
/// Example:
///     >>> og = registry.get_by_id("FO4_OG")
///     >>> print(og.xse.acronym)
///     F4SE
///     >>> for name, hash_val in og.xse.script_hashes:
///     ...     print(f"{name}: {hash_val}")
#[pyclass(name = "XseConfig")]
#[derive(Clone)]
pub struct PyXseConfig {
    inner: core::XseConfig,
}

impl From<core::XseConfig> for PyXseConfig {
    fn from(config: core::XseConfig) -> Self {
        Self { inner: config }
    }
}

#[pymethods]
impl PyXseConfig {
    /// Gets the XSE acronym.
    #[getter]
    fn acronym(&self) -> &str {
        &self.inner.acronym
    }

    /// Gets the compatible XSE version string.
    #[getter]
    fn compatible_version(&self) -> &str {
        &self.inner.compatible_version
    }

    /// Gets the loader executable name.
    #[getter]
    fn loader(&self) -> &str {
        &self.inner.loader
    }

    /// Gets the script hashes as a tuple of (filename, hash) pairs.
    #[getter]
    fn script_hashes(&self) -> Vec<(String, String)> {
        self.inner.script_hashes.clone()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "XseConfig(acronym='{}', compatible_version='{}')",
            self.inner.acronym, self.inner.compatible_version
        )
    }
}

/// Version range for compatibility matching.
///
/// Attributes:
///     min_version: Minimum version string (inclusive).
///     max_version: Maximum version string (inclusive).
///
/// Example:
///     >>> og = registry.get_by_id("FO4_OG")
///     >>> if og.compatible_range:
///     ...     print(og.compatible_range.min_version)
#[pyclass(name = "CompatibleRange")]
#[derive(Clone)]
pub struct PyCompatibleRange {
    inner: core::CompatibleRange,
}

impl From<core::CompatibleRange> for PyCompatibleRange {
    fn from(range: core::CompatibleRange) -> Self {
        Self { inner: range }
    }
}

#[pymethods]
impl PyCompatibleRange {
    /// Gets the minimum version string.
    #[getter]
    fn min_version(&self) -> String {
        self.inner.min_version.to_string()
    }

    /// Gets the maximum version string.
    #[getter]
    fn max_version(&self) -> String {
        self.inner.max_version.to_string()
    }

    /// Check if a version string falls within this range.
    ///
    /// Args:
    ///     version_str: Version string to check.
    ///
    /// Returns:
    ///     True if the version is within the range (inclusive).
    ///
    /// Raises:
    ///     ValueError: If the version string is invalid.
    fn contains(&self, version_str: &str) -> PyResult<bool> {
        let v = core::GameVersion::parse(version_str).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid version: {e}"))
        })?;
        Ok(self.inner.contains(&v))
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "CompatibleRange(min='{}', max='{}')",
            self.inner.min_version, self.inner.max_version
        )
    }
}

/// Crash generator configuration for a specific version.
///
/// Attributes:
///     version: Version string of the crash generator (e.g., "1.28.6").
///     name: Display name (e.g., "Buffout 4").
///     description: Description of this crash generator version.
///     download_url: Nexus Mods or other download URL.
///     compatible_range: Optional game version range restriction.
///
/// Example:
///     >>> configs = registry.get_crashgen_configs("FO4_OG")
///     >>> for c in configs:
///     ...     print(f"{c.name} v{c.version}")
#[pyclass(name = "CrashgenConfig")]
#[derive(Clone)]
pub struct PyCrashgenConfig {
    inner: core::CrashgenConfig,
}

impl From<core::CrashgenConfig> for PyCrashgenConfig {
    fn from(config: core::CrashgenConfig) -> Self {
        Self { inner: config }
    }
}

#[pymethods]
impl PyCrashgenConfig {
    /// Gets the crash generator version string.
    #[getter]
    fn version(&self) -> &str {
        &self.inner.version
    }

    /// Gets the display name.
    #[getter]
    fn name(&self) -> &str {
        &self.inner.name
    }

    /// Gets the description.
    #[getter]
    fn description(&self) -> &str {
        &self.inner.description
    }

    /// Gets the download URL.
    #[getter]
    fn download_url(&self) -> &str {
        &self.inner.download_url
    }

    /// Gets the compatible range, if any.
    #[getter]
    fn compatible_range(&self) -> Option<PyCompatibleRange> {
        self.inner
            .compatible_range
            .clone()
            .map(PyCompatibleRange::from)
    }

    /// Check if this crash generator is compatible with a game version.
    ///
    /// Args:
    ///     version_str: Game version string to check.
    ///
    /// Returns:
    ///     True if compatible (or no range restriction).
    ///
    /// Raises:
    ///     ValueError: If the version string is invalid.
    fn is_compatible_with(&self, version_str: &str) -> PyResult<bool> {
        let v = core::GameVersion::parse(version_str).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid version: {e}"))
        })?;
        Ok(self.inner.is_compatible_with(&v))
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "CrashgenConfig(version='{}', name='{}')",
            self.inner.version, self.inner.name
        )
    }
}

/// Configuration for handling unknown/unsupported versions.
///
/// Attributes:
///     strategy: Matching strategy ("nearest_match", "strict", or "default_only").
///     log_level: Log level for warnings ("debug", "warning", or "error").
///
/// Example:
///     >>> handling = registry.unknown_version_handling
///     >>> print(handling.strategy)
///     nearest_match
#[pyclass(name = "UnknownVersionHandling")]
#[derive(Clone)]
pub struct PyUnknownVersionHandling {
    inner: core::UnknownVersionHandling,
}

impl From<core::UnknownVersionHandling> for PyUnknownVersionHandling {
    fn from(handling: core::UnknownVersionHandling) -> Self {
        Self { inner: handling }
    }
}

#[pymethods]
impl PyUnknownVersionHandling {
    /// Gets the matching strategy as a string.
    #[getter]
    fn strategy(&self) -> &'static str {
        match self.inner.strategy {
            core::UnknownVersionStrategy::NearestMatch => "nearest_match",
            core::UnknownVersionStrategy::Strict => "strict",
            core::UnknownVersionStrategy::DefaultOnly => "default_only",
        }
    }

    /// Gets the log level as a string.
    #[getter]
    fn log_level(&self) -> &'static str {
        match self.inner.log_level {
            core::LogLevel::Debug => "debug",
            core::LogLevel::Warning => "warning",
            core::LogLevel::Error => "error",
        }
    }

    /// Gets the default version ID for a game.
    ///
    /// Args:
    ///     game: Game identifier (e.g., "Fallout4").
    ///
    /// Returns:
    ///     Default version ID string, or None.
    fn get_default(&self, game: &str) -> Option<String> {
        self.inner.get_default(game).map(String::from)
    }

    /// Gets all defaults as a dictionary.
    #[getter]
    fn defaults(&self) -> std::collections::HashMap<String, String> {
        self.inner.defaults.clone()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "UnknownVersionHandling(strategy='{}', log_level='{}')",
            self.strategy(),
            self.log_level()
        )
    }
}

/// Complete version information for a game version.
///
/// Attributes:
///     id: Unique identifier (e.g., "FO4_OG", "FO4_NG", "FO4_VR").
///     game: Game identifier (e.g., "Fallout4").
///     is_vr: Whether this is a VR version.
///     version: Version string (e.g., "1.10.163.0").
///     display_name: Human-readable display name.
///     short_name: Short identifier (e.g., "OG", "NG", "VR").
///     description: Description of this version.
///     address_library: Address Library configuration, if applicable.
///     xse: Script Extender configuration, if applicable.
///     compatible_range: Version range for matching, if applicable.
///     priority: Priority for matching (higher = preferred).
///     deprecated: Whether this version is deprecated.
///     exe_hash: SHA-256 hash of the game executable, or None.
///     crashgen_versions: Tuple of CrashgenConfig objects.
///
/// Example:
///     >>> og = registry.get_by_id("FO4_OG")
///     >>> print(og.display_name)
///     Fallout 4 Original
///     >>> print(og.version)
///     1.10.163.0
#[pyclass(name = "VersionInfo")]
#[derive(Clone)]
pub struct PyVersionInfo {
    inner: core::VersionInfo,
}

impl From<core::VersionInfo> for PyVersionInfo {
    fn from(info: core::VersionInfo) -> Self {
        Self { inner: info }
    }
}

#[pymethods]
impl PyVersionInfo {
    /// Gets the unique identifier.
    #[getter]
    fn id(&self) -> &str {
        &self.inner.id
    }

    /// Gets the game identifier.
    #[getter]
    fn game(&self) -> &str {
        &self.inner.game
    }

    /// Gets whether this is a VR version.
    #[getter]
    fn is_vr(&self) -> bool {
        self.inner.is_vr
    }

    /// Gets the version string.
    #[getter]
    fn version(&self) -> String {
        self.inner.version.to_string()
    }

    /// Gets the version string (alias for compatibility).
    #[getter]
    fn version_string(&self) -> String {
        self.inner.version_string()
    }

    /// Gets the human-readable display name.
    #[getter]
    fn display_name(&self) -> &str {
        &self.inner.display_name
    }

    /// Gets the short name.
    #[getter]
    fn short_name(&self) -> &str {
        &self.inner.short_name
    }

    /// Gets the description.
    #[getter]
    fn description(&self) -> &str {
        &self.inner.description
    }

    /// Gets the Address Library configuration, if applicable.
    #[getter]
    fn address_library(&self) -> Option<PyAddressLibraryConfig> {
        self.inner
            .address_library
            .clone()
            .map(PyAddressLibraryConfig::from)
    }

    /// Gets the Script Extender configuration, if applicable.
    #[getter]
    fn xse(&self) -> Option<PyXseConfig> {
        self.inner.xse.clone().map(PyXseConfig::from)
    }

    /// Gets the compatible range, if applicable.
    #[getter]
    fn compatible_range(&self) -> Option<PyCompatibleRange> {
        self.inner
            .compatible_range
            .clone()
            .map(PyCompatibleRange::from)
    }

    /// Gets the priority.
    #[getter]
    fn priority(&self) -> i32 {
        self.inner.priority
    }

    /// Gets whether this version is deprecated.
    #[getter]
    fn deprecated(&self) -> bool {
        self.inner.deprecated
    }

    /// Gets the SHA-256 hash of the game executable.
    #[getter]
    fn exe_hash(&self) -> Option<&str> {
        self.inner.exe_hash.as_deref()
    }

    /// Gets crash generator configurations as a list.
    #[getter]
    fn crashgen_versions(&self) -> Vec<PyCrashgenConfig> {
        self.inner
            .crashgen_versions
            .iter()
            .cloned()
            .map(PyCrashgenConfig::from)
            .collect()
    }

    /// Get crash generator versions as simple version strings.
    ///
    /// Returns:
    ///     Tuple of version strings.
    fn get_crashgen_version_strings(&self) -> Vec<String> {
        self.inner
            .get_crashgen_version_strings()
            .into_iter()
            .map(String::from)
            .collect()
    }

    /// Get a specific CrashgenConfig by its version string.
    ///
    /// Args:
    ///     crashgen_version: The crash generator version to look up.
    ///
    /// Returns:
    ///     The CrashgenConfig, or None if not found.
    fn get_crashgen_for_version(&self, crashgen_version: &str) -> Option<PyCrashgenConfig> {
        self.inner
            .get_crashgen_for_version(crashgen_version)
            .cloned()
            .map(PyCrashgenConfig::from)
    }

    /// Get crash generators compatible with a specific game version.
    ///
    /// Args:
    ///     game_version_str: Game version string, or None to use this version's own version.
    ///
    /// Returns:
    ///     List of compatible CrashgenConfig objects.
    ///
    /// Raises:
    ///     ValueError: If the game version string is invalid.
    #[pyo3(signature = (game_version_str=None))]
    fn get_compatible_crashgens(
        &self,
        game_version_str: Option<&str>,
    ) -> PyResult<Vec<PyCrashgenConfig>> {
        let game_version = match game_version_str {
            Some(s) => Some(core::GameVersion::parse(s).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid version: {e}"))
            })?),
            None => None,
        };
        Ok(self
            .inner
            .get_compatible_crashgens(game_version.as_ref())
            .into_iter()
            .cloned()
            .map(PyCrashgenConfig::from)
            .collect())
    }

    /// Check if a detected version is compatible with this version.
    ///
    /// Args:
    ///     version_str: Detected version string to check.
    ///
    /// Returns:
    ///     True if compatible.
    ///
    /// Raises:
    ///     ValueError: If the version string is invalid.
    fn is_compatible_with(&self, version_str: &str) -> PyResult<bool> {
        let v = core::GameVersion::parse(version_str).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Invalid version: {e}"))
        })?;
        Ok(self.inner.is_compatible_with(&v))
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!(
            "VersionInfo(id='{}', version='{}', display_name='{}')",
            self.inner.id, self.inner.version, self.inner.display_name
        )
    }

    /// String representation.
    fn __str__(&self) -> String {
        format!("{} ({})", self.inner.display_name, self.inner.version)
    }

    /// Equality comparison by ID.
    fn __eq__(&self, other: &PyVersionInfo) -> bool {
        self.inner.id == other.inner.id
    }

    /// Hash by ID.
    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.inner.id.hash(&mut hasher);
        hasher.finish()
    }
}

/// Register model components with the Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyAddressLibraryConfig>()?;
    m.add_class::<PyXseConfig>()?;
    m.add_class::<PyCompatibleRange>()?;
    m.add_class::<PyCrashgenConfig>()?;
    m.add_class::<PyUnknownVersionHandling>()?;
    m.add_class::<PyVersionInfo>()?;
    Ok(())
}
