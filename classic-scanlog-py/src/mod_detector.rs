//! Python bindings for mod detection functions - Thin wrapper over classic-scanlog-core

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

/// Detect single-type mods (standalone function)
#[pyfunction]
pub fn detect_mods_single(
    yaml_dict: HashMap<String, String>,
    crashlog_plugins: HashMap<String, String>,
) -> PyResult<Vec<String>> {
    classic_scanlog_core::detect_mods_single(yaml_dict, crashlog_plugins).map_err(crate::to_pyerr)
}

/// Detect double-type mods (standalone function)
#[pyfunction]
pub fn detect_mods_double(
    yaml_dict: HashMap<String, String>,
    crashlog_plugins: HashMap<String, String>,
) -> PyResult<Vec<String>> {
    classic_scanlog_core::detect_mods_double(yaml_dict, crashlog_plugins).map_err(crate::to_pyerr)
}

/// Detect important mods (standalone function)
#[pyfunction]
#[pyo3(signature = (yaml_dict, crashlog_plugins, gpu_rival=None, xse_modules=HashSet::new()))]
pub fn detect_mods_important(
    yaml_dict: HashMap<String, String>,
    crashlog_plugins: HashMap<String, String>,
    gpu_rival: Option<String>,
    xse_modules: HashSet<String>,
) -> PyResult<Vec<String>> {
    classic_scanlog_core::detect_mods_important(
        yaml_dict,
        crashlog_plugins,
        gpu_rival.as_deref(),
        xse_modules,
    )
    .map_err(crate::to_pyerr)
}

/// Detect all mod types in batch (standalone function)
#[pyfunction]
pub fn detect_mods_batch(
    yaml_dict: HashMap<String, String>,
    crashlog_plugins_list: Vec<HashMap<String, String>>,
) -> PyResult<Vec<Vec<String>>> {
    classic_scanlog_core::detect_mods_batch(yaml_dict, crashlog_plugins_list)
        .map_err(crate::to_pyerr)
}
