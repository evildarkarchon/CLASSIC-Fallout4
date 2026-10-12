//! `cargo xtask conformance check` over fixture repositories: packs,
//! `participants.json` and the consumer obligation catalog, plus the real
//! repository (clean and seeded) end to end.

mod common;

use std::process::Command;

use common::conformance::{
    OBLIGATIONS, PACK, PARTICIPANTS, check, demo_obligations, demo_pack, demo_participants,
    demo_repo, input_findings, real_inputs, real_root,
};
use serde_json::{Value, json};
use xtask::RepoRoot;
use xtask::conformance::{ExecutionKey, required_executions};

/// Findings for the demo repository after `mutate` edits one of its documents.
fn demo_findings(mutate: impl FnOnce(&mut Value, &mut Value, &mut Value)) -> Vec<String> {
    let (mut pack, mut participants, mut obligations) =
        (demo_pack(), demo_participants(), demo_obligations());
    mutate(&mut pack, &mut participants, &mut obligations);
    input_findings(&demo_repo(&pack, &participants, &obligations))
}

/// Asserts exactly one finding, in `file` under `rule`, mentioning `text`.
#[track_caller]
fn assert_single(findings: &[String], file: &str, rule: &str, text: &str) {
    assert_eq!(findings.len(), 1, "{findings:#?}");
    let finding = &findings[0];
    assert!(
        finding.starts_with(&format!("{file}:"))
            && finding.contains(&format!(": {rule}: "))
            && finding.contains(text),
        "expected {file} {rule} {text:?}, got {finding}"
    );
}

#[test]
fn a_clean_demo_repository_has_no_input_findings() {
    assert_eq!(demo_findings(|_, _, _| {}), Vec::<String>::new());
}

#[test]
fn the_demo_requirement_covers_rust_cxx_and_the_consumer() {
    let repo = demo_repo(&demo_pack(), &demo_participants(), &demo_obligations());
    let required = required_executions(&repo.root()).expect("clean inputs");
    let keys: Vec<(&str, &str)> = required
        .iter()
        .map(|key| (key.participant_id.as_str(), key.instance_id.as_str()))
        .collect();
    assert_eq!(
        keys,
        [
            ("cxx", "windows-clang-cl"),
            ("cxx", "windows-msvc"),
            ("rust", "rust"),
            ("tui", "tui")
        ]
    );
    assert!(required.contains(&ExecutionKey::new("demo", "rust", "rust")));
}

#[test]
fn strict_json_rejects_floats_and_duplicate_keys_with_their_line() {
    let repo = demo_repo(&demo_pack(), &demo_participants(), &demo_obligations()).replace(
        PACK,
        "\"familyVersion\": 1",
        "\"familyVersion\": 1.0",
    );
    let findings = input_findings(&repo);
    assert_single(
        &findings,
        PACK,
        "invalid-json",
        "floating-point JSON value is forbidden",
    );
    let text = std::fs::read_to_string(repo.path().join(PACK)).unwrap();
    let line = text
        .lines()
        .position(|line| line.contains("familyVersion"))
        .unwrap()
        + 1;
    assert!(
        findings[0].starts_with(&format!("{PACK}:{line}:")),
        "{findings:#?}"
    );

    let repo = demo_repo(&demo_pack(), &demo_participants(), &demo_obligations()).replace(
        PACK,
        "\"familyVersion\": 1,",
        "\"familyVersion\": 1,\n  \"familyVersion\": 1,",
    );
    assert_single(
        &input_findings(&repo),
        PACK,
        "invalid-json",
        "duplicate JSON object key",
    );
}

#[test]
fn the_closed_pack_shape_rejects_unknown_members() {
    let findings =
        demo_findings(|pack, _, _| pack["capabilities"][0]["operationScoped"] = json!(true));
    assert_single(
        &findings,
        PACK,
        "pack-schema",
        "unknown field `operationScoped`",
    );
}

