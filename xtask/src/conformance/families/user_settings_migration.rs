//! `user-settings.migrate`: expectation compiler and receipt normalizer.
//!
//! Each migrate scenario references one `migration_scenarios` entry of the
//! compatibility corpus, which names a `migration_cases` entry (source
//! document, planning outcome, review rows, proposed document) plus the
//! caller's actions: apply, restore, and optional interference before each
//! (an external edit, a tampered, removed or blocked backup). Compiling plays
//! those actions over an in-memory file tree to build every checkpoint the
//! participant must observe. Adapters receive only fixture references and the
//! caller actions.
//!
//! The normalizer authenticates the plan before comparing it: repeated
//! planning must be identical, the reversed plan must be the exact inverse,
//! and a double reversal must round-trip. Published proposals are compared as
//! YAML nodes only after their bytes match the approved proposal, and the
//! published revision token is checked against those bytes.

use std::collections::BTreeMap;

use serde_json::{Map, Value, json};

use super::user_settings_oracle::{
    Failure, LOCK, Oracle, SETTINGS, array, member, object, object_of, text, truthy,
};
use super::yaml_nodes::yaml_nodes;
use super::{InputContext, NormalizationError, decode_hex, revision};
use crate::digest;

/// The placeholder for a published revision in compiled expectations; the
/// normalizer swaps it in once the observed token matches the proposal.
const PROPOSED_REVISION: &str = "<verified-proposed-revision>";
/// The settings document's previous location.
const LEGACY_SETTINGS: &str = "CLASSIC Data/CLASSIC Settings.yaml";

/// The content of one file in the simulated installation.
#[derive(Debug, Clone)]
enum Content {
    /// Raw bytes, observed as `bytesHex`.
    Bytes(Vec<u8>),
    /// A published proposal, observed as raw bytes but compared as YAML
    /// nodes (`proposedYamlNodes`).
    Proposed(Value),
}

impl Content {
    /// The raw bytes, for revision tokens; a proposal has no fixed bytes.
    fn bytes(&self) -> Result<&[u8], String> {
        match self {
            Self::Bytes(bytes) => Ok(bytes),
            Self::Proposed(_) => Err("a published proposal has no authored bytes".into()),
        }
    }
}

/// The expected file tree: every file, its parent directories, `.` and any
/// retained directories, sorted by path.
fn tree(files: &BTreeMap<String, Content>, directories: &[String]) -> Vec<Value> {
    let mut entries: BTreeMap<String, Value> = BTreeMap::new();
    let mut directory = |path: &str| {
        entries.insert(
            path.to_owned(),
            json!({"path": {"path": path}, "kind": "directory"}),
        );
    };
    directory(".");
    for path in directories {
        directory(path);
    }
    for path in files.keys() {
        let mut parent = path.as_str();
        while let Some((head, _)) = parent.rsplit_once('/') {
            directory(head);
            parent = head;
        }
    }
    for (path, content) in files {
        let entry = match content {
            Content::Bytes(bytes) => {
                json!({"path": {"path": path}, "kind": "file", "bytesHex": digest::hex(bytes)})
            }
            Content::Proposed(nodes) => {
                json!({"path": {"path": path}, "kind": "file", "proposedYamlNodes": nodes})
            }
        };
        entries.insert(path.clone(), entry);
    }
    entries.into_values().collect()
}

/// A planning endpoint.
fn endpoint(location: &str, version: &Value) -> Value {
    json!({"location": location, "schemaVersion": version})
}

/// Review rows with their YAML fragments as nodes; version and location
/// transitions keep their plain values.
fn changes(rows: &Value) -> Result<Value, String> {
    let mut rows = rows
        .as_array()
        .ok_or("migration changes must be an array")?
        .clone();
    for row in &mut rows {
        let kind = row.get("kind").and_then(Value::as_str);
        if matches!(
            kind,
            Some("schema_version_transition" | "location_transition")
        ) {
            continue;
        }
        let row = row
            .as_object_mut()
            .ok_or("migration change rows must be objects")?;
        for key in ["before", "after"] {
            match row.get(key) {
                None => return Err(format!("migration change row lacks {key}")),
                Some(Value::Null) => {}
                Some(Value::String(fragment)) => {
                    let nodes = yaml_nodes(fragment.as_bytes())?;
                    row.insert(key.into(), nodes);
                }
                Some(_) => return Err(format!("migration change {key} must be YAML text")),
            }
        }
    }
    Ok(Value::Array(rows))
}

