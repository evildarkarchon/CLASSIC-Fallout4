use serde_json::{Value, json};

use super::*;

fn pack() -> Value {
    json!({
        "schemaVersion": 1,
        "familyId": "demo",
        "familyVersion": 1,
        "domainOwner": {"rustCrate": "classic-demo-core"},
        "fixtureRoot": "tests/fixtures/demo",
        "fixtures": {"one": "one.json"},
        "capabilities": [{"id": "demo.observe", "rustSymbols": ["f"], "observationFamilies": ["values"]}],
        "scenarios": [{
            "id": "first",
            "action": "demo.observe",
            "capabilityIds": ["demo.observe"],
            "fixtureRefs": ["one"],
            "input": {"fixtureRef": "one"},
            "expected": {"value": 1},
            "normalization": {"rootRelativePaths": false, "unorderedPaths": [], "excludedPaths": []}
        }],
        "consumerObligations": []
    })
}

fn deserialize_error(value: Value) -> String {
    serde_json::from_value::<Pack>(value)
        .expect_err("pack must be rejected")
        .to_string()
}

#[test]
fn a_well_formed_pack_deserializes() {
    let pack: Pack = serde_json::from_value(pack()).expect("valid pack");
    assert_eq!(pack.family_id, "demo");
    assert_eq!(pack.scenarios[0].input["fixtureRef"], "one");
    assert!(pack.capabilities[0].rust_crate.is_none());
    assert!(pack.scenarios[0].normalization.optional_empty_files.is_none());
}

#[test]
fn unknown_and_missing_members_and_wrong_types_are_rejected() {
    let mut unknown = pack();
    unknown["capabilities"][0]["operationScoped"] = json!(true);
    assert!(deserialize_error(unknown).contains("unknown field `operationScoped`"));

    let mut missing = pack();
    missing.as_object_mut().unwrap().remove("consumerObligations");
    assert!(deserialize_error(missing).contains("missing field `consumerObligations`"));

    let mut wrong_type = pack();
    wrong_type["scenarios"][0]["normalization"]["rootRelativePaths"] = json!(1);
    assert!(deserialize_error(wrong_type).contains("invalid type"));

    let mut input_not_object = pack();
    input_not_object["scenarios"][0]["input"] = json!(["fixtureRef"]);
    assert!(deserialize_error(input_not_object).contains("invalid type"));
}

#[test]
fn participants_admit_only_the_cxx_enrolment() {
    let catalog: Participants = serde_json::from_value(json!({
        "schemaVersion": 1,
        "families": [{"familyId": "demo", "cxx": {"capabilityIds": ["demo.observe"]}}]
    }))
    .expect("valid catalog");
    assert_eq!(catalog.families[0].cxx.as_ref().unwrap().capability_ids, ["demo.observe"]);

    let error = serde_json::from_value::<Participants>(json!({
        "schemaVersion": 1,
        "families": [{"familyId": "demo", "node": {"capabilityIds": ["demo.observe"]}}]
    }))
    .expect_err("node is not enrollable")
    .to_string();
    assert!(error.contains("unknown field `node`"), "{error}");
}

#[test]
fn consumer_obligations_have_a_closed_shape() {
    let document = json!({
        "schemaVersion": 1,
        "families": [{"familyId": "demo", "consumers": [{
            "id": "cli",
            "executionInstanceIds": ["windows-msvc"],
            "sourcePaths": ["classic-cli/src"],
            "obligations": [{"id": "demo.shown", "scenarioIds": ["first"], "expected": {}}]
        }]}]
    });
    let catalog: ConsumerObligations = serde_json::from_value(document.clone()).expect("valid");
    assert_eq!(catalog.families[0].consumers[0].obligations[0].id, "demo.shown");

    let mut extra = document;
    extra["families"][0]["consumers"][0]["obligations"][0]["owner"] = json!("x");
    assert!(serde_json::from_value::<ConsumerObligations>(extra).is_err());
}

#[test]
fn stable_ids_are_lowercase_words_joined_by_dots_or_hyphens() {
    for valid in ["a", "user-settings", "scan-run.execute", "v2", "a1.b2-c3"] {
        assert!(is_stable_id(valid), "{valid}");
    }
    for invalid in ["", "A", "1a", "a--b", "a.", "-a", "a_b", "a b", "é"] {
        assert!(!is_stable_id(invalid), "{invalid}");
    }
}

#[test]
fn fixture_refs_are_ascii_aliases() {
    for valid in ["a", "validCrashLog", "x_1-y"] {
        assert!(is_fixture_ref(valid), "{valid}");
    }
    for invalid in ["", "1a", "_a", "a.b", "a/b"] {
        assert!(!is_fixture_ref(invalid), "{invalid}");
    }
}

#[test]
fn exact_json_paths_name_one_non_root_node() {
    for valid in ["$.a", "$.a[0].b_c-d", "$[12]", "$._x"] {
        assert!(is_exact_json_path(valid), "{valid}");
    }
    for invalid in ["$", "a", "$.*", "$..a", "$[01]", "$[-1]", "$.a[", "$.1a", "$[*]"] {
        assert!(!is_exact_json_path(invalid), "{invalid}");
    }
}

#[test]
fn relative_paths_are_canonical_and_contained() {
    for valid in ["a", "a/b.json", "CLASSIC Data/x.yaml"] {
        assert!(is_canonical_relative_path(valid), "{valid}");
        assert!(is_relative_file_path(valid), "{valid}");
    }
    for invalid in ["", ".", "..", "a/../b", "./a", "a//b", "a/", "/a", "C:/a", "a\\b"] {
        assert!(!is_canonical_relative_path(invalid), "{invalid}");
    }
    assert!(is_canonical_relative_path("a:b"));
    assert!(!is_relative_file_path("a:b"));
}