#[test]
fn identities_must_be_stable_and_actions_must_be_own_capabilities() {
    let findings =
        demo_findings(|pack, _, _| pack["scenarios"][0]["action"] = json!("demo.missing"));
    assert!(
        findings
            .iter()
            .any(|f| f.contains(": pack-identity: ")
                && f.contains("must be one of its capabilityIds")),
        "{findings:#?}"
    );

    let findings =
        demo_findings(|pack, _, _| pack["domainOwner"]["rustCrate"] = json!("Classic_Demo"));
    assert_single(
        &findings,
        PACK,
        "pack-identity",
        "stable machine identifier",
    );
}

#[test]
fn fixtures_must_stay_beneath_the_fixture_root() {
    let findings = demo_findings(|pack, _, _| pack["fixtures"]["one"] = json!("../demo/one.json"));
    assert!(
        findings
            .iter()
            .any(|f| f.contains(": pack-fixture: ") && f.contains("canonical relative path")),
        "{findings:#?}"
    );
    let findings = demo_findings(|pack, _, _| pack["fixtures"]["one"] = json!("missing.json"));
    assert_single(
        &findings,
        PACK,
        "pack-fixture",
        "existing file beneath fixtureRoot",
    );
}

#[test]
fn inputs_are_fixture_references_only() {
    let findings =
        demo_findings(|pack, _, _| pack["scenarios"][0]["input"]["mode"] = json!("fast"));
    assert_single(
        &findings,
        PACK,
        "pack-input",
        "input must be exactly {\"fixtureRef\": <ref>}",
    );

    let findings = demo_findings(|pack, _, _| {
        pack["scenarios"][0]["input"] = json!({"fixtureRef": "one", "expected": {"value": 2}});
    });
    assert!(
        findings.iter().any(|f| f.contains("carries result data")),
        "{findings:#?}"
    );
    assert!(
        findings
            .iter()
            .any(|f| f.contains("contains the scenario's expected observation")),
        "{findings:#?}"
    );
}

#[test]
fn fixtures_must_not_carry_the_expected_result() {
    let repo = demo_repo(&demo_pack(), &demo_participants(), &demo_obligations()).json(
        "tests/fixtures/demo/one.json",
        &json!({"request": {"value": 1}, "answer": {"value": 2}}),
    );
    assert_single(
        &input_findings(&repo),
        PACK,
        "pack-input",
        "fixture one contains the scenario's expected observation",
    );
}

#[test]
fn normalization_paths_must_be_exact() {
    let findings = demo_findings(|pack, _, _| {
        pack["scenarios"][0]["normalization"]["unorderedPaths"] = json!(["$..value"]);
    });
    assert_single(&findings, PACK, "pack-normalization", "exact JSON path");
}

#[test]
fn participants_must_enrol_tracked_families_and_known_capabilities() {
    let findings = demo_findings(|_, participants, _| {
        participants["families"][0]["familyId"] = json!("ghost")
    });
    assert_single(
        &findings,
        PARTICIPANTS,
        "participants",
        "enrols untracked family ghost",
    );

    let findings = demo_findings(|_, participants, _| {
        participants["families"][0]["cxx"]["capabilityIds"] = json!(["demo.unknown"]);
    });
    assert!(
        findings
            .iter()
            .any(|f| f.contains("unknown capability demo.unknown")),
        "{findings:#?}"
    );

    // demo.extra is named by the scenario but is never its action.
    let findings = demo_findings(|_, participants, _| {
        participants["families"][0]["cxx"]["capabilityIds"] = json!(["demo.extra"]);
    });
    assert_single(
        &findings,
        PARTICIPANTS,
        "participants",
        "selects no scenario",
    );

    let findings = demo_findings(|_, participants, _| {
        participants["families"][0]["cxx"]["capabilityIds"] = json!(["demo.observe", "demo.extra"]);
    });
    assert_single(&findings, PARTICIPANTS, "participants", "sorted, unique");

    let findings = demo_findings(|_, participants, _| {
        participants["families"][0] = json!({"familyId": "demo"})
    });
    assert_single(
        &findings,
        PARTICIPANTS,
        "participants",
        "must enrol at least one participant",
    );

    let findings = demo_findings(|_, participants, _| {
        participants["families"][0]["node"] = json!({"capabilityIds": ["demo.observe"]});
    });
    assert_single(
        &findings,
        PARTICIPANTS,
        "participants",
        "unknown field `node`",
    );
}

