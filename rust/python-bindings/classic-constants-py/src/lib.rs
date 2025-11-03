//! Python bindings for classic-constants-core.
//!
//! This module provides Python access to all application constants, version
//! identifiers, YAML file enumerations, and game identifiers defined in the
//! core constants crate.
//!
//! # Python Usage
//!
//! ```python
//! from classic_constants import (
//!     YamlFile, GameId,
//!     FALLOUT4_OG_VERSION, FALLOUT4_NG_VERSION,
//!     SETTINGS_IGNORE_NONE, must_not_be_none
//! )
//!
//! # Use version constants
//! print(f"OG Version: {FALLOUT4_OG_VERSION}")
//!
//! # Use YAML file enumeration
//! settings_file = YamlFile.Settings
//! print(settings_file.as_str())
//!
//! # Use game identifiers
//! game = GameId.Fallout4
//! print(game.exe_name())
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
    fn Main() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Main,
        }
    }

    /// CLASSIC Settings.yaml
    #[classattr]
    fn Settings() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Settings,
        }
    }

    /// CLASSIC Ignore.yaml
    #[classattr]
    fn Ignore() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Ignore,
        }
    }

    /// CLASSIC Data/databases/CLASSIC {Game}.yaml
    #[classattr]
    fn Game() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Game,
        }
    }

    /// CLASSIC Data/CLASSIC {Game} Local.yaml
    #[classattr]
    fn GameLocal() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::GameLocal,
        }
    }

    /// tests/test_settings.yaml (for testing only)
    #[classattr]
    fn Test() -> Self {
        Self {
            inner: classic_constants_core::YamlFile::Test,
        }
    }

    /// User config dir/CLASSIC-Fallout4/cache.yaml (persistent cache for uvx)
    #[classattr]
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
    fn Fallout4() -> Self {
        Self {
            inner: classic_constants_core::GameId::Fallout4,
        }
    }

    /// Fallout 4 VR
    #[classattr]
    fn Fallout4VR() -> Self {
        Self {
            inner: classic_constants_core::GameId::Fallout4VR,
        }
    }

    /// Skyrim Special Edition
    #[classattr]
    fn Skyrim() -> Self {
        Self {
            inner: classic_constants_core::GameId::Skyrim,
        }
    }

    /// Starfield
    #[classattr]
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
/// - Version constants (FALLOUT4_OG_VERSION, FALLOUT4_NG_VERSION, etc.)
/// - YAML file enumeration (YamlFile)
/// - Game identifiers (GameId)
/// - Settings constants (SETTINGS_IGNORE_NONE)
///
/// # Examples
///
/// ```python
/// import classic_constants
///
/// # Access version constants
/// print(f"OG Version: {classic_constants.FALLOUT4_OG_VERSION}")
/// print(f"NG Version: {classic_constants.FALLOUT4_NG_VERSION}")
///
/// # Use YAML file enumeration
/// settings = classic_constants.YamlFile.Settings
/// print(settings.as_str())
///
/// # Use game identifiers
/// game = classic_constants.GameId.Fallout4
/// print(game.exe_name())
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

    // Add version constants as strings (since semver::Version doesn't have Python bindings)
    m.add("NULL_VERSION", "0.0.0")?;
    m.add("FALLOUT4_OG_VERSION", "1.10.163")?;
    m.add("FALLOUT4_NG_VERSION", "1.10.984")?;
    m.add("FALLOUT4_VR_VERSION", "1.2.72")?;
    m.add("F4SE_OG_VERSION", "0.6.23")?;
    m.add("F4SE_NG_VERSION", "0.7.2")?;

    // Add version arrays
    m.add("FALLOUT4_VERSIONS", vec!["1.10.163", "1.10.984"])?;
    m.add("F4SE_VERSIONS", vec!["0.6.23", "0.7.2"])?;

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
