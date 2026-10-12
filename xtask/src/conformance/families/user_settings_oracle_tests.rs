//! The user-settings compiler over the real pack and corpus, its oracle
//! agreement checks (seeded into the real pack), and the committed-update
//! normalizer.
//!
//! Expected literals were recorded from the retired Python engine. Settings
//! fixtures are text files whose line endings follow the checkout, so no test
//! pins their bytes; byte-derived members are checked against the fixture
//! files instead.

use super::super::tests::PackRepo;
use super::super::{Stage, normalize_observation};
use super::*;

const FIXTURES: &str = "tests/fixtures/user_settings_compatibility";

fn real() -> PackRepo {
    PackRepo::real("user_settings")
}

/// The scenario index whose authored expectation is `{key: value}`.
fn index_referencing(repo: &PackRepo, key: &str, value: &str) -> usize {
    repo.pack
        .scenarios
        .iter()
        .position(|scenario| scenario.expected.get(key) == Some(&json!(value)))
        .unwrap_or_else(|| panic!("no scenario references {key} {value}"))
}

/// Bytes of a corpus file in the real repository.
fn corpus(name: &str) -> Vec<u8> {
    std::fs::read(real().root.join(&format!("{FIXTURES}/{name}"))).expect("read corpus file")
}

#[test]
fn truthiness_follows_python() {
    for falsy in [
        json!(null),
        json!(false),
        json!(0),
        json!(""),
        json!([]),
        json!({}),
    ] {
        assert!(!truthy(&falsy), "{falsy}");
    }
    for value in [
        json!(true),
        json!(1),
        json!("x"),
        json!([0]),
        json!({"a": 0}),
    ] {
        assert!(truthy(&value), "{value}");
    }
}

#[test]
fn open_cases_compile_from_the_corpus() {
    let repo = real();
    let compiled = repo.compile().expect("the real pack compiles");
    let missing = index_referencing(&repo, "compatibilityCase", "missing_document");
    assert_eq!(
        Value::Object(compiled.expected[missing].clone()),
        json!({
            "commitEligibility": "eligible",
            "diagnostics": [],
            "durableEffects": {"treeUnchanged": true},
            "originalContent": {"matchesSourceBytes": true, "present": false},
            "revision": {"kind": "missing", "matchesSourceBytes": true},
            "source": {"classification": "missing", "location": "missing", "path": null},
            "view": {
                "fcx_mode": false, "game_version": "auto", "max_concurrent_scans": 0,
                "move_unsolved_logs": true, "show_formid_values": false,
                "simplify_logs": false, "update_check": true
            }
        })
    );
    let current = index_referencing(&repo, "compatibilityCase", "canonical_current_nested");
    assert_eq!(
        Value::Object(compiled.expected[current].clone()),
        json!({
            "commitEligibility": "eligible",
            "diagnostics": [],
            "durableEffects": {"treeUnchanged": true},
            "originalContent": {"matchesSourceBytes": true, "present": true},
            "revision": {"kind": "sha256", "matchesSourceBytes": true},
            "source": {
                "classification": "current",
                "location": "canonical",
                "path": {"path": "CLASSIC Settings.yaml"}
            },
            "view": {
                "formid_databases": {"Fallout4": ["databases/Fallout4 FormIDs.db"]},
                "game_version": "auto",
                "max_concurrent_scans": 0,
                "move_unsolved_logs": true,
                "scan_formid_databases": {
                    "Fallout4": ["databases/Fallout4 FormIDs.db"],
                    "Fallout4VR": ["databases/Fallout4 FormIDs.db"]
                },
                "update_check": true
            }
        })
    );
}

#[test]
fn committed_and_conflicting_updates_compile_from_the_corpus() {
    let repo = real();
    let compiled = repo.compile().expect("the real pack compiles");
    let source = corpus("unknown_entries.yaml");
    let commit = index_referencing(
        &repo,
        "operationScenario",
        "commit_one_canonical_field_without_losing_unknowns",
    );
    let expected = &compiled.expected[commit];
    assert_eq!(
        expected["preview"],
        json!({
            "status": "accepted",
            "baseRevision": revision(Some(&source)),
            "acceptedFields": [{"fieldPath": "/CLASSIC_Settings/Update Check", "value": false}],
            "diagnostics": []
        })
    );
    assert_eq!(
        expected["commit"],
        json!({
            "status": "committed",
            "revision": {"matchesPublishedBytes": true},
            "expectedRevision": null,
            "actualRevision": null,
            "diagnostics": []
        })
    );
    let tree = expected["finalTree"].as_array().unwrap();
    assert_eq!(tree[0], json!({"path": {"path": "."}, "kind": "directory"}));
    assert_eq!(
        tree[1]["yamlNodes"]["value"]["CLASSIC_Settings"]["value"]["Update Check"],
        json!({"type": "boolean", "value": false})
    );
    assert_eq!(
        tree[2],
        json!({"path": {"path": LOCK}, "kind": "file", "bytesHex": ""})
    );

    let stale = index_referencing(&repo, "operationScenario", "refuse_stale_revision");
    let commit = &compiled.expected[stale]["commit"];
    assert_eq!(commit["status"], "conflict");
    assert_eq!(commit["revision"], Value::Null);
    assert_ne!(commit["expectedRevision"], commit["actualRevision"]);
}

