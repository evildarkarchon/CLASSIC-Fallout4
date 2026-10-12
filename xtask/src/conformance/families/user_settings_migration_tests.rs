//! The migration compiler over the real pack and corpus, and the migration
//! normalizer driven with raw observations a correct participant reports.
//!
//! Settings fixtures follow the checkout's line endings, so no test pins their
//! bytes; statuses and tree shapes were recorded from the retired Python
//! engine.

use serde_json::json;

use super::super::tests::PackRepo;
use super::super::{Compiled, Stage, normalize_observation};
use super::*;

const FIXTURES: &str = "tests/fixtures/user_settings_compatibility";

#[test]
fn trees_list_parents_and_sorted_entries() {
    let mut files = BTreeMap::new();
    files.insert("a/b/c.yaml".to_owned(), Content::Bytes(vec![1]));
    files.insert("z".to_owned(), Content::Proposed(json!({"type": "null"})));
    let entries = tree(&files, &["kept".to_owned()]);
    let paths: Vec<&str> = entries
        .iter()
        .map(|entry| entry["path"]["path"].as_str().unwrap())
        .collect();
    assert_eq!(paths, [".", "a", "a/b", "a/b/c.yaml", "kept", "z"]);
    assert_eq!(entries[3]["bytesHex"], "01");
    assert_eq!(entries[5]["proposedYamlNodes"], json!({"type": "null"}));
}

/// The real repository, its compiled expectations and the corpus oracle.
struct Real {
    repo: PackRepo,
    compiled: Compiled,
    oracle: Value,
}

impl Real {
    fn new() -> Self {
        let repo = PackRepo::real("user_settings");
        let compiled = repo.compile().expect("the real pack compiles");
        let oracle = serde_json::from_slice(&Self::corpus(&repo, "expectations.json")).unwrap();
        Self {
            repo,
            compiled,
            oracle,
        }
    }

    fn corpus(repo: &PackRepo, name: &str) -> Vec<u8> {
        std::fs::read(repo.root.join(&format!("{FIXTURES}/{name}"))).expect("read corpus file")
    }

    /// The index of the migrate scenario referencing `id`.
    fn index(&self, id: &str) -> usize {
        self.repo
            .pack
            .scenarios
            .iter()
            .position(|scenario| scenario.expected.get("migrationScenario") == Some(&json!(id)))
            .unwrap_or_else(|| panic!("no scenario {id}"))
    }

    fn expected(&self, id: &str) -> &Map<String, Value> {
        &self.compiled.expected[self.index(id)]
    }

    /// The corpus case behind migration scenario `id`.
    fn case(&self, id: &str) -> &Value {
        let spec = self.oracle["migration_scenarios"]
            .as_array()
            .unwrap()
            .iter()
            .find(|spec| spec["id"] == id)
            .unwrap();
        &self.oracle["migration_cases"][spec["case"].as_str().unwrap()]
    }

    /// The raw observation a correct participant reports for `id`: plans
    /// carry raw YAML review rows and proposal bytes, the reversal is the
    /// exact inverse, revision tokens are real and published files are raw
    /// bytes.
    fn observation(&self, id: &str) -> (Map<String, Value>, Option<Vec<u8>>) {
        let mut actual = self.expected(id).clone();
        let case = self.case(id);
        let proposed = case
            .get("expected_document")
            .and_then(Value::as_str)
            .map(|name| Self::corpus(&self.repo, name));
        if let Some(proposed) = &proposed
            && !actual["planning"]["plan"].is_null()
        {
            let plan = actual["planning"]["plan"].as_object_mut().unwrap();
            plan.remove("proposedYamlNodes");
            plan.insert("proposedHex".into(), json!(digest::hex(proposed)));
            plan.insert("changes".into(), case["changes"].clone());
            let plan = Value::Object(plan.clone());
            let mut inverse = plan.clone();
            inverse["source"] = plan["target"].clone();
            inverse["target"] = plan["source"].clone();
            inverse["baseRevision"] = json!(revision(Some(proposed)));
            inverse["originalHex"] = plan["proposedHex"].clone();
            inverse["proposedHex"] = plan["originalHex"].clone();
            inverse["changes"] = plan["changes"]
                .as_array()
                .unwrap()
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
            actual.insert("reversedPlan".into(), inverse);
            actual.insert("roundTripPlan".into(), plan);
        }
        actual.insert("repeatedPlanning".into(), actual["planning"].clone());
        let token = proposed.as_ref().map(|bytes| revision(Some(bytes)));
        if !actual["apply"]["receipt"].is_null() {
            actual["apply"]["receipt"]["publishedRevision"] = json!(token);
        }
        if actual["restore"]["expectedRevision"] == PROPOSED_REVISION {
            actual["restore"]["expectedRevision"] = json!(token);
        }
        for checkpoint in ["afterPlanningTree", "afterApplyTree", "finalTree"] {
            for entry in actual[checkpoint].as_array_mut().unwrap() {
                if let Some(entry) = entry.as_object_mut()
                    && entry.remove("proposedYamlNodes").is_some()
                {
                    entry.insert(
                        "bytesHex".into(),
                        json!(digest::hex(proposed.as_ref().unwrap())),
                    );
                }
            }
        }
        (actual, proposed)
    }

    fn normalize(
        &self,
        id: &str,
        actual: Map<String, Value>,
    ) -> Result<Map<String, Value>, NormalizationError> {
        normalize_observation(
            "user-settings",
            "user-settings.migrate",
            Stage::AfterDeclared,
            self.expected(id).clone(),
            actual,
        )
        .map(|(_, actual)| actual)
    }
}

