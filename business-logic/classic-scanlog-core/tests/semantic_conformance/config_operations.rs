//! Observe caller-selected configuration files through the public Rust loader.

use super::{RunnerResult, invalid, text};
use classic_config_core::{
    ExplicitYamlDataLoadError, ExplicitYamlDataRequest, ExplicitYamlDataRole,
    load_explicit_yaml_data,
};
use classic_shared_core::{GameId, get_runtime};
use serde_json::{Value, json};
use std::{fs, path::Path};

/// Re-read all durable bytes after execution; the loader's read-only contract is observable.
fn inventory(root: &Path, directory: &Path) -> RunnerResult<Vec<Value>> {
    let mut files = Vec::new();
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let path = entry.path();
        if entry.file_type()?.is_symlink() {
            return Err(invalid("unexpected link in config workspace").into());
        }
        if path.is_dir() {
            files.extend(inventory(root, &path)?);
        } else {
            files.push(json!({"path": path.strip_prefix(root)?.to_string_lossy().replace('\\', "/"), "content": fs::read_to_string(path)?}));
        }
    }
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    Ok(files)
}

/// Execute one input-only fixture with disposable files and typed failure attribution.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    if fixture["operation"] != "load-explicit"
        || fixture.as_object().is_none_or(|value| value.len() != 2)
    {
        return Err(invalid("unsupported config operation fixture").into());
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for (name, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be an object"))?
    {
        if !matches!(name.as_str(), "main.yaml" | "game.yaml" | "ignore.yaml") {
            return Err(invalid("config fixture requires owned YAML filenames").into());
        }
        fs::write(root.join(name), text(content)?)?;
    }
    let loaded = get_runtime().block_on(load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path: root.join("main.yaml"),
        game_path: root.join("game.yaml"),
        ignore_path: root.join("ignore.yaml"),
        game: GameId::Fallout4,
        selected_game_version: "auto".into(),
    }));
    let (result, error) = match loaded {
        Ok(snapshot) => {
            let data = snapshot.yaml_data();
            (
                json!({"classicVersion": data.classic_version, "xseAcronym": data.xse_acronym, "crashgenName": data.crashgen_name, "gameVersion": data.game_version, "ignoreList": data.ignore_list}),
                Value::Null,
            )
        }
        Err(error) => {
            let (code, role, path) = match error {
                ExplicitYamlDataLoadError::Read { role, path, .. } => ("read", role, path),
                ExplicitYamlDataLoadError::Parse { role, path, .. } => ("parse", role, path),
                ExplicitYamlDataLoadError::InvalidUtf8 { role, path, .. } => {
                    ("invalid_utf8", role, path)
                }
                ExplicitYamlDataLoadError::InvalidRoleData { role, path, .. } => {
                    ("invalid_role_data", role, path)
                }
                other => return Err(other.into()),
            };
            let role = match role {
                ExplicitYamlDataRole::Main => "main",
                ExplicitYamlDataRole::Game => "game",
                ExplicitYamlDataRole::LocalIgnore => "local_ignore",
            };
            (
                Value::Null,
                json!({"code": code, "role": role, "path": path.strip_prefix(root)?.to_string_lossy().replace('\\', "/")}),
            )
        }
    };
    Ok(json!({"result": result, "error": error, "files": inventory(root, root)?}))
}
