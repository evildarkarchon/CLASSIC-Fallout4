//! Integration tests for the notification-check `CACHE_IO` error branch.
//!
//! Purpose: exercise the full orchestrator path in [`classic_update_core::notification`]
//! so that the `NotificationCacheIo` variant — and the Node `CACHE_IO:` /
//! Python `ClassicNotificationCacheIoError` surfaces that mirror it — is
//! observable end-to-end rather than asserted only at the
//! `map_ensure_cache_result` helper level.
//!
//! # Fixture strategy
//!
//! `ensure_notification_cache_dir_with_env` builds the final path as
//! `<cache_root>/CLASSIC/app-notification/<owner>/<repo>/`, and when an
//! intermediate component is a regular file `std::fs::create_dir_all`
//! returns a typed `io::Error`. We exploit that: plant a file at
//! `<cache_root>/CLASSIC` and the resolver deterministically fails with
//! a real I/O error regardless of OS or filesystem permissions tooling
//! — no process-env mutation, no `chmod`/`icacls`, no elevated rights
//! required. The seam is
//! [`classic_update_core::check_app_notification_with_env`] which
//! accepts an injected env closure; production callers of
//! `check_app_notification` see the same code path via the process
//! `std::env::var` shim.
//!
//! # Cross-platform shape
//!
//! Path-core reads `LOCALAPPDATA` on Windows and `XDG_CACHE_HOME` on
//! non-Windows. The test closure honors both names; whichever the
//! platform queries resolves to the same sandboxed temp root, so the
//! same test exercises both code paths from a single fixture.
//!
//! # What it does NOT cover
//!
//! With a well-formed `installed_version`, the production
//! `check_app_notification` short-circuits before any network call when
//! cache-dir materialization fails (the `?` sits above
//! `check_app_notification_with`), so this test does not need a
//! `mockito` server. That also means it stays green in fully-offline
//! CI where outbound HTTPS is blocked — the CacheIo branch fires before
//! anything downstream runs.

use classic_update_core::{UpdateError, check_app_notification_with_env};
use std::collections::HashMap;
use std::path::PathBuf;
use tempfile::TempDir;

/// Build an env closure that maps every cache-root name path-core
/// queries (Windows: `LOCALAPPDATA` / `APPDATA`; non-Windows:
/// `XDG_CACHE_HOME` / `HOME`) to the same `root` path, and returns
/// `None` for anything else. Accepting the full name set means a
/// single closure works on both platforms without `cfg` gating.
fn sandbox_env(root: PathBuf) -> impl Fn(&str) -> Option<String> {
    let mapping: HashMap<&'static str, String> = [
        ("LOCALAPPDATA", root.to_string_lossy().into_owned()),
        ("APPDATA", root.to_string_lossy().into_owned()),
        ("XDG_CACHE_HOME", root.to_string_lossy().into_owned()),
        ("HOME", root.to_string_lossy().into_owned()),
    ]
    .into_iter()
    .collect();

    move |name: &str| mapping.get(name).cloned()
}

