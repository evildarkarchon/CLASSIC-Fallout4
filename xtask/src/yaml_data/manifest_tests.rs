//! Expected strings below were produced by CPython 3.12's
//! `urllib.parse.quote(..., safe="")` and `json.dumps(..., indent=2)`.

use super::*;

#[test]
fn quote_matches_python_urllib_quote_with_no_safe_characters() {
    assert_eq!(quote("CLASSIC Main.yaml"), "CLASSIC%20Main.yaml");
    assert_eq!(
        quote("a+b/c?d#e%f~_.-\u{e9}\u{1f600}"),
        "a%2Bb%2Fc%3Fd%23e%25f~_.-%C3%A9%F0%9F%98%80"
    );
}

#[test]
fn download_url_encodes_only_the_asset_name() {
    assert_eq!(
        download_url(
            "owner/repo",
            "yaml-data-v2026.04.17",
            "CLASSIC Fallout4.yaml"
        ),
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Fallout4.yaml"
    );
}

#[test]
fn ensure_ascii_escapes_like_python_json() {
    let serialized = serde_json::to_string_pretty(&serde_json::json!({
        "k": "\u{e9}\u{1f600}\u{7f}\u{1f}\"\\/"
    }))
    .expect("serialize");

    assert_eq!(
        ensure_ascii(&serialized),
        "{\n  \"k\": \"\\u00e9\\ud83d\\ude00\\u007f\\u001f\\\"\\\\/\"\n}"
    );
}
