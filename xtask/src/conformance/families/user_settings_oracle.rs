//! Expectation compiler and receipt normalizer for `user-settings`.
//!
//! The family's only authored value oracle is the shared compatibility corpus,
//! `<fixtureRoot>/expectations.json`, plus the YAML documents it names. The
//! pack's `expected` members only reference it:
//!
//! - `user-settings.open`: `{"compatibilityCase": id}`, one scenario per
//!   ordinary corpus case;
//! - `user-settings.update`: `{"operationScenario": id}`, one per corpus
//!   operation with a `conformance` block;
//! - `user-settings.migrate`: `{"migrationScenario": id}` (see
//!   `user_settings_migration`);
//! - `user-settings.legacy-import`: `{"legacyImportCase": "restore-existing"}`.
//!
//! Compiling resolves each reference into the exact observation, and checks
//! that the scenario's input-only controls agree with the oracle. The oracle
//! and the expected documents are digest dependencies, never adapter inputs.
//! `user-settings.defaults` and `user-settings.geometry` expectations are
//! authored inline and stay as they are.
//!
//! The normalizer authenticates published settings bytes before comparing
//! them as YAML nodes (`yaml_nodes`), so a participant cannot claim a revision
//! match or hand over pre-normalized YAML.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use serde_json::{Map, Value, json};

use super::user_settings_migration;
use super::yaml_nodes::yaml_nodes;
use super::{
    Compiled, EXPECTATION_RULE, InputContext, NormalizationError, decode_hex, expectation_issue,
    oracle_file, read_oracle, revision,
};
use crate::conformance::{Issue, json as strict_json};
use crate::digest;

/// The canonical settings document name.
pub(super) const SETTINGS: &str = "CLASSIC Settings.yaml";
/// The commit coordination file a publication leaves behind.
pub(super) const LOCK: &str = "CLASSIC Settings.yaml.commit.lock";
/// The oracle's file name beneath the fixture root.
const ORACLE: &str = "expectations.json";
/// Corpus cases that describe mutating operations, so no open scenario may
/// cover them.
const MUTATING_CASES: [&str; 2] = ["tui_remembered_state", "concurrent_revision_conflict"];

/// Open-view fields a defaults case reads, with their `CLASSIC_Settings` label.
const DEFAULT_FIELDS: [(&str, &str); 7] = [
    ("update_check", "Update Check"),
    ("game_version", "Game Version"),
    ("move_unsolved_logs", "Move Unsolved Logs"),
    ("max_concurrent_scans", "Max Concurrent Scans"),
    ("fcx_mode", "FCX Mode"),
    ("simplify_logs", "Simplify Logs"),
    ("show_formid_values", "Show FormID Values"),
];

/// The FormID database mapping's field path.
const FORMID_DATABASES: &str = "/CLASSIC_Settings/FormID Databases";
/// A request selector below the mapping names a game-aware save for that game.
const FORMID_DATABASE_SAVE_PREFIX: &str = "/CLASSIC_Settings/FormID Databases/";

/// The order accepted update fields are reported in: the first three typed
/// setters, the grouped window/TUI fields, then the remaining setters.
const UPDATE_FIELD_ORDER: [&str; 26] = [
    "/CLASSIC_Settings/Update Check",
    "/CLASSIC_Settings/Update Source",
    "/UI/preferences/auto_switch_after_scan",
    "/UI/window_geometry/main_tab/maximized",
    "/UI/window_geometry/main_tab/width",
    "/UI/window_geometry/main_tab/height",
    "/UI/tui/active_tab",
    "/UI/tui/results_panel_width",
    "/UI/tui/sort_ascending",
    "/CLASSIC_Settings/Managed Game",
    "/CLASSIC_Settings/Game Version",
    "/CLASSIC_Settings/Game Folder Path",
    "/CLASSIC_Settings/Game EXE Path",
    "/CLASSIC_Settings/Documents Folder Path",
    "/CLASSIC_Settings/INI Folder Path",
    "/CLASSIC_Settings/MODS Folder Path",
    "/CLASSIC_Settings/FCX Mode",
    "/CLASSIC_Settings/Simplify Logs",
    "/CLASSIC_Settings/Show Statistics",
    "/CLASSIC_Settings/Show FormID Values",
    FORMID_DATABASES,
    "/CLASSIC_Settings/Move Unsolved Logs",
    "/CLASSIC_Settings/Unsolved Logs Destination",
    "/CLASSIC_Settings/SCAN Custom Path",
    "/CLASSIC_Settings/Papyrus Log Path",
    "/CLASSIC_Settings/Max Concurrent Scans",
];

