//! Python bindings for the unified YAML settings cache and YAML operations.
//!
//! This module provides Python access to the Rust-accelerated YAML settings cache
//! (sync + async loading, cache management, validators) AND the YAML operations
//! class that was formerly in `classic-yaml-py`. The two crates were merged in
//! plan 01-02 (D-05/D-06) after `classic-yaml-core` was absorbed into
//! `classic-settings-core` in plan 01-01.

use classic_settings_core::{
    self as core, Yaml, YamlError, YamlOperations,
    clear_global_yaml_cache as core_clear_yaml_cache, merge_keys as core_merge_keys,
    reset_yaml_cache_stats as core_reset_yaml_cache_stats,
    yaml_cache_stats as core_yaml_cache_stats,
};
use classic_shared::{PathLike, define_exceptions, register_exceptions, without_gil};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::path::PathBuf;

mod yaml_file;

// ============================================================================
// Exception hierarchy (folded in from classic-yaml-py — D-06)
// ============================================================================
//
// Three yaml-specific exception types preserved from classic-yaml-py:
//   - RustYamlError (base — inherits PyException)
//   - RustYamlIOError (inherits RustYamlError)
//   - RustYamlParseError (inherits RustYamlError)
//
// There is NO RustYamlSerializeError. YamlError::SerializeError maps to
// RustYamlParseError in `yaml_err_to_pyerr` below (matching the yaml-py
// behavior at yaml-py/src/lib.rs lines 117-119).

define_exceptions!(
    module: classic_settings,
    base: RustYamlError,
    io: RustYamlIOError,
    parse: RustYamlParseError
);

