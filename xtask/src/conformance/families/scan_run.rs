//! Input hooks for the Crash Log Scan families: `crash-log-scan-run` and
//! `autoscan-report` (which share the scan-run input plan), and
//! `crash-log-scan-launch`.
//!
//! These inputs are run requests, not single fixtures. The hooks keep them
//! closed: only known request members, typed scalar options, staged
//! documents as `{fixtureRef, path}`, and contained relative paths in every
//! path list, so a participant can only stage and observe inside its run
//! directory.

use std::collections::BTreeSet;

use serde_json::{Map, Value};

use super::{InputContext, has_exact_keys, issue};
use crate::conformance::Issue;
use crate::conformance::schema::is_canonical_relative_path;

/// Members every scan-run input plan carries.
const RUN_REQUIRED: [&str; 8] = [
    "game",
    "gameVersion",
    "installationData",
    "intent",
    "maxConcurrent",
    "showFormidValues",
    "simplifyLogs",
    "formidDatabasePaths",
];

/// Optional scan-run input members (flows, sources, observation selectors).
const RUN_OPTIONAL: [&str; 14] = [
    "continuationFlow",
    "directoryInputs",
    "executionFlow",
    "forbiddenEffectPaths",
    "localIgnorePaddingBytes",
    "logInputs",
    "observationProfile",
    "observedPaths",
    "setupContext",
    "standardSource",
    "targetedInputs",
    "unsolvedLogs",
    "unsolvedLogsDestination",
    "unsolvedLogsPath",
];

/// Scan-run members that list staged `{fixtureRef, path}` documents.
const STAGED_LISTS: [&str; 2] = ["installationData", "logInputs"];

/// Scan-run members that list contained relative paths, as strings or as
/// `{path}` objects.
const PATH_LISTS: [&str; 3] = ["formidDatabasePaths", "forbiddenEffectPaths", "observedPaths"];

/// The exact members of a Crash Log Scan Launch input.
const LAUNCH_KEYS: [&str; 5] = ["settingsFixtureRef", "intent", "targetedInputs", "overrides", "files"];

/// `crash-log-scan-run` and `autoscan-report` scan-run input plans.
pub(super) fn validate_run(context: &InputContext<'_>) -> Vec<Issue> {
    context
        .pack
        .scenarios
        .iter()
        .enumerate()
        .filter_map(|(index, scenario)| run_plan(&scenario.input).err().map(|message| issue(index, message)))
        .collect()
}

fn run_plan(input: &Map<String, Value>) -> Result<(), String> {
    let present: BTreeSet<&str> = input.keys().map(String::as_str).collect();
    let missing: Vec<&str> = RUN_REQUIRED.iter().copied().filter(|key| !present.contains(key)).collect();
    if !missing.is_empty() {
        return Err(format!("a scan-run input is missing {missing:?}"));
    }
    let unknown: Vec<&str> = present
        .iter()
        .copied()
        .filter(|key| !RUN_REQUIRED.contains(key) && !RUN_OPTIONAL.contains(key))
        .collect();
    if !unknown.is_empty() {
        return Err(format!("a scan-run input has unknown members {unknown:?}"));
    }
    for key in ["showFormidValues", "simplifyLogs"] {
        if !input[key].is_boolean() {
            return Err(format!("{key} must be a boolean"));
        }
    }
    // Zero stays allowed: the request-validation scenarios submit it on purpose.
    if !input["maxConcurrent"].is_u64() {
        return Err("maxConcurrent must be a non-negative integer".into());
    }
    for key in STAGED_LISTS {
        if let Some(value) = input.get(key) {
            let staged = value
                .as_array()
                .is_some_and(|items| items.iter().all(|item| has_exact_keys(item, &["fixtureRef", "path"])));
            if !staged {
                return Err(format!("{key} must list {{fixtureRef, path}} documents"));
            }
        }
    }
    for key in PATH_LISTS {
        if let Some(value) = input.get(key) {
            let contained = value.as_array().is_some_and(|items| {
                items
                    .iter()
                    .all(|item| {
                        let path = if has_exact_keys(item, &["path"]) { &item["path"] } else { item };
                        path.as_str().is_some_and(is_canonical_relative_path)
                    })
            });
            if !contained {
                return Err(format!("{key} must list canonical relative paths"));
            }
        }
    }
    Ok(())
}

/// `crash-log-scan-launch` launch requests.
pub(super) fn validate_launch(context: &InputContext<'_>) -> Vec<Issue> {
    let mut issues = Vec::new();
    for (index, scenario) in context.pack.scenarios.iter().enumerate() {
        let input = Value::Object(scenario.input.clone());
        let ok = has_exact_keys(&input, &LAUNCH_KEYS)
            && input["intent"].is_string()
            && input["targetedInputs"].is_array()
            && input["overrides"].is_object()
            && input["files"].is_array();
        if !ok {
            issues.push(issue(
                index,
                format!("a launch input must be exactly {LAUNCH_KEYS:?} with a string intent, list targetedInputs and files, and an overrides object"),
            ));
        }
    }
    issues
}
