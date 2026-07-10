//! Executable contract checks for the ADR-0004 User Settings compatibility corpus.

use classic_settings_core::{Yaml, parse_yaml_content};
use serde_json::Value;
use std::collections::BTreeSet;
use std::path::PathBuf;

/// Returns the repository-owned compatibility corpus directory.
fn corpus_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("tests/fixtures/user_settings_compatibility")
}

/// Loads the independently authored expectations that future User Settings implementations must satisfy.
///
/// Returns the parsed JSON contract and panics with the fixture path when the manifest cannot be
/// read or parsed, because either failure means the checked-in corpus is unusable.
fn load_expectations() -> Value {
    let path = corpus_dir().join("expectations.json");
    let content = std::fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", path.display()));
    serde_json::from_str(&content)
        .unwrap_or_else(|error| panic!("failed to parse {}: {error}", path.display()))
}

/// Resolves an RFC 6901-style pointer against a parsed YAML tree with string mapping keys.
///
/// Returns `None` for malformed pointers, absent nodes, non-container traversal, or invalid array
/// indexes; callers decide which missing nodes violate their scenario contract.
fn yaml_node_at_pointer<'a>(root: &'a Yaml, pointer: &str) -> Option<&'a Yaml> {
    if pointer.is_empty() {
        return Some(root);
    }

    pointer
        .strip_prefix('/')?
        .split('/')
        .try_fold(root, |node, token| {
            let token = token.replace("~1", "/").replace("~0", "~");
            match node {
                Yaml::Hash(mapping) => mapping.get(&Yaml::String(token)),
                Yaml::Array(sequence) => sequence.get(token.parse::<usize>().ok()?),
                _ => None,
            }
        })
}

/// Returns the semantic YAML kind used by the losslessness contract.
fn yaml_type(node: &Yaml) -> &'static str {
    match node {
        Yaml::Null => "null",
        Yaml::Boolean(_) => "boolean",
        Yaml::Integer(_) => "integer",
        Yaml::Real(_) => "real",
        Yaml::String(_) => "string",
        Yaml::Array(_) => "sequence",
        Yaml::Hash(_) => "mapping",
        Yaml::Alias(_) => "alias",
        Yaml::BadValue => "bad_value",
    }
}

/// Converts a parsed YAML node into a JSON value for deterministic semantic comparison.
///
/// Real-number spellings remain strings to avoid floating-point drift. Panics when a corpus mapping
/// uses a non-string key or when the parser exposes a bad-value sentinel, as neither has a stable
/// representation in this contract.
fn yaml_semantic_value(node: &Yaml) -> Value {
    match node {
        Yaml::Null => Value::Null,
        Yaml::Boolean(value) => Value::Bool(*value),
        Yaml::Integer(value) => Value::Number((*value).into()),
        // Keep the parser's real-number spelling so the comparison does not introduce
        // floating-point rounding into a semantic-preservation characterization.
        Yaml::Real(value) => Value::String(value.clone()),
        Yaml::String(value) => Value::String(value.clone()),
        Yaml::Array(values) => Value::Array(values.iter().map(yaml_semantic_value).collect()),
        Yaml::Hash(mapping) => Value::Object(
            mapping
                .iter()
                .map(|(key, value)| {
                    let key = key
                        .as_str()
                        .expect("corpus mappings must use string keys")
                        .to_string();
                    (key, yaml_semantic_value(value))
                })
                .collect(),
        ),
        Yaml::Alias(value) => Value::Number((*value).into()),
        Yaml::BadValue => panic!("corpus must not contain Yaml::BadValue nodes"),
    }
}

/// Reads a corpus fixture as exact bytes for no-write, backup, and restore assertions.
///
/// Panics with the resolved path when a declared fixture is absent or unreadable.
fn read_fixture_bytes(name: &str) -> Vec<u8> {
    let path = corpus_dir().join(name);
    std::fs::read(&path)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", path.display()))
}

