//! Workflow-policy mutations: every pinned CI step and job of the real
//! workflows fails `check` when it is deleted or weakened. The required
//! executions come from the real repository's packs and catalogs, so the
//! policy runs against the same denominator CI uses; only the copied
//! workflows are mutated.
//!
//! Structural mutations (delete a step, add a key) are made on the parsed
//! workflow and written back with `YamlEmitter`; the policy reads workflows
//! structurally, so the re-emitted text is equivalent. A baseline test proves
//! that an unmutated round trip still passes.

mod common;

use std::collections::BTreeSet;
use std::sync::OnceLock;

use common::FixtureRepo;
use common::conformance::{real_root, real_workflows};
use xtask::RepoRoot;
use xtask::conformance::{ExecutionKey, required_executions, workflow_policy};
use yaml_rust2::{Yaml, YamlEmitter, YamlLoader};

const CI_RUST: &str = ".github/workflows/ci-rust.yml";
const CI_CPP: &str = ".github/workflows/ci-cpp.yml";
const CI_FULL: &str = ".github/workflows/ci-binding-compliance.yml";

/// Every surviving gate's CI step, written out independently of the policy's
/// own table: (workflow, job, step name). Deleting or editing any of them
/// must fail `check`.
const GATE_STEPS: &[(&str, &str, &str)] = &[
    (CI_RUST, "lint", "Check User Settings exclusive ownership"),
    (
        CI_RUST,
        "lint",
        "Check conformance packs, catalogs and workflow policy",
    ),
    (CI_RUST, "lint", "Run clippy"),
    (CI_RUST, "test", "Run phase-1 logging contract tests (Rust)"),
    (CI_RUST, "test", "Run Rust tests"),
    (CI_RUST, "test", "Run Rust tests with all features"),
    (
        CI_RUST,
        "test",
        "Validate Crash Log Scan Run variant coverage",
    ),
    (CI_RUST, "test", "Run Rust conformance"),
    (CI_RUST, "test", "Run TUI consumer conformance"),
    (CI_RUST, "test", "Upload Rust conformance artifacts"),
    (CI_RUST, "test", "Upload TUI consumer conformance artifacts"),
    (CI_RUST, "xtask-linux", "Build xtask"),
    (CI_RUST, "xtask-linux", "Validate YAML Data"),
    (CI_RUST, "xtask-linux", "Validate app-notification source"),
    (CI_RUST, "xtask-linux", "Dry-run app-notification publish"),
    (CI_CPP, "cxx-bridge-gate", "Build xtask"),
    (
        CI_CPP,
        "cxx-bridge-gate",
        "Check for orphan CXX bridge exports",
    ),
    (CI_CPP, "cli-tests", "Build and test CLI"),
    (CI_CPP, "cli-tests", "Run native CXX conformance"),
    (CI_CPP, "cli-tests", "Run CLI consumer conformance"),
    (
        CI_CPP,
        "cli-tests",
        "Upload native CXX conformance artifacts",
    ),
    (
        CI_CPP,
        "cli-tests",
        "Upload CLI consumer conformance artifacts",
    ),
    (CI_CPP, "gui-tests", "Build and test GUI"),
    (CI_CPP, "gui-tests", "Run GUI consumer conformance"),
    (
        CI_CPP,
        "gui-tests",
        "Upload GUI consumer conformance artifacts",
    ),
    (
        CI_FULL,
        "full",
        "Download current-run conformance artifacts",
    ),
    (
        CI_FULL,
        "full",
        "Require every retained participant job to pass",
    ),
    (CI_FULL, "full", "Run full repository conformance verdict"),
    (
        CI_FULL,
        "full",
        "Upload full repository conformance verdict",
    ),
];

/// Every job those steps live in.
const GATE_JOBS: &[(&str, &str)] = &[
    (CI_RUST, "lint"),
    (CI_RUST, "test"),
    (CI_RUST, "xtask-linux"),
    (CI_CPP, "cxx-bridge-gate"),
    (CI_CPP, "cli-tests"),
    (CI_CPP, "gui-tests"),
    (CI_FULL, "full"),
];

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

