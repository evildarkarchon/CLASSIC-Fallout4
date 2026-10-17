//! Family reports over the demo family: denominators per scope, evidence
//! consistency, consumer coverage, and the repository verdict.

use serde_json::json;

use super::super::plan::{self, Payload, PlanRequest, PreparedPack};
use super::super::receipt::validate;
use super::super::schema::RunPlan;
use super::super::tests::{Demo, demo_expected, receipt_for};
use super::*;

/// A validated invocation of the demo pack by `participant`/`instance` over
/// `scenarios`, whose observations come from `observe`.
fn invocation(
    demo: &Demo,
    prepared: &PreparedPack,
    participant: &str,
    instance: &str,
    scenarios: &[&str],
    observe: impl Fn(&str) -> serde_json::Value,
) -> PreparedReport {
    let plan = plan::build(
        &demo.root,
        prepared,
        &PlanRequest {
            participant: participant.into(),
            role: Role::SemanticAdapter,
            instance: instance.into(),
            source_paths: vec!["runner".into()],
            payload: Payload::Scenarios(scenarios.iter().map(|s| (*s).to_owned()).collect()),
        },
    )
    .unwrap();
    let receipt = serde_json::to_vec(&receipt_for(&plan, observe)).unwrap();
    let plan: RunPlan = serde_json::from_value(plan).unwrap();
    validate(prepared, &plan, Some(&receipt), None)
}

/// A validated TUI invocation reporting `shown`.
fn tui_invocation(demo: &Demo, prepared: &PreparedPack, shown: bool) -> PreparedReport {
    let plan = plan::build(
        &demo.root,
        prepared,
        &PlanRequest {
            participant: "tui".into(),
            role: Role::Consumer,
            instance: "tui".into(),
            source_paths: vec![
                "tests/conformance/consumer-obligations.json".into(),
                "ui/src".into(),
            ],
            payload: Payload::Obligations(vec![("demo.shown".into(), vec!["first".into()])]),
        },
    )
    .unwrap();
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
    receipt["obligations"] = json!([{"id": "demo.shown", "executionStatus": "completed", "observation": {"shown": shown}, "failure": null}]);
    let mut expectations = super::super::receipt::ConsumerExpectations::new();
    expectations.insert(
        "demo.shown".into(),
        json!({"shown": true}).as_object().cloned().unwrap(),
    );
    let plan: RunPlan = serde_json::from_value(plan).unwrap();
    validate(
        prepared,
        &plan,
        Some(&serde_json::to_vec(&receipt).unwrap()),
        Some(&expectations),
    )
}

fn kinds(report: &FamilyReport) -> Vec<&'static str> {
    report
        .failures
        .iter()
        .map(|failure| failure.kind.as_str())
        .collect()
}

#[test]
fn an_instance_report_requires_exactly_its_own_execution() {
    let demo = Demo::new();
    let (loaded, prepared, applicability) = demo.prepare();
    let executions = applicability.executions(&loaded.pack);
    let consumers = applicability.consumers_of("demo");
    let rust = invocation(
        &demo,
        &prepared,
        "rust",
        "rust",
        &["first", "second"],
        demo_expected,
    );
    let scope = Scope::Instance {
        participant: "rust".into(),
        instance: "rust".into(),
    };
    let report = family_report(
        &loaded.pack,
        scope.clone(),
        &executions,
        &consumers,
        vec![rust],
        Vec::new(),
    );
    assert!(report.passed(), "{:#?}", report.failures);
    assert_eq!(report.required, [("rust".to_owned(), "rust".to_owned())]);
    let document = report.document();
    assert_eq!(document["scope"]["kind"], "execution-instance");
    assert_eq!(
        document["repositoryComplete"], false,
        "an instance never claims the repository"
    );

    // A Rust invocation that skipped a scenario does not cover the instance.
    let partial = invocation(&demo, &prepared, "rust", "rust", &["first"], demo_expected);
    let report = family_report(
        &loaded.pack,
        scope,
        &executions,
        &consumers,
        vec![partial],
        Vec::new(),
    );
    assert_eq!(kinds(&report), ["missing_execution_receipt"]);
}

