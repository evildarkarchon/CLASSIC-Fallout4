//! Execute checker and orchestrator independently against preserved input-only files.

use super::{RunnerResult, invalid};
use classic_scangame_core::crashgen_orchestrator::CrashgenCheckOrchestrator;
use classic_scangame_core::{CrashgenChecker, TomlConfigIssue};
use serde_json::{Value, json};
use std::path::Path;

/// Project every native issue field; paths are relative to the invocation-owned tree.
fn issues(values: &[TomlConfigIssue], root: &Path) -> RunnerResult<Value> {
    Ok(json!(values.iter().map(|value| Ok(json!({"path":value.file_path.strip_prefix(root)?.to_string_lossy().replace('\\',"/"),"section":value.section,"setting":value.setting,"current":value.current_value,"recommended":value.recommended_value,"description":value.description,"severity":format!("{:?}",value.severity)}))).collect::<RunnerResult<Vec<_>>>()?))
}

/// Compare separate public checks and metadata getters before emitting native observations.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for (path, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be object"))?
    {
        let target = super::file_operations::destination(root, path)?;
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(
            target,
            content
                .as_str()
                .ok_or_else(|| invalid("content must be string"))?,
        )?;
    }
    let before = super::file_operations::files(root)?;
    let mut checker = CrashgenChecker::new(root, "Buffout4");
    let (message, values) = checker.check()?;
    let projected = issues(&values, root)?;
    let report = CrashgenCheckOrchestrator::check(root, "Buffout4")?;
    let resolved = CrashgenCheckOrchestrator::resolve_config_path(root);
    let mut plugins = report.installed_plugins.clone();
    plugins.sort();
    let mut detected = CrashgenCheckOrchestrator::detect_plugins(root)?;
    detected.sort();
    if report.message != message
        || issues(&report.issues, root)? != projected
        || report.config_path != resolved
        || plugins != detected
        || checker.config_file() != resolved.as_ref()
    {
        return Err(invalid("Crashgen public aliases disagree").into());
    }
    let mut checker_plugins = checker.installed_plugins().to_vec();
    checker_plugins.sort();
    if checker_plugins != plugins {
        return Err(invalid("checker plugin metadata disagrees").into());
    }
    let config = resolved
        .as_ref()
        .map(|path| {
            path.strip_prefix(root)
                .map(|path| path.to_string_lossy().replace('\\', "/"))
        })
        .transpose()?;
    Ok(
        json!({"message":message,"issues":projected,"name":report.crashgen_name,"config":config,"plugins":plugins,"beforeFiles":before,"files":super::file_operations::files(root)?}),
    )
}
