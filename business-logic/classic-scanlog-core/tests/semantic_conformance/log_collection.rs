//! Native log moves, preserved XSE source copies, and additive custom discovery.

use super::file_operations::{destination, files};
use super::{RunnerResult, invalid, text};
use classic_file_io_core::LogCollector;
use serde_json::{Value, json};
use std::{
    fs,
    path::{Path, PathBuf},
};

/// Materializes contained authored files before a native collection stage.
fn materialize(root: &Path, values: &Value) -> RunnerResult<()> {
    for (path, content) in values
        .as_object()
        .ok_or_else(|| invalid("collection files must be an object"))?
    {
        let target = destination(root, path)?;
        fs::create_dir_all(
            target
                .parent()
                .ok_or_else(|| invalid("file needs parent"))?,
        )?;
        fs::write(target, text(content)?.as_bytes())?;
    }
    Ok(())
}

/// Normalizes only actual returned paths while preserving the complete result set.
fn paths(root: &Path, values: Vec<PathBuf>) -> RunnerResult<Vec<String>> {
    let mut values = values
        .iter()
        .map(|path| {
            Ok(path
                .strip_prefix(root)?
                .to_string_lossy()
                .replace('\\', "/"))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    values.sort();
    Ok(values)
}

/// Runs full collection and individual copy/move/discovery APIs against two input stages.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for folder in ["base", "xse", "custom"] {
        fs::create_dir(root.join(folder))?;
    }
    materialize(root, &fixture["files"])?;
    let yaml_root = tempfile::tempdir()?;
    // The explicit local-YAML XSE path avoids ambient installation discovery.
    // Keep bootstrap YAML outside the observed log tree because it contains an invocation path.
    let collector = if fixture["configured"] == true {
        fs::write(
            yaml_root.path().join("CLASSIC Fallout4 Local.yaml"),
            format!(
                "Game_Info:\n  Docs_Folder_XSE: {}\n",
                serde_json::to_string(&root.join("xse").to_string_lossy())?
            ),
        )?;
        LogCollector::new_for_scan(
            root.join("base"),
            yaml_root.path(),
            "Fallout4",
            "OG",
            None,
            Some(root.join("custom")),
        )
    } else {
        LogCollector::new(
            root.join("base"),
            Some(root.join("xse")),
            Some(root.join("custom")),
        )
    };
    let runtime = classic_shared_core::get_runtime();
    let mut result = json!({"before":files(root)?,"first":paths(root,runtime.block_on(collector.collect_all())?)?});
    if json!(paths(
        root,
        runtime.block_on(collector.collect_crash_logs())?
    )?) != result["first"]
    {
        return Err(invalid("crash discovery disagrees with full collection").into());
    }
    if collector.crash_logs_dir() != root.join("base/Crash Logs")
        || collector.pastebin_dir() != root.join("base/Crash Logs/Pastebin")
    {
        return Err(invalid("collector path accessor changed").into());
    }
    result["afterFirst"] = files(root)?;
    materialize(root, &fixture["later"])?;
    let moved = runtime.block_on(collector.move_from_base_folder())?;
    let copied = runtime.block_on(collector.copy_from_xse_folder())?;
    let later = fixture["later"]
        .as_object()
        .ok_or_else(|| invalid("later files must be an object"))?;
    if moved
        != later
            .keys()
            .filter(|path| path.starts_with("base/"))
            .count()
        || copied != later.keys().filter(|path| path.starts_with("xse/")).count()
    {
        return Err(invalid("individual move/copy counts disagree").into());
    }
    result["second"] = json!(paths(
        root,
        runtime.block_on(collector.collect_crash_logs())?
    )?);
    if json!(paths(root, runtime.block_on(collector.collect_all())?)?) != result["second"] {
        return Err(invalid("full discovery changed after individual operations").into());
    }
    result["files"] = files(root)?;
    let mut targeted = result["second"]
        .as_array()
        .ok_or_else(|| invalid("missing second collection"))?
        .iter()
        .map(|value| text(value).map(|path| root.join(path)))
        .collect::<RunnerResult<Vec<_>>>()?;
    targeted.push(root.join("missing-target.log"));
    let resolved =
        runtime.block_on(classic_file_io_core::log_collection::resolve_targeted_inputs(targeted));
    if json!(paths(root, resolved.logs)?) != result["second"]
        || resolved.rejected.len() != 1
        || resolved.rejected[0].path != root.join("missing-target.log")
        || resolved.rejected[0].reason != "path does not exist"
        || files(root)? != result["files"]
    {
        return Err(invalid("targeted resolver changed paths, rejection or owned files").into());
    }
    Ok(result)
}
