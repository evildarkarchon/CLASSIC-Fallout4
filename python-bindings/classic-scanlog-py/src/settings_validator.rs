//! Python bindings for SettingsValidator - Thin wrapper over classic-scanlog-core

use classic_config_core::CrashgenSettingsSnapshot;
use classic_scanlog_core::settings_validator::SettingsValidator;
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use std::collections::HashSet;

use crate::py_adapters::crashgen_entry_from_py;

/// Convert a Python section-to-settings mapping into the Rust settings snapshot.
pub(crate) fn crashgen_snapshot_from_py_sections(
    crashgen: &Bound<'_, PyDict>,
) -> PyResult<CrashgenSettingsSnapshot> {
    let mut snapshot = CrashgenSettingsSnapshot::new();
    for (section, settings) in crashgen.iter() {
        let section: String = section.extract()?;
        let settings = settings.cast::<PyDict>().map_err(|_| {
            PyTypeError::new_err(
                "crashgen settings must be a dict[str, dict[str, str]] grouped by section",
            )
        })?;
        for (key, value) in settings.iter() {
            let key: String = key.extract()?;
            let value: String = value.extract()?;
            snapshot.insert(&section, &key, value);
        }
    }

    Ok(snapshot)
}

/// Python wrapper for SettingsValidator
#[pyclass(name = "SettingsValidator")]
pub struct PySettingsValidator {
    inner: SettingsValidator,
}

#[pymethods]
impl PySettingsValidator {
    /// Create a new SettingsValidator from a crashgen name and registry entry dictionary.
    ///
    /// Expected `crashgen_entry` keys: `display_section`, `ignore_keys`, `checks`,
    /// and optional `settings_rules`. `checks` is accepted as deprecated inert metadata.
    #[new]
    pub fn new(crashgen_name: String, crashgen_entry: &Bound<'_, PyAny>) -> Self {
        Self {
            inner: SettingsValidator::new(crashgen_name, crashgen_entry_from_py(crashgen_entry)),
        }
    }

    #[pyo3(signature = (crashgen, xse_modules, crashgen_version = None, config_layout = None))]
    /// Validate all Crashgen Expectations and Disabled Setting Notices.
    ///
    /// The optional `crashgen_version` and `config_layout` inputs are used to
    /// apply version-gated and layout-specific YAML rules during validation.
    pub fn scan_all_settings(
        &self,
        crashgen: &Bound<'_, PyDict>,
        xse_modules: HashSet<String>,
        crashgen_version: Option<(u32, u32, u32)>,
        config_layout: Option<String>,
    ) -> PyResult<Vec<Vec<String>>> {
        let layout = config_layout
            .as_deref()
            .and_then(classic_config_core::ConfigLayout::parse)
            .unwrap_or(classic_config_core::ConfigLayout::Unknown);
        let crashgen = crashgen_snapshot_from_py_sections(crashgen)?;

        let fragments = self
            .inner
            .scan_all_settings(&crashgen, &xse_modules, crashgen_version, layout)
            .map_err(crate::to_pyerr)?;

        Ok(fragments.into_iter().map(|f| f.to_list()).collect())
    }

    /// Scan for disabled crash generator settings
    pub fn check_disabled_settings(&self, crashgen: &Bound<'_, PyDict>) -> PyResult<Vec<String>> {
        let crashgen = crashgen_snapshot_from_py_sections(crashgen)?;
        let fragment = self
            .inner
            .check_disabled_settings(&crashgen)
            .map_err(crate::to_pyerr)?;
        Ok(fragment.to_list())
    }
}
