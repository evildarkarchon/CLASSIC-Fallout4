//! Python bindings for PluginAnalyzer - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::PluginAnalyzer;
use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

/// Python wrapper for PluginAnalyzer
#[pyclass(name = "PluginAnalyzer")]
pub struct PyPluginAnalyzer {
    inner: PluginAnalyzer,
}

#[pymethods]
impl PyPluginAnalyzer {
    #[new]
    #[pyo3(signature = (game_ignore_plugins, ignore_list, crashgen_name, game_version="".to_string(), game_version_vr="".to_string(), game_version_new="".to_string()))]
    pub fn new(
        game_ignore_plugins: Vec<String>,
        ignore_list: Vec<String>,
        crashgen_name: String,
        game_version: String,
        game_version_vr: String,
        game_version_new: String,
    ) -> PyResult<Self> {
        let inner = PluginAnalyzer::new(
            game_ignore_plugins,
            ignore_list,
            crashgen_name,
            game_version,
            game_version_vr,
            game_version_new,
        )
        .map_err(crate::to_pyerr)?;
        Ok(Self { inner })
    }

    /// Scan log for plugins
    pub fn loadorder_scan_log(&self, segment_plugins: Vec<String>) -> PyResult<Vec<String>> {
        self.inner
            .loadorder_scan_log(segment_plugins)
            .map_err(crate::to_pyerr)
    }

    /// Check plugin limit - returns (plugin_limit_triggered, limit_check_disabled)
    pub fn check_plugin_limit(
        &self,
        segment_plugins: Vec<String>,
        game_version: String,
        version_current: String,
    ) -> PyResult<(bool, bool)> {
        self.inner
            .check_plugin_limit(segment_plugins, &game_version, &version_current)
            .map_err(crate::to_pyerr)
    }

    /// Match plugins
    pub fn plugin_match(
        &self,
        segment_callstack_lower: Vec<String>,
        crashlog_plugins_lower: HashSet<String>,
    ) -> PyResult<Vec<String>> {
        self.inner
            .plugin_match(segment_callstack_lower, crashlog_plugins_lower)
            .map_err(crate::to_pyerr)
    }

    /// Filter ignored plugins
    pub fn filter_ignored_plugins(
        &self,
        plugins: HashMap<String, String>,
    ) -> PyResult<HashMap<String, String>> {
        self.inner
            .filter_ignored_plugins(plugins)
            .map_err(crate::to_pyerr)
    }
}

/// Detect plugins from multiple logs (standalone function)
#[pyfunction]
pub fn detect_plugins_batch(logs: Vec<String>) -> Vec<HashMap<String, String>> {
    classic_scanlog_core::detect_plugins_batch(logs)
}

/// Check if a line contains a plugin reference (standalone function)
#[pyfunction]
pub fn contains_plugin(line: String) -> bool {
    classic_scanlog_core::contains_plugin(&line)
}
