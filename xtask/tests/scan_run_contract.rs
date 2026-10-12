//! Fixture-tree tests for `cargo xtask scan-run-contract`, driven through
//! `scan_run_contract::run` (the subcommand seam).
//!
//! Each test starts from a consistent tree generated from the compiled variant
//! policy (manifest, Rust enums, conformance pack, fixture files, export
//! surfaces), seeds one or more violations, and asserts the findings.

mod common;

use std::collections::BTreeMap;
use std::process::Command;

use common::FixtureRepo;
use serde_json::{Value, json};
use xtask::scan_run_contract::variant_policy::{Evidence, TARGETS};
use xtask::{Outcome, RepoRoot, scan_run_contract};

const MANIFEST: &str = "tests/fixtures/crash_log_scan_run/manifest.json";
const PACK: &str = "tests/conformance/packs/crash_log_scan_run/v1.json";
const POLICY: &str = "xtask/src/scan_run_contract/variant_policy.rs";
const CONTRACT_RS: &str = "src/contract.rs";
const BRIDGE_RS: &str = "src/bridge.rs";

/// Clean `src/bridge.rs`: `orchestrator_new` is forbidden, but the longer
/// `orchestrator_new_minimal` name on line 2 must not match it.
const CLEAN_BRIDGE: &str = "// bridge\nfn orchestrator_new_minimal() {}\n";

/// The editable inputs of one fixture tree.
struct Inputs {
    manifest: Value,
    /// Generated Rust source holding one enum per variant category.
    contract_rs: String,
    /// Scenario IDs written to the crash-log-scan-run pack.
    scenarios: Vec<String>,
    bridge_rs: String,
}

/// `cancelled_before_discovery` -> `CancelledBeforeDiscovery`.
fn pascal(snake: &str) -> String {
    snake
        .split('_')
        .map(|part| {
            let mut chars = part.chars();
            chars
                .next()
                .map(|first| first.to_ascii_uppercase().to_string() + chars.as_str())
                .unwrap_or_default()
        })
        .collect()
}

