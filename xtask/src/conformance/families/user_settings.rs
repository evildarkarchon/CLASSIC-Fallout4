//! Input hook for `user-settings`.
//!
//! The pack's inputs are input-only controls: which settings documents to
//! stage, which fields to observe, and the caller actions (preview, commit,
//! apply, restore, interference). This hook pins their shape per action. The
//! check that each scenario's input agrees with its case in the independent
//! compatibility oracle (`tests/fixtures/user_settings_compatibility/`)
//! belongs to the family's expectation compiler, which reads that oracle.

use std::collections::BTreeSet;

use serde_json::{Map, Value};

use super::{InputContext, issue};
use crate::conformance::Issue;

/// The canonical settings document name.
const SETTINGS: &str = "CLASSIC Settings.yaml";
/// The previous settings location a migration may edit.
const LEGACY_SETTINGS: &str = "CLASSIC Data/CLASSIC Settings.yaml";

/// Checks every scenario's input against its action's shape.
pub(super) fn validate(context: &InputContext<'_>) -> Vec<Issue> {
    let mut issues = Vec::new();
    for (index, scenario) in context.pack.scenarios.iter().enumerate() {
        let input = &scenario.input;
        let result = match scenario.action.as_str() {
            "user-settings.open" => keys(input, &["installationData", "observationFields"])
                .and_then(|()| staged(input))
                .and_then(|()| observation_fields(&input["observationFields"])),
            "user-settings.update" => keys(
                input,
                &[
                    "installationData",
                    "installationRootExists",
                    "previewMode",
                    "requestedUpdate",
                    "commit",
                    "externalEdit",
                ],
            )
            .and_then(|()| staged(input))
            .and_then(|()| update(input))
            .and_then(|()| only_capability(&scenario.capability_ids, "user-settings.update")),
            "user-settings.migrate" => keys(
                input,
                &[
                    "installationData",
                    "apply",
                    "restore",
                    "beforeApply",
                    "beforeRestore",
                ],
            )
            .and_then(|()| staged(input))
            .and_then(|()| migrate(input))
            .and_then(|()| only_capability(&scenario.capability_ids, "user-settings.migrate")),
            "user-settings.defaults" => keys(input, &[]),
            "user-settings.geometry" => keys(input, &["installationData", "blockLock"])
                .and_then(|()| staged(input))
                .and_then(|()| boolean(input, "blockLock")),
            "user-settings.legacy-import" => keys(input, &["installationData"])
                .and_then(|()| staged(input))
                .and_then(|()| legacy_import(input)),
            other => Err(format!("unsupported User Settings action {other}")),
        };
        if let Err(message) = result {
            issues.push(issue(index, message));
        }
    }
    issues
}

/// Requires exactly the member names `expected`.
fn keys(input: &Map<String, Value>, expected: &[&str]) -> Result<(), String> {
    let actual: BTreeSet<&str> = input.keys().map(String::as_str).collect();
    let wanted: BTreeSet<&str> = expected.iter().copied().collect();
    if actual == wanted {
        Ok(())
    } else {
        Err(format!(
            "User Settings input must contain exactly {wanted:?}, found {actual:?}"
        ))
    }
}

/// `installationData` is a list of staged `{fixtureRef, path}` documents.
fn staged(input: &Map<String, Value>) -> Result<(), String> {
    let ok = input["installationData"].as_array().is_some_and(|items| {
        items
            .iter()
            .all(|item| super::has_exact_keys(item, &["fixtureRef", "path"]))
    });
    ok.then_some(())
        .ok_or_else(|| "installationData must list {fixtureRef, path} documents".to_owned())
}

fn boolean(input: &Map<String, Value>, key: &str) -> Result<(), String> {
    input[key]
        .is_boolean()
        .then_some(())
        .ok_or_else(|| format!("{key} must be a boolean"))
}

fn only_capability(capabilities: &[String], capability: &str) -> Result<(), String> {
    (capabilities == [capability])
        .then_some(())
        .ok_or_else(|| format!("this scenario must name only the {capability} capability"))
}

/// Observation fields select oracle view fields: sorted, unique strings.
fn observation_fields(fields: &Value) -> Result<(), String> {
    let names: Option<Vec<&str>> = fields
        .as_array()
        .and_then(|items| items.iter().map(Value::as_str).collect());
    let sorted = names.is_some_and(|names| names.windows(2).all(|pair| pair[0] < pair[1]));
    sorted
        .then_some(())
        .ok_or_else(|| "observationFields must be sorted, unique field names".to_owned())
}

fn update(input: &Map<String, Value>) -> Result<(), String> {
    boolean(input, "commit")?;
    boolean(input, "installationRootExists")?;
    if !matches!(input["previewMode"].as_str(), Some("update" | "bootstrap")) {
        return Err("previewMode must be update or bootstrap".into());
    }
    if !input["requestedUpdate"].is_object() {
        return Err("requestedUpdate must map field paths to values".into());
    }
    let staged_at_settings = input["installationData"]
        .as_array()
        .is_some_and(|items| items.len() <= 1 && items.iter().all(|item| item["path"] == SETTINGS));
    if !staged_at_settings {
        return Err(format!(
            "an update stages at most one document, at {SETTINGS}"
        ));
    }
    let external = &input["externalEdit"];
    let external_ok = external.is_null()
        || (super::has_exact_keys(external, &["fixtureRef", "path"])
            && external["path"] == SETTINGS);
    external_ok.then_some(()).ok_or_else(|| {
        format!("externalEdit must be null or a {{fixtureRef, path}} edit of {SETTINGS}")
    })
}

fn migrate(input: &Map<String, Value>) -> Result<(), String> {
    boolean(input, "apply")?;
    boolean(input, "restore")?;
    for key in ["beforeApply", "beforeRestore"] {
        let control = &input[key];
        if control.is_null() {
            continue;
        }
        let fields: &[&str] = match control["kind"].as_str() {
            Some("external-edit") => &["kind", "fixtureRef", "path"],
            Some("tamper-backup") => &["kind", "fixtureRef"],
            Some("remove-backup" | "block-backup-directory") => &["kind"],
            _ => {
                return Err(format!(
                    "{key} has an unsupported migration interference kind"
                ));
            }
        };
        if !super::has_exact_keys(control, fields) {
            return Err(format!("{key} must contain exactly {fields:?}"));
        }
        if control["kind"] == "external-edit"
            && !matches!(control["path"].as_str(), Some(SETTINGS | LEGACY_SETTINGS))
        {
            return Err(format!("{key} must edit a supported settings location"));
        }
    }
    Ok(())
}

fn legacy_import(input: &Map<String, Value>) -> Result<(), String> {
    let paths: BTreeSet<&str> = input["installationData"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|item| item["path"].as_str())
        .collect();
    let complete = paths == BTreeSet::from([SETTINGS, "state.json"]);
    complete
        .then_some(())
        .ok_or_else(|| format!("a legacy import stages exactly {SETTINGS} and state.json"))
}
