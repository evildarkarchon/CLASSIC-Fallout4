//! Settings operations bridge for CXX FFI.
//!
//! Bridges `classic_settings_core` to the C++ layer. Covers three surfaces:
//!
//! 1. **YAML operations** (pre-existing): File loading, parsing, settings access
//!    via dot-notation keys, and per-instance cache observation. Delegates to
//!    `classic_settings_core::YamlOperations`.
//! 2. **Settings cache** (new — D-09): Process-wide YAML-settings cache with
//!    sync and async-blocking load helpers, cache inspection, invalidation,
//!    and observability. Delegates to the `classic_settings_core::cache`
//!    module. The async helpers use `classic_shared_core::get_runtime().block_on()`
//!    to preserve the ONE RUNTIME RULE.
//! 3. **Validators** (new — D-09): Settings document structure validation,
//!    per-value type checking, and string-to-typed coercion. Mirrors the
//!    Python `classic_settings` validator surface 1:1.
//!
//! ## CXX type-system exceptions (documented)
//!
//! Two entries in the underlying `classic_settings_core` surface cannot cross
//! the CXX boundary directly and are therefore intentionally omitted from
//! this bridge:
//!
//! - `get_cached(key) -> Option<Arc<Vec<Yaml>>>` — `Arc<Vec<Yaml>>` cannot be
//!   marshalled through CXX. C++ callers can test `settings_is_cached(key)`
//!   and then use the existing `yaml_ops_*` load helpers if they need the
//!   parsed documents.
//! - The `load_settings_*` family returns the full parsed documents as
//!   `Arc<Vec<Yaml>>` in Rust. Across CXX the bridge helpers return the
//!   document count as `u32` instead, because the `Yaml` type is not
//!   CXX-marshallable. C++ consumers needing the parsed docs must round-trip
//!   through `yaml_ops_*`.
//!
//! Everything else on the `cache` and `validators` modules IS exposed.

use classic_settings_core::validators::{self, CoercedValue, IssueSeverity, SettingType};
use classic_settings_core::{
    self as settings_core, SETTINGS_IGNORE_NONE, YamlCacheStats, YamlFile as CoreYamlFile,
    YamlOperations, must_not_be_none as core_must_not_be_none, yaml_cache_stats,
};
use std::path::Path;
use yaml_rust2::Yaml;

/// Opaque wrapper around `YamlOperations` + a loaded YAML document.
pub struct YamlOps {
    ops: YamlOperations,
    doc: Option<Yaml>,
}

// ── Construction ────────────────────────────────────────────────────

fn yaml_ops_new() -> Box<YamlOps> {
    Box::new(YamlOps {
        ops: YamlOperations::new(),
        doc: None,
    })
}

// ── File operations ─────────────────────────────────────────────────

fn yaml_ops_load_file(ops: &mut YamlOps, path: &str) -> Result<(), String> {
    let yaml = ops
        .ops
        .load_yaml_file(Path::new(path))
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(yaml);
    Ok(())
}

fn yaml_ops_save_file(ops: &YamlOps, path: &str) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    ops.ops
        .save_yaml_file(Path::new(path), doc)
        .map_err(|e| format!("{e}"))
}

// ── Parse/dump ──────────────────────────────────────────────────────

fn yaml_ops_parse(ops: &mut YamlOps, content: &str) -> Result<(), String> {
    let yaml = ops.ops.parse_yaml(content).map_err(|e| format!("{e}"))?;
    ops.doc = Some(yaml);
    Ok(())
}

fn yaml_ops_dump(ops: &YamlOps) -> Result<String, String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    ops.ops.dump_yaml(doc).map_err(|e| format!("{e}"))
}

// ── Settings access ─────────────────────────────────────────────────

fn yaml_ops_get_string(ops: &YamlOps, key_path: &str, default_val: &str) -> String {
    match &ops.doc {
        Some(doc) => ops.ops.get_string_value(doc, key_path, default_val),
        None => default_val.to_string(),
    }
}

fn yaml_ops_get_vec(ops: &YamlOps, key_path: &str) -> Vec<String> {
    match &ops.doc {
        Some(doc) => ops.ops.get_vec_value(doc, key_path),
        None => Vec::new(),
    }
}

