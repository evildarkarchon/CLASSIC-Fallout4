//! Classic Config Python Bindings
//!
//! This crate provides thin PyO3 bindings for classic-config-core.
//! It contains ONLY type conversions and Python wrappers - all business
//! logic is in classic-config-core.
//!
//! ## Complete Usage Example
//!
//! ```python
//! from classic_core import config
//! from pathlib import Path
//!
//! # Load all configuration from YAML files
//! yaml_dirs = [
//!     Path("YAML/Main"),
//!     Path("YAML/Games"),
//!     Path("YAML/Ignore"),
//! ]
//!
//! yamldata = config.YamlData(yaml_dirs, "Fallout4", False)
//!
//! # Access game configuration
//! print(f"Game: {yamldata.crashgen_name}")
//! print(f"Version: {yamldata.game_version}")
//! print(f"XSE: {yamldata.xse_acronym}")  # "F4SE"
//!
//! # Access ignore lists for filtering
//! ignore_plugins = yamldata.game_ignore_plugins  # ["Fallout4.esm", ...]
//! ignore_records = yamldata.game_ignore_records  # ["System", ...]
//! ignore_list = yamldata.ignore_list  # User-defined ignores
//!
//! # Access mod detection databases
//! core_mods = yamldata.game_mods_core  # Essential mods
//! freq_mods = yamldata.game_mods_freq  # Frequently problematic mods
//! conf_mods = yamldata.game_mods_conf  # Conflicting mod pairs
//! solu_mods = yamldata.game_mods_solu  # Solution mods
//!
//! # Access suspect pattern dictionaries
//! error_patterns = yamldata.suspects_error_list  # Error message patterns
//! stack_patterns = yamldata.suspects_stack_list  # Stack trace patterns
//!
//! # Access CLASSIC metadata
//! print(f"CLASSIC Version: {yamldata.classic_version}")
//! print(f"Date: {yamldata.classic_version_date}")
//!
//! # Functional API (alternative to class instantiation)
//! yamldata2 = config.create_yamldata(yaml_dirs, "Skyrim", False)
//! ```
//!
//! ## Performance Characteristics
//!
//! - **YAML loading**: Uses yaml-rust2 (15-30x faster than ruamel.yaml)
//! - **Async I/O**: Non-blocking file loading with Tokio
//! - **Single load**: Configuration loaded once, cached for lifetime of object
//! - **Memory efficient**: Rust data structures with minimal Python overhead
//!
//! ## Thread Safety
//!
//! YamlData instances are immutable after creation and thread-safe. They can be
//! shared across Python threads without additional synchronization.
//!
//! ```python
//! from classic_core import config
//! from threading import Thread
//! from pathlib import Path
//!
//! # Load configuration once
//! yamldata = config.YamlData([Path("YAML/Main")], "Fallout4", False)
//!
//! def worker(thread_id):
//!     # Safe to access from multiple threads
//!     mods = yamldata.game_mods_freq
//!     print(f"Thread {thread_id}: {len(mods)} mods")
//!
//! threads = [Thread(target=worker, args=(i,)) for i in range(10)]
//! for t in threads:
//!     t.start()
//! for t in threads:
//!     t.join()
//! ```

use classic_config_core::{ConfigError, YamlDataCore};
use classic_shared::{ResultExt, ToPyErr, define_exceptions, register_exceptions, without_gil};
use classic_shared_core::get_runtime;
use pyo3::exceptions::{PyIOError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PySet};
use std::path::PathBuf;

// Define the standard 3-tier exception hierarchy using the shared macro
define_exceptions!(
    module: classic_config,
    base: RustConfigError,
    io: RustConfigIOError,
    parse: RustConfigParseError
);

// Wrapper to satisfy orphan rules
struct PyConfigError(ConfigError);

// Implement ToPyErr for the local wrapper
impl ToPyErr for PyConfigError {
    type BaseException = PyRuntimeError;
    type IOException = PyIOError;
    type ParseException = PyValueError;

