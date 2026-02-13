//! YAML bindings for classic-yaml-core
//!
//! Exposes YAML parsing, serialization, and value extraction to JavaScript/TypeScript.
//! All business logic is delegated to `classic_yaml_core::YamlOperations`.
//!
//! ## Modules
//! - **Free functions**: Stateless YAML parsing, serialization, extraction, and batch operations.
//! - **YamlDocument class**: Stateful wrapper that holds a parsed YAML document in memory
//!   for repeated reads and mutations without re-parsing.

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
pub fn yaml_get_string_value(content: String, key_path: String, default: String) -> Result<String> {
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

// ---------------------------------------------------------------------------
// YamlDocument class -- stateful wrapper
// ---------------------------------------------------------------------------

/// A stateful YAML document that holds parsed content in memory.
///
/// Construct with `new YamlDocument(yamlString)`, then use `getValue`, `getStringValue`,
/// `getVecValue`, `getHashmapValue`, `setValue`, and `toString` without re-parsing.
#[napi]
pub struct YamlDocument {
    ops: YamlOperations,
    yaml: Yaml,
}

#[napi]
impl YamlDocument {
    /// Parse a YAML string and store it internally.
    ///
    /// @param content - Raw YAML string to parse.
    /// @throws if the YAML content is invalid.
    #[napi(constructor)]
    pub fn new(content: String) -> Result<Self> {
        let ops = YamlOperations::new();
        let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
        Ok(Self { ops, yaml })
    }

    /// Extract a value at the given dot-notation key path.
    ///
    /// Returns the JSON-compatible value, or `null` if the key path does not exist.
    #[napi]
    pub fn get_value(&self, key_path: String) -> serde_json::Value {
        match self.ops.get_setting(&self.yaml, &key_path) {
            Some(value) => yaml_to_json(&value),
            None => serde_json::Value::Null,
        }
    }

    /// Extract a string value at the given dot-notation key path, with a default fallback.
    #[napi]
    pub fn get_string_value(&self, key_path: String, default: String) -> String {
        self.ops.get_string_value(&self.yaml, &key_path, &default)
    }

    /// Extract a string array at the given dot-notation key path.
    ///
    /// Returns an empty array if the key does not exist or is not an array.
    #[napi]
    pub fn get_vec_value(&self, key_path: String) -> Vec<String> {
        self.ops.get_vec_value(&self.yaml, &key_path)
    }

    /// Extract a string-to-string map at the given dot-notation key path.
    ///
    /// Returns an empty object if the key does not exist or is not a hash.
    #[napi]
    pub fn get_hashmap_value(&self, key_path: String) -> HashMap<String, String> {
        self.ops.get_hashmap_value(&self.yaml, &key_path)
    }

    /// Set (or create) a value at the given dot-notation key path.
    ///
    /// Mutates the internal document in-place.
    ///
    /// @param keyPath - Dot-separated key path (e.g. "settings.debug").
    /// @param value   - Any JSON-compatible value to set.
    /// @throws if the key path is empty or invalid.
    #[napi]
    pub fn set_value(&mut self, key_path: String, value: serde_json::Value) -> Result<()> {
        let yaml_value = json_to_yaml(&value);
        self.yaml = self
            .ops
            .set_setting(&self.yaml, &key_path, yaml_value)
            .map_err(to_napi_err)?;
        Ok(())
    }

    /// Serialize the internal YAML document back to a string.
    #[napi(js_name = "toString")]
    pub fn to_string_yaml(&self) -> Result<String> {
        self.ops.dump_yaml(&self.yaml).map_err(to_napi_err)
    }
}

// ---------------------------------------------------------------------------
// Additional free functions
// ---------------------------------------------------------------------------

/// Save a JSON-compatible value to a YAML file (atomic write).
///
/// @param path - File path to write to.
/// @param data - Any JSON-compatible value to serialize as YAML.
/// @throws on I/O or serialization errors.
#[napi]
pub fn yaml_save_file(path: String, data: serde_json::Value) -> Result<()> {
    let ops = YamlOperations::new();
    let yaml = json_to_yaml(&data);
    ops.save_yaml_file(Path::new(&path), &yaml)
        .map_err(to_napi_err)
}

/// Set a single setting in a YAML string and return the modified YAML string.
///
/// @param content  - Raw YAML string.
/// @param keyPath  - Dot-notation path to the setting.
/// @param value    - New value (JSON-compatible).
/// @returns The modified YAML string.
/// @throws on parse or key-path errors.
#[napi]
pub fn yaml_set_setting(
    content: String,
    key_path: String,
    value: serde_json::Value,
) -> Result<String> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    let yaml_value = json_to_yaml(&value);
    let updated = ops
        .set_setting(&yaml, &key_path, yaml_value)
        .map_err(to_napi_err)?;
    ops.dump_yaml(&updated).map_err(to_napi_err)
}