fn yaml_ops_get_setting_value(ops: &YamlOps, key_path: &str) -> ffi::YamlValue {
    match &ops.doc {
        Some(doc) => match ops.ops.get_setting(doc, key_path) {
            Some(yaml) => match yaml {
                Yaml::String(s) => ffi::YamlValue {
                    value: s,
                    is_null: false,
                    value_type: "string".to_string(),
                },
                Yaml::Boolean(b) => ffi::YamlValue {
                    value: b.to_string(),
                    is_null: false,
                    value_type: "bool".to_string(),
                },
                Yaml::Integer(i) => ffi::YamlValue {
                    value: i.to_string(),
                    is_null: false,
                    value_type: "integer".to_string(),
                },
                Yaml::Real(r) => ffi::YamlValue {
                    value: r,
                    is_null: false,
                    value_type: "real".to_string(),
                },
                Yaml::Null => ffi::YamlValue {
                    value: String::new(),
                    is_null: true,
                    value_type: "null".to_string(),
                },
                _ => ffi::YamlValue {
                    value: format!("{yaml:?}"),
                    is_null: false,
                    value_type: "complex".to_string(),
                },
            },
            None => ffi::YamlValue {
                value: String::new(),
                is_null: true,
                value_type: "null".to_string(),
            },
        },
        None => ffi::YamlValue {
            value: String::new(),
            is_null: true,
            value_type: "null".to_string(),
        },
    }
}

fn yaml_ops_set_string_setting(
    ops: &mut YamlOps,
    key_path: &str,
    value: &str,
) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    let updated = ops
        .ops
        .set_setting(doc, key_path, Yaml::String(value.to_string()))
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(updated);
    Ok(())
}

fn yaml_ops_set_bool_setting(ops: &mut YamlOps, key_path: &str, value: bool) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    let updated = ops
        .ops
        .set_setting(doc, key_path, Yaml::Boolean(value))
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(updated);
    Ok(())
}

fn yaml_ops_set_integer_setting(
    ops: &mut YamlOps,
    key_path: &str,
    value: i64,
) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    let updated = ops
        .ops
        .set_setting(doc, key_path, Yaml::Integer(value))
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(updated);
    Ok(())
}

fn yaml_ops_set_vec_setting(
    ops: &mut YamlOps,
    key_path: &str,
    values: Vec<String>,
) -> Result<(), String> {
    let doc = ops.doc.as_ref().ok_or("No YAML document loaded")?;
    let yaml_array = Yaml::Array(values.into_iter().map(Yaml::String).collect());
    let updated = ops
        .ops
        .set_setting(doc, key_path, yaml_array)
        .map_err(|e| format!("{e}"))?;
    ops.doc = Some(updated);
    Ok(())
}

// ── Cache management (per-YamlOps — delegates to YAML-file cache) ──

fn yaml_ops_clear_cache(ops: &YamlOps) {
    ops.ops.clear_cache();
}

fn yaml_ops_cache_size(ops: &YamlOps) -> usize {
    yaml_ops_cache_stats(ops).size
}

fn yaml_cache_stats_from(stats: YamlCacheStats) -> ffi::YamlCacheStatsDto {
    ffi::YamlCacheStatsDto {
        hits: stats.hits,
        misses: stats.misses,
        hit_rate: stats.hit_rate,
        size: stats.size,
        capacity: stats.capacity,
    }
}

fn yaml_ops_cache_stats(ops: &YamlOps) -> ffi::YamlCacheStatsDto {
    let _ = ops;
    yaml_cache_stats_from(yaml_cache_stats())
}

fn yaml_ops_has_document(ops: &YamlOps) -> bool {
    ops.doc.is_some()
}

// ── Settings cache ops (D-09 — process-wide settings cache) ────────

fn settings_load_sync(key: &str, path: &str) -> Result<u32, String> {
    let docs =
        settings_core::load_settings_sync(key, Path::new(path)).map_err(|e| e.to_string())?;
    Ok(docs.len() as u32)
}