/// Convert `YamlError` to a `PyErr` using the 3-tier exception hierarchy.
///
/// Preserved verbatim from classic-yaml-py/src/lib.rs `to_pyerr`:
/// `SerializeError` routes to `RustYamlParseError` — there is no separate
/// `RustYamlSerializeError` exception.
fn yaml_err_to_pyerr(err: YamlError) -> PyErr {
    match err {
        YamlError::IoError(e) => RustYamlIOError::new_err(format!("Failed to read file: {}", e)),
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

/// Convert Rust Yaml to Python object.
///
/// Converts a yaml_rust2::Yaml value into appropriate Python types:
/// - Yaml::Hash -> dict
/// - Yaml::Array -> list
/// - Yaml::String -> str
/// - Yaml::Integer -> int
/// - Yaml::Real -> float
/// - Yaml::Boolean -> bool
/// - Yaml::Null -> None
fn yaml_to_py(py: Python, yaml: &Yaml) -> PyResult<Py<PyAny>> {
    use pyo3::IntoPyObject;

    match yaml {
        Yaml::Real(s) => {
            // Try to parse as float
            if let Ok(f) = s.parse::<f64>() {
                Ok(f.into_pyobject(py)?.unbind().into())
            } else {
                // If parsing fails, return as string
                Ok(s.into_pyobject(py)?.unbind().into())
            }
        }
        Yaml::Integer(i) => Ok(i.into_pyobject(py)?.unbind().into()),
        Yaml::String(s) => Ok(s.into_pyobject(py)?.unbind().into()),
        Yaml::Boolean(b) => Ok(b.into_pyobject(py)?.to_owned().unbind().into()),
        Yaml::Array(arr) => {
            let list = PyList::empty(py);
            for item in arr {
                list.append(yaml_to_py(py, item)?)?;
            }
            Ok(list.unbind().into())
        }
        Yaml::Hash(hash) => {
            let dict = PyDict::new(py);
            for (key, value) in hash {
                let py_key = yaml_to_py(py, key)?;
                let py_value = yaml_to_py(py, value)?;
                dict.set_item(py_key, py_value)?;
            }
            Ok(dict.unbind().into())
        }
        Yaml::Alias(_) => {
            // Aliases are resolved by the parser, so this shouldn't happen
            Ok(py.None())
        }
        Yaml::Null => Ok(py.None()),
        Yaml::BadValue => {
            // BadValue indicates a parsing error
            Err(pyo3::exceptions::PyValueError::new_err(
                "Invalid YAML value",
            ))
        }
    }
}

/// Convert a Python object to a yaml-rust2 Yaml value.
///
/// Mirrors `python_to_yaml` from the former classic-yaml-py module. Needed by
/// `PyYamlOperations` to round-trip Python data through the Rust YAML API.
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

    if let Ok(list) = bound_obj.clone().into_any().cast_into::<PyList>() {
        let mut arr = Vec::new();
        for item in list.iter() {
            arr.push(python_to_yaml(py, item.unbind())?);
        }
        return Ok(Yaml::Array(arr));
    }

    if let Ok(dict) = bound_obj.clone().into_any().cast_into::<PyDict>() {
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

// ============================================================================
// YamlOperations wrapper (folded in from classic-yaml-py — D-05/D-06)
// ============================================================================

/// Python-facing YAML operations wrapper.
///
/// Stateful YAML handler with caching. Delegates to
/// `classic_settings_core::YamlOperations`. All methods that do file I/O or
/// heavy serialization release the GIL via `without_gil` so concurrent Python
/// threads can keep running.
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

    /// Parse YAML content from a string.
    ///
    /// Releases GIL during parsing for content >1KB to allow concurrent Python threads.
    #[pyo3(signature = (content))]
    fn parse_yaml(&self, py: Python<'_>, content: &str) -> PyResult<Py<PyAny>> {
        let content_owned = content.to_string();
        let yaml = if content.len() > 1024 {
            without_gil(py, || self.inner.parse_yaml(&content_owned)).map_err(yaml_err_to_pyerr)?
        } else {
            self.inner
                .parse_yaml(&content_owned)
                .map_err(yaml_err_to_pyerr)?
        };
        yaml_to_py(py, &yaml)
    }

    /// Convert data to YAML string with format preservation.
    ///
    /// Releases GIL during serialization to allow concurrent Python threads.
    #[pyo3(signature = (data))]
    fn dump_yaml(&self, py: Python<'_>, data: Py<PyAny>) -> PyResult<String> {
        let yaml = python_to_yaml(py, data)?;
        without_gil(py, || self.inner.dump_yaml(&yaml)).map_err(yaml_err_to_pyerr)
    }

    /// Load YAML file with caching.
    ///
    /// Accepts both string paths and pathlib.Path objects.
    #[pyo3(signature = (path))]
    fn load_yaml_file(&self, py: Python<'_>, path: PathLike) -> PyResult<Py<PyAny>> {
        let path_buf: PathBuf = path.into();
        let yaml =
            without_gil(py, || self.inner.load_yaml_file(&path_buf)).map_err(yaml_err_to_pyerr)?;
        yaml_to_py(py, &yaml)
    }

    /// Save data to YAML file with atomic write.
    #[pyo3(signature = (path, data))]
    fn save_yaml_file(&self, py: Python<'_>, path: PathLike, data: Py<PyAny>) -> PyResult<()> {
        let path_buf: PathBuf = path.into();
        let yaml = python_to_yaml(py, data)?;
        without_gil(py, || self.inner.save_yaml_file(&path_buf, &yaml)).map_err(yaml_err_to_pyerr)
    }

    /// Get a setting value by key path (dot notation).
    #[pyo3(signature = (data, key_path))]
    fn get_setting(
        &self,
        py: Python<'_>,
        data: Py<PyAny>,
        key_path: &str,
    ) -> PyResult<Option<Py<PyAny>>> {
        let yaml = python_to_yaml(py, data)?;
        match self.inner.get_setting(&yaml, key_path) {
            Some(value) => Ok(Some(yaml_to_py(py, &value)?)),
            None => Ok(None),
        }
    }

    /// Set a setting value by key path (dot notation).
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
            .map_err(yaml_err_to_pyerr)?;
        yaml_to_py(py, &result)
    }

    /// Clear the YAML cache.
    fn clear_cache(&self) {
        self.inner.clear_cache();
    }

    /// Get cache statistics for the YAML-file cache.
    ///
    /// This delegates to `classic_settings_core::yaml_cache_stats` (distinct
    /// from the settings cache stats returned by `classic_settings.cache_stats`).
    /// Plan 01-01 renamed `cache_stats` → `yaml_cache_stats` in settings-core
    /// per D-03, so this must call `yaml_cache_stats()` to preserve the
    /// original yaml-py semantics — calling the unrelated `cache_stats()` would
    /// silently return the settings cache numbers.
    fn get_cache_stats(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let stats = core_yaml_cache_stats();
        let dict = PyDict::new(py);
        dict.set_item("hits", stats.hits)?;
        dict.set_item("misses", stats.misses)?;
        dict.set_item("hit_rate", stats.hit_rate)?;
        dict.set_item("size", stats.size)?;
        dict.set_item("capacity", stats.capacity)?;
        Ok(dict.unbind().into())
    }

    /// Extract a string value from YAML using a dot-separated key path.
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

    /// Extract a vector of strings from YAML using a dot-separated key path.
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

    /// Extract a string-to-string map from YAML using a dot-separated key path.
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

// ============================================================================
// Module-level yaml helpers (folded in from classic-yaml-py)
// ============================================================================

/// Clear the global YAML-file cache.
#[pyfunction]
fn clear_global_yaml_cache() {
    core_clear_yaml_cache();
}

/// Reset the global YAML-file cache hit/miss counters.
#[pyfunction]
fn reset_yaml_cache_stats() {
    core_reset_yaml_cache_stats();
}

/// Get statistics for the global YAML-file cache.
///
/// Distinct from `cache_stats()` — that one covers the settings cache.
#[pyfunction]
fn yaml_cache_stats(py: Python) -> PyResult<Py<PyAny>> {
    let stats = core_yaml_cache_stats();
    let dict = PyDict::new(py);
    dict.set_item("hits", stats.hits)?;
    dict.set_item("misses", stats.misses)?;
    dict.set_item("hit_rate", stats.hit_rate)?;
    dict.set_item("size", stats.size)?;
    dict.set_item("capacity", stats.capacity)?;
    Ok(dict.unbind().into())
}

/// Apply YAML merge keys (`<<:`) to a document.
///
/// Takes a parsed YAML value (typically obtained from `YamlOperations.parse_yaml`)
/// and returns a new value with all merge keys expanded.
#[pyfunction]
fn merge_keys(py: Python, data: Py<PyAny>) -> PyResult<Py<PyAny>> {
    let yaml = python_to_yaml(py, data)?;
    let merged = core_merge_keys(yaml).map_err(yaml_err_to_pyerr)?;
    yaml_to_py(py, &merged)
}

/// Load YAML settings synchronously.
///
/// Loads a YAML file, caches it with the given key, and returns the parsed documents
/// as Python objects (dicts/lists).
///
/// Args:
///     key: Cache key (typically the file path or a logical name)
///     path: Path to the YAML file
///
/// Returns:
///     List of parsed YAML documents as Python objects
///
/// Raises:
///     IOError: If the file cannot be read
///     ValueError: If the YAML is invalid
///
/// Example:
///     >>> import classic_settings
///     >>> docs = classic_settings.load_settings_sync("config", "config.yaml")
///     >>> print(docs[0]["key"])
///     value
#[pyfunction]
fn load_settings_sync(py: Python, key: &str, path: &str) -> PyResult<Py<PyAny>> {
    let path_buf = PathBuf::from(path);
    let docs = core::load_settings_sync(key, &path_buf)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    let list = PyList::empty(py);
    for doc in docs.iter() {
        list.append(yaml_to_py(py, doc)?)?;
    }

    Ok(list.unbind().into())
}

/// Load YAML settings asynchronously.
///
/// Loads a YAML file asynchronously, caches it with the given key, and returns the parsed
/// documents as Python objects (dicts/lists).
///
/// Args:
///     key: Cache key (typically the file path or a logical name)
///     path: Path to the YAML file
///
/// Returns:
///     Coroutine that yields a list of parsed YAML documents as Python objects
///
/// Raises:
///     IOError: If the file cannot be read
///     ValueError: If the YAML is invalid
///
/// Example:
///     >>> import classic_settings
///     >>> import asyncio
///     >>> docs = await classic_settings.load_settings_async("config", "config.yaml")
///     >>> print(docs[0]["key"])
///     value
#[pyfunction]
fn load_settings_async(py: Python, key: String, path: String) -> PyResult<Py<PyAny>> {
    let fut = pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let path_buf = PathBuf::from(path);
        let docs = core::load_settings_async(&key, &path_buf)
            .await
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        Python::attach(|py| {
            let list = PyList::empty(py);
            for doc in docs.iter() {
                list.append(yaml_to_py(py, doc)?)?;
            }
            // Convert to Py<PyAny> which is 'static and implements IntoPyObject
            Ok::<Py<PyAny>, PyErr>(list.unbind().into())
        })
    })?;

    // future_into_py returns Bound<PyAny>, convert to Py<PyAny>
    Ok(fut.unbind())
}

