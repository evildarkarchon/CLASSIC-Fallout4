//! Conformance fixture builders: a `git init` repository with `json!`-built
//! packs and catalogs, and copies of the real repository's conformance inputs
//! for seeded-failure tests.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use serde_json::{Value, json};
use xtask::conformance::{self, CheckArgs, Command as ConformanceCommand};
use xtask::{Outcome, RepoRoot};

use super::FixtureRepo;

/// The real repository root (the parent of the `xtask/` crate).
pub fn real_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("xtask has a parent directory")
        .to_path_buf()
}

/// An empty repository with `git init` run in it, as the engine's plan and
/// source-identity code expects a git checkout.
pub fn git_repo() -> FixtureRepo {
    let repo = FixtureRepo::empty();
    let status = Command::new("git")
        .args(["init", "-q"])
        .current_dir(repo.path())
        .status()
        .expect("git is on PATH");
    assert!(status.success(), "git init failed");
    repo
}

impl FixtureRepo {
    /// Writes `value` as pretty JSON to the repo-relative `path`.
    pub fn json(self, path: &str, value: &Value) -> Self {
        let text = serde_json::to_string_pretty(value).expect("serialize fixture JSON");
        self.file(path, &format!("{text}\n"))
    }

    /// Replaces the first `needle` in the repo-relative `path` with
    /// `replacement`, asserting the needle is present.
    pub fn replace(self, path: &str, needle: &str, replacement: &str) -> Self {
        let full = self.path().join(path);
        let text = fs::read_to_string(&full).expect("read file to mutate");
        // A CRLF working copy (core.autocrlf) still matches LF-written needles.
        let (needle, replacement) = if text.contains("\r\n") {
            (
                needle.replace('\n', "\r\n"),
                replacement.replace('\n', "\r\n"),
            )
        } else {
            (needle.to_owned(), replacement.to_owned())
        };
        assert!(text.contains(&needle), "{path} must contain {needle:?}");
        fs::write(&full, text.replacen(&needle, &replacement, 1)).expect("write mutated file");
        self
    }
}

/// The `demo` family: one fixture, two capabilities (`demo.extra` is never a
/// scenario action), one consumer obligation.
pub fn demo_pack() -> Value {
    json!({
        "schemaVersion": 1,
        "familyId": "demo",
        "familyVersion": 1,
        "domainOwner": {"rustCrate": "classic-demo-core"},
        "fixtureRoot": "tests/fixtures/demo",
        "fixtures": {"one": "one.json"},
        "capabilities": [
            {"id": "demo.observe", "rustSymbols": ["observe"], "observationFamilies": ["values"]},
            {"id": "demo.extra", "rustSymbols": ["extra"], "observationFamilies": ["values"]}
        ],
        "scenarios": [{
            "id": "first",
            "action": "demo.observe",
            "capabilityIds": ["demo.observe", "demo.extra"],
            "fixtureRefs": ["one"],
            "input": {"fixtureRef": "one"},
            "expected": {"value": 2},
            "normalization": {"rootRelativePaths": false, "unorderedPaths": [], "excludedPaths": []}
        }],
        "consumerObligations": [{"id": "demo.shown"}]
    })
}

/// `participants.json` enrolling CXX in `demo.observe`.
pub fn demo_participants() -> Value {
    json!({
        "schemaVersion": 1,
        "families": [{"familyId": "demo", "cxx": {"capabilityIds": ["demo.observe"]}}]
    })
}

/// `consumer-obligations.json` registering the TUI for `demo.shown`.
pub fn demo_obligations() -> Value {
    json!({
        "schemaVersion": 1,
        "families": [{"familyId": "demo", "consumers": [{
            "id": "tui",
            "executionInstanceIds": ["tui"],
            "sourcePaths": ["ui/src"],
            "obligations": [{"id": "demo.shown", "scenarioIds": ["first"], "expected": {"shown": true}}]
        }]}]
    })
}