/// A tree that satisfies every check: the manifest's `contractVariants` are the
/// policy's variants, each category has a matching Rust enum, the pack holds
/// every scenario the policy names, and the failure fixtures cover every stage.
fn clean() -> Inputs {
    let variants: Vec<&str> = TARGETS.iter().map(|target| target.variant).collect();
    let mut by_category: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for variant in &variants {
        let (category, name) = variant.split_once('.').expect("category.name");
        by_category.entry(category).or_default().push(name);
    }

    let mut contract_rs = String::from("//! Generated scan-run contract enums.\n");
    let mut rust_enums = Vec::new();
    for (category, names) in &by_category {
        let enum_name = pascal(category);
        contract_rs.push_str(&format!("\npub enum {enum_name} {{\n"));
        for name in names {
            contract_rs.push_str(&format!("    /// Variant docs.\n    {},\n", pascal(name)));
        }
        contract_rs.push_str("}\n");
        rust_enums.push(json!({"category": category, "path": CONTRACT_RS, "name": enum_name}));
    }
    // A surviving name that shares a forbidden identifier's prefix.
    contract_rs.push_str("\npub fn scan_run_contract_execute() {}\n");

    let stages = |prefix: &str| -> Vec<String> {
        variants
            .iter()
            .filter_map(|variant| variant.strip_prefix(prefix).map(str::to_owned))
            .collect()
    };
    let log_failures: Vec<Value> = stages("log_failure_stage.")
        .into_iter()
        .map(|stage| json!({"stage": stage, "message": format!("shared {stage} failure")}))
        .collect();
    let infrastructure_errors: Vec<Value> = stages("infrastructure_error_stage.")
        .into_iter()
        .map(|stage| {
            json!({"stage": stage, "rawMessage": "raw", "message": "Error: raw", "path": null})
        })
        .collect();

    let mut scenarios: Vec<String> = TARGETS
        .iter()
        .filter_map(|target| match target.evidence {
            Evidence::Runtime { scenario_id } => Some(scenario_id.to_owned()),
            Evidence::Retained { .. } => None,
        })
        .collect();
    scenarios.sort();
    scenarios.dedup();

    let manifest = json!({
        "schemaVersion": 1,
        "description": "fixture",
        "fixtureRoot": "tests/fixtures/crash_log_scan_run",
        "fixtureFiles": ["tests/fixtures/crash_log_scan_run/valid-crash.log"],
        "fixtures": {
            "installedYamlData": {
                "expectedRecoveryRequired": {
                    "mainProvenance": "bundled",
                    "gameProvenance": "bundled",
                    "localIgnoreState": "recovery_required",
                    "diagnosticKinds": ["parse"]
                },
                "expectedResetToDefault": {
                    "mainProvenance": "bundled",
                    "gameProvenance": "bundled",
                    "localIgnoreState": "reset_to_default",
                    "diagnosticKinds": ["parse", "local_ignore_reset"]
                },
                "resetOutcomes": {
                    "conflictCode": "local_ignore_reset_conflict",
                    "backupFailureCode": "local_ignore_reset_backup_failure",
                    "replacementFailureCode": "local_ignore_reset_replacement_failure",
                    "durabilityUnknownCode": "local_ignore_reset_durability_unknown",
                    "consumedCode": "scan_run_continuation_consumed",
                    "backupMustEqualMalformedBytes": true,
                    "reportMustEqualExistingBytes": true,
                    "preResetCancellationMutates": false,
                    "postCriticalCancellationStatus": "cancelled"
                }
            }
        },
        "failureFixtures": {
            "logResult": {"failures": log_failures},
            "infrastructureErrors": infrastructure_errors
        },
        "rustEnums": rust_enums,
        "contractVariants": variants,
        "supportedAdapters": ["rust", "cxx"],
        "forbiddenExports": {
            "rust": [{"path": CONTRACT_RS, "symbols": ["scan_run_execute", "pub fn continuation"]}],
            "cxx": [
                {"path": BRIDGE_RS, "symbols": ["orchestrator_new"]},
                {"path": "include/legacy.h", "symbols": ["BatchProgressEvent"], "optional": true}
            ]
        }
    });

    Inputs {
        manifest,
        contract_rs,
        scenarios,
        bridge_rs: CLEAN_BRIDGE.to_owned(),
    }
}

impl Inputs {
    /// Writes the inputs (plus the fixture log) into a fresh temp tree.
    fn write(&self) -> FixtureRepo {
        let pack = json!({
            "familyId": "crash-log-scan-run",
            "scenarios": self.scenarios.iter().map(|id| json!({"id": id})).collect::<Vec<_>>()
        });
        FixtureRepo::empty()
            .file(
                MANIFEST,
                &serde_json::to_string_pretty(&self.manifest).unwrap(),
            )
            .file(PACK, &serde_json::to_string_pretty(&pack).unwrap())
            .file(CONTRACT_RS, &self.contract_rs)
            .file(BRIDGE_RS, &self.bridge_rs)
            .file("tests/fixtures/crash_log_scan_run/valid-crash.log", "log\n")
    }

    /// Mutable access to the manifest value at a JSON pointer.
    fn at(&mut self, pointer: &str) -> &mut Value {
        self.manifest
            .pointer_mut(pointer)
            .unwrap_or_else(|| panic!("fixture manifest has {pointer}"))
    }
}

/// Runs the contract over `root` and returns its findings rendered as
/// `path:line: rule: message` lines (empty on a pass).
fn findings_at(root: &RepoRoot) -> Vec<String> {
    match scan_run_contract::run(root, scan_run_contract::Args::default()).expect("contract runs") {
        Outcome::Pass { .. } => Vec::new(),
        Outcome::Fail { findings, .. } => findings.iter().map(ToString::to_string).collect(),
    }
}

