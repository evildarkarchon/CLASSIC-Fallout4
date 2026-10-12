//! Input hook for the auxiliary operation families: `web-operations`,
//! `resource-operations` and the five `version-*` operation families.
//!
//! Each fixture holds only an authored request (plus, for file-backed
//! operations, the files to stage), with exact field sets, so a participant
//! never receives anything it could echo back as an answer, and every
//! filesystem path stays inside the fixture workspace.

use serde_json::Value;

use super::{InputContext, has_exact_keys, issue};
use crate::conformance::Issue;
use crate::conformance::schema::is_relative_file_path;

/// The resource type list a resource request must enumerate, in order.
const RESOURCE_TYPES: [&str; 11] = [
    "texture",
    "mesh",
    "script",
    "plugin",
    "sound",
    "animation",
    "interface",
    "strings",
    "archive",
    "config",
    "other",
];

/// Checks every scenario's action and fixture request shape.
pub(super) fn validate(context: &InputContext<'_>) -> Vec<Issue> {
    let family = context.pack.family_id.as_str();
    let mut issues = Vec::new();
    for (index, scenario) in context.pack.scenarios.iter().enumerate() {
        let allowed = if family == "web-operations" {
            scenario.action == "web-operations.observe"
                || scenario.action == "web-operations.routes"
        } else {
            scenario.action == format!("{family}.observe")
        };
        if !allowed {
            issues.push(issue(
                index,
                format!(
                    "{} is not an auxiliary operation action of {family}",
                    scenario.action
                ),
            ));
        }
    }
    for (index, scenario, fixture) in context.sole_json_fixtures() {
        if let Err(message) = check_fixture(family, &scenario.action, fixture) {
            issues.push(issue(index, message));
        }
    }
    issues
}

/// Validates one fixture; the error names the first violated rule.
fn check_fixture(family: &str, action: &str, fixture: &Value) -> Result<(), String> {
    if action == "web-operations.routes" {
        let routes =
            serde_json::json!({"request": {"operation": "game-routes", "game": "Fallout4"}});
        return if fixture == &routes {
            Ok(())
        } else {
            Err("a web routing fixture must be exactly the Fallout4 game-routes request".into())
        };
    }
    let request = &fixture["request"];
    if family.starts_with("version-") && request.get("operation").is_some() {
        return check_version_request(fixture);
    }
    let fields: &[&str] = match family {
        "web-operations" => &["url", "path", "params", "suffix"],
        "resource-operations" => &["path", "type", "validate", "types"],
        "version-operations" => &["version", "other"],
        _ => {
            return Err(format!(
                "{family} fixtures must name an extended version operation"
            ));
        }
    };
    let fixture_keys: &[&str] = if family == "resource-operations" {
        &["request", "files"]
    } else {
        &["request"]
    };
    if !has_exact_keys(fixture, fixture_keys) {
        return Err(format!(
            "an auxiliary fixture must contain only {fixture_keys:?}"
        ));
    }
    if !has_exact_keys(request, fields) {
        return Err(format!(
            "an auxiliary request must have exactly the fields {fields:?}"
        ));
    }
    let plain_strings = request
        .as_object()
        .into_iter()
        .flatten()
        .filter(|(key, _)| !matches!(key.as_str(), "params" | "validate" | "types"))
        .all(|(_, value)| value.is_string());
    if !plain_strings {
        return Err("auxiliary request fields must be strings".into());
    }
    if family == "web-operations" {
        let pairs = request["params"].as_array().is_some_and(|params| {
            params.iter().all(|pair| {
                pair.as_array()
                    .is_some_and(|pair| pair.len() == 2 && pair.iter().all(Value::is_string))
            })
        });
        if !pairs {
            return Err("URL query parameters must be ordered string pairs".into());
        }
    }
    if family == "resource-operations" {
        let relative = |value: &Value| value.as_str().is_some_and(is_relative_file_path);
        let files = fixture["files"].as_object().is_some_and(|files| {
            files
                .iter()
                .all(|(path, content)| is_relative_file_path(path) && content.is_string())
        });
        let validate = request["validate"]
            .as_array()
            .is_some_and(|items| items.iter().all(relative));
        let types = request["types"] == serde_json::json!(RESOURCE_TYPES);
        if !files || !relative(&request["path"]) || !validate || !types {
            return Err("resource paths must stay inside the fixture workspace and types must list the 11 resource types".into());
        }
    }
    Ok(())
}

/// Validates an extended version operation request (`extract`, `known-*`,
/// `pe-*`): exact fields, string values, and contained hex files for PE.
fn check_version_request(fixture: &Value) -> Result<(), String> {
    let request = &fixture["request"];
    let operation = request["operation"].as_str().unwrap_or_default();
    let fields: &[&str] = match operation {
        "extract" => &["operation", "filename", "content"],
        "known-fallout4" | "known-f4se" => &["operation", "version"],
        "pe-extract" | "pe-path" => &["operation", "path"],
        _ => return Err(format!("unknown extended version operation {operation:?}")),
    };
    let strings = request
        .as_object()
        .is_some_and(|map| map.values().all(Value::is_string));
    if !has_exact_keys(request, fields) || !strings {
        return Err(format!(
            "a {operation} request must have exactly the string fields {fields:?}"
        ));
    }
    let pe = operation.starts_with("pe-");
    let fixture_keys: &[&str] = if pe {
        &["request", "files"]
    } else {
        &["request"]
    };
    if !has_exact_keys(fixture, fixture_keys) {
        return Err(format!(
            "a version fixture must contain only {fixture_keys:?}"
        ));
    }
    if pe {
        let hex = |text: &str| {
            text.len().is_multiple_of(2)
                && text
                    .bytes()
                    .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
        };
        let files = fixture["files"].as_object().is_some_and(|files| {
            files
                .iter()
                .all(|(path, bytes)| is_relative_file_path(path) && bytes.as_str().is_some_and(hex))
        });
        let path = request["path"].as_str().is_some_and(is_relative_file_path);
        if !files || !path {
            return Err("PE fixtures must use contained paths and lowercase hex bytes".into());
        }
    }
    Ok(())
}
