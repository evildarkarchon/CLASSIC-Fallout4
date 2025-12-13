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
//!
//! ## Complete Usage Example
//!
//! ```python
//! from classic_core import yaml
//!
//! # Create YAML operations handler
//! ops = yaml.YamlOperations()
//!
//! # Parse YAML from string
//! yaml_content = """
//! game: Fallout4
//! version: 1.10.163
//! settings:
//!   fcx_mode: true
//!   show_values: false
//! plugins:
//!   - Fallout4.esm
//!   - MyMod.esp
//! """
//!
//! data = ops.parse_yaml(yaml_content)
//!
//! # Access nested settings using dot notation
//! fcx_mode = ops.get_setting(data, "settings.fcx_mode")
//! print(f"FCX Mode: {fcx_mode}")  # Output: True
//!
//! # Modify settings
//! data = ops.set_setting(data, "settings.show_values", True)
//!
//! # Save to file with atomic write
//! ops.save_yaml_file("config.yaml", data)
//!
//! # Load from file with caching (15-30x faster than ruamel.yaml)
//! cached_data = ops.load_yaml_file("config.yaml")
//!
//! # Convert back to YAML string
//! yaml_string = ops.dump_yaml(data)
//!
//! # Clear cache when needed (e.g., after external file modifications)
//! ops.clear_cache()
//!
//! # Check cache statistics
//! stats = ops.get_cache_stats()
//! print(f"Cache hits: {stats['hits']}, misses: {stats['misses']}")
//! ```
//!
//! ## Performance Characteristics
//!
//! - **Parsing**: 15-30x faster than ruamel.yaml
//! - **File loading with caching**: 50-100x faster on cache hits
//! - **Atomic writes**: Crash-safe file saving with temporary files
//! - **Memory efficient**: Minimal Python ↔ Rust conversion overhead
//!
//! ## Thread Safety
//!
//! The YamlOperations wrapper is thread-safe and can be shared across Python threads.
//! Internal caching uses thread-safe data structures (DashMap) for concurrent access.
//!
//! ```python
//! from classic_core import yaml
//! from threading import Thread
//!
//! ops = yaml.YamlOperations()
//!
//! def worker(file_path):
//!     # Safe to call from multiple threads
//!     data = ops.load_yaml_file(file_path)
//!     # Process data...
//!
//! threads = [Thread(target=worker, args=(f"config{i}.yaml",)) for i in range(10)]
//! for t in threads:
//!     t.start()
//! for t in threads:
//!     t.join()
//! ```

use classic_shared::{define_exceptions, register_exceptions, PathLike};
use classic_yaml_core::{YamlError, YamlOperations};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::path::PathBuf;
use yaml_rust2::Yaml;

// Define the standard 3-tier exception hierarchy using the shared macro
define_exceptions!(
    module: classic_yaml,
    base: RustYamlError,
    io: RustYamlIOError,
    parse: RustYamlParseError
);

/// Convert YamlError to PyErr using custom exception types
///
/// Maps Rust YamlError variants to Python exception types from
/// ClassicLib.integration.exceptions for better error handling.
fn to_pyerr(err: YamlError) -> PyErr {
    match err {
        // I/O errors map to RustYamlIOError
        YamlError::IoError(e) => RustYamlIOError::new_err(format!("Failed to read file: {}", e)),

        // Parse/validation errors map to RustYamlParseError
        YamlError::ParseError(msg) => {
            RustYamlParseError::new_err(format!("Failed to parse YAML: {}", msg))
        }
        YamlError::SerializeError(msg) => {
            RustYamlParseError::new_err(format!("Serialize error: {}", msg))
        }
        YamlError::EmptyDocument => RustYamlParseError::new_err("Empty YAML document"),
        YamlError::InvalidValue(msg) => {
            RustYamlParseError::new_err(format!("Invalid value: {}", msg))
        }
        YamlError::UnresolvedAlias => RustYamlParseError::new_err("Unresolved YAML alias"),
        YamlError::InvalidKeyPath(msg) => {
            RustYamlParseError::new_err(format!("Invalid key path: {}", msg))
        }
        YamlError::TypeConversionError(msg) => {
            RustYamlParseError::new_err(format!("Type conversion error: {}", msg))
        }
    }
}