/// Retrieve multiple settings at once from a YAML string.
///
/// @param content  - Raw YAML string.
/// @param keyPaths - Array of dot-notation key paths.
/// @returns A Record mapping each found key path to its JSON-compatible value.
///          Missing keys are omitted from the result.
#[napi]
pub fn yaml_get_settings_batch(
    content: String,
    key_paths: Vec<String>,
) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    let refs: Vec<&str> = key_paths.iter().map(|s| s.as_str()).collect();
    let batch = ops.get_settings_batch(&yaml, &refs);

    let mut map = serde_json::Map::new();
    for (key, value) in &batch {
        map.insert(key.clone(), yaml_to_json(value));
    }
    Ok(serde_json::Value::Object(map))
}

/// Set multiple settings at once in a YAML string and return the modified YAML string.
///
/// @param content  - Raw YAML string.
/// @param settings - A JSON object where keys are dot-notation paths and values are the
///                   new values to set.
/// @returns The modified YAML string.
/// @throws on parse or key-path errors.
#[napi]
pub fn yaml_set_settings_batch(content: String, settings: serde_json::Value) -> Result<String> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;

    let obj = settings
        .as_object()
        .ok_or_else(|| napi::Error::from_reason("settings must be a JSON object"))?;

    let pairs: Vec<(&str, Yaml)> = obj
        .iter()
        .map(|(k, v)| (k.as_str(), json_to_yaml(v)))
        .collect();

    let updated = ops.set_settings_batch(&yaml, &pairs).map_err(to_napi_err)?;
    ops.dump_yaml(&updated).map_err(to_napi_err)
}

/// Extract an order-preserving string-to-string map from YAML using dot-notation key path.
///
/// Internally uses `IndexMap` to preserve YAML key order, then serializes to a JSON object
/// (which serde_json preserves insertion order for).
///
/// @param content - Raw YAML string.
/// @param keyPath - Dot-notation key path.
/// @returns A Record<string, string> preserving YAML source order.
#[napi]
pub fn yaml_get_indexmap_value(content: String, key_path: String) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    let imap = ops.get_indexmap_value(&yaml, &key_path);

    let mut map = serde_json::Map::new();
    for (k, v) in &imap {
        map.insert(k.clone(), serde_json::Value::String(v.clone()));
    }
    Ok(serde_json::Value::Object(map))
}

/// Extract a map where values are arrays of strings from YAML using dot-notation key path.
///
/// @param content - Raw YAML string.
/// @param keyPath - Dot-notation key path.
/// @returns A Record<string, string[]>.
#[napi]
pub fn yaml_get_hashmap_vec_value(
    content: String,
    key_path: String,
) -> Result<HashMap<String, Vec<String>>> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    Ok(ops.get_hashmap_vec_value(&yaml, &key_path))
}

/// Clear the global YAML file cache.
///
/// Useful after external file modifications or during testing.
#[napi]
pub fn yaml_clear_cache() {
    let ops = YamlOperations::new();
    ops.clear_cache();
}

/// Get statistics about the global YAML file cache.
///
/// @returns An object with `cachedFiles` (number) and `totalBytes` (number).
#[napi]
pub fn yaml_get_cache_stats() -> serde_json::Value {
    let ops = YamlOperations::new();
    let stats = ops.get_cache_stats();

    let cached_files = stats.get("cached_files").copied().unwrap_or(0);
    let total_bytes = stats.get("total_bytes").copied().unwrap_or(0);

    serde_json::json!({
        "cachedFiles": cached_files,
        "totalBytes": total_bytes,
    })
}
