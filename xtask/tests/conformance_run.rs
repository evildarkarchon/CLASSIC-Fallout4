//! `cargo xtask conformance run` with a fake runner (no participant process is
//! spawned) and `conformance verdict` over its artifacts, in fixture
//! repositories: plans, receipts, consumers, keep-going behaviour, the
//! failed-family summary, the controlled update service, and repository
//! completeness.

mod common;

use std::cell::RefCell;
use std::path::Path;
use std::time::Duration;

use common::FixtureRepo;
use common::conformance::{
    Evidence, OBLIGATIONS, PARTICIPANTS, commit, demo_obligations, demo_pack, demo_participants,
    demo_repo, read_plan, receipt_for,
};
use serde_json::{Value, json};
use xtask::Outcome;
use xtask::conformance::{
    Attempt, CommandTable, Compiler, Launch, Participant, ParticipantCommand, RunArgs, VerdictArgs,
    run_participant,
};

/// A table that "runs" every participant with the same inert command, bound
/// to `runner/fake.rs`.
fn fake_table() -> CommandTable {
    CommandTable::new(|participant, _| {
        Some(ParticipantCommand {
            program: "fake-participant".into(),
            args: Vec::new(),
            source_paths: if matches!(participant, "rust" | "cxx") {
                vec!["runner/fake.rs".into()]
            } else {
                Vec::new()
            },
            timeout: Duration::from_secs(5),
            wrapper: false,
        })
    })
}

/// The `other` family: Rust-only, no consumers, one scenario.
fn other_pack(family: &str, value: i64) -> Value {
    let mut pack = demo_pack();
    pack["familyId"] = json!(family);
    pack["capabilities"] = json!([{"id": format!("{family}.observe"), "rustSymbols": ["observe"], "observationFamilies": ["values"]}]);
    pack["scenarios"][0]["action"] = json!(format!("{family}.observe"));
    pack["scenarios"][0]["capabilityIds"] = json!([format!("{family}.observe")]);
    pack["scenarios"][0]["expected"] = json!({"value": value});
    pack["consumerObligations"] = json!([]);
    pack
}

/// The demo repository plus the `other` and `third` families and a runner
/// source, committed.
fn repo() -> FixtureRepo {
    commit(
        demo_repo(&demo_pack(), &demo_participants(), &demo_obligations())
            .json(
                "tests/conformance/packs/other/v1.json",
                &other_pack("other", 5),
            )
            .json(
                "tests/conformance/packs/third/v1.json",
                &other_pack("third", 7),
            )
            .file("runner/fake.rs", "// fake runner\n")
            .file("ui/src/main.rs", "fn main() {}\n"),
    )
}

/// The expected observation of each family's only scenario.
fn expected(family: &str) -> Value {
    match family {
        "demo" => json!({"value": 2}),
        "other" => json!({"value": 5}),
        "third" => json!({"value": 7}),
        other => panic!("unknown family {other}"),
    }
}

fn args(participant: Participant, compiler: Option<Compiler>, artifacts: &Path) -> RunArgs {
    RunArgs {
        participant,
        compiler,
        preset: "default".into(),
        families: Vec::new(),
        artifact_root: artifacts.to_path_buf(),
    }
}

/// A fake runner writing a receipt for each launch through `observe(family,
/// scenario)`; consumers report `{"shown": true}`. Records each launch.
fn echo_runner<'a>(
    launches: &'a RefCell<Vec<Launch>>,
    observe: impl Fn(&str, &Value) -> Option<Evidence> + 'a,
) -> impl FnMut(&Launch) -> Attempt + 'a {
    move |launch: &Launch| {
        launches.borrow_mut().push(launch.clone());
        let plan = read_plan(launch);
        let family = plan["familyId"].as_str().unwrap().to_owned();
        // `None` from `observe` means: write no receipt and fail the command.
        let all: Option<Vec<Evidence>> = plan["scenarios"]
            .as_array()
            .map(|scenarios| scenarios.iter().map(|s| observe(&family, s)).collect())
            .unwrap_or_else(|| Some(Vec::new()));
        let Some(evidence) = all else {
            return Attempt::exited(1);
        };
        let evidence = RefCell::new(evidence.into_iter());
        let receipt = receipt_for(
            &plan,
            |_| {
                evidence
                    .borrow_mut()
                    .next()
                    .expect("one evidence per scenario")
            },
            |_| json!({"shown": true}),
        );
        std::fs::write(&launch.receipt, serde_json::to_vec(&receipt).unwrap()).unwrap();
        Attempt::exited(0)
    }
}

