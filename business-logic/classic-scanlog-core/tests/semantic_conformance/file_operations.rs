//! Public text I/O observations with a fresh filesystem for every scenario.

use super::{RunnerResult, invalid, text};
use classic_file_io_core::{FileIOCore, FileIOError};
use serde_json::{Value, json};
use std::{
    fs,
    path::{Path, PathBuf},
};

/// Rejects nonportable fixture destinations before native file operations begin.
fn destination(root: &Path, path: &str) -> RunnerResult<PathBuf> {
    if path.is_empty()
        || path.contains([':', '\\'])
        || path.split('/').any(|part| matches!(part, "" | "." | ".."))
    {
        return Err(invalid("file operation needs a contained relative path").into());
    }
    Ok(root.join(path))
}

/// Recursively re-reads exact durable text, including unexpected files.
fn collect_files(root: &Path, directory: &Path, output: &mut Vec<Value>) -> RunnerResult<()> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            collect_files(root, &entry.path(), output)?;
        } else if entry.file_type()?.is_file() {
            output.push(
                json!({"path":entry.path().strip_prefix(root)?.to_string_lossy().replace('\\', "/"),
                "content":fs::read_to_string(entry.path())?}),
            );
        } else {
            return Err(invalid("unexpected non-file durable artifact").into());
        }
    }
    Ok(())
}

/// Returns a stable full inventory, independent of filesystem enumeration order.
fn files(root: &Path) -> RunnerResult<Value> {
    let mut output = Vec::new();
    collect_files(root, root, &mut output)?;
    output.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    Ok(json!(output))
}

/// Executes an input-only public file I/O operation on the shared core runtime.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let operation = text(&fixture["operation"])?;
    if !matches!(operation.as_str(), "read-text" | "write-text") {
        return Err(invalid("unsupported file operation").into());
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    let path = text(&fixture["path"])?;
    let target = destination(root, &path)?;
    for (path, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be an object"))?
    {
        let target = destination(root, path)?;
        fs::create_dir_all(
            target
                .parent()
                .ok_or_else(|| invalid("file needs a parent"))?,
        )?;
        fs::write(target, text(content)?.as_bytes())?;
    }
    let mut observation = json!({"operation":operation,"path":path,"content":null,"error":null,
        "beforeFiles":files(root)?,"files":[]});
    let io = FileIOCore::default();
    let runtime = classic_shared_core::get_runtime();
    let result = if operation == "read-text" {
        runtime.block_on(io.read_file(&target)).map(Some)
    } else {
        runtime
            .block_on(io.write_file(&target, &text(&fixture["content"])?))
            .map(|()| None)
    };
    match result {
        Ok(content) => observation["content"] = json!(content),
        Err(FileIOError::IoError(_)) => observation["error"] = json!("io_error"),
        Err(error) => return Err(error.into()),
    }
    observation["files"] = files(root)?;
    Ok(observation)
}
