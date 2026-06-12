use super::*;
use crate::github::GithubClient;
use serde::Deserialize;
use tempfile::TempDir;

// ---------------------------------------------------------------------------
// read_etag
// ---------------------------------------------------------------------------

#[test]
fn read_etag_returns_none_for_missing_file() {
    let tmp = TempDir::new().unwrap();
    assert!(read_etag(&tmp.path().join("does-not-exist.etag")).is_none());
}

#[test]
fn read_etag_returns_none_for_empty_file() {
    let tmp = TempDir::new().unwrap();
    let path = tmp.path().join("manifest.etag");
    std::fs::write(&path, "").unwrap();
    assert!(read_etag(&path).is_none());
}

#[test]
fn read_etag_returns_none_for_whitespace_only_file() {
    let tmp = TempDir::new().unwrap();
    let path = tmp.path().join("manifest.etag");
    std::fs::write(&path, "   \n\t  ").unwrap();
    assert!(read_etag(&path).is_none());
}

#[test]
fn read_etag_trims_whitespace() {
    let tmp = TempDir::new().unwrap();
    let path = tmp.path().join("manifest.etag");
    std::fs::write(&path, "  \"W/abc\"  \n").unwrap();
    assert_eq!(read_etag(&path).unwrap(), "\"W/abc\"");
}

// ---------------------------------------------------------------------------
// try_pages: cold cache, warm cache 200, warm cache 304 (task 2.4)
// ---------------------------------------------------------------------------
//
// Uses a minimal test-only manifest type (`TestManifest`) so the helper
// tests don't depend on the YAML or notification DTOs. This keeps the
// suite scoped to the Pages-fetch plumbing: conditional-GET headers,
// cache persistence, 304 cached-body reuse, and error classification.

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
struct TestManifest {
    id: String,
}

fn parse_test(bytes: &[u8]) -> Result<TestManifest> {
    serde_json::from_slice::<TestManifest>(bytes).map_err(UpdateError::JsonError)
}

fn validate_test_accept_all(_m: &TestManifest) -> Result<()> {
    Ok(())
}

fn validate_test_require_id_abc(m: &TestManifest) -> Result<()> {
    if m.id != "abc" {
        return Err(UpdateError::ManifestInvalid {
            reason: format!("unexpected id `{}`", m.id),
        });
    }
    Ok(())
}

fn tokenless_client(base_url: &str) -> GithubClient {
    GithubClient::with_base_url("owner", "repo", base_url, None).unwrap()
}

#[tokio::test(flavor = "multi_thread")]
async fn try_pages_cold_cache_persists_body_and_etag() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/test-channel/manifest-latest.json", server.url());
    let body = r#"{"id": "abc"}"#;

    let mock = server
        .mock("GET", "/test-channel/manifest-latest.json")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_header("etag", "\"W/abc\"")
        .with_body(body)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let manifest = try_pages(
        &client,
        &pages_url,
        Some(cache_dir.path()),
        parse_test,
        validate_test_accept_all,
    )
    .await
    .expect("cold fetch succeeds");

    assert_eq!(manifest.id, "abc");
    mock.assert_async().await;
    // Cache files are written with the shared filenames.
    let cached_body =
        std::fs::read_to_string(cache_dir.path().join(CACHED_MANIFEST_FILENAME)).unwrap();
    assert!(cached_body.contains("\"id\""));
    let cached_etag = std::fs::read_to_string(cache_dir.path().join(ETAG_FILENAME)).unwrap();
    assert_eq!(cached_etag, "\"W/abc\"");
}

#[tokio::test(flavor = "multi_thread")]
async fn try_pages_warm_cache_304_reuses_cached_body() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/test-channel/manifest-latest.json", server.url());

    // Pre-populate the cache as if a prior 200 had run.
    let cache_dir = TempDir::new().unwrap();
    std::fs::write(
        cache_dir.path().join(CACHED_MANIFEST_FILENAME),
        r#"{"id": "cached"}"#,
    )
    .unwrap();
    std::fs::write(cache_dir.path().join(ETAG_FILENAME), b"\"W/prior\"").unwrap();

    let mock = server
        .mock("GET", "/test-channel/manifest-latest.json")
        .match_header("if-none-match", "\"W/prior\"")
        .with_status(304)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let manifest = try_pages(
        &client,
        &pages_url,
        Some(cache_dir.path()),
        parse_test,
        validate_test_accept_all,
    )
    .await
    .expect("304 path returns cached body");

    assert_eq!(
        manifest.id, "cached",
        "304 must reuse the pre-populated body"
    );
    mock.assert_async().await;
}

