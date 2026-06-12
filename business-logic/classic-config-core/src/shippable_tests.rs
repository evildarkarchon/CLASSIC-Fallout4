use super::*;
use classic_path_core::ensure_yaml_cache_dir_with_env;
use classic_settings_core::clear_global_yaml_cache;
use serial_test::serial;
use std::collections::HashMap;
use std::path::PathBuf;
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

// ---------------------------------------------------------------------------
// load_main_yaml_version — schema-gated `CLASSIC_Info.version` extractor used
// by the C++/Node/Python startup bridges. The tests below are the regression
// gate that replaced the GUI's raw `yaml_ops_get_string("CLASSIC_Info.version",
// "")` call; they exist to prove the loader rejects the legacy `CLASSIC v...`
// shape on `schema_version: 1.x` and refuses blank / non-string values on the
// post-2.0 shape.
// ---------------------------------------------------------------------------

fn v2_0_no_classic_info() -> &'static str {
    "schema_version: \"2.0\"\n"
}

fn v2_0_empty_version() -> &'static str {
    "schema_version: \"2.0\"\nCLASSIC_Info:\n  version: \"\"\n"
}

fn v2_0_whitespace_version() -> &'static str {
    "schema_version: \"2.0\"\nCLASSIC_Info:\n  version: \"   \"\n"
}

fn v2_0_nonstring_version() -> &'static str {
    "schema_version: \"2.0\"\nCLASSIC_Info:\n  version:\n    - a\n    - b\n"
}

fn v2_0_null_version() -> &'static str {
    "schema_version: \"2.0\"\nCLASSIC_Info:\n  version: ~\n"
}

fn v2_0_with_padding(version: &str) -> String {
    format!("schema_version: \"2.0\"\nCLASSIC_Info:\n  version: \"  {version}  \"\n",)
}

/// Happy path: `schema_version: 2.0` bundled payload with a bare SemVer —
/// the trimmed version flows through.
#[tokio::test]
#[serial]
async fn main_yaml_version_happy_path_bundled() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_payload(),
    );

    let version = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect("2.0 payload with bare SemVer must succeed");
    assert_eq!(version, "v9.1.0");
}

/// Values are trimmed, not echoed verbatim — guards against accidental
/// whitespace leaking into downstream update classification.
#[tokio::test]
#[serial]
async fn main_yaml_version_trims_surrounding_whitespace() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        &v2_0_with_padding("v9.0.0"),
    );

    let version = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect("padded version must trim cleanly");
    assert_eq!(version, "v9.0.0");
}

/// The regression gate: a stale `schema_version: 1.x` payload with
/// `CLASSIC v...` must fail loudly via the schema gate instead of flowing
/// through to `QApplication::applicationVersion()`.
#[tokio::test]
#[serial]
async fn main_yaml_version_rejects_legacy_classic_prefix_schema_v1() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v1_2_payload(),
    );

    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect_err("schema_version 1.2 must not satisfy MAIN_YAML = 2.0");
    match err {
        super::MainYamlVersionError::Load(YamlLoadError::NoCompatibleSource {
            file_name,
            candidates,
        }) => {
            assert_eq!(file_name, "CLASSIC Main.yaml");
            assert!(
                candidates
                    .iter()
                    .any(|c| c.reason.starts_with("incompatible MAJOR")),
                "expected an incompatible-major rejection, got {candidates:?}",
            );
        }
        other => panic!("expected Load(NoCompatibleSource), got {other:?}"),
    }
}

/// A schema-2.0 document with no `CLASSIC_Info` section at all is a typed
/// `VersionKeyMissing`, not a generic load failure.
#[tokio::test]
#[serial]
async fn main_yaml_version_missing_section_is_structural_error() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_no_classic_info(),
    );

    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect_err("missing CLASSIC_Info section must surface VersionKeyMissing");
    assert!(
        matches!(err, super::MainYamlVersionError::VersionKeyMissing { .. }),
        "expected VersionKeyMissing, got {err:?}",
    );
}

