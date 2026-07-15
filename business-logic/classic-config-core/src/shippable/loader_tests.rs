use super::*;
use classic_path_core::ensure_yaml_cache_dir_with_env;
use classic_settings_core::clear_global_yaml_cache;
use serial_test::serial;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tempfile::tempdir;

/// Build an env-lookup closure backed by a static map, so tests can feed
/// the `_with_env` helpers without touching process env.
fn env_map(entries: &[(&str, String)]) -> impl Fn(&str) -> Option<String> + Clone + use<> {
    let map: HashMap<String, String> = entries
        .iter()
        .map(|(k, v)| ((*k).to_string(), v.clone()))
        .collect();
    move |name| map.get(name).cloned()
}

/// Resolve the cache dir for the same env the test just mocked. Not a
/// re-export from `classic-path-core` because production code doesn't
/// need it, only the tests here do.
fn resolve_cache_dir<F: Fn(&str) -> Option<String>>(env: F) -> PathBuf {
    ensure_yaml_cache_dir_with_env(env).unwrap()
}

fn write(path: &Path, contents: &str) {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).unwrap();
    }
    std::fs::write(path, contents).unwrap();
}

/// Thin wrapper over the public [`load_shippable_yaml_with_env`] so the
/// test call sites stay terse. Kept here so any breaking refactor of the
/// env-injection surface shows up as a compile error in one place.
async fn load_with_env<F>(
    file: ShippableFile,
    compat: &SchemaCompat,
    env: F,
) -> Result<LoadedShippable, YamlLoadError>
where
    F: Fn(&str) -> Option<String> + Clone,
{
    load_shippable_yaml_with_env(file, compat, env).await
}

// Legacy pre-2.0 shape under test: the `CLASSIC v` decoration was canonical
// for schema_version 1.x; these fixtures deliberately retain it so the
// schema-gate tests keep covering the historical shape that older clients
// wrote and read.
fn v1_0_payload() -> &'static str {
    "schema_version: \"1.0\"\nCLASSIC_Info:\n  version: CLASSIC v9.0.0\n"
}

fn v1_2_payload() -> &'static str {
    "schema_version: \"1.2\"\nCLASSIC_Info:\n  version: CLASSIC v9.1.0\n"
}

// Post-change shape: schema_version 2.0 drops the `CLASSIC v` decoration
// and stores a bare SemVer per `openspec/specs/yaml-app-version-field/spec.md`.
// Uses a valid release SemVer because the loader now enforces strict
// `v?MAJOR.MINOR.PATCH` shape at post-load time (no prerelease suffix, no
// build metadata, no legacy `CLASSIC ` decoration); a made-up token like
// the previous `vFuture` would surface as `VersionInvalid`.
fn v2_0_payload() -> &'static str {
    "schema_version: \"2.0\"\nCLASSIC_Info:\n  version: v9.1.0\n"
}

fn windows_env(tmp: &Path) -> Vec<(&'static str, String)> {
    #[cfg(target_os = "windows")]
    {
        vec![("LOCALAPPDATA", tmp.to_string_lossy().into_owned())]
    }
    #[cfg(not(target_os = "windows"))]
    {
        vec![("XDG_CACHE_HOME", tmp.to_string_lossy().into_owned())]
    }
}

#[test]
fn fallout4_vr_uses_the_shared_fallout4_shippable_file() {
    let file = ShippableFile::game("Fallout4VR");

    assert_eq!(file.file_name, "CLASSIC Fallout4.yaml");
    assert_eq!(
        file.bundled_path,
        PathBuf::from("CLASSIC Data/databases/CLASSIC Fallout4.yaml")
    );
}

#[tokio::test]
#[serial]
async fn cache_compatible_wins_over_bundled() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    write(&cache_copy, v1_2_payload());

    // Bundled copy in an isolated path so we control its contents.
    let bundled_dir = tempdir().unwrap();
    let bundled_path = bundled_dir.path().join("CLASSIC Main.yaml");
    write(&bundled_path, v1_0_payload());

    let file = ShippableFile {
        file_name: "CLASSIC Main.yaml".into(),
        bundled_path: bundled_path.clone(),
    };
    let compat = SchemaCompat::new(1, 0);

    let loaded = load_with_env(file, &compat, env).await.unwrap();
    assert!(matches!(loaded.source, LoadSource::Cache(_)));
    assert_eq!(loaded.schema_version, SchemaVersion::new(1, 2));
}

