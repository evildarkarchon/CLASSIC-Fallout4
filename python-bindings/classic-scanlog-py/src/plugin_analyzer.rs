//! Python bindings for PluginAnalyzer - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::PluginAnalyzer;
use classic_shared::{pydict_to_indexmap_str, without_gil};
use indexmap::IndexMap;
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Convert IndexMap to Python dict, preserving insertion order
/// Python 3.7+ dicts maintain insertion order, so this is safe
fn indexmap_to_pydict(py: Python<'_>, map: IndexMap<String, String>) -> PyResult<Py<PyDict>> {
    let dict = PyDict::new(py);
    for (k, v) in map {
        dict.set_item(k, v)?;
    }
    Ok(dict.into())
}

/// Python wrapper for load-order parsing, limit validation, filtering, and batch utilities.
#[pyclass(name = "PluginAnalyzer")]
pub struct PyPluginAnalyzer {
    inner: PluginAnalyzer,
}

#[pymethods]
impl PyPluginAnalyzer {
    /// Creates a utility analyzer for Bethesda game crash logs.
    ///
    /// This constructor initializes load-order parsing, plugin-limit checks, and ignored-plugin
    /// filtering. Semantic call-stack matching is owned by `PluginEvidenceAnalyzer`.
    ///
    /// # Arguments
    ///
    /// * `game_ignore_plugins` - Legacy compatibility input retained for the stable constructor;
    ///   semantic ignores are configured on `PluginEvidenceAnalyzer`
    /// * `ignore_list` - Additional custom plugins to ignore
    /// * `crashgen_name` - Legacy compatibility input retained for the stable constructor; report
    ///   prose is owned by Autoscan Report Assembly
    /// * `game_version` - Base game version string (default: empty)
    /// * `game_version_vr` - VR version string if applicable (default: empty)
    ///
    /// # Returns
    ///
    /// A new `PyPluginAnalyzer` instance ready to parse and validate load orders.
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
    ///     game_version_vr="1.2.72"
    /// )
    /// ```
    #[new]
    #[pyo3(signature = (game_ignore_plugins, ignore_list, crashgen_name, game_version="".to_string(), game_version_vr="".to_string()))]
    pub fn new(
        game_ignore_plugins: Vec<String>,
        ignore_list: Vec<String>,
        crashgen_name: String,
        game_version: String,
        game_version_vr: String,
    ) -> PyResult<Self> {
        let inner = PluginAnalyzer::new(
            game_ignore_plugins,
            ignore_list,
            crashgen_name,
            game_version,
            game_version_vr,
        )
        .map_err(crate::to_pyerr)?;
        Ok(Self { inner })
    }

    /// Scan log for plugins and check limits
    ///
    /// Scans segment plugins and extracts plugin information, returning a mapping of
    /// plugin names to their load order IDs/status along with plugin limit flags.
    /// Releases GIL during scanning to allow concurrent Python threads.
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
    /// - Dict mapping plugin names to IDs/status (order preserved)
    /// - Boolean flag for plugin limit triggered
    /// - Boolean flag for limit check disabled
    #[pyo3(signature = (segment_plugins, game_version=None, version_current=None))]
    pub fn loadorder_scan_log(
        &self,
        py: Python<'_>,
        segment_plugins: Vec<String>,
        game_version: Option<String>,
        version_current: Option<String>,
    ) -> PyResult<(Py<PyDict>, bool, bool)> {
        // Release GIL during plugin scanning
        let (plugins, limit_triggered, limit_disabled) = without_gil(py, || {
            self.inner.loadorder_scan_log(
                &segment_plugins,
                game_version.as_deref(),
                version_current.as_deref(),
            )
        })
        .map_err(crate::to_pyerr)?;
        // Convert IndexMap to Python dict preserving order
        Ok((
            indexmap_to_pydict(py, plugins)?,
            limit_triggered,
            limit_disabled,
        ))
    }

    /// Check plugin limit - returns (plugin_limit_triggered, limit_check_disabled)
    ///
    /// Releases GIL during limit checking to allow concurrent Python threads.
    pub fn check_plugin_limit(
        &self,
        py: Python<'_>,
        segment_plugins: Vec<String>,
        game_version: String,
        version_current: String,
    ) -> PyResult<(bool, bool)> {
        without_gil(py, || {
            self.inner
                .check_plugin_limit(&segment_plugins, &game_version, &version_current)
        })
        .map_err(crate::to_pyerr)
    }

    /// Filter ignored plugins
    ///
    /// Takes a dict of plugins and returns a filtered dict with ignored plugins removed.
    /// The order of plugins is preserved.
    /// Releases GIL during filtering to allow concurrent Python threads.
    pub fn filter_ignored_plugins(
        &self,
        py: Python<'_>,
        plugins: &Bound<'_, PyDict>,
    ) -> PyResult<Py<PyDict>> {
        // Extract Python data before releasing GIL
        let plugins_map = pydict_to_indexmap_str(plugins)?;
        // Release GIL during filtering
        let filtered = without_gil(py, || self.inner.filter_ignored_plugins(plugins_map))
            .map_err(crate::to_pyerr)?;
        indexmap_to_pydict(py, filtered)
    }
}

/// Detect plugins from multiple logs (standalone function)
///
/// Returns a list of dicts, each mapping plugin names to their load order IDs.
/// The order of plugins within each dict is preserved from the crash log.
/// Releases GIL during batch detection to allow concurrent Python threads.
#[pyfunction]
pub fn detect_plugins_batch(py: Python<'_>, logs: Vec<String>) -> PyResult<Vec<Py<PyDict>>> {
    // Release GIL during batch detection
    let results = without_gil(py, || classic_scanlog_core::detect_plugins_batch(logs));
    results
        .into_iter()
        .map(|map| indexmap_to_pydict(py, map))
        .collect()
}

/// Check if a line contains a plugin reference (standalone function)
#[pyfunction]
pub fn contains_plugin(line: String) -> bool {
    classic_scanlog_core::contains_plugin(&line)
}