fn findings(inputs: &Inputs) -> Vec<String> {
    findings_at(&inputs.write().root())
}

/// Replaces the `:<line>:` of a rendered finding with `:_:`, for findings whose
/// line is an artefact of how the fixture JSON or the policy table is laid out.
fn any_line(finding: &str) -> String {
    let (path, rest) = finding.split_once(':').expect("path:line");
    let (_, rest) = rest.split_once(':').expect("line:rule");
    format!("{path}:_:{rest}")
}

/// Line-agnostic findings, sorted, so tests do not depend on how the fixture
/// JSON happens to order its keys.
fn any_lines(findings: &[String]) -> Vec<String> {
    let mut lines: Vec<String> = findings.iter().map(|finding| any_line(finding)).collect();
    lines.sort();
    lines
}

#[test]
fn a_consistent_tree_passes() {
    assert_eq!(findings(&clean()), Vec::<String>::new());
}

#[test]
fn the_live_repository_passes() {
    let root = RepoRoot::discover(None).expect("live root");
    assert_eq!(findings_at(&root), Vec::<String>::new());
}

#[test]
fn rust_enum_variants_must_match_the_manifest_in_both_directions() {
    let mut inputs = clean();
    // Point `event` at its own file: one unregistered variant (line 4) and
    // `LogPhase` gone, which leaves `event.log_phase` stale in the manifest.
    let event = "pub enum Event {\n    DiscoveryCompleted(u8),\n    EffectiveConcurrencySelected { n: u8 },\n    \
                 AdapterForgottenVariant,\n    LogQueued,\n    LogStarted,\n    LogFinished,\n}\n";
    let entry = inputs.manifest["rustEnums"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|entry| entry["category"] == "event")
        .unwrap();
    entry["path"] = json!("src/event.rs");
    let repo = inputs.write().file("src/event.rs", event);

    let found = findings_at(&repo.root());

    assert_eq!(
        any_lines(&found),
        [
            "src/event.rs:_: rust-enum-mismatch: Rust enum Event does not match the manifest: unregistered event.adapter_forgotten_variant".to_owned(),
            format!("{MANIFEST}:_: rust-enum-mismatch: Rust enum Event does not match the manifest: stale event.log_phase"),
        ]
    );
    // The unregistered finding points at the variant itself.
    assert!(found[0].starts_with("src/event.rs:4: "), "{found:?}");
}

#[test]
fn a_renamed_variant_maps_through_renames_and_stale_renames_fail() {
    let mut inputs = clean();
    inputs.contract_rs = inputs
        .contract_rs
        .replace("    FormidDatabaseAccess,", "    FormIdDatabaseAccess,");
    let without_rename = findings(&inputs);
    assert_eq!(
        any_lines(&without_rename),
        [
            "src/contract.rs:_: rust-enum-mismatch: Rust enum InfrastructureErrorStage does not match the manifest: unregistered infrastructure_error_stage.form_id_database_access".to_owned(),
            format!("{MANIFEST}:_: rust-enum-mismatch: Rust enum InfrastructureErrorStage does not match the manifest: stale infrastructure_error_stage.formid_database_access"),
        ]
    );

    let entry = inputs.manifest["rustEnums"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|entry| entry["category"] == "infrastructure_error_stage")
        .unwrap();
    entry["renames"] = json!({"FormIdDatabaseAccess": "formid_database_access", "Gone": "gone"});
    assert_eq!(
        any_lines(&findings(&inputs)),
        [format!(
            "{MANIFEST}:_: rust-enum-mismatch: Rust enum InfrastructureErrorStage has stale renames: Gone"
        )]
    );
}