/// What the per-action compilers share.
pub(super) struct Oracle<'a> {
    /// The parsed `expectations.json`.
    pub oracle: &'a Value,
    /// The canonical fixture root.
    pub base: &'a Path,
    /// The pack's fixture aliases (alias → fixture-root-relative path).
    pub fixtures: &'a BTreeMap<String, String>,
}

impl Oracle<'_> {
    /// Reads the fixture-root-relative oracle file `name`.
    pub fn read(&self, name: &str) -> Result<Vec<u8>, String> {
        read_oracle(self.base, name)
    }

    /// The pack alias declaring the fixture file `name`.
    pub fn alias(&self, name: &str) -> Result<&str, String> {
        self.fixtures
            .iter()
            .find(|(_, path)| *path == name)
            .map(|(alias, _)| alias.as_str())
            .ok_or_else(|| format!("oracle fixture {name} is not declared by the pack"))
    }
}

/// Compiles every user-settings expectation (see the module docs).
pub(super) fn compile(context: &InputContext<'_>) -> Result<Compiled, Issue> {
    let base = context.fixture_root()?;
    let pack_issue = |message: String| {
        Issue::new(
            "/fixtureRoot",
            EXPECTATION_RULE,
            format!("invalid User Settings compatibility oracle: {message}"),
        )
    };
    let oracle_path = oracle_file(&base, ORACLE).map_err(pack_issue)?;
    if context.fixture_paths(&base).contains(&oracle_path) {
        return Err(pack_issue(
            "the oracle cannot be an adapter input fixture".into(),
        ));
    }
    let text = std::fs::read_to_string(&oracle_path)
        .map_err(|error| pack_issue(format!("cannot read {ORACLE}: {error}")))?;
    let document = strict_json::parse_strict(&text)
        .map_err(|error| pack_issue(format!("{ORACLE}: {error}")))?;
    let oracle = Oracle {
        oracle: document.value(),
        base: &base,
        fixtures: &context.pack.fixtures,
    };
    let mut compiled = Compiled::identity(context.pack);
    let scenarios = &context.pack.scenarios;
    let actions: Vec<&str> = scenarios.iter().map(|s| s.action.as_str()).collect();
    if let Some(index) = actions.iter().position(|action| {
        !matches!(
            *action,
            "user-settings.open"
                | "user-settings.update"
                | "user-settings.migrate"
                | "user-settings.defaults"
                | "user-settings.geometry"
                | "user-settings.legacy-import"
        )
    }) {
        return Err(expectation_issue(
            index,
            "unsupported User Settings scenario action",
        ));
    }

    open_cases(&oracle, context, &mut compiled.expected).map_err(at_pack(&pack_issue))?;
    operations(&oracle, context, &mut compiled.expected).map_err(at_pack(&pack_issue))?;
    user_settings_migration::compile(&oracle, context, &mut compiled.expected)
        .map_err(at_pack(&pack_issue))?;
    legacy_import(&oracle, context, &mut compiled.expected).map_err(at_pack(&pack_issue))?;

    let mut oracles = vec![format!("{}/{ORACLE}", context.pack.fixture_root)];
    oracles.extend(
        expected_documents(oracle.oracle)
            .map_err(pack_issue)?
            .into_iter()
            .map(|name| format!("{}/{name}", context.pack.fixture_root)),
    );
    compiled.oracles = oracles;
    Ok(compiled)
}

/// A compiler failure: scenario-level (with its index) or pack-level.
pub(super) type Failure = (Option<usize>, String);

/// Renders a [`Failure`] as an issue.
fn at_pack(pack_issue: &impl Fn(String) -> Issue) -> impl Fn(Failure) -> Issue + '_ {
    move |(index, message)| match index {
        Some(index) => expectation_issue(index, message),
        None => pack_issue(message),
    }
}

