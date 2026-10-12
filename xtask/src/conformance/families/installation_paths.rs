//! Input hook for `installation-paths`.
//!
//! - `inspect` cases stage owned cache directories with the controlled
//!   registry metadata and one executable marker, so discovery never reads a
//!   host installation.
//! - `locate` cases start the Installation Root search inside a
//!   runner-owned tree (`tree/build/bin`, `tree/work`) and may place
//!   `CLASSIC Data` only in one of the six documented candidates. The
//!   expected directory tree must be exactly the tree those inputs create.

use std::collections::BTreeSet;

use serde_json::{Value, json};

use super::{InputContext, has_exact_keys, issue, sha256_hex};
use crate::conformance::Issue;

/// SHA-256 of the controlled Version Registry YAML an `inspect` case stages.
const REGISTRY_SHA256: &str = "d6659f95c1a4bd45e4ba4d6e6e505f405f458b4eaba37fc2e67e950c90dd8567";

/// Where a locate case's executable runs from.
const EXECUTABLE_DIR: &str = "tree/build/bin";
/// A locate case's working directory.
const WORKING_DIR: &str = "tree/work";
/// The six Installation Root candidates, in the documented search order.
const CANDIDATES: [&str; 6] = [
    EXECUTABLE_DIR,
    WORKING_DIR,
    "tree/build",
    "tree",
    "tree/build/install",
    "tree/work/install",
];

/// Checks every scenario's action and fixture.
pub(super) fn validate(context: &InputContext<'_>) -> Vec<Issue> {
    let mut issues = Vec::new();
    for (index, scenario) in context.pack.scenarios.iter().enumerate() {
        if !matches!(
            scenario.action.as_str(),
            "installation-paths.inspect" | "installation-paths.locate"
        ) {
            issues.push(issue(index, format!("{} is not an installation-paths action", scenario.action)));
        }
    }
    for (index, scenario, fixture) in context.sole_json_fixtures() {
        let result = if scenario.action == "installation-paths.locate" {
            let capability_ok = scenario.capability_ids == ["installation-paths.locate"];
            check_locate(fixture, scenario.expected.get("directories")).and_then(|()| {
                capability_ok
                    .then_some(())
                    .ok_or_else(|| "a locate case must name only the locate capability".to_owned())
            })
        } else {
            check_inspect(fixture)
        };
        if let Err(message) = result {
            issues.push(issue(index, message));
        }
    }
    issues
}

fn check_locate(fixture: &Value, expected_directories: Option<&Value>) -> Result<(), String> {
    if !has_exact_keys(fixture, &["operation", "executableDir", "workingDir", "classicDataIn"]) {
        return Err("an Installation Root fixture must contain exactly operation, executableDir, workingDir and classicDataIn".into());
    }
    if fixture["operation"] != "locate" {
        return Err("an Installation Root fixture must request the locate operation".into());
    }
    if fixture["executableDir"] != EXECUTABLE_DIR || fixture["workingDir"] != WORKING_DIR {
        return Err("the Installation Root search must start inside the owned tree".into());
    }
    let placements: Option<Vec<&str>> = fixture["classicDataIn"]
        .as_array()
        .and_then(|items| items.iter().map(Value::as_str).collect());
    let Some(placements) = placements else {
        return Err("classicDataIn must be a list of candidate directories".into());
    };
    let unique: BTreeSet<&str> = placements.iter().copied().collect();
    if unique.len() != placements.len() || !unique.iter().all(|place| CANDIDATES.contains(place)) {
        return Err("CLASSIC Data may only be placed, once each, in a locator candidate".into());
    }
    if expected_directories != Some(&json!(directory_tree(&placements))) {
        return Err("the expected directory tree must be exactly the tree the locate inputs create".into());
    }
    Ok(())
}

/// Every directory a locate runner creates: the two start directories and
/// each `CLASSIC Data` placement, with all their ancestors, sorted.
fn directory_tree(placements: &[&str]) -> Vec<String> {
    let mut found = BTreeSet::new();
    let leaves = [EXECUTABLE_DIR.to_owned(), WORKING_DIR.to_owned()]
        .into_iter()
        .chain(placements.iter().map(|place| format!("{place}/CLASSIC Data")));
    for leaf in leaves {
        let parts: Vec<&str> = leaf.split('/').collect();
        for end in 1..=parts.len() {
            found.insert(parts[..end].join("/"));
        }
    }
    found.into_iter().collect()
}

fn check_inspect(fixture: &Value) -> Result<(), String> {
    if !has_exact_keys(fixture, &["gamePath", "docsPath", "registryYaml", "files"]) {
        return Err("an installation paths fixture must contain exactly gamePath, docsPath, registryYaml and files".into());
    }
    let (game, docs) = (fixture["gamePath"].as_str(), fixture["docsPath"].as_str());
    if !matches!((game, docs), (Some("game"), Some("docs")) | (Some("Game Folder"), Some("Docs Folder"))) {
        return Err("installation paths must be owned cache directories".into());
    }
    let registry_ok = fixture["registryYaml"]
        .as_str()
        .is_some_and(|text| sha256_hex(text.as_bytes()) == REGISTRY_SHA256);
    let marker = json!({format!("{}/Fallout4.exe", game.unwrap_or_default()): "owned executable marker"});
    if !registry_ok || fixture["files"] != marker {
        return Err("installation paths need the controlled registry metadata and exactly one executable marker".into());
    }
    Ok(())
}
