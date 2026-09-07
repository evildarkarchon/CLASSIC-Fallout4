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
fn inventory(
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
        settings::clear_cache();
        let after_clear: Vec<_> = keys.iter().map(|key| settings::is_cached(key)).collect();
        observed.insert(
            operation.to_string(),
            json!({"count": count, "error": error, "cached": cached, "afterClear": after_clear}),
        );
    }
    let mut files = serde_json::Map::new();
    inventory(root, root, &mut files)?;
    observed.insert("files".to_string(), Value::Object(files));
    Ok(Value::Object(observed))
}