/// Parses one YAML fixture and returns its only document.
///
/// Panics when the fixture is unreadable, malformed, or contains multiple YAML documents because
/// operation golden files deliberately characterize a single persisted document.
fn load_yaml_fixture(name: &str) -> Yaml {
    let path = corpus_dir().join(name);
    let content = std::fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", path.display()));
    let mut documents = parse_yaml_content(path.display().to_string(), &content)
        .unwrap_or_else(|error| panic!("failed to parse {}: {error}", path.display()));
    assert_eq!(
        documents.len(),
        1,
        "{} must contain exactly one YAML document",
        path.display()
    );
    documents.remove(0)
}

/// Counts scalar and sequence leaves so migration mappings cannot silently omit a flat value.
fn yaml_leaf_count(node: &Yaml) -> usize {
    match node {
        Yaml::Hash(mapping) => mapping.values().map(yaml_leaf_count).sum(),
        Yaml::Array(_)
        | Yaml::Null
        | Yaml::Boolean(_)
        | Yaml::Integer(_)
        | Yaml::Real(_)
        | Yaml::String(_)
        | Yaml::Alias(_)
        | Yaml::BadValue => 1,
    }
}

/// Collects semantic JSON pointers whose values differ between two documents.
fn collect_semantic_differences(
    before: &Value,
    after: &Value,
    pointer: &str,
    differences: &mut BTreeSet<String>,
) {
    match (before, after) {
        (Value::Object(before), Value::Object(after)) => {
            let keys: BTreeSet<_> = before.keys().chain(after.keys()).collect();
            for key in keys {
                let escaped = key.replace('~', "~0").replace('/', "~1");
                let child_pointer = format!("{pointer}/{escaped}");
                match (before.get(key), after.get(key)) {
                    (Some(before), Some(after)) => {
                        collect_semantic_differences(before, after, &child_pointer, differences)
                    }
                    _ => {
                        differences.insert(child_pointer);
                    }
                }
            }
        }
        _ if before != after => {
            differences.insert(pointer.to_string());
        }
        _ => {}
    }
}

mod compatibility_contract_tests {
    use super::*;

    /// Verifies the issue-defined vocabulary, defaults, fallbacks, and losslessness boundary.
    #[test]
    fn test_corpus_records_the_full_decision_and_preservation_contract() {
        let expectations = load_expectations();

        assert_eq!(
            expectations["outcome_vocabulary"],
            serde_json::json!([
                "read_only_open",
                "degraded_fallback",
                "proposed_update",
                "accepted_commit",
                "rejected_commit",
                "conflict",
                "migration",
                "restore"
            ])
        );
        assert_eq!(
            expectations["semantic_losslessness"]["preserves"],
            serde_json::json!([
                "unknown_keys",
                "unknown_values",
                "unknown_nested_structures",
                "scalar_types",
                "untouched_invalid_values"
            ])
        );
        assert_eq!(
            expectations["semantic_losslessness"]["excludes"],
            serde_json::json!(["comments", "quoting", "whitespace"])
        );

        let canonical_defaults = &expectations["canonical_defaults"]["CLASSIC_Settings"];
        assert_eq!(
            canonical_defaults,
            &serde_json::json!({
                "Managed Game": "Fallout 4",
                "Update Check": true,
                "Game Version": "auto",
                "FCX Mode": false,
                "Simplify Logs": false,
                "Show Statistics": false,
                "Show FormID Values": false,
                "Move Unsolved Logs": true,
                "Unsolved Logs Destination": null,
                "INI Folder Path": null,
                "MODS Folder Path": null,
                "SCAN Custom Path": null,
                "Audio Notifications": false,
                "Update Source": "GitHub",
                "Disable CLI Progress": false,
                "Max Concurrent Scans": 0
            })
        );

        // Degraded safety policy is deliberately separate from published defaults:
        // unreadable Update Check state must not silently opt a user into network access.
        let degraded = &expectations["degraded_fallbacks"]["CLASSIC_Settings"];
        assert_eq!(degraded["Update Check"]["value"], false);
        assert_eq!(degraded["Update Check"]["policy"], "fail_closed");
        assert_ne!(
            degraded["Update Check"]["value"],
            canonical_defaults["Update Check"]
        );
    }

