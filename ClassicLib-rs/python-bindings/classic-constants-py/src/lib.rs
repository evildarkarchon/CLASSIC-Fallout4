//! Python bindings for classic-constants-core.
//!
//! This module provides Python access to all application constants,
//! YAML file enumerations, game identifiers, and Fallout 4 version
//! variants defined in the core constants crate.
//!
//! For version information, use the `classic_version` module instead.
//!
//! # Python Usage
//!
//! ```python
//! from classic_constants import (
//!     YamlFile, GameId, Fallout4Version,
//!     SETTINGS_IGNORE_NONE, must_not_be_none
//! )
//!
//! # Use YAML file enumeration
//! settings_file = YamlFile.Settings
//! print(settings_file.as_str())
//!
//! # Use game identifiers
//! game = GameId.Fallout4
//! print(game.exe_name())
//!
//! # Use Fallout 4 version variants (new in v8.0)
//! version = Fallout4Version.NextGen
//! print(version.display_name())  # "Next-Gen"
//! print(version.is_vr())  # False
//!
//! # For version constants, use classic_version instead
//! import classic_version
//! print(classic_version.is_known_fallout4_version((1, 10, 163)))
//! ```

use pyo3::prelude::*;

/// Python wrapper for YAML file enumeration.
///
/// Each variant corresponds to a specific YAML configuration file used by CLASSIC.
///
/// # Python Examples
///
/// ```python
/// from classic_constants import YamlFile
///
/// settings = YamlFile.Settings
/// print(settings.as_str())  # "Settings"
/// print(settings.description())  # "CLASSIC Settings.yaml"
/// ```
#[pyclass(module = "classic_constants", name = "YamlFile")]
#[derive(Clone)]
pub struct PyYamlFile {
    inner: classic_constants_core::YamlFile,
}

#[pymethods]
impl PyYamlFile {
    /// CLASSIC Data/databases/CLASSIC Main.yaml
    #[classattr]
    #[allow(non_snake_case)]
    fn Main() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Main,
        }
    }

    /// CLASSIC Settings.yaml
    #[classattr]
    #[allow(non_snake_case)]
    fn Settings() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Settings,
        }
    }

    /// CLASSIC Ignore.yaml
    #[classattr]
    #[allow(non_snake_case)]
    fn Ignore() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Ignore,
        }
    }

    /// CLASSIC Data/databases/CLASSIC {Game}.yaml
    #[classattr]
    #[allow(non_snake_case)]
    fn Game() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Game,
        }
    }

    /// CLASSIC Data/CLASSIC {Game} Local.yaml
    #[classattr]
    #[allow(non_snake_case)]
    fn GameLocal() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::GameLocal,
        }
    }

    /// tests/test_settings.yaml (for testing only)
    #[classattr]
    #[allow(non_snake_case)]
    fn Test() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Test,
        }
    }

    /// User config dir/CLASSIC-Fallout4/cache.yaml (persistent cache for uvx)
    #[classattr]
    #[allow(non_snake_case)]
    fn Cache() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Cache,
        }
    }

    /// Get the string representation of the YAML file variant.
    ///
    /// # Returns
    ///
    /// The variant name as a string (e.g., "Main", "Settings").
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import YamlFile
    ///
    /// assert YamlFile.Main.as_str() == "Main"
    /// assert YamlFile.Settings.as_str() == "Settings"
    /// ```
    fn as_str(&self) -> &'static str {
        self.inner.as_str()
    }

    /// Get a human-readable description of the YAML file.
    ///
    /// # Returns
    ///
    /// A description string including the typical file path.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import YamlFile
    ///
    /// desc = YamlFile.Main.description()
    /// assert "CLASSIC Main.yaml" in desc
    /// ```
    fn description(&self) -> &'static str {
        self.inner.description()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!("YamlFile.{}", self.inner.as_str())
    }

    /// String conversion.
    fn __str__(&self) -> &'static str {
        self.inner.as_str()
    }

    /// Equality comparison.
    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    /// Hash support.
    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        self.inner.hash(&mut hasher);
        hasher.finish()
    }
}

/// Python wrapper for game identifiers.
///
/// Each variant corresponds to a Bethesda game supported by CLASSIC.
///
/// # Python Examples
///
/// ```python
/// from classic_constants import GameId
///
/// game = GameId.Fallout4
/// print(game.as_str())  # "Fallout4"
/// print(game.exe_name())  # "Fallout4.exe"
/// print(game.is_vr())  # False
/// ```
#[pyclass(module = "classic_constants", name = "GameId")]
#[derive(Clone)]
pub struct PyGameId {
    inner: classic_constants_core::GameId,
}

#[pymethods]
impl PyGameId {
    /// Fallout 4 (base game)
    #[classattr]
    #[allow(non_snake_case)]
    fn Fallout4() -> Self {
        Self {
            inner: classic_constants_core::GameId::Fallout4,
        }
    }

