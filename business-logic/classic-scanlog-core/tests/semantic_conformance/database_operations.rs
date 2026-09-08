//! Observe the public SQLite pool with owned fixture bytes and deterministic lifecycle state.

use super::{RunnerResult, invalid, text};
use classic_database_core::{DatabaseError, DatabasePool};
use classic_shared_core::get_runtime;
use serde_json::{Value, json};
use std::{fs, path::Path, time::Duration};

/// Decode exact input bytes without adding a SQLite construction dependency to adapters.
fn decode_hex(value: &str) -> RunnerResult<Vec<u8>> {
    if !value.len().is_multiple_of(2)
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(invalid("database bytes require lowercase hex").into());
    }
    (0..value.len())
        .step_by(2)
        .map(|offset| u8::from_str_radix(&value[offset..offset + 2], 16).map_err(Into::into))
        .collect()
}

/// Re-read all durable bytes, including any unexpected SQLite sidecar files.
fn inventory(root: &Path, directory: &Path) -> RunnerResult<Vec<Value>> {
    let mut files = Vec::new();
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let path = entry.path();
        if entry.file_type()?.is_symlink() {
            return Err(invalid("unexpected link in database workspace").into());
        }
        if path.is_dir() {
            files.extend(inventory(root, &path)?);
        } else {
            let hex: String = fs::read(&path)?
                .iter()
                .map(|byte| format!("{byte:02x}"))
                .collect();
            files.push(json!({"path": path.strip_prefix(root)?.to_string_lossy().replace('\\', "/"), "hex": hex}));
        }
    }
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    Ok(files)
}

/// Run native pool operations; cleanup precedes byte observation even on a native failure.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    if fixture == &json!({"operation":"cache-defaults"}) {
        use classic_database_core::{
            BATCH_CACHE_TTL_SECS, DEFAULT_CACHE_CLEANUP_INTERVAL_SECS,
            DEFAULT_CACHE_CLEANUP_OP_THRESHOLD, DEFAULT_CACHE_TTL_SECS,
            DEFAULT_QUERY_CACHE_CAPACITY, MAX_CACHE_TTL_SECS,
        };
        return Ok(
            json!({"defaultTtl":DEFAULT_CACHE_TTL_SECS, "batchTtl":BATCH_CACHE_TTL_SECS, "maximumTtl":MAX_CACHE_TTL_SECS, "capacity":DEFAULT_QUERY_CACHE_CAPACITY, "cleanupThreshold":DEFAULT_CACHE_CLEANUP_OP_THRESHOLD, "cleanupInterval":DEFAULT_CACHE_CLEANUP_INTERVAL_SECS}),
        );
    }
    if fixture["operation"] != "pool"
        || fixture.as_object().is_none_or(|object| {
            object.len() != 3
                || !object.contains_key("databaseHex")
                || !object.contains_key("queries")
        })
    {
        return Err(invalid("unsupported database operation fixture").into());
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    let path = root.join("formids.db");
    if !fixture["databaseHex"].is_null() {
        fs::write(&path, decode_hex(&text(&fixture["databaseHex"])?)?)?;
    }
    let pairs = fixture["queries"]
        .as_array()
        .ok_or_else(|| invalid("database queries require string pairs"))?
        .iter()
        .map(|pair| {
            if pair.as_array().is_none_or(|values| values.len() != 2) {
                return Err(invalid("database queries require string pairs").into());
            }
            Ok((text(&pair[0])?.to_owned(), text(&pair[1])?.to_owned()))
        })
        .collect::<RunnerResult<Vec<(String, String)>>>()?;
    let pool = DatabasePool::new(Some(1), Duration::from_secs(300), "Fallout4".into());
    let mut observation = json!({"table": pool.get_game_table(), "initialAvailable": pool.is_available(), "error": null, "single": [], "batch": []});
    let runtime = get_runtime();
    let executed: RunnerResult<()> = runtime.block_on(async {
        match pool.initialize(vec![path]).await {
            Ok(()) => {}
            Err(DatabaseError::OpenError(_)) => {
                observation["error"] = json!({"code": "open", "path": "formids.db"})
            }
            Err(error) => return Err(error.into()),
        }
        observation["available"] = json!(pool.is_available());
        if observation["error"].is_null() {
            let mut single = Vec::new();
            for (formid, plugin) in &pairs {
                single.push(pool.get_entry(formid, plugin, None).await?);
            }
            let batch = pool.get_entries_batch(pairs.clone(), None, 100).await?;
            observation["single"] = json!(single);
            observation["batch"] = json!(
                pairs
                    .iter()
                    .map(|(formid, plugin)| batch.get(&format!("{formid}:{plugin}")))
                    .collect::<Vec<_>>()
            );
        }
        let cache_size = pool.cache_size();
        observation["cleared"] = json!(pool.clear_cache(false));
        if observation["cleared"] != json!(cache_size) {
            return Err(invalid("cache size disagrees with removed entries").into());
        }
        observation["afterClear"] = json!(pool.clear_cache(false));
        Ok(())
    });
    // Explicitly close even when the operation fails; Windows cleanup cannot unlink open SQLite handles.
    runtime.block_on(pool.close())?;
    executed?;
    observation["closedAvailable"] = json!(pool.is_available());
    observation["closedCache"] = json!(pool.clear_cache(false));
    observation["files"] = json!(inventory(root, root)?);
    Ok(observation)
}
