//! Settings + YAML bindings (classic-settings-core)
//!
//! Exposes the unified YAML settings cache and stateless YAML operations to
//! JavaScript/TypeScript. This module was created by merging the former
//! `yaml` NAPI module into `settings` per plan 01-02 D-08: after plan 01-01
//! absorbed `classic-yaml-core` into `classic-settings-core` the two NAPI
//! modules were redundant. All functions continue to be exported from
//! `index.js` under the same names.
//!
//! ## API Overview
//!
//! ### Settings cache — loading
//! - `loadSettingsSync(key, path)` — Load a YAML file, cache it, return parsed documents
//! - `loadSettingsAsync(key, path)` — Async variant of loadSettingsSync
//! - `loadBatchSync(paths)` — Load multiple YAML files in sequence
//! - `loadBatchAsync(paths)` — Load multiple YAML files concurrently
//!
//! ### Settings cache — retrieval / management / stats
//! - `getCached`, `isCached`, `invalidateSettings`, `clearSettingsCache`
//! - `settingsCacheSize`, `settingsCacheKeys`
//! - `getSettingsCacheStats`, `resetSettingsCacheStats`
//!
//! ### YAML operations (stateless, free functions)
//! - `yamlParse`, `yamlStringify`, `yamlLoadFile`, `yamlSaveFile`
//! - `yamlGetValue`, `yamlGetStringValue`, `yamlGetVecValue`, `yamlGetHashmapValue`
//! - `yamlGetIndexmapValue`, `yamlGetHashmapVecValue`
//! - `yamlSetSetting`, `yamlGetSettingsBatch`, `yamlSetSettingsBatch`
//! - `yamlClearCache`, `yamlGetCacheStats`
//!
//! ### YamlDocument class (stateful)
//! - `new YamlDocument(content)` with `getValue`, `getStringValue`, `getVecValue`,
//!   `getHashmapValue`, `setValue`, `toString`

use classic_settings_core::{self as core, YamlError, YamlFile, YamlOperations, yaml_cache_stats};
use napi::bindgen_prelude::*;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use yaml_rust2::Yaml;

/// Convert any Display error to a napi::Error.
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// YAML configuration file identifiers exposed to JavaScript.
#[napi(string_enum)]
pub enum JsYamlFile {
    /// CLASSIC Data/databases/CLASSIC Main.yaml
    Main,
    /// CLASSIC Ignore.yaml
    Ignore,
    /// CLASSIC Data/databases/CLASSIC {Game}.yaml
    Game,
    /// CLASSIC Data/CLASSIC {Game} Local.yaml
    GameLocal,
    /// tests/test_settings.yaml (for testing only)
    Test,
    /// User config dir/CLASSIC/cache.yaml
    Cache,
}

fn js_to_core_yaml_file(file: &JsYamlFile) -> YamlFile {
    match file {
        JsYamlFile::Main => YamlFile::Main,
        JsYamlFile::Ignore => YamlFile::Ignore,
        JsYamlFile::Game => YamlFile::Game,
        JsYamlFile::GameLocal => YamlFile::GameLocal,
        JsYamlFile::Test => YamlFile::Test,
        JsYamlFile::Cache => YamlFile::Cache,
    }
}