    /// Fallout 4 VR
    #[classattr]
    #[allow(non_snake_case)]
    fn Fallout4VR() -> Self {
        Self {
            inner: classic_constants_core::GameId::Fallout4VR,
        }
    }

    /// Skyrim Special Edition
    #[classattr]
    #[allow(non_snake_case)]
    fn Skyrim() -> Self {
        Self {
            inner: classic_constants_core::GameId::Skyrim,
        }
    }

    /// Starfield
    #[classattr]
    #[allow(non_snake_case)]
    fn Starfield() -> Self {
        Self {
            inner: classic_constants_core::GameId::Starfield,
        }
    }

    /// Get the string representation of the game identifier.
    ///
    /// # Returns
    ///
    /// The game name as a string (e.g., "Fallout4", "Skyrim").
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import GameId
    ///
    /// assert GameId.Fallout4.as_str() == "Fallout4"
    /// assert GameId.Fallout4VR.as_str() == "Fallout4VR"
    /// ```
    fn as_str(&self) -> &'static str {
        self.inner.as_str()
    }

    /// Get the executable name for this game.
    ///
    /// # Returns
    ///
    /// The game executable filename (e.g., "Fallout4.exe").
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import GameId
    ///
    /// assert GameId.Fallout4.exe_name() == "Fallout4.exe"
    /// assert GameId.Skyrim.exe_name() == "SkyrimSE.exe"
    /// ```
    fn exe_name(&self) -> &'static str {
        self.inner.exe_name()
    }

    /// Check if this is a VR game.
    ///
    /// # Returns
    ///
    /// `True` if this is a VR variant, `False` otherwise.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import GameId
    ///
    /// assert not GameId.Fallout4.is_vr()
    /// assert GameId.Fallout4VR.is_vr()
    /// ```
    fn is_vr(&self) -> bool {
        self.inner.is_vr()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!("GameId.{}", self.inner.as_str())
    }

    /// String conversion.
    fn __str__(&self) -> &'static str {
        self.inner.as_str()
    }

    /// Equality comparison.
    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    /// Hash support.
    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        self.inner.hash(&mut hasher);
        hasher.finish()
    }
}

/// Python wrapper for Fallout 4 version variants.
///
/// Represents the different versions of Fallout 4 that CLASSIC supports.
/// This replaces the legacy VR Mode toggle with a proper version enum.
///
/// # Variants
///
/// - `Original` (OG) - Pre-Next-Gen Update version (before April 2024)
/// - `NextGen` (NG) - Next-Gen Update version (April 2024+)
/// - `Vr` - Fallout 4 VR
///
/// # Python Examples
///
/// ```python
/// from classic_constants import Fallout4Version
///
/// version = Fallout4Version.NextGen
/// print(version.display_name())  # "Next-Gen"
/// print(version.is_vr())  # False
/// print(version.exe_name())  # "Fallout4.exe"
/// print(version.steam_app_id())  # 377160
///
/// # VR version
/// vr = Fallout4Version.Vr
/// print(vr.is_vr())  # True
/// print(vr.exe_name())  # "Fallout4VR.exe"
/// print(vr.steam_app_id())  # 611660
///
/// # Get all versions
/// all_versions = Fallout4Version.all()
/// for v in all_versions:
///     print(f"{v.display_name()}: {v.steam_app_id()}")
/// ```
///
/// .. versionadded:: 8.0.0
#[pyclass(module = "classic_constants", name = "Fallout4Version")]
#[derive(Clone)]
pub struct PyFallout4Version {
    inner: classic_constants_core::Fallout4Version,
}

#[pymethods]
impl PyFallout4Version {
    /// Original (OG) Fallout 4 - pre-Next-Gen Update version.
    ///
    /// This is the classic Fallout 4 version before the April 2024
    /// Next-Gen Update. Uses F4SE OG and has version 1.10.163.
    #[classattr]
    #[allow(non_snake_case)]
    fn Original() -> Self {
        Self {
            inner: classic_constants_core::Fallout4Version::Original,
        }
    }

    /// Next-Gen (NG) Fallout 4 - post-April 2024 version.
    ///
    /// This is the updated Fallout 4 version from the April 2024
    /// Next-Gen Update. Uses F4SE NG and has version 1.10.984+.
    #[classattr]
    #[allow(non_snake_case)]
    fn NextGen() -> Self {
        Self {
            inner: classic_constants_core::Fallout4Version::NextGen,
        }
    }

    /// Anniversary Edition (AE) Fallout 4 - version 1.11.137+.
    ///
    /// This is the Anniversary Edition branch which is actively developed.
    /// Version range starts at 1.11.137 and continues to evolve.
    #[classattr]
    #[allow(non_snake_case)]
    fn AnniversaryEdition() -> Self {
        Self {
            inner: classic_constants_core::Fallout4Version::AnniversaryEdition,
        }
    }

