//! Deterministic Scan Game subdomain observations on disposable game roots.

use super::{RunnerResult, invalid, text};
use classic_scangame_core::{EnbChecker, IniValidator};
use serde_json::{Value, json};
use std::{
    fs,
    path::{Path, PathBuf},
};

/// Rejects fixture paths that could escape the invocation-owned game root.
fn owned_path(root: &Path, path: &str) -> RunnerResult<PathBuf> {
    if path.is_empty()
        || path.contains([':', '\\'])
        || path.split('/').any(|part| matches!(part, "" | "." | ".."))
    {
        return Err(invalid("scan game needs a contained relative path").into());
    }
    Ok(root.join(path))
}

/// Inventories exact file bytes and directories so read-only checks cannot hide writes.
fn inventory(
    root: &Path,
    directory: &Path,
    files: &mut Vec<Value>,
    directories: &mut Vec<String>,
) -> RunnerResult<()> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let path = entry.path();
        let relative = path
            .strip_prefix(root)?
            .to_string_lossy()
            .replace('\\', "/");
        if entry.file_type()?.is_dir() {
            directories.push(relative);
            inventory(root, &path, files, directories)?;
        } else if entry.file_type()?.is_file() {
            files.push(json!({"path":relative,"content":fs::read_to_string(path)?}));
        } else {
            return Err(invalid("unexpected scan game durable artifact").into());
        }
    }
    Ok(())
}

/// Adds a stable complete filesystem snapshot before or after the native operation.
fn snapshot(root: &Path, observation: &mut Value, before: bool) -> RunnerResult<()> {
    let mut files = Vec::new();
    let mut directories = Vec::new();
    inventory(root, root, &mut files, &mut directories)?;
    files.sort_by(|left, right| left["path"].as_str().cmp(&right["path"].as_str()));
    directories.sort();
    observation[if before { "beforeFiles" } else { "files" }] = json!(files);
    observation[if before {
        "beforeDirectories"
    } else {
        "directories"
    }] = json!(directories);
    Ok(())
}

/// Executes public INI/ENB checks using only explicit fixture files and game selection.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let operation = text(&fixture["operation"])?;
    let game = text(&fixture["game"])?;
    if !matches!(operation.as_str(), "validate-ini" | "validate-enb") {
        return Err(invalid("unsupported scan game operation").into());
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for path in fixture["directories"]
        .as_array()
        .ok_or_else(|| invalid("directories must be an array"))?
    {
        fs::create_dir_all(owned_path(root, &text(path)?)?)?;
    }
    for (path, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be an object"))?
    {
        let target = owned_path(root, path)?;
        fs::create_dir_all(
            target
                .parent()
                .ok_or_else(|| invalid("file needs a parent"))?,
        )?;
        fs::write(target, text(content)?.as_bytes())?;
    }
    let mut observation = json!({"operation":operation,"game":game,"result":null});
    snapshot(root, &mut observation, true)?;
    observation["result"] = if operation == "validate-ini" {
        let mut validator = IniValidator::new(game);
        let report = validator.validate_inis(root)?;
        let config_files = validator.scan_config_files(root)?;
        let issues = validator.detect_all_issues(&config_files).into_iter().map(|issue| {
            Ok(json!({"filePath":issue.file_path.strip_prefix(root)?.to_string_lossy().replace('\\', "/"),
                "section":issue.section,"setting":issue.setting,"currentValue":issue.current_value,
                "recommendedValue":issue.recommended_value,"description":issue.description,
                "severity":format!("{:?}",issue.severity)}))
        }).collect::<RunnerResult<Vec<Value>>>()?;
        // Only ephemeral root spelling is normalized; authored report text remains exact.
        json!({"report":report.replace(&*root.to_string_lossy(), "<ROOT>").replace('\\', "/"),"issues":issues})
    } else {
        let checker = EnbChecker::new(root);
        let result = checker.validate();
        if checker.check_binaries() != result.binaries || checker.check_config() != result.config {
            return Err(invalid("ENB public check methods disagree with validate").into());
        }
        json!({"binaries":format!("{:?}",result.binaries),"config":format!("{:?}",result.config)})
    };
    snapshot(root, &mut observation, false)?;
    Ok(observation)
}