fn settings_load_async_blocking(key: &str, path: &str) -> Result<u32, String> {
    let key = key.to_string();
    let path = path.to_string();
    let docs = classic_shared_core::get_runtime()
        .block_on(async move { settings_core::load_settings_async(&key, Path::new(&path)).await })
        .map_err(|e| e.to_string())?;
    Ok(docs.len() as u32)
}

fn settings_load_batch_sync(paths: Vec<String>) -> Result<u32, String> {
    let path_bufs: Vec<std::path::PathBuf> = paths.iter().map(std::path::PathBuf::from).collect();
    let path_refs: Vec<&Path> = path_bufs.iter().map(|p| p.as_path()).collect();
    let count = settings_core::load_batch_sync(&path_refs).map_err(|e| e.to_string())?;
    Ok(count as u32)
}

fn settings_load_batch_async_blocking(paths: Vec<String>) -> Result<u32, String> {
    let path_bufs: Vec<std::path::PathBuf> = paths.iter().map(std::path::PathBuf::from).collect();
    let count = classic_shared_core::get_runtime()
        .block_on(async move {
            let path_refs: Vec<&Path> = path_bufs.iter().map(|p| p.as_path()).collect();
            settings_core::load_batch_async(&path_refs).await
        })
        .map_err(|e| e.to_string())?;
    Ok(count as u32)
}

fn settings_cache_stats() -> ffi::SettingsCacheStats {
    let stats = settings_core::cache_stats();
    ffi::SettingsCacheStats {
        hits: stats.hits,
        misses: stats.misses,
        hit_rate: stats.hit_rate,
        size: stats.size as u64,
        capacity: stats.capacity as u64,
    }
}

fn settings_reset_cache_stats() {
    settings_core::reset_cache_stats();
}

fn settings_clear_cache() {
    settings_core::clear_cache();
}

fn settings_cache_size() -> u64 {
    settings_core::cache_size() as u64
}

fn settings_cache_keys() -> Vec<String> {
    settings_core::cache_keys()
}

fn settings_is_cached(key: &str) -> bool {
    settings_core::is_cached(key)
}

fn settings_invalidate(key: &str) -> bool {
    settings_core::invalidate(key)
}

fn from_bridge_yaml_file(f: ffi::YamlFile) -> CoreYamlFile {
    match f {
        ffi::YamlFile::Main => CoreYamlFile::Main,
        ffi::YamlFile::Settings => CoreYamlFile::Settings,
        ffi::YamlFile::Ignore => CoreYamlFile::Ignore,
        ffi::YamlFile::Game => CoreYamlFile::Game,
        ffi::YamlFile::GameLocal => CoreYamlFile::GameLocal,
        ffi::YamlFile::Test => CoreYamlFile::Test,
        ffi::YamlFile::Cache => CoreYamlFile::Cache,
        _ => CoreYamlFile::Settings,
    }
}

fn yaml_file_as_str(f: ffi::YamlFile) -> String {
    from_bridge_yaml_file(f).as_str().to_string()
}

fn yaml_file_description(f: ffi::YamlFile) -> String {
    from_bridge_yaml_file(f).description().to_string()
}

fn must_not_be_none_key(key: &str) -> bool {
    core_must_not_be_none(key)
}

fn settings_ignore_none_contains(key: &str) -> bool {
    SETTINGS_IGNORE_NONE.contains(&key)
}

// ── Validators (D-09 — mirrors Python classic_settings surface) ────

/// Parse a setting-type token into `SettingType`.
///
/// Mirrors `parse_setting_type` in `classic-settings-py/src/lib.rs` 1:1:
/// accepts `int|integer`, `bool|boolean`, `float|double`, `path`, `string|str`
/// (case-insensitive).
fn parse_setting_type_token(type_name: &str) -> Result<SettingType, String> {
    match type_name.to_lowercase().as_str() {
        "int" | "integer" => Ok(SettingType::Int),
        "bool" | "boolean" => Ok(SettingType::Bool),
        "float" | "double" => Ok(SettingType::Float),
        "path" => Ok(SettingType::Path),
        "string" | "str" => Ok(SettingType::String),
        _ => Err(format!("unknown setting type: {type_name}")),
    }
}

fn severity_token(sev: IssueSeverity) -> &'static str {
    match sev {
        IssueSeverity::Warning => "warning",
        IssueSeverity::Error => "error",
    }
}

