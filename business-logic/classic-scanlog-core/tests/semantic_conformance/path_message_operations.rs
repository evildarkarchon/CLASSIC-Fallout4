//! Public path and message observations from independently authored fixture inputs.

use super::{RunnerResult, invalid, strings, text};
use classic_message_core::{Message, MessageTarget, MessageType, format_log_message};
use classic_shared_core::path_core::PathHandler;
use serde_json::{Value, json};
use std::{
    fs,
    path::{Path, PathBuf},
};

#[cfg(test)]
#[path = "path_message_operations_tests.rs"]
mod tests;

/// Restrict authored destinations to portable paths beneath the temporary root.
fn owned(root: &Path, relative: &str) -> RunnerResult<PathBuf> {
    if relative.is_empty()
        || relative.contains(['\\', ':'])
        || relative
            .split('/')
            .any(|part| matches!(part, "" | "." | ".."))
    {
        return Err(invalid("fixture path must be a contained relative path").into());
    }
    Ok(root.join(relative))
}

/// Remove only this invocation's root and native separators from path-bearing text.
fn portable(value: &str, root: &Path) -> String {
    // Core APIs may already normalize separators while the temporary root remains native.
    let value = value.replace('\\', "/");
    let root = root.to_string_lossy().replace('\\', "/");
    let root = root.strip_prefix("//?/").unwrap_or(&root);
    value
        .strip_prefix("//?/")
        .unwrap_or(&value)
        .replace(&format!("//?/{root}/"), "")
        .replace(&format!("{root}/"), "")
}

/// Exercise real core APIs; temporary inputs are removed even when a call fails.
pub(super) fn execute(family: &str, fixture: &Value) -> RunnerResult<Value> {
    let request = &fixture["request"];
    if family == "message-operations" {
        let kind = match text(&request["type"])?.as_str() {
            "Info" => MessageType::Info,
            "Warning" => MessageType::Warning,
            "Error" => MessageType::Error,
            "Success" => MessageType::Success,
            "Progress" => MessageType::Progress,
            "Debug" => MessageType::Debug,
            "Critical" => MessageType::Critical,
            _ => return Err(invalid("unknown message type").into()),
        };
        let target = match text(&request["target"])?.as_str() {
            "All" => MessageTarget::All,
            "Gui" => MessageTarget::Gui,
            "Console" => MessageTarget::Console,
            "LogOnly" => MessageTarget::LogOnly,
            _ => return Err(invalid("unknown message target").into()),
        };
        let mut message = Message::with_target(&text(&request["content"])?, kind, target);
        if !request["details"].is_null() {
            message = message.with_details(&text(&request["details"])?);
        }
        return Ok(
            json!({"type": message.msg_type().name(), "target": format!("{:?}", message.target()),
            "content": message.content(), "title": message.title(), "details": message.details(),
            "formatted": format_log_message(message.content(), message.details())}),
        );
    }
    let temporary = tempfile::tempdir()?;
    let root = temporary.path();
    for relative in strings(&fixture["directories"])? {
        fs::create_dir_all(owned(root, &relative)?)?;
    }
    for (relative, content) in fixture["files"]
        .as_object()
        .ok_or_else(|| invalid("files must be an object"))?
    {
        let path = owned(root, relative)?;
        fs::create_dir_all(path.parent().ok_or_else(|| invalid("missing parent"))?)?;
        fs::write(path, text(content)?.as_bytes())?;
    }
    match family {
        "path-operations" => {
            let relative = text(&request["path"])?;
            let path = owned(root, &relative)?;
            let exists = classic_path_core::is_valid_path(&path);
            let result = classic_path_core::validate_required_files(
                &path,
                &strings(&request["requiredFiles"])?,
            );
            let error = result.err().map(|error| portable(&error.to_string(), root));
            Ok(
                json!({"path": relative, "exists": exists, "requiredFiles": {"accepted": error.is_none(), "error": error}}),
            )
        }
        "path-normalization" => {
            let handler = PathHandler::default();
            let base = owned(root, &text(&request["base"])?)?;
            let joined =
                handler.join_paths(&base.to_string_lossy(), &strings(&request["components"])?);
            let normalized = handler.normalize_path(&joined)?;
            let paths = strings(&request["validatePaths"])?
                .iter()
                .map(|path| Ok(owned(root, path)?.to_string_lossy().to_string()))
                .collect::<RunnerResult<Vec<_>>>()?;
            let validation: Vec<_> = handler
                .validate_paths_batch(&paths)
                .into_iter()
                .map(|(path, exists, _)| json!({"path": portable(&path, root), "exists": exists}))
                .collect();
            Ok(
                json!({"joinedPath": portable(&joined, root), "normalizedPath": portable(&normalized, root), "validation": validation}),
            )
        }
        _ => Err(invalid("unsupported path/message family").into()),
    }
}