#[tokio::test]
#[serial]
async fn cache_incompatible_bundled_compatible_falls_back() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    write(&cache_copy, v2_0_payload());

    let bundled_dir = tempdir().unwrap();
    let bundled_path = bundled_dir.path().join("CLASSIC Main.yaml");
    write(&bundled_path, v1_0_payload());

    let file = ShippableFile {
        file_name: "CLASSIC Main.yaml".into(),
        bundled_path: bundled_path.clone(),
    };
    let compat = SchemaCompat::new(1, 0);

    let loaded = load_with_env(file, &compat, env).await.unwrap();
    match loaded.source {
        LoadSource::Bundled(ref p) => assert_eq!(p, &bundled_path),
        ref other => panic!("expected Bundled, got {other:?}"),
    }
    assert_eq!(loaded.schema_version, SchemaVersion::new(1, 0));

    // Cache file MUST NOT be deleted — spec requirement.
    assert!(
        cache_copy.exists(),
        "incompatible cache copy must remain on disk"
    );
}

#[tokio::test]
#[serial]
async fn both_incompatible_returns_no_compatible_source() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    write(&cache_copy, v2_0_payload());

    let bundled_dir = tempdir().unwrap();
    let bundled_path = bundled_dir.path().join("CLASSIC Main.yaml");
    write(&bundled_path, v2_0_payload());

    let file = ShippableFile {
        file_name: "CLASSIC Main.yaml".into(),
        bundled_path: bundled_path.clone(),
    };
    let compat = SchemaCompat::new(1, 0);

    let err = load_with_env(file, &compat, env).await.unwrap_err();
    let YamlLoadError::NoCompatibleSource {
        file_name,
        candidates,
    } = err;
    assert_eq!(file_name, "CLASSIC Main.yaml");
    assert_eq!(candidates.len(), 2, "both candidates should be rejected");
    for c in &candidates {
        assert!(
            c.reason.contains("MAJOR"),
            "expected MAJOR rejection, got: {c}"
        );
    }
}

#[tokio::test]
#[serial]
async fn neither_exists_returns_no_compatible_source() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    // Resolve and then forget the cache dir so there's nothing to find.
    let _ = resolve_cache_dir(env.clone());

    let bundled_dir = tempdir().unwrap();
    let bundled_path = bundled_dir.path().join("CLASSIC Main.yaml");

    let file = ShippableFile {
        file_name: "CLASSIC Main.yaml".into(),
        bundled_path: bundled_path.clone(),
    };
    let compat = SchemaCompat::new(1, 0);

    let err = load_with_env(file, &compat, env).await.unwrap_err();
    let YamlLoadError::NoCompatibleSource { candidates, .. } = err;
    assert!(!candidates.is_empty(), "bundled miss must be recorded");
    assert!(
        candidates
            .iter()
            .any(|c| c.reason.contains("not found on disk")),
        "expected 'not found' rejection for missing bundled file: {candidates:?}"
    );
}

#[tokio::test]
#[serial]
async fn malformed_schema_version_in_cache_is_rejected_not_deleted() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    write(&cache_copy, "schema_version: \"v1.2\"\n");

    let bundled_dir = tempdir().unwrap();
    let bundled_path = bundled_dir.path().join("CLASSIC Main.yaml");
    write(&bundled_path, v1_0_payload());

    let file = ShippableFile {
        file_name: "CLASSIC Main.yaml".into(),
        bundled_path: bundled_path.clone(),
    };
    let compat = SchemaCompat::new(1, 0);

    let loaded = load_with_env(file, &compat, env).await.unwrap();
    // Bundled is compatible, so load should succeed via bundled despite
    // malformed cache.
    assert!(matches!(loaded.source, LoadSource::Bundled(_)));
    assert!(
        cache_copy.exists(),
        "malformed cache copy must remain on disk for manual recovery"
    );
}

