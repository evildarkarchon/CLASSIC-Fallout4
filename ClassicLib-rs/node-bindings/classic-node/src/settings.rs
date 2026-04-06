//! Settings cache bindings (classic-settings-core)
//!
//! Exposes the YAML settings cache with sync/async load operations, cache
//! management, and statistics to JavaScript/TypeScript.
//!
//! ## API Overview
//!
//! ### Loading
//! - `loadSettingsSync(key, path)` — Load a YAML file, cache it, return parsed documents
//! - `loadSettingsAsync(key, path)` — Async variant of loadSettingsSync
//! - `loadBatchSync(paths)` — Load multiple YAML files in sequence
//! - `loadBatchAsync(paths)` — Load multiple YAML files concurrently
//!
//! ### Cache Retrieval
//! - `getCached(key)` — Get cached documents (returns `undefined` if not cached)
//! - `isCached(key)` — Check if a key exists in the cache
//!
//! ### Cache Management
//! - `invalidateSettings(key)` — Remove a single cache entry
//! - `clearSettingsCache()` — Remove all cache entries
//! - `settingsCacheSize()` — Get the number of cached entries
//! - `settingsCacheKeys()` — Get all cache keys
//!
//! ### Statistics
//! - `getSettingsCacheStats()` — Get hit/miss/rate stats
//! - `resetSettingsCacheStats()` — Reset hit/miss counters

use classic_settings_core as core;
use napi::bindgen_prelude::*;
use std::path::PathBuf;
use yaml_rust2::Yaml;

/// Convert any Display error to a napi::Error.
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
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
