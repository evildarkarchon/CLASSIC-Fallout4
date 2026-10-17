//! Agreement tests: each mirrored rule and the real client implementation run
//! over one shared table of cases (the real crates are dev-dependencies only).

use super::*;
use classic_config_core::client_schema_ranges::parse_client_schema_ranges;
use classic_shared_core::yaml::SchemaVersion;
use classic_update_core::yaml_update::validate_cache_file_name;
use yaml_rust2::YamlLoader;

/// Cache basenames: the retired Python suite's tables plus edge cases.
const CACHE_NAMES: &[&str] = &[
    // valid
    "CLASSIC Main.yaml",
    "CLASSIC Fallout4.yaml",
    "CLASSIC Fallout4 Local.yaml",
    "NULL.yaml",
    "COM10.yaml",
    "LPT10.yaml",
    "CON_main.yaml",
    "COM0.yaml",
    ".hidden.yaml",
    "a",
    "caf\u{e9}.yaml",
    // invalid
    "",
    ".",
    "..",
    "NUL.yaml",
    "nul",
    "CON.txt",
    "Con .yaml",
    "com1.tar.gz",
    "LPT9",
    "aux",
    "foo:bar.yaml",
    "CLASSIC Main.yaml:alt",
    "C:x",
    "../etc/passwd",
    "/abs.yaml",
    "foo\\bar.yaml",
    "a/b.yaml",
    "nul\0.yaml",
    "CLASSIC Main.yaml.",
    "CLASSIC Main.yaml ",
];

#[test]
fn cache_basename_rule_agrees_with_classic_update_core() {
    for name in CACHE_NAMES {
        assert_eq!(
            is_valid_cache_file_name(name),
            validate_cache_file_name(name).is_ok(),
            "cache basename {name:?}"
        );
    }
    // The table must exercise both outcomes.
    assert!(
        CACHE_NAMES
            .iter()
            .any(|name| is_valid_cache_file_name(name))
    );
    assert!(
        CACHE_NAMES
            .iter()
            .any(|name| !is_valid_cache_file_name(name))
    );
}

#[test]
fn windows_duplicate_key_folds_case_and_trailing_dots_and_spaces() {
    assert_eq!(
        windows_normalized_cache_file_key("CLASSIC Main.yaml"),
        windows_normalized_cache_file_key("classic main.yaml")
    );
    assert_eq!(windows_normalized_cache_file_key("A.yaml. ."), "a.yaml");
    assert_ne!(
        windows_normalized_cache_file_key("CLASSIC Main.yaml"),
        windows_normalized_cache_file_key("CLASSIC Fallout4.yaml")
    );
}

/// Schema versions: the client parser is the oracle.
const SCHEMA_VERSIONS: &[&str] = &[
    "1.0",
    "2.999",
    "0.0",
    "01.010",
    "4294967295.4294967295",
    "",
    "1",
    "1.",
    ".1",
    "1.0.0",
    "v1.0",
    "1.x",
    " 1.0",
    "1.0 ",
    "1.0\n",
    "+1.0",
    "-1.0",
    "1.-0",
    "\u{0661}.0",
    "4294967296.0",
    "99999999999.0",
];

#[test]
fn schema_version_format_agrees_with_classic_shared_core() {
    for value in SCHEMA_VERSIONS {
        let real = value
            .parse::<SchemaVersion>()
            .ok()
            .map(|version| (version.major, version.minor));
        assert_eq!(
            parse_schema_version(value),
            real,
            "schema version {value:?}"
        );
    }
}

/// Ranges documents whose only defects are rules the client loader owns, so
/// the mirror and `classic-config-core` must agree on accept/reject.
const RANGES_DOCUMENTS: &[&str] = &[
    // accepted
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"1.0\"\n    max_client_schema: \"1.999\"\n",
    "files:\n  - name: \"a.yaml\"\n    client_schemas_const: \"MAIN_YAML\"\n    min_client_schema: \"1.9\"\n    max_client_schema: \"1.10\"\n",
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"2.0\"\n    max_client_schema: \"2.0\"\n  - name: \"b.yaml\"\n    min_client_schema: \"1.0\"\n    max_client_schema: \"3.0\"\n",
    // rejected
    "- not a mapping\n",
    "files: {}\n",
    "other: []\n",
    "files:\n  - \"a.yaml\"\n",
    "files:\n  - min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n",
    "files:\n  - name: 12\n    min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n",
    "files:\n  - name: \"a.yaml\"\n    client_schemas_const: [x]\n    min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n",
    "files:\n  - name: \"a.yaml\"\n    max_client_schema: \"1.0\"\n",
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"1.0\"\n",
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: 1.0\n    max_client_schema: \"1.0\"\n",
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"1.0\"\n    max_client_schema: 2\n",
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: ~\n    max_client_schema: \"1.0\"\n",
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"1.x\"\n    max_client_schema: \"1.0\"\n",
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"1.0\"\n    max_client_schema: \"99999999999.0\"\n",
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"1.10\"\n    max_client_schema: \"1.9\"\n",
    "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"3.0\"\n    max_client_schema: \"2.999\"\n",
];

#[test]
fn ranges_rules_agree_with_classic_config_core() {
    for text in RANGES_DOCUMENTS {
        let document = YamlLoader::load_from_str(text)
            .expect("table documents are valid YAML")
            .remove(0);
        let mirror = check_ranges(&document);
        assert_eq!(
            mirror.problems.is_empty(),
            parse_client_schema_ranges(text).is_ok(),
            "ranges document {text:?}: mirror problems {:?}",
            mirror.problems
        );
    }
}

#[test]
fn publish_only_ranges_rules_are_reported_on_top_of_the_client_loader() {
    let check = |text: &str| {
        check_ranges(
            &YamlLoader::load_from_str(text)
                .expect("valid YAML")
                .remove(0),
        )
        .problems
        .into_iter()
        .map(|problem| problem.rule)
        .collect::<Vec<_>>()
    };

    assert_eq!(check("files: []\n"), ["ranges-no-files"]);
    assert_eq!(
        check(
            "files:\n  - name: \"NUL.yaml\"\n    min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n"
        ),
        ["invalid-cache-file-name"]
    );
    assert_eq!(
        check(
            "files:\n  - name: \"A.yaml\"\n    min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n  \
             - name: \"a.yaml\"\n    min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n"
        ),
        ["duplicate-cache-file-name"]
    );
}

#[test]
fn every_problem_in_a_ranges_document_is_collected() {
    let text = "files:\n  - name: \"NUL.yaml\"\n    min_client_schema: 1.0\n    max_client_schema: \"1.x\"\n  \
                - name: \"b.yaml\"\n    min_client_schema: \"2.0\"\n    max_client_schema: \"1.0\"\n";
    let ranges = check_ranges(
        &YamlLoader::load_from_str(text)
            .expect("valid YAML")
            .remove(0),
    );

    let rules: Vec<_> = ranges.problems.iter().map(|problem| problem.rule).collect();
    assert_eq!(
        rules,
        [
            "invalid-cache-file-name",
            "schema-range-not-string",
            "malformed-schema-range",
            "empty-schema-range"
        ]
    );
    assert!(ranges.entries.is_empty());
    assert_eq!(
        ranges.problems[1].message,
        "entry 'NUL.yaml': min_client_schema must be a quoted string, got float (1.0)"
    );
}
