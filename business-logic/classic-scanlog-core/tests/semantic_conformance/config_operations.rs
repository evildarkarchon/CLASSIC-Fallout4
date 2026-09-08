//! Observe caller-selected configuration files through the public Rust loader.

use super::{RunnerResult, invalid, text};
use classic_config_core::{
    ExplicitYamlDataLoadError, ExplicitYamlDataRequest, ExplicitYamlDataRole,
    load_explicit_yaml_data,
};
use classic_shared_core::{GameId, get_runtime};
use serde_json::{Value, json};
use std::{fs, path::Path};

#[path = "config_yaml_values.rs"]
mod yaml_values;

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
    if (fixture["operation"] != "load-explicit"
        && fixture["operation"] != "main-version"
        && fixture["operation"] != "clear-cache"
        && fixture["operation"] != "persist-local")
        || fixture.as_object().is_none_or(|value| {
            value.len()
                != if fixture["operation"] == "persist-local" {
                    4
                } else {
                    2
                }
        })
    {
        return Err(invalid("unsupported config operation fixture").into());
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for (name, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be an object"))?
    {
        if !matches!(
            name.as_str(),
            "main.yaml"
                | "game.yaml"
                | "ignore.yaml"
                | "CLASSIC Main.yaml"
                | "local.yaml"
                | "CLASSIC Settings.yaml"
        ) {
            return Err(invalid("config fixture requires owned YAML filenames").into());
        }
        fs::write(root.join(name), text(content)?)?;
    }
    if fixture["operation"] == "clear-cache" {
        classic_settings_core::clear_global_yaml_cache();
        classic_settings_core::clear_global_yaml_cache();
        return Ok(json!({"result": [null, null], "error": null, "files": inventory(root, root)?}));
    }
    if fixture["operation"] == "persist-local" {
        get_runtime().block_on(classic_config_core::persist_game_local_paths(
            &root.join("local.yaml"),
            fixture["gameRoot"].as_str().map(Path::new),
            fixture["docsRoot"].as_str().map(Path::new),
        ))?;
        return Ok(json!({"result": null, "error": null, "files": inventory(root, root)?}));
    }
    if fixture["operation"] == "main-version" {
        // The core's injected resolver avoids mutating global process environment.
        let version = get_runtime().block_on(
            classic_config_core::load_main_yaml_version_with_env(Some(root), |_| None),
        )?;
        return Ok(
            json!({"result": {"version": version}, "error": null, "files": inventory(root, root)?}),
        );
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
            if snapshot.game() != GameId::Fallout4 {
                return Err(invalid("explicit snapshot returned an unexpected game").into());
            }
            let data = snapshot.yaml_data();
            if snapshot.game_data_role() != classic_config_core::GameDataRole::Fallout4 {
                return Err(invalid("explicit snapshot returned an unexpected game role").into());
            }
            let identity = |value: &classic_config_core::YamlDataContentIdentity| json!({"sha256": value.sha256_hex(), "byteLen": value.byte_len()});
            (
                json!({"game": "Fallout4", "gameRole": "Fallout4", "yamlValues": yaml_values::observe(data), "identities": {"main.yaml": identity(snapshot.main_identity()), "game.yaml": identity(snapshot.game_identity()), "ignore.yaml": identity(snapshot.ignore_identity())}, "classicVersion": data.classic_version, "xseAcronym": data.xse_acronym, "crashgenName": data.crashgen_name, "gameVersion": data.game_version, "ignoreList": data.ignore_list}),
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
