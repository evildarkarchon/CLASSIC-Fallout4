//! Observe fixture-seeded Version Registry metadata through the public core API.

use super::{RunnerResult, invalid, text};
use classic_version_registry_core::{GameVersion, VersionRegistryError, get_version_registry};
use serde_json::{Value, json};
use std::{env, fs};

/// Execute against an owned YAML registry; the family runs serially in its own process.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    if fixture.as_object().is_none_or(|object| object.len() != 3) {
        return Err(invalid("unsupported version registry fixture").into());
    }
    let operation = text(&fixture["operation"])?;
    if !matches!(
        operation.as_str(),
        "lookup" | "match" | "enumerate" | "crashgen" | "xse" | "details" | "values"
    ) {
        return Err(invalid("unsupported version registry operation").into());
    }
    let temporary = tempfile::tempdir()?;
    fs::write(
        temporary.path().join("CLASSIC Main.yaml"),
        text(&fixture["registryYaml"])?,
    )?;
    let previous = env::current_dir()?;
    env::set_current_dir(temporary.path())?;
    // The singleton loads only on first use. Every family fixture carries identical
    // bytes, and the dedicated participant process prevents unrelated initialization.
    let registry = get_version_registry();
    env::set_current_dir(previous)?;
    let mut observation = observe(&operation, &fixture["request"], registry)?;
    let mut files = Vec::new();
    for entry in fs::read_dir(temporary.path())? {
        let entry = entry?;
        if !entry.file_type()?.is_file() {
            return Err(invalid("unexpected non-file in version registry workspace").into());
        }
        files.push(json!({"path": entry.file_name().to_string_lossy(), "content": fs::read_to_string(entry.path())?}));
    }
    files.sort_by(|left, right| left["path"].as_str().cmp(&right["path"].as_str()));
    observation["files"] = json!(files);
    Ok(observation)
}

/// Convert public registry values and typed parse errors into the shared envelope.
fn observe(
    operation: &str,
    request: &Value,
    registry: &classic_version_registry_core::VersionRegistry,
) -> RunnerResult<Value> {
    if operation == "details" {
        return details(request, registry);
    }
    if operation == "values" {
        return values(request, registry);
    }
    if operation == "enumerate" {
        let mut ids: Vec<_> = registry
            .get_all()
            .iter()
            .map(|info| info.id.clone())
            .collect();
        ids.sort();
        let mut filtered: Vec<_> = registry
            .get_all_for_game(&text(&request["game"])?, request["isVr"].as_bool())
            .iter()
            .map(|info| info.id.clone())
            .collect();
        filtered.sort();
        return Ok(
            json!({"result": {"count": ids.len(), "ids": ids, "filteredIds": filtered}, "error": null}),
        );
    }
    if operation == "crashgen" {
        let id = text(&request["id"])?;
        let configs: Vec<_> = registry
            .get_crashgen_versions(&id)
            .into_iter()
            .map(crashgen)
            .collect();
        let selected = registry
            .get_crashgen_for_version(&id, &text(&request["version"])?)
            .map(crashgen);
        return Ok(json!({"result": {"configs": configs, "selected": selected}, "error": null}));
    }
    if operation == "xse" {
        let result = registry.get_by_id(&text(&request["id"])?).and_then(|info| info.xse.as_ref()).map(|xse| {
            json!({"acronym": xse.acronym, "fullName": xse.full_name, "compatibleVersion": xse.compatible_version,
                "loader": xse.loader, "fileCount": xse.file_count})
        });
        return Ok(json!({"result": result, "error": null}));
    }
    if operation == "lookup" {
        let result = registry.get_by_id(&text(&request["id"])?).map(|info| {
            json!({"id": info.id, "version": info.version.to_string(), "shortName": info.short_name,
                "game": info.game, "docsName": info.docs_name, "steamId": info.steam_id, "isVr": info.is_vr})
        });
        return Ok(json!({"result": result, "error": null}));
    }
    let detected = match GameVersion::parse(&text(&request["version"])?) {
        Ok(version) => version,
        Err(VersionRegistryError::InvalidVersion(_)) => {
            return Ok(json!({"result": null, "error": {"code": "invalid_version"}}));
        }
        Err(error) => return Err(error.into()),
    };
    let matched = registry.match_version(
        &detected,
        &text(&request["game"])?,
        request["isVr"]
            .as_bool()
            .ok_or_else(|| invalid("isVr must be boolean"))?,
    );
    Ok(
        json!({"result": {"matchedId": matched.version_info.as_ref().map(|info| &info.id),
        "confidence": format!("{:?}", matched.confidence).to_lowercase(), "message": matched.message}, "error": null}),
    )
}

/// Project the full common crash generator metadata without interpreting its contents.
fn crashgen(config: &classic_version_registry_core::CrashgenConfig) -> Value {
    json!({"version": config.version, "name": config.name, "acronym": config.acronym,
        "dllFile": config.dll_file, "description": config.description, "downloadUrl": config.download_url})
}

