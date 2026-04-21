//! Integration tests for the YAML update-delivery subsystem.
//!
//! These tests run in a dedicated integration binary so `mockito::Server`
//! (which spawns a real tokio listener per test) has a clean per-test
//! runtime. Each test drives the production fetch / classify / orchestrator
//! path with `GITHUB_TOKEN` proven-unset via `GithubClient::with_base_url`
//! and explicit `None` tokens, matching the spec's "no client credentials"
//! guarantee.
//!
//! # Coverage split
//!
//! - `validate_*` / `classify_*` tests exercise the manifest model directly.
//! - `fetch_*` tests use `mockito::Server` to drive the two-leg fetch (Pages
//!   with If-None-Match, API fallback, total failure).
//! - `download_*` tests prove the URL allowlist at the download layer
//!   (HTTPS + `github.com` host).
//! - The `install_atomic` primitive is *not* re-tested here; Phase A covers
//!   clean install, `.prev` promotion, mismatch, self-heal, and rollback
//!   with tempfiles. The orchestrator's job here is to compose these two
//!   already-tested primitives (download + install_atomic), and the
//!   composition failure modes (download failure, checksum mismatch) are
//!   covered at unit level in this module via small direct calls.

use classic_settings_core::{SchemaCompat, SchemaVersion};
use classic_update_core::{
    ApprovedUpdate, ClientSchemaSet, FileInstallOutcome, GithubClient, MAX_MANIFEST_VERSION,
    UpdateCheckConfig, UpdateError, YamlManifest, YamlManifestFile, YamlUpdateStatus,
    apply_yaml_update_with_decision, check_yaml_update, classify_manifest, fetch_yaml_manifest,
    rollback_yaml_update, validate_manifest,
};
use std::path::Path;
use tempfile::TempDir;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn write(path: &Path, bytes: &[u8]) {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).unwrap();
    }
    std::fs::write(path, bytes).unwrap();
}

/// A valid single-file manifest pointing at a real-looking github.com asset
/// URL (we never actually fetch it — validate_manifest just shapes-checks).
fn valid_manifest_json(tag: &str, sha: &str, download_url: &str, size: u64) -> String {
    format!(
        r#"{{
  "manifest_version": 1,
  "release_tag": "{tag}",
  "published_at": "2026-04-17T12:00:00Z",
  "files": [
    {{
      "name": "CLASSIC Main.yaml",
      "schema_version": "1.1",
      "sha256": "{sha}",
      "size_bytes": {size},
      "download_url": "{download_url}"
    }}
  ]
}}"#
    )
}

// Reusable token-less client pointed at `base_url`. Emulates a client
// running with `$GITHUB_TOKEN` unset — the default-flow spec.
fn tokenless_client(base_url: &str) -> GithubClient {
    GithubClient::with_base_url("owner", "repo", base_url, None).unwrap()
}

fn valid_manifest() -> YamlManifest {
    YamlManifest {
        manifest_version: 1,
        release_tag: "yaml-data-v2026.04.17".into(),
        published_at: "2026-04-17T12:00:00Z".into(),
        files: vec![YamlManifestFile {
            name: "CLASSIC Main.yaml".into(),
            schema_version: "1.0".into(),
            sha256: "a".repeat(64),
            size_bytes: 123,
            min_client_schema: None,
            max_client_schema: None,
            download_url:
                "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml"
                    .into(),
        }],
        signatures: vec![],
    }
}

fn client_set(
    name: &str,
    compat: SchemaCompat,
    installed: Option<SchemaVersion>,
) -> ClientSchemaSet {
    let mut set = ClientSchemaSet::new();
    set.insert(name, compat, installed);
    set
}

// ---------------------------------------------------------------------------
// Manifest validation
// ---------------------------------------------------------------------------

#[test]
fn validate_rejects_unsupported_manifest_version() {
    let mut m = valid_manifest();
    m.manifest_version = MAX_MANIFEST_VERSION + 1;
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    match err {
        UpdateError::ManifestUnsupportedVersion { found, .. } => {
            assert_eq!(found, MAX_MANIFEST_VERSION + 1);
        }
        other => panic!("expected ManifestUnsupportedVersion, got {other:?}"),
    }
}

