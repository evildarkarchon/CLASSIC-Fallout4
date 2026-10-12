//! Workflow-policy mutations: each reviewed property of the real CI
//! workflows fails closed when weakened. The required executions come from
//! the real repository's packs and catalogs, so the policy runs against the
//! same denominator CI uses; only the copied workflows are mutated.

mod common;

use std::collections::BTreeSet;
use std::sync::OnceLock;

use common::FixtureRepo;
use common::conformance::{real_root, real_workflows};
use xtask::RepoRoot;
use xtask::conformance::{ExecutionKey, required_executions, workflow_policy};

const CI_RUST: &str = ".github/workflows/ci-rust.yml";
const CI_CPP: &str = ".github/workflows/ci-cpp.yml";
const CI_FULL: &str = ".github/workflows/ci-binding-compliance.yml";

/// The real repository's required executions, computed once.
fn required() -> &'static BTreeSet<ExecutionKey> {
    static REQUIRED: OnceLock<BTreeSet<ExecutionKey>> = OnceLock::new();
    REQUIRED.get_or_init(|| {
        required_executions(&RepoRoot::new(real_root())).expect("real inputs are clean")
    })
}

fn policy(repo: &FixtureRepo, required: &BTreeSet<ExecutionKey>) -> Vec<String> {
    workflow_policy::check(&repo.root(), required)
        .expect("policy runs")
        .iter()
        .map(ToString::to_string)
        .collect()
}

/// Asserts a finding in `file` mentioning `text`.
#[track_caller]
fn assert_finding(findings: &[String], file: &str, text: &str) {
    assert!(
        findings
            .iter()
            .any(|finding| finding.starts_with(&format!("{file}:"))
                && finding.contains(": workflow-policy: ")
                && finding.contains(text)),
        "expected a {file} finding mentioning {text:?}, got {findings:#?}"
    );
}

#[test]
fn the_real_workflows_satisfy_the_real_denominator() {
    assert_eq!(required().len(), 123);
    assert_eq!(policy(&real_workflows(), required()), Vec::<String>::new());
}

