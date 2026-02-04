//! Python bindings for mod detection functions - Thin wrapper over classic-scanlog-core

use classic_shared::pydict_to_indexmap_str;
use indexmap::IndexMap;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashSet;

/// Detect single-type mods (standalone function)
///
/// Takes a YAML dict of mod patterns and a dict of crash log plugins.
/// Both dicts preserve insertion order using IndexMap internally for Python parity.
#[pyfunction]
pub fn detect_mods_single(
    yaml_dict: &Bound<'_, PyDict>,
    crashlog_plugins: &Bound<'_, PyDict>,
) -> PyResult<Vec<String>> {
    let yaml_map = pydict_to_indexmap_str(yaml_dict)?;
    let plugins_map = pydict_to_indexmap_str(crashlog_plugins)?;
    classic_scanlog_core::detect_mods_single(yaml_map, plugins_map).map_err(crate::to_pyerr)
}

/// Detect double-type mods (standalone function)
///
/// Takes a YAML dict of mod conflict patterns and a dict of crash log plugins.
/// Both dicts preserve insertion order using IndexMap internally for Python parity.
#[pyfunction]
pub fn detect_mods_double(
    yaml_dict: &Bound<'_, PyDict>,
    crashlog_plugins: &Bound<'_, PyDict>,
) -> PyResult<Vec<String>> {
    let yaml_map = pydict_to_indexmap_str(yaml_dict)?;
    let plugins_map = pydict_to_indexmap_str(crashlog_plugins)?;
    classic_scanlog_core::detect_mods_double(yaml_map, plugins_map).map_err(crate::to_pyerr)
}

/// Detect important mods (standalone function)
///
/// Uses IndexMap to preserve Python dict iteration order for parity.
/// Both yaml_dict and crashlog_plugins preserve insertion order.
#[pyfunction]
#[pyo3(signature = (yaml_dict, crashlog_plugins, gpu_rival=None, xse_modules=HashSet::new()))]
pub fn detect_mods_important(
    yaml_dict: &Bound<'_, PyDict>,
    crashlog_plugins: &Bound<'_, PyDict>,
    gpu_rival: Option<String>,
    xse_modules: HashSet<String>,
) -> PyResult<Vec<String>> {
    let yaml_map = pydict_to_indexmap_str(yaml_dict)?;
    let plugins_map = pydict_to_indexmap_str(crashlog_plugins)?;
    classic_scanlog_core::detect_mods_important(
        yaml_map,
        plugins_map,
        gpu_rival.as_deref(),
        xse_modules,
    )
    .map_err(crate::to_pyerr)
}

/// Detect all mod types in batch (standalone function)
///
/// Takes a YAML dict of mod patterns and a list of plugin dicts.
/// Both yaml_dict and each plugin dict preserve insertion order using IndexMap internally.
#[pyfunction]
pub fn detect_mods_batch(
    yaml_dict: &Bound<'_, PyDict>,
    crashlog_plugins_list: Vec<Bound<'_, PyDict>>,
) -> PyResult<Vec<Vec<String>>> {
    let yaml_map = pydict_to_indexmap_str(yaml_dict)?;
    let plugins_list: PyResult<Vec<IndexMap<String, String>>> = crashlog_plugins_list
        .iter()
        .map(|d| pydict_to_indexmap_str(d))
        .collect();
    classic_scanlog_core::detect_mods_batch(yaml_map, plugins_list?)
        .map_err(crate::to_pyerr)
}