/// The expected documents the oracle names, sorted and unique: the
/// documents a conformance operation publishes and every migration case's
/// proposal. They stay out of adapter run plans.
fn expected_documents(oracle: &Value) -> Result<BTreeSet<String>, String> {
    let mut names = BTreeSet::new();
    for operation in array(oracle, "operation_scenarios")? {
        if operation.get("conformance").is_some() && truthy(member(operation, "writes_document")?) {
            names.insert(text(operation, "expected_document")?.to_owned());
        }
    }
    if let Some(cases) = oracle.get("migration_cases") {
        for case in object(cases, "migration_cases")?.values() {
            if let Some(name) = case.get("expected_document") {
                names.insert(
                    name.as_str()
                        .ok_or("migration expected_document must be a string")?
                        .to_owned(),
                );
            }
        }
    }
    Ok(names)
}

/// Compiles the `user-settings.open` scenarios from the corpus cases.
fn open_cases(
    oracle: &Oracle<'_>,
    context: &InputContext<'_>,
    expected: &mut [Map<String, Value>],
) -> Result<(), Failure> {
    let pack_level = |message: String| (None, message);
    let root = oracle.oracle;
    if root.get("contract_version") != Some(&json!(1)) {
        return Err(pack_level(
            "unsupported User Settings compatibility contract version".into(),
        ));
    }
    let mut cases = BTreeMap::new();
    for case in array(root, "cases").map_err(pack_level)? {
        let id = text(case, "id").map_err(pack_level)?;
        if cases.insert(id, case).is_some() {
            return Err(pack_level(
                "duplicate User Settings compatibility case identity".into(),
            ));
        }
    }
    let scenarios = &context.pack.scenarios;
    let selected: Vec<Option<&Value>> = scenarios
        .iter()
        .filter(|scenario| scenario.action == "user-settings.open")
        .map(|scenario| scenario.expected.get("compatibilityCase"))
        .collect();
    let selected_ids: BTreeSet<&str> = selected
        .iter()
        .filter_map(|value| value.and_then(Value::as_str))
        .collect();
    let required: BTreeSet<&str> = cases
        .keys()
        .copied()
        .filter(|id| !MUTATING_CASES.contains(id))
        .collect();
    if selected_ids.len() != selected.len() || selected_ids != required {
        return Err(pack_level(
            "User Settings pack must cover every ordinary open compatibility case exactly once"
                .into(),
        ));
    }
    for (index, scenario) in scenarios.iter().enumerate() {
        if scenario.action != "user-settings.open" {
            continue;
        }
        let fail = |message: &str| (Some(index), message.to_owned());
        let reference = &scenario.expected;
        if reference.len() != 1 || !reference.contains_key("compatibilityCase") {
            return Err(fail(
                "User Settings expectations must reference a compatibilityCase",
            ));
        }
        let case_id = reference["compatibilityCase"].as_str().unwrap_or_default();
        let case = cases.get(case_id).ok_or_else(|| {
            (
                Some(index),
                format!("unknown User Settings compatibility case: {case_id}"),
            )
        })?;
        let located = |message: String| (Some(index), message);
        let view = view(root, case).map_err(located)?;
        let input = &scenario.input;
        if input.len() != 2
            || !input.contains_key("installationData")
            || !input.contains_key("observationFields")
        {
            return Err(fail(
                "User Settings open input must contain only installationData and observationFields",
            ));
        }
        let fields: Vec<&String> = view.keys().collect();
        if input["observationFields"] != json!(fields) {
            return Err(fail(
                "User Settings observationFields must exactly select the oracle view",
            ));
        }
        let fixture = member(case, "fixture").map_err(located)?;
        let installed = &input["installationData"];
        let source = member(case, "source").map_err(located)?;
        if fixture.is_null() {
            if truthy(installed) || !scenario.fixture_refs.is_empty() {
                return Err(fail("missing User Settings case cannot install a fixture"));
            }
        } else {
            let placement = installed
                .as_array()
                .and_then(|items| match items.as_slice() {
                    [item] => item.as_object(),
                    _ => None,
                })
                .filter(|item| {
                    item.len() == 2 && item.contains_key("fixtureRef") && item.contains_key("path")
                });
            let matches = placement.is_some_and(|item| {
                let alias = item["fixtureRef"].as_str().unwrap_or_default();
                Some(&item["path"]) == source.get("relative_path")
                    && oracle.fixtures.get(alias).map(|path| json!(path)).as_ref() == Some(fixture)
                    && scenario.fixture_refs == [alias]
            });
            if !matches {
                return Err(fail(
                    "User Settings installed input does not match its compatibility case",
                ));
            }
        }
        let present = !fixture.is_null();
        let classification = match text(source, "classification").map_err(located)? {
            "canonical_current"
            | "current"
            | "current_with_diagnostics"
            | "current_with_alias"
            | "current_with_unknown_entries" => "current",
            // This corpus case is the historical nested shape without
            // schema_version.
            "legacy_location" => "unversioned",
            "legacy_flat_shape" => "legacy_flat",
            "missing" => "missing",
            "malformed" => "malformed",
            "future_major" => "future_major",
            other => return Err(located(format!("unknown source classification {other}"))),
        };
        let eligibility = if truthy(member(case, "commit_eligible").map_err(located)?) {
            "eligible"
        } else if truthy(member(case, "migration_required").map_err(located)?) {
            "requires_migration"
        } else {
            "blocked_untrusted"
        };
        let location = match text(source, "location").map_err(located)? {
            "classic_root" => "canonical",
            "classic_data_directory" => "legacy",
            "none" => "missing",
            other => return Err(located(format!("unknown source location {other}"))),
        };
        let path = if present {
            json!({"path": member(source, "relative_path").map_err(located)?})
        } else {
            Value::Null
        };
        expected[index] = object_of(json!({
            "source": {"location": location, "path": path, "classification": classification},
            "commitEligibility": eligibility,
            "diagnostics": member(case, "diagnostics").map_err(located)?,
            "view": view,
            "durableEffects": {"treeUnchanged": true},
            "revision": {
                "kind": if present { "sha256" } else { "missing" },
                "matchesSourceBytes": true,
            },
            "originalContent": {"present": present, "matchesSourceBytes": true},
        }));
    }
    Ok(())
}

