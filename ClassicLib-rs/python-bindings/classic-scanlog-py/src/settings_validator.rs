//! Python bindings for SettingsValidator - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::crashgen_registry::CheckId;
use classic_scanlog_core::settings_validator::SettingsValidator;
use classic_scanlog_core::CrashgenEntry;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use std::collections::{HashMap, HashSet};

use crate::crashgen_rules::parse_settings_rules;

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
    /// and optional `settings_rules`.
    #[new]
    pub fn new(crashgen_name: String, crashgen_entry: &Bound<'_, PyAny>) -> Self {
        let entry_dict = crashgen_entry.cast::<PyDict>().ok();

        let display_section = entry_dict
            .and_then(|d| d.get_item("display_section").ok().flatten())
            .and_then(|v| v.extract::<String>().ok())
            .unwrap_or_default();

        let ignore_keys = entry_dict
            .and_then(|d| d.get_item("ignore_keys").ok().flatten())
            .and_then(|v| v.extract::<Vec<String>>().ok())
            .unwrap_or_default()
            .into_iter()
            .collect();

        let checks = entry_dict
            .and_then(|d| d.get_item("checks").ok().flatten())
            .and_then(|v| v.extract::<Vec<String>>().ok())
            .unwrap_or_default()
            .into_iter()
            .filter_map(|name| CheckId::parse(&name))
            .collect();

        let settings_rules = entry_dict
            .and_then(|d| d.get_item("settings_rules").ok().flatten())
            .and_then(|v| parse_settings_rules(&v));

        let entry = CrashgenEntry {
            display_section,
            ignore_keys,
            checks,
            settings_rules,
        };

        Self {
            inner: SettingsValidator::new(crashgen_name, entry),
        }
    }

    #[pyo3(signature = (crashgen, xse_modules, crashgen_version = None, config_layout = None))]
    /// Validate all crashgen settings and return report fragments as Python lists.
    ///
    /// The optional `crashgen_version` and `config_layout` inputs are used to
    /// apply version-gated and layout-specific rules during validation.
    pub fn scan_all_settings(
        &self,
        crashgen: HashMap<String, String>,
        xse_modules: HashSet<String>,
        crashgen_version: Option<(u32, u32, u32)>,
        config_layout: Option<String>,
    ) -> PyResult<Vec<Vec<String>>> {
        let layout = config_layout
            .as_deref()
            .and_then(classic_crashgen_settings_core::ConfigLayout::parse)
            .unwrap_or(classic_crashgen_settings_core::ConfigLayout::Unknown);

        let fragments = self
            .inner
            .scan_all_settings(&crashgen, &xse_modules, crashgen_version, layout)
            .map_err(crate::to_pyerr)?;

        Ok(fragments.into_iter().map(|f| f.to_list()).collect())
    }

    /// Scan Buffout achievements setting for conflicts
    pub fn scan_buffout_achievements_setting(
        &self,
        xse_modules: HashSet<String>,
        crashgen: HashMap<String, String>,
    ) -> PyResult<Vec<String>> {
        let fragment = self
            .inner
            .scan_buffout_achievements_setting(xse_modules, &crashgen)
            .map_err(crate::to_pyerr)?;
        Ok(fragment.to_list())
    }

    /// Analyze and validate memory management settings
    pub fn scan_buffout_memorymanagement_settings(
        &self,
        crashgen: HashMap<String, String>,
        has_xcell: bool,
        has_old_xcell: bool,
        has_baka_scrapheap: bool,
    ) -> PyResult<Vec<String>> {
        let fragment = self
            .inner
            .scan_buffout_memorymanagement_settings(
                &crashgen,
                has_xcell,
                has_old_xcell,
                has_baka_scrapheap,
            )
            .map_err(crate::to_pyerr)?;
        Ok(fragment.to_list())
    }

    /// Scan archive limit settings
    pub fn scan_archivelimit_setting(
        &self,
        crashgen: HashMap<String, String>,
        crashgen_version: Option<(u32, u32, u32)>,
    ) -> PyResult<Vec<String>> {
        let fragment = self
            .inner
            .scan_archivelimit_setting(&crashgen, crashgen_version)
            .map_err(crate::to_pyerr)?;
        Ok(fragment.to_list())
    }

    /// Scan LooksMenu (F4EE) compatibility
    pub fn scan_buffout_looksmenu_setting(
        &self,
        crashgen: HashMap<String, String>,
        xse_modules: HashSet<String>,
    ) -> PyResult<Vec<String>> {
        let fragment = self
            .inner
            .scan_buffout_looksmenu_setting(&crashgen, xse_modules)
            .map_err(crate::to_pyerr)?;
        Ok(fragment.to_list())
    }

    /// Scan for disabled crash generator settings
    pub fn check_disabled_settings(
        &self,
        crashgen: HashMap<String, String>,
    ) -> PyResult<Vec<String>> {
        let fragment = self
            .inner
            .check_disabled_settings(&crashgen)
            .map_err(crate::to_pyerr)?;
        Ok(fragment.to_list())
    }
}