/// An explicit null `version` key is treated as "missing", matching how the
/// rest of this crate folds YAML nulls into the absent case.
#[tokio::test]
#[serial]
async fn main_yaml_version_null_is_missing() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_null_version(),
    );

    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect_err("null version must surface VersionKeyMissing");
    assert!(
        matches!(err, super::MainYamlVersionError::VersionKeyMissing { .. }),
        "expected VersionKeyMissing, got {err:?}",
    );
}

/// Blank string and whitespace-only values both map to `VersionEmpty`.
#[tokio::test]
#[serial]
async fn main_yaml_version_empty_string_is_version_empty() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_empty_version(),
    );

    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env.clone())
        .await
        .expect_err("empty version must surface VersionEmpty");
    assert!(
        matches!(err, super::MainYamlVersionError::VersionEmpty { .. }),
        "expected VersionEmpty for empty string, got {err:?}",
    );

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_whitespace_version(),
    );
    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect_err("whitespace-only version must surface VersionEmpty");
    assert!(
        matches!(err, super::MainYamlVersionError::VersionEmpty { .. }),
        "expected VersionEmpty for whitespace, got {err:?}",
    );
}

/// A non-scalar YAML node under `version` (e.g. an array or mapping) is
/// `VersionNotString` — distinct from "missing" so the GUI can show a more
/// actionable diagnostic.
#[tokio::test]
#[serial]
async fn main_yaml_version_nonstring_value() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_nonstring_version(),
    );

    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect_err("non-string version must surface VersionNotString");
    assert!(
        matches!(err, super::MainYamlVersionError::VersionNotString { .. }),
        "expected VersionNotString, got {err:?}",
    );
}

/// Regression for Codex adversarial review finding: a cache copy that
/// satisfies the schema-compat gate but is structurally unusable for
/// `CLASSIC_Info.version` (missing `CLASSIC_Info` section, blank
/// `version`, non-string `version`) MUST NOT lock out the bundled
/// fallback. Before this fix, a schema-2.0 cache copy with no
/// `CLASSIC_Info` section would surface `VersionKeyMissing` even when
/// the bundled 2.0 file was perfectly valid, bricking GUI startup on
/// recoverable per-user cache corruption.
#[tokio::test]
#[serial]
async fn main_yaml_version_cache_missing_section_falls_back_to_bundled() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    // Schema-compatible 2.0 header but no `CLASSIC_Info` section at all.
    write(&cache_copy, v2_0_no_classic_info());

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_payload(),
    );

    let version = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect("structurally-broken cache must not block bundled fallback");
    assert_eq!(version, "v9.1.0");
    assert!(
        cache_copy.exists(),
        "structurally-broken cache copy must remain on disk (never-delete rule)",
    );
}

/// Regression for Codex adversarial review finding (empty-version
/// variant): a schema-compatible cache copy whose
/// `CLASSIC_Info.version` is blank must fall through to the bundled
/// file rather than surfacing `VersionEmpty` as a fatal error.
#[tokio::test]
#[serial]
async fn main_yaml_version_cache_empty_version_falls_back_to_bundled() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    write(&cache_copy, v2_0_empty_version());

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_payload(),
    );

    let version = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect("empty cache version must not block bundled fallback");
    assert_eq!(version, "v9.1.0");
    assert!(
        cache_copy.exists(),
        "empty-version cache must remain on disk"
    );
}

/// Regression for Codex adversarial review finding (non-string
/// variant): a schema-compatible cache copy whose
/// `CLASSIC_Info.version` is a mapping or sequence must fall through to
/// the bundled file rather than surfacing `VersionNotString` as a fatal
/// error.
#[tokio::test]
#[serial]
async fn main_yaml_version_cache_nonstring_version_falls_back_to_bundled() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    write(&cache_copy, v2_0_nonstring_version());

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_payload(),
    );

    let version = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect("non-string cache version must not block bundled fallback");
    assert_eq!(version, "v9.1.0");
    assert!(
        cache_copy.exists(),
        "non-string-version cache must remain on disk",
    );
}