/// The open view a corpus case expects: its `expected_view`, or the view
/// built from the canonical defaults, overlaid with the degraded fallbacks
/// when the case uses them.
fn view(oracle: &Value, case: &Value) -> Result<Map<String, Value>, String> {
    let defaults_case = case.get("uses_canonical_defaults").is_some_and(truthy);
    let degraded_case = case.get("uses_degraded_fallbacks").is_some_and(truthy);
    if !defaults_case && !degraded_case {
        return match case.get("expected_view") {
            None => Ok(Map::new()),
            Some(view) => Ok(object(view, "expected_view")?.clone()),
        };
    }
    let defaults = member(member(oracle, "canonical_defaults")?, "CLASSIC_Settings")?;
    let fallbacks = member(member(oracle, "degraded_fallbacks")?, "CLASSIC_Settings")?;
    let mut view = Map::new();
    for (field, label) in DEFAULT_FIELDS {
        view.insert(field.into(), member(defaults, label)?.clone());
    }
    if degraded_case {
        for (field, label) in DEFAULT_FIELDS {
            if let Some(fallback) = fallbacks.get(label) {
                view.insert(field.into(), member(fallback, "value")?.clone());
            }
        }
    }
    Ok(view)
}

/// The expected installation tree after an operation step: the root
/// directory (when it exists), the settings document, and the commit lock.
fn tree(content: Option<&[u8]>, root_exists: bool, lock: bool) -> Vec<Value> {
    let mut tree = Vec::new();
    if root_exists {
        tree.push(json!({"path": {"path": "."}, "kind": "directory"}));
    }
    if let Some(content) = content {
        tree.push(
            json!({"path": {"path": SETTINGS}, "kind": "file", "bytesHex": digest::hex(content)}),
        );
    }
    if lock {
        tree.push(json!({"path": {"path": LOCK}, "kind": "file", "bytesHex": ""}));
    }
    tree
}