/// Load multiple YAML files in batch (synchronous).
///
/// Loads multiple YAML files and caches them. Each path becomes its own cache key.
///
/// Args:
///     paths: List of file paths to load
///
/// Returns:
///     Number of files successfully loaded and cached
///
/// Raises:
///     IOError: If any file cannot be read
///     ValueError: If any YAML is invalid
///
/// Example:
///     >>> import classic_settings
///     >>> count = classic_settings.load_batch_sync(["config1.yaml", "config2.yaml"])
///     >>> print(f"Loaded {count} files")
///     Loaded 2 files
#[pyfunction]
fn load_batch_sync(paths: Vec<String>) -> PyResult<usize> {
    let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
    let path_refs: Vec<&std::path::Path> = path_bufs.iter().map(|p| p.as_path()).collect();

    core::load_batch_sync(&path_refs)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
}

/// Load multiple YAML files in batch (asynchronous).
///
/// Loads multiple YAML files concurrently and caches them. Each path becomes its own cache key.
///
/// Args:
///     paths: List of file paths to load
///
/// Returns:
///     Coroutine that yields the number of files successfully loaded and cached
///
/// Raises:
///     IOError: If any file cannot be read
///     ValueError: If any YAML is invalid
///
/// Example:
///     >>> import classic_settings
///     >>> import asyncio
///     >>> count = await classic_settings.load_batch_async(["config1.yaml", "config2.yaml"])
///     >>> print(f"Loaded {count} files")
///     Loaded 2 files
#[pyfunction]
fn load_batch_async(py: Python, paths: Vec<String>) -> PyResult<Py<PyAny>> {
    let fut = pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
        let path_refs: Vec<&std::path::Path> = path_bufs.iter().map(|p| p.as_path()).collect();

        let count = core::load_batch_async(&path_refs)
            .await
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        // usize implements IntoPyObject
        Ok::<usize, PyErr>(count)
    })?;

    // future_into_py returns Bound<PyAny>, convert to Py<PyAny>
    Ok(fut.unbind())
}