/// Negative case: when the cache is structurally broken AND the bundled
/// file is absent, the structural fallback cannot save the load. This
/// surfaces a generic `Load(NoCompatibleSource)` error rather than the
/// cache-side `Version*` error, because at that point the install
/// itself is broken and the bundled path is the actionable diagnostic.
#[tokio::test]
#[serial]
async fn main_yaml_version_cache_structural_with_bundled_missing_surfaces_error() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    write(&cache_copy, v2_0_no_classic_info());

    // Bundled directory exists but contains no CLASSIC Main.yaml.
    let bundled_dir = tempdir().unwrap();

    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect_err("missing bundled file on structural-fallback must error");
    match err {
        super::MainYamlVersionError::Load(YamlLoadError::NoCompatibleSource {
            file_name,
            candidates,
        }) => {
            assert_eq!(file_name, "CLASSIC Main.yaml");
            assert!(
                candidates
                    .iter()
                    .any(|c| c.reason.contains("not found on disk")),
                "expected 'not found' rejection for missing bundled file, got {candidates:?}",
            );
        }
        other => panic!("expected Load(NoCompatibleSource), got {other:?}"),
    }
    assert!(cache_copy.exists(), "cache copy must remain on disk");
}

/// When the cache has a legacy 1.x payload but the bundled file is 2.0,
/// the cache is rejected by the schema gate, the bundled 2.0 `version`
/// flows through, and the cache file stays on disk (spec requirement).
#[tokio::test]
#[serial]
async fn main_yaml_version_cache_incompatible_bundled_wins() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    write(&cache_copy, v1_2_payload());

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_payload(),
    );

    let version = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect("bundled 2.0 must win when cache is 1.x");
    assert_eq!(version, "v9.1.0");
    assert!(
        cache_copy.exists(),
        "incompatible cache copy must remain on disk",
    );
}

// ---------------------------------------------------------------------------
// VersionInvalid — strict schema-2.0 release-semver shape enforcement.
// Regression gate for the Codex adversarial-review MEDIUM finding on
// `extract_main_yaml_version`: the loader MUST reject
//   (a) the legacy `CLASSIC v...` / `CLASSIC ...` decoration that
//       `schema_version: 2.0` dropped (previously flowed through because
//       a non-empty YAML string was enough),
//   (b) SemVer prerelease suffixes (`-beta.1`) and build metadata
//       (`+build.5`) — CLASSIC policy is release-only versions, so
//       anything else is a publish error,
//   (c) non-numeric / wrong-arity components (`9.1`, `1.2.a`, `garbage`),
// so a malformed publish fails fast instead of silently degrading to
// `Classification::Unknown` in `check_app_notification::classify`.
// ---------------------------------------------------------------------------

fn v2_0_with_raw_version(version: &str) -> String {
    format!("schema_version: \"2.0\"\nCLASSIC_Info:\n  version: \"{version}\"\n",)
}

/// A schema-2.0 bundled file that still carries the dropped `CLASSIC v...`
/// decoration must surface as `VersionInvalid`, not flow through to
/// downstream update-check classification.
#[tokio::test]
#[serial]
async fn main_yaml_version_rejects_legacy_classic_prefix_schema_v2() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        &v2_0_with_raw_version("CLASSIC v9.1.0"),
    );

    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect_err("legacy `CLASSIC ` prefix must surface VersionInvalid on 2.0");
    match err {
        super::MainYamlVersionError::VersionInvalid { value, reason, .. } => {
            assert_eq!(value, "CLASSIC v9.1.0");
            assert!(
                reason.contains("legacy `CLASSIC `") || reason.contains("CLASSIC"),
                "reason must name the legacy prefix, got: {reason}",
            );
        }
        other => panic!("expected VersionInvalid, got {other:?}"),
    }
}