/// Compiles the `user-settings.update` scenarios from the corpus operations.
fn operations(
    oracle: &Oracle<'_>,
    context: &InputContext<'_>,
    expected: &mut [Map<String, Value>],
) -> Result<(), Failure> {
    let pack_level = |message: String| (None, message);
    let mut operations = BTreeMap::new();
    for operation in array(oracle.oracle, "operation_scenarios").map_err(pack_level)? {
        if operation.get("conformance").is_none() {
            continue;
        }
        if operations
            .insert(text(operation, "id").map_err(pack_level)?, operation)
            .is_some()
        {
            return Err(pack_level(
                "duplicate User Settings operation scenario identity".into(),
            ));
        }
    }
    let scenarios = &context.pack.scenarios;
    let selected: Vec<Option<&str>> = scenarios
        .iter()
        .filter(|scenario| scenario.action == "user-settings.update")
        .map(|scenario| {
            scenario
                .expected
                .get("operationScenario")
                .and_then(Value::as_str)
        })
        .collect();
    let selected_ids: BTreeSet<&str> = selected.iter().flatten().copied().collect();
    let wanted: BTreeSet<&str> = operations.keys().copied().collect();
    if selected_ids.len() != selected.len() || selected_ids != wanted {
        return Err(pack_level(
            "User Settings pack must cover every authored conformance operation exactly once"
                .into(),
        ));
    }
    let documents: BTreeSet<_> = expected_documents(oracle.oracle)
        .map_err(pack_level)?
        .iter()
        .map(|name| oracle_file(oracle.base, name))
        .collect::<Result<_, _>>()
        .map_err(pack_level)?;
    if context
        .fixture_paths(oracle.base)
        .iter()
        .any(|path| documents.contains(path))
    {
        return Err(pack_level(
            "User Settings expected documents cannot be adapter input fixtures".into(),
        ));
    }
    for (index, scenario) in scenarios.iter().enumerate() {
        if scenario.action != "user-settings.update" {
            continue;
        }
        let located = |message: String| (Some(index), message);
        if scenario.expected.len() != 1 {
            return Err(located(
                "User Settings operation expectations must reference an operationScenario".into(),
            ));
        }
        let operation = operations[selected_id(&scenario.expected)];
        expected[index] = operation_expectation(oracle, scenario, operation).map_err(located)?;
    }
    Ok(())
}

/// The `operationScenario` a validated update expectation names.
fn selected_id(expected: &Map<String, Value>) -> &str {
    expected["operationScenario"].as_str().unwrap_or_default()
}

