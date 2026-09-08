//! Native loose-file issue classification and read-only directory inventory.

use super::file_operations::destination;
use super::scan_game::snapshot;
use super::{RunnerResult, invalid, text};
use classic_scangame_core::UnpackedScanner;
use serde_json::{Value, json};
use std::fs;

/// Scans input-owned paths and keeps DDS discovery separate from issue-count methods.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for path in fixture["directories"]
        .as_array()
        .ok_or_else(|| invalid("directories must be an array"))?
    {
        fs::create_dir_all(destination(root, &text(path)?)?)?;
    }
    for (path, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be an object"))?
    {
        let target = destination(root, path)?;
        fs::create_dir_all(
            target
                .parent()
                .ok_or_else(|| invalid("file needs parent"))?,
        )?;
        fs::write(target, text(content)?.as_bytes())?;
    }
    let scripts = fixture["scripts"]
        .as_array()
        .ok_or_else(|| invalid("scripts must be an array"))?
        .iter()
        .map(text)
        .collect::<RunnerResult<Vec<_>>>()?;
    let mut result = json!({});
    snapshot(root, &mut result, true)?;
    let scanner = UnpackedScanner::new();
    let value = scanner.scan_directory(root, &scripts)?;
    let count = value.animdata.len()
        + value.tex_frmt.len()
        + value.snd_frmt.len()
        + value.xse_file.len()
        + value.previs.len();
    if value.total_count() != count || value.has_issues() != (count > 0) {
        return Err(invalid("unpacked summary counted DDS inventory as issues").into());
    }
    let normalize = |values: &std::collections::HashSet<String>| {
        let mut values = values
            .iter()
            .map(|value| value.replace('\\', "/"))
            .collect::<Vec<_>>();
        values.sort();
        values
    };
    let mut dds = value
        .dds_files
        .iter()
        .map(|path| {
            Ok(path
                .strip_prefix(root)?
                .to_string_lossy()
                .replace('\\', "/"))
        })
        .collect::<RunnerResult<Vec<_>>>()?;
    dds.sort();
    result["issues"] = json!({"animation":normalize(&value.animdata),"formats":normalize(&value.tex_frmt),"sounds":normalize(&value.snd_frmt),"scripts":normalize(&value.xse_file),"previs":normalize(&value.previs),"dds":dds});
    snapshot(root, &mut result, false)?;
    Ok(result)
}