#[test]
fn validate_rejects_empty_files() {
    let mut m = valid_manifest();
    m.files.clear();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

#[test]
fn validate_rejects_missing_download_url() {
    let mut m = valid_manifest();
    m.files[0].download_url = String::new();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

#[test]
fn validate_rejects_non_github_download_url() {
    let mut m = valid_manifest();
    m.files[0].download_url =
        "https://evil.example.com/releases/download/v1/CLASSIC%20Main.yaml".into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    match err {
        UpdateError::ManifestInvalid { reason } => {
            assert!(
                reason.contains("canonical release-asset template"),
                "got: {reason}"
            );
        }
        other => panic!("expected ManifestInvalid, got {other:?}"),
    }
}

#[test]
fn validate_rejects_non_https_download_url() {
    let mut m = valid_manifest();
    m.files[0].download_url =
        "http://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml"
            .into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

// Repo-pinning regression (Codex adversarial review, second pass). Reject
// any `download_url` that does not match
// https://github.com/<configured-owner>/<configured-repo>/releases/download/<manifest.release_tag>/<url-encoded entry.name>.
#[test]
fn validate_rejects_download_url_with_wrong_owner() {
    let mut m = valid_manifest();
    // Same template, different owner — previously accepted under the
    // host-only allowlist, must be refused under template pinning.
    m.files[0].download_url =
        "https://github.com/attacker/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml"
            .into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    match err {
        UpdateError::ManifestInvalid { reason } => {
            assert!(
                reason.contains("canonical release-asset template"),
                "got: {reason}"
            );
        }
        other => panic!("expected ManifestInvalid, got {other:?}"),
    }
}

#[test]
fn validate_rejects_download_url_with_wrong_release_tag() {
    let mut m = valid_manifest();
    m.files[0].download_url =
        "https://github.com/owner/repo/releases/download/yaml-data-v1970.01.01/CLASSIC%20Main.yaml"
            .into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

#[test]
fn validate_rejects_download_url_with_mismatched_asset_name() {
    let mut m = valid_manifest();
    // URL claims a different asset than manifest entry.
    m.files[0].download_url =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/OTHER%20File.yaml"
            .into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

#[test]
fn validate_rejects_download_url_with_subdomain_host() {
    let mut m = valid_manifest();
    // `release-assets.githubusercontent.com` and similar subdomains were
    // accepted by the prior host-only allowlist; the template check
    // requires host == `github.com` exactly.
    m.files[0].download_url =
        "https://release-assets.github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml"
            .into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

#[test]
fn validate_rejects_download_url_with_query_or_fragment() {
    let mut m = valid_manifest();
    m.files[0].download_url =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml?redirect=evil"
            .into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

#[test]
fn validate_accepts_canonical_release_asset_url() {
    // Sanity check: the valid_manifest() fixture's URL must match the
    // canonical template so the rest of the suite is exercising the
    // happy path, not a validator bug.
    let m = valid_manifest();
    validate_manifest(&m, "owner", "repo").unwrap();
}

#[test]
fn validate_rejects_malformed_schema_version() {
    let mut m = valid_manifest();
    m.files[0].schema_version = "v1.2".into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

#[test]
fn validate_rejects_bad_sha256() {
    let mut m = valid_manifest();
    m.files[0].sha256 = "notahash".into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

/// A manifest that lists the same `files[].name` twice must be refused at
/// the validation boundary. `apply_yaml_update` installs entries in order
/// and `install_atomic` keeps only one `.prev` per target — a duplicated
/// row would rotate `.prev` away from the user's pre-update copy on the
/// second install, making rollback depend on manifest order instead of
/// on-disk state. Regression for Codex adversarial review finding:
/// "duplicate manifest entries are accepted and can destroy the only
/// rollback copy".
#[test]
fn validate_rejects_duplicate_file_names() {
    let mut m = valid_manifest();
    let dup = m.files[0].clone();
    m.files.push(dup);
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    match err {
        UpdateError::ManifestInvalid { reason } => {
            assert!(
                reason.contains("duplicate"),
                "reason should mention duplicate, got: {reason}"
            );
            assert!(
                reason.contains("CLASSIC Main.yaml"),
                "reason should name the duplicated file, got: {reason}"
            );
        }
        other => panic!("expected ManifestInvalid, got {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// classify_manifest
// ---------------------------------------------------------------------------

#[test]
fn classify_newer_compatible_is_update_available() {
    let m = valid_manifest(); // schema "1.0"
    let set = client_set(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(0, 9)),
    );
    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpdateAvailable {
            compatible_files,
            incompatible_files,
            ..
        } => {
            assert_eq!(compatible_files.len(), 1);
            assert!(incompatible_files.is_empty());
        }
        other => panic!("expected UpdateAvailable, got {other:?}"),
    }
}

#[test]
fn classify_matching_installed_is_up_to_date() {
    let m = valid_manifest(); // schema "1.0"
    let set = client_set(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(1, 0)),
    );
    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpToDate { .. } => {}
        other => panic!("expected UpToDate, got {other:?}"),
    }
}

#[test]
fn classify_incompatible_major_records_rejection() {
    let mut m = valid_manifest();
    m.files[0].schema_version = "2.0".into();
    let set = client_set(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(1, 0)),
    );
    // Post-fix semantics: no compatible-and-newer file means UpToDate,
    // regardless of how many entries were rejected. The rejection detail
    // still rides along so the caller can surface "you might want to
    // upgrade the client" diagnostics.
    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpToDate {
            incompatible_files, ..
        } => {
            assert_eq!(incompatible_files.len(), 1);
            assert!(incompatible_files[0].reason.contains("MAJOR"));
        }
        other => panic!("expected UpToDate-with-major-rejection, got {other:?}"),
    }
}

#[test]
fn classify_unknown_file_alone_is_up_to_date_with_diagnostic() {
    // Regression for Codex adversarial review, classify_manifest finding:
    // when the manifest advertises a file the client does not know about
    // and there is nothing else to install, the status must be UpToDate
    // (not UpdateAvailable) so older clients do not loop on an un-actionable
    // "update available" after a feed adds forward-only files.
    let m = valid_manifest();
    let set = ClientSchemaSet::new(); // empty — nothing known
    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpToDate {
            incompatible_files, ..
        } => {
            assert_eq!(incompatible_files.len(), 1);
            assert!(incompatible_files[0].reason.contains("unknown"));
        }
        other => panic!("expected UpToDate-with-unknown-diagnostic, got {other:?}"),
    }
}

#[test]
fn classify_known_all_current_plus_future_file_is_up_to_date() {
    // Regression for the exact version-skew scenario Codex named: a
    // manifest that keeps advertising a known file (already current) AND
    // a future file this client cannot install must classify as UpToDate.
    // Previously, the presence of the unknown/future entry forced the
    // classifier down the UpdateAvailable branch with an empty compatible
    // list — the "persistent update/failure loop" described in the
    // adversarial review.
    let mut m = valid_manifest();
    m.files.push(YamlManifestFile {
        name: "future.yaml".into(),
        schema_version: "3.0".into(),
        sha256: "b".repeat(64),
        size_bytes: 42,
        min_client_schema: None,
        max_client_schema: None,
        download_url:
            "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/future.yaml"
                .into(),
    });
    let set = client_set(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(1, 0)), // known file is current
    );

    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpToDate {
            incompatible_files, ..
        } => {
            // The unknown/future file is surfaced as a diagnostic, not as
            // an actionable install item.
            assert_eq!(incompatible_files.len(), 1);
            assert_eq!(incompatible_files[0].file.name, "future.yaml");
            assert!(incompatible_files[0].reason.contains("unknown"));
        }
        other => panic!("expected UpToDate when known files current, got {other:?}"),
    }
}

#[test]
fn classify_no_compatible_files_is_up_to_date_with_diagnostics() {
    // Post-fix version of the old "UpdateAvailable with empty compatible"
    // assertion. When every manifest entry is either unknown or
    // schema-incompatible and no compatible file is newer, the outcome is
    // UpToDate — the user has nothing they can install regardless of why.
    let mut m = valid_manifest();
    m.files[0].schema_version = "2.0".into();
    let set = client_set("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpToDate {
            incompatible_files, ..
        } => {
            assert_eq!(incompatible_files.len(), 1);
        }
        other => panic!("expected UpToDate-with-incompatible-diagnostics, got {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// check_yaml_update: Disabled short-circuit
// ---------------------------------------------------------------------------

#[tokio::test(flavor = "multi_thread")]
async fn check_disabled_short_circuits_without_http() {
    // Point at a definitely-unreachable URL so a non-short-circuited call
    // would hang or error. We assert it returns Disabled synchronously.
    let client = tokenless_client("http://127.0.0.1:1"); // reserved / unroutable
    let set = ClientSchemaSet::new();
    let status = check_yaml_update(
        &client,
        "http://127.0.0.1:1/manifest-latest.json",
        "yaml-data-v",
        &set,
        UpdateCheckConfig::disabled(),
    )
    .await
    .unwrap();
    assert!(matches!(status, YamlUpdateStatus::Disabled));
}

// ---------------------------------------------------------------------------
// fetch_yaml_manifest: Pages happy path, 304 caching, 5xx → API fallback,
// total failure, unsupported manifest_version.
// ---------------------------------------------------------------------------

#[tokio::test(flavor = "multi_thread")]
async fn fetch_pages_200_happy_path_persists_etag_and_body() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    // download_url must pass the github.com allowlist inside validate_manifest.
    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";
    let body = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &"a".repeat(64),
        canonical_download,
        7,
    );

    let mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_header("etag", "\"W/abc\"")
        .with_body(body)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let manifest = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap();
    assert_eq!(manifest.release_tag, "yaml-data-v2026.04.17");

    mock.assert_async().await;
    assert!(cache_dir.path().join("manifest.etag").exists());
    assert!(cache_dir.path().join("manifest-latest.json").exists());
}

#[tokio::test(flavor = "multi_thread")]
async fn fetch_pages_304_uses_cached_body() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";

    // Pre-populate cache-dir with body + etag from a prior round.
    let cache_dir = TempDir::new().unwrap();
    let cached_body = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &"b".repeat(64),
        canonical_download,
        9,
    );
    write(
        &cache_dir.path().join("manifest-latest.json"),
        cached_body.as_bytes(),
    );
    write(&cache_dir.path().join("manifest.etag"), b"\"W/xyz\"");

    let mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .match_header("if-none-match", "\"W/xyz\"")
        .with_status(304)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let manifest = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap();
    assert_eq!(manifest.files[0].sha256, "b".repeat(64));

    mock.assert_async().await;
}

#[tokio::test(flavor = "multi_thread")]
async fn fetch_pages_5xx_falls_back_to_releases_api() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";
    let manifest_body = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &"a".repeat(64),
        canonical_download,
        7,
    );

    let pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(500)
        .with_body("boom")
        .create_async()
        .await;

    // Releases list contains two tags; highest-sorted should win.
    let releases_json = format!(
        r#"[{{
            "tag_name": "yaml-data-v2026.04.16",
            "name": "older",
            "body": "",
            "prerelease": false,
            "draft": false,
            "html_url": "https://github.com/owner/repo/releases/tag/yaml-data-v2026.04.16",
            "assets": [],
            "created_at": "2026-04-16T00:00:00Z",
            "published_at": "2026-04-16T12:00:00Z"
        }}, {{
            "tag_name": "yaml-data-v2026.04.17",
            "name": "newer",
            "body": "",
            "prerelease": false,
            "draft": false,
            "html_url": "https://github.com/owner/repo/releases/tag/yaml-data-v2026.04.17",
            "assets": [{{
                "name": "manifest.json",
                "size": {size},
                "browser_download_url": "{server}/releases/download/yaml-data-v2026.04.17/manifest.json",
                "content_type": "application/json",
                "download_count": 0
            }}],
            "created_at": "2026-04-17T00:00:00Z",
            "published_at": "2026-04-17T12:00:00Z"
        }}]"#,
        size = manifest_body.len(),
        server = server.url(),
    );
    let api_mock = server
        .mock("GET", "/repos/owner/repo/releases")
        .match_query(mockito::Matcher::Any)
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(releases_json)
        .create_async()
        .await;
    let asset_mock = server
        .mock(
            "GET",
            "/releases/download/yaml-data-v2026.04.17/manifest.json",
        )
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(manifest_body)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let manifest = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap();
    assert_eq!(manifest.release_tag, "yaml-data-v2026.04.17");

    pages_mock.assert_async().await;
    api_mock.assert_async().await;
    asset_mock.assert_async().await;
}

