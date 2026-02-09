//! YAML bindings for classic-yaml-core
//!
//! Exposes YAML parsing, serialization, and value extraction to JavaScript/TypeScript.
//! All business logic is delegated to `classic_yaml_core::YamlOperations`.

use classic_yaml_core::{YamlError, YamlOperations};
use napi::bindgen_prelude::*;
use std::collections::HashMap;
use std::path::Path;
use yaml_rust2::Yaml;

/// Convert a YamlError to a napi::Error
fn to_napi_err(err: YamlError) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// Convert a yaml-rust2 Yaml value to a serde_json::Value for JavaScript consumption.
fn yaml_to_json(yaml: &Yaml) -> serde_json::Value {
    match yaml {
        Yaml::Null => serde_json::Value::Null,
        Yaml::Boolean(b) => serde_json::Value::Bool(*b),
        Yaml::Integer(i) => serde_json::json!(*i),
        Yaml::Real(s) => {
            if let Ok(f) = s.parse::<f64>() {
                serde_json::json!(f)
            } else {
                serde_json::Value::String(s.clone())
            }
        }
        Yaml::String(s) => serde_json::Value::String(s.clone()),
        Yaml::Array(arr) => serde_json::Value::Array(arr.iter().map(yaml_to_json).collect()),
        Yaml::Hash(hash) => {
            let mut map = serde_json::Map::new();
            for (k, v) in hash {
                let key = match k {
                    Yaml::String(s) => s.clone(),
                    other => format!("{other:?}"),
                };
                map.insert(key, yaml_to_json(v));
            }
            serde_json::Value::Object(map)
        }
        Yaml::Alias(_) | Yaml::BadValue => serde_json::Value::Null,
    }
}

/// Convert a serde_json::Value back to a yaml-rust2 Yaml value.
fn json_to_yaml(value: &serde_json::Value) -> Yaml {
    match value {
        serde_json::Value::Null => Yaml::Null,
        serde_json::Value::Bool(b) => Yaml::Boolean(*b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Yaml::Integer(i)
            } else if let Some(f) = n.as_f64() {
                Yaml::Real(f.to_string())
            } else {
                Yaml::String(n.to_string())
            }
        }
        serde_json::Value::String(s) => Yaml::String(s.clone()),
        serde_json::Value::Array(arr) => Yaml::Array(arr.iter().map(json_to_yaml).collect()),
        serde_json::Value::Object(map) => {
            let mut hash = yaml_rust2::yaml::Hash::new();
            for (k, v) in map {
                hash.insert(Yaml::String(k.clone()), json_to_yaml(v));
            }
            Yaml::Hash(hash)
        }
    }
}

/// Parse a YAML string and return a JavaScript-compatible object.
#[napi]
pub fn yaml_parse(content: String) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    Ok(yaml_to_json(&yaml))
}

/// Convert a JavaScript object to a YAML string.
#[napi]
pub fn yaml_stringify(data: serde_json::Value) -> Result<String> {
    let ops = YamlOperations::new();
    let yaml = json_to_yaml(&data);
    ops.dump_yaml(&yaml).map_err(to_napi_err)
}

/// Load and parse a YAML file, returning a JavaScript-compatible object.
#[napi]
pub fn yaml_load_file(path: String) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops.load_yaml_file(Path::new(&path)).map_err(to_napi_err)?;
    Ok(yaml_to_json(&yaml))
}

/// Extract a value from a YAML string using dot-notation key path.
#[napi]
pub fn yaml_get_value(content: String, key_path: String) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    match ops.get_setting(&yaml, &key_path) {
        Some(value) => Ok(yaml_to_json(&value)),
        None => Ok(serde_json::Value::Null),
    }
}

/// Extract a string value from YAML using dot-notation, with a default fallback.
#[napi]
pub fn yaml_get_string_value(
    content: String,
    key_path: String,
    default: String,
) -> Result<String> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    Ok(ops.get_string_value(&yaml, &key_path, &default))
}

/// Extract a string array from YAML using dot-notation key path.
#[napi]
pub fn yaml_get_vec_value(content: String, key_path: String) -> Result<Vec<String>> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    Ok(ops.get_vec_value(&yaml, &key_path))
}

/// Extract a string-to-string map from YAML using dot-notation key path.
#[napi]
pub fn yaml_get_hashmap_value(
    content: String,
    key_path: String,
) -> Result<HashMap<String, String>> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    Ok(ops.get_hashmap_value(&yaml, &key_path))
}
