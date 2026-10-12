use serde_json::json;

use super::*;

fn error(text: &str) -> JsonError {
    parse_strict(text).expect_err("strict parse must reject the input")
}

#[test]
fn strict_parse_accepts_plain_json_and_records_lines() {
    let document = parse_strict("{\n  \"a\": [1, -2, \"x\"],\n  \"b\": {\n    \"c/d\": null\n  }\n}\n")
        .expect("valid JSON");
    assert_eq!(
        document.value(),
        &json!({"a": [1, -2, "x"], "b": {"c/d": null}})
    );
    assert_eq!(document.line(""), 1);
    assert_eq!(document.line("/a"), 2);
    assert_eq!(document.line("/a/2"), 2);
    assert_eq!(document.line("/b/c~1d"), 4);
    // A pointer with no recorded value falls back to its nearest ancestor.
    assert_eq!(document.line("/b/missing"), 3);
}

#[test]
fn duplicate_keys_are_rejected_at_every_depth() {
    let top = error("{\"a\": 1,\n \"a\": 2}");
    assert_eq!(top.line, 2);
    assert!(top.message.contains("duplicate JSON object key: \"a\""), "{top}");
    let nested = error("{\"x\": [{\"k\": 1, \"k\": 1}]}");
    assert!(nested.message.contains("duplicate"), "{nested}");
}

#[test]
fn floating_point_and_non_finite_numbers_are_rejected() {
    for text in ["1.0", "[1e5]", "{\"a\": -0.5}", "2E-3"] {
        let failure = error(text);
        assert!(
            failure.message.contains("floating-point JSON value is forbidden"),
            "{text}: {failure}"
        );
    }
    for text in ["NaN", "[Infinity]", "{\"a\": -Infinity}"] {
        let failure = error(text);
        assert!(
            failure.message.contains("floating-point") || failure.message.contains("number"),
            "{text}: {failure}"
        );
    }
    assert!(error("123456789012345678901234567890").message.contains("64-bit range"));
}

#[test]
fn malformed_text_is_rejected() {
    for text in [
        "",
        "{",
        "{\"a\" 1}",
        "[1,]",
        "{\"a\":1,}",
        "\"tab\tinside\"",
        "\"\\ud800\"",
        "\u{feff}{}",
        "{} {}",
        "01",
        "tru",
    ] {
        assert!(parse_strict(text).is_err(), "{text:?} must be rejected");
    }
}

#[test]
fn escapes_and_surrogate_pairs_decode() {
    let document = parse_strict(r#"["\u00e9\n\/\"", "\ud83d\ude00"]"#).expect("valid JSON");
    assert_eq!(document.value(), &json!(["é\n/\"", "😀"]));
}

#[test]
fn canonical_bytes_sort_keys_and_escape_like_the_protocol() {
    // Expected bytes from Python's json.dumps(ensure_ascii=False,
    // sort_keys=True, separators=(",", ":")), the protocol's reference form.
    let value = json!({"b": [1, "é\n\u{1}\""], "a": null, "é": true, "Z": -3});
    assert_eq!(
        String::from_utf8(canonical_bytes(&value)).unwrap(),
        "{\"Z\":-3,\"a\":null,\"b\":[1,\"é\\n\\u0001\\\"\"],\"é\":true}"
    );
}

#[test]
fn framed_digest_matches_the_protocol_frame_layout() {
    // Reference value computed independently with Python's hashlib over
    // u64_be(len(tag)) || tag || u64_be(len(payload)) || payload frames.
    let mut digest = FramedDigest::new("classic-conformance-expectation-v1");
    digest.frame("pack", b"{\"a\":1}");
    assert_eq!(
        digest.finish(),
        "sha256:21ad89b0615a65b6e5faaf5e59702b0155a43cdf6f7920d8b919840d6524fd65"
    );
}

#[test]
fn pointer_escapes_reference_tokens() {
    assert_eq!(pointer("", "a/b~c"), "/a~1b~0c");
    assert_eq!(pointer("/x", 3), "/x/3");
}
