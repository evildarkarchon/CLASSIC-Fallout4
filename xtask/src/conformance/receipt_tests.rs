//! Receipt validation driven directly, without spawning a participant: each
//! stage's failure kind for a seeded defect, after an echo of the expected
//! observation passes.

use serde_json::{Value, json};

use super::super::pack;
use super::super::plan::{self, Role};
use super::super::tests::{Demo, demo_expected, receipt_for};
use super::*;

/// Validates `receipt` against the demo Rust plan; returns
/// `(kind, item, path)` per failure.
fn failures_for(
    mutate: impl FnOnce(&mut Value, &Value),
) -> Vec<(&'static str, Option<String>, Option<String>)> {
    let demo = Demo::new();
    let (_, prepared, _) = demo.prepare();
    let plan = demo.rust_plan(&prepared);
    let mut receipt = receipt_for(&plan, demo_expected);
    mutate(&mut receipt, &plan);
    let bytes = serde_json::to_vec(&receipt).unwrap();
    validated(&prepared, &plan, Some(&bytes))
}

fn validated(
    prepared: &PreparedPack,
    plan: &Value,
    bytes: Option<&[u8]>,
) -> Vec<(&'static str, Option<String>, Option<String>)> {
    let plan: RunPlan = serde_json::from_value(plan.clone()).unwrap();
    validate(prepared, &plan, bytes, None)
        .failures
        .into_iter()
        .map(|failure| (failure.kind.as_str(), failure.item, failure.path))
        .collect()
}