/// Compiles one update scenario from its corpus operation.
fn operation_expectation(
    oracle: &Oracle<'_>,
    scenario: &crate::conformance::schema::Scenario,
    operation: &Value,
) -> Result<Map<String, Value>, String> {
    let config = member(operation, "conformance")?;
    let source_name = member(operation, "source_fixture")?;
    let disk_name = member(operation, "disk_fixture_before")?;
    let read = |name: &Value| -> Result<Option<Vec<u8>>, String> {
        match name {
            Value::Null => Ok(None),
            Value::String(name) => oracle.read(name).map(Some),
            _ => Err("operation fixtures must be file names or null".into()),
        }
    };
    let source = read(source_name)?;
    let disk = read(disk_name)?;
    let installation = match source_name.as_str() {
        None => json!([]),
        Some(name) => json!([{"fixtureRef": oracle.alias(name)?, "path": SETTINGS}]),
    };
    let external = if disk_name == source_name {
        Value::Null
    } else {
        let name = disk_name
            .as_str()
            .ok_or("an external edit needs a disk fixture")?;
        json!({"fixtureRef": oracle.alias(name)?, "path": SETTINGS})
    };
    let requested = member(operation, "requested_update")?;
    let expected_input = json!({
        "installationData": installation,
        "installationRootExists": member(config, "installation_root_exists")?,
        "previewMode": member(config, "preview_mode")?,
        "requestedUpdate": requested,
        "commit": member(config, "commit")?,
        "externalEdit": external,
    });
    let mut refs: Vec<&str> = installation
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|item| item["fixtureRef"].as_str())
        .collect();
    if let Some(alias) = external.get("fixtureRef").and_then(Value::as_str) {
        refs.push(alias);
    }
    if expected_input != Value::Object(scenario.input.clone())
        || scenario.fixture_refs != refs
        || Some(&json!(scenario.action)) != config.get("action")
        || scenario.capability_ids != ["user-settings.update"]
    {
        return Err("User Settings operation input does not match its independent oracle".into());
    }
    let requested = object(requested, "requested_update")?;
    let saves: Vec<&String> = requested
        .keys()
        .filter(|field| {
            field.starts_with(FORMID_DATABASE_SAVE_PREFIX)
                && field.len() > FORMID_DATABASE_SAVE_PREFIX.len()
        })
        .collect();
    let unknown = requested
        .keys()
        .any(|field| !UPDATE_FIELD_ORDER.contains(&field.as_str()) && !saves.contains(&field));
    if unknown || saves.len() > 1 {
        return Err("unsupported User Settings operation update selector".into());
    }
    // A game-aware save publishes a complete mapping that differs from its
    // request, so it must author the accepted values; raw field writes accept
    // exactly what they request.
    let accepted_values = match operation.get("expected_preview") {
        Some(preview) => object(preview, "expected_preview")?,
        None => requested,
    };
    if !saves.is_empty()
        && !(accepted_values.len() == 1 && accepted_values.contains_key(FORMID_DATABASES))
    {
        return Err("User Settings FormID database save must author its published mapping".into());
    }
    if saves.is_empty() && accepted_values != requested {
        return Err("User Settings field writes must accept exactly their requested values".into());
    }
    let (Some(commit), Some(root_exists)) = (
        member(config, "commit")?.as_bool(),
        member(config, "installation_root_exists")?.as_bool(),
    ) else {
        return Err("User Settings operation controls must be booleans".into());
    };
    if !matches!(
        member(config, "preview_mode")?.as_str(),
        Some("update" | "bootstrap")
    ) || config.get("action") != Some(&json!("user-settings.update"))
    {
        return Err(
            "User Settings operation must select an explicit supported preview mode".into(),
        );
    }
    let diagnostics = member(config, "preview_diagnostics")?;
    // Accepted previews may carry non-rejecting effect diagnostics, so the
    // authored outcome rather than an empty diagnostic list decides
    // acceptance.
    let accepted = operation.get("outcome") != Some(&json!("rejected_commit"));
    if !accepted && !truthy(diagnostics) {
        return Err("rejected User Settings operation must author its diagnostics".into());
    }
    let attempted = accepted && commit;
    let committed = attempted && truthy(member(operation, "writes_document")?);
    let accepted_fields: Vec<Value> = if accepted {
        UPDATE_FIELD_ORDER
            .iter()
            .filter_map(|field| {
                accepted_values
                    .get(*field)
                    .map(|value| json!({"fieldPath": field, "value": value}))
            })
            .collect()
    } else {
        Vec::new()
    };
    let conflict = attempted && !committed;
    let preview = json!({
        "status": if accepted { "accepted" } else { "rejected" },
        "baseRevision": if accepted { json!(revision(source.as_deref())) } else { Value::Null },
        "acceptedFields": accepted_fields,
        "diagnostics": diagnostics,
    });
    let commit_outcome = json!({
        "status": if committed { "committed" } else if attempted { "conflict" } else { "not-attempted" },
        "revision": if committed { json!({"matchesPublishedBytes": true}) } else { Value::Null },
        "expectedRevision": if conflict { json!(revision(source.as_deref())) } else { Value::Null },
        "actualRevision": if conflict { json!(revision(disk.as_deref())) } else { Value::Null },
        // A committed update reports the same effect diagnostics its preview
        // showed.
        "diagnostics": if committed { diagnostics.clone() } else { json!([]) },
    });
    let before = tree(source.as_deref(), root_exists, false);
    let mut after = tree(disk.as_deref(), root_exists || attempted, committed);
    if committed {
        let published = oracle.read(text(operation, "expected_document")?)?;
        let document = json!({
            "path": {"path": SETTINGS},
            "kind": "file",
            "yamlNodes": yaml_nodes(&published)?,
        });
        // A committed update always has the root directory first; the
        // document replaces the disk copy or precedes the lock.
        if disk.is_none() {
            after.insert(1, document);
        } else {
            after[1] = document;
        }
    }
    Ok(object_of(json!({
        "preview": preview,
        "afterPreviewTree": before,
        "commit": commit_outcome,
        "finalTree": after,
    })))
}

