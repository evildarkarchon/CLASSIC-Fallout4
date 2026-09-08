//! Generic settings loading through public sync/async APIs on the shared runtime.

use super::{RunnerResult, invalid, strings, text};
use classic_settings_core as settings;
use classic_shared_core::get_runtime;
use serde_json::{Value, json};
use std::{
    fs,
    path::{Path, PathBuf},
};

/// Ensure global cache cleanup on every scenario exit, including native errors.
struct CacheReset;
impl Drop for CacheReset {
    fn drop(&mut self) {
        settings::clear_cache();
    }
}

/// Clear scenario-owned global YAML cache state even when a native operation fails.
struct YamlCacheReset;
impl Drop for YamlCacheReset {
    fn drop(&mut self) {
        settings::clear_global_yaml_cache();
    }
}

/// Contain authored destinations before creating scenario-owned files.
fn owned(root: &Path, relative: &str) -> RunnerResult<PathBuf> {
    if relative.is_empty()
        || relative.contains(['\\', ':'])
        || relative
            .split('/')
            .any(|part| matches!(part, "" | "." | ".."))
    {
        return Err(invalid("settings fixture requires a contained relative path").into());
    }
    Ok(root.join(relative))
}

/// Preserve typed core failures and their attributed path without OS-specific prose.
fn domain_error(error: settings::SettingsError, root: &Path) -> RunnerResult<Value> {
    let (kind, path) = match error {
        settings::SettingsError::IoError { path, .. } => ("io", path),
        settings::SettingsError::YamlParseError { source, .. } => (
            "yaml-parse",
            source
                .path()
                .ok_or_else(|| invalid("expected file-backed parse error"))?
                .clone(),
        ),
        other => return Err(other.into()),
    };
    Ok(json!({"kind": kind, "path": path.strip_prefix(root)?.to_string_lossy().replace('\\', "/")}))
}

/// Inventory every resulting file so unexpected writes cannot hide behind input paths.
pub(super) fn inventory(
    root: &Path,
    directory: &Path,
    files: &mut serde_json::Map<String, Value>,
) -> RunnerResult<()> {
    for entry in fs::read_dir(directory)? {
        let path = entry?.path();
        if path.is_dir() {
            inventory(root, &path, files)?;
        } else {
            files.insert(
                path.strip_prefix(root)?
                    .to_string_lossy()
                    .replace('\\', "/"),
                Value::String(fs::read_to_string(path)?),
            );
        }
    }
    Ok(())
}