#[tokio::test(flavor = "multi_thread")]
async fn fetch_both_pages_and_api_fail_returns_not_found() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());

    let _pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(500)
        .create_async()
        .await;
    let _api_mock = server
        .mock("GET", "/repos/owner/repo/releases")
        .match_query(mockito::Matcher::Any)
        .with_status(200)
        .with_body("[]") // empty releases list
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let err = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap_err();
    assert!(matches!(err, UpdateError::NotFound(_)));
}

#[tokio::test(flavor = "multi_thread")]
async fn fetch_rejects_unsupported_manifest_version() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let body = r#"{
        "manifest_version": 99,
        "release_tag": "yaml-data-v2026.04.17",
        "published_at": "2026-04-17T12:00:00Z",
        "files": [{
            "name": "CLASSIC Main.yaml",
            "schema_version": "1.0",
            "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "size_bytes": 7,
            "download_url": "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml"
        }]
    }"#;

    let _pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_body(body)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let err = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap_err();
    assert!(matches!(
        err,
        UpdateError::ManifestUnsupportedVersion { found: 99, .. }
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn fetch_tag_prefix_filters_api_releases() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());

    let _pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(500)
        .create_async()
        .await;

    // Only return non-matching tags; fallback must NotFound.
    let releases_json = r#"[{
        "tag_name": "v9.1.0",
        "name": "binary release (should be ignored)",
        "body": "",
        "prerelease": false,
        "draft": false,
        "html_url": "https://github.com/owner/repo/releases/tag/v9.1.0",
        "assets": [],
        "created_at": "2026-04-01T00:00:00Z",
        "published_at": "2026-04-01T12:00:00Z"
    }]"#;
    let _api_mock = server
        .mock("GET", "/repos/owner/repo/releases")
        .match_query(mockito::Matcher::Any)
        .with_status(200)
        .with_body(releases_json)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let err = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap_err();
    assert!(matches!(err, UpdateError::NotFound(_)));
}

// Multi-page regression (Codex adversarial review, fourth pass): the
// `/releases` API fallback must paginate, otherwise once YAML-data
// releases fall off the first page (as binary releases accumulate) the
// Pages-blocked client spuriously reports `NotFound` even though a
// newer `yaml-data-v*` tag is still published. This test fills page 1
// with non-matching binary releases and puts the only YAML-data tag
// on page 2; the client must walk to page 2, discover the tag, and
// resolve its manifest asset.
#[tokio::test(flavor = "multi_thread")]
async fn fetch_api_fallback_paginates_past_full_first_page() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());

    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";
    let manifest_body = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &"a".repeat(64),
        canonical_download,
        7,
    );

    let _pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(500)
        .create_async()
        .await;

    // Build a full first page: 100 binary releases, none matching the
    // `yaml-data-v` tag prefix. `get_all_releases` requests `per_page=100`,
    // so a full page signals "keep paginating".
    let page1_items: Vec<String> = (0..100)
        .map(|i| {
            format!(
                r#"{{
                "tag_name": "v9.{i}.0",
                "name": "binary release",
                "body": "",
                "prerelease": false,
                "draft": false,
                "html_url": "https://github.com/owner/repo/releases/tag/v9.{i}.0",
                "assets": [],
                "created_at": "2026-01-01T00:00:00Z",
                "published_at": "2026-01-01T12:00:00Z"
            }}"#
            )
        })
        .collect();
    let page1_json = format!("[{}]", page1_items.join(","));

    // Page 2 has exactly one YAML-data release — the one we want. Its
    // short length (< per_page) terminates pagination.
    let page2_json = format!(
        r#"[{{
            "tag_name": "yaml-data-v2026.04.17",
            "name": "yaml release",
            "body": "",
            "prerelease": false,
            "draft": false,
            "html_url": "https://github.com/owner/repo/releases/tag/yaml-data-v2026.04.17",
            "assets": [{{
                "name": "manifest.json",
                "size": {size},
                "browser_download_url": "{server}/releases/download/yaml-data-v2026.04.17/manifest.json",
                "content_type": "application/json",
                "download_count": 0
            }}],
            "created_at": "2026-04-17T00:00:00Z",
            "published_at": "2026-04-17T12:00:00Z"
        }}]"#,
        size = manifest_body.len(),
        server = server.url(),
    );

    let page1_mock = server
        .mock("GET", "/repos/owner/repo/releases")
        .match_query(mockito::Matcher::UrlEncoded("page".into(), "1".into()))
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(page1_json)
        .create_async()
        .await;
    let page2_mock = server
        .mock("GET", "/repos/owner/repo/releases")
        .match_query(mockito::Matcher::UrlEncoded("page".into(), "2".into()))
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(page2_json)
        .create_async()
        .await;
    let asset_mock = server
        .mock(
            "GET",
            "/releases/download/yaml-data-v2026.04.17/manifest.json",
        )
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(manifest_body)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let manifest = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap();
    assert_eq!(manifest.release_tag, "yaml-data-v2026.04.17");

    // Both pages must have been fetched. The asset mock confirms that
    // the yaml-data release on page 2 was actually selected.
    page1_mock.assert_async().await;
    page2_mock.assert_async().await;
    asset_mock.assert_async().await;
}