/// Get cached settings by key.
///
/// Retrieves cached YAML documents by key. Returns None if the key is not in the cache.
///
/// Args:
///     key: Cache key to look up
///
/// Returns:
///     List of parsed YAML documents as Python objects, or None if not cached
///
/// Example:
///     >>> import classic_settings
///     >>> classic_settings.load_settings_sync("config", "config.yaml")
///     >>> docs = classic_settings.get_cached("config")
///     >>> print(docs is not None)
///     True
#[pyfunction]
fn get_cached(py: Python, key: &str) -> PyResult<Option<Py<PyAny>>> {
    match core::get_cached(key) {
        Some(docs) => {
            let list = PyList::empty(py);
            for doc in docs.iter() {
                list.append(yaml_to_py(py, doc)?)?;
            }
            Ok(Some(list.unbind().into()))
        }
        None => Ok(None),
    }
}

/// Check if a key exists in the cache.
///
/// Args:
///     key: Cache key to check
///
/// Returns:
///     True if the key exists, False otherwise
///
/// Example:
///     >>> import classic_settings
///     >>> classic_settings.load_settings_sync("config", "config.yaml")
///     >>> classic_settings.is_cached("config")
///     True
///     >>> classic_settings.is_cached("nonexistent")
///     False
#[pyfunction]
fn is_cached(key: &str) -> bool {
    core::is_cached(key)
}

