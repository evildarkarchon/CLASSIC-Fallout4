//! Conversion helpers for `CoreModExclude` ↔ Python dict round-tripping.

use classic_config_core::CoreModExclude;
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Parse an `exclude_when` key from a Python dict into `Option<CoreModExclude>`.
///
/// Expects the dict shape `{"plugin_any": ["Plugin.esp", ...]}` mirroring the
/// YAML representation. Returns `None` when the key is absent, malformed, or
/// the plugin list is empty.
pub fn exclude_when_from_pydict(dict: &Bound<'_, PyDict>) -> Option<CoreModExclude> {
    let ew = dict.get_item("exclude_when").ok()??;
    let ew_dict = ew.cast::<PyDict>().ok()?;
    let plugin_any = ew_dict.get_item("plugin_any").ok()??;
    let plugins = plugin_any.extract::<Vec<String>>().ok()?;
    if plugins.is_empty() {
        None
    } else {
        Some(CoreModExclude::PluginAny(plugins))
    }
}

/// Convert `Option<CoreModExclude>` into a Python dict suitable for embedding
/// in a `CoreModEntry` dict under the `"exclude_when"` key.
///
/// Returns `Ok(None)` when there is no exclusion condition.
pub fn exclude_when_to_pydict<'py>(
    py: Python<'py>,
    exclude: &Option<CoreModExclude>,
) -> PyResult<Option<Bound<'py, PyDict>>> {
    match exclude {
        Some(CoreModExclude::PluginAny(plugins)) => {
            let dict = PyDict::new(py);
            dict.set_item("plugin_any", plugins)?;
            Ok(Some(dict))
        }
        None => Ok(None),
    }
}