#[test]
fn the_repository_scope_requires_every_participant_and_consumer_coverage() {
    let demo = Demo::new();
    let (loaded, prepared, applicability) = demo.prepare();
    let executions = applicability.executions(&loaded.pack);
    let consumers = applicability.consumers_of("demo");
    let all = || {
        vec![
            invocation(
                &demo,
                &prepared,
                "rust",
                "rust",
                &["first", "second"],
                demo_expected,
            ),
            invocation(
                &demo,
                &prepared,
                "cxx",
                "windows-clang-cl",
                &["first"],
                demo_expected,
            ),
            invocation(
                &demo,
                &prepared,
                "cxx",
                "windows-msvc",
                &["first"],
                demo_expected,
            ),
            tui_invocation(&demo, &prepared, true),
        ]
    };
    let report = family_report(
        &loaded.pack,
        Scope::Repository,
        &executions,
        &consumers,
        all(),
        Vec::new(),
    );
    assert!(
        report.passed(),
        "{:#?} {:#?}",
        report.failures,
        report.coverage
    );
    assert_eq!(report.document()["repositoryComplete"], true);
    assert_eq!(report.coverage.as_ref().unwrap().covered.len(), 1);

    // Without the msvc instance the family is incomplete.
    let mut partial = all();
    partial.remove(2);
    let report = family_report(
        &loaded.pack,
        Scope::Repository,
        &executions,
        &consumers,
        partial,
        Vec::new(),
    );
    assert!(!report.passed());
    assert_eq!(
        report.missing(),
        [&("cxx".to_owned(), "windows-msvc".to_owned())]
    );

    // A failing consumer observation leaves the obligation uncovered.
    let mut wrong = all();
    wrong[3] = tui_invocation(&demo, &prepared, false);
    let report = family_report(
        &loaded.pack,
        Scope::Repository,
        &executions,
        &consumers,
        wrong,
        Vec::new(),
    );
    assert!(!report.passed());
    let coverage = report.coverage.as_ref().unwrap();
    assert_eq!(coverage.gaps.len(), 1, "{coverage:#?}");
    assert!(
        report
            .findings("tests/conformance/packs/demo/v1.json", &BTreeMap::new())
            .iter()
            .any(|finding| finding.rule == "coverage_mapping_gap"),
    );

    // A failed invocation fails the family with its detailed findings.
    let mut mismatched = all();
    mismatched[0] = invocation(
        &demo,
        &prepared,
        "rust",
        "rust",
        &["first", "second"],
        |_| json!({"value": 0}),
    );
    let report = family_report(
        &loaded.pack,
        Scope::Repository,
        &executions,
        &consumers,
        mismatched,
        Vec::new(),
    );
    assert_eq!(kinds(&report), ["semantic_conformance_mismatch"]);
    let mut locations = BTreeMap::new();
    locations.insert(
        ("rust".to_owned(), "rust".to_owned()),
        "artifacts/rust/receipt.json".to_owned(),
    );
    let findings = report.findings("tests/conformance/packs/demo/v1.json", &locations);
    assert!(
        findings
            .iter()
            .any(|finding| finding.path == "artifacts/rust/receipt.json"
                && finding.rule == "semantic_conformance_mismatch"
                && finding.message.contains("scenario first at $.items")),
        "{findings:#?}"
    );
}

#[test]
fn duplicate_or_inconsistent_evidence_fails() {
    let demo = Demo::new();
    let (loaded, prepared, applicability) = demo.prepare();
    let executions = applicability.executions(&loaded.pack);
    let rust = || {
        invocation(
            &demo,
            &prepared,
            "rust",
            "rust",
            &["first", "second"],
            demo_expected,
        )
    };
    let scope = Scope::Instance {
        participant: "rust".into(),
        instance: "rust".into(),
    };
    let report = family_report(
        &loaded.pack,
        scope.clone(),
        &executions,
        &[],
        vec![rust(), rust()],
        Vec::new(),
    );
    assert_eq!(kinds(&report), ["malformed_execution_receipt"]);

    let mut other_revision = invocation(
        &demo,
        &prepared,
        "cxx",
        "windows-msvc",
        &["first"],
        demo_expected,
    );
    let identity = other_revision.invocation["sourceIdentity"]
        .as_str()
        .unwrap()
        .to_owned();
    let (_, rest) = identity.split_at(4 + 40);
    other_revision.invocation["sourceIdentity"] = json!(format!("git:{}{rest}", "f".repeat(40)));
    let report = family_report(
        &loaded.pack,
        Scope::Repository,
        &executions,
        &[],
        vec![rust(), other_revision],
        Vec::new(),
    );
    assert_eq!(
        kinds(&report),
        ["stale_execution_receipt"],
        "{:#?}",
        report.failures
    );
    assert!(
        report.failures[0]
            .message
            .contains("one common git revision")
    );
}

#[test]
fn the_verdict_is_complete_only_when_every_family_passes() {
    let demo = Demo::new();
    let (loaded, prepared, applicability) = demo.prepare();
    let executions = applicability.executions(&loaded.pack);
    let consumers = applicability.consumers_of("demo");
    let report = family_report(
        &loaded.pack,
        Scope::Repository,
        &executions,
        &consumers,
        vec![invocation(
            &demo,
            &prepared,
            "rust",
            "rust",
            &["first", "second"],
            demo_expected,
        )],
        Vec::new(),
    );
    let verdict = Verdict {
        required: vec!["demo".into()],
        missing: Vec::new(),
        families: vec![report],
    };
    assert!(!verdict.complete(), "cxx and tui are still missing");
    assert_eq!(verdict.document()["result"], "fail");

    let empty = Verdict {
        required: vec!["demo".into()],
        missing: vec!["demo".into()],
        families: Vec::new(),
    };
    assert!(!empty.complete());
    assert_eq!(empty.document()["missingFamilies"], json!(["demo"]));
}

#[test]
fn pretty_reports_sort_members_and_end_with_a_newline() {
    let text = pretty(&json!({"b": 1, "a": {"d": 2, "c": 3}}));
    assert!(text.ends_with("}\n"));
    assert!(text.find("\"a\"").unwrap() < text.find("\"b\"").unwrap());
    assert!(text.find("\"c\"").unwrap() < text.find("\"d\"").unwrap());
}