#[tokio::test(flavor = "multi_thread")]
async fn try_pages_warm_cache_200_overwrites_cached_body_and_etag() {
    // Server replies 200 with a new body + new ETag. Tests that the
    // helper (a) does send If-None-Match with the existing ETag and
    // (b) updates cache files atomically on the new 200 response.
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/test-channel/manifest-latest.json", server.url());

    let cache_dir = TempDir::new().unwrap();
    std::fs::write(
        cache_dir.path().join(CACHED_MANIFEST_FILENAME),
        r#"{"id": "old"}"#,
    )
    .unwrap();
    std::fs::write(cache_dir.path().join(ETAG_FILENAME), b"\"W/old\"").unwrap();

    let mock = server
        .mock("GET", "/test-channel/manifest-latest.json")
        .match_header("if-none-match", "\"W/old\"")
        .with_status(200)
        .with_header("etag", "\"W/new\"")
        .with_body(r#"{"id": "new"}"#)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let manifest = try_pages(
        &client,
        &pages_url,
        Some(cache_dir.path()),
        parse_test,
        validate_test_accept_all,
    )
    .await
    .expect("200 refresh succeeds");

    assert_eq!(manifest.id, "new");
    mock.assert_async().await;

    let cached_body =
        std::fs::read_to_string(cache_dir.path().join(CACHED_MANIFEST_FILENAME)).unwrap();
    assert!(
        cached_body.contains("\"new\""),
        "cache body must be refreshed"
    );
    let cached_etag = std::fs::read_to_string(cache_dir.path().join(ETAG_FILENAME)).unwrap();
    assert_eq!(cached_etag, "\"W/new\"", "etag must be refreshed");
}

#[tokio::test(flavor = "multi_thread")]
async fn try_pages_none_cache_dir_does_not_write_files() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/test-channel/manifest-latest.json", server.url());

    let mock = server
        .mock("GET", "/test-channel/manifest-latest.json")
        .with_status(200)
        .with_header("etag", "\"W/abc\"")
        .with_body(r#"{"id": "abc"}"#)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let manifest = try_pages(
        &client,
        &pages_url,
        None,
        parse_test,
        validate_test_accept_all,
    )
    .await
    .expect("fetch succeeds without cache");

    assert_eq!(manifest.id, "abc");
    mock.assert_async().await;
    // No cache dir means we never write any files — nothing to assert
    // beyond "did not panic, did not return Err".
}

#[tokio::test(flavor = "multi_thread")]
async fn try_pages_5xx_classifies_as_transport_error() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/test-channel/manifest-latest.json", server.url());

    let mock = server
        .mock("GET", "/test-channel/manifest-latest.json")
        .with_status(500)
        .with_body("boom")
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let err = try_pages(
        &client,
        &pages_url,
        Some(cache_dir.path()),
        parse_test,
        validate_test_accept_all,
    )
    .await
    .expect_err("5xx must error");

    assert!(
        matches!(err, PagesError::Transport(_)),
        "5xx must classify as Transport (retryable to Releases)"
    );
    mock.assert_async().await;
}