#[tokio::test]
#[serial]
async fn steady_state_read_with_both_cache_and_prev_does_not_swap() {
    // Regression for Codex adversarial review finding:
    // `load_shippable_yaml` must NOT swap `<file>` and `<file>.prev` on a
    // normal read. Calling the full `rollback()` helper on every load
    // silently reverts the just-installed file whenever a `.prev`
    // rollback copy is preserved alongside it.
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    let prev_copy = cache_dir.join("CLASSIC Main.yaml.prev");

    // Post-install steady state: canonical holds the newly-applied v1.2;
    // `.prev` preserves the previously-installed v1.0 for rollback.
    write(&cache_copy, v1_2_payload());
    write(&prev_copy, v1_0_payload());

    let bundled_dir = tempdir().unwrap();
    let bundled_path = bundled_dir.path().join("CLASSIC Main.yaml");
    write(&bundled_path, v1_0_payload());

    let file = ShippableFile {
        file_name: "CLASSIC Main.yaml".into(),
        bundled_path: bundled_path.clone(),
    };
    let compat = SchemaCompat::new(1, 0);

    let loaded = load_with_env(file, &compat, env).await.unwrap();

    // Load must come from the canonical cache (the v1.2 file).
    assert!(matches!(loaded.source, LoadSource::Cache(_)));
    assert_eq!(loaded.schema_version, SchemaVersion::new(1, 2));

    // CRITICAL: neither file must have been swapped or mutated.
    assert_eq!(
        std::fs::read_to_string(&cache_copy).unwrap(),
        v1_2_payload(),
        "canonical cache copy must be unchanged (v1.2) after a read"
    );
    assert_eq!(
        std::fs::read_to_string(&prev_copy).unwrap(),
        v1_0_payload(),
        "`.prev` rollback copy must be unchanged (v1.0) after a read"
    );
}

/// Regression for Codex adversarial review finding: a transient cache
/// self-heal failure (missing parent dir, locked `.prev`, rename denial)
/// MUST NOT prevent loading the bundled copy. The cache is an optional
/// override; the bundled file is the canonical fallback and should still
/// satisfy the load.
///
/// Forces the failure by pointing the env resolver at a tempdir but NOT
/// creating the `CLASSIC/yaml-cache/` subtree — `self_heal`'s
/// lock-file creation then fails with a filesystem error.
#[tokio::test]
#[serial]
async fn self_heal_failure_falls_back_to_bundled() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);
    // Intentionally skip `resolve_cache_dir(env)` so the yaml-cache
    // subtree does not exist. `self_heal` will then fail when it tries
    // to open its lock file inside the nonexistent parent.

    let bundled_dir = tempdir().unwrap();
    let bundled_path = bundled_dir.path().join("CLASSIC Main.yaml");
    write(&bundled_path, v1_0_payload());

    let file = ShippableFile {
        file_name: "CLASSIC Main.yaml".into(),
        bundled_path: bundled_path.clone(),
    };
    let compat = SchemaCompat::new(1, 0);

    let loaded = load_with_env(file, &compat, env)
        .await
        .expect("bundled fallback must succeed despite cache self-heal failure");
    match loaded.source {
        LoadSource::Bundled(ref p) => assert_eq!(p, &bundled_path),
        ref other => panic!("expected Bundled source, got {other:?}"),
    }
    assert_eq!(loaded.schema_version, SchemaVersion::new(1, 0));
}

#[tokio::test]
#[serial]
async fn self_heal_recovers_interrupted_install() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    // Simulate interrupted install state: no canonical file, only `.prev`.
    let prev_path = cache_dir.join("CLASSIC Main.yaml.prev");
    write(&prev_path, v1_0_payload());
    assert!(!cache_dir.join("CLASSIC Main.yaml").exists());

    let bundled_dir = tempdir().unwrap();
    let bundled_path = bundled_dir.path().join("CLASSIC Main.yaml");
    // Bundled exists but at a higher schema so we can distinguish which
    // path the loader took.
    write(&bundled_path, v1_2_payload());

    let file = ShippableFile {
        file_name: "CLASSIC Main.yaml".into(),
        bundled_path: bundled_path.clone(),
    };
    let compat = SchemaCompat::new(1, 0);

    let loaded = load_with_env(file, &compat, env).await.unwrap();

    // After self-heal, the cache path must exist and must have been the
    // source of the load.
    assert!(cache_dir.join("CLASSIC Main.yaml").exists());
    assert!(!prev_path.exists());
    match loaded.source {
        LoadSource::Cache(ref p) => assert_eq!(p, &cache_dir.join("CLASSIC Main.yaml")),
        other => panic!("expected Cache source after self-heal, got {other:?}"),
    }
    assert_eq!(loaded.schema_version, SchemaVersion::new(1, 0));
}