/// Observe the extended public queries plus stable projections of native hash collections.
fn details(
    request: &Value,
    registry: &classic_version_registry_core::VersionRegistry,
) -> RunnerResult<Value> {
    use std::collections::{BTreeMap, BTreeSet};
    let id = text(&request["id"])?;
    let game = text(&request["game"])?;
    let version = match GameVersion::parse(&text(&request["version"])?) {
        Ok(version) => version,
        Err(VersionRegistryError::InvalidVersion(_)) => {
            return Ok(json!({"result": null, "error": {"code": "invalid_version"}}));
        }
        Err(error) => return Err(error.into()),
    };
    let is_vr = request["isVr"]
        .as_bool()
        .ok_or_else(|| invalid("isVr must be boolean"))?;
    let mut correct: Vec<_> = registry
        .get_correct_versions(is_vr)
        .iter()
        .map(|info| info.id.clone())
        .collect();
    let mut wrong: Vec<_> = registry
        .get_wrong_versions(is_vr)
        .iter()
        .map(|info| info.id.clone())
        .collect();
    correct.sort();
    wrong.sort();
    let filtered = registry.get_all_for_game(&game, Some(is_vr));
    let mut hashes = BTreeSet::new();
    let mut scripts: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for info in &filtered {
        if let Some(hash) = &info.exe_hash {
            hashes.insert(hash.clone());
        }
        if let Some(xse) = &info.xse {
            for (name, hash) in &xse.script_hashes {
                scripts
                    .entry(name.clone())
                    .or_default()
                    .insert(hash.clone());
            }
        }
    }
    let version_scripts: BTreeMap<_, _> = registry
        .get_by_id(&id)
        .and_then(|info| info.xse.as_ref())
        .map(|xse| xse.script_hashes.iter().cloned().collect())
        .unwrap_or_default();
    let handling = registry.unknown_version_handling();
    let strategy = match handling.strategy {
        classic_version_registry_core::UnknownVersionStrategy::NearestMatch => "nearest_match",
        classic_version_registry_core::UnknownVersionStrategy::Strict => "strict",
        classic_version_registry_core::UnknownVersionStrategy::DefaultOnly => "default_only",
    };
    let level = match handling.log_level {
        classic_version_registry_core::LogLevel::Debug => "debug",
        classic_version_registry_core::LogLevel::Warning => "warning",
        classic_version_registry_core::LogLevel::Error => "error",
    };
    Ok(json!({"result": {
        "byVersion": registry.get_by_version(&version).map(|info| &info.id),
        "byShortName": registry.get_by_short_name(&text(&request["shortName"])?).map(|info| &info.id),
        "correctIds": correct, "wrongIds": wrong,
        "addressLibrary": registry.get_address_library_filename(&version, is_vr),
        "crashgenVersions": registry.get_crashgen_version_strings(&id),
        "exeHashes": hashes, "scriptHashes": scripts, "versionScriptHashes": version_scripts,
        "strategy": strategy, "logLevel": level, "defaultId": handling.get_default(&game),
        "compatible": registry.get_by_id(&id).is_some_and(|info| info.is_compatible_with(&version)),
        "snapshotIds": filtered.iter().map(|info| &info.id).collect::<Vec<_>>()
    }, "error": null}))
}

/// Execute model compatibility methods and compare the ID semantics exposed by Python values.
fn values(
    request: &Value,
    registry: &classic_version_registry_core::VersionRegistry,
) -> RunnerResult<Value> {
    use std::hash::{DefaultHasher, Hash, Hasher};
    let info = registry
        .get_by_id(&text(&request["id"])?)
        .ok_or_else(|| invalid("value fixture ID missing"))?;
    let clone = info.clone();
    let other = registry
        .get_by_id(&text(&request["otherId"])?)
        .ok_or_else(|| invalid("other fixture ID missing"))?;
    let range = info
        .compatible_range
        .as_ref()
        .ok_or_else(|| invalid("fixture range missing"))?;
    let crashgen = info
        .get_crashgen_for_version(&text(&request["crashgen"])?)
        .ok_or_else(|| invalid("fixture crashgen missing"))?;
    let versions: Vec<_> = request["versions"]
        .as_array()
        .ok_or_else(|| invalid("versions must be array"))?
        .iter()
        .map(|value| GameVersion::parse(value.as_str().unwrap_or_default()))
        .collect::<Result<_, _>>()?;
    let mut original_hash = DefaultHasher::new();
    let mut clone_hash = DefaultHasher::new();
    // Python's public equality/hash contract is explicitly the core ID value;
    // hash bytes are implementation-dependent and never enter the observation.
    info.id.hash(&mut original_hash);
    clone.id.hash(&mut clone_hash);
    Ok(json!({"result": {
        "range": [range.min_version.to_string(), range.max_version.to_string()],
        "contains": versions.iter().map(|version| range.contains(version)).collect::<Vec<_>>(),
        "versionCompatible": versions.iter().map(|version| info.is_compatible_with(version)).collect::<Vec<_>>(),
        "crashgenCompatible": versions.iter().map(|version| crashgen.is_compatible_with(version)).collect::<Vec<_>>(),
        "compatibleCrashgens": versions.iter().map(|version| info.get_compatible_crashgens(Some(version)).iter().map(|config| config.version.clone()).collect::<Vec<_>>()).collect::<Vec<_>>(),
        "defaultCrashgens": info.get_compatible_crashgens(None).iter().map(|config| config.version.clone()).collect::<Vec<_>>(),
        "versions": info.get_crashgen_version_strings(), "selected": crashgen.version,
        "missing": info.get_crashgen_for_version("missing").map(|config| &config.version),
        "equalClone": info.id == clone.id, "differentId": info.id == other.id,
        "hashClone": original_hash.finish() == clone_hash.finish()
    }, "error": null}))
}