#[test]
fn the_legacy_import_keeps_content_addressed_backups() {
    let repo = real();
    let compiled = repo.compile().expect("the real pack compiles");
    let index = repo
        .pack
        .scenarios
        .iter()
        .position(|scenario| scenario.action == "user-settings.legacy-import")
        .expect("a legacy import scenario");
    let files = compiled.expected[index]["files"].as_array().unwrap();
    let paths: Vec<&str> = files
        .iter()
        .map(|file| file["path"].as_str().unwrap())
        .collect();
    assert_eq!(paths.len(), 5, "{paths:?}");
    assert_eq!(&paths[2..], [SETTINGS, LOCK, "state.json"]);
    assert!(paths[0].starts_with("CLASSIC Backup/User Settings/TUI State Imports/"));
    assert_eq!(
        compiled.expected[index]["restore"],
        json!({"status": "restored", "revisionMatches": true, "expectedRevision": null, "actualRevision": null})
    );
}

#[test]
fn the_oracle_and_expected_documents_are_digest_dependencies() {
    let compiled = real().compile().expect("the real pack compiles");
    assert_eq!(compiled.oracles[0], format!("{FIXTURES}/expectations.json"));
    assert_eq!(compiled.oracles.len(), 13);
    assert!(compiled.oracles[1..].is_sorted());
    assert!(
        compiled
            .oracles
            .contains(&format!("{FIXTURES}/flat_migrated.yaml"))
    );
}

/// Seeds one oracle disagreement into the real pack and returns the issue.
fn seeded(mutate: impl FnOnce(&mut Value, &PackRepo)) -> String {
    let probe = real();
    real()
        .edit(|pack| mutate(pack, &probe))
        .compile()
        .unwrap_err()
}

/// Seeds one oracle disagreement into the real pack's JSON.
type PackSeed = fn(&mut Value, &PackRepo);
/// Seeds one defect into a raw committed-update observation (given its
/// published bytes).
type ObservationSeed = fn(&mut Map<String, Value>, &[u8]);

#[test]
fn inputs_and_references_must_agree_with_the_oracle() {
    let cases: [(&str, PackSeed, &str); 8] = [
        (
            "an update input changes",
            |pack, repo| {
                let index = index_referencing(repo, "operationScenario", "refuse_stale_revision");
                pack["scenarios"][index]["input"]["commit"] = json!(false);
            },
            "operation input does not match its independent oracle",
        ),
        (
            "an update names an unknown operation",
            |pack, repo| {
                let index = index_referencing(repo, "operationScenario", "refuse_stale_revision");
                pack["scenarios"][index]["expected"]["operationScenario"] = json!("nope");
            },
            "cover every authored conformance operation exactly once",
        ),
        (
            "an open case is covered twice",
            |pack, repo| {
                let index = index_referencing(repo, "compatibilityCase", "missing_document");
                pack["scenarios"][index]["expected"]["compatibilityCase"] = json!("alias_only");
            },
            "cover every ordinary open compatibility case exactly once",
        ),
        (
            "an open view selection changes",
            |pack, repo| {
                let index = index_referencing(repo, "compatibilityCase", "missing_document");
                pack["scenarios"][index]["input"]["observationFields"]
                    .as_array_mut()
                    .unwrap()
                    .pop();
            },
            "observationFields must exactly select the oracle view",
        ),
        (
            "an open case installs a different document",
            |pack, repo| {
                let index = index_referencing(repo, "compatibilityCase", "alias_only");
                pack["scenarios"][index]["input"]["installationData"][0]["path"] =
                    json!("CLASSIC Data/CLASSIC Settings.yaml");
            },
            "installed input does not match its compatibility case",
        ),
        (
            "a migration control changes",
            |pack, repo| {
                let index = index_referencing(repo, "migrationScenario", "migration-flat-restore");
                pack["scenarios"][index]["input"]["restore"] = json!(false);
            },
            "migration input does not match its independent oracle",
        ),
        (
            "an expected document becomes an input fixture",
            |pack, _| pack["fixtures"]["published"] = json!("flat_migrated.yaml"),
            "expected documents cannot be adapter input fixtures",
        ),
        (
            "the legacy import names another case",
            |pack, repo| {
                let index = repo
                    .pack
                    .scenarios
                    .iter()
                    .position(|s| s.action == "user-settings.legacy-import")
                    .unwrap();
                pack["scenarios"][index]["expected"]["legacyImportCase"] = json!("other");
            },
            "unsupported legacy import expectation",
        ),
    ];
    for (seed, mutate, text) in cases {
        let error = seeded(mutate);
        assert!(error.contains(text), "{seed}: {error}");
    }
}

