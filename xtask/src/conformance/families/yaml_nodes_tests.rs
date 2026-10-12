use serde_json::json;

use super::*;

/// The node for `x: <scalar>`.
fn scalar(text: &str) -> Result<Value, String> {
    yaml_nodes(format!("x: {text}").as_bytes()).map(|nodes| nodes["value"]["x"].clone())
}

/// Expected nodes recorded from the retired Python oracle (ruamel, YAML 1.2,
/// `Decimal` reals) over the same scalars.
#[test]
fn scalars_match_the_python_oracle() {
    let cases = [
        ("1.50", json!({"type": "real", "value": "15e-1"})),
        ("-0.0", json!({"type": "real", "value": "0"})),
        ("0.0", json!({"type": "real", "value": "0"})),
        ("00.50", json!({"type": "real", "value": "5e-1"})),
        ("0.05", json!({"type": "real", "value": "5e-2"})),
        ("1e5", json!({"type": "real", "value": "1e5"})),
        ("1.0e5", json!({"type": "real", "value": "1e5"})),
        ("1E+05", json!({"type": "real", "value": "1e5"})),
        ("100.", json!({"type": "real", "value": "1e2"})),
        (".5", json!({"type": "real", "value": "5e-1"})),
        ("+1.5", json!({"type": "real", "value": "15e-1"})),
        ("-2.500e-3", json!({"type": "real", "value": "-25e-4"})),
        ("1.", json!({"type": "real", "value": "1e0"})),
        ("!!float 1", json!({"type": "real", "value": "1e0"})),
        (
            "123456789012345678901234567890.5",
            json!({"type": "real", "value": "1234567890123456789012345678905e-1"}),
        ),
        ("~", json!({"type": "null"})),
        ("null", json!({"type": "null"})),
        ("", json!({"type": "null"})),
        ("yes", json!({"type": "string", "value": "yes"})),
        ("on", json!({"type": "string", "value": "on"})),
        ("nan", json!({"type": "string", "value": "nan"})),
        ("inf", json!({"type": "string", "value": "inf"})),
        ("'1.50'", json!({"type": "string", "value": "1.50"})),
        ("True", json!({"type": "boolean", "value": true})),
        ("TRUE", json!({"type": "boolean", "value": true})),
        ("017", json!({"type": "integer", "value": 17})),
        ("0o17", json!({"type": "integer", "value": 15})),
        ("0x1F", json!({"type": "integer", "value": 31})),
        ("+12", json!({"type": "integer", "value": 12})),
    ];
    for (text, expected) in cases {
        assert_eq!(scalar(text), Ok(expected), "scalar {text:?}");
    }
}

#[test]
fn collections_become_sorted_mappings_and_ordered_sequences() {
    let nodes = yaml_nodes(b"b: [2, 1]\na: {c: null}\n").expect("valid YAML");
    assert_eq!(
        nodes,
        json!({"type": "mapping", "value": {
            "a": {"type": "mapping", "value": {"c": {"type": "null"}}},
            "b": {"type": "sequence", "value": [
                {"type": "integer", "value": 2},
                {"type": "integer", "value": 1},
            ]},
        }})
    );
    assert_eq!(yaml_nodes(b""), Ok(json!({"type": "null"})));
    assert_eq!(
        yaml_nodes(b"# only a comment\n"),
        Ok(json!({"type": "null"}))
    );
}

#[test]
fn a_self_referencing_alias_loads_as_a_bad_value_and_is_rejected() {
    let error = yaml_nodes(b"a: &x [1, *x]").unwrap_err();
    assert!(error.contains("unsupported YAML node"), "{error}");
}

#[test]
fn non_finite_reals_are_rejected() {
    for text in [".inf", "-.inf", "+.INF", ".nan", ".NaN"] {
        let error = scalar(text).unwrap_err();
        assert!(error.contains("nonfinite"), "{text}: {error}");
    }
}

#[test]
fn non_string_mapping_keys_are_rejected() {
    for document in ["1: a", "true: a", "~: a", "1.5: a", "[a]: b"] {
        let error = yaml_nodes(document.as_bytes()).unwrap_err();
        assert!(
            error.contains("unsupported YAML node"),
            "{document}: {error}"
        );
    }
}

#[test]
fn duplicate_keys_undefined_aliases_and_extra_documents_are_parse_errors() {
    for document in ["a: 1\na: 2", "a: *y", "---\na: 1\n---\nb: 2\n"] {
        let error = yaml_nodes(document.as_bytes()).unwrap_err();
        assert!(
            error.contains("invalid User Settings YAML"),
            "{document}: {error}"
        );
    }
    assert!(yaml_nodes(b"\xff: 1").is_err());
}

/// Accepted divergences from the retired ruamel oracle (spec #302,
/// "Conformance engine port"). `yaml-rust2` treats underscored numerals as
/// strings, where ruamel read `1_000` as 1000 and `1_000.5` as `10005e-1`;
/// it also reads `Null` and `NULL` as strings, where ruamel's YAML 1.2
/// resolver read them as null. No pack or fixture uses either form, and the
/// product parses with `yaml-rust2`, so the oracle matches the product. If a
/// `yaml-rust2` upgrade changes any of these, this test fails so the change is
/// noticed and the oracle's behaviour is re-decided deliberately.
#[test]
fn yaml_rust2_divergences_from_ruamel_are_pinned() {
    for text in ["1_000", "1_000.5", "Null", "NULL"] {
        assert_eq!(
            scalar(text),
            Ok(json!({"type": "string", "value": text})),
            "scalar {text:?}"
        );
    }
}