pub const PACK: &str = "tests/conformance/packs/demo/v1.json";
pub const PARTICIPANTS: &str = "tests/conformance/participants.json";
pub const OBLIGATIONS: &str = "tests/conformance/consumer-obligations.json";

/// A git repository holding the demo pack, its fixture and both catalogs,
/// each replaceable through the arguments.
pub fn demo_repo(pack: &Value, participants: &Value, obligations: &Value) -> FixtureRepo {
    let repo = git_repo()
        .json(PACK, pack)
        .json(
            "tests/fixtures/demo/one.json",
            &json!({"request": {"value": 1}}),
        )
        .json(PARTICIPANTS, participants)
        .json(OBLIGATIONS, obligations);
    fs::create_dir_all(repo.path().join("ui/src")).expect("create consumer source dir");
    repo
}

/// Runs `conformance check` and returns its findings as
/// `path:line: rule: message` lines (empty on a pass).
pub fn check(root: &RepoRoot) -> Vec<String> {
    let args = conformance::Args {
        command: ConformanceCommand::Check(CheckArgs::default()),
    };
    match conformance::run(root, args).expect("check runs") {
        Outcome::Pass { .. } => Vec::new(),
        Outcome::Fail { findings, .. } => findings.iter().map(ToString::to_string).collect(),
    }
}

/// [`check`]'s findings without the workflow policy, for fixture trees that
/// carry no workflows.
pub fn input_findings(repo: &FixtureRepo) -> Vec<String> {
    check(&repo.root())
        .into_iter()
        .filter(|finding| !finding.contains(": workflow-policy: "))
        .collect()
}

/// Copies `relative` (file or directory) from the real repository.
fn copy_real(repo: &FixtureRepo, relative: &str) {
    let source = real_root().join(relative);
    let target = repo.path().join(relative);
    if source.is_dir() {
        for entry in walkdir::WalkDir::new(&source) {
            let entry = entry.expect("walk real tree");
            let destination =
                target.join(entry.path().strip_prefix(&source).expect("under source"));
            if entry.file_type().is_dir() {
                fs::create_dir_all(&destination).expect("create copied dir");
            } else {
                fs::copy(entry.path(), &destination).expect("copy real file");
            }
        }
    } else {
        fs::create_dir_all(target.parent().expect("parent")).expect("create parent");
        fs::copy(&source, &target).expect("copy real file");
    }
}

/// A git repository holding a copy of every input `conformance check` reads
/// from the real repository: the workflows, `tests/conformance`,
/// `tests/fixtures`, the vocabulary sources, and empty placeholders for the
/// consumer source paths (only their existence is checked).
pub fn real_inputs() -> FixtureRepo {
    let repo = git_repo();
    for relative in [
        ".github/workflows",
        "tests/conformance",
        "tests/fixtures",
        "business-logic/classic-config-core/src/installed_yaml_data.rs",
        "business-logic/classic-scanlog-core/src/scan_run/contract.rs",
        "business-logic/classic-durable-publication/src/error.rs",
    ] {
        copy_real(&repo, relative);
    }
    let obligations: Value = serde_json::from_str(
        &fs::read_to_string(real_root().join(OBLIGATIONS)).expect("read real obligations"),
    )
    .expect("parse real obligations");
    for family in obligations["families"].as_array().expect("families") {
        for consumer in family["consumers"].as_array().expect("consumers") {
            for path in consumer["sourcePaths"].as_array().expect("sourcePaths") {
                let path = path.as_str().expect("source path");
                let target = repo.path().join(path);
                if real_root().join(path).is_dir() {
                    fs::create_dir_all(&target).expect("create placeholder dir");
                } else {
                    fs::create_dir_all(target.parent().expect("parent")).expect("create parent");
                    fs::write(&target, "").expect("create placeholder file");
                }
            }
        }
    }
    repo
}

/// A repository holding only a copy of the real `.github/workflows`.
pub fn real_workflows() -> FixtureRepo {
    let repo = FixtureRepo::empty();
    copy_real(&repo, ".github/workflows");
    repo
}
