//! Actual public Installed YAML Data observations in a fresh, isolated installation.

use super::{RunnerResult, invalid, text};
use classic_config_core::{
    GameDataRole, InspectedYamlDataFile, InstalledYamlDataDiagnostic,
    InstalledYamlDataInspectionError, InstalledYamlDataInspectionRequest,
    InstalledYamlDataLoadError, InstalledYamlDataLoadOutcome, InstalledYamlDataLoadRequest,
    InstalledYamlDataProvenance, InstalledYamlDataRole, YamlDataContentIdentity,
    inspect_installed_yaml_data_with_env, load_installed_yaml_data_with_env,
};
use classic_shared_core::GameId;
use classic_vocabulary::Vocabulary;
use serde_json::{Value, json};
use std::{
    fs,
    path::{Component, Path, PathBuf},
};

const IGNORE: &str = "installation/CLASSIC Data/CLASSIC Ignore.yaml";

/// Rejects fixture destinations that could escape the operation's temporary state.
fn destination(root: &Path, relative: &str) -> RunnerResult<PathBuf> {
    let path = Path::new(relative);
    if relative.contains('\\')
        || path
            .components()
            .any(|c| !matches!(c, Component::Normal(_)))
        || path.as_os_str().is_empty()
    {
        return Err(invalid("fixture destination must be a contained relative path").into());
    }
    Ok(root.join(path))
}

/// Materializes authored bytes, also used for explicit post-load mutation inputs.
fn write_files(root: &Path, files: &Value) -> RunnerResult<()> {
    for (path, content) in files
        .as_object()
        .ok_or_else(|| invalid("files must be an object"))?
    {
        let path = destination(root, path)?;
        fs::create_dir_all(
            path.parent()
                .ok_or_else(|| invalid("file needs a parent"))?,
        )?;
        fs::write(path, text(content)?.as_bytes())?;
    }
    Ok(())
}

/// Projects retained byte identity independently of the current filesystem contents.
fn identity(path: &str, value: &YamlDataContentIdentity) -> Value {
    json!({"path":path,"sha256":value.sha256_hex(),"byteLength":value.byte_len()})
}

/// Derives the known candidate path from the public selected role and provenance.
fn selected(value: &InspectedYamlDataFile) -> Value {
    let filename = match value.role() {
        InstalledYamlDataRole::Main => "CLASSIC Main.yaml",
        InstalledYamlDataRole::Game => "CLASSIC Fallout4.yaml",
    };
    let path = match value.provenance() {
        InstalledYamlDataProvenance::Updated => format!("cache/CLASSIC/yaml-cache/{filename}"),
        InstalledYamlDataProvenance::Previous => {
            format!("cache/CLASSIC/yaml-cache/{filename}.prev")
        }
        InstalledYamlDataProvenance::Bundled => {
            format!("installation/CLASSIC Data/databases/{filename}")
        }
    };
    json!({"role":value.role().as_str(),"provenance":value.provenance().as_str(),
        "schemaVersion":value.schema_version().to_string(),"identity":identity(&path,value.identity())})
}

/// Normalizes only paths owned by this scenario, refusing external attribution.
fn relative(root: &Path, path: &Path) -> RunnerResult<String> {
    Ok(path
        .strip_prefix(root)?
        .to_string_lossy()
        .replace('\\', "/"))
}

/// Preserves typed diagnostic attribution and ordering without platform error prose.
fn diagnostics(root: &Path, values: &[InstalledYamlDataDiagnostic]) -> RunnerResult<Value> {
    Ok(Value::Array(
        values
            .iter()
            .map(|value| {
                Ok(json!({"role":value.role().map(Vocabulary::as_str),
            "candidate":value.candidate().map(Vocabulary::as_str),
            "path":value.path().map(|path| relative(root,path)).transpose()?,
            "kind":value.kind().as_str()}))
            })
            .collect::<RunnerResult<Vec<_>>>()?,
    ))
}

/// Enumerates every durable file, including unexpected publication leftovers.
fn files(root: &Path, directory: &Path, output: &mut Vec<Value>) -> RunnerResult<()> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            files(root, &entry.path(), output)?;
        } else if entry.file_type()?.is_file() {
            output.push(identity(
                &relative(root, &entry.path())?,
                &YamlDataContentIdentity::from_bytes(&fs::read(entry.path())?),
            ));
        } else {
            return Err(invalid("unexpected non-file durable artifact").into());
        }
    }
    Ok(())
}

/// Keeps all union arms explicit so stale values cannot leak between scenarios.
fn empty() -> Value {
    json!({"outcome":"error","game":null,"gameDataRole":null,"main":null,
        "gameFile":null,"localIgnore":null,"recovery":null,"snapshot":null,
        "diagnostics":[],"error":null,"files":[]})
}

/// Projects the registered role exhaustively instead of copying the fixture game.
fn game_role(role: GameDataRole) -> &'static str {
    match role {
        GameDataRole::Fallout4 => "Fallout4",
    }
}