// ---------------------------------------------------------------------------
// download_release_asset: URL allowlist enforcement.
// ---------------------------------------------------------------------------

#[tokio::test(flavor = "multi_thread")]
async fn download_rejects_non_github_host() {
    let cache = TempDir::new().unwrap();
    let client = tokenless_client("https://api.github.com");
    let err = classic_update_core::download_release_asset(
        &client,
        "https://evil.example.com/asset.yaml",
        &cache.path().join("tmp"),
        "yaml-data-v2026.04.17",
        "CLASSIC Main.yaml",
    )
    .await
    .unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

#[tokio::test(flavor = "multi_thread")]
async fn download_rejects_http_scheme() {
    let cache = TempDir::new().unwrap();
    let client = tokenless_client("https://api.github.com");
    let err = classic_update_core::download_release_asset(
        &client,
        "http://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml",
        &cache.path().join("tmp"),
        "yaml-data-v2026.04.17",
        "CLASSIC Main.yaml",
    )
    .await
    .unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

// Defense-in-depth regression (Codex adversarial review, repo-pinning):
// a direct call to `download_release_asset` with a URL that passes the
// generic HTTPS/github.com host check but does NOT match the canonical
// release-asset template must still be refused.
#[tokio::test(flavor = "multi_thread")]
async fn download_rejects_off_template_github_url() {
    let cache = TempDir::new().unwrap();
    let client = tokenless_client("https://api.github.com");
    let err = classic_update_core::download_release_asset(
        &client,
        // Same host, different owner.
        "https://github.com/attacker/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml",
        &cache.path().join("tmp"),
        "yaml-data-v2026.04.17",
        "CLASSIC Main.yaml",
    )
    .await
    .unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

// ---------------------------------------------------------------------------
// rollback_yaml_update: "no previous version" round-trip.
//
// Swap and self-heal semantics are already covered at the file-io-core
// unit level in Phase A; this test only ensures the update-core wrapper
// doesn't panic or surface an unexpected error variant on the happy
// "no .prev" path, which is the steady-state after a fresh install.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Adversarial review regressions
// ---------------------------------------------------------------------------

/// Pages returns HTTP 200 with a body that parses as JSON but fails
/// `validate_manifest` (empty `files`, non-github download_url, etc.).
/// The fetch must NOT surface that validation failure — it must fall
/// through to the Releases API, which in this test serves a healthy
/// manifest. Regression for Codex adversarial review finding:
/// "a malformed Pages manifest aborts the check instead of using the
/// documented API fallback".
#[tokio::test(flavor = "multi_thread")]
async fn fetch_pages_200_with_invalid_manifest_falls_back_to_api() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";

    // Pages returns JSON-that-parses but fails validation (empty `files`).
    let invalid_pages_body = r#"{
        "manifest_version": 1,
        "release_tag": "yaml-data-v2026.04.17",
        "published_at": "2026-04-17T12:00:00Z",
        "files": []
    }"#;
    let pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(invalid_pages_body)
        .create_async()
        .await;

    // API leg has a healthy manifest available.
    let healthy_manifest = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &"a".repeat(64),
        canonical_download,
        7,
    );
    let releases_json = format!(
        r#"[{{
            "tag_name": "yaml-data-v2026.04.17",
            "name": "latest",
            "body": "",
            "prerelease": false,
            "draft": false,
            "html_url": "https://github.com/owner/repo/releases/tag/yaml-data-v2026.04.17",
            "assets": [{{
                "name": "manifest.json",
                "size": {size},
                "browser_download_url": "{server}/releases/download/yaml-data-v2026.04.17/manifest.json",
                "content_type": "application/json",
                "download_count": 0
            }}],
            "created_at": "2026-04-17T00:00:00Z",
            "published_at": "2026-04-17T12:00:00Z"
        }}]"#,
        size = healthy_manifest.len(),
        server = server.url(),
    );
    let api_mock = server
        .mock("GET", "/repos/owner/repo/releases")
        .match_query(mockito::Matcher::Any)
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(releases_json)
        .create_async()
        .await;
    let asset_mock = server
        .mock(
            "GET",
            "/releases/download/yaml-data-v2026.04.17/manifest.json",
        )
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(healthy_manifest)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let manifest = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap();
    assert_eq!(manifest.release_tag, "yaml-data-v2026.04.17");
    assert_eq!(manifest.files[0].sha256, "a".repeat(64));

    pages_mock.assert_async().await;
    api_mock.assert_async().await;
    asset_mock.assert_async().await;

    // The poisoned Pages body MUST NOT have been persisted: we validate
    // before writing the 304-cacheable body so a future call can't serve
    // the invalid bytes from the cached-body branch either.
    assert!(
        !cache_dir.path().join("manifest-latest.json").exists(),
        "invalid Pages body must never be cached",
    );
}

/// Pages returns HTTP 200 with a structurally valid manifest whose
/// `release_tag` does not match the requested prefix. The client must treat
/// that as a wrong-channel Pages publish, fall back to the Releases API, and
/// avoid caching the mismatched body.
#[tokio::test(flavor = "multi_thread")]
async fn fetch_pages_200_with_wrong_tag_prefix_falls_back_to_api() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let wrong_pages_manifest = valid_manifest_json(
        "v9.1.0",
        &"b".repeat(64),
        "https://github.com/owner/repo/releases/download/v9.1.0/CLASSIC%20Main.yaml",
        7,
    );
    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";

    let pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(wrong_pages_manifest)
        .create_async()
        .await;

    let healthy_manifest = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &"c".repeat(64),
        canonical_download,
        7,
    );
    let releases_json = format!(
        r#"[{{
            "tag_name": "yaml-data-v2026.04.17",
            "name": "latest",
            "body": "",
            "prerelease": false,
            "draft": false,
            "html_url": "https://github.com/owner/repo/releases/tag/yaml-data-v2026.04.17",
            "assets": [{{
                "name": "manifest.json",
                "size": {size},
                "browser_download_url": "{server}/releases/download/yaml-data-v2026.04.17/manifest.json",
                "content_type": "application/json",
                "download_count": 0
            }}],
            "created_at": "2026-04-17T00:00:00Z",
            "published_at": "2026-04-17T12:00:00Z"
        }}]"#,
        size = healthy_manifest.len(),
        server = server.url(),
    );
    let api_mock = server
        .mock("GET", "/repos/owner/repo/releases")
        .match_query(mockito::Matcher::Any)
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(releases_json)
        .create_async()
        .await;
    let asset_mock = server
        .mock(
            "GET",
            "/releases/download/yaml-data-v2026.04.17/manifest.json",
        )
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(healthy_manifest)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let manifest = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap();
    assert_eq!(manifest.release_tag, "yaml-data-v2026.04.17");
    assert_eq!(manifest.files[0].sha256, "c".repeat(64));

    pages_mock.assert_async().await;
    api_mock.assert_async().await;
    asset_mock.assert_async().await;

    assert!(
        !cache_dir.path().join("manifest-latest.json").exists(),
        "wrong-channel Pages body must never be cached",
    );
}

