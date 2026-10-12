//! Declared normalization and exact comparison, ported from the retired
//! Python engine's `compare.py` cases.

use serde_json::{Value, json};

use super::*;

fn object(value: Value) -> Map<String, Value> {
    match value {
        Value::Object(map) => map,
        other => panic!("not an object: {other}"),
    }
}

fn rules(value: Value) -> Normalization {
    serde_json::from_value(value).expect("normalization deserializes")
}

fn none() -> Normalization {
    rules(json!({"rootRelativePaths": false, "unorderedPaths": [], "excludedPaths": []}))
}

fn differences(expected: Value, actual: Value) -> Vec<(String, &'static str)> {
    exact_differences(&expected, &actual)
        .into_iter()
        .map(|difference| (difference.path, difference.kind))
        .collect()
}

#[test]
fn exact_comparison_reports_every_undeclared_difference_in_path_order() {
    assert_eq!(differences(json!({"a": 1}), json!({"a": 1})), []);
    assert_eq!(
        differences(
            json!({"b": [1, 2], "a": true, "c": {"x": "y"}, "gone": 1}),
            json!({"b": [1], "a": 1, "c": {"x": "z"}, "new": 1}),
        ),
        [
            ("$.gone".to_owned(), "missing_field"),
            ("$.new".to_owned(), "extra_field"),
            // Booleans never equal integers.
            ("$.a".to_owned(), "type_mismatch"),
            ("$.b[1]".to_owned(), "missing_element"),
            ("$.c.x".to_owned(), "value_mismatch"),
        ]
    );
    assert_eq!(
        differences(json!({"list": []}), json!({"list": [null]})),
        [("$.list[0]".to_owned(), "extra_element")]
    );
}

#[test]
fn only_declared_exclusions_and_unordered_paths_are_applied() {
    let normalization = rules(json!({
        "rootRelativePaths": false,
        "unorderedPaths": ["$.items"],
        "excludedPaths": [
            {"path": "$.volatile", "rationale": "timestamps"},
            {"path": "$.rows[0]", "rationale": "first row is volatile"},
            {"path": "$.rows[1].when", "rationale": "nested"}
        ]
    }));
    let expected =
        object(json!({"items": [2, 1], "rows": [{"a": 1}, {"b": 2}, {"c": 3}], "kept": 1}));
    let actual = object(json!({
        "items": [1, 2],
        "volatile": "now",
        "rows": [{"z": 9}, {"b": 2, "when": "later"}, {"c": 3}],
        "kept": 1
    }));
    let (expected, actual) = normalize(expected, actual, &normalization, "/root").unwrap();
    // The deeper `$.rows[1].when` is removed before `$.rows[0]` shifts it.
    assert_eq!(
        Value::Object(actual.clone()),
        json!({"items": [1, 2], "rows": [{"b": 2}, {"c": 3}], "kept": 1})
    );
    assert_eq!(expected, actual);

    // Undeclared, the same members differ.
    let (expected, actual) = normalize(
        object(json!({"items": [2, 1]})),
        object(json!({"items": [1, 2]})),
        &none(),
        "/root",
    )
    .unwrap();
    assert_ne!(expected, actual);
}

#[test]
fn root_relative_paths_rewrite_only_absolute_path_carriers() {
    let normalization =
        rules(json!({"rootRelativePaths": true, "unorderedPaths": [], "excludedPaths": []}));
    let expected = object(json!({
        "files": [{"path": "data/a.txt"}, {"path": "data/b.txt"}],
        "label": "C:\\Root\\data\\a.txt",
        "posix": {"path": "x/y"}
    }));
    let actual = object(json!({
        "files": [{"path": "c:\\root\\data\\a.txt"}, {"path": "data\\b.txt"}],
        "label": "C:\\Root\\data\\a.txt",
        "posix": {"path": "x/y"}
    }));
    let (expected, actual) = normalize(expected, actual, &normalization, "C:\\Root").unwrap();
    assert_eq!(expected, actual, "Windows paths compare case-insensitively");

    let (expected, actual) = normalize(
        object(json!({"path": "a/b"})),
        object(json!({"path": "/tmp/run/a/b"})),
        &normalization,
        "/tmp/run",
    )
    .unwrap();
    assert_eq!(expected, actual);

    // Undeclared, an absolute path stays absolute.
    let (_, actual) = normalize(
        object(json!({"path": "a"})),
        object(json!({"path": "/tmp/run/a"})),
        &none(),
        "/tmp/run",
    )
    .unwrap();
    assert_eq!(actual["path"], "/tmp/run/a");
}

