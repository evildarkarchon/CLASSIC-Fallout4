//! IndexMap conversion utilities for PyO3
//!
//! Provides helper functions to convert Python dicts to Rust IndexMaps,
//! preserving insertion order for Python parity.
//!
//! # Available Functions
//!
//! - [`pydict_to_indexmap_str`] - Convert `Dict[str, str]` to `IndexMap<String, String>`
//! - [`pydict_to_indexmap_vecstr`] - Convert `Dict[str, List[str]]` to `IndexMap<String, Vec<String>>`
//! - [`pyany_to_indexmap_str`] - Convert any dict-like object to `IndexMap<String, String>`
//! - [`pyany_to_indexmap_vecstr`] - Convert any dict-like object to `IndexMap<String, Vec<String>>`

use indexmap::IndexMap;
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Convert a Python dict with string keys and string values to IndexMap.
///
/// Preserves insertion order from the Python dict for deterministic iteration.
///
/// # Arguments
///
/// * `dict` - Python dict reference
///
/// # Returns
///
/// IndexMap preserving insertion order, or PyErr if extraction fails.
///
/// # Example
///
/// ```rust,ignore
/// use classic_shared_py::indexmap_utils::pydict_to_indexmap_str;
///
/// #[pyfunction]
/// fn process_dict(dict: &Bound<'_, PyDict>) -> PyResult<Vec<String>> {
///     let map = pydict_to_indexmap_str(dict)?;
///     Ok(map.keys().cloned().collect())
/// }
/// ```
pub fn pydict_to_indexmap_str(dict: &Bound<'_, PyDict>) -> PyResult<IndexMap<String, String>> {
    let mut map = IndexMap::new();
    for (key, value) in dict.iter() {
        let k: String = key.extract()?;
        let v: String = value.extract()?;
        map.insert(k, v);
    }
    Ok(map)
}

/// Convert a Python dict with optional presence to IndexMap.
///
/// Handles `None` by returning an empty IndexMap.
///
/// # Arguments
///
/// * `dict` - Optional Python dict reference
///
/// # Returns
///
/// IndexMap preserving insertion order, or empty IndexMap if dict is None.
///
/// # Example
///
/// ```rust,ignore
/// use classic_shared_py::indexmap_utils::pydict_to_indexmap_str_optional;
///
/// #[pyfunction]
/// fn process_optional_dict(dict: Option<&Bound<'_, PyDict>>) -> IndexMap<String, String> {
///     pydict_to_indexmap_str_optional(dict)
/// }
/// ```
pub fn pydict_to_indexmap_str_optional(
    dict: Option<&Bound<'_, PyDict>>,
) -> IndexMap<String, String> {
    match dict {
        Some(d) => {
            let mut map = IndexMap::new();
            for (key, value) in d.iter() {
                if let (Ok(k), Ok(v)) = (key.extract::<String>(), value.extract::<String>()) {
                    map.insert(k, v);
                }
            }
            map
        }
        None => IndexMap::new(),
    }
}

/// Convert a Python dict with string keys and list of string values to IndexMap.
///
/// Preserves insertion order from the Python dict.
///
/// # Arguments
///
/// * `dict` - Python dict reference with List[str] values
///
/// # Returns
///
/// IndexMap preserving insertion order, or PyErr if extraction fails.
///
/// # Example
///
/// ```rust,ignore
/// use classic_shared_py::indexmap_utils::pydict_to_indexmap_vecstr;
///
/// #[pyfunction]
/// fn process_patterns(dict: &Bound<'_, PyDict>) -> PyResult<usize> {
///     let map = pydict_to_indexmap_vecstr(dict)?;
///     Ok(map.values().map(|v| v.len()).sum())
/// }
/// ```
pub fn pydict_to_indexmap_vecstr(
    dict: &Bound<'_, PyDict>,
) -> PyResult<IndexMap<String, Vec<String>>> {
    let mut map = IndexMap::new();
    for (key, value) in dict.iter() {
        let k: String = key.extract()?;
        let v: Vec<String> = value.extract()?;
        map.insert(k, v);
    }
    Ok(map)
}

/// Convert any dict-like PyAny to IndexMap with string values.
///
/// Handles any Python object that can be downcast to a dict.
/// Silently skips entries that cannot be extracted as strings.
///
/// # Arguments
///
/// * `py_any` - Any Python object that should be a dict
///
/// # Returns
///
/// IndexMap preserving insertion order, or empty IndexMap if not a dict.
///
/// # Example
///
/// ```rust,ignore
/// use classic_shared_py::indexmap_utils::pyany_to_indexmap_str;
///
/// #[setter]
/// fn set_config(&mut self, value: &Bound<'_, PyAny>) {
///     self.config = pyany_to_indexmap_str(value);
/// }
/// ```
pub fn pyany_to_indexmap_str(py_any: &Bound<'_, pyo3::types::PyAny>) -> IndexMap<String, String> {
    // Use extract() to try to get the value as a dict
    if let Ok(dict) = py_any.extract::<Bound<'_, PyDict>>() {
        let mut map = IndexMap::new();
        for (key, value) in dict.iter() {
            if let (Ok(k), Ok(v)) = (key.extract::<String>(), value.extract::<String>()) {
                map.insert(k, v);
            }
        }
        map
    } else {
        IndexMap::new()
    }
}

/// Convert any dict-like PyAny to IndexMap with `Vec<String>` values.
///
/// Handles any Python object that can be downcast to a dict.
/// Silently skips entries that cannot be extracted.
///
/// # Arguments
///
/// * `py_any` - Any Python object that should be a dict
///
/// # Returns
///
/// IndexMap preserving insertion order, or empty IndexMap if not a dict.
///
/// # Example
///
/// ```rust,ignore
/// use classic_shared_py::indexmap_utils::pyany_to_indexmap_vecstr;
///
/// #[setter]
/// fn set_patterns(&mut self, value: &Bound<'_, PyAny>) {
///     self.patterns = pyany_to_indexmap_vecstr(value);
/// }
/// ```
pub fn pyany_to_indexmap_vecstr(
    py_any: &Bound<'_, pyo3::types::PyAny>,
) -> IndexMap<String, Vec<String>> {
    // Use extract() to try to get the value as a dict
    if let Ok(dict) = py_any.extract::<Bound<'_, PyDict>>() {
        let mut map = IndexMap::new();
        for (key, value) in dict.iter() {
            if let (Ok(k), Ok(v)) = (key.extract::<String>(), value.extract::<Vec<String>>()) {
                map.insert(k, v);
            }
        }
        map
    } else {
        IndexMap::new()
    }
}

#[cfg(test)]
#[path = "indexmap_utils_tests.rs"]
mod tests;