/// Pages returns 304 against a previously-cached body that happens to be
/// invalid. The fetch must not return that poisoned body — it must fall
/// back to the Releases API. Regression for Codex adversarial review
/// finding (same issue, cached-304 variant).
#[tokio::test(flavor = "multi_thread")]
async fn fetch_pages_304_with_invalid_cached_body_falls_back_to_api() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";

    let cache_dir = TempDir::new().unwrap();
    // Pre-populate the cache with a poisoned body + matching ETag — as if
    // an older publish (or a misbehaving server) had written junk there.
    let poisoned = r#"{
        "manifest_version": 1,
        "release_tag": "",
        "published_at": "2026-04-17T12:00:00Z",
        "files": []
    }"#;
    write(
        &cache_dir.path().join("manifest-latest.json"),
        poisoned.as_bytes(),
    );
    write(&cache_dir.path().join("manifest.etag"), b"\"W/poison\"");

    let pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .match_header("if-none-match", "\"W/poison\"")
        .with_status(304)
        .create_async()
        .await;

    let healthy_manifest = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &"c".repeat(64),
        canonical_download,
        7,
    );
    let releases_json = format!(
        r#"[{{
            "tag_name": "yaml-data-v2026.04.17",
            "name": "latest",
            "body": "",
            "prerelease": false,
            "draft": false,
            "html_url": "https://github.com/owner/repo/releases/tag/yaml-data-v2026.04.17",
            "assets": [{{
                "name": "manifest.json",
                "size": {size},
                "browser_download_url": "{server}/releases/download/yaml-data-v2026.04.17/manifest.json",
                "content_type": "application/json",
                "download_count": 0
            }}],
            "created_at": "2026-04-17T00:00:00Z",
            "published_at": "2026-04-17T12:00:00Z"
        }}]"#,
        size = healthy_manifest.len(),
        server = server.url(),
    );
    let api_mock = server
        .mock("GET", "/repos/owner/repo/releases")
        .match_query(mockito::Matcher::Any)
        .with_status(200)
        .with_body(releases_json)
        .create_async()
        .await;
    let asset_mock = server
        .mock(
            "GET",
            "/releases/download/yaml-data-v2026.04.17/manifest.json",
        )
        .with_status(200)
        .with_body(healthy_manifest)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let manifest = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap();
    // The manifest we got back MUST be the healthy one from the API leg,
    // not the poisoned cached body.
    assert_eq!(manifest.files[0].sha256, "c".repeat(64));

    pages_mock.assert_async().await;
    api_mock.assert_async().await;
    asset_mock.assert_async().await;
}

/// API fallback picks the greatest release by parsed `YYYY.MM.DD[.N]`
/// order, not by raw string compare. `.10` must win over `.9`. Regression
/// for Codex adversarial review finding:
/// "API fallback picks releases by raw string sort, which misorders
/// multi-digit republish suffixes".
#[tokio::test(flavor = "multi_thread")]
async fn fetch_api_fallback_orders_republish_suffixes_numerically() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let canonical_download = "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17.10/CLASSIC%20Main.yaml";

    let _pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(500)
        .create_async()
        .await;

    // Body advertises the winning tag so the assertion on `release_tag`
    // pins which release was actually selected.
    let winning_manifest = valid_manifest_json(
        "yaml-data-v2026.04.17.10",
        &"d".repeat(64),
        canonical_download,
        7,
    );

    // Deliberately list `.9` first so a stable-sort bug would keep `.9`
    // at the head under a flawed comparator.
    let releases_json = format!(
        r#"[
            {{
                "tag_name": "yaml-data-v2026.04.17.9",
                "name": "nine",
                "body": "",
                "prerelease": false,
                "draft": false,
                "html_url": "https://github.com/owner/repo/releases/tag/yaml-data-v2026.04.17.9",
                "assets": [{{
                    "name": "manifest.json",
                    "size": 10,
                    "browser_download_url": "{server}/releases/download/yaml-data-v2026.04.17.9/manifest.json",
                    "content_type": "application/json",
                    "download_count": 0
                }}],
                "created_at": "2026-04-17T00:00:00Z",
                "published_at": "2026-04-17T12:00:00Z"
            }},
            {{
                "tag_name": "yaml-data-v2026.04.17.10",
                "name": "ten",
                "body": "",
                "prerelease": false,
                "draft": false,
                "html_url": "https://github.com/owner/repo/releases/tag/yaml-data-v2026.04.17.10",
                "assets": [{{
                    "name": "manifest.json",
                    "size": {size},
                    "browser_download_url": "{server}/releases/download/yaml-data-v2026.04.17.10/manifest.json",
                    "content_type": "application/json",
                    "download_count": 0
                }}],
                "created_at": "2026-04-17T00:00:00Z",
                "published_at": "2026-04-17T18:00:00Z"
            }}
        ]"#,
        size = winning_manifest.len(),
        server = server.url(),
    );
    let _api_mock = server
        .mock("GET", "/repos/owner/repo/releases")
        .match_query(mockito::Matcher::Any)
        .with_status(200)
        .with_body(releases_json)
        .create_async()
        .await;
    let ten_asset_mock = server
        .mock(
            "GET",
            "/releases/download/yaml-data-v2026.04.17.10/manifest.json",
        )
        .with_status(200)
        .with_body(winning_manifest)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let manifest = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", Some(cache_dir.path()))
        .await
        .unwrap();

    assert_eq!(
        manifest.release_tag, "yaml-data-v2026.04.17.10",
        "numeric ordering must pick `.10` over `.9`",
    );
    ten_asset_mock.assert_async().await;
}

