use super::*;

const VALID: &str = r#"files:
  - name: "CLASSIC Main.yaml"
    client_schemas_const: "MAIN_YAML"
    min_client_schema: "2.0"
    max_client_schema: "2.999"
  - name: "CLASSIC Fallout4.yaml"
    min_client_schema: "1.0"
    max_client_schema: "1.10"
"#;

/// A one-entry ranges document with the given `min`/`max` YAML values (written
/// verbatim, so callers choose quoting).
fn one_entry(min: &str, max: &str) -> String {
    format!(
        "files:\n  - name: \"CLASSIC Main.yaml\"\n    min_client_schema: {min}\n    max_client_schema: {max}\n"
    )
}

#[test]
fn parses_entries_in_file_order_with_versions_and_optional_const() {
    let ranges = parse_client_schema_ranges(VALID).expect("valid ranges parse");

    assert_eq!(
        ranges,
        vec![
            ClientSchemaRange {
                name: "CLASSIC Main.yaml".into(),
                client_schemas_const: Some("MAIN_YAML".into()),
                min_client_schema: SchemaVersion::new(2, 0),
                max_client_schema: SchemaVersion::new(2, 999),
            },
            ClientSchemaRange {
                name: "CLASSIC Fallout4.yaml".into(),
                client_schemas_const: None,
                min_client_schema: SchemaVersion::new(1, 0),
                max_client_schema: SchemaVersion::new(1, 10),
            },
        ]
    );
}

#[test]
fn the_bundled_ranges_file_loads() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../CLASSIC Data/databases/client-schema-ranges.yaml");

    let ranges = load_client_schema_ranges(&path).expect("bundled ranges load");

    let names: Vec<&str> = ranges.iter().map(|range| range.name.as_str()).collect();
    assert_eq!(names, ["CLASSIC Main.yaml", "CLASSIC Fallout4.yaml"]);
}

#[test]
fn a_missing_file_is_an_io_error() {
    let error = load_client_schema_ranges(std::path::Path::new("no/such/ranges.yaml"))
        .expect_err("missing file fails");
    assert!(
        matches!(error, ClientSchemaRangesError::Io { .. }),
        "{error:?}"
    );
}

#[test]
fn rejects_malformed_documents() {
    let cases: &[(&str, &str)] = &[
        ("files: [unclosed", "invalid YAML"),
        ("", "expected one YAML document, found 0"),
        ("- just a list\n", "top-level `files` list"),
        ("files: {}\n", "top-level `files` list"),
        ("files:\n  - plain string\n", "entry 0 is not a mapping"),
        (
            "files:\n  - min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n",
            "entry 0 has no string `name`",
        ),
        (
            "files:\n  - name: 7\n    min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n",
            "entry 0 has no string `name`",
        ),
        (
            "files:\n  - name: \"a.yaml\"\n    client_schemas_const: 3\n    min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n",
            "`client_schemas_const` must be a string",
        ),
        (
            "files:\n  - name: \"a.yaml\"\n    max_client_schema: \"1.0\"\n",
            "missing `min_client_schema`",
        ),
    ];
    for (text, expected) in cases {
        let error = parse_client_schema_ranges(text).expect_err(text);
        assert!(
            error.to_string().contains(expected),
            "{text:?}: {error} does not mention {expected:?}"
        );
    }
}

#[test]
fn range_bounds_must_be_quoted_major_minor_strings() {
    for (min, max) in [
        ("1.0", "\"1.0\""),
        ("\"1.0\"", "~"),
        ("\"1\"", "\"1.0\""),
        ("\"1.0.0\"", "\"1.0\""),
        ("\"1.x\"", "\"1.0\""),
        ("\"v1.0\"", "\"1.0\""),
        ("\"99999999999.0\"", "\"1.0\""),
    ] {
        let text = one_entry(min, max);
        assert!(
            parse_client_schema_ranges(&text).is_err(),
            "min={min} max={max} must be rejected"
        );
    }
}

#[test]
fn an_inverted_range_is_rejected_by_numeric_order() {
    let error = parse_client_schema_ranges(&one_entry("\"1.10\"", "\"1.9\""))
        .expect_err("1.10 > 1.9 numerically");
    assert!(
        matches!(error, ClientSchemaRangesError::EmptyRange { .. }),
        "{error:?}"
    );

    // A single-point range is not empty.
    assert!(parse_client_schema_ranges(&one_entry("\"1.9\"", "\"1.9\"")).is_ok());
}