fn correct(family: &str, _: &Value) -> Option<Evidence> {
    Some(Evidence::Observed(expected(family)))
}

fn outcome_findings(outcome: &Outcome) -> Vec<String> {
    match outcome {
        Outcome::Pass { .. } => Vec::new(),
        Outcome::Fail { findings, .. } => findings.iter().map(ToString::to_string).collect(),
    }
}

#[test]
fn rust_runs_every_family_and_writes_its_artifacts() {
    let repo = repo();
    let artifacts = tempfile::tempdir().unwrap();
    let launches = RefCell::new(Vec::new());
    let mut progress = Vec::new();
    let outcome = run_participant(
        &repo.root(),
        &args(Participant::Rust, None, artifacts.path()),
        &fake_table(),
        &mut echo_runner(&launches, correct),
        &mut |line| progress.push(line.to_owned()),
    )
    .unwrap();
    assert_eq!(
        outcome,
        Outcome::Pass {
            summary: "conformance run rust/rust: 3 families passed".into()
        }
    );
    let launches = launches.into_inner();
    let families: Vec<&str> = launches
        .iter()
        .map(|launch| launch.family_id.as_str())
        .collect();
    assert_eq!(families, ["demo", "other", "third"]);
    assert!(
        progress
            .iter()
            .any(|line| line.starts_with("[2/3] other: pass")),
        "{progress:#?}"
    );

    let launch = &launches[0];
    assert_eq!(
        launch.env["CLASSIC_CONFORMANCE_RUN_PLAN"],
        launch.run_plan.to_string_lossy()
    );
    assert_eq!(
        launch.env["CLASSIC_CONFORMANCE_OUTPUT"],
        launch.receipt.to_string_lossy()
    );
    assert!(!launch.env.contains_key("CLASSIC_CONFORMANCE_SERVICE"));
    let dir = launch.run_plan.parent().unwrap();
    assert!(dir.starts_with(artifacts.path().join("rust").join("rust")));
    let plan = read_plan(launch);
    assert!(
        plan["scenarios"][0].get("expected").is_none(),
        "plans are input only"
    );
    assert_eq!(plan["sourcePaths"], json!(["runner/fake.rs"]));
    let attempt: Value =
        serde_json::from_slice(&std::fs::read(dir.join("attempt.json")).unwrap()).unwrap();
    assert_eq!(attempt["exitCode"], 0);
    assert_eq!(attempt["command"], json!(["fake-participant"]));
    let report: Value =
        serde_json::from_slice(&std::fs::read(dir.join("conformance_report.json")).unwrap())
            .unwrap();
    assert_eq!(report["result"], "pass");
    assert_eq!(report["scope"]["kind"], "execution-instance");
    assert_eq!(report["invocations"][0]["scenarios"][0]["result"], "pass");
}