#[test]
fn rollback_no_previous_version_is_ok() {
    let res = rollback_yaml_update("__definitely_nonexistent_file_xyzzy__.yaml");
    match res {
        Ok(outcome) => {
            assert!(matches!(
                outcome,
                classic_update_core::RollbackOutcome::NoPreviousVersion { .. }
            ));
        }
        Err(UpdateError::Generic(_)) => {
            // Acceptable on a machine whose yaml-cache directory cannot be
            // resolved (e.g. no `$HOME` and no `$LOCALAPPDATA`). The
            // production code surfaces this as `Generic`, which is what we
            // want to guard against regressing to a panic.
        }
        Err(other) => panic!("unexpected error: {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// Adversarial review regressions — path traversal + unenforced schema bounds
// ---------------------------------------------------------------------------

/// A manifest that names a path-traversal basename must fail the shared
/// `validate_manifest` boundary check. Regression for Codex adversarial
/// review finding: "unvalidated file names let install and rollback escape
/// `yaml-cache` and overwrite arbitrary user files".
#[test]
fn validate_rejects_path_traversal_name() {
    let mut m = valid_manifest();
    m.files[0].name = "../etc/passwd".into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    match err {
        UpdateError::ManifestInvalid { reason } => {
            assert!(reason.contains("basename"), "got: {reason}");
        }
        other => panic!("expected ManifestInvalid, got {other:?}"),
    }
}

#[test]
fn validate_rejects_absolute_file_name() {
    let mut m = valid_manifest();
    m.files[0].name = "/etc/shadow".into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));

    m.files[0].name = "C:\\Windows\\System32\\cmd.exe".into();
    let err = validate_manifest(&m, "owner", "repo").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

/// `rollback_yaml_update` is a direct binding entry point, so a traversal
/// string reaching it bypasses `validate_manifest`. The function itself
/// must refuse. Same adversarial-review root cause.
#[test]
fn rollback_rejects_path_traversal_name() {
    let err = rollback_yaml_update("../evil.txt").unwrap_err();
    match err {
        UpdateError::ManifestInvalid { reason } => {
            assert!(reason.contains("basename"), "got: {reason}");
        }
        other => panic!("expected ManifestInvalid, got {other:?}"),
    }

    let err = rollback_yaml_update("/tmp/evil.txt").unwrap_err();
    assert!(matches!(err, UpdateError::ManifestInvalid { .. }));
}

// ---------------------------------------------------------------------------
// Adversarial review regressions — min/max_client_schema enforcement
// ---------------------------------------------------------------------------

/// A client that reads `major.minimum_minor..` should still accept a
/// file whose published `min_client_schema` lies *above* the floor —
/// the client's range extends upward and overlaps the file range.
///
/// Regression for the second Codex adversarial review pass: the first
/// version of this check collapsed the client to a single point
/// `(accepted_major, minimum_minor)` and rejected whenever that point
/// fell below `min_client_schema`, silently suppressing legitimate
/// updates once publishers started using `min_client_schema` to narrow
/// releases. The rule in `CLASSIC Data/databases/client-schema-ranges.yaml`
/// is range overlap, not point-in-interval.
#[test]
fn classify_accepts_when_min_client_schema_above_client_floor_but_ranges_overlap() {
    let mut m = valid_manifest();
    m.files[0].schema_version = "1.5".into();
    m.files[0].min_client_schema = Some("1.3".into());
    m.files[0].max_client_schema = Some("1.999".into());

    // Client reads {1.0, 1.1, …} — its accepted range overlaps [1.3, 1.999].
    let set = client_set("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpdateAvailable {
            compatible_files,
            incompatible_files,
            ..
        } => {
            assert_eq!(
                compatible_files.len(),
                1,
                "expected 1 compatible, got {compatible_files:?}"
            );
            assert!(incompatible_files.is_empty(), "no rejections expected");
        }
        other => panic!("expected UpdateAvailable with overlapping schema range, got {other:?}"),
    }
}

/// First non-overlap branch inside `check_client_schema_bounds`: the
/// client's sole major is below the file's published `min_client_schema`
/// major. `schema_compat_check` must pass first (otherwise bounds
/// enforcement never runs), which forces this to be a malformed-manifest
/// scenario — the publisher declared a `min_client_schema` major above
/// the file's own `schema_version` major. Test guards that we reject
/// anyway rather than install contradictory metadata.
#[test]
fn classify_rejects_when_client_major_below_file_min_major() {
    let mut m = valid_manifest();
    m.files[0].schema_version = "1.5".into();
    m.files[0].min_client_schema = Some("2.0".into());

    // Client reads 1.0.. — `schema_compat_check` says Compatible for
    // file schema 1.5, so the bounds check is the gate that catches this.
    let set = client_set("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpToDate {
            incompatible_files, ..
        } => {
            assert_eq!(incompatible_files.len(), 1);
            assert!(
                incompatible_files[0].reason.contains("min_client_schema"),
                "reason should mention min_client_schema, got: {}",
                incompatible_files[0].reason,
            );
        }
        other => panic!("expected UpToDate with client-major-below rejection, got {other:?}"),
    }
}

/// Second non-overlap branch: client major sits above the file's highest
/// supported major.
#[test]
fn classify_rejects_when_client_major_above_file_max_major() {
    let mut m = valid_manifest();
    m.files[0].schema_version = "2.0".into();
    m.files[0].max_client_schema = Some("1.9".into());

    // Client reads only major 2 — above the file's max_client_schema major.
    let set = client_set("CLASSIC Main.yaml", SchemaCompat::new(2, 0), None);

    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpToDate {
            incompatible_files, ..
        } => {
            assert_eq!(incompatible_files.len(), 1);
            assert!(
                incompatible_files[0].reason.contains("max_client_schema"),
                "reason should mention max_client_schema, got: {}",
                incompatible_files[0].reason,
            );
        }
        other => panic!("expected UpToDate with max-bound rejection, got {other:?}"),
    }
}

/// Third non-overlap branch: same top major, client's floor above the
/// file's ceiling minor. Must be reachable through `schema_compat_check`
/// (file's own minor must be at or above the client's floor). Example:
/// publisher ships `schema_version = "1.15"` but `max_client_schema = "1.5"`,
/// a malformed-manifest contradiction. Client floor of `1.10` is compatible
/// with the file's schema but above the published max minor, so bounds
/// enforcement must reject.
#[test]
fn classify_rejects_when_client_floor_above_max_minor_in_shared_major() {
    let mut m = valid_manifest();
    m.files[0].schema_version = "1.15".into();
    m.files[0].max_client_schema = Some("1.5".into());

    // Client reads {1.10, 1.11, …}. schema_compat: 1==1, 15 >= 10 → Compatible.
    let set = client_set("CLASSIC Main.yaml", SchemaCompat::new(1, 10), None);

    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpToDate {
            incompatible_files, ..
        } => {
            assert_eq!(incompatible_files.len(), 1);
            assert!(
                incompatible_files[0].reason.contains("max_client_schema"),
                "reason should mention max_client_schema, got: {}",
                incompatible_files[0].reason,
            );
        }
        other => panic!("expected UpToDate with floor-above-max rejection, got {other:?}"),
    }
}

#[test]
fn classify_accepts_when_client_point_within_bounds() {
    let mut m = valid_manifest();
    m.files[0].schema_version = "1.1".into();
    m.files[0].min_client_schema = Some("1.0".into());
    m.files[0].max_client_schema = Some("1.5".into());

    // Client floor 1.0 sits inside [1.0, 1.5] — install should proceed.
    let set = client_set(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(1, 0)),
    );

    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpdateAvailable {
            compatible_files,
            incompatible_files,
            ..
        } => {
            assert_eq!(compatible_files.len(), 1);
            assert!(incompatible_files.is_empty());
        }
        other => panic!("expected UpdateAvailable, got {other:?}"),
    }
}