#[test]
fn a_missing_enum_or_unreadable_enum_source_fails() {
    let mut inputs = clean();
    let entries = inputs.manifest["rustEnums"].as_array_mut().unwrap();
    entries[0]["name"] = json!("NoSuchEnum");
    entries[1]["path"] = json!("src/missing.rs");
    let found = any_lines(&findings(&inputs));
    // Neither enum can be compared, so neither reports stale variants.
    assert_eq!(found.len(), 2, "{found:?}");
    assert!(found.contains(&format!(
        "{MANIFEST}:_: rust-enum-mismatch: Rust enum NoSuchEnum was not found in src/contract.rs"
    )));
    assert!(
        found.iter().any(|f| f.starts_with(&format!(
            "{MANIFEST}:_: rust-enum-mismatch: Cannot read Rust enum source src/missing.rs: "
        ))),
        "{found:?}"
    );
}

#[test]
fn a_missing_failure_fixture_stage_fails() {
    let mut inputs = clean();
    inputs
        .at("/failureFixtures/logResult/failures")
        .as_array_mut()
        .unwrap()
        .pop();
    inputs
        .at("/failureFixtures/infrastructureErrors")
        .as_array_mut()
        .unwrap()
        .pop();

    assert_eq!(
        any_lines(&findings(&inputs)),
        [
            format!(
                "{MANIFEST}:_: failure-fixture: shared infrastructure failure stages differ: missing infrastructure_error_stage.internal_invariant"
            ),
            format!(
                "{MANIFEST}:_: failure-fixture: shared log failure stages differ: missing log_failure_stage.unsolved_logs_finalization"
            ),
        ]
    );
}

#[test]
fn a_malformed_failure_fixture_fails() {
    let mut inputs = clean();
    inputs.at("/failureFixtures/logResult/failures/0")["message"] = json!("");
    inputs.at("/failureFixtures/infrastructureErrors/0")["path"] = json!(7);

    let found = any_lines(&findings(&inputs));

    assert!(found.contains(&format!(
        "{MANIFEST}:_: failure-fixture: log failure fixtures require string stage and non-empty message"
    )), "{found:?}");
    assert!(found.contains(&format!(
        "{MANIFEST}:_: failure-fixture: infrastructure failure fixture path must be a string or null"
    )), "{found:?}");
}

#[test]
fn a_missing_reset_fixture_fails() {
    let mut inputs = clean();
    inputs.manifest["fixtures"]
        .as_object_mut()
        .unwrap()
        .remove("installedYamlData");
    assert_eq!(
        any_lines(&findings(&inputs)),
        [format!(
            "{MANIFEST}:_: reset-fixture: fixtures.installedYamlData must be an object"
        )]
    );
}

#[test]
fn every_reset_outcome_and_semantic_is_checked() {
    let mut inputs = clean();
    let outcomes = inputs
        .at("/fixtures/installedYamlData/resetOutcomes")
        .as_object_mut()
        .unwrap();
    outcomes.remove("durabilityUnknownCode");
    outcomes.remove("replacementFailureCode");
    outcomes.insert("preResetCancellationMutates".into(), json!(true));
    inputs.at("/fixtures/installedYamlData/expectedResetToDefault")["localIgnoreState"] =
        json!("existing");
    inputs.at("/fixtures/installedYamlData/expectedResetToDefault")["gameProvenance"] =
        json!("updated");
    inputs.at("/fixtures/installedYamlData/expectedResetToDefault")["diagnosticKinds"] =
        json!(["parse"]);

    let found = any_lines(&findings(&inputs));

    let prefix = format!("{MANIFEST}:_: reset-fixture: fixtures.installedYamlData.");
    let mut expected = vec![
        format!(
            "{prefix}expectedResetToDefault.diagnosticKinds must be [\"local_ignore_reset\", \"parse\"] (in any order)"
        ),
        format!(
            "{prefix}expectedResetToDefault.gameProvenance must retain expectedRecoveryRequired.gameProvenance"
        ),
        format!("{prefix}expectedResetToDefault.localIgnoreState must be \"reset_to_default\""),
        format!(
            "{prefix}resetOutcomes.durabilityUnknownCode must be \"local_ignore_reset_durability_unknown\""
        ),
        format!("{prefix}resetOutcomes.preResetCancellationMutates must be false"),
        format!(
            "{prefix}resetOutcomes.replacementFailureCode must be \"local_ignore_reset_replacement_failure\""
        ),
    ];
    expected.sort();
    assert_eq!(found, expected);
}