    fn to_pyerr(self) -> PyErr {
        match self.0 {
            ConfigError::IOError { context, source } => {
                Self::io_err(format!("{}: {}", context, source))
            }
            ConfigError::ParseError { context, source } => {
                Self::parse_err(format!("{}: {}", context, source))
            }
            ConfigError::EmptyDocument(doc_name) => {
                Self::parse_err(format!("Empty YAML document: {}", doc_name))
            }
            ConfigError::InvalidInput(msg) => Self::parse_err(format!("Invalid input: {}", msg)),
            ConfigError::RuntimeError(msg) => Self::base_err(format!("Runtime error: {}", msg)),
        }
    }
}

/// Python wrapper for YamlDataCore
///
/// This is a thin adapter that:
/// 1. Calls YamlDataCore::load_from_yaml_files (business logic)
/// 2. Converts Rust types (Vec, HashMap) to Python types (PyList, PyDict)
/// 3. Exposes fields as Python properties
#[pyclass(name = "YamlData")]
pub struct PyYamlData {
    /// The inner pure Rust data structure
    inner: YamlDataCore,
}

#[pymethods]
impl PyYamlData {
    #[new]
    #[pyo3(signature = (yaml_dirs, game, vr_mode))]
    fn new(py: Python<'_>, yaml_dirs: Vec<PathBuf>, game: String, vr_mode: bool) -> PyResult<Self> {
        // Call pure Rust core using shared runtime, releasing GIL during blocking I/O
        let core = without_gil(py, || {
            get_runtime().block_on(async {
                YamlDataCore::load_from_yaml_files(yaml_dirs, game, vr_mode).await
            })
        })
        .map_err(PyConfigError)
        .map_pyerr()?;

        Ok(Self { inner: core })
    }

    /// Create YamlData from YAML content strings (for testing without file I/O).
    ///
    /// This constructor is useful for unit tests and integration tests where you want
    /// to test YamlData parsing without needing actual YAML files on disk.
    ///
    /// Args:
    ///     main_content: Content of the main YAML configuration file
    ///     game_content: Content of the game-specific YAML configuration file
    ///     ignore_content: Content of the ignore list YAML configuration file
    ///     game: Game identifier (e.g., "Fallout4", "Skyrim")
    ///     vr_mode: Whether to load VR-specific configuration
    ///
    /// Returns:
    ///     YamlData instance with parsed configuration
    ///
    /// Raises:
    ///     RustConfigParseError: If any YAML content fails to parse
    #[staticmethod]
    #[pyo3(name = "from_yaml_content")]
    fn py_from_yaml_content(
        main_content: String,
        game_content: String,
        ignore_content: String,
        game: String,
        vr_mode: bool,
    ) -> PyResult<Self> {
        let inner = YamlDataCore::from_yaml_content(
            &main_content,
            &game_content,
            &ignore_content,
            game,
            vr_mode,
        )
        .map_err(PyConfigError)
        .map_pyerr()?;

        Ok(Self { inner })
    }

    // ========================================================================
    // Game Configuration Properties
    // ========================================================================