#[test]
fn run_keeps_going_past_failures_and_names_each_failed_family() {
    let repo = repo();
    let artifacts = tempfile::tempdir().unwrap();
    let launches = RefCell::new(Vec::new());
    let observe = |family: &str, _: &Value| match family {
        "demo" => Some(Evidence::Observed(json!({"value": 3}))),
        "other" => None,
        _ => Some(Evidence::Observed(expected(family))),
    };
    let outcome = run_participant(
        &repo.root(),
        &args(Participant::Rust, None, artifacts.path()),
        &fake_table(),
        &mut echo_runner(&launches, observe),
        &mut |_| {},
    )
    .unwrap();
    assert_eq!(
        launches.borrow().len(),
        3,
        "every family runs after a failure"
    );
    let Outcome::Fail { findings, summary } = &outcome else {
        panic!("expected a failure: {outcome:?}");
    };
    assert_eq!(
        summary,
        "conformance run rust/rust failed: 2 of 3 families failed: demo, other"
    );
    let rendered: Vec<String> = findings.iter().map(ToString::to_string).collect();
    assert!(
        rendered.iter().any(|f| f
            .contains(": semantic_conformance_mismatch: demo rust/rust scenario first at $.value")),
        "{rendered:#?}"
    );
    assert!(
        rendered.iter().any(|f| f.contains(
            ": adapter_command_failure: other rust/rust: the conformance command exited with code 1"
        )),
        "{rendered:#?}"
    );
    assert!(
        rendered.iter().any(|f| f.contains(": missing_execution_receipt: other rust/rust: the prepared invocation did not produce a receipt")),
        "{rendered:#?}"
    );
    assert!(
        !rendered.iter().any(|f| f.contains("third")),
        "{rendered:#?}"
    );

    // A participant-reported failure is an adapter failure, not a mismatch.
    let launches = RefCell::new(Vec::new());
    let outcome = run_participant(
        &repo.root(),
        &RunArgs {
            families: vec!["third".into()],
            ..args(Participant::Rust, None, artifacts.path())
        },
        &fake_table(),
        &mut echo_runner(&launches, |_, _| Some(Evidence::Failed)),
        &mut |_| {},
    )
    .unwrap();
    let rendered = outcome_findings(&outcome);
    assert_eq!(launches.borrow().len(), 1);
    assert!(
        rendered
            .iter()
            .all(|f| f.contains(": adapter_command_failure: third rust/rust")),
        "{rendered:#?}"
    );
}

#[test]
fn cxx_and_consumers_run_only_their_applicable_work() {
    let repo = repo();
    let artifacts = tempfile::tempdir().unwrap();
    let launches = RefCell::new(Vec::new());
    let outcome = run_participant(
        &repo.root(),
        &args(Participant::Cxx, Some(Compiler::ClangCl), artifacts.path()),
        &fake_table(),
        &mut echo_runner(&launches, correct),
        &mut |_| {},
    )
    .unwrap();
    assert!(matches!(outcome, Outcome::Pass { .. }), "{outcome:?}");
    let launch = launches.borrow()[0].clone();
    assert_eq!(
        launches.borrow().len(),
        1,
        "participants.json enrols only demo"
    );
    assert_eq!(launch.instance, "windows-clang-cl");
    assert_eq!(
        read_plan(&launch)["participant"]["executionInstanceId"],
        "windows-clang-cl"
    );

    let launches = RefCell::new(Vec::new());
    let outcome = run_participant(
        &repo.root(),
        &args(Participant::Tui, None, artifacts.path()),
        &fake_table(),
        &mut echo_runner(&launches, correct),
        &mut |_| {},
    )
    .unwrap();
    assert!(matches!(outcome, Outcome::Pass { .. }), "{outcome:?}");
    let launch = launches.borrow()[0].clone();
    assert!(
        launch
            .env
            .contains_key("CLASSIC_CONSUMER_CONFORMANCE_RUN_PLAN")
    );
    assert!(
        launch
            .env
            .contains_key("CLASSIC_CONSUMER_CONFORMANCE_OUTPUT")
    );
    let plan = read_plan(&launch);
    assert_eq!(plan["participant"]["role"], "consumer");
    assert_eq!(
        plan["obligations"],
        json!([{"id": "demo.shown", "scenarioIds": ["first"]}])
    );
    assert_eq!(plan["sourcePaths"], json!([OBLIGATIONS, "ui/src"]));

    // A consumer observation that differs from the catalog fails.
    let launches = RefCell::new(Vec::new());
    let mut runner = |launch: &Launch| {
        launches.borrow_mut().push(launch.clone());
        let receipt = receipt_for(
            &read_plan(launch),
            |_| unreachable!(),
            |_| json!({"shown": false}),
        );
        std::fs::write(&launch.receipt, serde_json::to_vec(&receipt).unwrap()).unwrap();
        Attempt::exited(0)
    };
    let outcome = run_participant(
        &repo.root(),
        &args(Participant::Tui, None, artifacts.path()),
        &fake_table(),
        &mut runner,
        &mut |_| {},
    )
    .unwrap();
    let rendered = outcome_findings(&outcome);
    assert!(
        rendered.iter().any(|f| f.contains(
            ": semantic_conformance_mismatch: demo tui/tui scenario demo.shown at $.shown"
        )),
        "{rendered:#?}"
    );
    assert!(
        rendered
            .iter()
            .any(|f| f.contains(": coverage_mapping_gap: demo obligation demo.shown")),
        "{rendered:#?}"
    );
}

