//! Classic Config Python Bindings
//!
//! This crate provides thin PyO3 bindings for classic-config-core.
//! It contains ONLY type conversions and Python wrappers - all business
//! logic is in classic-config-core.

use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PySet};
use classic_config_core::{YamlDataCore, ConfigError};
use classic_shared::get_runtime;
use std::path::PathBuf;

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
    fn new(
        yaml_dirs: Vec<PathBuf>,
        game: String,
        vr_mode: bool,
    ) -> PyResult<Self> {
        // Call pure Rust core using shared runtime
        let core = get_runtime().block_on(async {
            YamlDataCore::load_from_yaml_files(yaml_dirs, game, vr_mode).await
        }).map_err(to_pyerr)?;

        Ok(Self { inner: core })
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
            self.inner.crashgen_name.split('_').next().unwrap_or("unknown"),
            self.inner.classic_version,
            !self.inner.crashgen_latest_vr.is_empty()
        )
    }
}

/// Convert ConfigError to Python exception
fn to_pyerr(err: ConfigError) -> PyErr {
    match err {
        ConfigError::InvalidInput(msg) => {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(msg)
        }
        ConfigError::IOError(msg) => {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(msg)
        }
        ConfigError::ParseError(msg) => {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(msg)
        }
        ConfigError::RuntimeError(msg) => {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(msg)
        }
    }
}

/// Python API function to create YamlData
///
/// This is a convenience function for Python code that wants to
/// use a functional style instead of instantiating the class.
#[pyfunction]
#[pyo3(signature = (yaml_dirs, game, vr_mode))]
pub fn create_yamldata(
    yaml_dirs: Vec<PathBuf>,
    game: String,
    vr_mode: bool,
) -> PyResult<PyYamlData> {
    PyYamlData::new(yaml_dirs, game, vr_mode)
}

/// Initialize the classic_config Python module
#[pymodule]
fn classic_config(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyYamlData>()?;
    m.add_function(wrap_pyfunction!(create_yamldata, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