#[test]
fn a_missing_fixture_root_or_fixture_file_fails() {
    let mut inputs = clean();
    inputs.manifest["fixtureRoot"] = json!("tests/fixtures/missing");
    inputs
        .at("/fixtureFiles")
        .as_array_mut()
        .unwrap()
        .push(json!("tests/fixtures/gone.log"));
    assert_eq!(
        any_lines(&findings(&inputs)),
        [
            format!(
                "{MANIFEST}:_: fixture-files: Shared fixture file is missing: tests/fixtures/gone.log"
            ),
            format!(
                "{MANIFEST}:_: reset-fixture: fixtureRoot directory is missing: tests/fixtures/missing"
            ),
        ]
    );

    inputs.manifest["fixtureRoot"] = json!("../outside");
    assert!(
        findings(&inputs)
            .iter()
            .any(|f| f.ends_with("reset-fixture: fixtureRoot must remain within the repository")),
    );
}

#[test]
fn a_forbidden_export_fails_at_the_line_that_names_it() {
    let mut inputs = clean();
    inputs.bridge_rs = format!("{CLEAN_BRIDGE}\nfn orchestrator_new() {{}}\n");
    inputs.contract_rs.push_str("pub fn continuation() {}\n");
    let contract_lines = inputs.contract_rs.lines().count();

    assert_eq!(
        findings(&inputs),
        [
            "src/bridge.rs:4: forbidden-export: cxx src/bridge.rs still contains `orchestrator_new`".to_owned(),
            format!("src/contract.rs:{contract_lines}: forbidden-export: rust src/contract.rs still contains `pub fn continuation`"),
        ]
    );
}

#[test]
fn a_missing_required_export_surface_fails_but_an_optional_one_is_skipped() {
    let mut inputs = clean();
    inputs.at("/forbiddenExports/cxx/0")["path"] = json!("src/renamed_bridge.rs");
    assert_eq!(
        any_lines(&findings(&inputs)),
        [format!(
            "{MANIFEST}:_: forbidden-export: Cannot read cxx forbidden-export surface src/renamed_bridge.rs"
        )]
    );
}

#[test]
fn forbidden_exports_must_cover_exactly_the_supported_adapters() {
    let mut inputs = clean();
    inputs.manifest["supportedAdapters"] = json!(["rust", "cxx", "tui"]);
    assert_eq!(
        any_lines(&findings(&inputs)),
        [format!(
            "{MANIFEST}:_: forbidden-export: forbiddenExports must exactly match supportedAdapters (missing tui)"
        )]
    );
}

#[test]
fn variant_evidence_is_keyed_on_pack_scenario_ids() {
    let mut inputs = clean();
    // `fcx-setup-failed` is the only evidence for `run_status.setup_failed`.
    inputs.scenarios.retain(|id| id != "fcx-setup-failed");

    assert_eq!(
        any_lines(&findings(&inputs)),
        [format!(
            "{POLICY}:_: variant-evidence: variant run_status.setup_failed references scenario \
             'fcx-setup-failed', which is not a scenario in {PACK}"
        )]
    );
}