/// The input-only controls a migration scenario must carry, and its fixture
/// references (the source, then each interference fixture once).
fn input(oracle: &Oracle<'_>, spec: &Value, case: &Value) -> Result<(Value, Vec<String>), String> {
    let installation = match member(case, "source_fixture")? {
        Value::Null => json!([]),
        name => {
            let name = name.as_str().ok_or("source_fixture must be a file name")?;
            json!([{"fixtureRef": oracle.alias(name)?, "path": text(case, "source_path")?}])
        }
    };
    let mut references: Vec<String> = installation
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|item| item["fixtureRef"].as_str().map(str::to_owned))
        .collect();
    for key in ["before_apply", "before_restore"] {
        let control = member(spec, key)?;
        if control.is_null() {
            continue;
        }
        let kind = control.get("kind").and_then(Value::as_str);
        let fields: &[&str] = match kind {
            Some("external-edit") => &["kind", "fixtureRef", "path"],
            Some("tamper-backup") => &["kind", "fixtureRef"],
            Some("remove-backup" | "block-backup-directory") => &["kind"],
            _ => return Err("invalid migration interference control".into()),
        };
        if !super::has_exact_keys(control, fields) {
            return Err("invalid migration interference control".into());
        }
        if kind == Some("external-edit")
            && !matches!(control["path"].as_str(), Some(SETTINGS | LEGACY_SETTINGS))
        {
            return Err("migration edit must select a supported settings location".into());
        }
        if let Some(reference) = control.get("fixtureRef") {
            let reference = reference
                .as_str()
                .filter(|reference| oracle.fixtures.contains_key(*reference))
                .ok_or("migration interference requires a declared fixture")?;
            if !references.iter().any(|known| known == reference) {
                references.push(reference.to_owned());
            }
        }
    }
    if !member(spec, "apply")?.is_boolean() || !member(spec, "restore")?.is_boolean() {
        return Err("migration approval controls must be booleans".into());
    }
    Ok((
        json!({
            "installationData": installation,
            "apply": spec["apply"],
            "restore": spec["restore"],
            "beforeApply": spec["before_apply"],
            "beforeRestore": spec["before_restore"],
        }),
        references,
    ))
}

/// Compiles every `user-settings.migrate` scenario.
pub(super) fn compile(
    oracle: &Oracle<'_>,
    context: &InputContext<'_>,
    expected: &mut [Map<String, Value>],
) -> Result<(), Failure> {
    let pack_level = |message: String| (None, message);
    let empty = Vec::new();
    let specs_list = match oracle.oracle.get("migration_scenarios") {
        None => &empty,
        Some(_) => array(oracle.oracle, "migration_scenarios").map_err(pack_level)?,
    };
    let mut specs = BTreeMap::new();
    for spec in specs_list {
        if specs
            .insert(text(spec, "id").map_err(pack_level)?, spec)
            .is_some()
        {
            return Err(pack_level("duplicate migration oracle scenario".into()));
        }
    }
    let scenarios = &context.pack.scenarios;
    let selected: Vec<Option<&str>> = scenarios
        .iter()
        .filter(|scenario| scenario.action == "user-settings.migrate")
        .map(|scenario| {
            scenario
                .expected
                .get("migrationScenario")
                .and_then(Value::as_str)
        })
        .collect();
    let selected_ids: std::collections::BTreeSet<&str> =
        selected.iter().flatten().copied().collect();
    if selected_ids.len() != selected.len() || selected_ids != specs.keys().copied().collect() {
        return Err(pack_level(
            "User Settings pack must cover every migration oracle scenario exactly once".into(),
        ));
    }
    for (index, scenario) in scenarios.iter().enumerate() {
        if scenario.action != "user-settings.migrate" {
            continue;
        }
        let located = |message: String| (Some(index), message);
        if scenario.expected.len() != 1 {
            return Err(located(
                "migration expectations must reference the shared oracle".into(),
            ));
        }
        let spec = specs[scenario.expected["migrationScenario"]
            .as_str()
            .unwrap_or_default()];
        expected[index] = migration(oracle, scenario, spec).map_err(located)?;
    }
    Ok(())
}