/// Python-facing YAML operations wrapper
#[pyclass(name = "YamlOperations")]
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
    ///
    /// Accepts both string paths and pathlib.Path objects without requiring manual conversion.
    ///
    /// # Arguments
    /// * `path` - Path to YAML file (str or pathlib.Path)
    ///
    /// # Examples
    /// ```python
    /// # Both work without conversion:
    /// data = ops.load_yaml_file("config.yaml")           # str
    /// data = ops.load_yaml_file(Path("config.yaml"))     # pathlib.Path
    /// ```
    #[pyo3(signature = (path))]
    fn load_yaml_file(&self, py: Python<'_>, path: PathLike) -> PyResult<Py<PyAny>> {
        let path_buf: PathBuf = path.into();
        let yaml = self.inner.load_yaml_file(&path_buf).map_err(to_pyerr)?;
        yaml_to_python(py, &yaml)
    }

    /// Save data to YAML file with atomic write
    ///
    /// Accepts both string paths and pathlib.Path objects without requiring manual conversion.
    ///
    /// # Arguments
    /// * `path` - Path to YAML file (str or pathlib.Path)
    /// * `data` - YAML data to save
    ///
    /// # Examples
    /// ```python
    /// # Both work without conversion:
    /// ops.save_yaml_file("config.yaml", data)           # str
    /// ops.save_yaml_file(Path("config.yaml"), data)     # pathlib.Path
    /// ```
    #[pyo3(signature = (path, data))]
    fn save_yaml_file(&self, py: Python<'_>, path: PathLike, data: Py<PyAny>) -> PyResult<()> {
        let path_buf: PathBuf = path.into();
        let yaml = python_to_yaml(py, data)?;
        self.inner
            .save_yaml_file(&path_buf, &yaml)
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

    /// Extract a string value from YAML using a dot-separated key path
    ///
    /// This is a convenience method for getting string values from nested YAML structures.
    /// It navigates through the YAML document using dot notation (e.g., "parent.child.field")
    /// and returns the string value or a default if the key doesn't exist or isn't a string.
    ///
    /// # Arguments
    /// * `data` - YAML data to extract from
    /// * `key_path` - Dot-separated path (e.g., "parent.child.field")
    /// * `default` - Default value if key not found or not a string
    ///
    /// # Returns
    /// String value or default
    ///
    /// # Example
    /// ```python
    /// ops = YamlOperations()
    /// yaml_str = """
    /// game:
    ///   name: Fallout4
    ///   version: "1.10.163"
    /// """
    /// data = ops.parse_yaml(yaml_str)
    ///
    /// name = ops.get_string_value(data, "game.name", "Unknown")
    /// # Returns: "Fallout4"
    ///
    /// missing = ops.get_string_value(data, "game.missing", "default")
    /// # Returns: "default"
    /// ```
    #[pyo3(signature = (data, key_path, default))]
    fn get_string_value(
        &self,
        py: Python<'_>,
        data: Py<PyAny>,
        key_path: &str,
        default: &str,
    ) -> PyResult<String> {
        let yaml = python_to_yaml(py, data)?;
        Ok(self.inner.get_string_value(&yaml, key_path, default))
    }

    /// Extract a vector of strings from YAML using a dot-separated key path
    ///
    /// This is a convenience method for getting string arrays from nested YAML structures.
    /// It navigates through the YAML document using dot notation and returns a vector
    /// of strings, or an empty vector if the key doesn't exist or isn't an array.
    ///
    /// # Arguments
    /// * `data` - YAML data to extract from
    /// * `key_path` - Dot-separated path (e.g., "parent.child.array")
    ///
    /// # Returns
    /// List of strings, or empty list if key not found or not an array
    ///
    /// # Example
    /// ```python
    /// ops = YamlOperations()
    /// yaml_str = """
    /// game:
    ///   plugins:
    ///     - plugin1.esp
    ///     - plugin2.esp
    ///     - plugin3.esp
    /// """
    /// data = ops.parse_yaml(yaml_str)
    ///
    /// plugins = ops.get_vec_value(data, "game.plugins")
    /// # Returns: ["plugin1.esp", "plugin2.esp", "plugin3.esp"]
    /// ```
    #[pyo3(signature = (data, key_path))]
    fn get_vec_value(
        &self,
        py: Python<'_>,
        data: Py<PyAny>,
        key_path: &str,
    ) -> PyResult<Vec<String>> {
        let yaml = python_to_yaml(py, data)?;
        Ok(self.inner.get_vec_value(&yaml, key_path))
    }

    /// Extract a hashmap from YAML using a dot-separated key path
    ///
    /// This is a convenience method for getting string key-value maps from nested YAML structures.
    /// It navigates through the YAML document using dot notation and returns a dict,
    /// or an empty dict if the key doesn't exist or isn't a hash.
    ///
    /// # Arguments
    /// * `data` - YAML data to extract from
    /// * `key_path` - Dot-separated path (e.g., "parent.child.map")
    ///
    /// # Returns
    /// Dictionary of string key-value pairs, or empty dict if key not found or not a hash
    ///
    /// # Example
    /// ```python
    /// ops = YamlOperations()
    /// yaml_str = """
    /// game:
    ///   mods:
    ///     mod1: "Description 1"
    ///     mod2: "Description 2"
    /// """
    /// data = ops.parse_yaml(yaml_str)
    ///
    /// mods = ops.get_hashmap_value(data, "game.mods")
    /// # Returns: {"mod1": "Description 1", "mod2": "Description 2"}
    /// ```
    #[pyo3(signature = (data, key_path))]
    fn get_hashmap_value(
        &self,
        py: Python<'_>,
        data: Py<PyAny>,
        key_path: &str,
    ) -> PyResult<HashMap<String, String>> {
        let yaml = python_to_yaml(py, data)?;
        Ok(self.inner.get_hashmap_value(&yaml, key_path))
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

/// Python module initialization
#[pymodule]
fn classic_yaml(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyYamlOperations>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Register custom exception types using the shared macro
    register_exceptions!(m, RustYamlError, RustYamlIOError, RustYamlParseError);

    Ok(())
}
