//! Public text I/O observations with a fresh filesystem for every scenario.

use super::{RunnerResult, invalid, text};
use classic_file_io_core::{FileIOCore, FileIOError};
use serde_json::{Value, json};
use std::{
    fs,
    path::{Path, PathBuf},
};

/// Rejects nonportable fixture destinations before native file operations begin.
pub(super) fn destination(root: &Path, path: &str) -> RunnerResult<PathBuf> {
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
pub(super) fn files(root: &Path) -> RunnerResult<Value> {
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
    if operation == "read-text" {
        check_read_variants(&io, &target, &observation)?;
        observation["similarity"] = similarity_observation()?;
    } else if observation["error"].is_null() {
        check_write_variants(&io, &target, &text(&fixture["content"])?)?;
    }
    observation["files"] = files(root)?;
    Ok(observation)
}

/// Compare both native similarity APIs while preserving all owned source bytes.
fn similarity_observation() -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let left = temporary.path().join("left.txt");
    let right = temporary.path().join("right.txt");
    let first = "alpha\nbeta\n";
    fs::write(&left, first)?;
    let mut results = Vec::new();
    for second in [first, "gamma\ndelta\n", "alpha\ngamma\n"] {
        fs::write(&right, second)?;
        let result = classic_file_io_core::similarity::calculate_similarity(&left, &right)?;
        if classic_file_io_core::similarity::similarity_ratio(first, second) != result
            || fs::read_to_string(&left)? != first
            || fs::read_to_string(&right)? != second
        {
            return Err(invalid("similarity APIs disagree or changed source bytes").into());
        }
        results.push(format!("{result:.6}"));
    }
    Ok(json!(results))
}

/// Checks public read/stream/metadata variants against native text and durable bytes.
/// A disagreement aborts the receipt so one successful alias cannot mask another.
fn check_read_variants(io: &FileIOCore, target: &Path, observation: &Value) -> RunnerResult<()> {
    let runtime = classic_shared_core::get_runtime();
    let content = observation["content"].as_str();
    let expected_lines = content.map(|value| value.lines().map(str::to_owned).collect::<Vec<_>>());
    let variants = runtime.block_on(async {
        let bytes = io.read_bytes(target).await.map(|value| json!(value));
        let lines = io.read_lines(target).await.map(|value| json!(value));
        let mmap = io.read_file_mmap(target).await.map(|value| json!(value));
        let asynchronous = async {
            let mut stream = io.stream_lines(target).await?;
            let mut lines = Vec::new();
            while let Some(line) = stream.next_line().await? {
                lines.push(line);
            }
            Ok::<_, FileIOError>(json!(lines))
        }
        .await;
        let synchronous = io.stream_lines_sync(target).and_then(|stream| {
            stream
                .collect::<Result<Vec<_>, _>>()
                .map(|lines| json!(lines))
                .map_err(FileIOError::from)
        });
        [
            (bytes, content.map(|value| json!(value.as_bytes()))),
            (lines, expected_lines.as_ref().map(|value| json!(value))),
            (mmap, content.map(|value| json!(value))),
            (
                asynchronous,
                expected_lines.as_ref().map(|value| json!(value)),
            ),
            (
                synchronous,
                expected_lines.as_ref().map(|value| json!(value)),
            ),
        ]
    });
    for (actual, expected) in variants {
        match (actual, expected) {
            (Ok(actual), Some(expected)) if actual == expected => {}
            (Err(FileIOError::IoError(_)), None) if observation["error"] == "io_error" => {}
            _ => return Err(invalid("public read variant disagrees with native text read").into()),
        }
    }
    if io.file_exists(target) != target.is_file()
        || io.get_file_size(target) != fs::metadata(target).ok().map(|metadata| metadata.len())
    {
        return Err(invalid("public metadata disagrees with durable file").into());
    }
    let batch = runtime.block_on(io.read_multiple_files(vec![target.to_path_buf()]));
    if batch.len() != 1 || batch[0].0 != target {
        return Err(invalid("public batch reader changed the requested path").into());
    }
    match (&batch[0].1, content) {
        (Ok(actual), Some(expected)) if actual == expected => {}
        (Err(FileIOError::IoError(_)), None) => {}
        _ => return Err(invalid("public batch reader disagrees with text read").into()),
    }
    let parent = target
        .parent()
        .ok_or_else(|| invalid("file needs a parent"))?;
    let mut walked = io.walk_directory(parent, None, None)?;
    walked.sort();
    let mut expected_files = Vec::new();
    collect_files(parent, parent, &mut expected_files)?;
    let mut expected_paths = expected_files
        .iter()
        .map(|value| parent.join(value["path"].as_str().unwrap()))
        .collect::<Vec<_>>();
    expected_paths.sort();
    if walked != expected_paths {
        return Err(invalid("public directory walk disagrees with durable files").into());
    }
    if let Some(content) = content {
        fs::write(target, b"fresh after invalidation\n")?;
        runtime.block_on(io.clear_cache());
        if runtime.block_on(io.read_file(target))? != "fresh after invalidation\n" {
            return Err(invalid("cache invalidation preserved stale content").into());
        }
        fs::write(target, content.as_bytes())?;
        runtime.block_on(io.clear_cache());
    }
    Ok(())
}

/// Verifies public write variants against durable bytes, preserving the final fixture state.
fn check_write_variants(io: &FileIOCore, target: &Path, content: &str) -> RunnerResult<()> {
    let runtime = classic_shared_core::get_runtime();
    runtime.block_on(io.write_bytes(target, content.as_bytes().to_vec()))?;
    if fs::read(target)? != content.as_bytes() {
        return Err(invalid("byte writer changed durable content").into());
    }
    if content.ends_with('\n') {
        runtime.block_on(io.write_lines(target, content.lines().map(str::to_owned).collect()))?;
        if fs::read(target)? != content.as_bytes() {
            return Err(invalid("line writer changed durable content").into());
        }
    }
    fs::write(target, b"")?;
    runtime.block_on(io.append_file(target, content))?;
    if fs::read(target)? != content.as_bytes() {
        return Err(invalid("append writer changed durable content").into());
    }
    for (_, result) in
        runtime.block_on(io.write_multiple_files(vec![(target.to_path_buf(), content.to_owned())]))
    {
        result?;
    }
    if fs::read(target)? != content.as_bytes() {
        return Err(invalid("batch writer changed durable content").into());
    }
    Ok(())
}
