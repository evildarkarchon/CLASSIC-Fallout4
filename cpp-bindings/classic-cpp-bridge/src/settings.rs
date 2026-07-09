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
//! 4. **User Settings read path**: Opens the deep User Settings module from an
//!    explicit CLASSIC root and returns the typed Update Preferences needed by
//!    native update-check policy.
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
use classic_user_settings_core::{
    CommitEligibility, DocumentClassification, PreferenceOrigin, Revision, SourceLocation,
    UserSettings,
};
use std::path::Path;
use yaml_rust2::Yaml;

/// Opaque wrapper around `YamlOperations` + a loaded YAML document.
pub struct YamlOps {
    ops: YamlOperations,
    doc: Option<Yaml>,
}

// ── Typed User Settings read path ───────────────────────────────────

/// Opens User Settings at an explicit CLASSIC root and flattens the typed
/// Update Preferences view into a CXX-compatible diagnostic DTO.
fn user_settings_open_update_preferences(classic_root: &str) -> ffi::UpdatePreferencesDto {
    let settings = UserSettings::open(Path::new(classic_root));
    let source = settings.source();
    let (has_schema_version, schema_major, schema_minor) = settings
        .schema_version()
        .map_or((false, 0, 0), |(major, minor)| (true, major, minor));
    let (has_original_content, original_content) = settings
        .original_bytes()
        .map_or((false, Vec::new()), |content| (true, content.to_vec()));

    ffi::UpdatePreferencesDto {
        update_check_enabled: settings.update_preferences().update_check(),
        update_check_origin: preference_origin_token(
            settings.update_preferences().update_check_origin(),
        )
        .to_string(),
        source_location: source_location_token(source.location()).to_string(),
        source_path: source
            .path()
            .map_or_else(String::new, |path| path.display().to_string()),
        classification: document_classification_token(settings.classification()).to_string(),
        has_schema_version,
        schema_major,
        schema_minor,
        revision: revision_token(settings.revision()),
        commit_eligibility: commit_eligibility_token(settings.commit_eligibility()).to_string(),
        diagnostics: settings
            .diagnostics()
            .iter()
            .map(|diagnostic| ffi::UserSettingsDiagnosticDto {
                code: diagnostic.code().to_string(),
                message: diagnostic.message().to_string(),
            })
            .collect(),
        has_original_content,
        original_content,
    }
}

/// Returns the stable cross-language token for a preference's provenance.
fn preference_origin_token(origin: PreferenceOrigin) -> &'static str {
    match origin {
        PreferenceOrigin::Document => "document",
        PreferenceOrigin::Default => "default",
        PreferenceOrigin::DegradedFallback => "degraded_fallback",
    }
}

/// Returns the stable cross-language token for the selected source location.
fn source_location_token(location: SourceLocation) -> &'static str {
    match location {
        SourceLocation::Canonical => "canonical",
        SourceLocation::Legacy => "legacy",
        SourceLocation::Missing => "missing",
    }
}

/// Returns the stable cross-language token for document classification.
fn document_classification_token(classification: DocumentClassification) -> &'static str {
    match classification {
        DocumentClassification::Current => "current",
        DocumentClassification::Unversioned => "unversioned",
        DocumentClassification::Older => "older",
        DocumentClassification::NewerCompatible => "newer_compatible",
        DocumentClassification::FutureMajor => "future_major",
        DocumentClassification::LegacyFlat => "legacy_flat",
        DocumentClassification::Malformed => "malformed",
        DocumentClassification::Missing => "missing",
    }
}

/// Returns the stable cross-language token for commit eligibility.
fn commit_eligibility_token(eligibility: CommitEligibility) -> &'static str {
    match eligibility {
        CommitEligibility::Eligible => "eligible",
        CommitEligibility::RequiresMigration => "requires_migration",
        CommitEligibility::BlockedUntrusted => "blocked_untrusted",
    }
}

/// Formats a content revision without exposing Rust-only enum layout through CXX.
fn revision_token(revision: &Revision) -> String {
    match revision {
        Revision::Missing => "missing".to_string(),
        Revision::Unavailable => "unavailable".to_string(),
        Revision::ContentSha256(digest) => {
            let mut token = String::with_capacity("sha256:".len() + digest.len() * 2);
            token.push_str("sha256:");
            for byte in digest {
                use std::fmt::Write as _;
                write!(&mut token, "{byte:02x}").expect("writing to a String cannot fail");
            }
            token
        }
    }
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

    /// One structured diagnostic produced while opening User Settings.
    struct UserSettingsDiagnosticDto {
        code: String,
        message: String,
    }

    /// Typed Update Preferences plus User Settings source and diagnostic metadata.
    ///
    /// The boolean is already safety-adjusted by Rust: missing settings use the
    /// published default, while malformed, incompatible, or invalid values are
    /// fail-closed. C++ callers must not reinterpret raw YAML.
    struct UpdatePreferencesDto {
        update_check_enabled: bool,
        update_check_origin: String,
        source_location: String,
        source_path: String,
        classification: String,
        has_schema_version: bool,
        schema_major: u32,
        schema_minor: u32,
        revision: String,
        commit_eligibility: String,
        diagnostics: Vec<UserSettingsDiagnosticDto>,
        has_original_content: bool,
        original_content: Vec<u8>,
    }

    extern "Rust" {
        type YamlOps;

        fn yaml_file_as_str(f: YamlFile) -> String;
        fn yaml_file_description(f: YamlFile) -> String;
        fn must_not_be_none_key(key: &str) -> bool;
        fn settings_ignore_none_contains(key: &str) -> bool;

        /// Open User Settings from an explicit CLASSIC root and return the
        /// typed Update Preferences view used by native update-check policy.
        fn user_settings_open_update_preferences(classic_root: &str) -> UpdatePreferencesDto;

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
#[path = "settings_tests.rs"]
mod tests;