#[test]
fn migrations_compile_their_checkpoints_from_the_corpus() {
    let real = Real::new();
    let expected = real.expected("migration-previous-restore");
    let paths = |checkpoint: &str| -> Vec<String> {
        expected[checkpoint]
            .as_array()
            .unwrap()
            .iter()
            .map(|entry| entry["path"]["path"].as_str().unwrap().to_owned())
            .collect()
    };
    assert_eq!(
        paths("afterPlanningTree"),
        [".", "CLASSIC Data", "CLASSIC Data/CLASSIC Settings.yaml"]
    );
    let after_apply = paths("afterApplyTree");
    assert_eq!(after_apply.len(), 9, "{after_apply:?}");
    assert_eq!(
        &after_apply[5..],
        [
            "CLASSIC Data",
            "CLASSIC Data/CLASSIC Settings.yaml",
            SETTINGS,
            LOCK
        ]
    );
    // Restoring a legacy-location source removes the published canonical
    // document but keeps the backup directories.
    let final_tree = paths("finalTree");
    assert_eq!(final_tree.len(), 8, "{final_tree:?}");
    assert!(!final_tree.contains(&SETTINGS.to_owned()));
    assert_eq!(expected["apply"]["status"], "applied");
    assert_eq!(
        expected["apply"]["receipt"]["publishedRevision"],
        PROPOSED_REVISION
    );
    assert_eq!(
        expected["apply"]["receipt"]["source"],
        json!({"location": "legacy", "schemaVersion": null})
    );
    assert_eq!(expected["restore"]["status"], "restored");

    let stale = real.expected("migration-stale-restore");
    assert_eq!(stale["restore"]["status"], "conflict");
    assert_eq!(stale["restore"]["expectedRevision"], PROPOSED_REVISION);

    let unsupported = real.expected("migration-unsupported");
    assert_eq!(unsupported["planning"]["status"], "unsupported");
    assert_eq!(unsupported["planning"]["plan"], Value::Null);
    assert_eq!(unsupported["reversedPlan"], Value::Null);

    let review = real.expected("migration-review-only");
    let rows = review["planning"]["plan"]["changes"].as_array().unwrap();
    let field = rows
        .iter()
        .find(|row| row["kind"] == "field_transition")
        .expect("a field transition row");
    assert!(field["after"]["type"].is_string(), "{field}");
}

#[test]
fn every_migration_normalizes_a_correct_raw_observation_to_its_expectation() {
    let real = Real::new();
    let ids: Vec<String> = real.oracle["migration_scenarios"]
        .as_array()
        .unwrap()
        .iter()
        .map(|spec| spec["id"].as_str().unwrap().to_owned())
        .collect();
    assert_eq!(ids.len(), 17);
    for id in &ids {
        let (actual, _) = real.observation(id);
        assert_eq!(
            real.normalize(id, actual),
            Ok(real.expected(id).clone()),
            "{id}"
        );
    }
}

/// Seeds one defect into a raw migration observation.
type Mutation = fn(&mut Map<String, Value>);

#[test]
fn migration_evidence_must_authenticate() {
    let real = Real::new();
    let seeds: [(&str, &str, Mutation); 8] = [
        (
            "migration-flat-restore",
            "planning is not deterministic",
            |actual| {
                actual["repeatedPlanning"]["status"] = json!("unsupported");
            },
        ),
        (
            "migration-flat-restore",
            "reversal is not the exact inverse",
            |actual| {
                actual["reversedPlan"]["changes"]
                    .as_array_mut()
                    .unwrap()
                    .reverse();
            },
        ),
        (
            "migration-flat-restore",
            "double reversal changed the plan",
            |actual| {
                actual["roundTripPlan"]["required"] = json!(false);
            },
        ),
        (
            "migration-flat-restore",
            "base revision does not match",
            |actual| {
                actual["planning"]["plan"]["baseRevision"] = json!("sha256:00");
                actual["repeatedPlanning"]["plan"]["baseRevision"] = json!("sha256:00");
            },
        ),
        (
            "migration-flat-restore",
            "published revision does not match",
            |actual| {
                actual["apply"]["receipt"]["publishedRevision"] = json!(PROPOSED_REVISION);
            },
        ),
        (
            "migration-flat-restore",
            "differ from the approved proposal",
            |actual| {
                for entry in actual["afterApplyTree"].as_array_mut().unwrap() {
                    if entry["path"]["path"] == SETTINGS {
                        entry["bytesHex"] = json!("00");
                    }
                }
            },
        ),
        (
            "migration-flat-restore",
            "raw regular-file byte evidence",
            |actual| {
                for entry in actual["afterApplyTree"].as_array_mut().unwrap() {
                    if entry["path"]["path"] == SETTINGS {
                        entry["kind"] = json!("directory");
                    }
                }
            },
        ),
        (
            "migration-stale-restore",
            "not anchored to the published revision",
            |actual| {
                actual["restore"]["expectedRevision"] = json!("sha256:00");
            },
        ),
    ];
    for (id, text, mutate) in seeds {
        let (mut actual, _) = real.observation(id);
        mutate(&mut actual);
        let error = real.normalize(id, actual).unwrap_err();
        assert_eq!(error.path, "$.planning", "{id} {text}: {error:?}");
        assert!(error.message.contains(text), "{id} {text}: {error:?}");
    }
}