#[test]
fn every_weakened_topology_property_fails() {
    let cases: &[(&str, &str, &str, &str)] = &[
        (
            CI_RUST,
            "run_user_settings_conformance.py --participant rust",
            "run_removed_settings_conformance.py --participant rust",
            "missing a required marker",
        ),
        (
            CI_RUST,
            "run: python tools/binding_compliance/run_scan_run_conformance.py --participant rust",
            "continue-on-error: true\n        run: python tools/binding_compliance/run_scan_run_conformance.py --participant rust",
            "launcher must be blocking",
        ),
        (
            CI_CPP,
            "compiler: [msvc, clang-cl]",
            "compiler: [msvc]",
            "missing the exact required matrix",
        ),
        (
            CI_CPP,
            "timeout-minutes: 180",
            "timeout-minutes: 120",
            "timeout-minutes: 180",
        ),
        (
            CI_CPP,
            "timeout-minutes: 360",
            "timeout-minutes: 300",
            "timeout-minutes: 360",
        ),
        (
            CI_CPP,
            "compiler: [msvc, clang-cl]",
            "compiler: [msvc, clang-cl]\n        exclude:\n          - compiler: clang-cl",
            "matrix cannot exclude required executions",
        ),
        (
            CI_CPP,
            "fail-fast: false",
            "fail-fast: true",
            "fail-fast: false",
        ),
        (
            CI_CPP,
            "needs: [corrosion-source]\n    if: ${{ !cancelled() }}",
            "needs: [corrosion-source]\n    if: false",
            "run after upstream failures unless cancelled",
        ),
        (
            CI_CPP,
            "run_cxx_conformance.ps1 -Family user-settings -Compiler ${{ matrix.compiler }}",
            "run_cxx_conformance.ps1 -Family user-settings -Compiler ${{ matrix.compiler }} --profile full",
            "cannot claim full-repository scope",
        ),
        (
            CI_RUST,
            "- name: Upload Rust Crash Log Scan Run conformance diagnostics\n        if: always()",
            "- name: Upload Rust Crash Log Scan Run conformance diagnostics\n        if: success()",
            "diagnostics must upload even on failure",
        ),
        (
            CI_RUST,
            "Run Rust tests with all features",
            "Run Rust tests without conformance",
            "missing a required marker",
        ),
        (
            CI_RUST,
            "- name: Validate Crash Log Scan Run variant coverage\n        if: ${{ !cancelled() }}",
            "- name: Validate Crash Log Scan Run variant coverage\n        if: success()",
            "variant preflight must run after earlier failures unless cancelled",
        ),
        (
            CI_RUST,
            "run: cargo xtask scan-run-contract",
            "run: cargo xtask scan-run-contract --skip",
            "variant preflight (cargo xtask scan-run-contract) exactly once",
        ),
        (
            CI_CPP,
            "      - uses: actions/checkout@v6\n        with:\n          submodules: recursive",
            "      - uses: actions/checkout@v6\n        with:\n          submodules: recursive\n          ref: classic-next",
            "cannot replace the event source revision",
        ),
        (
            CI_CPP,
            "run_gui_consumer_conformance.ps1 -Compiler ${{ matrix.compiler }} -Preset ci-system-qt",
            "run_gui_consumer_conformance.ps1 -Compiler ${{ matrix.compiler }}",
            "must reuse the preceding GUI build preset",
        ),
        (
            CI_CPP,
            "run_gui_consumer_conformance.ps1 -Family user-settings -Compiler ${{ matrix.compiler }} -Preset ci-system-qt",
            "run_gui_consumer_conformance.ps1 -Family user-settings -Compiler ${{ matrix.compiler }} -Preset default",
            "must reuse the preceding GUI build preset",
        ),
        (
            CI_CPP,
            "classic-gui/build_gui.ps1 -Preset ci-system-qt",
            "classic-gui/build_gui.ps1 -Preset default",
            "must reuse the preceding GUI build preset",
        ),
        (
            CI_CPP,
            "run_gui_consumer_conformance.ps1",
            "run_removed_gui_consumer_conformance.ps1",
            "missing a required marker",
        ),
        (
            CI_CPP,
            "**/run_plan.json",
            "**/plan.json",
            "must retain the authenticated run plan",
        ),
        // Keeping an approved condition as a prefix cannot disable a step.
        (
            CI_RUST,
            "if: ${{ !cancelled() }}\n        run: python tools/binding_compliance/run_scan_run_conformance.py",
            "if: ${{ !cancelled() }} && false\n        run: python tools/binding_compliance/run_scan_run_conformance.py",
            "launcher must run after earlier failures unless cancelled",
        ),
        (
            CI_RUST,
            "if: always()",
            "if: always() && false",
            "diagnostics must upload even on failure",
        ),
    ];
    for (file, needle, replacement, message) in cases {
        let repo = real_workflows().replace(file, needle, replacement);
        assert_finding(&policy(&repo, required()), file, message);
    }
}

#[test]
fn full_aggregation_cannot_lose_required_jobs_or_artifact_identity() {
    let cases: &[(&str, &str)] = &[
        ("needs: [rust, native]", "needs: [rust]"),
        (
            "uses: ./.github/workflows/ci-cpp.yml",
            "uses: owner/repo/.github/workflows/ci-cpp.yml@main",
        ),
        ("merge-multiple: false", "merge-multiple: true"),
        ("pattern: '*conformance*'", "pattern: 'rust-*'"),
        ("--profile full", "--profile ci"),
        (
            "pattern: '*conformance*'",
            "pattern: '*conformance*'\n          run-id: 12345",
        ),
        (
            "      - uses: actions/checkout@v6",
            "      - uses: actions/checkout@v6\n        with:\n          ref: classic-next",
        ),
        (
            "    name: Full Repository Conformance",
            "    name: Full Repository Conformance\n    continue-on-error: true",
        ),
        (
            "PARTICIPANT_RESULTS: ${{ toJSON(needs) }}",
            "PARTICIPANT_RESULTS: '{}'",
        ),
    ];
    for (needle, replacement) in cases {
        let repo = real_workflows().replace(CI_FULL, needle, replacement);
        assert_finding(&policy(&repo, required()), CI_FULL, "full aggregation");
    }
}

