//! Manifest-loading cases ported from the retired Python suite
//! (`test_verify_assets_reachable.py`). The probe cases run end to end in
//! `xtask/tests/yaml_data.rs` against a localhost server.

use super::*;

/// An arbitrary well-formed lowercase SHA-256 hex digest.
const DIGEST: &str = "3d1d3f3bb27f04f62b6a0d5d0ee66e8ee1de92b6fd8ea52d1e74d3b1ee82d8f0";

fn one_file(sha256: Value) -> Vec<u8> {
    serde_json::to_vec(&serde_json::json!({
        "files": [{
            "name": "CLASSIC Fallout4.yaml",
            "download_url": "https://example.test/file.yaml",
            "sha256": sha256,
        }]
    }))
    .expect("serialize")
}

fn error(bytes: &[u8]) -> String {
    manifest_assets("manifest.json", bytes)
        .expect_err("manifest is rejected")
        .to_string()
}

#[test]
fn rejects_a_non_object_root() {
    assert!(error(br#"["not", "an", "object"]"#).contains("root is not a JSON object"));
}

#[test]
fn rejects_missing_or_empty_files() {
    assert!(error(br"{}").contains("has no non-empty 'files' array"));
    assert!(error(br#"{"files": []}"#).contains("has no non-empty 'files' array"));
}

#[test]
fn requires_string_name_url_and_sha256() {
    assert!(error(br#"{"files": [1]}"#).contains("manifest entry is not a mapping"));
    assert!(
        error(br#"{"files": [{"name": "a", "sha256": "x"}]}"#)
            .contains("missing string name/download_url")
    );
    assert!(
        error(br#"{"files": [{"name": "a", "download_url": "https://example.test/a"}]}"#)
            .contains("missing string sha256")
    );
}

#[test]
fn rejects_malformed_sha256() {
    let long = format!("{DIGEST}deadbeef");
    for digest in ["", "   ", "not-a-digest", &DIGEST[..32], long.as_str()] {
        assert!(
            error(&one_file(Value::from(digest))).contains("64-character hex digest"),
            "{digest:?}"
        );
    }
}

#[test]
fn trims_and_lowercases_sha256_and_appends_the_release_manifest_asset() {
    let bytes = one_file(Value::from(format!("  {}  ", DIGEST.to_ascii_uppercase())));

    let assets = manifest_assets("manifest.json", &bytes).expect("valid manifest");

    assert_eq!(
        assets,
        vec![
            Asset {
                name: "CLASSIC Fallout4.yaml".into(),
                url: "https://example.test/file.yaml".into(),
                sha256: DIGEST.into(),
            },
            Asset {
                name: "manifest.json".into(),
                url: "https://example.test/manifest.json".into(),
                sha256: digest::sha256_hex(&bytes),
            },
        ]
    );
}

#[test]
fn the_release_manifest_asset_sits_next_to_the_first_file() {
    let bytes = serde_json::to_vec(&serde_json::json!({
        "files": [{
            "name": "CLASSIC Fallout4.yaml",
            "download_url": "https://github.com/example/repo/releases/download/yaml-data-v2026.06.12/CLASSIC%20Fallout4.yaml",
            "sha256": DIGEST,
        }]
    }))
    .expect("serialize");

    let assets = manifest_assets("manifest.json", &bytes).expect("valid manifest");

    assert_eq!(
        assets[1].url,
        "https://github.com/example/repo/releases/download/yaml-data-v2026.06.12/manifest.json"
    );
}

#[test]
fn a_download_url_without_a_slash_cannot_locate_the_manifest_asset() {
    let bytes = serde_json::to_vec(&serde_json::json!({
        "files": [{"name": "a", "download_url": "no-slash", "sha256": DIGEST}]
    }))
    .expect("serialize");

    assert!(error(&bytes).contains("cannot derive manifest.json release asset URL"));
}
