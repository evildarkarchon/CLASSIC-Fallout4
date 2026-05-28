use super::*;
use crate::yaml_cache::yaml_cache_dir_with_env;
use std::collections::HashMap;

const TEST_OWNER: &str = "evildarkarchon";
const TEST_REPO: &str = "CLASSIC-Fallout4";

fn env_from_map(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
    // The closure captures an owned HashMap via `move`, so it does not
    // borrow from `pairs`. No lifetime parameter is needed.
    let map: HashMap<String, String> = pairs
        .iter()
        .map(|(k, v)| ((*k).to_string(), (*v).to_string()))
        .collect();
    move |key: &str| map.get(key).cloned()
}

// ---------------------------------------------------------------------------
// Resolution — platform-specific env var precedence
// ---------------------------------------------------------------------------

#[cfg(target_os = "windows")]
#[test]
fn windows_prefers_localappdata_over_appdata() {
    let env = env_from_map(&[
        ("LOCALAPPDATA", "C:\\Users\\me\\AppData\\Local"),
        ("APPDATA", "C:\\Users\\me\\AppData\\Roaming"),
    ]);
    let dir = notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, env).unwrap();
    let dir_str = dir.to_string_lossy();
    assert!(
        dir_str.contains("AppData\\Local\\CLASSIC\\app-notification"),
        "LOCALAPPDATA must win over APPDATA, got {dir_str}",
    );
}

#[cfg(target_os = "windows")]
#[test]
fn windows_falls_back_to_appdata_when_localappdata_missing() {
    let env = env_from_map(&[("APPDATA", "C:\\Users\\me\\AppData\\Roaming")]);
    let dir = notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, env).unwrap();
    assert!(
        dir.ends_with(format!(
            "CLASSIC\\app-notification\\{TEST_OWNER}\\{TEST_REPO}"
        )),
        "expected owner/repo-namespaced path, got {}",
        dir.display(),
    );
}

#[cfg(target_os = "windows")]
#[test]
fn windows_errors_when_both_env_vars_missing() {
    let env = env_from_map(&[]);
    let err = notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, env).unwrap_err();
    assert!(
        matches!(err, PathError::InvalidPath(_)),
        "missing LOCALAPPDATA+APPDATA must yield InvalidPath, got {err:?}"
    );
}

#[cfg(not(target_os = "windows"))]
#[test]
fn unix_prefers_xdg_cache_home_over_home() {
    let env = env_from_map(&[
        ("XDG_CACHE_HOME", "/var/cache/custom"),
        ("HOME", "/home/me"),
    ]);
    let dir = notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, env).unwrap();
    assert!(dir.starts_with("/var/cache/custom/CLASSIC/app-notification"));
    assert!(dir.ends_with(format!("{TEST_OWNER}/{TEST_REPO}")));
}

#[cfg(not(target_os = "windows"))]
#[test]
fn unix_falls_back_to_home_dot_cache_when_xdg_missing() {
    let env = env_from_map(&[("HOME", "/home/me")]);
    let dir = notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, env).unwrap();
    assert_eq!(
        dir,
        std::path::PathBuf::from(format!(
            "/home/me/.cache/CLASSIC/app-notification/{TEST_OWNER}/{TEST_REPO}"
        ))
    );
}

#[cfg(not(target_os = "windows"))]
#[test]
fn unix_errors_when_both_env_vars_missing() {
    let env = env_from_map(&[]);
    let err = notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, env).unwrap_err();
    assert!(matches!(err, PathError::InvalidPath(_)));
}

// Empty-string env handling lives in the `process_env_lookup` helper
// shared with yaml_cache (filters `Ok("")` to `None`). The `*_with_env`
// closure seam does not apply that filter — tests that want to exercise
// it should drive `process_env_lookup` directly, as yaml_cache_tests.rs
// does. Re-running that coverage here would duplicate without adding
// notification-specific value.

// ---------------------------------------------------------------------------
// Disjoint from yaml-cache (design D-06)
// ---------------------------------------------------------------------------