    /// Verifies that the case matrix covers every persisted form and decision named by issue #93.
    #[test]
    fn test_corpus_cases_cover_every_required_form_and_outcome() {
        let expectations = load_expectations();
        let cases = expectations["cases"]
            .as_array()
            .expect("cases must be an array");

        let coverage: BTreeSet<_> = cases
            .iter()
            .flat_map(|case| {
                case["coverage"]
                    .as_array()
                    .expect("case coverage must be an array")
            })
            .map(|coverage| coverage.as_str().expect("coverage names must be strings"))
            .collect();
        assert_eq!(
            coverage,
            BTreeSet::from([
                "canonical_label_aliases",
                "canonical_alias_conflicts",
                "canonical_nested_document",
                "flat_classic_config_shape",
                "gui_geometry",
                "invalid_known_values",
                "malformed_document",
                "missing_document",
                "newer_major_schema",
                "previous_settings_location",
                "tui_remembered_state",
                "unknown_nested_entries",
                "unknown_root_entries",
            ])
        );

        let outcomes: BTreeSet<_> = cases
            .iter()
            .flat_map(|case| {
                case["expected_outcomes"]
                    .as_array()
                    .expect("expected_outcomes must be an array")
            })
            .map(|outcome| outcome.as_str().expect("outcomes must be strings"))
            .collect();
        let vocabulary: BTreeSet<_> = expectations["outcome_vocabulary"]
            .as_array()
            .expect("outcome_vocabulary must be an array")
            .iter()
            .map(|outcome| outcome.as_str().expect("outcomes must be strings"))
            .collect();
        assert_eq!(outcomes, vocabulary);

        let semantics: BTreeSet<_> = expectations["outcome_semantics"]
            .as_object()
            .expect("outcome_semantics must be an object")
            .keys()
            .map(String::as_str)
            .collect();
        assert_eq!(semantics, vocabulary);
    }

