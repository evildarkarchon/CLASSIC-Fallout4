//! Observe public folder precedence against owned YAML and registry metadata.
//!
//! `xse-folder.derive` exercises XSE's own derivation from supplied Game Local
//! facts (`classic_xse_core::resolve_xse_folder_from_game_local_facts`), and
//! `xse-folder.resolve` exercises scangame's composition that first reads
//! those facts from the Game Local document.
use super::{RunnerResult, invalid, optional, text};
use serde_json::{Value, json};
use std::{env, fs, path::Path, path::PathBuf};

/// Resolve a folder in a dedicated serial process with test-owned registry bytes.
///
/// `action` is the scenario's trusted action; it must agree with the fixture's
/// fact source (Game Local facts for derivation, Local.yaml for composition).
pub(super) fn execute(action: &str, fixture: &Value) -> RunnerResult<Value> {
    if action == "xse-folder.log" {
        return execute_log(fixture);
    }
    let derive = match action {
        "xse-folder.derive" => true,
        "xse-folder.resolve" => false,
        _ => return Err(invalid("unsupported XSE folder action").into()),
    };
    if derive != fixture.get("gameLocalFacts").is_some()
        || derive == fixture.get("localYaml").is_some()
    {
        return Err(invalid("XSE folder action does not match fixture facts").into());
    }
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
    if !derive && !fixture["localYaml"].is_null() {
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
    let configured = if configured.is_empty() {
        None
    } else {
        Some(Path::new(&configured))
    };
    let selected_version = text(&fixture["selectedVersion"])?;
    let folder = if derive {
        let facts = &fixture["gameLocalFacts"];
        let game_local = classic_xse_core::XseGameLocalFacts {
            docs_folder_xse: optional(&facts["docsFolderXse"])?.map(PathBuf::from),
            root_folder_docs: optional(&facts["rootFolderDocs"])?.map(PathBuf::from),
        };
        classic_xse_core::resolve_xse_folder_from_game_local_facts(
            &game_local,
            &game,
            &selected_version,
            configured,
        )
    } else {
        classic_scangame_core::resolve_xse_folder_for_scan(
            root,
            &game,
            &selected_version,
            configured,
        )
    };
    let mut files = Vec::new();
    for entry in fs::read_dir(root)? {
        let entry = entry?;
        files.push(json!({"path": entry.file_name().to_string_lossy(), "content": fs::read_to_string(entry.path())?}));
    }
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    Ok(json!({"folder": folder.map(|p| p.to_string_lossy().replace('\\', "/")), "files": files}))
}

/// The only log files a log fixture may create; the central validator freezes the same set.
const CONTROLLED_LOG_FILES: [&str; 4] = [
    "configured-docs/F4SE/f4se.log",
    "configured-docs/F4SE/f4sevr.log",
    "local-docs/F4SE/f4se.log",
    "explicit-xse/f4se.log",
];

/// Locate the XSE log (`xse-folder.log`) against owned registry, Local.yaml and logs.
///
/// The resolver runs with the owned root as cwd so the relative fixture
/// folders resolve inside it; the returned log stays root-relative. Only the
/// typed operational failure becomes an `error` observation.
fn execute_log(fixture: &Value) -> RunnerResult<Value> {
    let game = text(&fixture["game"])?;
    if !matches!(game.as_str(), "Fallout4" | "Fallout4VR") {
        return Err(invalid("unsupported XSE log game").into());
    }
    let log_files = fixture["logFiles"]
        .as_array()
        .ok_or_else(|| invalid("XSE log fixture needs logFiles"))?;
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    fs::write(
        root.join("CLASSIC Main.yaml"),
        text(&fixture["registryYaml"])?,
    )?;
    if !fixture["localYaml"].is_null() {
        fs::write(
            root.join(format!("CLASSIC {game} Local.yaml")),
            text(&fixture["localYaml"])?,
        )?;
    }
    for file in log_files {
        let relative = text(file)?;
        if !CONTROLLED_LOG_FILES.contains(&relative.as_str()) {
            return Err(invalid("uncontrolled XSE log file").into());
        }
        let path = root.join(&relative);
        fs::create_dir_all(path.parent().ok_or_else(|| invalid("log has no parent"))?)?;
        fs::write(path, b"")?;
    }
    let configured = text(&fixture["configuredDocs"])?;
    let selected_version = text(&fixture["selectedVersion"])?;
    let previous = env::current_dir()?;
    env::set_current_dir(root)?;
    // Initialize the singleton in this owned directory before any resolver call.
    let _ = classic_version_registry_core::get_version_registry();
    let located = classic_scangame_core::resolve_xse_log_for_scan(
        root,
        &game,
        &selected_version,
        (!configured.is_empty()).then(|| Path::new(&configured)),
    );
    env::set_current_dir(previous)?;
    Ok(match located {
        Ok(log) => {
            json!({"log": log.map(|p| p.to_string_lossy().replace('\\', "/")), "error": null})
        }
        Err(classic_scangame_core::XseLogError::Inspect { .. }) => {
            json!({"log": null, "error": "inspect"})
        }
    })
}