/// Invalidate (remove) a cached entry.
///
/// Removes a key from the cache. Returns True if the key existed and was removed.
///
/// Args:
///     key: Cache key to invalidate
///
/// Returns:
///     True if the key was removed, False if it didn't exist
///
/// Example:
///     >>> import classic_settings
///     >>> classic_settings.load_settings_sync("config", "config.yaml")
///     >>> classic_settings.invalidate("config")
///     True
///     >>> classic_settings.is_cached("config")
///     False
#[pyfunction]
fn invalidate(key: &str) -> bool {
    core::invalidate(key)
}

/// Clear all cached settings.
///
/// Removes all entries from the cache.
///
/// Example:
///     >>> import classic_settings
///     >>> classic_settings.load_settings_sync("config1", "config1.yaml")
///     >>> classic_settings.load_settings_sync("config2", "config2.yaml")
///     >>> classic_settings.clear_cache()
///     >>> classic_settings.cache_size()
///     0
#[pyfunction]
fn clear_cache() {
    core::clear_cache();
}

/// Get the number of cached entries.
///
/// Returns:
///     The number of entries currently in the cache
///
/// Example:
///     >>> import classic_settings
///     >>> classic_settings.load_settings_sync("config", "config.yaml")
///     >>> classic_settings.cache_size()
///     1
#[pyfunction]
fn cache_size() -> usize {
    core::cache_size()
}

/// Get all cache keys.
///
/// Returns:
///     List of all keys currently in the cache
///
/// Example:
///     >>> import classic_settings
///     >>> classic_settings.load_settings_sync("config1", "config1.yaml")
///     >>> classic_settings.load_settings_sync("config2", "config2.yaml")
///     >>> keys = classic_settings.cache_keys()
///     >>> len(keys)
///     2
#[pyfunction]
fn cache_keys() -> Vec<String> {
    core::cache_keys()
}

/// Get current cache statistics.
///
/// Returns a dictionary with:
/// - hits: Number of cache hits
/// - misses: Number of cache misses
/// - hit_rate: Hit rate as fraction (0.0 to 1.0)
/// - size: Current number of entries
/// - capacity: Maximum bounded cache capacity
///
/// Example:
///     >>> import classic_settings
///     >>> stats = classic_settings.cache_stats()
///     >>> print(f"Hit rate: {stats['hit_rate'] * 100:.1f}%")
#[pyfunction]
fn cache_stats(py: Python) -> PyResult<Py<PyAny>> {
    let stats = core::cache_stats();
    let dict = PyDict::new(py);
    dict.set_item("hits", stats.hits)?;
    dict.set_item("misses", stats.misses)?;
    dict.set_item("hit_rate", stats.hit_rate)?;
    dict.set_item("size", stats.size)?;
    dict.set_item("capacity", stats.capacity)?;

    Ok(dict.unbind().into())
}

/// Reset cache statistics.
///
/// Resets hit and miss counters to zero. Useful for testing or
/// starting fresh measurements.
///
/// Example:
///     >>> import classic_settings
///     >>> classic_settings.reset_cache_stats()
///     >>> stats = classic_settings.cache_stats()
///     >>> assert stats['hits'] == 0
#[pyfunction]
fn reset_cache_stats() {
    core::reset_cache_stats();
}