#[test]
fn consumer_obligations_must_match_the_packs() {
    let findings = demo_findings(|_, _, obligations| {
        obligations["families"][0]["consumers"][0]["obligations"][0]["scenarioIds"] =
            json!(["ghost"]);
    });
    assert_single(
        &findings,
        OBLIGATIONS,
        "consumer-obligations",
        "unknown demo scenario ghost",
    );

    let findings = demo_findings(|pack, _, _| {
        pack["consumerObligations"] = json!([{"id": "demo.shown"}, {"id": "demo.other"}])
    });
    assert_single(
        &findings,
        PACK,
        "consumer-obligations",
        "demo.other has no registration",
    );

    let findings = demo_findings(|pack, _, _| pack["consumerObligations"] = json!([]));
    assert_single(
        &findings,
        OBLIGATIONS,
        "consumer-obligations",
        "not declared by the demo pack",
    );

    let findings = demo_findings(|_, _, obligations| {
        obligations["families"][0]["consumers"][0]["id"] = json!("node")
    });
    assert_single(
        &findings,
        OBLIGATIONS,
        "consumer-obligations",
        "must be one of",
    );

    let findings = demo_findings(|_, _, obligations| {
        obligations["families"][0]["consumers"][0]["sourcePaths"] = json!(["ui/missing"]);
    });
    assert_single(
        &findings,
        OBLIGATIONS,
        "consumer-obligations",
        "existing repository path",
    );
}

#[test]
fn the_real_repository_passes_check() {
    assert_eq!(check(&RepoRoot::new(real_root())), Vec::<String>::new());
}

#[test]
fn a_copy_of_the_real_inputs_passes_and_seeded_failures_fail() {
    let clean = real_inputs();
    assert_eq!(check(&clean.root()), Vec::<String>::new());

    let bad_pack = real_inputs().replace(
        "tests/conformance/packs/performance/v1.json",
        "\"fixtureRef\"",
        "\"fixtureRef\": \"extra\", \"other\"",
    );
    let findings = check(&bad_pack.root());
    assert!(
        findings.iter().any(
            |f| f.starts_with("tests/conformance/packs/performance/v1.json:")
                && f.contains(": pack-input: ")
        ),
        "{findings:#?}"
    );

    let bad_participants = real_inputs().replace(
        PARTICIPANTS,
        "\"familyId\": \"xse-folder\"",
        "\"familyId\": \"xse-folders\"",
    );
    let findings = check(&bad_participants.root());
    assert!(
        findings
            .iter()
            .any(|f| f.contains("enrols untracked family xse-folders")),
        "{findings:#?}"
    );

    let bad_workflow = real_inputs().replace(
        ".github/workflows/ci-binding-compliance.yml",
        "needs: [rust, native]",
        "needs: [rust]",
    );
    let findings = check(&bad_workflow.root());
    assert!(
        findings.iter().any(
            |f| f.starts_with(".github/workflows/ci-binding-compliance.yml:")
                && f.contains("full aggregation")
        ),
        "{findings:#?}"
    );
}

#[test]
fn the_binary_exits_1_with_findings_on_a_seeded_pack() {
    let repo = real_inputs().replace(
        "tests/conformance/packs/performance/v1.json",
        "\"schemaVersion\": 1",
        "\"schemaVersion\": 1.0",
    );
    let output = Command::new(env!("CARGO_BIN_EXE_xtask"))
        .args([
            "--repo-root",
            repo.path().to_str().unwrap(),
            "conformance",
            "check",
        ])
        .output()
        .expect("run the xtask binary");
    assert_eq!(output.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("tests/conformance/packs/performance/v1.json:2: invalid-json:"),
        "{stderr}"
    );
    assert!(
        stderr.contains("conformance check failed: 1 findings"),
        "{stderr}"
    );
}