#[test]
fn notification_cache_path_is_disjoint_from_yaml_cache() {
    // Same env drives both resolvers; the per-channel sub-directory must
    // differ so a cleanup of one cache does not nuke the other.
    #[cfg(target_os = "windows")]
    let env_pairs = [("LOCALAPPDATA", "C:\\Users\\me\\AppData\\Local")];
    #[cfg(not(target_os = "windows"))]
    let env_pairs = [("HOME", "/home/me")];

    let notif_env = env_from_map(&env_pairs);
    let yaml_env = env_from_map(&env_pairs);

    let notif = notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, notif_env).unwrap();
    let yaml = yaml_cache_dir_with_env(yaml_env).unwrap();

    assert_ne!(
        notif, yaml,
        "app-notification and yaml-cache paths must differ"
    );
    let notif_str = notif.to_string_lossy().to_string();
    let yaml_str = yaml.to_string_lossy().to_string();
    assert!(
        notif_str.contains("app-notification"),
        "notification path must contain 'app-notification', got {notif_str}"
    );
    assert!(
        yaml_str.contains("yaml-cache"),
        "yaml-cache path must contain 'yaml-cache', got {yaml_str}"
    );
}

// ---------------------------------------------------------------------------
// Owner/repo namespacing — the codex adversarial-review fix
// ---------------------------------------------------------------------------

#[test]
fn notification_cache_namespaces_by_owner_repo() {
    // Two repos under the same env must yield disjoint cache paths so
    // repo A cannot seed repo B's manifest body / ETag / fallback marker.
    #[cfg(target_os = "windows")]
    let env_pairs = [("LOCALAPPDATA", "C:\\Users\\me\\AppData\\Local")];
    #[cfg(not(target_os = "windows"))]
    let env_pairs = [("HOME", "/home/me")];

    let env_a = env_from_map(&env_pairs);
    let env_b = env_from_map(&env_pairs);
    let env_c = env_from_map(&env_pairs);

    let dir_a = notification_cache_dir_with_env(TEST_OWNER, "repo-a", env_a).unwrap();
    let dir_b = notification_cache_dir_with_env(TEST_OWNER, "repo-b", env_b).unwrap();
    let dir_c = notification_cache_dir_with_env("other-owner", "repo-a", env_c).unwrap();

    assert_ne!(dir_a, dir_b, "different repos must produce different paths");
    assert_ne!(
        dir_a, dir_c,
        "different owners must produce different paths"
    );
    assert_ne!(dir_b, dir_c);
}

#[test]
fn notification_cache_path_contains_owner_and_repo_segments() {
    #[cfg(target_os = "windows")]
    let env_pairs = [("LOCALAPPDATA", "C:\\Users\\me\\AppData\\Local")];
    #[cfg(not(target_os = "windows"))]
    let env_pairs = [("HOME", "/home/me")];

    let env = env_from_map(&env_pairs);
    let dir = notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, env).unwrap();
    let dir_str = dir.to_string_lossy();
    assert!(
        dir_str.contains(TEST_OWNER),
        "path must contain owner segment, got {dir_str}"
    );
    assert!(
        dir_str.contains(TEST_REPO),
        "path must contain repo segment, got {dir_str}"
    );
}

// ---------------------------------------------------------------------------
// Owner/repo input validation
// ---------------------------------------------------------------------------

fn invalid_owner_err(owner: &str, repo: &str) -> PathError {
    let env = env_from_map(&[("LOCALAPPDATA", "C:\\tmp"), ("HOME", "/tmp")]);
    notification_cache_dir_with_env(owner, repo, env).unwrap_err()
}

#[test]
fn rejects_empty_owner() {
    let err = invalid_owner_err("", TEST_REPO);
    let PathError::InvalidPath(msg) = err else {
        panic!("expected InvalidPath, got {err:?}");
    };
    assert!(
        msg.contains("owner"),
        "message should name the owner field: {msg}"
    );
    assert!(msg.contains("empty"));
}

#[test]
fn rejects_empty_repo() {
    let err = invalid_owner_err(TEST_OWNER, "");
    let PathError::InvalidPath(msg) = err else {
        panic!("expected InvalidPath, got {err:?}");
    };
    assert!(
        msg.contains("repo"),
        "message should name the repo field: {msg}"
    );
}

#[test]
fn rejects_owner_with_path_separator() {
    // `/` and `\` in either segment would let a malicious upstream caller
    // climb out of the namespaced subtree.
    for poisoned in ["bad/owner", "bad\\owner", "bad:owner", "bad\0owner"] {
        let err = invalid_owner_err(poisoned, TEST_REPO);
        assert!(
            matches!(err, PathError::InvalidPath(_)),
            "owner `{poisoned}` should be rejected, got {err:?}"
        );
    }
}

#[test]
fn rejects_repo_with_path_separator() {
    for poisoned in ["bad/repo", "bad\\repo", "bad:repo", "bad\0repo"] {
        let err = invalid_owner_err(TEST_OWNER, poisoned);
        assert!(
            matches!(err, PathError::InvalidPath(_)),
            "repo `{poisoned}` should be rejected, got {err:?}"
        );
    }
}