/// Python module for YAML settings cache.
///
/// This module provides Rust-accelerated YAML settings caching with both
/// synchronous and asynchronous APIs. It integrates with the ONE RUNTIME RULE
/// to ensure all async operations use the shared global Tokio runtime.
///
/// # Synchronous API
///
/// - `load_settings_sync(key, path)`: Load and cache a YAML file
/// - `load_batch_sync(paths)`: Load multiple files
///
/// # Asynchronous API
///
/// - `load_settings_async(key, path)`: Load and cache a YAML file (async)
/// - `load_batch_async(paths)`: Load multiple files (async)
///
/// # Cache Management
///
/// - `get_cached(key)`: Get cached settings
/// - `is_cached(key)`: Check if key exists
/// - `invalidate(key)`: Remove a key
/// - `clear_cache()`: Clear all entries
/// - `cache_size()`: Get number of entries
/// - `cache_keys()`: Get all keys
/// - `cache_stats()`: Get cache performance statistics
/// - `reset_cache_stats()`: Reset hit/miss counters
///
/// Example:
///     >>> import classic_settings
///     >>> # Sync API
///     >>> docs = classic_settings.load_settings_sync("game_config", "config.yaml")
///     >>> print(docs[0]["game"])
///     Fallout4
///     >>>
///     >>> # Async API
///     >>> import asyncio
///     >>> async def load_async():
///     ...     docs = await classic_settings.load_settings_async("game_config", "config.yaml")
///     ...     print(docs[0]["game"])
///     >>> asyncio.run(load_async())
///     Fallout4
#[pymodule]
fn classic_settings(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add functions
    m.add_function(wrap_pyfunction!(load_settings_sync, m)?)?;
    m.add_function(wrap_pyfunction!(load_settings_async, m)?)?;
    m.add_function(wrap_pyfunction!(load_batch_sync, m)?)?;
    m.add_function(wrap_pyfunction!(load_batch_async, m)?)?;
    m.add_function(wrap_pyfunction!(get_cached, m)?)?;
    m.add_function(wrap_pyfunction!(is_cached, m)?)?;
    m.add_function(wrap_pyfunction!(invalidate, m)?)?;
    m.add_function(wrap_pyfunction!(clear_cache, m)?)?;
    m.add_function(wrap_pyfunction!(cache_size, m)?)?;
    m.add_function(wrap_pyfunction!(cache_keys, m)?)?;
    m.add_function(wrap_pyfunction!(cache_stats, m)?)?;
    m.add_function(wrap_pyfunction!(reset_cache_stats, m)?)?;

    // Validator functions
    m.add_function(wrap_pyfunction!(validate_settings_structure, m)?)?;
    m.add_function(wrap_pyfunction!(validate_setting_value, m)?)?;
    m.add_function(wrap_pyfunction!(coerce_setting_value, m)?)?;

    // YAML operations class (folded in from classic-yaml-py)
    m.add_class::<PyYamlOperations>()?;
    yaml_file::register(m)?;

    // Module-level YAML helpers (folded in from classic-yaml-py)
    m.add_function(wrap_pyfunction!(clear_global_yaml_cache, m)?)?;
    m.add_function(wrap_pyfunction!(reset_yaml_cache_stats, m)?)?;
    m.add_function(wrap_pyfunction!(yaml_cache_stats, m)?)?;
    m.add_function(wrap_pyfunction!(merge_keys, m)?)?;

    // YAML exception hierarchy (folded in from classic-yaml-py — D-06)
    register_exceptions!(m, RustYamlError, RustYamlIOError, RustYamlParseError);

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}

/// Validate the structure of a YAML settings document.
///
/// Checks for common structural issues such as missing root keys,
/// non-mapping roots, and empty documents.
///
/// Args:
///     yaml_content: Raw YAML content string to validate
///
/// Returns:
///     List of dicts, each with 'severity' ('warning' or 'error') and 'message' keys.
///     An empty list means the document is valid.
///
/// Raises:
///     ValueError: If the YAML content cannot be parsed
///
/// Example:
///     >>> import classic_settings
///     >>> issues = classic_settings.validate_settings_structure("CLASSIC_Settings:\\n  key: value")
///     >>> assert len(issues) == 0  # Valid structure
///     >>> issues = classic_settings.validate_settings_structure("42")
///     >>> assert issues[0]['severity'] == 'error'
#[pyfunction]
fn validate_settings_structure(py: Python, yaml_content: &str) -> PyResult<Py<PyAny>> {
    use classic_settings_core::validators;
    use yaml_rust2::YamlLoader;

    let docs = YamlLoader::load_from_str(yaml_content)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid YAML: {}", e)))?;

    if docs.is_empty() {
        // No documents parsed -- treat as null/empty
        let issues = validators::validate_settings_structure(&Yaml::Null);
        return issues_to_py(py, &issues);
    }

    let issues = validators::validate_settings_structure(&docs[0]);
    issues_to_py(py, &issues)
}