#[test]
fn a_path_outside_the_fixture_root_is_a_normalization_failure() {
    let normalization =
        rules(json!({"rootRelativePaths": true, "unorderedPaths": [], "excludedPaths": []}));
    for (actual, message) in [
        ("D:\\elsewhere\\a", "outside the prepared fixture root"),
        ("/elsewhere/a", "outside the prepared fixture root"),
        ("C:\\Root", "must remain beneath the fixture root"),
        ("C:\\Root\\..\\a", "must remain beneath the fixture root"),
        ("..\\a", "must remain beneath the fixture root"),
    ] {
        let error = normalize(
            object(json!({"path": "a"})),
            object(json!({"path": actual})),
            &normalization,
            "C:\\Root",
        )
        .unwrap_err();
        assert_eq!(error.path, "$.path", "{actual}");
        assert!(error.message.contains(message), "{actual}: {error:?}");
    }
}

#[test]
fn optional_empty_files_accept_absence_or_an_exact_empty_file() {
    let normalization = rules(json!({
        "rootRelativePaths": false,
        "unorderedPaths": [],
        "excludedPaths": [],
        "optionalEmptyFiles": [{"path": "$.tree", "relativePath": "lock", "rationale": "racy"}]
    }));
    let kept = json!({"path": {"path": "a"}, "kind": "file", "bytesHex": "00"});
    let empty = json!({"path": {"path": "lock"}, "kind": "file", "bytesHex": ""});
    let (expected, actual) = normalize(
        object(json!({"tree": [kept.clone()]})),
        object(json!({"tree": [kept.clone(), empty]})),
        &normalization,
        "/r",
    )
    .unwrap();
    assert_eq!(expected, actual);

    for (tree, message) in [
        (
            json!([kept.clone(), {"path": {"path": "lock"}, "kind": "file", "bytesHex": "01"}]),
            "exact empty regular file",
        ),
        (
            json!([{"path": "lock", "kind": "file"}]),
            "malformed path carrier",
        ),
        (json!("not a tree"), "present tree array"),
    ] {
        let error = normalize(
            object(json!({"tree": [kept.clone()]})),
            object(json!({"tree": tree})),
            &normalization,
            "/r",
        )
        .unwrap_err();
        assert!(error.message.contains(message), "{error:?}");
        assert_eq!(error.path, "$.tree");
    }
}

#[test]
fn an_unperformable_declared_normalization_fails() {
    let normalization = rules(
        json!({"rootRelativePaths": false, "unorderedPaths": ["$.items"], "excludedPaths": []}),
    );
    let error = normalize(
        object(json!({"items": []})),
        object(json!({"items": {"not": "an array"}})),
        &normalization,
        "/r",
    )
    .unwrap_err();
    assert_eq!(error.path, "$.items");
    assert!(
        error.message.contains("non-array actual value"),
        "{error:?}"
    );

    let normalization = rules(
        json!({"rootRelativePaths": false, "unorderedPaths": [], "excludedPaths": [{"path": "$.a.b", "rationale": "r"}]}),
    );
    let error = normalize(
        object(json!({})),
        object(json!({"a": 1})),
        &normalization,
        "/r",
    )
    .unwrap_err();
    assert!(error.message.contains("non-object"), "{error:?}");
}

#[test]
fn display_content_carriers_must_keep_their_frozen_shape() {
    let line = |segment: Value| json!({"severity": "info", "segments": [segment]});
    let good = line(json!({"kind": "text", "text": "hello", "path": "", "count": 0}));
    let expected = json!({"report": {"displayContent": [good.clone()]}});
    assert_eq!(validate_display_content(&expected, &expected), Ok(()));

    for (actual, path) in [
        (
            json!({"report": {"displayContent": [{"severity": "info"}]}}),
            "$.report.displayContent[0]",
        ),
        (
            json!({"report": {"displayContent": [{"severity": "loud", "segments": []}]}}),
            "$.report.displayContent[0].severity",
        ),
        (
            json!({"report": {"displayContent": [line(json!({"kind": "path", "text": "", "path": "/abs", "count": 0}))]}}),
            "$.report.displayContent[0].segments[0]",
        ),
        (
            json!({"report": {"displayContent": [line(json!({"kind": "text", "text": "x", "path": "", "count": -1}))]}}),
            "$.report.displayContent[0].segments[0].count",
        ),
        (
            json!({"report": {"displayContent": "flat"}}),
            "$.report.displayContent",
        ),
    ] {
        let error = validate_display_content(&expected, &actual).unwrap_err();
        assert_eq!(error.path, path, "{actual}");
    }

    // A domain record that happens to carry `severity` is not a display line.
    let record = json!({"finding": {"severity": "high"}});
    assert_eq!(validate_display_content(&record, &record), Ok(()));
}
