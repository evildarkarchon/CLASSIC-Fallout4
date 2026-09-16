//! Native typed INI cache and mod scan observations over owned fixture files.

use super::file_operations::{destination, files};
use super::{RunnerResult, invalid, text};
use classic_scangame_core::{config_cache::ConfigFileCache, mod_ini::ModIniScanner};
use serde_json::{Value, json};
use std::{collections::BTreeMap, fs, path::Path};

/// Converts an actual native path to a contained portable fixture path.
fn relative(root: &Path, path: &Path) -> RunnerResult<String> {
    Ok(path
        .strip_prefix(root)?
        .to_string_lossy()
        .replace('\\', "/"))
}

/// Executes public native cache getters or the full mod scanner without mutating inputs.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for (path, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be an object"))?
    {
        let target = destination(root, path)?;
        fs::create_dir_all(
            target
                .parent()
                .ok_or_else(|| invalid("file needs parent"))?,
        )?;
        fs::write(target, text(content)?.as_bytes())?;
    }
    let operation = text(&fixture["operation"])?;
    let mut result = json!({"operation":operation,"before":files(root)?});
    result["result"] = if operation == "cache" {
        let mut cache = ConfigFileCache::new(root, &[])?;
        let mut names = cache.config_files().keys().cloned().collect::<Vec<_>>();
        names.sort();
        let path = cache
            .get_path("sample.ini")
            .map(|path| relative(root, path))
            .transpose()?;
        let mut duplicates = BTreeMap::new();
        for (name, paths) in &cache.duplicate_files {
            let mut paths = paths
                .iter()
                .map(|path| relative(root, path))
                .collect::<RunnerResult<Vec<_>>>()?;
            paths.sort();
            duplicates.insert(name.clone(), paths);
        }
        json!({"names":names,"contains":cache.contains("sample.ini"),"path":path,
            "name":cache.get_str("sample.ini","Settings","name"),"enabled":cache.get_bool("sample.ini","Settings","enabled"),
            "count":cache.get_int("sample.ini","Settings","count"),"scale":cache.get_float("sample.ini","Settings","scale").map(|value|format!("{value:.3}")),
            "hasName":cache.has_setting("sample.ini","Settings","name"),"missing":cache.get_str("absent.ini","Settings","name"),"duplicates":duplicates})
    } else if operation == "duplicates" {
        use classic_scangame_core::ConfigDuplicateDetector;
        let project = |detector: &ConfigDuplicateDetector| -> RunnerResult<Vec<Value>> {
            let mut groups = detector
                .get_duplicates()
                .values()
                .map(|group| {
                    let mut copies = group
                        .duplicates
                        .iter()
                        .map(|path| relative(root, path))
                        .collect::<RunnerResult<Vec<_>>>()?;
                    copies.sort();
                    Ok(json!({"original":relative(root,&group.canonical)?,"duplicates":copies}))
                })
                .collect::<RunnerResult<Vec<_>>>()?;
            groups
                .sort_by(|left, right| left["original"].as_str().cmp(&right["original"].as_str()));
            Ok(groups)
        };
        let mapping = |values: std::collections::HashMap<String, Vec<std::path::PathBuf>>| -> RunnerResult<BTreeMap<String, Vec<String>>>{ values.into_iter().map(|(name, paths)| Ok((name, paths.iter().map(|path| relative(root, path)).collect::<RunnerResult<Vec<_>>>()?))).collect() };
        let mut detector = ConfigDuplicateDetector::new();
        let initial_map = mapping(detector.scan_directory(root)?)?;
        let initial = project(&detector)?;
        let mut excluded =
            ConfigDuplicateDetector::with_whitelist(vec!["no-fixture-matches".into()]);
        if !excluded.scan_directory(root)?.is_empty() {
            return Err(invalid("custom duplicate whitelist ignored").into());
        }
        let replacement = destination(root, &text(&fixture["replacement"]["path"])?)?;
        fs::write(
            replacement,
            text(&fixture["replacement"]["content"])?.as_bytes(),
        )?;
        let after_map = mapping(detector.scan_directory(root)?)?;
        let after = project(&detector)?;
        json!({"initialGroups":initial,"initialMap":initial_map,"afterGroups":after,"afterMap":after_map})
    } else if operation == "scan" {
        let value = ModIniScanner::scan(root, &text(&fixture["game"])?)?;
        let issues = value.issues.iter().map(|issue| Ok(json!({"filePath":relative(root,&issue.file_path)?,"section":issue.section,"setting":issue.setting,"currentValue":issue.current_value,"recommendedValue":issue.recommended_value,"description":issue.description,"severity":format!("{:?}",issue.severity)}))).collect::<RunnerResult<Vec<_>>>()?;
        let vsync = value
            .vsync_files
            .iter()
            .map(|entry| {
                Ok(json!({"path":relative(root,&entry.file_path)?,"setting":entry.setting}))
            })
            .collect::<RunnerResult<Vec<_>>>()?;
        let duplicates = value
            .duplicates
            .iter()
            .map(|entry| {
                let mut paths = entry
                    .paths
                    .iter()
                    .map(|path| relative(root, path))
                    .collect::<RunnerResult<Vec<_>>>()?;
                paths.sort();
                Ok(json!({"name":entry.file_name,"paths":paths}))
            })
            .collect::<RunnerResult<Vec<_>>>()?;
        json!({"message":value.message.replace(&*root.to_string_lossy(),"<ROOT>").replace('\\',"/"),"issues":issues,"vsync":vsync,"duplicates":duplicates})
    } else {
        return Err(invalid("unsupported mod INI operation").into());
    };
    result["files"] = files(root)?;
    Ok(result)
}