/// A SemVer prerelease suffix on a schema-2.0 version (e.g. `-beta.1`)
/// violates CLASSIC's release-only policy and must surface as
/// `VersionInvalid` rather than flowing through where `semver::Version`
/// parsing downstream would silently accept it.
#[tokio::test]
#[serial]
async fn main_yaml_version_rejects_prerelease_suffix() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        &v2_0_with_raw_version("v9.2.0-beta.1"),
    );

    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect_err("prerelease suffix must surface VersionInvalid");
    match err {
        super::MainYamlVersionError::VersionInvalid { value, reason, .. } => {
            assert_eq!(value, "v9.2.0-beta.1");
            // The `.` inside `-beta.1` makes `split('.')` yield four
            // components, so the arity check fires before the
            // non-digit check. Either failure is acceptable — both
            // correctly reject the prerelease — but we assert on the
            // actual message to keep the diagnostic stable.
            assert!(
                reason.contains("three dot-separated")
                    || reason.contains("non-digit")
                    || reason.contains("prerelease"),
                "reason must describe the prerelease / arity failure, got: {reason}",
            );
        }
        other => panic!("expected VersionInvalid, got {other:?}"),
    }
}

/// A prerelease suffix without an extra dot (e.g. `v9.2.0-beta`) still
/// gets caught, this time by the non-digit component check rather than
/// the arity check. Complements
/// `main_yaml_version_rejects_prerelease_suffix` to prove both branches
/// of the shape validator fire on the same policy violation.
#[tokio::test]
#[serial]
async fn main_yaml_version_rejects_dotless_prerelease_suffix() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        &v2_0_with_raw_version("v9.2.0-beta"),
    );

    let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect_err("dotless prerelease suffix must surface VersionInvalid");
    match err {
        super::MainYamlVersionError::VersionInvalid { value, reason, .. } => {
            assert_eq!(value, "v9.2.0-beta");
            assert!(
                reason.contains("non-digit"),
                "dotless prerelease should trip the non-digit check, got: {reason}",
            );
        }
        other => panic!("expected VersionInvalid, got {other:?}"),
    }
}

/// SemVer build metadata (`+build.5`) is also a release-policy
/// violation and must surface as `VersionInvalid`, whether the version
/// carries the optional leading `v` or not. Both the `v9.2.0+build.5`
/// and the bare `9.1.0+build.5` forms are covered so the assertion
/// holds for every `CLASSIC_Info.version` shape the
/// `yaml-app-version-field` spec accepts as input.
#[tokio::test]
#[serial]
async fn main_yaml_version_rejects_build_metadata() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    for bad in ["v9.2.0+build.5", "9.1.0+build.5"] {
        let bundled_dir = tempdir().unwrap();
        write(
            &bundled_dir.path().join("CLASSIC Main.yaml"),
            &v2_0_with_raw_version(bad),
        );

        let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env.clone())
            .await
            .expect_err("build metadata must surface VersionInvalid");
        match err {
            super::MainYamlVersionError::VersionInvalid { value, reason, .. } => {
                assert_eq!(value, bad);
                // The `.5` tail makes `split('.')` yield four components,
                // so the arity check fires before the non-digit check.
                // Either diagnostic correctly names the policy violation.
                assert!(
                    reason.contains("three dot-separated")
                        || reason.contains("non-digit")
                        || reason.contains("build metadata"),
                    "reason must describe the build-metadata / arity failure for `{bad}`, got: {reason}",
                );
            }
            other => panic!("expected VersionInvalid for `{bad}`, got {other:?}"),
        }
    }
}