#[test]
fn the_oracle_must_not_be_an_input_fixture() {
    let error = seeded(|pack, _| pack["fixtures"]["oracle"] = json!("expectations.json"));
    assert!(
        error.contains("cannot be an adapter input fixture"),
        "{error}"
    );
}

/// The raw observation a correct participant reports for the committed
/// update at `index`: the oracle's published bytes and their revision.
fn committed_observation(
    repo: &PackRepo,
    compiled: &Compiled,
    index: usize,
) -> (Map<String, Value>, Vec<u8>) {
    let operation = repo.pack.scenarios[index].expected["operationScenario"]
        .as_str()
        .unwrap();
    let oracle: Value = serde_json::from_slice(&corpus("expectations.json")).unwrap();
    let published = oracle["operation_scenarios"]
        .as_array()
        .unwrap()
        .iter()
        .find(|entry| entry["id"] == operation)
        .and_then(|entry| entry["expected_document"].as_str())
        .map(corpus)
        .unwrap();
    let mut actual = compiled.expected[index].clone();
    actual["commit"]["revision"] = json!(revision(Some(&published)));
    actual["finalTree"][1] = json!({
        "path": {"path": SETTINGS},
        "kind": "file",
        "bytesHex": encode_hex(&published),
    });
    (actual, published)
}

fn normalize_update(
    expected: &Map<String, Value>,
    actual: Map<String, Value>,
) -> Result<Map<String, Value>, NormalizationError> {
    normalize_observation(
        "user-settings",
        "user-settings.update",
        Stage::AfterDeclared,
        expected.clone(),
        actual,
    )
    .map(|(_, actual)| actual)
}

#[test]
fn committed_updates_normalize_authenticated_bytes_to_yaml_nodes() {
    let repo = real();
    let compiled = repo.compile().expect("the real pack compiles");
    let committed: Vec<usize> = (0..repo.pack.scenarios.len())
        .filter(|index| {
            compiled.expected[*index]
                .get("commit")
                .and_then(|c| c.get("status"))
                == Some(&json!("committed"))
        })
        .collect();
    assert!(committed.len() >= 5, "{committed:?}");
    for index in committed {
        let (actual, _) = committed_observation(&repo, &compiled, index);
        assert_eq!(
            normalize_update(&compiled.expected[index], actual),
            Ok(compiled.expected[index].clone()),
            "{}",
            repo.pack.scenarios[index].id
        );
    }
}

#[test]
fn committed_updates_must_carry_authentic_raw_bytes() {
    let repo = real();
    let compiled = repo.compile().expect("the real pack compiles");
    let index = index_referencing(
        &repo,
        "operationScenario",
        "commit_one_canonical_field_without_losing_unknowns",
    );
    let expected = &compiled.expected[index];
    let seeds: [(&str, ObservationSeed); 6] = [
        ("a claimed revision match", |actual, _| {
            actual["commit"]["revision"] = json!({"matchesPublishedBytes": true});
        }),
        ("another revision", |actual, _| {
            actual["commit"]["revision"] = json!(revision(Some(b"other")));
        }),
        ("uppercase hex", |actual, bytes| {
            actual["finalTree"][1]["bytesHex"] = json!(encode_hex(bytes).to_uppercase());
        }),
        ("pre-normalized YAML", |actual, _| {
            let entry = actual["finalTree"][1].as_object_mut().unwrap();
            entry.remove("bytesHex");
            entry.insert("yamlNodes".into(), json!({"type": "null"}));
        }),
        ("two documents", |actual, _| {
            let document = actual["finalTree"][1].clone();
            actual["finalTree"].as_array_mut().unwrap().push(document);
        }),
        ("bytes that are not YAML", |actual, _| {
            let bytes = b"a: [";
            actual["finalTree"][1]["bytesHex"] = json!(encode_hex(bytes));
            actual["commit"]["revision"] = json!(revision(Some(bytes)));
        }),
    ];
    for (seed, mutate) in seeds {
        let (mut actual, bytes) = committed_observation(&repo, &compiled, index);
        mutate(&mut actual, &bytes);
        let error = normalize_update(expected, actual).unwrap_err();
        assert_eq!(error.path, "$.finalTree", "{seed}: {error:?}");
    }
}

#[test]
fn uncommitted_observations_stay_exact() {
    let repo = real();
    let compiled = repo.compile().expect("the real pack compiles");
    let index = index_referencing(&repo, "operationScenario", "refuse_stale_revision");
    let mut actual = compiled.expected[index].clone();
    actual.insert("anything".into(), json!("kept"));
    assert_eq!(
        normalize_update(&compiled.expected[index], actual.clone()),
        Ok(actual)
    );
}
