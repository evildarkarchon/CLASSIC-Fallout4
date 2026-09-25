//! Read-only setup intake with explicit path facts and primitive normalization.
use super::{RunnerResult, invalid, text};
use classic_scangame_core::{
    GameSetupIntake, GameSetupIntakeResult, game_setup_needs_path_detection,
    normalize_game_setup_version_selection,
};
use classic_shared_core::GameId;
use classic_user_settings_core::UserSettings;
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    fs,
    path::{Component, Path},
};

/// Inventory all files and directories under this scenario's exclusively owned root.
fn tree(
    root: &Path,
    directory: &Path,
    out: &mut BTreeMap<String, Option<Vec<u8>>>,
) -> RunnerResult<()> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let path = entry.path();
        if entry.file_type()?.is_symlink() {
            return Err(invalid("unexpected setup link").into());
        }
        let key = path
            .strip_prefix(root)?
            .to_string_lossy()
            .replace('\\', "/");
        if path.is_dir() {
            out.insert(key, None);
            tree(root, &path, out)?;
        } else {
            out.insert(key, Some(fs::read(path)?));
        }
    }
    Ok(())
}

/// Project stable public summaries without reproducing any path-resolution policy.
fn project(root: &Path, result: &GameSetupIntakeResult) -> RunnerResult<Value> {
    let relative = |path: Option<&Path>| -> RunnerResult<String> {
        Ok(path
            .ok_or_else(|| invalid("missing explicit setup path"))?
            .strip_prefix(root)?
            .to_string_lossy()
            .replace('\\', "/"))
    };
    let report = &result.rendered_report;
    if report != &result.render_report() {
        return Err(invalid("rendered setup report differs").into());
    }
    Ok(
        json!({"status":result.status.as_str(),"hasErrors":result.has_errors(),"totalChecks":result.total_checks(),"failedChecks":result.failed_checks(),"actionCount":result.actions.len(),"pathUpdateCount":result.path_updates.len(),"pathUpdates":result.path_updates.iter().map(|update|Ok(json!({"kind":update.kind,"path":relative(Some(&update.path))?}))).collect::<RunnerResult<Vec<_>>>()?,"gameRoot":relative(result.paths.game_root.as_deref())?,"docsRoot":relative(result.paths.docs_root.as_deref())?,"gameExecutable":relative(result.paths.game_exe_path.as_deref())?,"reportFlags":{"gameNamed":report.contains("Game Setup Intake: Starfield"),"metadataUnsupported":report.contains("[unsupported] registry_metadata:"),"versionWarning":report.contains("[warning] executable_version:"),"documentsPassed":report.contains("[passed] documents_folder:"),"loaderFailed":report.contains("[failed] xse_loader:")}}),
    )
}

/// Execute explicit and settings-backed intake against the same supplied paths.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    if fixture["operation"] == "normalize" {
        let versions = fixture["versions"]
            .as_array()
            .ok_or_else(|| invalid("versions must be array"))?
            .iter()
            .map(|v| normalize_game_setup_version_selection(v.as_str().unwrap_or("")))
            .collect::<Vec<_>>();
        let needs = fixture["paths"]
            .as_array()
            .ok_or_else(|| invalid("paths must be array"))?
            .iter()
            .map(|v| {
                let (game, docs) = game_setup_needs_path_detection(v[0].as_str(), v[1].as_str());
                json!([game, docs])
            })
            .collect::<Vec<_>>();
        return Ok(json!({"versions":versions,"needs":needs}));
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for (name, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be object"))?
    {
        if name.contains('\\')
            || Path::new(name)
                .components()
                .any(|part| !matches!(part, Component::Normal(_)))
        {
            return Err(invalid("setup fixture escaped root").into());
        }
        let path = root.join(name);
        fs::create_dir_all(path.parent().ok_or_else(|| invalid("missing parent"))?)?;
        fs::write(
            path,
            text(content)?.replace("<ROOT>", &root.to_string_lossy().replace('\\', "/")),
        )?;
    }
    let mut before = BTreeMap::new();
    tree(root, root, &mut before)?;
    let direct = GameSetupIntake::new(GameId::Starfield, "Original")
        .with_game_root(root.join("Game"))
        .with_docs_root(root.join("Docs"))
        .with_game_exe_path(root.join("Game/Starfield.exe"));
    let direct = project(root, &direct.run())?;
    let settings = UserSettings::open(root);
    let mut result = project(
        root,
        &GameSetupIntake::from_user_settings(settings.game_setup_settings()).run(),
    )?;
    if result != direct {
        return Err(invalid("equivalent setup facts differ").into());
    }
    let mut after = BTreeMap::new();
    tree(root, root, &mut after)?;
    result["files"] = json!(
        after
            .iter()
            .filter_map(|(path, bytes)| bytes.as_ref().map(|_| path))
            .collect::<Vec<_>>()
    );
    result["unchanged"] = json!(before == after);
    Ok(result)
}