#[test]
fn a_manifest_variant_without_policy_evidence_fails() {
    let mut inputs = clean();
    // Registered in the manifest and the Rust enum, but absent from the policy.
    inputs.contract_rs = inputs.contract_rs.replace(
        "pub enum Event {\n",
        "pub enum Event {\n    AdapterForgottenVariant,\n",
    );
    inputs
        .at("/contractVariants")
        .as_array_mut()
        .unwrap()
        .push(json!("event.adapter_forgotten_variant"));

    assert_eq!(
        any_lines(&findings(&inputs)),
        [format!(
            "{MANIFEST}:_: variant-evidence: variant evidence policy differs: missing event.adapter_forgotten_variant \
             (add it to {POLICY})"
        )]
    );
}

#[test]
fn a_policy_variant_missing_from_the_manifest_fails() {
    let mut inputs = clean();
    inputs.contract_rs = inputs.contract_rs.replace("    LogPhase,\n", "");
    inputs
        .at("/contractVariants")
        .as_array_mut()
        .unwrap()
        .retain(|v| v != "event.log_phase");

    assert_eq!(
        any_lines(&findings(&inputs)),
        [format!(
            "{POLICY}:_: variant-evidence: variant evidence policy differs: stale event.log_phase"
        )]
    );
}

#[test]
fn every_finding_is_collected_in_one_run() {
    let mut inputs = clean();
    inputs.contract_rs = inputs.contract_rs.replace(
        "pub enum Event {\n",
        "pub enum Event {\n    AdapterForgottenVariant,\n",
    );
    inputs
        .at("/failureFixtures/logResult/failures")
        .as_array_mut()
        .unwrap()
        .pop();
    inputs
        .at("/fixtures/installedYamlData/resetOutcomes")
        .as_object_mut()
        .unwrap()
        .remove("consumedCode");
    inputs.scenarios.retain(|id| id != "fcx-setup-failed");
    inputs.bridge_rs.push_str("fn orchestrator_new() {}\n");

    let rules: Vec<String> = findings(&inputs)
        .iter()
        .map(|finding| finding.split(": ").nth(1).unwrap().to_owned())
        .collect();

    let mut sorted = rules.clone();
    sorted.sort();
    assert_eq!(
        sorted,
        [
            "failure-fixture",
            "forbidden-export",
            "reset-fixture",
            "rust-enum-mismatch",
            "variant-evidence"
        ]
    );
}

#[test]
fn schema_version_and_variant_list_shape_are_checked() {
    let mut inputs = clean();
    inputs.manifest["schemaVersion"] = json!(2);
    inputs
        .at("/contractVariants")
        .as_array_mut()
        .unwrap()
        .push(json!("event.log_phase"));
    let found = any_lines(&findings(&inputs));
    assert_eq!(
        found,
        [
            format!("{MANIFEST}:_: manifest-shape: contractVariants contains duplicates"),
            format!("{MANIFEST}:_: manifest-shape: schemaVersion must be 1"),
        ]
    );
}

#[test]
fn an_unparseable_manifest_is_an_operational_error() {
    let repo = FixtureRepo::empty().file(MANIFEST, "{ not json");
    let error = scan_run_contract::run(&repo.root(), scan_run_contract::Args::default())
        .expect_err("unparseable manifest");
    assert!(format!("{error:#}").contains("manifest.json"), "{error:#}");
}

#[test]
fn the_binary_reports_findings_on_stderr_and_exits_1() {
    let mut inputs = clean();
    inputs.scenarios.retain(|id| id != "fcx-setup-failed");
    let repo = inputs.write();

    let output = Command::new(env!("CARGO_BIN_EXE_xtask"))
        .args([
            "--repo-root",
            repo.path().to_str().unwrap(),
            "scan-run-contract",
        ])
        .output()
        .expect("run the xtask binary");

    assert_eq!(output.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&output.stderr).replace("\r\n", "\n");
    let lines: Vec<&str> = stderr.lines().collect();
    assert_eq!(lines.len(), 2, "{stderr}");
    assert!(lines[0].starts_with(&format!("{POLICY}:")), "{stderr}");
    assert_eq!(
        lines[1],
        "scan-run-contract: 1 finding(s) in the Crash Log Scan Run contract"
    );
}