/// SemVer §2 forbids leading-zero numeric identifiers. The validator
/// must reject `v01.2.3` / `v1.02.3` / `v1.2.03` here so a malformed
/// publish surfaces as `VersionInvalid` with a specific diagnostic,
/// rather than slipping through to `semver::Version::parse` downstream
/// (which would silently degrade the update check to
/// `Classification::Unknown`). Regression gate for the Codex
/// adversarial-review HIGH finding on `validate_release_semver_shape`.
#[tokio::test]
#[serial]
async fn main_yaml_version_rejects_leading_zero_components() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    for bad in [
        "v01.2.3", "v1.02.3", "v1.2.03", "01.2.3", "1.02.3", "1.2.03",
    ] {
        let bundled_dir = tempdir().unwrap();
        write(
            &bundled_dir.path().join("CLASSIC Main.yaml"),
            &v2_0_with_raw_version(bad),
        );

        let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env.clone())
            .await
            .expect_err("leading-zero component must surface VersionInvalid");
        match err {
            super::MainYamlVersionError::VersionInvalid { value, reason, .. } => {
                assert_eq!(value, bad);
                assert!(
                    reason.contains("leading zero"),
                    "reason must name the leading-zero rule for `{bad}`, got: {reason}",
                );
            }
            other => panic!("expected VersionInvalid for `{bad}`, got {other:?}"),
        }
    }
}

/// A bare `0.Y.Z` / `X.0.Z` / `X.Y.0` stays valid — the leading-zero
/// rule only rejects multi-digit identifiers that start with `0`, not
/// the literal single-digit `0`.
#[tokio::test]
#[serial]
async fn main_yaml_version_accepts_single_digit_zero_components() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    for good in ["0.0.0", "v0.1.0", "v9.0.1", "v9.1.0", "0.99.0"] {
        let bundled_dir = tempdir().unwrap();
        write(
            &bundled_dir.path().join("CLASSIC Main.yaml"),
            &v2_0_with_raw_version(good),
        );

        let value = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env.clone())
            .await
            .unwrap_or_else(|err| panic!("bare-zero component must load for `{good}`: {err:?}"));
        assert_eq!(value, good);
    }
}

/// A two-component `9.1` or a word like `garbage` fails the strict
/// `MAJOR.MINOR.PATCH` shape check.
#[tokio::test]
#[serial]
async fn main_yaml_version_rejects_wrong_arity_and_nonnumeric() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    for bad in ["9.1", "v9.1", "9.1.2.3", "garbage", "v", "CLASSIC"] {
        let bundled_dir = tempdir().unwrap();
        write(
            &bundled_dir.path().join("CLASSIC Main.yaml"),
            &v2_0_with_raw_version(bad),
        );

        let err = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env.clone())
            .await
            .expect_err("malformed version must surface VersionInvalid");
        assert!(
            matches!(err, super::MainYamlVersionError::VersionInvalid { .. }),
            "expected VersionInvalid for `{bad}`, got {err:?}",
        );
    }
}

/// A schema-compatible cache copy whose `CLASSIC_Info.version` fails
/// the strict shape check must fall through to the bundled candidate
/// (same never-delete-cache behavior as the other structural variants).
/// Before the fix, a malformed cache write would lock startup because
/// the loader ran shape validation only once on the cache body.
#[tokio::test]
#[serial]
async fn main_yaml_version_cache_invalid_shape_falls_back_to_bundled() {
    clear_global_yaml_cache();
    let tmp = tempdir().unwrap();
    let env_entries = windows_env(tmp.path());
    let env = env_map(&env_entries);

    let cache_dir = resolve_cache_dir(env.clone());
    let cache_copy = cache_dir.join("CLASSIC Main.yaml");
    write(&cache_copy, &v2_0_with_raw_version("CLASSIC v9.1.0"));

    let bundled_dir = tempdir().unwrap();
    write(
        &bundled_dir.path().join("CLASSIC Main.yaml"),
        v2_0_payload(),
    );

    let version = super::load_main_yaml_version_with_env(Some(bundled_dir.path()), env)
        .await
        .expect("invalid-shape cache must not block bundled fallback");
    assert_eq!(version, "v9.1.0");
    assert!(
        cache_copy.exists(),
        "invalid-shape cache copy must remain on disk (never-delete rule)",
    );
}
