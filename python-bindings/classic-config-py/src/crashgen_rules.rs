use classic_config_core::{
    CrashgenExpectationParseResult, CrashgenSettingsRules, parse_crashgen_expectations,
};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use serde_json::{Map, Number, Value};

fn pyany_to_document(value: &Bound<'_, PyAny>) -> Value {
    if value.is_none() {
        return Value::Null;
    }
    if let Ok(value) = value.extract::<bool>() {
        return Value::Bool(value);
    }
    if let Ok(value) = value.extract::<i64>() {
        return Value::Number(Number::from(value));
    }
    if let Ok(value) = value.extract::<String>() {
        return Value::String(value);
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let mut map = Map::new();
        for (key, value) in dict.iter() {
            if let Ok(key) = key.extract::<String>() {
                map.insert(key, pyany_to_document(&value));
            }
        }
        return Value::Object(map);
    }
    if let Ok(items) = value.extract::<Vec<Bound<'_, PyAny>>>() {
        return Value::Array(items.iter().map(pyany_to_document).collect());
    }
    Value::Null
}

/// Parse a Python mapping into typed crashgen settings rules.
///
/// The expected input shape mirrors the `CrashgenSettingsRules` Python dict
/// shape exported by this crate. Python values are converted into the
/// carrier-neutral Crashgen Expectation document and parsed by
/// `classic-config-core`.
pub fn parse_settings_rules(value: &Bound<'_, PyAny>) -> Option<CrashgenSettingsRules> {
    parse_settings_rules_with_diagnostics(value, None).rules
}

/// Parse Python rule input while retaining diagnostics for strict analyzer construction.
pub fn parse_settings_rules_with_diagnostics(
    value: &Bound<'_, PyAny>,
    default_version: Option<u32>,
) -> CrashgenExpectationParseResult {
    parse_crashgen_expectations(&pyany_to_document(value), default_version)
}

#[cfg(test)]
#[path = "crashgen_rules_tests.rs"]
mod tests;