    /// Fallout 4 VR.
    ///
    /// The VR variant of Fallout 4. Has its own executable
    /// and Steam app ID.
    #[allow(non_snake_case)]
    #[classattr]
    fn Vr() -> Self {
        Self {
            inner: classic_constants_core::Fallout4Version::Vr,
        }
    }

    /// Create a Fallout4Version from a string.
    ///
    /// # Arguments
    ///
    /// * `s` - A string like "Original", "OG", "NextGen", "NG", "Vr", "VR"
    ///
    /// # Returns
    ///
    /// A Fallout4Version instance, or raises ValueError if invalid.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// v1 = Fallout4Version.from_str("NextGen")
    /// v2 = Fallout4Version.from_str("NG")  # Same as NextGen
    /// v3 = Fallout4Version.from_str("VR")
    /// ```
    #[staticmethod]
    fn from_str(s: &str) -> PyResult<Self> {
        use std::str::FromStr;
        classic_constants_core::Fallout4Version::from_str(s)
            .map(|inner| Self { inner })
            .map_err(pyo3::exceptions::PyValueError::new_err)
    }

    /// Get all Fallout 4 version variants.
    ///
    /// # Returns
    ///
    /// A list of all Fallout4Version variants.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// for version in Fallout4Version.all():
    ///     print(version.display_name())
    /// ```
    #[staticmethod]
    fn all() -> Vec<Self> {
        classic_constants_core::Fallout4Version::all()
            .iter()
            .map(|&v| Self { inner: v })
            .collect()
    }

    /// Check if this is the VR version.
    ///
    /// # Returns
    ///
    /// `True` if this is Fallout 4 VR, `False` otherwise.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert not Fallout4Version.Original.is_vr()
    /// assert not Fallout4Version.NextGen.is_vr()
    /// assert Fallout4Version.Vr.is_vr()
    /// ```
    fn is_vr(&self) -> bool {
        self.inner.is_vr()
    }

    /// Check if this is a standard (non-VR) version.
    ///
    /// # Returns
    ///
    /// `True` if this is Original or NextGen, `False` if VR.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert Fallout4Version.Original.is_standard()
    /// assert Fallout4Version.NextGen.is_standard()
    /// assert not Fallout4Version.Vr.is_standard()
    /// ```
    fn is_standard(&self) -> bool {
        self.inner.is_standard()
    }

