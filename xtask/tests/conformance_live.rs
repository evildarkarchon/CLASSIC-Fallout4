//! The live-repository conformance test.
//!
//! `check` passes over the real repository, and then, for every pack, a fake
//! Rust participant (no process is spawned) answers the real run plans:
//!
//! - a receipt reporting what a correct participant reports validates: the
//!   compiled expectation itself, except where a family normalization
//!   authenticates raw evidence (autoscan-report's execution root and
//!   expanded report bytes, user-settings' published bytes and migration
//!   plans), which the receipt then carries;
//! - a receipt whose first observation gains one member fails that family,
//!   and only with `semantic_conformance_mismatch` at that member.
//!
//! This replaces the retired Python engine's per-family lifecycle tests.

mod common;

use std::collections::BTreeMap;
use std::time::Duration;

use common::conformance::{Evidence, read_plan, real_root, receipt_for};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use xtask::conformance::{
    Attempt, CommandTable, Launch, Participant, ParticipantCommand, RunArgs, expectations,
    run_participant,
};
use xtask::{Outcome, RepoRoot};

/// The user-settings corpus and oracle.
const CORPUS: &str = "tests/fixtures/user_settings_compatibility";
/// The canonical settings document in a user-settings tree.
const SETTINGS: &str = "CLASSIC Settings.yaml";
/// The placeholder migration expectations use for the proposed revision.
const PROPOSED_REVISION: &str = "<verified-proposed-revision>";
/// The execution root the fake autoscan participant reports.
const EXECUTION_ROOT: &str = r"C:\conformance\run";

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn unhex(text: &str) -> Vec<u8> {
    (0..text.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&text[index..index + 2], 16).expect("hex"))
        .collect()
}

fn revision(bytes: &[u8]) -> String {
    format!("sha256:{}", hex(&Sha256::digest(bytes)))
}

fn replace(data: &[u8], needle: &[u8], replacement: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut index = 0;
    while index < data.len() {
        if data[index..].starts_with(needle) {
            out.extend_from_slice(replacement);
            index += needle.len();
        } else {
            out.push(data[index]);
            index += 1;
        }
    }
    out
}