/// Observe document/file counts, cache effects and attributed sync/async failures.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    if fixture["kind"] == "yaml-batch" {
        return execute_yaml_batch(fixture);
    }
    if fixture["kind"] == "yaml" {
        return execute_yaml(fixture);
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    let _reset = CacheReset;
    for (relative, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("expected files object"))?
    {
        let path = owned(root, relative)?;
        fs::create_dir_all(path.parent().ok_or_else(|| invalid("missing parent"))?)?;
        fs::write(path, text(content)?.as_bytes())?;
    }
    settings::reset_cache_stats();
    let mut observed = serde_json::Map::new();
    for operation in ["sync", "async", "batchSync", "batchAsync"] {
        settings::clear_cache();
        let batch = operation.starts_with("batch");
        let relatives = if batch {
            strings(&fixture["request"]["batch"])?
        } else {
            vec![text(&fixture["request"]["single"])?]
        };
        let paths = relatives
            .iter()
            .map(|relative| owned(root, relative))
            .collect::<RunnerResult<Vec<_>>>()?;
        let refs: Vec<_> = paths.iter().map(PathBuf::as_path).collect();
        let keys = if batch {
            paths
                .iter()
                .map(|path| path.to_string_lossy().to_string())
                .collect()
        } else {
            vec!["conformance.single".to_string()]
        };
        let result = match operation {
            "sync" => settings::load_settings_sync(&keys[0], &paths[0]).map(|docs| docs.len()),
            "async" => get_runtime()
                .block_on(settings::load_settings_async(&keys[0], &paths[0]))
                .map(|docs| docs.len()),
            "batchSync" => settings::load_batch_sync(&refs),
            _ => get_runtime().block_on(settings::load_batch_async(&refs)),
        };
        let (count, error) = match result {
            Ok(count) => (json!(count), Value::Null),
            Err(error) => (Value::Null, domain_error(error, root)?),
        };
        let cached: Vec<_> = keys.iter().map(|key| settings::is_cached(key)).collect();
        let mut normalized_keys: Vec<_> = settings::cache_keys()
            .iter()
            .map(|key| {
                if batch {
                    Path::new(key)
                        .strip_prefix(root)
                        .unwrap()
                        .to_string_lossy()
                        .replace('\\', "/")
                } else {
                    key.clone()
                }
            })
            .collect();
        normalized_keys.sort();
        let size = settings::cache_size();
        let stats = cache_statistics();
        let invalidated: Vec<_> = keys.iter().map(|key| settings::invalidate(key)).collect();
        let invalidated_again: Vec<_> = keys.iter().map(|key| settings::invalidate(key)).collect();
        let after_invalidate = settings::cache_size();
        settings::reset_cache_stats();
        let reset_stats = cache_statistics();
        let cache_state = json!({"keys": normalized_keys, "size": size, "stats": stats, "invalidated": invalidated, "invalidatedAgain": invalidated_again, "afterInvalidate": after_invalidate, "resetStats": reset_stats});
        // Refill successfully loaded entries so clearing is observed independently of invalidation.
        for ((key, path), present) in keys.iter().zip(&paths).zip(&cached) {
            if *present {
                settings::load_settings_sync(key, path)?;
            }
        }
        settings::clear_cache();
        let after_clear: Vec<_> = keys.iter().map(|key| settings::is_cached(key)).collect();
        observed.insert(
            operation.to_string(),
            json!({"count": count, "error": error, "cached": cached, "afterClear": after_clear, "cacheState": cache_state}),
        );
    }
    let mut files = serde_json::Map::new();
    inventory(root, root, &mut files)?;
    observed.insert("files".to_string(), Value::Object(files));
    Ok(Value::Object(observed))
}

/// Project stable cache counters while retaining whether storage is bounded.
fn cache_statistics() -> Value {
    let stats = settings::cache_stats();
    json!({"hits": stats.hits, "misses": stats.misses, "hitRateZero": stats.hit_rate == 0.0, "size": stats.size, "bounded": stats.capacity > 0})
}

/// Project authored JSON-compatible YAML values without hiding typed scalar changes.
pub(super) fn yaml_json(value: &settings::Yaml) -> RunnerResult<Value> {
    use settings::Yaml;
    Ok(match value {
        Yaml::String(value) => json!(value),
        Yaml::Integer(value) => json!(value),
        Yaml::Boolean(value) => json!(value),
        Yaml::Null | Yaml::BadValue => Value::Null,
        Yaml::Array(values) => {
            Value::Array(values.iter().map(yaml_json).collect::<RunnerResult<_>>()?)
        }
        Yaml::Hash(values) => Value::Object(
            values
                .iter()
                .map(|(key, value)| {
                    Ok((
                        key.as_str()
                            .ok_or_else(|| invalid("expected string YAML key"))?
                            .to_string(),
                        yaml_json(value)?,
                    ))
                })
                .collect::<RunnerResult<_>>()?,
        ),
        _ => return Err(invalid("unexpected non-JSON YAML value").into()),
    })
}