    #[getter]
    fn classic_game_hints(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.classic_game_hints)?;
        Ok(list.into())
    }

    #[getter]
    fn classic_records_list(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.classic_records_list)?;
        Ok(list.into())
    }

    #[getter]
    fn classic_version(&self) -> String {
        self.inner.classic_version.clone()
    }

    #[getter]
    fn classic_version_date(&self) -> String {
        self.inner.classic_version_date.clone()
    }

    // ========================================================================
    // Crashgen Configuration Properties
    // ========================================================================

    #[getter]
    fn crashgen_name(&self) -> String {
        self.inner.crashgen_name.clone()
    }

    #[getter]
    fn crashgen_latest_og(&self) -> String {
        self.inner.crashgen_latest_og.clone()
    }

    #[getter]
    fn crashgen_latest_vr(&self) -> String {
        self.inner.crashgen_latest_vr.clone()
    }

    #[getter]
    fn crashgen_ignore(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        // Convert Vec<String> to PySet (was a set in original Python)
        let list = PyList::new(py, &self.inner.crashgen_ignore)?;
        let py_set = PySet::new(py, list.iter())?;
        Ok(py_set.unbind().into())
    }

    // ========================================================================
    // Warning Properties
    // ========================================================================

    #[getter]
    fn warn_noplugins(&self) -> String {
        self.inner.warn_noplugins.clone()
    }

    #[getter]
    fn warn_outdated(&self) -> String {
        self.inner.warn_outdated.clone()
    }

    // ========================================================================
    // XSE Configuration
    // ========================================================================

    #[getter]
    fn xse_acronym(&self) -> String {
        self.inner.xse_acronym.clone()
    }

    // ========================================================================
    // Ignore Lists
    // ========================================================================

    #[getter]
    fn game_ignore_plugins(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.game_ignore_plugins)?;
        Ok(list.into())
    }

    #[getter]
    fn game_ignore_records(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.game_ignore_records)?;
        Ok(list.into())
    }

    #[getter]
    fn ignore_list(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let list = PyList::new(py, &self.inner.ignore_list)?;
        Ok(list.into())
    }

    // ========================================================================
    // Suspect Pattern Dictionaries
    // ========================================================================

    #[getter]
    fn suspects_error_list(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.suspects_error_list {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn suspects_stack_list(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.suspects_stack_list {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    // ========================================================================
    // Mod Database Dictionaries
    // ========================================================================

    #[getter]
    fn game_mods_conf(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_conf {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_core(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_core {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_core_folon(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_core_folon {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_freq(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_freq {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_opc2(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_opc2 {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    #[getter]
    fn game_mods_solu(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.game_mods_solu {
            dict.set_item(k, v)?;
        }
        Ok(dict.unbind())
    }

    // ========================================================================
    // UI Configuration
    // ========================================================================

    #[getter]
    fn autoscan_text(&self) -> String {
        self.inner.autoscan_text.clone()
    }

    // ========================================================================
    // Game Versions
    // ========================================================================

    #[getter]
    fn game_version(&self) -> String {
        self.inner.game_version.clone()
    }

    #[getter]
    fn game_version_new(&self) -> String {
        self.inner.game_version_new.clone()
    }

    #[getter]
    fn game_version_vr(&self) -> String {
        self.inner.game_version_vr.clone()
    }

    // ========================================================================
    // Python Special Methods
    // ========================================================================

    fn __repr__(&self) -> String {
        format!(
            "YamlData(game={}, version={}, vr_mode={})",
            self.inner
                .crashgen_name
                .split('_')
                .next()
                .unwrap_or("unknown"),
            self.inner.classic_version,
            !self.inner.crashgen_latest_vr.is_empty()
        )
    }
}

/// Python API function to create YamlData
///
/// This is a convenience function for Python code that wants to
/// use a functional style instead of instantiating the class.
#[pyfunction]
#[pyo3(signature = (yaml_dirs, game, vr_mode))]
pub fn create_yamldata(
    py: Python<'_>,
    yaml_dirs: Vec<PathBuf>,
    game: String,
    vr_mode: bool,
) -> PyResult<PyYamlData> {
    PyYamlData::new(py, yaml_dirs, game, vr_mode)
}

/// Clear the global YAML cache
///
/// This function clears all cached YAML data. It's primarily useful for
/// testing to ensure clean state between test runs.
#[pyfunction]
pub fn clear_yaml_cache() {
    classic_config_core::clear_global_yaml_cache();
}

/// Initialize the classic_config Python module
#[pymodule]
fn classic_config(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyYamlData>()?;
    m.add_function(wrap_pyfunction!(create_yamldata, m)?)?;
    m.add_function(wrap_pyfunction!(clear_yaml_cache, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Register custom exception types using the shared macro
    register_exceptions!(m, RustConfigError, RustConfigIOError, RustConfigParseError);

    Ok(())
}

/// Public registration function for use by facade modules
/// This allows classic-core to include config components in its submodule
pub fn register_config_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyYamlData>()?;
    m.add_function(wrap_pyfunction!(create_yamldata, m)?)?;
    m.add_function(wrap_pyfunction!(clear_yaml_cache, m)?)?;

    // Register custom exception types using the shared macro
    register_exceptions!(m, RustConfigError, RustConfigIOError, RustConfigParseError);

    Ok(())
}