/// A copy of the real workflows with `file` parsed, changed by `mutate`, and
/// re-emitted.
fn mutated(file: &str, mutate: impl FnOnce(&mut Yaml)) -> FixtureRepo {
    let repo = real_workflows();
    let path = repo.path().join(file);
    let text = std::fs::read_to_string(&path).expect("read workflow");
    let mut document = YamlLoader::load_from_str(&text)
        .expect("real workflow parses")
        .remove(0);
    mutate(&mut document);
    let mut out = String::new();
    YamlEmitter::new(&mut out)
        .dump(&document)
        .expect("emit workflow");
    std::fs::write(&path, out).expect("write workflow");
    repo
}

/// One way to weaken a parsed workflow.
type Mutation<'a> = Box<dyn Fn(&mut Yaml) + 'a>;

fn key(name: &str) -> Yaml {
    Yaml::String(name.to_owned())
}

/// The step named `name` in `job`.
fn step<'a>(document: &'a mut Yaml, job: &str, name: &str) -> &'a mut Yaml {
    document["jobs"][job]["steps"]
        .as_mut_vec()
        .expect("job has steps")
        .iter_mut()
        .find(|step| step["name"].as_str() == Some(name))
        .unwrap_or_else(|| panic!("step {name:?} exists in job {job}"))
}

/// Sets `field` of a mapping node.
fn set(node: &mut Yaml, field: &str, value: Yaml) {
    node.as_mut_hash()
        .expect("node is a mapping")
        .insert(key(field), value);
}

#[test]
fn the_real_workflows_satisfy_the_real_denominator() {
    assert_eq!(required().len(), 123);
    assert_eq!(policy(&real_workflows(), required()), Vec::<String>::new());
}

#[test]
fn a_re_emitted_unmutated_workflow_still_passes() {
    for file in [CI_RUST, CI_CPP, CI_FULL] {
        let repo = mutated(file, |_| {});
        assert_eq!(policy(&repo, required()), Vec::<String>::new(), "{file}");
    }
}

#[test]
fn deleting_any_gate_step_fails() {
    for (file, job, name) in GATE_STEPS {
        let repo = mutated(file, |document| {
            document["jobs"][*job]["steps"]
                .as_mut_vec()
                .expect("job has steps")
                .retain(|step| step["name"].as_str() != Some(name));
        });
        assert_finding(&policy(&repo, required()), file, name);
    }
}

#[test]
fn editing_any_gate_step_fails() {
    for (file, job, name) in GATE_STEPS {
        // The command, or for an action step its pinned action.
        let repo = mutated(file, |document| {
            let step = step(document, job, name);
            match step["run"].as_str().map(str::to_owned) {
                Some(run) => set(
                    step,
                    "run",
                    Yaml::String(format!("{} --edited", run.trim_end())),
                ),
                None => {
                    let uses = step["uses"].as_str().expect("action step").to_owned();
                    set(step, "uses", Yaml::String(format!("{uses}-edited")));
                }
            }
        });
        assert_finding(&policy(&repo, required()), file, name);

        // A non-blocking step.
        let repo = mutated(file, |document| {
            set(
                step(document, job, name),
                "continue-on-error",
                Yaml::Boolean(true),
            );
        });
        assert_finding(&policy(&repo, required()), file, name);

        // A condition that can skip it, even keeping an approved prefix.
        let repo = mutated(file, |document| {
            let step = step(document, job, name);
            let condition = match step["if"].as_str() {
                Some(condition) => format!("{condition} && false"),
                None => "false".to_owned(),
            };
            set(step, "if", Yaml::String(condition));
        });
        assert_finding(&policy(&repo, required()), file, name);

        // Renaming the step is a deletion.
        let repo = mutated(file, |document| {
            set(
                step(document, job, name),
                "name",
                Yaml::String(format!("{name} (renamed)")),
            );
        });
        assert_finding(&policy(&repo, required()), file, name);
    }
}

#[test]
fn an_action_steps_inputs_are_pinned() {
    for (file, job, name, field) in [
        (CI_RUST, "test", "Upload Rust conformance artifacts", "path"),
        (
            CI_CPP,
            "cli-tests",
            "Upload native CXX conformance artifacts",
            "name",
        ),
        (
            CI_CPP,
            "gui-tests",
            "Upload GUI consumer conformance artifacts",
            "path",
        ),
        (
            CI_FULL,
            "full",
            "Download current-run conformance artifacts",
            "pattern",
        ),
    ] {
        let repo = mutated(file, |document| {
            set(
                &mut step(document, job, name)["with"],
                field,
                Yaml::String("elsewhere".into()),
            );
        });
        assert_finding(&policy(&repo, required()), file, name);
        // An extra input (an artifact from another run) is rejected too.
        let repo = mutated(file, |document| {
            set(
                &mut step(document, job, name)["with"],
                "run-id",
                Yaml::Integer(12345),
            );
        });
        assert_finding(&policy(&repo, required()), file, name);
    }
}