    /// Get the executable name for this version.
    ///
    /// # Returns
    ///
    /// The game executable filename.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert Fallout4Version.Original.exe_name() == "Fallout4.exe"
    /// assert Fallout4Version.NextGen.exe_name() == "Fallout4.exe"
    /// assert Fallout4Version.Vr.exe_name() == "Fallout4VR.exe"
    /// ```
    fn exe_name(&self) -> &'static str {
        self.inner.exe_name()
    }

    /// Get the Documents folder name for this version.
    ///
    /// # Returns
    ///
    /// The folder name under My Documents.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert Fallout4Version.Original.docs_folder_name() == "Fallout4"
    /// assert Fallout4Version.Vr.docs_folder_name() == "Fallout4VR"
    /// ```
    fn docs_folder_name(&self) -> &'static str {
        self.inner.docs_folder_name()
    }

    /// Get the Steam app ID for this version.
    ///
    /// # Returns
    ///
    /// The Steam application ID.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert Fallout4Version.Original.steam_app_id() == 377160
    /// assert Fallout4Version.NextGen.steam_app_id() == 377160
    /// assert Fallout4Version.Vr.steam_app_id() == 611660
    /// ```
    fn steam_app_id(&self) -> u32 {
        self.inner.steam_app_id()
    }

    /// Get the game version string for this variant.
    ///
    /// Returns the version from the VersionRegistry. The version is fetched
    /// dynamically from the registry for data-driven configuration.
    ///
    /// # Returns
    ///
    /// The version string (e.g., "1.10.163.0").
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// # Version strings come from VersionRegistry
    /// og_version = Fallout4Version.Original.version()
    /// ng_version = Fallout4Version.NextGen.version()
    /// vr_version = Fallout4Version.Vr.version()
    /// ```
    fn version(&self) -> String {
        self.inner.game_version().to_string()
    }

    /// Get the VersionRegistry ID for this version variant.
    ///
    /// This is the key used to look up the full VersionInfo from the registry.
    ///
    /// # Returns
    ///
    /// The registry ID string (e.g., "FO4_OG", "FO4_NG", "FO4_VR").
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert Fallout4Version.Original.registry_id() == "FO4_OG"
    /// assert Fallout4Version.NextGen.registry_id() == "FO4_NG"
    /// assert Fallout4Version.Vr.registry_id() == "FO4_VR"
    /// ```
    fn registry_id(&self) -> &'static str {
        self.inner.registry_id()
    }

    /// Get the short name from the VersionRegistry.
    ///
    /// # Returns
    ///
    /// The short name (e.g., "OG", "NG", "VR").
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert Fallout4Version.Original.short_name() == "OG"
    /// assert Fallout4Version.NextGen.short_name() == "NG"
    /// assert Fallout4Version.Vr.short_name() == "VR"
    /// ```
    fn short_name(&self) -> &'static str {
        self.inner.short_name()
    }

    /// Get the script extender acronym for this version.
    ///
    /// # Returns
    ///
    /// The XSE acronym (e.g., "F4SE").
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert Fallout4Version.Original.xse_acronym() == "F4SE"
    /// assert Fallout4Version.Vr.xse_acronym() == "F4SEVR"
    /// ```
    fn xse_acronym(&self) -> &'static str {
        self.inner.xse_acronym()
    }

    /// Get a human-readable display name for this version.
    ///
    /// # Returns
    ///
    /// A user-friendly version name.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert Fallout4Version.Original.display_name() == "Original (OG)"
    /// assert Fallout4Version.NextGen.display_name() == "Next-Gen (NG)"
    /// assert Fallout4Version.Vr.display_name() == "VR"
    /// ```
    fn display_name(&self) -> &'static str {
        self.inner.display_name()
    }

    /// Get the string representation of this version.
    ///
    /// # Returns
    ///
    /// The canonical version name.
    ///
    /// # Examples
    ///
    /// ```python
    /// from classic_constants import Fallout4Version
    ///
    /// assert Fallout4Version.Original.as_str() == "Original"
    /// assert Fallout4Version.NextGen.as_str() == "NextGen"
    /// assert Fallout4Version.Vr.as_str() == "Vr"
    /// ```
    fn as_str(&self) -> &'static str {
        self.inner.as_str()
    }

    /// String representation.
    fn __repr__(&self) -> String {
        format!("Fallout4Version.{}", self.inner.as_str())
    }

    /// String conversion.
    fn __str__(&self) -> &'static str {
        self.inner.as_str()
    }

    /// Equality comparison.
    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    /// Hash support.
    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        self.inner.hash(&mut hasher);
        hasher.finish()
    }
}

/// Check if a settings key should not allow None values.
///
/// # Arguments
///
/// * `key` - The settings key to check
///
/// # Returns
///
/// `True` if the key must not be None, `False` otherwise.
///
/// # Examples
///
/// ```python
/// from classic_constants import must_not_be_none
///
/// assert must_not_be_none("SCAN Custom Path")
/// assert must_not_be_none("Root_Folder_Game")
/// assert not must_not_be_none("Some Other Setting")
/// ```
#[pyfunction]
fn must_not_be_none(key: &str) -> bool {
    classic_constants_core::must_not_be_none(key)
}

/// Python module for application constants.
///
/// This module provides zero-cost compile-time constants and type-safe enumerations
/// used throughout CLASSIC:
///
/// - YAML file enumeration (YamlFile)
/// - Game identifiers (GameId)
/// - Fallout 4 version variants (Fallout4Version)
/// - Settings constants (SETTINGS_IGNORE_NONE)
///
/// For version detection and parsing, use the `classic_version` module.
///
/// # Examples
///
/// ```python
/// import classic_constants
///
/// # Use YAML file enumeration
/// settings = classic_constants.YamlFile.Settings
/// print(settings.as_str())
///
/// # Use game identifiers
/// game = classic_constants.GameId.Fallout4
/// print(game.exe_name())
///
/// # Use Fallout 4 version variants
/// version = classic_constants.Fallout4Version.NextGen
/// print(version.display_name())
///
/// # Check settings validation
/// if classic_constants.must_not_be_none("Root_Folder_Game"):
///     print("This setting must have a value")
/// ```
#[pymodule]
fn classic_constants(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add enum classes
    m.add_class::<PyYamlFile>()?;
    m.add_class::<PyGameId>()?;
    m.add_class::<PyFallout4Version>()?; // New in v8.0

    // Add NULL_VERSION constant
    m.add("NULL_VERSION", "0.0.0")?;

    // Add settings constants
    m.add(
        "SETTINGS_IGNORE_NONE",
        vec![
            "SCAN Custom Path",
            "MODS Folder Path",
            "INI Folder Path",
            "Root_Folder_Game",
            "Root_Folder_Docs",
        ],
    )?;

    // Add helper functions
    m.add_function(wrap_pyfunction!(must_not_be_none, m)?)?;

    // Module metadata
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add(
        "__doc__",
        "Python bindings for CLASSIC application constants",
    )?;

    Ok(())
}