    /// Verifies fixture syntax classifications and semantic nodes that later writes must preserve.
    #[test]
    fn test_fixture_syntax_and_preserved_semantics_match_the_declared_expectations() {
        let expectations = load_expectations();
        let cases = expectations["cases"]
            .as_array()
            .expect("cases must be an array");

        for case in cases {
            let id = case["id"].as_str().expect("case id must be a string");
            let format = case["format"]
                .as_str()
                .expect("case format must be a string");
            let parse_expectation = case["parse"]
                .as_str()
                .expect("parse expectation must be a string");

            let Some(fixture_name) = case["fixture"].as_str() else {
                assert_eq!(format, "missing", "only missing cases may omit a fixture");
                assert_eq!(parse_expectation, "not_applicable");
                continue;
            };

            let fixture_path = corpus_dir().join(fixture_name);
            let content = std::fs::read_to_string(&fixture_path).unwrap_or_else(|error| {
                panic!(
                    "case {id} failed to read {}: {error}",
                    fixture_path.display()
                )
            });

            match format {
                "yaml" => {
                    let parsed = parse_yaml_content(fixture_path.display().to_string(), &content);
                    if parse_expectation == "invalid" {
                        assert!(parsed.is_err(), "case {id} must be invalid YAML");
                        continue;
                    }

                    let documents = parsed
                        .unwrap_or_else(|error| panic!("case {id} must parse as YAML: {error}"));
                    assert_eq!(
                        documents.len(),
                        1,
                        "case {id} must remain a single-document compatibility fixture"
                    );
                    let document = &documents[0];

                    if let Some(nodes) = case["preserve_nodes"].as_array() {
                        for expected in nodes {
                            let pointer = expected["pointer"]
                                .as_str()
                                .expect("preserved node pointer must be a string");
                            let node =
                                yaml_node_at_pointer(document, pointer).unwrap_or_else(|| {
                                    panic!("case {id} is missing preserved node {pointer}")
                                });
                            assert_eq!(
                                yaml_type(node),
                                expected["type"]
                                    .as_str()
                                    .expect("node type must be a string"),
                                "case {id} changed the semantic type at {pointer}"
                            );
                            assert_eq!(
                                yaml_semantic_value(node),
                                expected["value"],
                                "case {id} changed the semantic value at {pointer}"
                            );
                        }
                    }
                }
                "json" => {
                    assert_eq!(parse_expectation, "valid");
                    serde_json::from_str::<Value>(&content)
                        .unwrap_or_else(|error| panic!("case {id} must parse as JSON: {error}"));
                }
                unexpected => panic!("case {id} has unsupported fixture format {unexpected}"),
            }

            if let Some(external_fixture) = case["external_fixture"].as_str() {
                let external_path = corpus_dir().join(external_fixture);
                let external = std::fs::read_to_string(&external_path).unwrap_or_else(|error| {
                    panic!(
                        "case {id} failed to read external revision {}: {error}",
                        external_path.display()
                    )
                });
                parse_yaml_content(external_path.display().to_string(), &external).unwrap_or_else(
                    |error| panic!("case {id} external revision must parse as YAML: {error}"),
                );
            }
        }
    }