#[test]
fn reordering_gate_steps_fails() {
    // The CLI must be built before CTest-only conformance runs it.
    let repo = mutated(CI_CPP, |document| {
        let steps = document["jobs"]["cli-tests"]["steps"].as_mut_vec().unwrap();
        let build = steps
            .iter()
            .position(|step| step["name"].as_str() == Some("Build and test CLI"))
            .unwrap();
        let moved = steps.remove(build);
        steps.push(moved);
    });
    assert_finding(&policy(&repo, required()), CI_CPP, "Build and test CLI");

    // The variant preflight runs before the Rust receipt run.
    let repo = mutated(CI_RUST, |document| {
        let steps = document["jobs"]["test"]["steps"].as_mut_vec().unwrap();
        let preflight = steps
            .iter()
            .position(|step| {
                step["name"].as_str() == Some("Validate Crash Log Scan Run variant coverage")
            })
            .unwrap();
        let moved = steps.remove(preflight);
        steps.push(moved);
    });
    assert_finding(
        &policy(&repo, required()),
        CI_RUST,
        "Validate Crash Log Scan Run variant coverage",
    );
}

#[test]
fn weakening_any_gate_job_fails() {
    for (file, job) in GATE_JOBS {
        let label = format!("job {job}");
        let cases: Vec<Mutation<'_>> = vec![
            Box::new(|document| {
                let condition = match document["jobs"][*job]["if"].as_str() {
                    Some(condition) => format!("{condition} && false"),
                    None => "false".to_owned(),
                };
                set(&mut document["jobs"][*job], "if", Yaml::String(condition));
            }),
            Box::new(|document| {
                set(
                    &mut document["jobs"][*job],
                    "continue-on-error",
                    Yaml::Boolean(true),
                );
            }),
            Box::new(|document| {
                let minutes = document["jobs"][*job]["timeout-minutes"]
                    .as_i64()
                    .unwrap_or(0);
                set(
                    &mut document["jobs"][*job],
                    "timeout-minutes",
                    Yaml::Integer(minutes + 1),
                );
            }),
            Box::new(|document| {
                set(
                    &mut document["jobs"][*job],
                    "runs-on",
                    Yaml::String("macos-latest".into()),
                );
            }),
            Box::new(|document| {
                set(
                    &mut document["jobs"][*job],
                    "needs",
                    Yaml::Array(vec![Yaml::String("format".into())]),
                );
            }),
        ];
        for mutate in cases {
            let repo = mutated(file, |document| mutate(document));
            assert_finding(&policy(&repo, required()), file, &label);
        }
        let repo = mutated(file, |document| {
            document
                .as_mut_hash()
                .unwrap()
                .get_mut(&key("jobs"))
                .unwrap()
                .as_mut_hash()
                .unwrap()
                .remove(&key(job));
        });
        assert_finding(&policy(&repo, required()), file, job);
    }
}

#[test]
fn both_native_jobs_keep_the_two_compiler_matrix() {
    for job in ["cli-tests", "gui-tests"] {
        let label = format!("job {job}");
        let cases: Vec<Mutation<'_>> = vec![
            Box::new(|document| {
                document["jobs"][job]["strategy"]["matrix"]["compiler"] =
                    Yaml::Array(vec![Yaml::String("msvc".into())]);
            }),
            Box::new(|document| {
                document["jobs"][job]["strategy"]["fail-fast"] = Yaml::Boolean(true);
            }),
            Box::new(|document| {
                let mut exclude = yaml_rust2::yaml::Hash::new();
                exclude.insert(key("compiler"), Yaml::String("clang-cl".into()));
                set(
                    &mut document["jobs"][job]["strategy"]["matrix"],
                    "exclude",
                    Yaml::Array(vec![Yaml::Hash(exclude)]),
                );
            }),
        ];
        for mutate in cases {
            let repo = mutated(CI_CPP, |document| mutate(document));
            assert_finding(&policy(&repo, required()), CI_CPP, &label);
        }
    }
}