/// Observe YAML handles through parsing, typed access, persisted mutation and cache reuse.
fn execute_yaml(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let _reset = YamlCacheReset;
    let ops = settings::YamlOperations::new();
    ops.clear_cache();
    let mut doc = ops.parse_yaml(&text(&fixture["content"])?)?;
    let before = json!({"name": ops.get_string_value(&doc, "name", "fallback"), "missing": ops.get_string_value(&doc, "absent", "fallback"), "items": ops.get_vec_value(&doc, "items"), "mapping": ops.get_hashmap_value(&doc, "mapping")});
    let updates = fixture["updates"]
        .as_object()
        .ok_or_else(|| invalid("expected updates"))?;
    for key in strings(&fixture["updateOrder"])? {
        let value = &updates[&key];
        let native = match value {
            Value::String(value) => settings::Yaml::String(value.clone()),
            Value::Bool(value) => settings::Yaml::Boolean(*value),
            Value::Number(value) => {
                settings::Yaml::Integer(value.as_i64().ok_or_else(|| invalid("expected integer"))?)
            }
            Value::Array(values) => settings::Yaml::Array(
                values
                    .iter()
                    .map(|value| Ok(settings::Yaml::String(text(value)?.to_string())))
                    .collect::<RunnerResult<_>>()?,
            ),
            _ => return Err(invalid("unsupported fixture update").into()),
        };
        doc = ops.set_setting(&doc, &key, native)?;
    }
    let round_trip = ops.parse_yaml(&ops.dump_yaml(&doc)?)?;
    let after = updates
        .keys()
        .map(|key| {
            Ok((
                key.clone(),
                yaml_json(
                    &ops.get_setting(&round_trip, key)
                        .unwrap_or(settings::Yaml::Null),
                )?,
            ))
        })
        .collect::<RunnerResult<serde_json::Map<_, _>>>()?;
    let path = temporary.path().join("saved.yaml");
    ops.save_yaml_file(&path, &doc)?;
    let initial = settings::yaml_cache_stats();
    let loaded = ops.load_yaml_file(&path)?;
    ops.load_yaml_file(&path)?;
    let stats = settings::yaml_cache_stats();
    let persisted = updates
        .keys()
        .map(|key| {
            Ok((
                key.clone(),
                yaml_json(
                    &ops.get_setting(&loaded, key)
                        .unwrap_or(settings::Yaml::Null),
                )?,
            ))
        })
        .collect::<RunnerResult<serde_json::Map<_, _>>>()?;
    let mut files = serde_json::Map::new();
    inventory(temporary.path(), temporary.path(), &mut files)?;
    ops.clear_cache();
    ops.load_yaml_file(&path)?;
    if settings::yaml_cache_stats().size != 1 {
        return Err(invalid("global clear fixture did not populate YAML cache").into());
    }
    settings::clear_global_yaml_cache();
    Ok(
        json!({"before": before, "after": after, "persisted": persisted, "files": files, "cache": {"hits": stats.hits - initial.hits, "misses": stats.misses - initial.misses, "size": stats.size, "afterClear": settings::yaml_cache_stats().size}}),
    )
}

/// Observe batch access and order-preserving mappings through Rust's public YAML API.
fn execute_yaml_batch(fixture: &Value) -> RunnerResult<Value> {
    let ops = settings::YamlOperations::new();
    let doc = ops.parse_yaml(&text(&fixture["content"])?)?;
    let keys = strings(&fixture["keys"])?;
    let key_refs: Vec<_> = keys.iter().map(String::as_str).collect();
    let project =
        |values: std::collections::HashMap<String, settings::Yaml>| -> RunnerResult<Value> {
            Ok(Value::Object(
                values
                    .iter()
                    .map(|(key, value)| Ok((key.clone(), yaml_json(value)?)))
                    .collect::<RunnerResult<_>>()?,
            ))
        };
    let before = project(ops.get_settings_batch(&doc, &key_refs))?;
    let ordered: Vec<_> = ops
        .get_indexmap_value(&doc, "mapping")
        .into_iter()
        .collect();
    let vectors = ops.get_hashmap_vec_value(&doc, "vectors");
    let updates = fixture["updates"]
        .as_object()
        .ok_or_else(|| invalid("expected batch updates"))?;
    let values: Vec<_> = updates
        .iter()
        .map(|(key, value)| {
            Ok((
                key.as_str(),
                settings::Yaml::String(text(value)?.to_string()),
            ))
        })
        .collect::<RunnerResult<_>>()?;
    let updated = ops.set_settings_batch(&doc, &values)?;
    Ok(
        json!({"before": before, "ordered": ordered, "vectors": vectors, "after": project(ops.get_settings_batch(&updated, &key_refs))?}),
    )
}
