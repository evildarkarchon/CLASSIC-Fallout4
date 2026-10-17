//! Shared fixtures for the conformance engine's sibling tests: a throwaway
//! git repository holding one `demo` pack, its fixture, both catalogs and a
//! participant source file.

use std::path::Path;
use std::process::Command;

use serde_json::{Value, json};

use super::*;

/// Runs git in `dir`, asserting success.
pub(crate) fn git(dir: &Path, args: &[&str]) {
    let status = Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .expect("git is on PATH");
    assert!(status.success(), "git {args:?} failed");
}

/// `git init` plus one empty commit, so `HEAD` names a revision. Signing is
/// off for this throwaway repository only.
pub(crate) fn init_repository(dir: &Path) {
    git(dir, &["init", "-q"]);
    git(
        dir,
        &[
            "-c",
            "user.name=xtask",
            "-c",
            "user.email=xtask@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "fixture",
        ],
    );
}

/// The demo pack: two scenarios over one fixture each, one capability CXX
/// enrols, and one consumer obligation.
pub(crate) fn demo_pack() -> Value {
    let normalization =
        json!({"rootRelativePaths": false, "unorderedPaths": [], "excludedPaths": []});
    json!({
        "schemaVersion": 1,
        "familyId": "demo",
        "familyVersion": 1,
        "domainOwner": {"rustCrate": "classic-demo-core"},
        "fixtureRoot": "tests/fixtures/demo",
        "fixtures": {"one": "one.json", "two": "two.json"},
        "capabilities": [
            {"id": "demo.observe", "rustSymbols": ["observe"], "observationFamilies": ["values"]},
            {"id": "demo.other", "rustSymbols": ["other"], "observationFamilies": ["values"]}
        ],
        "scenarios": [
            {
                "id": "first",
                "action": "demo.observe",
                "capabilityIds": ["demo.observe"],
                "fixtureRefs": ["one"],
                "input": {"fixtureRef": "one"},
                "expected": {"value": 2, "items": ["a", "b"]},
                "normalization": normalization
            },
            {
                "id": "second",
                "action": "demo.other",
                "capabilityIds": ["demo.other"],
                "fixtureRefs": ["two"],
                "input": {"fixtureRef": "two"},
                "expected": {"value": 3},
                "normalization": normalization
            }
        ],
        "consumerObligations": [{"id": "demo.shown"}]
    })
}

/// A demo repository on disk.
pub(crate) struct Demo {
    _dir: tempfile::TempDir,
    pub root: RepoRoot,
}

impl Demo {
    /// Builds the demo repository with `pack` as its only pack.
    pub fn with(pack: &Value) -> Self {
        let dir = tempfile::tempdir().expect("temp dir");
        let path = dir.path().canonicalize().expect("canonical temp dir");
        let write = |relative: &str, value: &Value| {
            let full = path.join(relative);
            std::fs::create_dir_all(full.parent().expect("parent")).expect("create dir");
            std::fs::write(full, serde_json::to_string_pretty(value).expect("json"))
                .expect("write");
        };
        write("tests/conformance/packs/demo/v1.json", pack);
        write(
            "tests/fixtures/demo/one.json",
            &json!({"request": {"value": 1}}),
        );
        write(
            "tests/fixtures/demo/two.json",
            &json!({"request": {"value": 2}}),
        );
        write(
            "tests/conformance/participants.json",
            &json!({"schemaVersion": 1, "families": [{"familyId": "demo", "cxx": {"capabilityIds": ["demo.observe"]}}]}),
        );
        write(
            "tests/conformance/consumer-obligations.json",
            &json!({"schemaVersion": 1, "families": [{"familyId": "demo", "consumers": [{
                "id": "tui",
                "executionInstanceIds": ["tui"],
                "sourcePaths": ["ui/src"],
                "obligations": [{"id": "demo.shown", "scenarioIds": ["first"], "expected": {"shown": true}}]
            }]}]}),
        );
        std::fs::create_dir_all(path.join("ui/src")).expect("consumer sources");
        std::fs::write(path.join("ui/src/main.rs"), "fn main() {}\n").expect("consumer source");
        std::fs::create_dir_all(path.join("runner")).expect("runner dir");
        std::fs::write(path.join("runner/demo.rs"), "// runner\n").expect("runner source");
        init_repository(&path);
        Self {
            _dir: dir,
            root: RepoRoot::new(path),
        }
    }

    /// The demo repository with [`demo_pack`].
    pub fn new() -> Self {
        Self::with(&demo_pack())
    }

    /// Loads, validates and prepares the demo pack, with the applicability.
    pub fn prepare(&self) -> (LoadedPack, PreparedPack, Applicability) {
        let mut findings = Vec::new();
        let packs = pack::load_all(&self.root, &mut findings).expect("load packs");
        let applicability =
            applicability::derive(&self.root, &packs, &mut findings).expect("derive applicability");
        assert_eq!(findings, Vec::new(), "the demo inputs are clean");
        let loaded = packs.loaded.into_iter().next().expect("one pack");
        let prepared = plan::prepare(&self.root, &loaded).expect("prepare demo pack");
        (loaded, prepared, applicability)
    }

    /// A Rust plan over every demo scenario, bound to `runner/demo.rs`.
    pub fn rust_plan(&self, prepared: &PreparedPack) -> Value {
        plan::build(
            &self.root,
            prepared,
            &PlanRequest {
                participant: "rust".into(),
                role: Role::SemanticAdapter,
                instance: "rust".into(),
                source_paths: vec!["runner/demo.rs".into()],
                payload: Payload::Scenarios(vec!["first".into(), "second".into()]),
            },
        )
        .expect("build plan")
    }
}

/// The receipt a correct participant writes for `plan`: the envelope echoed,
/// and each planned scenario completed with `observation(id)`.
pub(crate) fn receipt_for(plan: &Value, observation: impl Fn(&str) -> Value) -> Value {
    let scenarios: Vec<Value> = plan["scenarios"]
        .as_array()
        .expect("scenarios")
        .iter()
        .map(|scenario| {
            let id = scenario["id"].as_str().expect("id");
            json!({
                "id": id,
                "executionStatus": "completed",
                "capabilityIds": scenario["capabilityIds"],
                "observation": observation(id),
                "failure": null
            })
        })
        .collect();
    json!({
        "schemaVersion": plan["schemaVersion"],
        "familyId": plan["familyId"],
        "familyVersion": plan["familyVersion"],
        "expectationDigest": plan["expectationDigest"],
        "invocation": plan["invocation"],
        "participant": plan["participant"],
        "runner": {"id": "demo-runner", "version": 1, "platform": "windows", "toolchain": "rust"},
        "scenarios": scenarios
    })
}

/// The demo pack's expected observation for scenario `id`.
pub(crate) fn demo_expected(id: &str) -> Value {
    match id {
        "first" => json!({"value": 2, "items": ["a", "b"]}),
        "second" => json!({"value": 3}),
        other => panic!("no demo scenario {other}"),
    }
}