/// Compiles the `user-settings.legacy-import` scenarios: the restored
/// installation keeps the source bytes, content-addressed backups of both
/// documents and the commit lock.
fn legacy_import(
    oracle: &Oracle<'_>,
    context: &InputContext<'_>,
    expected: &mut [Map<String, Value>],
) -> Result<(), Failure> {
    const PREFIX: &str = "CLASSIC Backup/User Settings/TUI State Imports/";
    for (index, scenario) in context.pack.scenarios.iter().enumerate() {
        if scenario.action != "user-settings.legacy-import" {
            continue;
        }
        let located = |message: String| (Some(index), message);
        if Value::Object(scenario.expected.clone())
            != json!({"legacyImportCase": "restore-existing"})
        {
            return Err(located("unsupported legacy import expectation".into()));
        }
        let placements = scenario
            .input
            .get("installationData")
            .and_then(Value::as_array);
        let mut contents = BTreeMap::new();
        for placement in placements.into_iter().flatten() {
            let (Some(path), Some(alias)) = (
                placement.get("path").and_then(Value::as_str),
                placement.get("fixtureRef").and_then(Value::as_str),
            ) else {
                return Err(located(
                    "legacy import placements need a path and fixtureRef".into(),
                ));
            };
            let name = oracle
                .fixtures
                .get(alias)
                .ok_or_else(|| located(format!("legacy import fixture {alias} is not declared")))?;
            contents.insert(path.to_owned(), oracle.read(name).map_err(located)?);
        }
        let (Some(original), Some(source)) = (
            contents.get(SETTINGS).cloned(),
            contents.get("state.json").cloned(),
        ) else {
            return Err(located(
                "legacy import fixture placements are incomplete".into(),
            ));
        };
        if contents.len() != 2 {
            return Err(located(
                "legacy import fixture placements are incomplete".into(),
            ));
        }
        let backup = format!("{PREFIX}{}.json", digest::sha256_hex(&source));
        let settings_backup = format!("{PREFIX}{}.yaml", digest::sha256_hex(&original));
        contents.insert(backup.clone(), source);
        contents.insert(settings_backup.clone(), original);
        contents.insert(LOCK.to_owned(), Vec::new());
        let files: Vec<Value> = contents
            .iter()
            .map(|(path, bytes)| json!({"path": path, "bytesHex": digest::hex(bytes)}))
            .collect();
        expected[index] = object_of(json!({
            "import": {
                "status": "applied",
                "sourcePath": "state.json",
                "backupPath": backup,
                "settingsPath": SETTINGS,
                "settingsBackupPath": settings_backup,
                "sourceRevisionMatches": true,
                "backupRevisionMatches": true,
                "baseRevisionMatches": true,
                "publishedRevisionMatches": true,
                "inapplicable": {
                    "classification": null,
                    "revision": null,
                    "expectedRevision": null,
                    "actualRevision": null,
                },
                "tui": {
                    "activeTab": 2,
                    "resultsPanelWidth": 42,
                    "sortAscending": true,
                    "origins": ["document", "document", "document"],
                },
            },
            "restore": {
                "status": "restored",
                "revisionMatches": true,
                "expectedRevision": null,
                "actualRevision": null,
            },
            "files": files,
        }));
    }
    Ok(())
}