/// Compiles one migrate scenario from its oracle spec.
fn migration(
    oracle: &Oracle<'_>,
    scenario: &crate::conformance::schema::Scenario,
    spec: &Value,
) -> Result<Map<String, Value>, String> {
    let case_id = text(spec, "case")?;
    let case = member(member(oracle.oracle, "migration_cases")?, case_id)?;
    let (inputs, refs) = input(oracle, spec, case)?;
    let normalization = &scenario.normalization;
    let optional_files = normalization.optional_empty_files.as_ref().map(|files| {
        files
            .iter()
            .map(|file| {
                json!({"path": file.path, "relativePath": file.relative_path, "rationale": file.rationale})
            })
            .collect::<Vec<_>>()
    });
    let normalization_matches = normalization.root_relative_paths
        && normalization.unordered_paths.is_empty()
        && normalization.excluded_paths.is_empty()
        && spec.get("optional_empty_files") == optional_files.map(Value::Array).as_ref();
    if inputs != Value::Object(scenario.input.clone())
        || scenario.fixture_refs != refs
        || scenario.capability_ids != ["user-settings.migrate"]
        || !normalization_matches
    {
        return Err("migration input does not match its independent oracle".into());
    }

    let source_path = text(case, "source_path")?;
    let original = match member(case, "source_fixture")? {
        Value::Null => None,
        name => Some(oracle.read(name.as_str().ok_or("source_fixture must be a file name")?)?),
    };
    let mut files: BTreeMap<String, Content> = BTreeMap::new();
    if let Some(original) = &original {
        files.insert(source_path.to_owned(), Content::Bytes(original.clone()));
    }
    let initial = tree(&files, &[]);
    let planned = member(case, "status")? == "planned";
    let source = endpoint(
        if source_path.starts_with("CLASSIC Data/") {
            "legacy"
        } else {
            "canonical"
        },
        case.get("source_version").unwrap_or(&Value::Null),
    );
    let target = endpoint("canonical", &json!({"major": 1, "minor": 0}));
    let original_revision = revision(original.as_deref());
    let proposed = if planned {
        Some(yaml_nodes(&oracle.read(text(case, "expected_document")?)?)?)
    } else {
        None
    };
    let plan = match (&proposed, &original) {
        (None, _) => Value::Null,
        (Some(proposed), Some(original)) => json!({
            "required": member(case, "required")?,
            "baseRevision": original_revision,
            "source": source,
            "target": target,
            "changes": changes(member(case, "changes")?)?,
            "originalHex": digest::hex(original),
            "proposedYamlNodes": proposed,
        }),
        (Some(_), None) => return Err("a planned migration needs a source document".into()),
    };
    let planning = json!({
        "status": member(case, "status")?,
        "diagnostics": member(case, "diagnostics")?,
        "plan": plan,
    });
    let mut apply = json!({
        "status": member(spec, "apply_status")?,
        "expectedRevision": null,
        "actualRevision": null,
        "errorCode": null,
        "receipt": null,
    });
    let mut restore = json!({
        "status": member(spec, "restore_status")?,
        "revision": null,
        "expectedRevision": null,
        "actualRevision": null,
        "errorCode": null,
    });

    // Applies only authored external changes to the expected tree.
    let interfere = |control: &Value,
                     backup: Option<&str>,
                     files: &mut BTreeMap<String, Content>|
     -> Result<(), String> {
        if control.is_null() {
            return Ok(());
        }
        match control["kind"].as_str() {
            Some("block-backup-directory") => {
                files.insert("CLASSIC Backup".into(), Content::Bytes(b"blocked".to_vec()));
            }
            Some("remove-backup") => {
                let backup = backup.ok_or("remove-backup needs an applied backup")?;
                files
                    .remove(backup)
                    .ok_or("remove-backup needs an existing backup")?;
            }
            kind => {
                let path = if kind == Some("tamper-backup") {
                    backup.ok_or("tamper-backup needs an applied backup")?
                } else {
                    text(control, "path")?
                };
                let alias = text(control, "fixtureRef")?;
                let name = oracle
                    .fixtures
                    .get(alias)
                    .ok_or("migration interference requires a declared fixture")?;
                files.insert(path.to_owned(), Content::Bytes(oracle.read(name)?));
            }
        }
        Ok(())
    };

    let mut backup = None;
    if let (Some(proposed), Some(original)) = (&proposed, &original)
        && truthy(&spec["apply"])
    {
        interfere(member(spec, "before_apply")?, None, &mut files)?;
        if apply["status"] == "conflict" {
            let current = files.get(SETTINGS).or_else(|| files.get(source_path));
            let current = current.map(Content::bytes).transpose()?;
            apply["expectedRevision"] = json!(original_revision);
            apply["actualRevision"] = json!(revision(current));
        } else {
            files.insert(LOCK.into(), Content::Bytes(Vec::new()));
            if apply["status"] == "error" {
                apply["errorCode"] = member(spec, "error_code")?.clone();
            } else {
                let path = format!(
                    "CLASSIC Backup/User Settings/Migrations/{}.yaml",
                    original_revision.trim_start_matches("sha256:")
                );
                files.insert(path.clone(), Content::Bytes(original.clone()));
                files.insert(SETTINGS.into(), Content::Proposed(proposed.clone()));
                apply["receipt"] = json!({
                    "sourcePath": {"path": source_path},
                    "destinationPath": {"path": SETTINGS},
                    "backupPath": {"path": path},
                    "source": source,
                    "target": target,
                    "backupRevision": original_revision,
                    "publishedRevision": PROPOSED_REVISION,
                });
                backup = Some(path);
            }
        }
    }
    let after_apply = tree(&files, &[]);
    let retained: Vec<String> = after_apply
        .iter()
        .filter(|entry| entry["kind"] == "directory")
        .filter_map(|entry| entry["path"]["path"].as_str().map(str::to_owned))
        .collect();
    if let Some(backup) = &backup
        && truthy(&spec["restore"])
    {
        let original = original
            .as_ref()
            .ok_or("a restore needs a source document")?;
        interfere(member(spec, "before_restore")?, Some(backup), &mut files)?;
        if restore["status"] == "restored" {
            files.insert(source_path.to_owned(), Content::Bytes(original.clone()));
            if source["location"] == "legacy" {
                files.remove(SETTINGS);
            }
            restore["revision"] = json!(original_revision);
        } else if restore["status"] == "error" {
            restore["errorCode"] = member(spec, "error_code")?.clone();
        } else {
            let edit_path = text(member(spec, "before_restore")?, "path")?;
            let edited = files
                .get(edit_path)
                .ok_or("a restore conflict needs the edited document")?
                .bytes()?;
            restore["expectedRevision"] = if edit_path == SETTINGS {
                json!(PROPOSED_REVISION)
            } else {
                json!(original_revision)
            };
            restore["actualRevision"] = json!(revision(Some(edited)));
        }
    }
    Ok(object_of(json!({
        "planning": planning,
        "repeatedPlanning": {"matchesPlanning": true},
        "reversedPlan": if planned { json!({"verifiedInverse": true}) } else { Value::Null },
        "roundTripPlan": if planned { json!({"matchesPlanning": true}) } else { Value::Null },
        "afterPlanningTree": initial,
        "apply": apply,
        "afterApplyTree": after_apply,
        "restore": restore,
        "finalTree": tree(&files, &retained),
    })))
}

