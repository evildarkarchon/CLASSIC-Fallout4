use super::*;

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
fn schema_version_ordering_major_then_minor() {
    assert!(SchemaVersion::new(1, 9) < SchemaVersion::new(2, 0));
    assert!(SchemaVersion::new(2, 3) < SchemaVersion::new(2, 10));
}
