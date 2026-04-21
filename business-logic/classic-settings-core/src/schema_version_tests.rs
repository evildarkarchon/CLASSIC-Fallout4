use super::*;
use yaml_rust2::YamlLoader;

fn parse_yaml(src: &str) -> Yaml {
    YamlLoader::load_from_str(src)
        .expect("test YAML parses")
        .into_iter()
        .next()
        .expect("non-empty YAML document")
}

#[test]
fn schema_version_parses_valid() {
    let v: SchemaVersion = "1.3".parse().unwrap();
    assert_eq!(v, SchemaVersion::new(1, 3));
    assert_eq!(v.to_string(), "1.3");
}

#[test]
fn schema_version_parse_rejects_single_number() {
    let err = "1".parse::<SchemaVersion>().unwrap_err();
    assert_eq!(err, SchemaParseError::MissingSeparator);
}

#[test]
fn schema_version_parse_rejects_three_components() {
    let err = "1.2.3".parse::<SchemaVersion>().unwrap_err();
    assert_eq!(err, SchemaParseError::TooManyComponents);
}

#[test]
fn schema_version_parse_rejects_v_prefix() {
    let err = "v1.2".parse::<SchemaVersion>().unwrap_err();
    assert_eq!(err, SchemaParseError::NonDigitComponent);
}

#[test]
fn schema_version_parse_rejects_empty_component() {
    assert_eq!(
        ".1".parse::<SchemaVersion>().unwrap_err(),
        SchemaParseError::EmptyComponent
    );
    assert_eq!(
        "1.".parse::<SchemaVersion>().unwrap_err(),
        SchemaParseError::EmptyComponent
    );
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

#[test]
fn compat_accepts_matching_major_and_minor_at_or_above_floor() {
    let v = SchemaVersion::new(2, 5);
    let compat = SchemaCompat::new(2, 4);
    assert_eq!(schema_compat_check(&v, &compat), Compatibility::Compatible);
}

#[test]
fn compat_equal_floor_is_compatible() {
    let v = SchemaVersion::new(1, 0);
    let compat = SchemaCompat::new(1, 0);
    assert_eq!(schema_compat_check(&v, &compat), Compatibility::Compatible);
}

#[test]
fn compat_rejects_major_mismatch() {
    let v = SchemaVersion::new(3, 0);
    let compat = SchemaCompat::new(2, 4);
    assert_eq!(
        schema_compat_check(&v, &compat),
        Compatibility::IncompatibleMajor {
            file_major: 3,
            client_accepted_major: 2
        }
    );
}

#[test]
fn compat_rejects_minor_below_floor() {
    let v = SchemaVersion::new(2, 2);
    let compat = SchemaCompat::new(2, 4);
    assert_eq!(
        schema_compat_check(&v, &compat),
        Compatibility::IncompatibleMinor {
            file_minor: 2,
            client_minimum_minor: 4
        }
    );
}

#[test]
fn schema_version_ordering_major_then_minor() {
    assert!(SchemaVersion::new(1, 9) < SchemaVersion::new(2, 0));
    assert!(SchemaVersion::new(2, 3) < SchemaVersion::new(2, 10));
}
