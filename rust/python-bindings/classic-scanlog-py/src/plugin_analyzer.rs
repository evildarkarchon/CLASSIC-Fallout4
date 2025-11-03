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
    /// Creates a new plugin analyzer for Bethesda game crash logs.
    ///
    /// This constructor initializes an analyzer that can scan crash logs for plugin references,
    /// check plugin limits, match plugins against callstacks, and filter ignored plugins.
    ///
    /// # Arguments
    ///
    /// * `game_ignore_plugins` - List of game-specific plugins to ignore during analysis
    /// * `ignore_list` - Additional custom plugins to ignore
    /// * `crashgen_name` - Name of the crash generator (e.g., "Buffout4", "Crash Logger")
    /// * `game_version` - Base game version string (default: empty)
    /// * `game_version_vr` - VR version string if applicable (default: empty)
    /// * `game_version_new` - Next-gen/updated version string if applicable (default: empty)
    ///
    /// # Returns
    ///
    /// A new `PyPluginAnalyzer` instance ready to analyze crash logs.
    ///
    /// # Errors
    ///
    /// Returns `PyErr` if the underlying core analyzer fails to initialize.
    ///
    /// # Example
    ///
    /// ```python
    /// # Python usage
    /// from classic_core import PluginAnalyzer
    ///
    /// analyzer = PluginAnalyzer(
    ///     game_ignore_plugins=["Fallout4.esm", "DLCRobot.esm"],
    ///     ignore_list=["MyCustomPlugin.esp"],
    ///     crashgen_name="Buffout4",
    ///     game_version="1.10.163",
    ///     game_version_vr="1.2.72",
    ///     game_version_new="1.10.980"
    /// )
    /// ```
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

    /// Scan log for plugins and check limits
    ///
    /// Scans segment plugins and extracts plugin information, returning a mapping of
    /// plugin names to their load order IDs/status along with plugin limit flags.
    ///
    /// # Arguments
    ///
    /// * `segment_plugins` - List of plugin segment lines from crash log
    /// * `game_version` - Optional game version for plugin limit detection
    /// * `version_current` - Optional crashgen version for plugin limit detection
    ///
    /// # Returns
    ///
    /// Tuple containing:
    /// - Dict mapping plugin names to IDs/status
    /// - Boolean flag for plugin limit triggered
    /// - Boolean flag for limit check disabled
    #[pyo3(signature = (segment_plugins, game_version=None, version_current=None))]
    pub fn loadorder_scan_log(
        &self,
        segment_plugins: Vec<String>,
        game_version: Option<String>,
        version_current: Option<String>,
    ) -> PyResult<(HashMap<String, String>, bool, bool)> {
        self.inner
            .loadorder_scan_log(
                segment_plugins,
                game_version.as_deref(),
                version_current.as_deref(),
            )
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