#[test]
fn rejects_traversal_segments() {
    for traversal in [".", ".."] {
        assert!(matches!(
            invalid_owner_err(traversal, TEST_REPO),
            PathError::InvalidPath(_)
        ));
        assert!(matches!(
            invalid_owner_err(TEST_OWNER, traversal),
            PathError::InvalidPath(_)
        ));
    }
}

#[test]
fn rejects_segment_with_whitespace() {
    // GitHub disallows spaces in owner/repo names — surface a clean
    // rejection rather than letting a quoted path component land on disk.
    let err = invalid_owner_err("bad owner", TEST_REPO);
    assert!(matches!(err, PathError::InvalidPath(_)));
}

#[test]
fn rejects_segment_exceeding_length_cap() {
    let too_long = "a".repeat(MAX_SEGMENT_LEN + 1);
    let err = invalid_owner_err(&too_long, TEST_REPO);
    let PathError::InvalidPath(msg) = err else {
        panic!("expected InvalidPath, got {err:?}");
    };
    assert!(
        msg.contains("exceeds"),
        "message should explain the cap: {msg}"
    );
}

#[test]
fn accepts_segment_at_length_cap() {
    let at_limit = "a".repeat(MAX_SEGMENT_LEN);
    #[cfg(target_os = "windows")]
    let env_pairs = [("LOCALAPPDATA", "C:\\tmp")];
    #[cfg(not(target_os = "windows"))]
    let env_pairs = [("HOME", "/tmp")];
    let env = env_from_map(&env_pairs);
    notification_cache_dir_with_env(&at_limit, TEST_REPO, env).unwrap();
}

#[test]
fn accepts_typical_github_identifiers() {
    // Sample identifiers that exercise the full allowed alphabet (digits,
    // hyphens, underscores, dots) so a future tightening of the regex
    // surfaces in CI rather than at first runtime use.
    #[cfg(target_os = "windows")]
    let env_pairs_template = [("LOCALAPPDATA", "C:\\tmp")];
    #[cfg(not(target_os = "windows"))]
    let env_pairs_template = [("HOME", "/tmp")];

    for (owner, repo) in [
        ("evildarkarchon", "CLASSIC-Fallout4"),
        ("Owner-1", "repo_2.test"),
        ("a", "b"),
        ("0123456789", "repo.with.dots"),
    ] {
        let env = env_from_map(&env_pairs_template);
        notification_cache_dir_with_env(owner, repo, env)
            .unwrap_or_else(|e| panic!("expected `{owner}/{repo}` to validate, got {e:?}"));
    }
}

// ---------------------------------------------------------------------------
// ensure_notification_cache_dir creates the namespaced directory
// ---------------------------------------------------------------------------

#[test]
fn ensure_notification_cache_dir_with_env_creates_namespaced_directory() {
    let tmp = tempfile::TempDir::new().unwrap();
    let root = tmp.path().to_string_lossy().to_string();
    #[cfg(target_os = "windows")]
    let env_pairs = [("LOCALAPPDATA", root.as_str())];
    #[cfg(not(target_os = "windows"))]
    let env_pairs = [("XDG_CACHE_HOME", root.as_str())];
    let env = env_from_map(&env_pairs);

    let dir = ensure_notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, env).unwrap();
    assert!(dir.exists(), "ensure_* must create the directory");
    assert!(dir.is_dir());
    assert!(
        dir.ends_with(format!("{TEST_OWNER}/{TEST_REPO}"))
            || dir.ends_with(format!("{TEST_OWNER}\\{TEST_REPO}")),
        "ensure_* must create the namespaced subtree, got {}",
        dir.display(),
    );

    // Idempotent — calling it again must not error.
    let env2 = env_from_map(&env_pairs);
    let dir2 = ensure_notification_cache_dir_with_env(TEST_OWNER, TEST_REPO, env2).unwrap();
    assert_eq!(dir, dir2);
}

#[test]
fn ensure_propagates_owner_validation_errors() {
    let tmp = tempfile::TempDir::new().unwrap();
    let root = tmp.path().to_string_lossy().to_string();
    #[cfg(target_os = "windows")]
    let env_pairs = [("LOCALAPPDATA", root.as_str())];
    #[cfg(not(target_os = "windows"))]
    let env_pairs = [("XDG_CACHE_HOME", root.as_str())];
    let env = env_from_map(&env_pairs);

    let err = ensure_notification_cache_dir_with_env("bad/owner", TEST_REPO, env).unwrap_err();
    assert!(matches!(err, PathError::InvalidPath(_)));
}