#[test]
fn usage_problems_are_errors() {
    let repo = repo();
    let artifacts = tempfile::tempdir().unwrap();
    let launches = RefCell::new(Vec::new());
    let mut runner = echo_runner(&launches, correct);
    let mut attempt = |args: RunArgs| {
        run_participant(&repo.root(), &args, &fake_table(), &mut runner, &mut |_| {})
            .unwrap_err()
            .to_string()
    };
    assert!(
        attempt(args(Participant::Cxx, None, artifacts.path())).contains("--compiler is required")
    );
    assert!(
        attempt(args(
            Participant::Rust,
            Some(Compiler::Msvc),
            artifacts.path()
        ))
        .contains("only to cxx, cli and gui")
    );
    let wrong_family = RunArgs {
        families: vec!["other".into()],
        ..args(Participant::Cxx, Some(Compiler::Msvc), artifacts.path())
    };
    assert!(attempt(wrong_family).contains("does not require cxx/windows-msvc"));
    assert!(
        attempt(args(
            Participant::Gui,
            Some(Compiler::Msvc),
            artifacts.path()
        ))
        .contains("no family requires gui")
    );
    assert!(launches.borrow().is_empty());
}

#[test]
fn a_family_without_a_command_fails_without_stopping_the_run() {
    let repo = repo();
    let artifacts = tempfile::tempdir().unwrap();
    let table = CommandTable::new(|_, family| {
        (family != "other").then(|| ParticipantCommand {
            program: "fake-participant".into(),
            args: Vec::new(),
            source_paths: vec!["runner/fake.rs".into()],
            timeout: Duration::from_secs(5),
            wrapper: false,
        })
    });
    let launches = RefCell::new(Vec::new());
    let outcome = run_participant(
        &repo.root(),
        &args(Participant::Rust, None, artifacts.path()),
        &table,
        &mut echo_runner(&launches, correct),
        &mut |_| {},
    )
    .unwrap();
    assert_eq!(launches.borrow().len(), 2);
    let rendered = outcome_findings(&outcome);
    assert_eq!(rendered.len(), 1, "{rendered:#?}");
    assert!(
        rendered[0].contains(
            ": conformance-run: other rust/rust: no rust command is registered for other"
        )
    );
}

/// Runs every applicable execution of the fixture repository into
/// `artifacts`.
fn run_everything(repo: &FixtureRepo, artifacts: &Path) {
    for (participant, compiler) in [
        (Participant::Rust, None),
        (Participant::Cxx, Some(Compiler::Msvc)),
        (Participant::Cxx, Some(Compiler::ClangCl)),
        (Participant::Tui, None),
    ] {
        let launches = RefCell::new(Vec::new());
        let outcome = run_participant(
            &repo.root(),
            &args(participant, compiler, artifacts),
            &fake_table(),
            &mut echo_runner(&launches, correct),
            &mut |_| {},
        )
        .unwrap();
        assert!(
            matches!(outcome, Outcome::Pass { .. }),
            "{participant:?}: {outcome:?}"
        );
    }
}