/// Authenticates a migration observation and normalizes its published YAML.
///
/// Only the YAML representation, verified proposed revision tokens and an
/// optional empty conflict coordination file (handled by the declared
/// normalization) vary across participants. Backups, original and restored
/// bytes, errors, tree contents and every other field compare exactly.
///
/// # Errors
///
/// Fails (at `$.planning`) when planning is not deterministic, the reversal
/// is not the exact inverse or does not round-trip, a revision token does not
/// match the observed bytes, or published bytes differ from the approved
/// proposal.
pub(super) fn normalize(
    expected: &Map<String, Value>,
    actual: &Map<String, Value>,
) -> Result<Map<String, Value>, NormalizationError> {
    let mut result = actual.clone();
    authenticate(expected, &mut result)
        .map_err(|message| NormalizationError::new(message, "$.planning"))?;
    Ok(result)
}

/// The body of [`normalize`], rewriting `result` in place.
fn authenticate(
    expected: &Map<String, Value>,
    result: &mut Map<String, Value>,
) -> Result<(), String> {
    let field = |result: &Map<String, Value>, key: &str| {
        result
            .get(key)
            .cloned()
            .ok_or_else(|| format!("migration observation lacks {key}"))
    };
    let mut planning = field(result, "planning")?;
    if planning != field(result, "repeatedPlanning")? {
        return Err("migration planning is not deterministic".into());
    }
    result.insert("repeatedPlanning".into(), json!({"matchesPlanning": true}));
    let mut proposed = None;
    let mut proposed_revision = None;
    let plan = planning
        .get_mut("plan")
        .ok_or("migration planning lacks plan")?;
    if !plan.is_null() {
        let original = hex_member(plan, "originalHex")?;
        let proposal = hex_member(plan, "proposedHex")?;
        if member(plan, "baseRevision")? != &json!(revision(Some(&original))) {
            return Err("migration base revision does not match retained original bytes".into());
        }
        let published = revision(Some(&proposal));
        let mut inverse = object(plan, "plan")?.clone();
        inverse.insert("source".into(), member(plan, "target")?.clone());
        inverse.insert("target".into(), member(plan, "source")?.clone());
        inverse.insert("baseRevision".into(), json!(published));
        inverse.insert("originalHex".into(), member(plan, "proposedHex")?.clone());
        inverse.insert("proposedHex".into(), member(plan, "originalHex")?.clone());
        let mut reversed_rows = Vec::new();
        for row in array(plan, "changes")?.iter().rev() {
            let mut reversed = object(row, "migration change row")?.clone();
            for (key, from) in [
                ("sourcePath", "targetPath"),
                ("targetPath", "sourcePath"),
                ("before", "after"),
                ("after", "before"),
            ] {
                reversed.insert(key.into(), member(row, from)?.clone());
            }
            reversed_rows.push(Value::Object(reversed));
        }
        inverse.insert("changes".into(), Value::Array(reversed_rows));
        if Value::Object(inverse) != field(result, "reversedPlan")? {
            return Err("migration reversal is not the exact inverse".into());
        }
        if *plan != field(result, "roundTripPlan")? {
            return Err("migration double reversal changed the plan".into());
        }
        result.insert("reversedPlan".into(), json!({"verifiedInverse": true}));
        result.insert("roundTripPlan".into(), json!({"matchesPlanning": true}));
        let changes = changes(member(plan, "changes")?)?;
        let plan = plan
            .as_object_mut()
            .ok_or("migration plan must be an object")?;
        plan.insert("changes".into(), changes);
        plan.remove("proposedHex");
        plan.insert("proposedYamlNodes".into(), yaml_nodes(&proposal)?);
        proposed = Some(proposal);
        proposed_revision = Some(published);
    }
    result.insert("planning".into(), planning);

    let apply = result
        .get_mut("apply")
        .ok_or("migration observation lacks apply")?;
    let receipt = apply
        .get_mut("receipt")
        .ok_or("migration apply lacks receipt")?;
    if !receipt.is_null() {
        if proposed_revision.is_none()
            || receipt.get("publishedRevision")
                != proposed_revision.as_ref().map(|r| json!(r)).as_ref()
        {
            return Err("migration published revision does not match the approved proposal".into());
        }
        receipt["publishedRevision"] = json!(PROPOSED_REVISION);
    }
    let expected_restore = expected
        .get("restore")
        .and_then(|restore| restore.get("expectedRevision"));
    if expected_restore == Some(&json!(PROPOSED_REVISION)) {
        let restore = result
            .get_mut("restore")
            .ok_or("migration observation lacks restore")?;
        if restore.get("expectedRevision") != proposed_revision.as_ref().map(|r| json!(r)).as_ref()
        {
            return Err("restore conflict is not anchored to the published revision".into());
        }
        restore["expectedRevision"] = json!(PROPOSED_REVISION);
    }
    for checkpoint in ["afterPlanningTree", "afterApplyTree", "finalTree"] {
        let authored: BTreeMap<&str, &Value> = expected
            .get(checkpoint)
            .and_then(Value::as_array)
            .ok_or_else(|| format!("expected {checkpoint} must be a tree array"))?
            .iter()
            .filter_map(|entry| Some((entry["path"]["path"].as_str()?, entry)))
            .collect();
        let tree = result
            .get_mut(checkpoint)
            .and_then(Value::as_array_mut)
            .ok_or("migration checkpoint must be a tree array")?;
        for entry in tree {
            let path = entry
                .get("path")
                .and_then(|path| path.get("path"))
                .and_then(Value::as_str)
                .ok_or("migration tree entries need a path")?;
            let publishes = authored
                .get(path)
                .is_some_and(|authored| authored.get("proposedYamlNodes").is_some());
            if !publishes {
                continue;
            }
            if !super::has_exact_keys(entry, &["path", "kind", "bytesHex"])
                || entry["kind"] != "file"
            {
                return Err("published migration requires raw regular-file byte evidence".into());
            }
            let bytes = hex_member(entry, "bytesHex")?;
            let proposed = proposed
                .as_ref()
                .filter(|proposed| **proposed == bytes)
                .ok_or("published migration bytes differ from the approved proposal")?;
            let entry = entry.as_object_mut().expect("checked object");
            entry.remove("bytesHex");
            entry.insert("proposedYamlNodes".into(), yaml_nodes(proposed)?);
        }
    }
    Ok(())
}

/// Decodes the lowercase hexadecimal member `key`.
fn hex_member(value: &Value, key: &str) -> Result<Vec<u8>, String> {
    member(value, key)?
        .as_str()
        .and_then(decode_hex)
        .ok_or_else(|| "migration bytes must be lowercase hexadecimal".to_owned())
}

#[cfg(test)]
#[path = "user_settings_migration_tests.rs"]
mod tests;