/// Normalizes a non-open observation before exact comparison.
///
/// Migrations (an expectation with `planning`) go to the migration
/// normalizer. A committed update must carry its published document as raw
/// bytes (`{path, kind: "file", bytesHex}`) whose revision equals the
/// reported commit revision; the bytes become YAML nodes and the revision
/// becomes `{"matchesPublishedBytes": true}`. Everything else stays exact.
///
/// # Errors
///
/// Fails (at `$.finalTree`) when a committed observation lacks exactly one
/// raw settings document, its bytes are not lowercase hexadecimal YAML, or
/// the reported revision does not match them.
pub(super) fn normalize(
    expected: &Map<String, Value>,
    actual: &Map<String, Value>,
) -> Result<Map<String, Value>, NormalizationError> {
    if expected.contains_key("planning") {
        return user_settings_migration::normalize(expected, actual);
    }
    let committed = expected
        .get("commit")
        .and_then(|commit| commit.get("status"))
        == Some(&json!("committed"));
    if !committed {
        return Ok(actual.clone());
    }
    let mut result = actual.clone();
    committed_document(&mut result)
        .map_err(|message| NormalizationError::new(message, "$.finalTree"))?;
    Ok(result)
}

/// Authenticates and normalizes the published document of a committed
/// update observation in place.
fn committed_document(result: &mut Map<String, Value>) -> Result<(), String> {
    let tree = result
        .get_mut("finalTree")
        .and_then(Value::as_array_mut)
        .filter(|tree| tree.iter().all(Value::is_object))
        .ok_or("committed observation tree must contain file or directory objects")?;
    let mut documents = tree
        .iter_mut()
        .filter(|entry| entry.get("path") == Some(&json!({"path": SETTINGS})));
    let (Some(document), None) = (documents.next(), documents.next()) else {
        return Err("committed observation must contain one canonical document".into());
    };
    if !super::has_exact_keys(document, &["path", "kind", "bytesHex"]) || document["kind"] != "file"
    {
        return Err("committed document requires a raw regular-file byte observation".into());
    }
    let content = document["bytesHex"]
        .as_str()
        .and_then(decode_hex)
        .ok_or("committed document bytes must be lowercase hexadecimal")?;
    let document = document.as_object_mut().expect("checked object");
    document.remove("bytesHex");
    document.insert("yamlNodes".into(), yaml_nodes(&content)?);
    let commit = result
        .get_mut("commit")
        .and_then(Value::as_object_mut)
        .ok_or("committed observation must report its commit")?;
    if commit.get("revision") != Some(&json!(revision(Some(&content)))) {
        return Err("committed revision does not match observed published bytes".into());
    }
    commit.insert("revision".into(), json!({"matchesPublishedBytes": true}));
    Ok(())
}

/// Python truthiness of a JSON value: `null`, `false`, `0`, `""`, `[]` and
/// `{}` are false. The retired oracle tested several corpus members this way.
pub(super) fn truthy(value: &Value) -> bool {
    match value {
        Value::Null => false,
        Value::Bool(flag) => *flag,
        Value::Number(number) => number.as_f64() != Some(0.0),
        Value::String(text) => !text.is_empty(),
        Value::Array(items) => !items.is_empty(),
        Value::Object(members) => !members.is_empty(),
    }
}

/// The member `key` of an oracle object.
pub(super) fn member<'a>(value: &'a Value, key: &str) -> Result<&'a Value, String> {
    value
        .get(key)
        .ok_or_else(|| format!("oracle entry lacks {key}"))
}

/// The string member `key` of an oracle object.
pub(super) fn text<'a>(value: &'a Value, key: &str) -> Result<&'a str, String> {
    member(value, key)?
        .as_str()
        .ok_or_else(|| format!("oracle member {key} must be a string"))
}

/// The array member `key` of an oracle object.
pub(super) fn array<'a>(value: &'a Value, key: &str) -> Result<&'a Vec<Value>, String> {
    member(value, key)?
        .as_array()
        .ok_or_else(|| format!("oracle member {key} must be an array"))
}

/// `value` as an object, or an error naming `label`.
pub(super) fn object<'a>(value: &'a Value, label: &str) -> Result<&'a Map<String, Value>, String> {
    value
        .as_object()
        .ok_or_else(|| format!("{label} must be an object"))
}

/// The object a `json!` object literal built.
pub(super) fn object_of(value: Value) -> Map<String, Value> {
    match value {
        Value::Object(map) => map,
        _ => unreachable!("built from an object literal"),
    }
}

#[cfg(test)]
#[path = "user_settings_oracle_tests.rs"]
mod tests;