fn verdict(repo: &FixtureRepo, receipts: &Path, output: Option<&Path>) -> Outcome {
    xtask::conformance::run(
        &repo.root(),
        xtask::conformance::Args {
            command: xtask::conformance::Command::Verdict(VerdictArgs {
                receipts: receipts.to_path_buf(),
                output: output.map(Path::to_path_buf),
            }),
        },
    )
    .unwrap()
}

#[test]
fn the_verdict_is_complete_only_with_every_execution() {
    let repo = repo();
    let artifacts = tempfile::tempdir().unwrap();
    run_everything(&repo, artifacts.path());
    let output = artifacts.path().join("verdict/verdict.json");
    assert_eq!(
        verdict(&repo, artifacts.path(), Some(&output)),
        Outcome::Pass {
            summary: "conformance verdict: repository complete: 3 families, 6 executions".into()
        }
    );
    let document: Value = serde_json::from_slice(&std::fs::read(&output).unwrap()).unwrap();
    assert_eq!(document["repositoryComplete"], true);
    assert_eq!(
        document["requiredFamilies"],
        json!(["demo", "other", "third"])
    );
    assert_eq!(
        document["families"][0]["consumerCoverage"]["result"],
        "pass"
    );

    // Only Rust: the demo family misses its CXX and TUI executions.
    let rust_only = tempfile::tempdir().unwrap();
    let launches = RefCell::new(Vec::new());
    run_participant(
        &repo.root(),
        &args(Participant::Rust, None, rust_only.path()),
        &fake_table(),
        &mut echo_runner(&launches, correct),
        &mut |_| {},
    )
    .unwrap();
    let Outcome::Fail { findings, summary } = verdict(&repo, rust_only.path(), None) else {
        panic!("a Rust-only download is incomplete");
    };
    assert_eq!(
        summary,
        "conformance verdict: repository incomplete: 1 of 3 families failed: demo"
    );
    let rendered: Vec<String> = findings.iter().map(ToString::to_string).collect();
    for missing in ["cxx/windows-clang-cl", "cxx/windows-msvc", "tui/tui"] {
        assert!(
            rendered
                .iter()
                .any(|f| f.contains(&format!("missing_execution_receipt: demo {missing}"))),
            "{missing}: {rendered:#?}"
        );
    }

    // A family with no artifacts at all is missing.
    let third_only = tempfile::tempdir().unwrap();
    run_participant(
        &repo.root(),
        &RunArgs {
            families: vec!["third".into()],
            ..args(Participant::Rust, None, third_only.path())
        },
        &fake_table(),
        &mut echo_runner(&RefCell::new(Vec::new()), correct),
        &mut |_| {},
    )
    .unwrap();
    let rendered = outcome_findings(&verdict(&repo, third_only.path(), None));
    assert!(
        rendered
            .iter()
            .any(|f| f.contains("missing_execution_receipt: other: no run artifacts")),
        "{rendered:#?}"
    );
}

#[test]
fn the_verdict_rejects_artifacts_that_no_longer_match_the_tree() {
    let repo = repo();
    let artifacts = tempfile::tempdir().unwrap();
    run_everything(&repo, artifacts.path());
    // The runner source changed after the run: every Rust and CXX plan that
    // bound it is stale.
    std::fs::write(repo.path().join("runner/fake.rs"), "// changed\n").unwrap();
    let rendered = outcome_findings(&verdict(&repo, artifacts.path(), None));
    assert!(
        rendered
            .iter()
            .any(|f| f.contains("stale_execution_receipt: other rust/rust:")
                && f.contains("source identity")),
        "{rendered:#?}"
    );
    std::fs::write(repo.path().join("runner/fake.rs"), "// fake runner\n").unwrap();

    // A receipt edited after the run is checked again.
    let receipt = walk(artifacts.path())
        .into_iter()
        .find(|path| path.ends_with("receipt.json") && path.to_string_lossy().contains("tui"))
        .unwrap();
    let text = std::fs::read_to_string(&receipt)
        .unwrap()
        .replace("\"shown\":true", "\"shown\":false");
    std::fs::write(&receipt, text).unwrap();
    let rendered = outcome_findings(&verdict(&repo, artifacts.path(), None));
    assert!(
        rendered
            .iter()
            .any(|f| f.contains("semantic_conformance_mismatch: demo tui/tui")),
        "{rendered:#?}"
    );
}