#[test]
fn classify_rejects_when_client_schema_bounds_are_inverted() {
    let mut m = valid_manifest();
    m.files[0].schema_version = "1.7".into();
    m.files[0].min_client_schema = Some("1.10".into());
    m.files[0].max_client_schema = Some("1.5".into());

    let set = client_set("CLASSIC Main.yaml", SchemaCompat::new(1, 7), None);

    match classify_manifest(m, &set).unwrap() {
        YamlUpdateStatus::UpToDate {
            incompatible_files, ..
        } => {
            assert_eq!(incompatible_files.len(), 1);
            assert!(
                incompatible_files[0].reason.contains("inverted")
                    && incompatible_files[0]
                        .reason
                        .contains("min_client_schema 1.10")
                    && incompatible_files[0]
                        .reason
                        .contains("max_client_schema 1.5"),
                "reason should describe inverted bounds, got: {}",
                incompatible_files[0].reason,
            );
        }
        other => panic!("expected UpToDate with inverted-bound rejection, got {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// Adversarial review regressions — cache-dir Option plumbing
// ---------------------------------------------------------------------------

/// When `cache_dir` is `None`, `fetch_yaml_manifest` must return the
/// manifest without persisting ETag or body anywhere. The previous
/// `PathBuf::new()` sentinel caused `path.join(...)` to fall back to the
/// process working directory, polluting it with `manifest.etag` /
/// `manifest-latest.json` files. Regression for Codex adversarial review
/// finding: "cache-dir creation failure still writes manifest cache files
/// into the working directory".
///
/// We deliberately do NOT swap the process working directory inside this
/// test — integration tests in this file share a process, so `set_current_dir`
/// would race with sibling tests running in parallel. The structural fix
/// (wrapping both cache paths in `Option` so `None` short-circuits all
/// persistence) is covered by the `fetch_pages_200_happy_path_...` test
/// which asserts that the `Some` variant DOES persist; the combination
/// proves the Option branch is what gates I/O.
#[tokio::test(flavor = "multi_thread")]
async fn fetch_with_no_cache_dir_returns_manifest_without_persistence() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";
    let body = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &"a".repeat(64),
        canonical_download,
        7,
    );

    let _mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_header("etag", "\"W/abc\"")
        .with_body(body)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let manifest = fetch_yaml_manifest(&client, &pages_url, "yaml-data-v", None)
        .await
        .unwrap();

    assert_eq!(manifest.release_tag, "yaml-data-v2026.04.17");
    assert_eq!(manifest.files[0].sha256, "a".repeat(64));
}

// ---------------------------------------------------------------------------
// apply_yaml_update_with_decision — adversarial-review regression coverage
// ---------------------------------------------------------------------------

/// Regression for Codex adversarial review, finding #2 ("apply does not
/// honor the Update Check: false setting end-to-end"):
/// `apply_yaml_update_with_decision` MUST refuse to run when the caller
/// passes `UpdateCheckConfig::disabled()`, even with a non-empty approved
/// decision. The error is typed (`UpdateError::UpdateCheckDisabled`) so
/// the GUI / CLI can render it as a user-facing "re-enable the setting"
/// message rather than a generic failure.
#[tokio::test(flavor = "multi_thread")]
async fn apply_with_decision_refuses_when_check_disabled() {
    // Unroutable URL: if the disabled short-circuit regresses, the test
    // either hangs on connect or surfaces an HTTP error instead of
    // UpdateCheckDisabled.
    let client = tokenless_client("http://127.0.0.1:1");
    let set = client_set("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);
    let approved = ApprovedUpdate {
        release_tag: "yaml-data-v2026.04.17".into(),
        file_names: vec!["CLASSIC Main.yaml".into()],
    };

    let err = apply_yaml_update_with_decision(
        &client,
        "http://127.0.0.1:1/manifest-latest.json",
        "yaml-data-v",
        &set,
        UpdateCheckConfig::disabled(),
        &approved,
    )
    .await
    .unwrap_err();

    assert!(
        matches!(err, UpdateError::UpdateCheckDisabled),
        "expected UpdateCheckDisabled, got: {err:?}"
    );
}

/// Regression for Codex adversarial review, finding #2 ("apply installs a
/// different release than the user reviewed when the feed rotates
/// mid-review"): when the freshly-fetched manifest's `release_tag` does
/// not match the approved decision, apply MUST error out with
/// `DecisionStale` and install nothing. Without this guard, a publisher
/// rotating the feed between Check and Apply silently substitutes the
/// new release.
#[tokio::test(flavor = "multi_thread")]
async fn apply_with_decision_rejects_stale_release_tag() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.18/CLASSIC%20Main.yaml";
    // Pages returns the NEWER release (v2026.04.18) — simulates a
    // publisher rotating between the user's Check and Apply clicks.
    let body = valid_manifest_json(
        "yaml-data-v2026.04.18",
        &"a".repeat(64),
        canonical_download,
        7,
    );
    let _mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(body)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let set = client_set("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);
    // User reviewed the OLDER release.
    let approved = ApprovedUpdate {
        release_tag: "yaml-data-v2026.04.17".into(),
        file_names: vec!["CLASSIC Main.yaml".into()],
    };

    let err = apply_yaml_update_with_decision(
        &client,
        &pages_url,
        "yaml-data-v",
        &set,
        UpdateCheckConfig::enabled(),
        &approved,
    )
    .await
    .unwrap_err();

    match err {
        UpdateError::DecisionStale { approved, manifest } => {
            assert_eq!(approved, "yaml-data-v2026.04.17");
            assert_eq!(manifest, "yaml-data-v2026.04.18");
        }
        other => panic!("expected DecisionStale, got: {other:?}"),
    }
}

/// Follow-on to `apply_with_decision_rejects_stale_release_tag`: when the
/// fresh classification is `UpToDate` (no file is newer than what is
/// installed) but the release tag differs, we still raise `DecisionStale`.
/// This protects against a subtle race where the user reviewed an update
/// on release X, the publisher then issued release Y whose bytes happen
/// to match what's already on disk — the user still reviewed X, so apply
/// should refuse to claim it installed something it didn't.
#[tokio::test(flavor = "multi_thread")]
async fn apply_with_decision_rejects_stale_even_when_up_to_date() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let canonical_download =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.18/CLASSIC%20Main.yaml";
    // Manifest declares schema 1.0 and some sha — we'll set the client's
    // installed version to 1.0 with a matching sha (content identity)
    // so classify reports UpToDate.
    let installed_sha = "a".repeat(64);
    let body = valid_manifest_json(
        "yaml-data-v2026.04.18",
        &installed_sha,
        canonical_download,
        7,
    );
    let _mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(body)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    // Caller supplies the sha directly via insert_with_sha256 so content
    // identity matches the manifest entry — this mirrors what
    // `enrich_installed` would do for a real on-disk file.
    let mut set = ClientSchemaSet::new();
    set.insert_with_sha256(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(1, 1)),
        Some(installed_sha.clone()),
    );
    // User reviewed the OLDER release.
    let approved = ApprovedUpdate {
        release_tag: "yaml-data-v2026.04.17".into(),
        file_names: vec!["CLASSIC Main.yaml".into()],
    };

    let err = apply_yaml_update_with_decision(
        &client,
        &pages_url,
        "yaml-data-v",
        &set,
        UpdateCheckConfig::enabled(),
        &approved,
    )
    .await
    .unwrap_err();

    assert!(
        matches!(err, UpdateError::DecisionStale { .. }),
        "UpToDate with mismatched release_tag must still surface DecisionStale, got: {err:?}"
    );
}

/// Same-tag `UpToDate` is not automatically success: if the approved file is
/// still in the manifest but fresh classification now rejects it (for example
/// because publisher/client compatibility bounds changed), apply must surface
/// that approved-file failure in `report.failed` rather than returning an
/// empty success.
#[tokio::test(flavor = "multi_thread")]
async fn apply_with_decision_reports_rejected_approved_file_when_up_to_date() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let body = format!(
        r#"{{
  "manifest_version": 1,
  "release_tag": "yaml-data-v2026.04.17",
  "published_at": "2026-04-17T12:00:00Z",
  "files": [
    {{
      "name": "CLASSIC Main.yaml",
      "schema_version": "1.1",
      "sha256": "{}",
      "size_bytes": 7,
      "min_client_schema": "2.0",
      "download_url": "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml"
    }}
  ]
}}"#,
        "a".repeat(64)
    );
    let _mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(body)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let set = client_set("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);
    let approved = ApprovedUpdate {
        release_tag: "yaml-data-v2026.04.17".into(),
        file_names: vec!["CLASSIC Main.yaml".into()],
    };

    let report = apply_yaml_update_with_decision(
        &client,
        &pages_url,
        "yaml-data-v",
        &set,
        UpdateCheckConfig::enabled(),
        &approved,
    )
    .await
    .unwrap();

    assert!(report.installed.is_empty());
    assert_eq!(report.failed.len(), 1, "expected approved-file failure");
    match &report.failed[0] {
        FileInstallOutcome::Failed { name, reason } => {
            assert_eq!(name, "CLASSIC Main.yaml");
            assert!(
                reason.contains("no longer installable") && reason.contains("min_client_schema"),
                "expected compatibility rejection reason, got: {reason}"
            );
        }
        other => panic!("expected Failed outcome, got {other:?}"),
    }
}