/// Records common selection facts from the retained public operation result.
fn selection(
    value: &mut Value,
    game: GameId,
    role: GameDataRole,
    main: &InspectedYamlDataFile,
    game_file: &InspectedYamlDataFile,
) {
    value["game"] = json!(game.as_str());
    value["gameDataRole"] = json!(game_role(role));
    value["main"] = selected(main);
    value["gameFile"] = selected(game_file);
}

/// Converts only typed public inspection failures; transport failures abort execution.
fn inspection_error(
    root: &Path,
    error: InstalledYamlDataInspectionError,
    value: &mut Value,
) -> RunnerResult<()> {
    match error {
        InstalledYamlDataInspectionError::UnsupportedGame { .. } => {
            value["error"] = json!({"code":"unsupported_game","role":null});
        }
        InstalledYamlDataInspectionError::NoUsableSource {
            role,
            diagnostics: details,
        } => {
            value["error"] = json!({"code":"no_usable_source","role":role.as_str()});
            value["diagnostics"] = diagnostics(root, &details)?;
        }
    }
    Ok(())
}

/// Executes inspection or load, mutating files only after a public handle exists.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    write_files(root, &fixture["files"])?;
    let game = text(&fixture["game"])?.parse::<GameId>()?;
    let cache = root.join("cache").to_string_lossy().into_owned();
    // The injected environment is a public cache-resolution seam; it cannot read
    // ambient installation data or mutate process-global environment in Rust tests.
    let env = |name: &str| match name {
        "LOCALAPPDATA" | "XDG_CACHE_HOME" => Some(cache.clone()),
        _ => None,
    };
    let mut value = empty();
    match text(&fixture["operation"])?.as_str() {
        "inspect" => {
            let outcome = inspect_installed_yaml_data_with_env(
                InstalledYamlDataInspectionRequest {
                    installation_root: root.join("installation"),
                    game,
                },
                env,
            );
            if let Some(mutations) = fixture.get("mutations") {
                write_files(root, mutations)?;
            }
            match outcome {
                Ok(result) => {
                    value["outcome"] = json!("inspected");
                    selection(
                        &mut value,
                        result.game(),
                        result.game_data_role(),
                        result.main(),
                        result.game_file(),
                    );
                    value["diagnostics"] = diagnostics(root, result.diagnostics())?;
                }
                Err(error) => inspection_error(root, error, &mut value)?,
            }
        }
        "load" => {
            let outcome = load_installed_yaml_data_with_env(
                InstalledYamlDataLoadRequest {
                    installation_root: root.join("installation"),
                    game,
                    selected_game_version: text(&fixture["selectedGameVersion"])?,
                },
                env,
            );
            if let Some(mutations) = fixture.get("mutations") {
                write_files(root, mutations)?;
            }
            match outcome {
                Ok(InstalledYamlDataLoadOutcome::Ready(result)) => {
                    value["outcome"] = json!("ready");
                    selection(
                        &mut value,
                        result.game(),
                        result.game_data_role(),
                        result.main(),
                        result.game_file(),
                    );
                    value["diagnostics"] = diagnostics(root, result.diagnostics())?;
                    value["localIgnore"] = json!({"state":result.local_ignore_state().as_str(),
                        "identity":identity(IGNORE,result.local_ignore_identity())});
                    value["snapshot"] = json!({"classicVersion":result.yaml_data().classic_version,
                        "gameRootName":result.yaml_data().game_root_name,
                        "ignoreList":result.yaml_data().ignore_list,
                        "simplifyRemoveList":result.simplify_remove_list()});
                }
                Ok(InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(result)) => {
                    value["outcome"] = json!("recovery_required");
                    selection(
                        &mut value,
                        result.game(),
                        result.game_data_role(),
                        result.main(),
                        result.game_file(),
                    );
                    value["diagnostics"] = diagnostics(root, result.diagnostics())?;
                    let path = relative(root, result.local_ignore_path())?;
                    value["recovery"] = json!({"localIgnorePath":path,
                        "malformedIdentity":identity(&path,result.malformed_local_ignore_identity()),
                        "defaultIdentity":result.default_local_ignore_identity().map(|v|identity(&path,v)),
                        "selectedGameVersion":result.selected_game_version()});
                }
                Err(InstalledYamlDataLoadError::UnsupportedGame { game }) => {
                    inspection_error(
                        root,
                        InstalledYamlDataInspectionError::UnsupportedGame { game },
                        &mut value,
                    )?;
                }
                Err(InstalledYamlDataLoadError::NoUsableSource { role, diagnostics }) => {
                    inspection_error(
                        root,
                        InstalledYamlDataInspectionError::NoUsableSource { role, diagnostics },
                        &mut value,
                    )?;
                }
                Err(InstalledYamlDataLoadError::LocalIgnoreDefaultInvalid { .. }) => {
                    value["error"] = json!({"code":"local_ignore_default_invalid","role":null});
                }
                Err(error) => return Err(error.into()),
            }
        }
        _ => return Err(invalid("unsupported installed YAML operation").into()),
    }
    let mut durable_files = Vec::new();
    files(root, root, &mut durable_files)?;
    durable_files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    value["files"] = json!(durable_files);
    Ok(value)
}
