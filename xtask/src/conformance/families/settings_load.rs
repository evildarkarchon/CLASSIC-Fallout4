//! Input hooks for the settings-load candidates: `settings-load`,
//! `settings-yaml` and `settings-yaml-batch`.
//!
//! Each fixture is an authored request with an exact shape: contained,
//! portable relative paths for the files a load case stages, and typed
//! updates with an explicit order for the YAML lifecycle cases.

use serde_json::{Value, json};

use super::{InputContext, has_exact_keys, issue, is_string_list};
use crate::conformance::Issue;
use crate::conformance::schema::is_relative_file_path;

/// `settings-load`: `{files: {path: text}, request: {single, batch}}`.
pub(super) fn validate_load(context: &InputContext<'_>) -> Vec<Issue> {
    validate_each(context, "settings-load.execute", |fixture| {
        if !has_exact_keys(fixture, &["files", "request"]) {
            return Err("a settings fixture must contain exactly files and request".into());
        }
        let request = &fixture["request"];
        let relative = |value: &Value| value.as_str().is_some_and(is_relative_file_path);
        let request_ok = has_exact_keys(request, &["single", "batch"])
            && relative(&request["single"])
            && request["batch"].as_array().is_some_and(|batch| batch.iter().all(relative));
        if !request_ok {
            return Err("a settings request needs a contained single path and a list of contained batch paths".into());
        }
        let files_ok = fixture["files"].as_object().is_some_and(|files| {
            files
                .iter()
                .all(|(path, content)| is_relative_file_path(path) && content.is_string())
        });
        if !files_ok {
            return Err("settings files must map contained relative paths to text".into());
        }
        Ok(())
    })
}

/// `settings-yaml`: `{kind: "yaml", content, updates{name,ready,size,values},
/// updateOrder: ["name","ready","size","values"]}`.
pub(super) fn validate_yaml(context: &InputContext<'_>) -> Vec<Issue> {
    validate_each(context, "settings-yaml.execute", |fixture| {
        if !has_exact_keys(fixture, &["kind", "content", "updates", "updateOrder"])
            || fixture["kind"] != "yaml"
            || !fixture["content"].is_string()
        {
            return Err("a YAML fixture must be {kind: \"yaml\", content, updates, updateOrder}".into());
        }
        let updates = &fixture["updates"];
        let typed = has_exact_keys(updates, &["name", "ready", "size", "values"])
            && updates["name"].is_string()
            && updates["ready"].is_boolean()
            && updates["size"].is_i64()
            && is_string_list(&updates["values"]);
        if !typed {
            return Err("YAML typed updates must be name (string), ready (bool), size (integer) and values (strings)".into());
        }
        if fixture["updateOrder"] != json!(["name", "ready", "size", "values"]) {
            return Err("YAML updates require the explicit common order name, ready, size, values".into());
        }
        Ok(())
    })
}

/// `settings-yaml-batch`: `{kind: "yaml-batch", content, keys: [str],
/// updates: {str: str}}`.
pub(super) fn validate_yaml_batch(context: &InputContext<'_>) -> Vec<Issue> {
    validate_each(context, "settings-yaml-batch.execute", |fixture| {
        let ok = has_exact_keys(fixture, &["kind", "content", "keys", "updates"])
            && fixture["kind"] == "yaml-batch"
            && fixture["content"].is_string()
            && is_string_list(&fixture["keys"])
            && fixture["updates"]
                .as_object()
                .is_some_and(|updates| updates.values().all(Value::is_string));
        if ok {
            Ok(())
        } else {
            Err("a YAML batch fixture must be {kind: \"yaml-batch\", content, keys: [string], updates: {string: string}}".into())
        }
    })
}

/// Requires `action` on every scenario and runs `check` on each fixture.
fn validate_each(
    context: &InputContext<'_>,
    action: &str,
    check: impl Fn(&Value) -> Result<(), String>,
) -> Vec<Issue> {
    let mut issues = Vec::new();
    for (index, scenario) in context.pack.scenarios.iter().enumerate() {
        if scenario.action != action {
            issues.push(issue(index, format!("{} scenarios must use the {action} action", context.pack.family_id)));
        }
    }
    for (index, _, fixture) in context.sole_json_fixtures() {
        if let Err(message) = check(fixture) {
            issues.push(issue(index, message));
        }
    }
    issues
}