#[tokio::test(flavor = "multi_thread")]
async fn try_pages_valid_json_failing_validator_returns_invalid_error() {
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/test-channel/manifest-latest.json", server.url());

    let mock = server
        .mock("GET", "/test-channel/manifest-latest.json")
        .with_status(200)
        .with_header("etag", "\"W/abc\"")
        .with_body(r#"{"id": "wrong"}"#)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    let client = tokenless_client(&server.url());
    let err = try_pages(
        &client,
        &pages_url,
        Some(cache_dir.path()),
        parse_test,
        validate_test_require_id_abc,
    )
    .await
    .expect_err("failing validator must error");

    assert!(
        matches!(err, PagesError::Invalid(_)),
        "ManifestInvalid must classify as Invalid (retryable to Releases)"
    );
    mock.assert_async().await;

    // Crucially: validator ran BEFORE cache write, so no cache files landed.
    assert!(
        !cache_dir.path().join(CACHED_MANIFEST_FILENAME).exists(),
        "failing validator must prevent cache write"
    );
    assert!(!cache_dir.path().join(ETAG_FILENAME).exists());
}

#[tokio::test(flavor = "multi_thread")]
async fn try_pages_body_write_failure_clears_stale_etag_and_does_not_persist_new_one() {
    // Regression: Codex adversarial-review finding on non-atomic cache
    // persistence. On a 200 response where the body write fails, the
    // helper MUST NOT leave the new ETag on disk and MUST clear any
    // stale ETag there — otherwise a subsequent request would carry
    // `If-None-Match: <new>` (or `<stale>`) and a `304` would silently
    // reuse bytes we never persisted.
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/test-channel/manifest-latest.json", server.url());

    let mock = server
        .mock("GET", "/test-channel/manifest-latest.json")
        .with_status(200)
        .with_header("etag", "\"W/new\"")
        .with_body(r#"{"id": "new"}"#)
        .create_async()
        .await;

    let cache_dir = TempDir::new().unwrap();
    // Pre-existing stale ETag as if a prior successful fetch had run.
    std::fs::write(cache_dir.path().join(ETAG_FILENAME), b"\"W/stale\"").unwrap();
    // Force body-write failure cross-platform: create a directory at
    // the body path so the temp-file + rename step cannot install a
    // regular file over it (Windows: access denied; POSIX: EISDIR /
    // ENOTEMPTY on rename).
    std::fs::create_dir_all(cache_dir.path().join(CACHED_MANIFEST_FILENAME)).unwrap();

    let client = tokenless_client(&server.url());
    let manifest = try_pages(
        &client,
        &pages_url,
        Some(cache_dir.path()),
        parse_test,
        validate_test_accept_all,
    )
    .await
    .expect("in-memory classification must succeed even when the cache write fails");

    assert_eq!(manifest.id, "new");
    mock.assert_async().await;

    // Stale ETag must be cleared so a future If-None-Match cannot take
    // a 304 against bytes we never persisted.
    assert!(
        !cache_dir.path().join(ETAG_FILENAME).exists(),
        "body-write failure must clear any stale ETag on disk",
    );
    // Any `.tmp.<pid>.<counter>.<nanos>` orphan must also be cleaned
    // up so a retry starts clean. The filename is uniquely generated
    // per write attempt (see `unique_tmp_sibling`), so we scan the
    // cache dir for anything starting with the cached-manifest prefix
    // + `.tmp.` rather than asserting on a single fixed name.
    let orphans: Vec<_> = std::fs::read_dir(cache_dir.path())
        .unwrap()
        .filter_map(|entry| entry.ok())
        .filter(|entry| {
            entry
                .file_name()
                .to_str()
                .is_some_and(|n| n.starts_with(&format!("{CACHED_MANIFEST_FILENAME}.tmp.")))
        })
        .map(|entry| entry.file_name().to_string_lossy().into_owned())
        .collect();
    assert!(
        orphans.is_empty(),
        "orphan temp body must be removed after a failed rename, found: {orphans:?}",
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn write_body_atomically_survives_concurrent_writers_to_same_target() {
    // Regression for Codex adversarial-review HIGH finding: two
    // concurrent writers against the same target MUST NOT end with a
    // mixed/truncated body. Before the fix, both writers shared a
    // single `<target>.tmp` sibling, so writer A's `std::fs::write`
    // could clobber writer B's in-flight temp bytes and B's `rename`
    // would publish A's bytes. With per-call unique temp names, each
    // writer owns its own temp path; the `rename` race is resolved by
    // the OS atomically, so the final file matches exactly one of the
    // input payloads — never a partial mix — and no orphan temps are
    // left behind.
    let tmp = TempDir::new().unwrap();
    let target = tmp.path().join(CACHED_MANIFEST_FILENAME);

    let payload_a = vec![b'A'; 4096];
    let payload_b = vec![b'B'; 4096];

    // Hand off to blocking threads so the two calls actually race
    // under the multi-thread runtime rather than serialising on a
    // single-thread executor.
    let target_a = target.clone();
    let bytes_a = payload_a.clone();
    let target_b = target.clone();
    let bytes_b = payload_b.clone();
    let (r_a, r_b) = tokio::join!(
        tokio::task::spawn_blocking(move || write_body_atomically(&target_a, &bytes_a)),
        tokio::task::spawn_blocking(move || write_body_atomically(&target_b, &bytes_b)),
    );
    r_a.unwrap().expect("writer A must succeed");
    r_b.unwrap().expect("writer B must succeed");

    // The final body MUST be exactly one of the two payloads — not a
    // mix of bytes, not a truncated write.
    let persisted = std::fs::read(&target).expect("target must exist after concurrent writes");
    assert!(
        persisted == payload_a || persisted == payload_b,
        "final body must equal one of the input payloads, got {} bytes",
        persisted.len(),
    );

    // No orphan temps should remain from either writer.
    let orphans: Vec<_> = std::fs::read_dir(tmp.path())
        .unwrap()
        .filter_map(|entry| entry.ok())
        .filter(|entry| {
            entry
                .file_name()
                .to_str()
                .is_some_and(|n| n.starts_with(&format!("{CACHED_MANIFEST_FILENAME}.tmp.")))
        })
        .map(|entry| entry.file_name().to_string_lossy().into_owned())
        .collect();
    assert!(
        orphans.is_empty(),
        "concurrent writers must leave no orphan temp files, found: {orphans:?}",
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn try_pages_304_with_corrupt_cached_body_returns_invalid_error() {
    // 304 requires a working cache body. A corrupt cached body classifies
    // as Invalid so the caller falls back to the Releases API rather than
    // silently returning bad data.
    let mut server = mockito::Server::new_async().await;
    let pages_url = format!("{}/test-channel/manifest-latest.json", server.url());

    let cache_dir = TempDir::new().unwrap();
    std::fs::write(cache_dir.path().join(CACHED_MANIFEST_FILENAME), b"not-json").unwrap();
    std::fs::write(cache_dir.path().join(ETAG_FILENAME), b"\"W/x\"").unwrap();

    let mock = server
        .mock("GET", "/test-channel/manifest-latest.json")
        .match_header("if-none-match", "\"W/x\"")
        .with_status(304)
        .create_async()
        .await;

    let client = tokenless_client(&server.url());
    let err = try_pages(
        &client,
        &pages_url,
        Some(cache_dir.path()),
        parse_test,
        validate_test_accept_all,
    )
    .await
    .expect_err("corrupt cached body on 304 must error");

    assert!(
        matches!(err, PagesError::Invalid(_)),
        "JsonError from cached body must classify as Invalid"
    );
    mock.assert_async().await;
}