/// Reports a correct participant writes for an autoscan scenario: the
/// execution root, and FCX path tokens expanded in the report bytes.
fn autoscan(expected: &Value) -> Value {
    let mut actual = expected.clone();
    actual["executionRoot"] = json!(EXECUTION_ROOT);
    let fcx = expected["semanticInputs"]["fcxMode"]
        .as_bool()
        .expect("fcxMode");
    for report in actual["durableEffects"]["reports"]
        .as_array_mut()
        .expect("reports")
    {
        let mut data = unhex(report["bytesHex"].as_str().expect("bytesHex"));
        if fcx {
            for (token, value) in [
                ("{{FCX_GAME_ROOT}}", format!(r"{EXECUTION_ROOT}\fcx-game")),
                (
                    "{{FCX_DOCUMENTS_ROOT}}",
                    format!(r"{EXECUTION_ROOT}\fcx-documents"),
                ),
                ("{{PATH_SEPARATOR}}", r"\".to_owned()),
            ] {
                data = replace(&data, token.as_bytes(), value.as_bytes());
            }
        }
        report["bytesHex"] = json!(hex(&data));
        report["sha256"] = json!(hex(&Sha256::digest(&data)));
        report["byteLength"] = json!(data.len());
    }
    actual
}

/// The user-settings corpus oracle and file reader.
struct Corpus {
    oracle: Value,
    /// Authored user-settings expectations by scenario ID; they name the
    /// corpus case each compiled expectation came from.
    authored: BTreeMap<String, Value>,
}

impl Corpus {
    fn load() -> Self {
        let pack: Value = serde_json::from_slice(
            &std::fs::read(real_root().join("tests/conformance/packs/user_settings/v1.json"))
                .expect("read the user-settings pack"),
        )
        .expect("pack JSON");
        let authored = pack["scenarios"]
            .as_array()
            .expect("scenarios")
            .iter()
            .map(|scenario| {
                (
                    scenario["id"].as_str().expect("id").to_owned(),
                    scenario["expected"].clone(),
                )
            })
            .collect();
        Self {
            oracle: serde_json::from_slice(&Self::read("expectations.json")).expect("oracle JSON"),
            authored,
        }
    }

    fn read(name: &str) -> Vec<u8> {
        std::fs::read(real_root().join(CORPUS).join(name)).expect("read corpus file")
    }

    /// What a correct participant reports for a user-settings scenario.
    fn observation(&self, id: &str, expected: &Value) -> Value {
        let authored = &self.authored[id];
        if expected.get("planning").is_some() {
            return self.migration(authored, expected);
        }
        if expected["commit"]["status"] == "committed" {
            return self.committed(authored, expected);
        }
        expected.clone()
    }

    /// A committed update reports its published bytes and their revision.
    fn committed(&self, authored: &Value, expected: &Value) -> Value {
        let operation = authored["operationScenario"]
            .as_str()
            .expect("operationScenario");
        let published = self.oracle["operation_scenarios"]
            .as_array()
            .expect("operation_scenarios")
            .iter()
            .find(|entry| entry["id"] == operation)
            .and_then(|entry| entry["expected_document"].as_str())
            .map(Self::read)
            .expect("published document");
        let mut actual = expected.clone();
        actual["commit"]["revision"] = json!(revision(&published));
        for entry in actual["finalTree"].as_array_mut().expect("finalTree") {
            if entry["path"] == json!({"path": SETTINGS}) {
                *entry = json!({"path": {"path": SETTINGS}, "kind": "file", "bytesHex": hex(&published)});
            }
        }
        actual
    }

    /// A migration reports raw plans, an exact inverse, real revisions and
    /// raw published bytes.
    fn migration(&self, authored: &Value, expected: &Value) -> Value {
        let id = authored["migrationScenario"]
            .as_str()
            .expect("migrationScenario");
        let spec = self.oracle["migration_scenarios"]
            .as_array()
            .expect("migration_scenarios")
            .iter()
            .find(|spec| spec["id"] == id)
            .expect("migration spec");
        let case = &self.oracle["migration_cases"][spec["case"].as_str().expect("case")];
        let proposed = case["expected_document"].as_str().map(Self::read);
        let mut actual = expected.clone();
        if let Some(proposed) = &proposed
            && !actual["planning"]["plan"].is_null()
        {
            let plan = actual["planning"]["plan"].as_object_mut().expect("plan");
            plan.remove("proposedYamlNodes");
            plan.insert("proposedHex".into(), json!(hex(proposed)));
            plan.insert("changes".into(), case["changes"].clone());
            let plan = Value::Object(plan.clone());
            let mut inverse = plan.clone();
            inverse["source"] = plan["target"].clone();
            inverse["target"] = plan["source"].clone();
            inverse["baseRevision"] = json!(revision(proposed));
            inverse["originalHex"] = plan["proposedHex"].clone();
            inverse["proposedHex"] = plan["originalHex"].clone();
            inverse["changes"] = plan["changes"]
                .as_array()
                .expect("changes")
                .iter()
                .rev()
                .map(|row| {
                    let mut reversed = row.clone();
                    reversed["sourcePath"] = row["targetPath"].clone();
                    reversed["targetPath"] = row["sourcePath"].clone();
                    reversed["before"] = row["after"].clone();
                    reversed["after"] = row["before"].clone();
                    reversed
                })
                .collect();
            actual["reversedPlan"] = inverse;
            actual["roundTripPlan"] = plan;
        }
        actual["repeatedPlanning"] = actual["planning"].clone();
        let token = proposed.as_deref().map(revision);
        if !actual["apply"]["receipt"].is_null() {
            actual["apply"]["receipt"]["publishedRevision"] = json!(token);
        }
        if actual["restore"]["expectedRevision"] == PROPOSED_REVISION {
            actual["restore"]["expectedRevision"] = json!(token);
        }
        for checkpoint in ["afterPlanningTree", "afterApplyTree", "finalTree"] {
            for entry in actual[checkpoint].as_array_mut().expect("checkpoint tree") {
                if let Some(entry) = entry.as_object_mut()
                    && entry.remove("proposedYamlNodes").is_some()
                {
                    entry.insert(
                        "bytesHex".into(),
                        json!(hex(proposed.as_ref().expect("proposed bytes"))),
                    );
                }
            }
        }
        actual
    }
}

/// Sends the requests a correct participant sends the controlled update
/// service: each scripted response once, in order, with the conditional
/// header it expects; a stalled response is abandoned at a short timeout.
fn follow_service_script(launch: &Launch, plan: &Value) {
    let Some(service) = launch.env.get("CLASSIC_CONFORMANCE_SERVICE") else {
        return;
    };
    for scenario in plan["scenarios"].as_array().expect("scenarios") {
        let id = scenario["id"].as_str().expect("id");
        let fixture = plan["fixtures"][scenario["input"]["fixtureRef"]
            .as_str()
            .expect("fixtureRef")]
        .as_str()
        .expect("fixture path");
        let fixture: Value = serde_json::from_slice(&std::fs::read(fixture).expect("read fixture"))
            .expect("fixture JSON");
        for (route, path) in [
            ("pages", "pages"),
            ("api", "api/repos/conformance/updates/releases"),
        ] {
            for response in fixture["service"][route].as_array().expect("route queue") {
                let stall = response["stall"] == true;
                let timeout = if stall {
                    Duration::from_millis(200)
                } else {
                    Duration::from_secs(10)
                };
                let agent = ureq::Agent::new_with_config(
                    ureq::Agent::config_builder()
                        .http_status_as_error(false)
                        .timeout_global(Some(timeout))
                        .build(),
                );
                let mut request = agent.get(&format!("{service}/{id}/{path}"));
                if let Some(tag) = response["ifNoneMatch"].as_str() {
                    request = request.header("If-None-Match", tag);
                }
                let result = request.call();
                assert_eq!(result.is_err(), stall, "{id}/{route}: {result:?}");
            }
        }
    }
}

/// A table whose every Rust command binds only the xtask manifest, so source
/// identities stay cheap; nothing is ever spawned.
fn table() -> CommandTable {
    CommandTable::new(|_, _| {
        Some(ParticipantCommand {
            program: "fake-participant".into(),
            args: Vec::new(),
            source_paths: vec!["xtask/Cargo.toml".into()],
            timeout: Duration::from_secs(5),
            wrapper: false,
        })
    })
}

/// Runs Rust over every family of the real repository with a fake runner
/// whose observation for `(family, scenario index, expected)` comes from
/// `observe`.
fn run_all(observe: &dyn Fn(&str, usize, &str, &Value) -> Value) -> (Outcome, usize) {
    let root = RepoRoot::new(real_root());
    let all: BTreeMap<String, BTreeMap<String, Value>> = expectations(&root).expect("clean inputs");
    let artifacts = tempfile::tempdir().expect("artifact dir");
    let mut launches = 0;
    let mut runner = |launch: &Launch| -> Attempt {
        launches += 1;
        let plan = read_plan(launch);
        follow_service_script(launch, &plan);
        let family = launch.family_id.as_str();
        let expected: &BTreeMap<String, Value> = &all[family];
        let index = std::cell::Cell::new(0);
        let receipt = receipt_for(
            &plan,
            |scenario| {
                let position = index.get();
                index.set(position + 1);
                let id = scenario["id"].as_str().expect("scenario id");
                Evidence::Observed(observe(family, position, id, &expected[id]))
            },
            |_| unreachable!("Rust plans carry scenarios"),
        );
        std::fs::write(
            &launch.receipt,
            serde_json::to_vec(&receipt).expect("receipt JSON"),
        )
        .expect("write receipt");
        Attempt::exited(0)
    };
    let args = RunArgs {
        participant: Participant::Rust,
        compiler: None,
        preset: "default".into(),
        families: Vec::new(),
        artifact_root: artifacts.path().to_path_buf(),
    };
    let outcome =
        run_participant(&root, &args, &table(), &mut runner, &mut |_| {}).expect("run starts");
    (outcome, launches)
}

/// What a correct participant reports.
fn correct(corpus: &Corpus, family: &str, id: &str, expected: &Value) -> Value {
    match family {
        "autoscan-report" => autoscan(expected),
        "user-settings" => corpus.observation(id, expected),
        _ => expected.clone(),
    }
}

#[test]
fn every_pack_validates_correct_receipts_and_rejects_a_mutated_observation() {
    let root = RepoRoot::new(real_root());
    let check = xtask::conformance::run(
        &root,
        xtask::conformance::Args {
            command: xtask::conformance::Command::Check(Default::default()),
        },
    )
    .expect("check runs");
    assert!(matches!(check, Outcome::Pass { .. }), "{check:?}");

    let corpus = Corpus::load();
    let (outcome, launches) =
        run_all(&|family, _, id, expected| correct(&corpus, family, id, expected));
    assert_eq!(launches, 86, "one Rust invocation per pack");
    assert_eq!(
        outcome,
        Outcome::Pass {
            summary: "conformance run rust/rust: 86 families passed".into()
        }
    );

    let (outcome, _) = run_all(&|family, position, id, expected| {
        let mut observation = correct(&corpus, family, id, expected);
        if position == 0 {
            observation["conformanceMutation"] = json!(true);
        }
        observation
    });
    let Outcome::Fail { findings, summary } = outcome else {
        panic!("mutated observations must fail");
    };
    assert!(summary.contains("86 of 86 families failed"), "{summary}");
    let mut failed: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for finding in &findings {
        let family = finding
            .message
            .split(' ')
            .next()
            .expect("family")
            .to_owned();
        failed
            .entry(family)
            .or_default()
            .push(format!("{}: {}", finding.rule, finding.message));
    }
    assert_eq!(failed.len(), 86, "{failed:#?}");
    for (family, messages) in &failed {
        assert_eq!(messages.len(), 1, "{family}: {messages:#?}");
        assert!(
            messages[0].starts_with("semantic_conformance_mismatch: ")
                && messages[0]
                    .ends_with("at $.conformanceMutation: exact observation differs: extra_field"),
            "{family}: {messages:#?}"
        );
    }
}