fn settings_validate_structure(
    yaml_content: &str,
) -> Result<Vec<ffi::SettingsValidationIssue>, String> {
    let docs = yaml_rust2::YamlLoader::load_from_str(yaml_content).map_err(|e| e.to_string())?;
    let issues = if docs.is_empty() {
        validators::validate_settings_structure(&Yaml::Null)
    } else {
        validators::validate_settings_structure(&docs[0])
    };
    Ok(issues
        .into_iter()
        .map(|issue| ffi::SettingsValidationIssue {
            severity: severity_token(issue.severity).to_string(),
            message: issue.message,
        })
        .collect())
}

fn settings_validate_value(value: &str, expected_type: &str) -> Result<bool, String> {
    let ty = parse_setting_type_token(expected_type)?;
    Ok(validators::validate_setting_value(value, ty))
}

fn settings_coerce_value(
    value: &str,
    target_type: &str,
) -> Result<ffi::SettingsCoercedValue, String> {
    let ty = parse_setting_type_token(target_type)?;
    let coerced = validators::coerce_setting_value(value, ty)?;
    Ok(match coerced {
        CoercedValue::Int(v) => ffi::SettingsCoercedValue {
            kind: "int".to_string(),
            string_val: String::new(),
            int_val: v,
            float_val: 0.0,
            bool_val: false,
        },
        CoercedValue::Bool(v) => ffi::SettingsCoercedValue {
            kind: "bool".to_string(),
            string_val: String::new(),
            int_val: 0,
            float_val: 0.0,
            bool_val: v,
        },
        CoercedValue::Float(v) => ffi::SettingsCoercedValue {
            kind: "float".to_string(),
            string_val: String::new(),
            int_val: 0,
            float_val: v,
            bool_val: false,
        },
        CoercedValue::Path(s) => ffi::SettingsCoercedValue {
            kind: "path".to_string(),
            string_val: s,
            int_val: 0,
            float_val: 0.0,
            bool_val: false,
        },
        CoercedValue::String(s) => ffi::SettingsCoercedValue {
            kind: "string".to_string(),
            string_val: s,
            int_val: 0,
            float_val: 0.0,
            bool_val: false,
        },
    })
}

#[cxx::bridge(namespace = "classic::settings")]
mod ffi {
    #[repr(u8)]
    enum YamlFile {
        Main = 0,
        Settings = 1,
        Ignore = 2,
        Game = 3,
        GameLocal = 4,
        Test = 5,
        Cache = 6,
    }

    /// YAML-file cache stats DTO (distinct from `SettingsCacheStats` below).
    ///
    /// Returned by `yaml_ops_cache_stats` for observing the YAML-file cache
    /// used internally by `YamlOperations::load_yaml_file`.
    struct YamlCacheStatsDto {
        hits: u64,
        misses: u64,
        hit_rate: f64,
        size: usize,
        capacity: usize,
    }

    /// Settings cache stats DTO — process-wide YAML-settings cache (D-09).
    ///
    /// Returned by `settings_cache_stats`. Distinct from `YamlCacheStatsDto`
    /// because these stats cover a different cache populated by the
    /// `load_settings_*` family. `size` and `capacity` are `u64` here (rather
    /// than `usize`) to keep the DTO width stable across platforms.
    struct SettingsCacheStats {
        hits: u64,
        misses: u64,
        hit_rate: f64,
        size: u64,
        capacity: u64,
    }

    /// One issue from settings structure validation.
    ///
    /// Mirrors `classic_settings_core::validators::ValidationIssue` 1:1.
    /// `severity` is exactly one of "warning" or "error" — there is no "info"
    /// variant in the underlying enum.
    struct SettingsValidationIssue {
        severity: String,
        message: String,
    }

    /// Tagged coerced-value DTO for `settings_coerce_value`.
    ///
    /// `kind` discriminates the payload: "int", "bool", "float", "path", or
    /// "string". The payload field matching `kind` holds the value; other
    /// fields are zero/empty. Note that `Path` and `String` both carry their
    /// payload in `string_val` but expose distinct `kind` tokens so C++
    /// callers can tell them apart (matching `CoercedValue::Path` vs
    /// `CoercedValue::String` in the Rust source).
    struct SettingsCoercedValue {
        kind: String,
        string_val: String,
        int_val: i64,
        float_val: f64,
        bool_val: bool,
    }

