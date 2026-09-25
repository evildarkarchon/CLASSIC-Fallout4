//! Observe XSE detection against fixed local fixture files.
use super::{RunnerResult, invalid, text};
use classic_xse_core::{XseError, XseType, detect_xse_version, get_xse_info, is_xse_installed};
use serde_json::{Value, json};
use std::fs;

/// Inspect one fresh fixture directory without consulting installed game state.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    if fixture.as_object().is_none_or(|object| {
        !object.contains_key("files") || object.keys().any(|key| key != "files" && key != "kind")
    }) {
        return Err(invalid("unsupported XSE fixture").into());
    }
    let variant = fixture
        .get("kind")
        .map(text)
        .transpose()?
        .unwrap_or_else(|| "F4SE".to_owned());
    let kind = match variant.as_str() {
        "F4SE" => XseType::F4SE,
        "F4SEVR" => XseType::F4SEVR,
        "SKSE" => XseType::SKSE,
        "SKSE64" => XseType::SKSE64,
        "SKSEVR" => XseType::SKSEVR,
        "SFSE" => XseType::SFSE,
        _ => return Err(invalid("unsupported XSE variant").into()),
    };
    let dll = format!("{}_1_10_163.dll", variant.to_lowercase());
    let game = match kind {
        XseType::F4SE => Some(classic_shared_core::GameId::Fallout4),
        XseType::F4SEVR => Some(classic_shared_core::GameId::Fallout4VR),
        XseType::SKSE64 => Some(classic_shared_core::GameId::Skyrim),
        XseType::SFSE => Some(classic_shared_core::GameId::Starfield),
        _ => None,
    };
    if game.is_some_and(|game| XseType::from_game_id(game) != kind) {
        return Err(invalid("XSE game mapping disagrees with fixture type").into());
    }
    let files = fixture["files"]
        .as_array()
        .ok_or_else(|| invalid("files must be an array"))?;
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for value in files {
        let name = text(value)?;
        if name != kind.loader_name() && name != dll {
            return Err(invalid("unsupported XSE filename").into());
        }
        fs::write(root.join(name), b"")?;
    }
    let version = match detect_xse_version(&root.join(kind.loader_name()), kind) {
        Ok(version) => Some(version.to_string()),
        Err(XseError::NotFound(_) | XseError::VersionDetectionFailed(_)) => None,
        Err(error) => return Err(error.into()),
    };
    let info = get_xse_info(root, kind);
    let installed = is_xse_installed(root, kind);
    let constructed = classic_xse_core::XseInfo::new(kind, root.to_path_buf());
    if constructed.installed
        || constructed.version.is_some()
        || constructed.xse_type != kind
        || constructed.check_installed() != installed
        || constructed.loader_path() != root.join(kind.loader_name())
    {
        return Err(invalid("XSE constructor or path/installation accessors changed").into());
    }
    // Snapshot bytes after every filesystem operation so unexpected writes remain visible.
    let mut inventory = Vec::new();
    for entry in fs::read_dir(root)? {
        let entry = entry?;
        if !entry.file_type()?.is_file() {
            return Err(invalid("unexpected non-file in XSE fixture").into());
        }
        let hex: String = fs::read(entry.path())?
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect();
        inventory.push(json!({"path": entry.file_name().to_string_lossy(), "hex": hex}));
    }
    inventory.sort_by(|left, right| left["path"].as_str().cmp(&right["path"].as_str()));
    Ok(
        json!({"typeName": kind.as_str(), "loaderName": kind.loader_name(), "dllPrefix": kind.dll_prefix(),
        "installed": installed, "version": version,
        "info": {"typeName": info.xse_type.as_str(), "installed": info.installed, "version": info.version.map(|version| version.to_string())},
        "files": inventory}),
    )
}