fn core_to_js_yaml_file(file: &YamlFile) -> JsYamlFile {
    match file {
        YamlFile::Main => JsYamlFile::Main,
        YamlFile::Ignore => JsYamlFile::Ignore,
        YamlFile::Game => JsYamlFile::Game,
        YamlFile::GameLocal => JsYamlFile::GameLocal,
        YamlFile::Test => JsYamlFile::Test,
        YamlFile::Cache => JsYamlFile::Cache,
    }
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

/// Convert an `Arc<Vec<Yaml>>` (multi-document) to a JSON array of documents.
fn docs_to_json(docs: &[Yaml]) -> serde_json::Value {
    serde_json::Value::Array(docs.iter().map(yaml_to_json).collect())
}

// ============================================================================
// Cache statistics DTO
// ============================================================================

/// Cache performance statistics returned by `getSettingsCacheStats()`.
#[napi(object)]
pub struct SettingsCacheStats {
    /// Number of cache hits since last reset.
    pub hits: i64,
    /// Number of cache misses since last reset.
    pub misses: i64,
    /// Hit rate as a fraction (0.0 to 1.0).
    #[napi(js_name = "hit_rate")]
    pub hit_rate: f64,
    /// Current number of entries in the cache.
    pub size: u32,
    /// Maximum bounded cache capacity.
    pub capacity: u32,
}

// ============================================================================
// Loading functions
// ============================================================================

/// Load a YAML file synchronously, cache it under the given key, and return
/// the parsed documents as a JSON array.
///
/// Each element in the returned array corresponds to a YAML document in the file
/// (most files contain a single document).
#[napi]
pub fn load_settings_sync(key: String, path: String) -> Result<serde_json::Value> {
    let path_buf = PathBuf::from(&path);
    let docs = core::load_settings_sync(&key, &path_buf).map_err(to_napi_err)?;
    Ok(docs_to_json(&docs))
}

/// Load a YAML file asynchronously, cache it under the given key, and return
/// the parsed documents as a JSON array.
///
/// Uses the shared global Tokio runtime (ONE RUNTIME RULE).
#[napi]
pub async fn load_settings_async(key: String, path: String) -> Result<serde_json::Value> {
    let path_buf = PathBuf::from(&path);
    let docs = core::load_settings_async(&key, &path_buf)
        .await
        .map_err(to_napi_err)?;
    Ok(docs_to_json(&docs))
}

/// Load multiple YAML files synchronously. Each file path is used as its cache key.
///
/// Returns the number of files successfully loaded and cached.
#[napi]
pub fn load_batch_sync(paths: Vec<String>) -> Result<u32> {
    let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
    let path_refs: Vec<&std::path::Path> = path_bufs.iter().map(|p| p.as_path()).collect();
    let count = core::load_batch_sync(&path_refs).map_err(to_napi_err)?;
    Ok(count as u32)
}

/// Load multiple YAML files concurrently. Each file path is used as its cache key.
///
/// Returns the number of files successfully loaded and cached.
#[napi]
pub async fn load_batch_async(paths: Vec<String>) -> Result<u32> {
    let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
    let path_refs: Vec<&std::path::Path> = path_bufs.iter().map(|p| p.as_path()).collect();
    let count = core::load_batch_async(&path_refs)
        .await
        .map_err(to_napi_err)?;
    Ok(count as u32)
}

// ============================================================================
// Cache retrieval
// ============================================================================

/// Get cached YAML documents by key.
///
/// Returns the parsed documents as a JSON array, or `undefined` if the key is
/// not present in the cache.
#[napi]
pub fn get_cached(key: String) -> Option<serde_json::Value> {
    core::get_cached(&key).map(|docs| docs_to_json(&docs))
}

/// Check whether a key exists in the settings cache.
#[napi]
pub fn is_cached(key: String) -> bool {
    core::is_cached(&key)
}

// ============================================================================
// Cache management
// ============================================================================

/// Remove a single entry from the settings cache.
///
/// Returns `true` if the key existed and was removed, `false` otherwise.
#[napi]
pub fn invalidate_settings(key: String) -> bool {
    core::invalidate(&key)
}

/// Clear all entries from the settings cache.
#[napi]
pub fn clear_settings_cache() {
    core::clear_cache();
}

/// Get the number of entries currently in the settings cache.
#[napi]
pub fn settings_cache_size() -> u32 {
    core::cache_size() as u32
}

/// Get all keys currently stored in the settings cache.
#[napi]
pub fn settings_cache_keys() -> Vec<String> {
    core::cache_keys()
}

// ============================================================================
// Statistics
// ============================================================================

/// Get cache performance statistics (hits, misses, hit rate, size, capacity).
#[napi]
pub fn get_settings_cache_stats() -> SettingsCacheStats {
    let stats = core::cache_stats();
    SettingsCacheStats {
        hits: stats.hits as i64,
        misses: stats.misses as i64,
        hit_rate: stats.hit_rate,
        size: stats.size as u32,
        capacity: stats.capacity as u32,
    }
}

/// Reset the cache hit/miss counters to zero.
#[napi]
pub fn reset_settings_cache_stats() {
    core::reset_cache_stats();
}

/// Get a human-readable description for a YAML file type.
#[napi]
pub fn get_yaml_file_description(file: JsYamlFile) -> String {
    let core_file = js_to_core_yaml_file(&file);
    core_file.description().to_string()
}

/// Get all YAML file type identifiers.
#[napi]
pub fn get_all_yaml_files() -> Vec<JsYamlFile> {
    YamlFile::all().iter().map(core_to_js_yaml_file).collect()
}

// ============================================================================
// YAML operations (merged from yaml.rs per D-08)
// ============================================================================

/// Convert a YamlError to a napi::Error.
///
/// Named `yaml_err_to_napi` so it doesn't collide with the generic
/// `to_napi_err` free function declared at the top of this module.
fn yaml_err_to_napi(err: YamlError) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
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
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
    Ok(yaml_to_json(&yaml))
}