#[test]
fn receipt_producers_keep_the_event_checkout() {
    for (file, job) in [(CI_RUST, "test"), (CI_CPP, "cli-tests"), (CI_FULL, "full")] {
        for field in ["ref", "path", "repository"] {
            let repo = mutated(file, |document| {
                let checkout = document["jobs"][job]["steps"]
                    .as_mut_vec()
                    .unwrap()
                    .iter_mut()
                    .find(|step| step["uses"].as_str() == Some("actions/checkout@v6"))
                    .unwrap();
                if checkout["with"].is_badvalue() {
                    set(checkout, "with", Yaml::Hash(yaml_rust2::yaml::Hash::new()));
                }
                set(
                    &mut checkout["with"],
                    field,
                    Yaml::String("alternate".into()),
                );
            });
            assert_finding(&policy(&repo, required()), file, &format!("job {job}"));
        }
    }
}

#[test]
fn every_required_participant_instance_needs_its_run_step() {
    // A participant the catalogs newly require has no CI step yet.
    let mut extended = required().clone();
    extended.insert(ExecutionKey::new("brand-new", "qt", "qt"));
    let findings = policy(&real_workflows(), &extended);
    assert_finding(
        &findings,
        "tests/conformance/consumer-obligations.json",
        "participant qt",
    );
    assert_eq!(findings.len(), 1, "{findings:#?}");

    // A new family for an existing participant needs nothing new: `run`
    // runs every family that requires the participant.
    let mut extended = required().clone();
    extended.insert(ExecutionKey::new("brand-new", "rust", "rust"));
    assert_eq!(policy(&real_workflows(), &extended), Vec::<String>::new());

    // One compiler alone cannot be satisfied by the two-compiler matrix.
    let narrowed: BTreeSet<ExecutionKey> = required()
        .iter()
        .filter(|key| !(key.participant_id == "cxx" && key.instance_id == "windows-msvc"))
        .cloned()
        .collect();
    assert_finding(
        &policy(&real_workflows(), &narrowed),
        CI_CPP,
        "cxx is required on instances",
    );

    // A run step for a participant nothing requires fails `run`, so it is a
    // finding too.
    let without_tui: BTreeSet<ExecutionKey> = required()
        .iter()
        .filter(|key| key.participant_id != "tui")
        .cloned()
        .collect();
    assert_finding(
        &policy(&real_workflows(), &without_tui),
        CI_RUST,
        "no family requires tui",
    );
}

#[test]
fn full_aggregation_cannot_lose_required_jobs() {
    let repo = mutated(CI_FULL, |document| {
        document["jobs"]["full"]["needs"] = Yaml::Array(vec![Yaml::String("rust".into())]);
    });
    assert_finding(&policy(&repo, required()), CI_FULL, "job full");

    let repo = mutated(CI_FULL, |document| {
        document["jobs"]["native"]["uses"] =
            Yaml::String("owner/repo/.github/workflows/ci-cpp.yml@main".into());
    });
    assert_finding(&policy(&repo, required()), CI_FULL, "full aggregation");

    let repo = mutated(CI_FULL, |document| {
        set(
            &mut document["jobs"]["rust"],
            "if",
            Yaml::String("false".into()),
        );
    });
    assert_finding(&policy(&repo, required()), CI_FULL, "full aggregation");

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
        ("if-no-files-found: error", "if-no-files-found: warn"),
    ] {
        let repo = real_workflows().replace(CI_CPP, needle, replacement);
        assert_finding(&policy(&repo, required()), CI_CPP, "Corrosion source");
    }
}

#[test]
fn findings_point_at_the_offending_step_line() {
    let repo = real_workflows().replace(
        CI_RUST,
        "- name: Upload Rust conformance artifacts\n        if: always()",
        "- name: Upload Rust conformance artifacts\n        if: success()",
    );
    let text = std::fs::read_to_string(repo.path().join(CI_RUST)).unwrap();
    let line = text
        .lines()
        .position(|line| line.contains("- name: Upload Rust conformance artifacts"))
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

#[test]
fn a_missing_workflow_is_a_finding() {
    let text = std::fs::read_to_string(real_root().join(CI_RUST)).unwrap();
    let repo = FixtureRepo::empty().file(CI_RUST, &text);
    let findings = policy(&repo, required());
    assert_finding(&findings, CI_CPP, "required workflow is missing");
    assert_finding(&findings, CI_FULL, "required workflow is missing");
}
