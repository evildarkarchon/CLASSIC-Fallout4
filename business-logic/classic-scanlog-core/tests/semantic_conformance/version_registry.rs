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
    if !matches!(operation.as_str(), "lookup" | "match") {
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
