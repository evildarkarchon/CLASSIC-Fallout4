//! Public concurrent game/mod orchestration and complete-pipeline equivalence.
use super::{RunnerResult, invalid, text};
use classic_file_io_core::dds::GameTarget;
use classic_scangame_core::{
    orchestrator::{GameScanConfig, GameScanOrchestrator, GameScanResult, ModScanResult},
    xse::GameVersion,
};
use classic_shared_core::get_runtime;
use serde_json::{Value, json};
use std::{collections::HashMap, fs};

/// Authenticate native report assembly before sorting scheduler-dependent job completion order.
fn game_result(result: &GameScanResult) -> Value {
    let assembled = result
        .check_results
        .iter()
        .map(|row| row.output.as_str())
        .collect::<Vec<_>>()
        .join("");
    let mut checks = result
        .check_results
        .iter()
        .map(|row| json!({"name":row.name,"output":row.output}))
        .collect::<Vec<_>>();
    checks.sort_by(|a, b| a["name"].as_str().cmp(&b["name"].as_str()));
    let mut errors = result.errors.clone();
    errors.sort();
    json!({"checkResults":checks,"reportMatchesChecks":result.report==assembled,"configIssueCount":result.config_issues.len(),"errors":errors})
}

/// Retain every public mod scan summary field and its nonfatal errors.
fn mod_result(result: &ModScanResult) -> Value {
    let mut errors = result.errors.clone();
    errors.sort();
    json!({"report":result.report,"unpackedIssueCount":result.unpacked_issue_count,"archivedIssueCount":result.archived_issue_count,"errors":errors})
}

/// Execute individual stages and the native full pipeline over the same isolated state.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for (name, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be object"))?
    {
        if name != "sentinel.txt" {
            return Err(invalid("unsupported orchestration fixture path").into());
        }
        fs::write(root.join(name), text(content)?)?;
    }
    let config = GameScanConfig {
        game_path: root.to_path_buf(),
        docs_path: None,
        mods_path: None,
        xse_acronym: text(&fixture["xseAcronym"])?,
        xse_scriptfiles: HashMap::new(),
        plugins_path: None,
        is_vr: false,
        game_version: GameVersion::Original,
        crashgen_name: text(&fixture["crashgenName"])?,
        crashgen_settings_rules: None,
        wrye_warnings: HashMap::new(),
        log_catch_errors: vec!["error".into()],
        log_exclude_files: Vec::new(),
        log_exclude_errors: Vec::new(),
        game_target: GameTarget::Fallout4,
        game_name: text(&fixture["gameName"])?,
    };
    let orchestrator = GameScanOrchestrator::new(config);
    let game = game_result(&get_runtime().block_on(orchestrator.run_game_checks())?);
    let mods = mod_result(&get_runtime().block_on(orchestrator.run_mod_scans())?);
    let (full_game, full_mods) = get_runtime().block_on(orchestrator.run_full_scan())?;
    if game_result(&full_game) != game || mod_result(&full_mods) != mods {
        return Err(invalid("full scan lost native component results").into());
    }
    let mut files = Vec::new();
    for entry in fs::read_dir(root)? {
        let entry = entry?;
        files.push(json!({"path":entry.file_name().to_string_lossy(),"content":fs::read_to_string(entry.path())?}));
    }
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    Ok(json!({"game":game,"mods":mods,"files":files}))
}