fn walk(dir: &Path) -> Vec<std::path::PathBuf> {
    walkdir::WalkDir::new(dir)
        .into_iter()
        .filter_map(Result::ok)
        .filter(|entry| entry.file_type().is_file())
        .map(walkdir::DirEntry::into_path)
        .collect()
}

/// An `update-services` pack whose one scenario scripts one Pages response.
fn update_services_pack() -> Value {
    json!({
        "schemaVersion": 1,
        "familyId": "update-services",
        "familyVersion": 1,
        "domainOwner": {"rustCrate": "classic-update-core"},
        "fixtureRoot": "tests/fixtures/update_services",
        "fixtures": {"current": "current.json"},
        "capabilities": [{"id": "update-services.notification", "rustSymbols": ["check"], "observationFamilies": ["values"]}],
        "scenarios": [{
            "id": "current",
            "action": "update-services.notification",
            "capabilityIds": ["update-services.notification"],
            "fixtureRefs": ["current"],
            "input": {"fixtureRef": "current"},
            "expected": {"status": "current"},
            "normalization": {"rootRelativePaths": false, "unorderedPaths": [], "excludedPaths": []}
        }],
        "consumerObligations": []
    })
}

#[test]
fn update_service_families_run_against_the_controlled_service() {
    let repo = commit(
        common::conformance::git_repo()
            .json(
                "tests/conformance/packs/update_services/v1.json",
                &update_services_pack(),
            )
            .json(
                "tests/fixtures/update_services/current.json",
                &json!({"installedVersion": "9.1.0", "timeoutMs": 3000, "checks": 1, "service": {
                    "pages": [{"status": 404, "body": "", "headers": {}}],
                    "api": []
                }}),
            )
            .json(PARTICIPANTS, &json!({"schemaVersion": 1, "families": []}))
            .json(OBLIGATIONS, &json!({"schemaVersion": 1, "families": []}))
            .file("runner/fake.rs", "// fake runner\n"),
    );
    let artifacts = tempfile::tempdir().unwrap();
    let run = |request: bool| {
        let mut runner = |launch: &Launch| {
            let service = launch.env["CLASSIC_CONFORMANCE_SERVICE"].clone();
            assert!(service.starts_with("http://127.0.0.1:"), "{service}");
            assert_eq!(launch.env["NO_PROXY"], "127.0.0.1,localhost");
            if request {
                let agent = ureq::Agent::new_with_config(
                    ureq::Agent::config_builder()
                        .http_status_as_error(false)
                        .build(),
                );
                let response = agent
                    .get(&format!("{service}/current/pages"))
                    .call()
                    .unwrap();
                assert_eq!(response.status().as_u16(), 404);
            }
            let receipt = receipt_for(
                &read_plan(launch),
                |_| Evidence::Observed(json!({"status": "current"})),
                |_| unreachable!(),
            );
            std::fs::write(&launch.receipt, serde_json::to_vec(&receipt).unwrap()).unwrap();
            Attempt::exited(0)
        };
        run_participant(
            &repo.root(),
            &args(Participant::Rust, None, artifacts.path()),
            &fake_table(),
            &mut runner,
            &mut |_| {},
        )
        .unwrap()
    };
    assert!(matches!(run(true), Outcome::Pass { .. }));
    let rendered = outcome_findings(&run(false));
    assert!(
        rendered.iter().any(|f| f.contains("adapter_command_failure: update-services rust/rust: the controlled update service was not used as scripted: unused responses: current/pages")),
        "{rendered:#?}"
    );
}
