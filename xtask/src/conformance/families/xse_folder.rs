//! Input hook for `xse-folder`.
//!
//! Every case must stay on controlled inputs so XSE folder resolution can
//! never fall through to host game or documents discovery: frozen OG/VR
//! registry metadata, a known (game, version, configured documents) triple,
//! controlled Game Local facts or Local.yaml text, and only the listed log
//! files. A resolution case's expected file inventory must be exactly the
//! fixture's own bytes.

use serde_json::{Value, json};

use super::{InputContext, has_exact_keys, issue};
use crate::conformance::Issue;
use crate::digest;

/// SHA-256 of the controlled registry YAML every case must carry. Deleting
/// either XSE record would let a configured-docs request reach the host.
const REGISTRY_SHA256: &str = "16ac61af30e482084589c03c2aec12b4f8333cec22f2528a10189bad393e5299";

/// The only (game, selectedVersion, configuredDocs) triples. Known games
/// always have a configured fallback; the unknown game returns before any
/// documents lookup.
const GAMES: [(&str, &str, &str); 3] = [
    ("Fallout4", "OG", "configured-docs"),
    ("Fallout4VR", "VR", "configured-docs"),
    ("Unknown", "auto", ""),
];

/// The YAML `\0` escape (backslash and zero, not a raw NUL) records an XSE
/// folder no platform can inspect; allowed only for log cases.
const UNINSPECTABLE_LOCAL_YAML: &str = "Game_Info:\n  Docs_Folder_XSE: \"bad\\0xse\"\n";

/// The Local.yaml texts a resolution case may seed (`None` = absent file).
const LOCAL_YAML: [Option<&str>; 4] = [
    None,
    Some("[invalid: yaml"),
    Some("Game_Info:\n  Docs_Folder_XSE: \" explicit-xse \"\n  Root_Folder_Docs: local-docs\n"),
    Some("Game_Info:\n  Docs_Folder_XSE: \" \"\n  Root_Folder_Docs: local-docs\n"),
];

/// The only log files a log case may create under its owned root.
const LOG_FILES: [&str; 4] = [
    "configured-docs/F4SE/f4se.log",
    "configured-docs/F4SE/f4sevr.log",
    "local-docs/F4SE/f4se.log",
    "explicit-xse/f4se.log",
];

/// Checks every scenario's fixture.
pub(super) fn validate(context: &InputContext<'_>) -> Vec<Issue> {
    let mut issues = Vec::new();
    let mut registry: Option<&str> = None;
    for (index, scenario, fixture) in context.sole_json_fixtures() {
        let derive = scenario.action == "xse-folder.derive";
        let log = scenario.action == "xse-folder.log";
        let source_key = if derive {
            "gameLocalFacts"
        } else {
            "localYaml"
        };
        let mut keys = vec![
            "registryYaml",
            "game",
            "selectedVersion",
            source_key,
            "configuredDocs",
        ];
        if log {
            keys.push("logFiles");
        }
        if !has_exact_keys(fixture, &keys) {
            issues.push(issue(
                index,
                format!(
                    "an XSE folder fixture for {} must contain exactly {keys:?}",
                    scenario.action
                ),
            ));
            continue;
        }
        let this_registry = fixture["registryYaml"].as_str().unwrap_or_default();
        if registry.is_some_and(|first| first != this_registry) {
            issues.push(issue(
                index,
                "every XSE folder case must carry identical registry bytes",
            ));
        }
        registry = Some(this_registry);
        if digest::sha256_hex(this_registry.as_bytes()) != REGISTRY_SHA256 {
            issues.push(issue(
                index,
                "XSE folder requires the controlled registry metadata",
            ));
        }
        let triple = (
            fixture["game"].as_str(),
            fixture["selectedVersion"].as_str(),
            fixture["configuredDocs"].as_str(),
        );
        if !GAMES
            .iter()
            .any(|(game, version, docs)| triple == (Some(game), Some(version), Some(docs)))
        {
            issues.push(issue(
                index,
                "XSE folder (game, selectedVersion, configuredDocs) could consult host discovery",
            ));
        }
        if derive {
            let controlled = [
                json!({"docsFolderXse": "explicit-xse", "rootFolderDocs": "local-docs"}),
                json!({"docsFolderXse": "", "rootFolderDocs": "local-docs"}),
                json!({"docsFolderXse": null, "rootFolderDocs": null}),
            ];
            if !controlled.contains(&fixture["gameLocalFacts"]) {
                issues.push(issue(
                    index,
                    "XSE folder derivation requires controlled Game Local facts",
                ));
            }
        } else {
            let local = fixture["localYaml"].as_str();
            let allowed = (fixture["localYaml"].is_null() || local.is_some())
                && (LOCAL_YAML.contains(&local)
                    || (log && local == Some(UNINSPECTABLE_LOCAL_YAML)));
            if !allowed {
                issues.push(issue(
                    index,
                    "XSE folder requires controlled Local.yaml text",
                ));
            }
        }
        if log {
            let files = fixture["logFiles"].as_array();
            let controlled = files.is_some_and(|files| {
                let names: Vec<Option<&str>> = files.iter().map(Value::as_str).collect();
                let unique = names
                    .iter()
                    .collect::<std::collections::BTreeSet<_>>()
                    .len()
                    == names.len();
                unique
                    && names
                        .iter()
                        .all(|name| name.is_some_and(|name| LOG_FILES.contains(&name)))
            });
            if !controlled {
                issues.push(issue(
                    index,
                    "XSE log cases may create only the controlled, distinct log files",
                ));
            }
            continue;
        }
        // A resolution case observes the preserved YAML inventory, which must
        // be the fixture's own bytes rather than an independent answer.
        let mut inventory = vec![json!({"path": "CLASSIC Main.yaml", "content": this_registry})];
        if let (Some(local), Some(game)) = (fixture["localYaml"].as_str(), fixture["game"].as_str())
        {
            inventory.push(json!({"path": format!("CLASSIC {game} Local.yaml"), "content": local}));
        }
        inventory.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
        if scenario.expected.get("files") != Some(&Value::Array(inventory)) {
            issues.push(issue(
                index,
                "an XSE folder expected inventory must preserve the fixture bytes",
            ));
        }
    }
    issues
}