/// Convert a JavaScript object to a YAML string.
#[napi]
pub fn yaml_stringify(data: serde_json::Value) -> Result<String> {
    let ops = YamlOperations::new();
    let yaml = json_to_yaml(&data);
    ops.dump_yaml(&yaml).map_err(yaml_err_to_napi)
}

/// Load and parse a YAML file, returning a JavaScript-compatible object.
#[napi]
pub fn yaml_load_file(path: String) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops
        .load_yaml_file(Path::new(&path))
        .map_err(yaml_err_to_napi)?;
    Ok(yaml_to_json(&yaml))
}

/// Extract a value from a YAML string using dot-notation key path.
#[napi]
pub fn yaml_get_value(content: String, key_path: String) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
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
    default_value: String,
) -> Result<String> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
    Ok(ops.get_string_value(&yaml, &key_path, &default_value))
}

/// Extract a string array from YAML using dot-notation key path.
#[napi]
pub fn yaml_get_vec_value(content: String, key_path: String) -> Result<Vec<String>> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
    Ok(ops.get_vec_value(&yaml, &key_path))
}

/// Extract a string-to-string map from YAML using dot-notation key path.
#[napi]
pub fn yaml_get_hashmap_value(
    content: String,
    key_path: String,
) -> Result<HashMap<String, String>> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
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
        let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
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
    pub fn get_string_value(&self, key_path: String, default_value: String) -> String {
        self.ops
            .get_string_value(&self.yaml, &key_path, &default_value)
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
            .map_err(yaml_err_to_napi)?;
        Ok(())
    }

    /// Serialize the internal YAML document back to a string.
    #[napi(js_name = "toString")]
    pub fn to_string_yaml(&self) -> Result<String> {
        self.ops.dump_yaml(&self.yaml).map_err(yaml_err_to_napi)
    }
}

// ---------------------------------------------------------------------------
// Additional YAML free functions
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
        .map_err(yaml_err_to_napi)
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
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
    let yaml_value = json_to_yaml(&value);
    let updated = ops
        .set_setting(&yaml, &key_path, yaml_value)
        .map_err(yaml_err_to_napi)?;
    ops.dump_yaml(&updated).map_err(yaml_err_to_napi)
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
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
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
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;

    let obj = settings
        .as_object()
        .ok_or_else(|| napi::Error::from_reason("settings must be a JSON object"))?;

    let pairs: Vec<(&str, Yaml)> = obj
        .iter()
        .map(|(k, v)| (k.as_str(), json_to_yaml(v)))
        .collect();

    let updated = ops
        .set_settings_batch(&yaml, &pairs)
        .map_err(yaml_err_to_napi)?;
    ops.dump_yaml(&updated).map_err(yaml_err_to_napi)
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
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
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
    let yaml = ops.parse_yaml(&content).map_err(yaml_err_to_napi)?;
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
/// @returns An object with canonical cache stats fields.
#[napi(
    ts_return_type = "{ hits: number; misses: number; hit_rate: number; size: number; capacity: number }"
)]
pub fn yaml_get_cache_stats() -> serde_json::Value {
    let stats = yaml_cache_stats();

    serde_json::json!({
        "hits": stats.hits,
        "misses": stats.misses,
        "hit_rate": stats.hit_rate,
        "size": stats.size,
        "capacity": stats.capacity,
    })
}