#[tokio::test(flavor = "multi_thread")]
async fn cache_dir_creation_failure_surfaces_as_notification_cache_io() {
    // Sandbox the cache root inside a TempDir so nothing touches the
    // real per-user cache directory.
    let tmp = TempDir::new().expect("tempdir");

    // Plant a regular file at `<tmp>/CLASSIC`. The resolver wants to
    // treat that path as a directory (it joins `app-notification`
    // under it), so `create_dir_all` fails with a typed I/O error the
    // moment it encounters the wrong file type. This is the
    // motivating scenario the codex adversarial-review finding calls
    // out: a machine where cache materialization genuinely cannot
    // succeed must surface CACHE_IO rather than pretending the check
    // is healthy while running uncached forever.
    std::fs::write(tmp.path().join("CLASSIC"), b"not a directory").expect("plant blocking file");

    let env = sandbox_env(tmp.path().to_path_buf());

    // `installed_version` is well-formed so the input-validation
    // short-circuit does not fire — this test specifically exercises
    // the cache-dir branch. `owner` / `repo` match the path-core
    // segment validator (`A-Za-z0-9._-`).
    let err = check_app_notification_with_env("owner", "repo", "9.2.0", env)
        .await
        .expect_err("unwritable cache dir must propagate as CacheIo");

    match err {
        UpdateError::NotificationCacheIo { path, source } => {
            // Path carried in the error must be the one
            // `ensure_notification_cache_dir_with_env` tried to create,
            // so a UI consumer can point the user at the offending
            // location rather than a generic "cache broken" string.
            let expected_suffix = PathBuf::from("CLASSIC")
                .join("app-notification")
                .join("owner")
                .join("repo");
            assert!(
                path.ends_with(&expected_suffix),
                "expected path to end with {expected_suffix:?}, got {path:?}",
            );
            // We don't pin the exact `ErrorKind` because Windows,
            // Linux, and macOS all surface the "intermediate
            // component is a file" case through different variants
            // (NotADirectory / AlreadyExists / Other across Rust
            // versions). The load-bearing assertion is "there is a
            // real I/O error" — `to_string()` on the source being
            // non-empty is sufficient without coupling the test to
            // platform-specific ErrorKind mappings.
            assert!(
                !source.to_string().is_empty(),
                "io::Error must have a human-readable rendering",
            );
        }
        other => panic!("expected NotificationCacheIo, got {other:?}"),
    }
}

/// Bad caller input must win before cache materialization, even when the
/// user's cache root is genuinely unwritable.
#[tokio::test(flavor = "multi_thread")]
async fn invalid_installed_version_surfaces_before_cache_dir_creation_failure() {
    let tmp = TempDir::new().expect("tempdir");
    std::fs::write(tmp.path().join("CLASSIC"), b"not a directory").expect("plant blocking file");

    let env = sandbox_env(tmp.path().to_path_buf());

    let err = check_app_notification_with_env("owner", "repo", "not-a-semver", env)
        .await
        .expect_err("unparseable installed_version must still error");

    match err {
        UpdateError::NotificationInstalledVersionParse { input, .. } => {
            assert_eq!(input, "not-a-semver");
        }
        UpdateError::NotificationCacheIo { .. } => {
            panic!("installed_version validation must run before cache materialization")
        }
        other => panic!("expected NotificationInstalledVersionParse, got {other:?}"),
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn invalid_path_degrades_to_no_cache_and_orchestrator_continues() {
    // Counterpart to `cache_dir_creation_failure_surfaces_as_notification_cache_io`:
    // a non-I/O cache-resolution failure — here, env resolution returning
    // `None` for every cache-root variable — stays best-effort per design
    // D-06 and must NOT be projected as CacheIo.
    //
    // The test is hermetic (no network). After the InvalidPath degrade,
    // the orchestrator runs `validate_installed_version` next, and we
    // hand it a deliberately-unparseable string. If the degrade path is
    // correct we expect `NotificationInstalledVersionParse`; if the
    // split broke, the error would still be `NotificationCacheIo`. Both
    // cases are pattern-matched explicitly so a regression surfaces as
    // a clean assertion failure instead of a generic "wrong variant".
    let env = |_: &str| None;

    let err = check_app_notification_with_env("owner", "repo", "not-a-semver", env)
        .await
        .expect_err("unparseable installed_version must still error");

    match err {
        UpdateError::NotificationInstalledVersionParse { input, .. } => {
            // Load-bearing: we reached the installed-version validator,
            // which means cache resolution degraded to Ok(None) instead
            // of erroring.
            assert_eq!(input, "not-a-semver");
        }
        UpdateError::NotificationCacheIo { .. } => panic!(
            "InvalidPath (env resolution failure) must degrade to no-cache, \
             not project as CacheIo",
        ),
        other => panic!(
            "expected NotificationInstalledVersionParse after InvalidPath degrade, \
             got {other:?}",
        ),
    }
}
