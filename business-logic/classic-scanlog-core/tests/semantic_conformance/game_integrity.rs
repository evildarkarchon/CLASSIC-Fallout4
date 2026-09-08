//! Independent public integrity results over controlled executable bytes.
use super::{RunnerResult, invalid, text};
use classic_scangame_core::integrity::{
    CheckType, GameIntegrityChecker, IntegrityCheckResult, IntegrityConfig,
};
use serde_json::{Value, json};
use std::{
    fs,
    path::{Component, Path},
};

/// Project public check type and fields without interpreting diagnostic prose.
fn project(result: &IntegrityCheckResult) -> Value {
    json!({"isValid":result.is_valid,"message":result.message,"checkType":match result.check_type {CheckType::ExecutableVersion=>"ExecutableVersion",CheckType::InstallationLocation=>"InstallationLocation"}})
}

/// Execute individual and grouped checks against isolated authored files.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
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
            return Err(invalid("integrity fixture escaped root").into());
        }
        let path = root.join(name);
        fs::create_dir_all(
            path.parent()
                .ok_or_else(|| invalid("file parent missing"))?,
        )?;
        fs::write(path, text(content)?)?;
    }
    let hashes = fixture["hashes"]
        .as_array()
        .ok_or_else(|| invalid("hashes must be array"))?
        .iter()
        .map(text)
        .collect::<Result<Vec<_>, _>>()?;
    let mut config = IntegrityConfig::new(
        root.join(text(&fixture["exe"])?),
        hashes,
        text(&fixture["rootName"])?,
    );
    if let Some(path) = fixture["steamIni"].as_str() {
        config = config.with_steam_ini(root.join(path));
    }
    if let Some(warn) = fixture["rootWarn"].as_str() {
        config = config.with_root_warn(warn.to_string());
    }
    let checker = GameIntegrityChecker::new(config);
    let results = checker.run_all_checks()?;
    if results
        != vec![
            checker.check_executable_version()?,
            checker.check_installation_location()?,
        ]
    {
        return Err(invalid("grouped integrity checks differ").into());
    }
    let mut files = Vec::new();
    /// Capture final owned bytes and reject unexpected link entries.
    fn visit(root: &Path, directory: &Path, files: &mut Vec<Value>) -> RunnerResult<()> {
        for entry in fs::read_dir(directory)? {
            let entry = entry?;
            if entry.file_type()?.is_symlink() {
                return Err(invalid("unexpected integrity symlink").into());
            }
            let path = entry.path();
            if path.is_dir() {
                visit(root, &path, files)?;
            } else {
                files.push(json!({"path":path.strip_prefix(root)?.to_string_lossy().replace('\\',"/"),"content":fs::read_to_string(path)?}));
            }
        }
        Ok(())
    }
    visit(root, root, &mut files)?;
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    Ok(
        json!({"checks":results.iter().map(project).collect::<Vec<_>>(),"report":checker.run_full_check()?,"files":files}),
    )
}