/// Validate that a string value can be interpreted as the expected setting type.
///
/// Args:
///     value: The string value to validate
///     expected_type: One of 'int', 'bool', 'float', 'path', 'string'
///
/// Returns:
///     True if the value matches or can be coerced to the expected type
///
/// Raises:
///     ValueError: If expected_type is not a recognized type name
///
/// Example:
///     >>> import classic_settings
///     >>> classic_settings.validate_setting_value("42", "int")
///     True
///     >>> classic_settings.validate_setting_value("yes", "bool")
///     True
///     >>> classic_settings.validate_setting_value("hello", "int")
///     False
#[pyfunction]
fn validate_setting_value(value: &str, expected_type: &str) -> PyResult<bool> {
    let setting_type = parse_setting_type(expected_type)?;
    Ok(classic_settings_core::validators::validate_setting_value(
        value,
        setting_type,
    ))
}

/// Coerce a string value to the target setting type.
///
/// Attempts to convert the value to the expected type. Supports:
/// - 'int': Parses as integer
/// - 'bool': Accepts true/false, yes/no, 1/0, on/off (case-insensitive)
/// - 'float': Parses as floating-point
/// - 'path': Any non-empty string
/// - 'string': Always succeeds (identity conversion)
///
/// Args:
///     value: The string value to coerce
///     target_type: One of 'int', 'bool', 'float', 'path', 'string'
///
/// Returns:
///     The coerced value as the appropriate Python type (int, bool, float, or str)
///
/// Raises:
///     ValueError: If coercion fails or target_type is not recognized
///
/// Example:
///     >>> import classic_settings
///     >>> classic_settings.coerce_setting_value("42", "int")
///     42
///     >>> classic_settings.coerce_setting_value("yes", "bool")
///     True
///     >>> classic_settings.coerce_setting_value("3.14", "float")
///     3.14
#[pyfunction]
fn coerce_setting_value(py: Python, value: &str, target_type: &str) -> PyResult<Py<PyAny>> {
    use classic_settings_core::validators::{self, CoercedValue};
    use pyo3::IntoPyObject;

    let setting_type = parse_setting_type(target_type)?;
    let coerced = validators::coerce_setting_value(value, setting_type)
        .map_err(pyo3::exceptions::PyValueError::new_err)?;

    match coerced {
        CoercedValue::Int(v) => Ok(v.into_pyobject(py)?.unbind().into()),
        CoercedValue::Bool(v) => Ok(v.into_pyobject(py)?.to_owned().unbind().into()),
        CoercedValue::Float(v) => Ok(v.into_pyobject(py)?.unbind().into()),
        CoercedValue::Path(v) => Ok(v.into_pyobject(py)?.unbind().into()),
        CoercedValue::String(v) => Ok(v.into_pyobject(py)?.unbind().into()),
    }
}

/// Parse a string setting type name into the Rust enum.
fn parse_setting_type(type_name: &str) -> PyResult<classic_settings_core::validators::SettingType> {
    use classic_settings_core::validators::SettingType;
    match type_name.to_lowercase().as_str() {
        "int" | "integer" => Ok(SettingType::Int),
        "bool" | "boolean" => Ok(SettingType::Bool),
        "float" | "double" => Ok(SettingType::Float),
        "path" => Ok(SettingType::Path),
        "string" | "str" => Ok(SettingType::String),
        _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Unknown setting type '{}'. Expected one of: int, bool, float, path, string",
            type_name
        ))),
    }
}

/// Convert validation issues to Python list of dicts.
fn issues_to_py(
    py: Python,
    issues: &[classic_settings_core::validators::ValidationIssue],
) -> PyResult<Py<PyAny>> {
    use classic_settings_core::validators::IssueSeverity;

    let list = PyList::empty(py);
    for issue in issues {
        let dict = PyDict::new(py);
        dict.set_item(
            "severity",
            match issue.severity {
                IssueSeverity::Warning => "warning",
                IssueSeverity::Error => "error",
            },
        )?;
        dict.set_item("message", &issue.message)?;
        list.append(dict)?;
    }
    Ok(list.unbind().into())
}
