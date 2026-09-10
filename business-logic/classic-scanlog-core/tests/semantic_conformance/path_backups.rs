//! Retain byte-copy and replacement evidence from the public path backup core.

use super::{RunnerResult, invalid, text};
use classic_path_core::{BackupManager, XseVersion};
use serde_json::{Value, json};
use std::{fs, path::Path};

/// Encode retained bytes without depending on a transport-specific binary codec.
fn encode(bytes: Vec<u8>) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// Decode the input-only fixture's lowercase hexadecimal byte string.
fn decode(value: String) -> RunnerResult<Vec<u8>> {
    if !value.len().is_multiple_of(2) || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(invalid("invalid backup fixture hex").into());
    }
    Ok((0..value.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&value[index..index + 2], 16))
        .collect::<Result<Vec<_>, _>>()?)
}

/// Read only contained files into stable relative-path byte observations.
fn inventory(
    root: &Path,
    directory: &Path,
    result: &mut serde_json::Map<String, Value>,
) -> RunnerResult<()> {
    for entry in fs::read_dir(directory)? {
        let path = entry?.path();
        if path.is_dir() {
            inventory(root, &path, result)?;
        } else {
            result.insert(
                path.strip_prefix(root)?
                    .to_string_lossy()
                    .replace('\\', "/"),
                json!(encode(fs::read(path)?)),
            );
        }
    }
    Ok(())
}

/// Exercise explicit/extracted versions, initial absence and same-version overwrite.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    if fixture.get("kind").and_then(Value::as_str) == Some("timestamp") {
        return timestamp(fixture);
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    let source = root.join("settings.ini");
    let log = root.join("xse.log");
    fs::write(&log, text(&fixture["log"])?)?;
    fs::write(&source, decode(text(&fixture["firstHex"])?)?)?;
    let manager = BackupManager::new(root.join("backups"));
    let initial = manager.list_versions()?;
    let version = manager.extract_version_from_xse_log(&log)?;
    let explicit = XseVersion::new(text(&fixture["version"])?);
    if version != explicit {
        return Err(invalid("explicit version disagrees with extraction").into());
    }
    let created = manager.create_backup(&source, &version)?;
    let first = encode(fs::read(&created)?);
    fs::write(&source, decode(text(&fixture["replacementHex"])?)?)?;
    if manager.create_backup(&source, &explicit)? != created {
        return Err(invalid("replacement path changed").into());
    }
    let local = |path: &Path| -> RunnerResult<String> {
        Ok(path
            .strip_prefix(root)?
            .to_string_lossy()
            .replace('\\', "/"))
    };
    let mut files = serde_json::Map::new();
    inventory(root, root, &mut files)?;
    Ok(
        json!({"version":version.full_version(),"sanitized":version.sanitized(),"initial":initial,"versions":manager.list_versions()?,"root":local(manager.backup_root())?,"directory":local(&manager.get_version_path(&explicit))?,"created":local(&created)?,"firstHex":first,"replacementHex":encode(fs::read(created)?),"files":files}),
    )
}

/// Reference timestamp naming through the same core operations used by CXX wrappers.
fn timestamp(fixture: &Value) -> RunnerResult<Value> {
    use std::time::{SystemTime, UNIX_EPOCH};
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    let source = root.join("settings.ini");
    fs::write(&source, decode(text(&fixture["hex"])?)?)?;
    let manager = BackupManager::new(root.join("CLASSIC Backups").join(text(&fixture["game"])?));
    let initial = manager.list_versions()?;
    let before = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    let version = XseVersion::new(before.to_string());
    let created = manager.create_backup(&source, &version)?;
    let after = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    let listed = manager.list_versions()?;
    if listed != [version.full_version()] || before > after || !created.starts_with(root) {
        return Err(invalid("timestamp backup escaped its owned interval or root").into());
    }
    let copied = encode(fs::read(&created)?);
    let mut files = serde_json::Map::new();
    inventory(root, root, &mut files)?;
    let files = files
        .keys()
        .map(|name| name.replace(version.full_version(), "<timestamp>"))
        .collect::<Vec<_>>();
    Ok(
        json!({"initial":initial,"listed":["<timestamp>"],"created":"CLASSIC Backups/Fallout4/<timestamp>/settings.ini","sourceHex":encode(fs::read(source)?),"copyHex":copied,"files":files}),
    )
}
