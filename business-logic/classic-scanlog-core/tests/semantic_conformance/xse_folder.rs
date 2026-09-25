//! Observe public folder precedence against owned YAML and registry metadata.
use super::{RunnerResult, invalid, text};
use serde_json::{Value, json};
use std::{env, fs, path::Path};

/// Resolve a folder in a dedicated serial process with test-owned registry bytes.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    fs::write(
        root.join("CLASSIC Main.yaml"),
        text(&fixture["registryYaml"])?,
    )?;
    let game = text(&fixture["game"])?;
    if !matches!(game.as_str(), "Fallout4" | "Fallout4VR" | "Unknown") {
        return Err(invalid("unsupported XSE folder game").into());
    }
    if !fixture["localYaml"].is_null() {
        fs::write(
            root.join(format!("CLASSIC {game} Local.yaml")),
            text(&fixture["localYaml"])?,
        )?;
    }
    let previous = env::current_dir()?;
    env::set_current_dir(root)?;
    // Initialize the singleton in this owned directory before any resolver call.
    let _ = classic_version_registry_core::get_version_registry();
    env::set_current_dir(previous)?;
    let configured = text(&fixture["configuredDocs"])?;
    let folder = classic_xse_core::resolve_xse_folder_for_scan(
        root,
        &game,
        &text(&fixture["selectedVersion"])?,
        if configured.is_empty() {
            None
        } else {
            Some(Path::new(&configured))
        },
    );
    let mut files = Vec::new();
    for entry in fs::read_dir(root)? {
        let entry = entry?;
        files.push(json!({"path": entry.file_name().to_string_lossy(), "content": fs::read_to_string(entry.path())?}));
    }
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    Ok(json!({"folder": folder.map(|p| p.to_string_lossy().replace('\\', "/")), "files": files}))
}