#[test]
fn a_reusable_participant_must_declare_workflow_call() {
    let repo = real_workflows().replace(CI_CPP, "workflow_call:", "workflow_dispatch:");
    assert_finding(
        &policy(&repo, required()),
        CI_FULL,
        "must declare `on: workflow_call`",
    );
}

#[test]
fn native_jobs_require_the_pinned_shared_corrosion_source() {
    for (needle, replacement) in [
        (
            "1499b14e4906a2890f5cee1547c8848db261753d",
            "0000000000000000000000000000000000000000",
        ),
        ("needs: [corrosion-source]", "needs: []"),
        ("if-no-files-found: error", "if-no-files-found: warn"),
    ] {
        let repo = real_workflows().replace(CI_CPP, needle, replacement);
        assert_finding(&policy(&repo, required()), CI_CPP, "Corrosion source");
    }
}

#[test]
fn receipt_producers_preserve_the_aggregation_checkout_layout() {
    let required = BTreeSet::from([ExecutionKey::new("performance", "rust", "rust")]);
    let repo = real_workflows().replace(
        CI_RUST,
        "  test:\n    name: Tests\n    runs-on: windows-latest",
        "  test:\n    name: Tests\n    runs-on: ubuntu-latest",
    );
    assert_finding(&policy(&repo, &required), CI_RUST, "checkout layout");

    let text = std::fs::read_to_string(real_root().join(CI_RUST))
        .unwrap()
        .replace("\r\n", "\n");
    let text = text.replace(
        "      - uses: actions/checkout@v6",
        "      - uses: actions/checkout@v6\n        with:\n          path: alternate",
    );
    let repo = FixtureRepo::empty()
        .file(CI_RUST, &text)
        .file(CI_CPP, "")
        .file(CI_FULL, "");
    assert_finding(
        &policy(&repo, &required),
        CI_RUST,
        "default receipt checkout layout",
    );
}

#[test]
fn a_newly_applicable_execution_requires_its_own_ci_step() {
    let mut extended = required().clone();
    extended.insert(ExecutionKey::new("brand-new", "rust", "rust"));
    let findings = policy(&real_workflows(), &extended);
    assert_finding(
        &findings,
        CI_RUST,
        "rust brand-new is missing a required marker",
    );
    assert_eq!(findings.len(), 1, "{findings:#?}");

    // One compiler alone cannot be satisfied by the two-compiler matrix step.
    let mut narrowed = required().clone();
    narrowed.remove(&ExecutionKey::new("user-settings", "cxx", "windows-msvc"));
    let findings = policy(&real_workflows(), &narrowed);
    assert!(
        findings
            .iter()
            .any(|f| f.contains("requires cxx instances")),
        "{findings:#?}"
    );
}

#[test]
fn findings_point_at_the_offending_step_line() {
    let repo = real_workflows().replace(
        CI_RUST,
        "- name: Upload Rust Crash Log Scan Run conformance diagnostics\n        if: always()",
        "- name: Upload Rust Crash Log Scan Run conformance diagnostics\n        if: success()",
    );
    let text = std::fs::read_to_string(repo.path().join(CI_RUST)).unwrap();
    let line = text
        .lines()
        .position(|line| {
            line.contains("- name: Upload Rust Crash Log Scan Run conformance diagnostics")
        })
        .unwrap()
        + 1;
    let findings = policy(&repo, required());
    assert!(
        findings
            .iter()
            .any(|f| f.starts_with(&format!("{CI_RUST}:{line}: workflow-policy: "))),
        "expected line {line}: {findings:#?}"
    );
}
