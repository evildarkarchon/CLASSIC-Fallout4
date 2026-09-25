//! Address Library metadata and actual plugin-file validation.

use super::{RunnerResult, invalid, text};
use classic_scangame_core::{AddressLibInfo, GameVersion, XseChecker};
use serde_json::{Value, json};
use std::{fs, path::PathBuf};

struct DirectoryGuard(PathBuf);
impl Drop for DirectoryGuard {
    fn drop(&mut self) {
        // Destructors cannot report restoration errors; the adapter process owns
        // this temporary cwd and exits immediately after its receipt run.
        let _ = std::env::set_current_dir(&self.0);
    }
}

/// Use embedded registry fallback in an owned directory and retain all read-only effects.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for (name, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files missing"))?
    {
        fs::write(root.join(name), text(content)?)?;
    }
    let _guard = DirectoryGuard(std::env::current_dir()?);
    std::env::set_current_dir(root)?;
    let (version, info) = match text(&fixture["version"])?.as_str() {
        "Original" => (GameVersion::Original, AddressLibInfo::original()),
        "NextGen" => (GameVersion::NextGen, AddressLibInfo::next_gen()),
        "Vr" => (GameVersion::Vr, AddressLibInfo::vr()),
        _ => return Err(invalid("unsupported game version").into()),
    };
    let inventory = || -> RunnerResult<serde_json::Map<String, Value>> {
        fs::read_dir(root)?
            .map(|entry| {
                let entry = entry?;
                Ok((
                    entry.file_name().to_string_lossy().into_owned(),
                    json!(fs::read_to_string(entry.path())?),
                ))
            })
            .collect()
    };
    let before = inventory()?;
    let checker = XseChecker::new(root, version)?;
    Ok(
        json!({"info":{"version":format!("{:?}",info.version),"filename":info.filename,"description":info.description,"url":info.url},"result":format!("{:?}",checker.check()),"message":checker.validate(),"beforeFiles":before,"files":inventory()?}),
    )
}
