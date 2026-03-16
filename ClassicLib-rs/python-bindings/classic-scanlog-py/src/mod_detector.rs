//! Python bindings for mod detection functions - Thin wrapper over classic-scanlog-core

use classic_config_core::ModConflictEntry;
use classic_shared::{pydict_to_indexmap_str, without_gil};
use indexmap::IndexMap;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashSet;

/// Detect single-type mods (standalone function)
///
/// Takes a YAML dict of mod patterns and a dict of crash log plugins.
/// Both dicts preserve insertion order using IndexMap internally for Python parity.
/// Releases GIL during pattern matching to allow concurrent Python threads.
#[pyfunction]
pub fn detect_mods_single(
    py: Python<'_>,
    yaml_dict: &Bound<'_, PyDict>,
    crashlog_plugins: &Bound<'_, PyDict>,
) -> PyResult<Vec<String>> {
    // Extract all Python data before releasing GIL
    let yaml_map = pydict_to_indexmap_str(yaml_dict)?;
    let plugins_map = pydict_to_indexmap_str(crashlog_plugins)?;
    // Release GIL during pattern matching
    without_gil(py, || {
        classic_scanlog_core::detect_mods_single(yaml_map, plugins_map)
    })
    .map_err(crate::to_pyerr)
}

/// Detect mod conflicts from structured conflict entries.
///
/// Takes a list of conflict entry dicts and a dict of crash log plugins.
/// Releases GIL during pattern matching to allow concurrent Python threads.
#[pyfunction]
pub fn detect_mods_double(
    py: Python<'_>,
    entries: &Bound<'_, PyList>,
    crashlog_plugins: &Bound<'_, PyDict>,
) -> PyResult<Vec<String>> {
    let conflict_entries: Vec<ModConflictEntry> = entries
        .iter()
        .filter_map(|item| {
            let dict = item.cast::<PyDict>().ok()?;
            Some(ModConflictEntry {
                mod_a: dict.get_item("mod_a").ok()??.extract::<String>().ok()?,
                mod_b: dict.get_item("mod_b").ok()??.extract::<String>().ok()?,
                name_a: dict.get_item("name_a").ok()??.extract::<String>().ok()?,
                name_b: dict.get_item("name_b").ok()??.extract::<String>().ok()?,
                description: dict.get_item("description").ok()??.extract::<String>().ok()?,
                fix: dict.get_item("fix").ok()??.extract::<String>().ok()?,
                link: dict
                    .get_item("link")
                    .ok()
                    .flatten()
                    .and_then(|v| v.extract::<String>().ok()),
            })
        })
        .collect();
    let plugins_map = pydict_to_indexmap_str(crashlog_plugins)?;
    without_gil(py, || {
        classic_scanlog_core::detect_mods_double(&conflict_entries, plugins_map)
    })
    .map_err(crate::to_pyerr)
}

/// Detect important mods (standalone function)
///
/// Uses IndexMap to preserve Python dict iteration order for parity.
/// Both yaml_dict and crashlog_plugins preserve insertion order.
/// Releases GIL during pattern matching to allow concurrent Python threads.
#[pyfunction]
#[pyo3(signature = (yaml_dict, crashlog_plugins, gpu_rival=None, xse_modules=HashSet::new()))]
pub fn detect_mods_important(
    py: Python<'_>,
    yaml_dict: &Bound<'_, PyDict>,
    crashlog_plugins: &Bound<'_, PyDict>,
    gpu_rival: Option<String>,
    xse_modules: HashSet<String>,
) -> PyResult<Vec<String>> {
    // Extract all Python data before releasing GIL
    let yaml_map = pydict_to_indexmap_str(yaml_dict)?;
    let plugins_map = pydict_to_indexmap_str(crashlog_plugins)?;
    // Release GIL during pattern matching
    without_gil(py, || {
        classic_scanlog_core::detect_mods_important(
            yaml_map,
            plugins_map,
            gpu_rival.as_deref(),
            xse_modules,
        )
    })
    .map_err(crate::to_pyerr)
}

/// Detect all mod types in batch (standalone function)
///
/// Takes a YAML dict of mod patterns and a list of plugin dicts.
/// Both yaml_dict and each plugin dict preserve insertion order using IndexMap internally.
/// Releases GIL during batch processing to allow concurrent Python threads.
#[pyfunction]
pub fn detect_mods_batch(
    py: Python<'_>,
    yaml_dict: &Bound<'_, PyDict>,
    crashlog_plugins_list: Vec<Bound<'_, PyDict>>,
) -> PyResult<Vec<Vec<String>>> {
    // Extract all Python data before releasing GIL
    let yaml_map = pydict_to_indexmap_str(yaml_dict)?;
    let plugins_list: PyResult<Vec<IndexMap<String, String>>> = crashlog_plugins_list
        .iter()
        .map(|d| pydict_to_indexmap_str(d))
        .collect();
    let plugins = plugins_list?;
    // Release GIL during batch processing
    without_gil(py, || {
        classic_scanlog_core::detect_mods_batch(yaml_map, plugins)
    })
    .map_err(crate::to_pyerr)
}