fn only_kind(failures: &[(&'static str, Option<String>, Option<String>)]) -> &'static str {
    let kinds: BTreeSet<&str> = failures.iter().map(|failure| failure.0).collect();
    assert_eq!(kinds.len(), 1, "{failures:#?}");
    failures[0].0
}

#[test]
fn a_receipt_echoing_the_expectations_passes() {
    assert_eq!(failures_for(|_, _| {}), Vec::new());
}

#[test]
fn each_validation_stage_reports_its_failure_kind() {
    type Seed = fn(&mut Value, &Value);
    let cases: [(&str, Seed, &str); 12] = [
        (
            "skipped execution",
            |r, _| r["scenarios"][0]["executionStatus"] = json!("skipped"),
            "applicability_violation",
        ),
        (
            "unsupported execution",
            |r, _| r["scenarios"][1]["executionStatus"] = json!("unsupported"),
            "applicability_violation",
        ),
        (
            "a policy exception",
            |r, _| {
                r["scenarios"][0]["executionStatus"] = json!("not_applicable");
                r["scenarios"][0]["policyExceptionId"] = json!("reviewed");
            },
            "malformed_execution_receipt",
        ),
        (
            "no runner",
            |r, _| {
                r.as_object_mut().unwrap().remove("runner");
            },
            "malformed_execution_receipt",
        ),
        (
            "a float observation",
            |r, _| r["scenarios"][0]["observation"]["value"] = json!(2.5),
            "malformed_execution_receipt",
        ),
        (
            "another expectation digest",
            |r, _| r["expectationDigest"] = json!(format!("sha256:{}", "0".repeat(64))),
            "stale_execution_receipt",
        ),
        (
            "another invocation",
            |r, _| r["invocation"]["id"] = json!("00000000-0000-4000-8000-000000000000"),
            "stale_execution_receipt",
        ),
        (
            "another participant",
            |r, _| r["participant"]["executionInstanceId"] = json!("windows-msvc"),
            "malformed_execution_receipt",
        ),
        (
            "an unplanned scenario",
            |r, _| r["scenarios"][1]["id"] = json!("third"),
            "malformed_execution_receipt",
        ),
        (
            "other capability IDs",
            |r, _| r["scenarios"][0]["capabilityIds"] = json!(["demo.other"]),
            "malformed_execution_receipt",
        ),
        (
            "duplicate evidence",
            |r, _| {
                let first = r["scenarios"][0].clone();
                r["scenarios"].as_array_mut().unwrap().push(first);
            },
            "malformed_execution_receipt",
        ),
        (
            "a reported failure",
            |r, _| {
                r["scenarios"][0]["executionStatus"] = json!("failed");
                r["scenarios"][0]["failure"] = json!({"kind": "panic", "message": "boom"});
            },
            "adapter_command_failure",
        ),
    ];
    for (label, seed, kind) in cases {
        let failures = failures_for(seed);
        assert_eq!(only_kind(&failures), kind, "{label}: {failures:#?}");
    }
}

#[test]
fn missing_evidence_is_a_missing_execution_receipt() {
    let demo = Demo::new();
    let (_, prepared, _) = demo.prepare();
    let plan = demo.rust_plan(&prepared);
    let failures = validated(&prepared, &plan, None);
    assert_eq!(only_kind(&failures), "missing_execution_receipt");

    let failures = failures_for(|receipt, _| {
        receipt["scenarios"].as_array_mut().unwrap().remove(1);
    });
    assert_eq!(
        failures,
        [("missing_execution_receipt", Some("second".to_owned()), None)]
    );

    let failures = validated(&prepared, &plan, Some(b"{\"a\": 1, \"a\": 2}"));
    assert_eq!(only_kind(&failures), "malformed_execution_receipt");
}

#[test]
fn a_changed_observation_is_a_semantic_mismatch_at_its_path() {
    let failures = failures_for(|receipt, _| {
        receipt["scenarios"][0]["observation"]["items"] = json!(["b", "a"]);
        receipt["scenarios"][1]["observation"]["extra"] = json!(true);
    });
    assert_eq!(
        failures,
        [
            (
                "semantic_conformance_mismatch",
                Some("first".to_owned()),
                Some("$.items[0]".to_owned())
            ),
            (
                "semantic_conformance_mismatch",
                Some("first".to_owned()),
                Some("$.items[1]".to_owned())
            ),
            (
                "semantic_conformance_mismatch",
                Some("second".to_owned()),
                Some("$.extra".to_owned())
            ),
        ]
    );
}

#[test]
fn declared_unordered_paths_apply_during_validation() {
    let mut pack = super::super::tests::demo_pack();
    pack["scenarios"][0]["normalization"]["unorderedPaths"] = json!(["$.items"]);
    let demo = Demo::with(&pack);
    let (_, prepared, _) = demo.prepare();
    let plan = demo.rust_plan(&prepared);
    let receipt = receipt_for(&plan, |id| {
        let mut observation = demo_expected(id);
        if id == "first" {
            observation["items"] = json!(["b", "a"]);
        }
        observation
    });
    let bytes = serde_json::to_vec(&receipt).unwrap();
    assert_eq!(validated(&prepared, &plan, Some(&bytes)), Vec::new());
}

#[test]
fn consumer_obligations_compare_with_the_catalog_expectation() {
    let demo = Demo::new();
    let (_, prepared, _) = demo.prepare();
    let plan = plan::build(
        &demo.root,
        &prepared,
        &plan::PlanRequest {
            participant: "tui".into(),
            role: Role::Consumer,
            instance: "tui".into(),
            source_paths: vec![
                "tests/conformance/consumer-obligations.json".into(),
                "ui/src".into(),
            ],
            payload: plan::Payload::Obligations(vec![("demo.shown".into(), vec!["first".into()])]),
        },
    )
    .unwrap();
    assert!(plan.get("scenarios").is_none() && plan["obligations"][0]["id"] == "demo.shown");
    let plan_value: RunPlan = serde_json::from_value(plan.clone()).unwrap();
    let mut expectations = ConsumerExpectations::new();
    expectations.insert(
        "demo.shown".into(),
        json!({"shown": true}).as_object().cloned().unwrap(),
    );
    let receipt = |shown: bool| {
        let mut receipt = receipt_for(&json!({"scenarios": []}), demo_expected);
        for key in [
            "schemaVersion",
            "familyId",
            "familyVersion",
            "expectationDigest",
            "invocation",
            "participant",
        ] {
            receipt[key] = plan[key].clone();
        }
        receipt.as_object_mut().unwrap().remove("scenarios");
        receipt["obligations"] = json!([{
            "id": "demo.shown", "executionStatus": "completed", "observation": {"shown": shown}, "failure": null
        }]);
        serde_json::to_vec(&receipt).unwrap()
    };
    let report = validate(
        &prepared,
        &plan_value,
        Some(&receipt(true)),
        Some(&expectations),
    );
    assert!(report.passed(), "{:#?}", report.failures);
    assert_eq!(report.obligations.len(), 1);

    let report = validate(
        &prepared,
        &plan_value,
        Some(&receipt(false)),
        Some(&expectations),
    );
    let kinds: Vec<&str> = report.failures.iter().map(|f| f.kind.as_str()).collect();
    assert_eq!(kinds, ["semantic_conformance_mismatch"]);
    assert_eq!(report.failures[0].path.as_deref(), Some("$.shown"));
}

#[test]
fn a_changed_pack_or_plan_makes_the_receipt_stale() {
    let demo = Demo::new();
    let (loaded, prepared, _) = demo.prepare();
    let plan = demo.rust_plan(&prepared);
    let materialized = plan::write(&demo.root.join("artifacts"), &plan).unwrap();
    let fresh =
        || pack::load_one(&demo.root, &loaded.file).and_then(|l| plan::prepare(&demo.root, &l));
    assert_eq!(
        check_current(
            &prepared,
            fresh(),
            &materialized.run_plan,
            &materialized.bytes
        ),
        Vec::new()
    );

    std::fs::write(&materialized.run_plan, b"{}").unwrap();
    let failures = check_current(
        &prepared,
        fresh(),
        &materialized.run_plan,
        &materialized.bytes,
    );
    assert_eq!(failures.len(), 1);
    assert_eq!(failures[0].kind, FailureKind::StaleReceipt);

    std::fs::write(&materialized.run_plan, &materialized.bytes).unwrap();
    std::fs::write(
        demo.root.join("tests/fixtures/demo/one.json"),
        b"{\"request\": {\"value\": 9}}",
    )
    .unwrap();
    let failures = check_current(
        &prepared,
        fresh(),
        &materialized.run_plan,
        &materialized.bytes,
    );
    assert_eq!(failures.len(), 1);
    assert!(
        failures[0]
            .message
            .contains("changed after the run was planned"),
        "{failures:#?}"
    );
}