    /// Verifies executable before/after invariants for all eight expected persistence outcomes.
    #[test]
    fn test_operation_goldens_enforce_mutation_and_document_state_contracts() {
        let expectations = load_expectations();
        let scenarios = expectations["operation_scenarios"]
            .as_array()
            .expect("operation_scenarios must be an array");
        let scenario_outcomes: BTreeSet<_> = scenarios
            .iter()
            .map(|scenario| {
                scenario["outcome"]
                    .as_str()
                    .expect("scenario outcome must be a string")
            })
            .collect();
        let vocabulary: BTreeSet<_> = expectations["outcome_vocabulary"]
            .as_array()
            .expect("outcome_vocabulary must be an array")
            .iter()
            .map(|outcome| outcome.as_str().expect("outcomes must be strings"))
            .collect();
        assert_eq!(scenario_outcomes, vocabulary);

        for scenario in scenarios {
            let id = scenario["id"]
                .as_str()
                .expect("scenario id must be a string");
            let outcome = scenario["outcome"]
                .as_str()
                .expect("scenario outcome must be a string");
            let source_fixture = scenario["source_fixture"]
                .as_str()
                .expect("source fixture must be a string");
            let disk_fixture_before = scenario["disk_fixture_before"]
                .as_str()
                .expect("disk fixture must be a string");
            let expected_document = scenario["expected_document"]
                .as_str()
                .expect("expected document must be a string");
            let writes_document = scenario["writes_document"]
                .as_bool()
                .expect("writes_document must be a boolean");

            let source_bytes = read_fixture_bytes(source_fixture);
            let disk_bytes = read_fixture_bytes(disk_fixture_before);
            let expected_bytes = read_fixture_bytes(expected_document);

            if !writes_document {
                assert_eq!(
                    expected_bytes, disk_bytes,
                    "scenario {id} outcome {outcome} must leave the on-disk document unchanged"
                );
            }

            match outcome {
                "read_only_open" | "degraded_fallback" | "rejected_commit" | "conflict" => {
                    assert!(!writes_document, "scenario {id} must not write");
                }
                "proposed_update" => {
                    assert!(!writes_document, "scenario {id} preview must not write");
                    assert_eq!(
                        scenario["requested_update"], scenario["expected_preview"],
                        "scenario {id} preview must name every requested field and no unrelated field"
                    );
                }
                "accepted_commit" => {
                    assert!(
                        writes_document,
                        "scenario {id} must publish its accepted update"
                    );
                    assert_eq!(
                        source_bytes, disk_bytes,
                        "scenario {id} must start at its opened revision"
                    );

                    let before = yaml_semantic_value(&load_yaml_fixture(source_fixture));
                    let after = yaml_semantic_value(&load_yaml_fixture(expected_document));
                    let mut differences = BTreeSet::new();
                    collect_semantic_differences(&before, &after, "", &mut differences);
                    let expected_differences: BTreeSet<_> = scenario["changed_pointers"]
                        .as_array()
                        .expect("changed_pointers must be an array")
                        .iter()
                        .map(|pointer| {
                            pointer
                                .as_str()
                                .expect("pointer must be a string")
                                .to_string()
                        })
                        .collect();
                    assert_eq!(
                        differences, expected_differences,
                        "scenario {id} changed unrelated nodes"
                    );

                    let requested: BTreeSet<_> = scenario["requested_update"]
                        .as_object()
                        .expect("requested_update must be an object")
                        .keys()
                        .cloned()
                        .collect();
                    assert_eq!(
                        requested, expected_differences,
                        "scenario {id} did not patch exactly the requested fields"
                    );
                }
                "migration" => {
                    assert!(
                        writes_document,
                        "scenario {id} must publish an approved migration"
                    );
                    assert_eq!(
                        read_fixture_bytes(
                            scenario["backup_fixture"]
                                .as_str()
                                .expect("backup fixture must be a string")
                        ),
                        source_bytes,
                        "scenario {id} backup must be byte-for-byte source content"
                    );

                    let source = load_yaml_fixture(source_fixture);
                    let migrated = load_yaml_fixture(expected_document);
                    let target_nodes = scenario["target_nodes"]
                        .as_array()
                        .expect("target_nodes must be an array");
                    assert_eq!(
                        yaml_leaf_count(&source),
                        target_nodes.len(),
                        "scenario {id} must map every flat ClassicConfig leaf exactly once"
                    );

                    let mut source_pointers = BTreeSet::new();
                    let mut target_pointers = BTreeSet::new();
                    for expected in target_nodes {
                        let source_pointer = expected["source_pointer"]
                            .as_str()
                            .expect("source pointer must be a string");
                        let target_pointer = expected["pointer"]
                            .as_str()
                            .expect("target pointer must be a string");
                        assert!(source_pointers.insert(source_pointer));
                        assert!(target_pointers.insert(target_pointer));

                        let source_node = yaml_node_at_pointer(&source, source_pointer)
                            .unwrap_or_else(|| {
                                panic!("scenario {id} is missing source {source_pointer}")
                            });
                        let target_node = yaml_node_at_pointer(&migrated, target_pointer)
                            .unwrap_or_else(|| {
                                panic!("scenario {id} is missing target {target_pointer}")
                            });
                        assert_eq!(yaml_type(target_node), expected["type"]);
                        assert_eq!(yaml_semantic_value(target_node), expected["value"]);
                        if expected.get("transform").is_none() {
                            assert_eq!(
                                yaml_semantic_value(source_node),
                                expected["value"],
                                "scenario {id} changed {source_pointer} without a declared transform"
                            );
                        }
                    }
                }
                "restore" => {
                    assert!(
                        writes_document,
                        "scenario {id} must publish an explicit restore"
                    );
                    let backup = read_fixture_bytes(
                        scenario["backup_fixture"]
                            .as_str()
                            .expect("backup fixture must be a string"),
                    );
                    assert_eq!(
                        expected_bytes, backup,
                        "scenario {id} must exactly restore the verified backup"
                    );
                }
                unexpected => panic!("scenario {id} uses unsupported outcome {unexpected}"),
            }
        }
    }
}