    /// Typed YAML value for cross-FFI returns.
    struct YamlValue {
        /// String representation of the value
        value: String,
        /// Whether the value is null/missing
        is_null: bool,
        /// Type hint: "string", "bool", "integer", "real", "null", "complex"
        value_type: String,
    }

    extern "Rust" {
        type YamlOps;

        fn yaml_file_as_str(f: YamlFile) -> String;
        fn yaml_file_description(f: YamlFile) -> String;
        fn must_not_be_none_key(key: &str) -> bool;
        fn settings_ignore_none_contains(key: &str) -> bool;

        // Construction
        fn yaml_ops_new() -> Box<YamlOps>;

        // File operations
        fn yaml_ops_load_file(ops: &mut YamlOps, path: &str) -> Result<()>;
        fn yaml_ops_save_file(ops: &YamlOps, path: &str) -> Result<()>;

        // Parse/dump
        fn yaml_ops_parse(ops: &mut YamlOps, content: &str) -> Result<()>;
        fn yaml_ops_dump(ops: &YamlOps) -> Result<String>;

        // Settings access
        fn yaml_ops_get_string(ops: &YamlOps, key_path: &str, default_val: &str) -> String;
        fn yaml_ops_get_vec(ops: &YamlOps, key_path: &str) -> Vec<String>;
        fn yaml_ops_get_setting_value(ops: &YamlOps, key_path: &str) -> YamlValue;
        fn yaml_ops_set_string_setting(
            ops: &mut YamlOps,
            key_path: &str,
            value: &str,
        ) -> Result<()>;
        fn yaml_ops_set_bool_setting(ops: &mut YamlOps, key_path: &str, value: bool) -> Result<()>;
        fn yaml_ops_set_integer_setting(
            ops: &mut YamlOps,
            key_path: &str,
            value: i64,
        ) -> Result<()>;
        fn yaml_ops_set_vec_setting(
            ops: &mut YamlOps,
            key_path: &str,
            values: Vec<String>,
        ) -> Result<()>;

        // Cache management (YAML-file cache via YamlOperations)
        fn yaml_ops_clear_cache(ops: &YamlOps);
        fn yaml_ops_cache_size(ops: &YamlOps) -> usize;
        fn yaml_ops_cache_stats(ops: &YamlOps) -> YamlCacheStatsDto;
        fn yaml_ops_has_document(ops: &YamlOps) -> bool;

        // Settings cache ops (D-09 — process-wide settings cache)
        fn settings_load_sync(key: &str, path: &str) -> Result<u32>;
        fn settings_load_async_blocking(key: &str, path: &str) -> Result<u32>;
        fn settings_load_batch_sync(paths: Vec<String>) -> Result<u32>;
        fn settings_load_batch_async_blocking(paths: Vec<String>) -> Result<u32>;
        fn settings_cache_stats() -> SettingsCacheStats;
        fn settings_reset_cache_stats();
        fn settings_clear_cache();
        fn settings_cache_size() -> u64;
        fn settings_cache_keys() -> Vec<String>;
        fn settings_is_cached(key: &str) -> bool;
        fn settings_invalidate(key: &str) -> bool;

        // Validators (D-09 — mirrors Python surface)
        fn settings_validate_structure(yaml_content: &str) -> Result<Vec<SettingsValidationIssue>>;
        fn settings_validate_value(value: &str, expected_type: &str) -> Result<bool>;
        fn settings_coerce_value(value: &str, target_type: &str) -> Result<SettingsCoercedValue>;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;
    use std::io::Write;
    use tempfile::NamedTempFile;

    // ── YAML ops tests (pre-existing) ──────────────────────────────

    #[test]
    fn test_yaml_ops_new() {
        let ops = yaml_ops_new();
        assert!(!yaml_ops_has_document(&ops));
    }

    #[test]
    fn test_parse_and_dump_round_trip() {
        let mut ops = yaml_ops_new();
        let yaml_str = "game: Fallout4\nversion: 1.10.163\n";
        yaml_ops_parse(&mut ops, yaml_str).unwrap();
        assert!(yaml_ops_has_document(&ops));

        let dumped = yaml_ops_dump(&ops).unwrap();
        assert!(dumped.contains("Fallout4"));
        assert!(dumped.contains("1.10.163"));
    }

    #[test]
    fn test_get_string_setting() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "game: Fallout4\n").unwrap();
        assert_eq!(yaml_ops_get_string(&ops, "game", "default"), "Fallout4");
    }

    #[test]
    fn test_get_string_default_when_missing() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "other: value\n").unwrap();
        assert_eq!(yaml_ops_get_string(&ops, "game", "default"), "default");
    }

    #[test]
    fn test_get_string_no_document() {
        let ops = yaml_ops_new();
        assert_eq!(yaml_ops_get_string(&ops, "game", "default"), "default");
    }

    #[test]
    fn test_get_setting_value_types() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "str_val: hello\nbool_val: true\nint_val: 42\n").unwrap();

        let str_v = yaml_ops_get_setting_value(&ops, "str_val");
        assert_eq!(str_v.value, "hello");
        assert_eq!(str_v.value_type, "string");
        assert!(!str_v.is_null);

        let bool_v = yaml_ops_get_setting_value(&ops, "bool_val");
        assert_eq!(bool_v.value, "true");
        assert_eq!(bool_v.value_type, "bool");

        let int_v = yaml_ops_get_setting_value(&ops, "int_val");
        assert_eq!(int_v.value, "42");
        assert_eq!(int_v.value_type, "integer");
    }

    #[test]
    fn test_get_setting_value_missing() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "a: 1\n").unwrap();
        let missing = yaml_ops_get_setting_value(&ops, "nonexistent");
        assert!(missing.is_null);
        assert_eq!(missing.value_type, "null");
    }

    #[test]
    fn test_set_string_setting() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "game: Fallout4\n").unwrap();
        yaml_ops_set_string_setting(&mut ops, "game", "Skyrim").unwrap();
        assert_eq!(yaml_ops_get_string(&ops, "game", ""), "Skyrim");
    }

    #[test]
    fn test_set_bool_setting() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "enabled: false\n").unwrap();
        yaml_ops_set_bool_setting(&mut ops, "enabled", true).unwrap();
        let val = yaml_ops_get_setting_value(&ops, "enabled");
        assert_eq!(val.value, "true");
        assert_eq!(val.value_type, "bool");
    }

    #[test]
    fn test_get_vec() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "items:\n  - a\n  - b\n  - c\n").unwrap();
        let vec = yaml_ops_get_vec(&ops, "items");
        assert_eq!(vec, vec!["a", "b", "c"]);
    }

    #[test]
    fn test_get_vec_missing() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "other: value\n").unwrap();
        let vec = yaml_ops_get_vec(&ops, "nonexistent");
        assert!(vec.is_empty());
    }

    #[test]
    #[serial]
    fn test_cache_management() {
        let ops = yaml_ops_new();
        yaml_ops_clear_cache(&ops); // Clear first to ensure a clean state
        assert_eq!(yaml_ops_cache_size(&ops), 0);
        let stats = yaml_ops_cache_stats(&ops);
        assert_eq!(stats.size, 0);
        assert_eq!(stats.capacity, 128);
        yaml_ops_clear_cache(&ops); // Should not panic on empty cache
    }

    #[test]
    fn test_dump_no_document_error() {
        let ops = yaml_ops_new();
        assert!(yaml_ops_dump(&ops).is_err());
    }

    #[test]
    fn test_save_no_document_error() {
        let ops = yaml_ops_new();
        assert!(yaml_ops_save_file(&ops, "test.yaml").is_err());
    }

    #[test]
    fn test_set_setting_no_document_error() {
        let mut ops = yaml_ops_new();
        assert!(yaml_ops_set_string_setting(&mut ops, "key", "val").is_err());
    }

    #[test]
    fn test_invalid_yaml_parse() {
        let mut ops = yaml_ops_new();
        let result = yaml_ops_load_file(&mut ops, "nonexistent_file_12345.yaml");
        assert!(result.is_err());
    }

    #[test]
    fn test_nested_settings() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(
            &mut ops,
            "settings:\n  fcx_mode: true\n  show_values: false\n",
        )
        .unwrap();
        let fcx = yaml_ops_get_setting_value(&ops, "settings.fcx_mode");
        assert_eq!(fcx.value, "true");
        assert_eq!(fcx.value_type, "bool");
    }

    #[test]
    fn test_set_integer_setting() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "max_scans: 4\n").unwrap();
        yaml_ops_set_integer_setting(&mut ops, "max_scans", 8).unwrap();
        let val = yaml_ops_get_setting_value(&ops, "max_scans");
        assert_eq!(val.value, "8");
        assert_eq!(val.value_type, "integer");
    }

    #[test]
    fn test_set_integer_setting_no_document() {
        let mut ops = yaml_ops_new();
        assert!(yaml_ops_set_integer_setting(&mut ops, "key", 1).is_err());
    }

    #[test]
    fn test_set_vec_setting() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "items:\n  - old\n").unwrap();
        yaml_ops_set_vec_setting(
            &mut ops,
            "items",
            vec!["a".to_string(), "b".to_string(), "c".to_string()],
        )
        .unwrap();
        let vec = yaml_ops_get_vec(&ops, "items");
        assert_eq!(vec, vec!["a", "b", "c"]);
    }

    #[test]
    fn test_set_vec_setting_empty() {
        let mut ops = yaml_ops_new();
        yaml_ops_parse(&mut ops, "items:\n  - old\n").unwrap();
        yaml_ops_set_vec_setting(&mut ops, "items", vec![]).unwrap();
        let vec = yaml_ops_get_vec(&ops, "items");
        assert!(vec.is_empty());
    }

    #[test]
    fn test_set_vec_setting_no_document() {
        let mut ops = yaml_ops_new();
        assert!(yaml_ops_set_vec_setting(&mut ops, "key", vec!["a".to_string()]).is_err());
    }

    // ── Settings cache ops tests (D-09 — new) ──────────────────────

    fn make_settings_yaml(content: &str) -> NamedTempFile {
        let mut file = NamedTempFile::new().unwrap();
        file.write_all(content.as_bytes()).unwrap();
        file.flush().unwrap();
        file
    }

    #[test]
    #[serial]
    fn test_settings_load_sync() {
        settings_clear_cache();
        let file = make_settings_yaml("key: value\nnumber: 42\n");
        let count = settings_load_sync("t_sync", &file.path().display().to_string()).unwrap();
        assert_eq!(count, 1);
        assert!(settings_is_cached("t_sync"));
        settings_clear_cache();
    }

    #[test]
    #[serial]
    fn test_settings_load_async_blocking() {
        settings_clear_cache();
        let file = make_settings_yaml("key: value\n");
        let count =
            settings_load_async_blocking("t_async", &file.path().display().to_string()).unwrap();
        assert_eq!(count, 1);
        assert!(settings_is_cached("t_async"));
        settings_clear_cache();
    }

    #[test]
    #[serial]
    fn test_settings_load_batch_sync() {
        settings_clear_cache();
        let f1 = make_settings_yaml("a: 1\n");
        let f2 = make_settings_yaml("b: 2\n");
        let paths = vec![
            f1.path().display().to_string(),
            f2.path().display().to_string(),
        ];
        let count = settings_load_batch_sync(paths).unwrap();
        assert_eq!(count, 2);
        settings_clear_cache();
    }

    #[test]
    #[serial]
    fn test_settings_load_batch_async_blocking() {
        settings_clear_cache();
        let f1 = make_settings_yaml("a: 1\n");
        let f2 = make_settings_yaml("b: 2\n");
        let paths = vec![
            f1.path().display().to_string(),
            f2.path().display().to_string(),
        ];
        let count = settings_load_batch_async_blocking(paths).unwrap();
        assert_eq!(count, 2);
        settings_clear_cache();
    }

    #[test]
    #[serial]
    fn test_settings_cache_stats_and_size_on_empty_cache() {
        settings_clear_cache();
        settings_reset_cache_stats();
        let stats = settings_cache_stats();
        assert_eq!(stats.hits, 0);
        assert_eq!(stats.misses, 0);
        assert_eq!(stats.size, 0);
        assert_eq!(stats.capacity, 64);
        assert_eq!(settings_cache_size(), 0);
        assert!(settings_cache_keys().is_empty());
    }

    #[test]
    #[serial]
    fn test_settings_is_cached_and_invalidate() {
        settings_clear_cache();
        assert!(!settings_is_cached("nope"));
        assert!(!settings_invalidate("nope"));

        let file = make_settings_yaml("x: 1\n");
        settings_load_sync("inv_key", &file.path().display().to_string()).unwrap();
        assert!(settings_is_cached("inv_key"));
        assert!(settings_invalidate("inv_key"));
        assert!(!settings_is_cached("inv_key"));
        settings_clear_cache();
    }

    #[test]
    #[serial]
    fn test_settings_clear_cache_is_idempotent() {
        settings_clear_cache();
        settings_clear_cache();
        assert_eq!(settings_cache_size(), 0);
    }

    // ── Validator tests (D-09 — new) ───────────────────────────────

    #[test]
    fn test_settings_validate_structure_happy_path() {
        let issues = settings_validate_structure("CLASSIC_Settings:\n  VR Mode: false\n").unwrap();
        assert!(issues.is_empty());
    }

    #[test]
    fn test_settings_validate_structure_non_mapping_root_is_error() {
        let issues = settings_validate_structure("42").unwrap();
        assert_eq!(issues.len(), 1);
        assert_eq!(issues[0].severity, "error");
    }

    #[test]
    fn test_settings_validate_structure_empty_string() {
        // Empty yaml -> no documents -> null-document error
        let issues = settings_validate_structure("").unwrap();
        assert_eq!(issues.len(), 1);
        assert_eq!(issues[0].severity, "error");
    }

    #[test]
    fn test_settings_validate_value_int_happy() {
        assert!(settings_validate_value("42", "int").unwrap());
        assert!(settings_validate_value("42", "integer").unwrap());
        assert!(!settings_validate_value("abc", "int").unwrap());
    }

    #[test]
    fn test_settings_validate_value_unknown_type_errors() {
        let err = settings_validate_value("42", "quux").unwrap_err();
        assert!(err.contains("unknown setting type"));
    }

    #[test]
    fn test_settings_validate_value_all_canonical_tokens() {
        assert!(settings_validate_value("1", "bool").unwrap());
        assert!(settings_validate_value("1", "boolean").unwrap());
        assert!(settings_validate_value("3.14", "float").unwrap());
        assert!(settings_validate_value("3.14", "double").unwrap());
        assert!(settings_validate_value("/tmp", "path").unwrap());
        assert!(settings_validate_value("anything", "string").unwrap());
        assert!(settings_validate_value("anything", "str").unwrap());
    }

    #[test]
    fn test_settings_validate_value_case_insensitive() {
        assert!(settings_validate_value("42", "INT").unwrap());
        assert!(settings_validate_value("yes", "Bool").unwrap());
    }

    #[test]
    fn test_settings_coerce_value_bool_yes() {
        let out = settings_coerce_value("yes", "bool").unwrap();
        assert_eq!(out.kind, "bool");
        assert!(out.bool_val);
    }

    #[test]
    fn test_settings_coerce_value_path_vs_string_discriminator() {
        let p = settings_coerce_value("/tmp/x", "path").unwrap();
        assert_eq!(p.kind, "path");
        assert_eq!(p.string_val, "/tmp/x");

        let s = settings_coerce_value("/tmp/x", "string").unwrap();
        assert_eq!(s.kind, "string");
        assert_eq!(s.string_val, "/tmp/x");
    }

    #[test]
    fn test_settings_coerce_value_int_and_float() {
        let i = settings_coerce_value("42", "int").unwrap();
        assert_eq!(i.kind, "int");
        assert_eq!(i.int_val, 42);

        let f = settings_coerce_value("3.125", "float").unwrap();
        assert_eq!(f.kind, "float");
        assert!((f.float_val - 3.125).abs() < 1e-9);
    }

    #[test]
    fn test_settings_coerce_value_unknown_type_errors() {
        assert!(settings_coerce_value("42", "list").is_err());
    }
}
