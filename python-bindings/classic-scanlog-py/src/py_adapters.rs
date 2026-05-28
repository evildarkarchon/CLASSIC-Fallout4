use classic_config_core::{
    CoreModEntry, CrashgenEntryRaw, CrashgenSettingsRules, ModConflictEntry, ModSolutionCriteria,
    ModSolutionEntry,
};
use classic_scanlog_core::{CheckId, CrashgenEntry};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use std::collections::{HashMap, HashSet};

use crate::core_mod_convert::exclude_when_from_pydict;
use crate::crashgen_rules::parse_settings_rules;

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
        checks: raw
            .checks
            .iter()
            .filter_map(|name| CheckId::parse(name))
            .collect(),
        settings_rules: raw.settings_rules.clone(),
    }
}

pub(crate) fn parse_crashgen_registry_from_py(
    registry_any: &Bound<'_, PyAny>,
) -> HashMap<String, CrashgenEntryRaw> {
    let Ok(registry_dict) = registry_any.cast::<PyDict>() else {
        return HashMap::new();
    };

    registry_dict
        .iter()
        .filter_map(|(name_any, entry_any)| {
            let name = name_any.extract::<String>().ok()?;
            let entry_dict = entry_any.cast::<PyDict>().ok()?;
            Some((name, crashgen_entry_raw_from_dict(entry_dict)))
        })
        .collect()
}

pub(crate) fn crashgen_entry_from_py(entry_any: &Bound<'_, PyAny>) -> CrashgenEntry {
    entry_any
        .cast::<PyDict>()
        .ok()
        .map(|dict| crashgen_entry_from_raw(&crashgen_entry_raw_from_dict(dict)))
        .unwrap_or_else(CrashgenEntry::default_entry)
}

pub(crate) fn string_attr_or_default(source: &Bound<'_, PyAny>, attr_name: &str) -> String {
    source
        .getattr(attr_name)
        .ok()
        .and_then(|attr| attr.extract::<String>().ok())
        .unwrap_or_default()
}

pub(crate) fn vec_string_attr_or_default(
    source: &Bound<'_, PyAny>,
    attr_name: &str,
) -> Vec<String> {
    source
        .getattr(attr_name)
        .ok()
        .and_then(|attr| attr.extract::<Vec<String>>().ok())
        .unwrap_or_default()
}

fn py_sequence_items<'py>(value: &Bound<'py, PyAny>) -> Option<Vec<Bound<'py, PyAny>>> {
    value.extract::<Vec<Bound<'py, PyAny>>>().ok()
}

pub(crate) fn mod_conflict_entries_from_py(
    value: &Bound<'_, PyAny>,
) -> Option<Vec<ModConflictEntry>> {
    Some(
        py_sequence_items(value)?
            .iter()
            .filter_map(|item| {
                let dict = item.cast::<PyDict>().ok()?;
                Some(ModConflictEntry {
                    mod_a: dict_string(dict, "mod_a")?,
                    mod_b: dict_string(dict, "mod_b")?,
                    name_a: dict_string(dict, "name_a")?,
                    name_b: dict_string(dict, "name_b")?,
                    description: dict_string(dict, "description")?,
                    fix: dict_string(dict, "fix")?,
                    link: dict_string(dict, "link"),
                })
            })
            .collect(),
    )
}

pub(crate) fn mod_conflict_entries_from_attr(
    source: &Bound<'_, PyAny>,
    attr_name: &str,
) -> Vec<ModConflictEntry> {
    source
        .getattr(attr_name)
        .ok()
        .and_then(|attr| mod_conflict_entries_from_py(&attr))
        .unwrap_or_default()
}

pub(crate) fn core_mod_entries_from_py(value: &Bound<'_, PyAny>) -> Option<Vec<CoreModEntry>> {
    Some(
        py_sequence_items(value)?
            .iter()
            .filter_map(|item| {
                let dict = item.cast::<PyDict>().ok()?;
                Some(CoreModEntry {
                    detect: dict_string(dict, "detect")?,
                    name: dict_string(dict, "name")?,
                    description: dict_string(dict, "description")?,
                    gpu: dict_string(dict, "gpu"),
                    gpu_mismatch_warning: dict_string(dict, "gpu_mismatch_warning"),
                    exclude_when: exclude_when_from_pydict(dict),
                })
            })
            .collect(),
    )
}

pub(crate) fn core_mod_entries_from_attr(
    source: &Bound<'_, PyAny>,
    attr_name: &str,
) -> Vec<CoreModEntry> {
    source
        .getattr(attr_name)
        .ok()
        .and_then(|attr| core_mod_entries_from_py(&attr))
        .unwrap_or_default()
}

fn mod_solution_criteria_from_dict(dict: &Bound<'_, PyDict>) -> Option<ModSolutionCriteria> {
    let criteria_value = dict.get_item("criteria").ok().flatten()?;
    let criteria_dict = criteria_value.cast::<PyDict>().ok()?;

    if let Some(any_values) =
        dict_string_vec(criteria_dict, "any").filter(|values| !values.is_empty())
    {
        Some(ModSolutionCriteria::Any(any_values))
    } else {
        dict_string_vec(criteria_dict, "all")
            .filter(|values| !values.is_empty())
            .map(ModSolutionCriteria::All)
    }
}

pub(crate) fn mod_solution_entries_from_py(
    value: &Bound<'_, PyAny>,
) -> Option<Vec<ModSolutionEntry>> {
    Some(
        py_sequence_items(value)?
            .iter()
            .filter_map(|item| {
                let dict = item.cast::<PyDict>().ok()?;
                Some(ModSolutionEntry {
                    id: dict_string(dict, "id")?,
                    criteria: mod_solution_criteria_from_dict(dict)?,
                    exceptions: dict_string_vec(dict, "exceptions").unwrap_or_default(),
                    name: dict_string(dict, "name")?,
                    description: dict_string(dict, "description")?,
                })
            })
            .collect(),
    )
}

pub(crate) fn mod_solution_entries_from_attr(
    source: &Bound<'_, PyAny>,
    attr_name: &str,
) -> Vec<ModSolutionEntry> {
    source
        .getattr(attr_name)
        .ok()
        .and_then(|attr| mod_solution_entries_from_py(&attr))
        .unwrap_or_default()
}

#[cfg(test)]
#[path = "py_adapters_tests.rs"]
mod tests;
