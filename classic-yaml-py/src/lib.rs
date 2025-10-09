//! Classic YAML Python Bindings
//!
//! This crate provides PyO3 bindings for classic-yaml-core.
//! It wraps the pure Rust business logic for Python consumption.
//!
//! ## Architecture
//! This is a THIN ADAPTER layer that:
//! - Delegates all business logic to classic-yaml-core
//! - Only handles Python ↔ Rust type conversions
//! - Maintains API compatibility with existing Python code

use classic_yaml_core::{YamlError, YamlOperations};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::path::Path;
use yaml_rust2::Yaml;

/// Python-facing YAML operations wrapper
#[pyclass(name = "RustYamlOperations")]
pub struct PyYamlOperations {
    inner: YamlOperations,
}

#[pymethods]
impl PyYamlOperations {
    #[new]
    fn new() -> PyResult<Self> {
        Ok(Self {
            inner: YamlOperations::new(),
        })
    }

    /// Parse YAML content from a string
    #[pyo3(signature = (content))]
    fn parse_yaml(&self, py: Python<'_>, content: &str) -> PyResult<Py<PyAny>> {
        let yaml = self.inner.parse_yaml(content).map_err(to_pyerr)?;
        yaml_to_python(py, &yaml)
    }

    /// Convert data to YAML string with format preservation
    #[pyo3(signature = (data))]
    fn dump_yaml(&self, py: Python<'_>, data: Py<PyAny>) -> PyResult<String> {
        let yaml = python_to_yaml(py, data)?;
        self.inner.dump_yaml(&yaml).map_err(to_pyerr)
    }

    /// Load YAML file with caching
    #[pyo3(signature = (path))]
    fn load_yaml_file(&self, py: Python<'_>, path: &str) -> PyResult<Py<PyAny>> {
        let yaml = self
            .inner
            .load_yaml_file(Path::new(path))
            .map_err(to_pyerr)?;
        yaml_to_python(py, &yaml)
    }

    /// Save data to YAML file with atomic write
    #[pyo3(signature = (path, data))]
    fn save_yaml_file(&self, py: Python<'_>, path: &str, data: Py<PyAny>) -> PyResult<()> {
        let yaml = python_to_yaml(py, data)?;
        self.inner
            .save_yaml_file(Path::new(path), &yaml)
            .map_err(to_pyerr)
    }

    /// Get a setting value by key path (dot notation)
    #[pyo3(signature = (data, key_path))]
    fn get_setting(
        &self,
        py: Python<'_>,
        data: Py<PyAny>,
        key_path: &str,
    ) -> PyResult<Option<Py<PyAny>>> {
        let yaml = python_to_yaml(py, data)?;
        match self.inner.get_setting(&yaml, key_path) {
            Some(value) => Ok(Some(yaml_to_python(py, &value)?)),
            None => Ok(None),
        }
    }

    /// Set a setting value by key path (dot notation)
    #[pyo3(signature = (data, key_path, value))]
    fn set_setting(
        &self,
        py: Python<'_>,
        data: Py<PyAny>,
        key_path: &str,
        value: Py<PyAny>,
    ) -> PyResult<Py<PyAny>> {
        let yaml = python_to_yaml(py, data)?;
        let new_value = python_to_yaml(py, value)?;
        let result = self
            .inner
            .set_setting(&yaml, key_path, new_value)
            .map_err(to_pyerr)?;
        yaml_to_python(py, &result)
    }

    /// Clear the YAML cache
    fn clear_cache(&self) {
        self.inner.clear_cache();
    }

    /// Get cache statistics
    fn get_cache_stats(&self) -> PyResult<HashMap<String, usize>> {
        Ok(self.inner.get_cache_stats())
    }
}

/// Convert yaml-rust2 Yaml to Python object
fn yaml_to_python(py: Python<'_>, yaml: &Yaml) -> PyResult<Py<PyAny>> {
    match yaml {
        Yaml::Null => Ok(py.None()),

        Yaml::Boolean(b) => Ok((*b).into_pyobject(py)?.as_any().clone().unbind()),

        Yaml::Integer(i) => Ok((*i).into_pyobject(py)?.as_any().clone().unbind()),

        Yaml::Real(s) => {
            // Parse string to f64
            let f = s.parse::<f64>().map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid float: {}", e))
            })?;
            Ok(f.into_pyobject(py)?.as_any().clone().unbind())
        }

        Yaml::String(s) => Ok(s.as_str().into_pyobject(py)?.as_any().clone().unbind()),

        Yaml::Array(arr) => {
            let mut items = Vec::new();
            for item in arr {
                items.push(yaml_to_python(py, item)?);
            }
            let list = PyList::new(py, items)?;
            Ok(list.unbind().into())
        }

        Yaml::Hash(hash) => {
            let dict = PyDict::new(py);
            for (k, v) in hash {
                let key_obj = yaml_to_python(py, k)?;
                let val_obj = yaml_to_python(py, v)?;
                dict.set_item(key_obj, val_obj)?;
            }
            Ok(dict.unbind().into())
        }

        Yaml::Alias(_) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Unresolved YAML alias",
        )),

        Yaml::BadValue => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid YAML value",
        )),
    }
}

/// Convert Python object to yaml-rust2 Yaml
fn python_to_yaml(py: Python<'_>, obj: Py<PyAny>) -> PyResult<Yaml> {
    let bound_obj = obj.bind(py);

    if bound_obj.is_none() {
        return Ok(Yaml::Null);
    }

    if let Ok(b) = bound_obj.extract::<bool>() {
        return Ok(Yaml::Boolean(b));
    }

    if let Ok(i) = bound_obj.extract::<i64>() {
        return Ok(Yaml::Integer(i));
    }

    if let Ok(f) = bound_obj.extract::<f64>() {
        return Ok(Yaml::Real(f.to_string()));
    }

    if let Ok(s) = bound_obj.extract::<String>() {
        return Ok(Yaml::String(s));
    }

    if let Ok(list) = bound_obj.downcast::<PyList>() {
        let mut arr = Vec::new();
        for item in list.iter() {
            arr.push(python_to_yaml(py, item.unbind())?);
        }
        return Ok(Yaml::Array(arr));
    }

    if let Ok(dict) = bound_obj.downcast::<PyDict>() {
        let mut hash = yaml_rust2::yaml::Hash::new();
        for (k, v) in dict.iter() {
            let key = python_to_yaml(py, k.unbind())?;
            let value = python_to_yaml(py, v.unbind())?;
            hash.insert(key, value);
        }
        return Ok(Yaml::Hash(hash));
    }

    Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(format!(
        "Cannot convert Python type to YAML: {:?}",
        bound_obj.get_type()
    )))
}

/// Convert YamlError to PyErr
fn to_pyerr(err: YamlError) -> PyErr {
    match err {
        YamlError::ParseError(msg) => {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Parse error: {}", msg))
        }
        YamlError::SerializeError(msg) => {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Serialize error: {}", msg))
        }
        YamlError::IoError(e) => PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()),
        YamlError::EmptyDocument => {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Empty YAML document")
        }
        YamlError::InvalidValue(msg) => {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid value: {}", msg))
        }
        YamlError::UnresolvedAlias => {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Unresolved YAML alias")
        }
        YamlError::InvalidKeyPath(msg) => {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid key path: {}", msg))
        }
        YamlError::TypeConversionError(msg) => PyErr::new::<pyo3::exceptions::PyTypeError, _>(
            format!("Type conversion error: {}", msg),
        ),
    }
}

/// Python module initialization
#[pymodule]
fn classic_yaml(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyYamlOperations>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
