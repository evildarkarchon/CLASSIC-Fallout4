//! Public fingerprint observations without an expected-value oracle.

use super::RunnerResult;
use classic_file_io_core::{EncodingDetector, FileHasher, FileIOError};
use serde_json::{Value, json};
use std::fs;

/// Project deterministic counters and check the independent size accessor.
fn stats() -> Value {
    let value = FileHasher::cache_stats();
    assert_eq!(value.size, FileHasher::cache_size());
    json!({"hits": value.hits, "misses": value.misses, "size": value.size})
}

/// Exercise hashing, filtering, encoding and cache reset against owned files.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let target = temporary.path().join("payload.bin");
    if !fixture["bytes"].is_null() {
        let bytes: Vec<u8> = serde_json::from_value(fixture["bytes"].clone())?;
        fs::write(&target, bytes)?;
    }
    FileHasher::clear_cache();
    FileHasher::reset_cache_stats();
    let mut digest = None;
    let mut error: Option<&str> = None;
    for _ in 0..2 {
        match FileHasher::hash_file(&target) {
            Ok(value) => digest = Some(value),
            Err(FileIOError::NotFound(_)) => error = Some("not_found"),
            Err(other) => return Err(other.into()),
        }
    }
    let cache = stats();
    let missing = temporary.path().join("absent.bin");
    let paths = [target.as_path(), missing.as_path()];
    let batch: serde_json::Map<String, Value> = FileHasher::hash_files_parallel(&paths)?
        .into_iter()
        .filter_map(|(path, value)| {
            value.map(|value| {
                (
                    path.file_name().unwrap().to_string_lossy().into_owned(),
                    json!(value),
                )
            })
        })
        .collect();
    let mapped: serde_json::Map<String, Value> = FileHasher::hash_files_to_map(&paths)?
        .into_iter()
        .map(|(path, value)| {
            (
                path.file_name().unwrap().to_string_lossy().into_owned(),
                json!(value),
            )
        })
        .collect();
    FileHasher::reset_cache_stats();
    let reset = stats();
    FileHasher::clear_cache();
    let encoding = if target.exists() {
        Some(EncodingDetector::new().detect_name(&fs::read(&target)?))
    } else {
        None
    };
    let files = if target.exists() {
        vec![json!({"path": "payload.bin", "bytes": fs::read(&target)?})]
    } else {
        vec![]
    };
    Ok(
        json!({"hash": digest, "error": error, "encoding": encoding, "batch": batch, "map": mapped,
        "cache": cache, "reset": reset, "cleared": stats(), "files": files}),
    )
}
