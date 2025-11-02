//! Python bindings for SettingsValidator - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::SettingsValidator;
use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

/// Python wrapper for SettingsValidator
#[pyclass(name = "SettingsValidator")]
pub struct PySettingsValidator {
    inner: SettingsValidator,
}

#[pymethods]
impl PySettingsValidator {
    /// Create a new instance

    #[new]
    pub fn new(crashgen_name: String, crashgen_ignore: Vec<String>) -> Self {
        Self {
            inner: SettingsValidator::new(crashgen_name, crashgen_ignore),
        }
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
