use classic_config_core::{
    CrashgenEntryRaw, CrashgenExpectationParseDiagnostic, CrashgenSettingsRules,
};
use classic_scanlog_core::CrashgenEntry;
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use std::collections::HashSet;

use crate::crashgen_rules::{parse_settings_rules, parse_settings_rules_with_diagnostics};

fn dict_string(dict: &Bound<'_, PyDict>, key: &str) -> Option<String> {
    dict.get_item(key)
        .ok()
        .flatten()
        .and_then(|value| value.extract::<String>().ok())
}

fn dict_string_vec(dict: &Bound<'_, PyDict>, key: &str) -> Option<Vec<String>> {
    dict.get_item(key)
        .ok()
        .flatten()
        .and_then(|value| value.extract::<Vec<String>>().ok())
}

fn dict_u32(dict: &Bound<'_, PyDict>, key: &str) -> Option<u32> {
    dict.get_item(key)
        .ok()
        .flatten()
        .and_then(|value| value.extract::<u32>().ok())
}

fn dict_settings_rules(dict: &Bound<'_, PyDict>, key: &str) -> Option<CrashgenSettingsRules> {
    dict.get_item(key)
        .ok()
        .flatten()
        .and_then(|value| parse_settings_rules(&value))
}

fn crashgen_entry_raw_from_dict(dict: &Bound<'_, PyDict>) -> CrashgenEntryRaw {
    CrashgenEntryRaw {
        display_section: dict_string(dict, "display_section").unwrap_or_default(),
        ignore_keys: dict_string_vec(dict, "ignore_keys").unwrap_or_default(),
        checks: dict_string_vec(dict, "checks").unwrap_or_default(),
        settings_rules_version: dict_u32(dict, "settings_rules_version"),
        settings_rules: dict_settings_rules(dict, "settings_rules"),
    }
}

fn crashgen_entry_from_raw(raw: &CrashgenEntryRaw) -> CrashgenEntry {
    CrashgenEntry {
        display_section: raw.display_section.clone(),
        ignore_keys: raw.ignore_keys.iter().cloned().collect::<HashSet<_>>(),
        settings_rules: raw.settings_rules.clone(),
    }
}

/// Converts one Python crashgen registry entry into the standalone analyzer shape.
pub(crate) fn crashgen_entry_from_py(entry_any: &Bound<'_, PyAny>) -> CrashgenEntry {
    entry_any
        .cast::<PyDict>()
        .ok()
        .map(|dict| crashgen_entry_from_raw(&crashgen_entry_raw_from_dict(dict)))
        .unwrap_or_else(CrashgenEntry::default_entry)
}

/// Strictly converts a Python crashgen registry entry for fallible analyzer construction.
pub(crate) fn crashgen_entry_from_py_strict(
    entry_any: &Bound<'_, PyAny>,
) -> PyResult<(CrashgenEntry, Vec<CrashgenExpectationParseDiagnostic>)> {
    let dict = entry_any.cast::<PyDict>().map_err(|_| {
        PyTypeError::new_err("crashgen_entry must be a dict with analyzer configuration")
    })?;
    let settings_rules_version = dict_u32(dict, "settings_rules_version");
    let parsed = dict
        .get_item("settings_rules")?
        .map(|value| parse_settings_rules_with_diagnostics(&value, settings_rules_version));
    let raw = CrashgenEntryRaw {
        display_section: dict_string(dict, "display_section").unwrap_or_default(),
        ignore_keys: dict_string_vec(dict, "ignore_keys").unwrap_or_default(),
        checks: dict_string_vec(dict, "checks").unwrap_or_default(),
        settings_rules_version,
        settings_rules: parsed.as_ref().and_then(|result| result.rules.clone()),
    };
    let diagnostics = parsed.map(|result| result.diagnostics).unwrap_or_default();
    Ok((crashgen_entry_from_raw(&raw), diagnostics))
}

#[cfg(test)]
#[path = "py_adapters_tests.rs"]
mod tests;
