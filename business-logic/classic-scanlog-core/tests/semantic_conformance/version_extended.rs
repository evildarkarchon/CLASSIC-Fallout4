//! Remaining version operations against hermetic authored inputs.
use super::{RunnerResult, invalid, text};
use serde_json::{Value, json};

/// Execute public operations, retaining the common CXX PE result contract.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    use classic_version_core as version;
    let request = &fixture["request"];
    let operation = text(&request["operation"])?;
    if operation == "extract" {
        let content = text(&request["content"])?;
        return Ok(
            json!({"filename":version::extract_version_from_filename(&text(&request["filename"])?).map(|v|v.to_string()), "log":version::extract_version_from_log(&content).map(|v|v.to_string()), "all":version::extract_all_versions(&content).iter().map(ToString::to_string).collect::<Vec<_>>()}),
        );
    }
    if operation.starts_with("known-") {
        let native = version::parse_version(&text(&request["version"])?)?;
        let known = if operation == "known-f4se" {
            version::is_known_f4se_version(&native)
        } else {
            version::is_known_fallout4_version(&native)
        };
        return Ok(json!({operation:known}));
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for (relative, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("missing PE files"))?
    {
        let target = owned(root, relative)?;
        std::fs::create_dir_all(target.parent().ok_or_else(|| invalid("missing parent"))?)?;
        let content = text(content)?;
        let bytes = (0..content.len())
            .step_by(2)
            .map(|i| {
                content
                    .get(i..i + 2)
                    .ok_or_else(|| invalid("invalid hex"))
                    .and_then(|s| u8::from_str_radix(s, 16).map_err(|_| invalid("invalid hex")))
            })
            .collect::<Result<Vec<_>, _>>()?;
        std::fs::write(target, bytes)?;
    }
    let path = owned(root, &text(&request["path"])?)?;
    if operation == "pe-path" {
        return Ok(json!({"validPath":version::pe_version::is_valid_executable_path(&path)}));
    }
    // CXX loses error details; this observation claims no error classification.
    let value = version::pe_version::extract_pe_version(&path)
        .map(|(a, b, c, d)| format!("{a}.{b}.{c}.{d}"))
        .unwrap_or_default();
    Ok(json!({"peVersion":value}))
}

/// Reject path escapes before creating any authored fixture files.
fn owned(root: &std::path::Path, relative: &str) -> RunnerResult<std::path::PathBuf> {
    if relative.is_empty()
        || relative.contains(['\\', ':'])
        || relative.split('/').any(|p| matches!(p, "" | "." | ".."))
    {
        return Err(invalid("invalid PE fixture path").into());
    }
    Ok(root.join(relative))
}
