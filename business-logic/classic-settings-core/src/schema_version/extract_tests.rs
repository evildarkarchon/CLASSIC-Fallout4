use super::*;
use yaml_rust2::{Yaml, YamlLoader};

fn parse_yaml(src: &str) -> Yaml {
    YamlLoader::load_from_str(src)
        .expect("test YAML parses")
        .into_iter()
        .next()
        .expect("non-empty YAML document")
}

#[test]
fn extract_reads_valid_quoted_string() {
    let doc = parse_yaml("schema_version: \"1.3\"\nother: yes\n");
    let v = extract_schema_version(&doc).unwrap();
    assert_eq!(v, SchemaVersion::new(1, 3));
}

#[test]
fn extract_missing_field_returns_missing() {
    let doc = parse_yaml("game: Fallout4\n");
    let err = extract_schema_version(&doc).unwrap_err();
    assert!(matches!(err, YamlSchemaError::Missing));
}

#[test]
fn extract_rejects_single_number_string() {
    let doc = parse_yaml("schema_version: \"1\"\n");
    let err = extract_schema_version(&doc).unwrap_err();
    match err {
        YamlSchemaError::Malformed { value, reason, .. } => {
            assert_eq!(value, "1");
            assert_eq!(reason, SchemaParseError::MissingSeparator);
        }
        other => panic!("expected Malformed, got {other:?}"),
    }
}

#[test]
fn extract_rejects_three_component_string() {
    let doc = parse_yaml("schema_version: \"1.2.3\"\n");
    let err = extract_schema_version(&doc).unwrap_err();
    assert!(matches!(
        err,
        YamlSchemaError::Malformed {
            reason: SchemaParseError::TooManyComponents,
            ..
        }
    ));
}

#[test]
fn extract_rejects_v_prefix_string() {
    let doc = parse_yaml("schema_version: \"v1.2\"\n");
    let err = extract_schema_version(&doc).unwrap_err();
    assert!(matches!(
        err,
        YamlSchemaError::Malformed {
            reason: SchemaParseError::NonDigitComponent,
            ..
        }
    ));
}

#[test]
fn extract_rejects_unquoted_number() {
    // yaml-rust2 parses an unquoted `1.0` as Yaml::Real, not Yaml::String.
    // The format contract requires a quoted string, so this must be rejected.
    let doc = parse_yaml("schema_version: 1.0\n");
    let err = extract_schema_version(&doc).unwrap_err();
    match err {
        YamlSchemaError::Malformed { value, reason, .. } => {
            assert_eq!(reason, SchemaParseError::NonDigitComponent);
            assert_eq!(value, "1.0");
        }
        other => panic!("expected Malformed for unquoted number, got {other:?}"),
    }
}

#[test]
fn with_file_attaches_label_to_malformed() {
    let err = YamlSchemaError::Malformed {
        file: String::new(),
        value: "v1".into(),
        reason: SchemaParseError::MissingSeparator,
    }
    .with_file("CLASSIC Main.yaml");
    match err {
        YamlSchemaError::Malformed { file, .. } => assert_eq!(file, "CLASSIC Main.yaml"),
        other => panic!("expected Malformed, got {other:?}"),
    }
}

#[test]
fn with_file_leaves_missing_untouched() {
    let err = YamlSchemaError::Missing.with_file("CLASSIC Main.yaml");
    assert!(matches!(err, YamlSchemaError::Missing));
}