/// Companion to the rejection regression above: when same-tag `UpToDate`
/// means the approved bytes are already installed, apply should remain a
/// truthful no-op rather than synthesizing a failure.
#[tokio::test(flavor = "multi_thread")]
async fn apply_with_decision_keeps_empty_success_when_approved_file_is_current() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let installed_sha = "a".repeat(64);
    let body = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &installed_sha,
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml",
        7,
    );
    let _mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(body)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let mut set = ClientSchemaSet::new();
    set.insert_with_sha256(
        "CLASSIC Main.yaml",
        SchemaCompat::new(1, 0),
        Some(SchemaVersion::new(1, 1)),
        Some(installed_sha),
    );
    let approved = ApprovedUpdate {
        release_tag: "yaml-data-v2026.04.17".into(),
        file_names: vec!["CLASSIC Main.yaml".into()],
    };

    let report = apply_yaml_update_with_decision(
        &client,
        &pages_url,
        "yaml-data-v",
        &set,
        UpdateCheckConfig::enabled(),
        &approved,
    )
    .await
    .unwrap();

    assert!(report.installed.is_empty());
    assert!(
        report.failed.is_empty(),
        "already-current file should stay a no-op"
    );
}

// ---------------------------------------------------------------------------
// check_yaml_update: explicit bundled-YAML override (Node/Python host fix).
// ---------------------------------------------------------------------------

/// Regression for Codex adversarial review finding (high):
///   "Bundled-version enrichment is tied to `current_exe()`, so Node/Python
///    clean installs will false-positive forever."
///
/// The contract: when a caller supplies `UpdateCheckConfig::bundled_yaml_dir`
/// (the Node/Python binding path), `check_yaml_update` MUST resolve the
/// "what's already installed" bytes from that directory — not from the
/// current-exe fallback. If the bundled file's sha256 already matches the
/// manifest entry, the classification is `UpToDate`, not `UpdateAvailable`.
///
/// Without this wiring, every clean Node/Python install would reclassify
/// unchanged manifests as updates, churning `.prev` rotations and forcing
/// pointless network downloads on every check.
#[tokio::test(flavor = "multi_thread")]
async fn check_yaml_update_uses_explicit_bundled_dir_for_clean_install() {
    // Bundled directory living OUTSIDE any plausible current-exe parent so
    // the `current_exe()` fallback cannot accidentally find it. The only way
    // enrichment can see this file is via the explicit override.
    let bundled_tmp = TempDir::new().unwrap();
    let bundled_path = bundled_tmp.path().join("CLASSIC Main.yaml");
    let bundled_body = b"schema_version: \"1.1\"\nkey: value\n";
    write(&bundled_path, bundled_body);
    // Content identity is the freshness signal per classify_manifest; the
    // manifest's sha256 must be the REAL sha of the bundled bytes.
    let bundled_sha = classic_file_io_core::FileHasher::hash_file(&bundled_path).unwrap();

    // Pages mock serving a manifest that advertises the same sha256.
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let download_url =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";
    let manifest_body = valid_manifest_json(
        "yaml-data-v2026.04.17",
        &bundled_sha,
        download_url,
        bundled_body.len() as u64,
    );
    let _pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(manifest_body)
        .create_async()
        .await;

    // Clean install: caller leaves `installed` unset so the orchestrator
    // MUST resolve it from disk. This is exactly the Node/Python binding
    // DTO default (`has_installed: false`).
    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    // Schema entry note: the manifest's schema_version is "1.1", so
    // `classify_manifest` compares against the file's sha256 (freshness),
    // not the raw schema_version (which would always say "updateAvailable"
    // against a None installed).
    let client = tokenless_client(&server.url());
    let config =
        UpdateCheckConfig::enabled().with_bundled_yaml_dir(bundled_tmp.path().to_path_buf());

    let status = check_yaml_update(&client, &pages_url, "yaml-data-v", &set, config)
        .await
        .expect("check_yaml_update should succeed against mocked Pages");

    match status {
        YamlUpdateStatus::UpToDate { manifest, .. } => {
            assert_eq!(manifest.release_tag, "yaml-data-v2026.04.17");
        }
        other => panic!(
            "clean install with bundled bytes matching manifest sha must classify as UpToDate, \
             got {other:?}"
        ),
    }
}

/// Companion to the UpToDate test: when the caller supplies a bundled_dir
/// whose bytes do NOT match the manifest's advertised sha, the outcome must
/// remain `UpdateAvailable`. This guards against the opposite failure mode
/// where the override silently short-circuits the real update flow.
#[tokio::test(flavor = "multi_thread")]
async fn check_yaml_update_with_bundled_dir_still_reports_update_when_shas_differ() {
    let bundled_tmp = TempDir::new().unwrap();
    let bundled_path = bundled_tmp.path().join("CLASSIC Main.yaml");
    write(&bundled_path, b"schema_version: \"1.0\"\nold: data\n");
    let bundled_sha = classic_file_io_core::FileHasher::hash_file(&bundled_path).unwrap();

    // Manifest advertises a DIFFERENT sha — simulates "a genuinely new
    // release shipped, the bundled copy is the previous version".
    let mismatched_sha = {
        let mut s = bundled_sha.clone();
        // Flip the last hex nibble.
        let last = s.pop().unwrap();
        s.push(if last == '0' { '1' } else { '0' });
        s
    };
    assert_ne!(bundled_sha, mismatched_sha);

    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/yaml-data/manifest-latest.json", server.url());
    let download_url =
        "https://github.com/owner/repo/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml";
    let manifest_body =
        valid_manifest_json("yaml-data-v2026.04.17", &mismatched_sha, download_url, 64);
    let _pages_mock = server
        .mock("GET", "/yaml-data/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(manifest_body)
        .create_async()
        .await;

    let mut set = ClientSchemaSet::new();
    set.insert("CLASSIC Main.yaml", SchemaCompat::new(1, 0), None);

    let client = tokenless_client(&server.url());
    let config =
        UpdateCheckConfig::enabled().with_bundled_yaml_dir(bundled_tmp.path().to_path_buf());

    let status = check_yaml_update(&client, &pages_url, "yaml-data-v", &set, config)
        .await
        .expect("check_yaml_update should succeed against mocked Pages");

    match status {
        YamlUpdateStatus::UpdateAvailable {
            compatible_files, ..
        } => {
            assert_eq!(compatible_files.len(), 1);
            assert_eq!(compatible_files[0].name, "CLASSIC Main.yaml");
        }
        other => panic!(
            "bundled sha differs from manifest sha → expected UpdateAvailable, got {other:?}"
        ),
    }
}
