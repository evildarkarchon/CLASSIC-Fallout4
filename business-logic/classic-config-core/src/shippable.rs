//! Shippable-YAML loader precedence with schema-compatibility gating.
//!
//! CLASSIC ships two YAML data files (`CLASSIC Main.yaml`,
//! `CLASSIC Fallout4.yaml`) bundled into the install tree. At runtime, an
//! **updated** copy can land in a per-user YAML cache directory via the
//! yaml-update-delivery flow. This module provides the one-stop loader that
//! resolves which copy to read:
//!
//! 1. **Self-heal** — If the cache copy is missing but a `<file>.prev` exists
//!    (interrupted install state), promote `.prev` → canonical before
//!    checking compatibility. This uses
//!    [`classic_file_io_core::self_heal`] rather than the full
//!    [`classic_file_io_core::rollback`] helper; the loader MUST NOT swap
//!    `<file>` ↔ `<file>.prev` on normal reads (that would silently revert
//!    the just-installed file every time its cache is loaded).
//! 2. **Cache candidate** — If `<cache>/<filename>` exists and its
//!    `schema_version` satisfies the caller's [`SchemaCompat`], load it.
//! 3. **Bundled candidate** — Else load the bundled
//!    `CLASSIC Data/databases/<filename>` if its `schema_version` satisfies
//!    the same range.
//! 4. **No compatible source** — Else return
//!    [`YamlLoadError::NoCompatibleSource`] carrying a per-candidate
//!    rejection reason so the caller can log / surface the diagnostic.
//!
//! # Design notes
//!
//! - The cache directory is obtained from [`classic_path_core::yaml_cache_dir`]
//!   so platform-specific resolution (Windows `%LOCALAPPDATA%\CLASSIC\yaml-cache\`,
//!   Unix `${XDG_CACHE_HOME:-$HOME/.cache}/CLASSIC/yaml-cache/`) lives in one
//!   place.
//! - The self-heal delegates to
//!   [`classic_file_io_core::self_heal`] so a startup crash between the
//!   "rename target → .prev" and "rename tmp → target" steps of
//!   [`classic_file_io_core::install_atomic`] is recovered transparently.
//!   Unlike the broader [`classic_file_io_core::rollback`] helper,
//!   [`classic_file_io_core::self_heal`] only promotes `.prev` when the
//!   canonical target is missing; when both exist it is a strict no-op.
//! - We deliberately **do not** repurpose `YamlSource::Cache` for the cache
//!   directory: that variant already names `cache.yaml` and is plumbed
//!   through Python/Node FFI as a stable enum ordinal, so repurposing it
//!   would break binding parity. This helper is the new public surface for
//!   cache-aware shippable loads instead.
//!
//! # Consumer pattern
//!
//! ```rust,no_run
//! use classic_config_core::{
//!     client_schemas,
//!     shippable::{load_shippable_yaml, ShippableFile},
//! };
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let loaded = load_shippable_yaml(
//!     ShippableFile::main(),
//!     &client_schemas::MAIN_YAML,
//! ).await?;
//! println!("loaded from {:?}, schema {}", loaded.source, loaded.schema_version);
//! # Ok(())
//! # }
//! ```

use classic_file_io_core::{SelfHealOutcome, self_heal};
use classic_path_core::{yaml_cache_dir, yaml_cache_dir_with_env};
use classic_settings_core::{
    Compatibility, SchemaCompat, SchemaVersion, YamlSchemaError, extract_schema_version,
    load_yaml_merged_async, schema_compat_check,
};
use std::fmt;
use std::path::{Path, PathBuf};
use thiserror::Error;
use yaml_rust2::Yaml;

/// Identifies one shippable YAML file by its canonical filename and its
/// bundled-install path. Factory helpers ([`ShippableFile::main`],
/// [`ShippableFile::game`]) produce the default instances for the two
/// currently-shipped files.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ShippableFile {
    /// Canonical filename as it appears both in the install tree and in the
    /// per-user cache directory (e.g. `CLASSIC Main.yaml`).
    pub file_name: String,
    /// Absolute or install-relative path to the bundled copy. Relative paths
    /// are resolved against the process working directory at load time.
    pub bundled_path: PathBuf,
}

impl ShippableFile {
    /// `CLASSIC Main.yaml` — global metadata / registry.
    pub fn main() -> Self {
        Self {
            file_name: "CLASSIC Main.yaml".to_string(),
            bundled_path: PathBuf::from("CLASSIC Data/databases/CLASSIC Main.yaml"),
        }
    }

    /// `CLASSIC <Game>.yaml` — per-game crashgen / suspect tables.
    pub fn game(game: &str) -> Self {
        let file_name = format!("CLASSIC {game}.yaml");
        let bundled_path = PathBuf::from(format!("CLASSIC Data/databases/{file_name}"));
        Self {
            file_name,
            bundled_path,
        }
    }
}

/// Which candidate actually produced the loaded YAML document.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LoadSource {
    /// Loaded from `<yaml_cache_dir>/<file_name>`.
    Cache(PathBuf),
    /// Loaded from the bundled install-tree path.
    Bundled(PathBuf),
}

/// Result of a successful [`load_shippable_yaml`] call.
#[derive(Debug, Clone)]
pub struct LoadedShippable {
    /// The parsed YAML document (merged if the file carried multiple `---`
    /// documents, matching the rest of the crate's load path).
    pub yaml: Yaml,
    /// Where the document came from.
    pub source: LoadSource,
    /// The compatible `schema_version` header observed on that source.
    pub schema_version: SchemaVersion,
}

/// Why a single candidate (cache or bundled) was not used. Each load attempt
/// produces at most one of these per candidate; [`YamlLoadError::NoCompatibleSource`]
/// collects them to explain what the loader saw.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateRejection {
    /// Absolute path to the candidate file.
    pub path: PathBuf,
    /// Short, human-readable reason — already formatted with the offending
    /// value where applicable.
    pub reason: String,
}

impl fmt::Display for CandidateRejection {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.path.display(), self.reason)
    }
}

/// Errors produced by [`load_shippable_yaml`].
///
/// Marked `#[non_exhaustive]` so callers must include a wildcard arm. The
/// surface has already shrunk once (the historical `SelfHealFailed` variant
/// was folded into per-candidate rejections after the Codex adversarial
/// review) and may grow again if load-time diagnostics need to be surfaced
/// as first-class variants; the attribute keeps external match sites stable
/// across those changes.
#[derive(Debug, Error)]
#[non_exhaustive]
pub enum YamlLoadError {
    /// Neither the cache nor the bundled candidate was loadable **and**
    /// compatible. The `candidates` list is ordered from first-tried (cache)
    /// to last-tried (bundled).
    ///
    /// Self-heal failures on the cache path are reported inside this variant
    /// as a [`CandidateRejection`] rather than a separate top-level error: a
    /// transient lock/rename/permission failure while promoting `<file>.prev`
    /// must not prevent loading the bundled copy, since the cache is an
    /// optional override and the bundled file is the canonical fallback.
    #[error(
        "no compatible source for `{file_name}` among {candidate_count} candidate(s)",
        candidate_count = .candidates.len(),
    )]
    NoCompatibleSource {
        /// Canonical file name (e.g. `CLASSIC Main.yaml`).
        file_name: String,
        /// Per-candidate rejection context.
        candidates: Vec<CandidateRejection>,
    },
}

/// Load the `file` shippable YAML, preferring a compatible cache copy over the
/// bundled install-tree copy.
///
/// Precedence:
///
/// 1. Self-heal the cache path via [`self_heal`] — promotes `<file>.prev` to
///    `<file>` only when the canonical cache path is missing. Never swaps;
///    when both files exist it is a strict no-op so steady-state reads never
///    mutate the cache.
/// 2. If cache exists and its schema is compatible → load cache.
/// 3. Else if bundled exists and compatible → load bundled.
/// 4. Else → [`YamlLoadError::NoCompatibleSource`] listing every rejection.
///
/// Rejected candidates are **never deleted** (spec requirement: user keeps
/// the option to rebase onto a future compatible build). Rejections are also
/// emitted via `log::warn!` so contributors running with tracing enabled see
/// the diagnostic immediately.
pub async fn load_shippable_yaml(
    file: ShippableFile,
    compat: &SchemaCompat,
) -> Result<LoadedShippable, YamlLoadError> {
    let cache_path = resolve_cache_path_via(&file.file_name, yaml_cache_dir);
    load_shippable_with_cache_path(file, compat, cache_path).await
}

/// Env-injectable variant of [`load_shippable_yaml`]. Production code calls
/// the no-arg form, which threads `std::env::var` through the cache-dir
/// resolver; callers that need to drive the loader with a mocked environment
/// (integration tests, tooling, alternate runtime hosts) pass a closure that
/// answers environment lookups without touching the real process env.
///
/// The `env` closure is invoked only for the cache-dir resolution step; the
/// bundled path is used verbatim from [`ShippableFile::bundled_path`].
pub async fn load_shippable_yaml_with_env<F>(
    file: ShippableFile,
    compat: &SchemaCompat,
    env: F,
) -> Result<LoadedShippable, YamlLoadError>
where
    F: Fn(&str) -> Option<String>,
{
    let cache_path = resolve_cache_path_via(&file.file_name, || yaml_cache_dir_with_env(&env));
    load_shippable_with_cache_path(file, compat, cache_path).await
}

fn resolve_cache_path_via<R>(file_name: &str, resolver: R) -> Option<PathBuf>
where
    R: FnOnce() -> Result<PathBuf, classic_path_core::PathError>,
{
    match resolver() {
        Ok(dir) => Some(dir.join(file_name)),
        Err(err) => {
            // Cache dir resolution failure is not fatal on its own — we can
            // still try the bundled copy. Log once so the operator notices.
            log::warn!(
                "cache directory unavailable for `{}`: {}; falling back to bundled copy only",
                file_name,
                err,
            );
            None
        }
    }
}

async fn load_shippable_with_cache_path(
    file: ShippableFile,
    compat: &SchemaCompat,
    cache_path: Option<PathBuf>,
) -> Result<LoadedShippable, YamlLoadError> {
    let mut rejections: Vec<CandidateRejection> = Vec::new();

    // Attempt to self-heal an interrupted install (promote `<file>.prev` to
    // canonical when canonical is missing). A failure here MUST NOT abort
    // the load: the cache is an optional override and the bundled copy is
    // the canonical fallback. Fold the failure into a candidate rejection
    // so the operator sees it in logs and in the final error's rejection
    // list, then skip the cache candidate and continue to bundled.
    let cache_path = if let Some(cache_path) = cache_path {
        match self_heal(&cache_path) {
            Ok(outcome) => {
                log_self_heal(&cache_path, &outcome);
                Some(cache_path)
            }
            Err(source) => {
                log::warn!(
                    "cache self-heal failed for `{}`: {}; continuing with bundled source",
                    cache_path.display(),
                    source,
                );
                rejections.push(CandidateRejection {
                    path: cache_path,
                    reason: format!("self-heal failed: {source}"),
                });
                None
            }
        }
    } else {
        None
    };

    if let Some(cache_path) = &cache_path {
        match try_candidate(cache_path, compat, &file.file_name).await {
            Ok(Some(loaded)) => {
                return Ok(LoadedShippable {
                    source: LoadSource::Cache(cache_path.clone()),
                    ..loaded
                });
            }
            Ok(None) => {
                // Cache path simply doesn't exist; move on silently.
            }
            Err(rejection) => {
                log::warn!(
                    "rejecting cached YAML `{}`: {}",
                    rejection.path.display(),
                    rejection.reason,
                );
                rejections.push(rejection);
            }
        }
    }

    match try_candidate(&file.bundled_path, compat, &file.file_name).await {
        Ok(Some(loaded)) => {
            return Ok(LoadedShippable {
                source: LoadSource::Bundled(file.bundled_path.clone()),
                ..loaded
            });
        }
        Ok(None) => {
            rejections.push(CandidateRejection {
                path: file.bundled_path.clone(),
                reason: "bundled YAML not found on disk".to_string(),
            });
        }
        Err(rejection) => {
            log::warn!(
                "rejecting bundled YAML `{}`: {}",
                rejection.path.display(),
                rejection.reason,
            );
            rejections.push(rejection);
        }
    }

    Err(YamlLoadError::NoCompatibleSource {
        file_name: file.file_name,
        candidates: rejections,
    })
}

/// Try one candidate path. Returns:
/// - `Ok(None)` when the path does not exist (silent miss — the caller tries
///   the next candidate without recording a rejection, except for the final
///   fallback).
/// - `Ok(Some(loaded))` when the candidate loads and is compatible. The
///   caller still fills in [`LoadedShippable::source`].
/// - `Err(rejection)` when the candidate exists but is not usable (parse
///   failure, missing / malformed schema_version, incompatible schema).
async fn try_candidate(
    path: &Path,
    compat: &SchemaCompat,
    file_name: &str,
) -> Result<Option<LoadedShippable>, CandidateRejection> {
    if !path.exists() {
        return Ok(None);
    }

    let yaml = match load_yaml_merged_async(path).await {
        Ok(y) => y,
        Err(source) => {
            return Err(CandidateRejection {
                path: path.to_path_buf(),
                reason: format!("failed to parse YAML: {source}"),
            });
        }
    };

    let version = match extract_schema_version(&yaml) {
        Ok(v) => v,
        Err(err) => {
            // Fold the filename in so the log line is copy-pasteable.
            let err = err.with_file(file_name.to_string());
            return Err(CandidateRejection {
                path: path.to_path_buf(),
                reason: match err {
                    YamlSchemaError::Missing => {
                        "missing required `schema_version` header".to_string()
                    }
                    other => other.to_string(),
                },
            });
        }
    };

    match schema_compat_check(&version, compat) {
        Compatibility::Compatible => Ok(Some(LoadedShippable {
            yaml,
            // The caller overwrites this with the correct LoadSource variant.
            source: LoadSource::Bundled(path.to_path_buf()),
            schema_version: version,
        })),
        Compatibility::IncompatibleMajor {
            file_major,
            client_accepted_major,
        } => Err(CandidateRejection {
            path: path.to_path_buf(),
            reason: format!(
                "incompatible MAJOR: file={file_major} client_accepted={client_accepted_major}"
            ),
        }),
        Compatibility::IncompatibleMinor {
            file_minor,
            client_minimum_minor,
        } => Err(CandidateRejection {
            path: path.to_path_buf(),
            reason: format!(
                "incompatible MINOR: file={file_minor} client_minimum={client_minimum_minor}"
            ),
        }),
    }
}

fn log_self_heal(path: &Path, outcome: &SelfHealOutcome) {
    match outcome {
        SelfHealOutcome::Promoted { target } => {
            log::warn!(
                "self-healed interrupted YAML install at `{}`: promoted `{}.prev` to canonical",
                target.display(),
                path.display(),
            );
        }
        SelfHealOutcome::NoAction { .. } => {
            // Steady state: either the cache is already canonical (normal
            // post-install state, possibly with a `.prev` rollback copy
            // preserved) or nothing exists yet. No log line.
        }
    }
}

#[cfg(test)]
mod tests {
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

    fn v1_0_payload() -> &'static str {
        "schema_version: \"1.0\"\nCLASSIC_Info:\n  version: CLASSIC v9.0.0\n"
    }

    fn v1_2_payload() -> &'static str {
        "schema_version: \"1.2\"\nCLASSIC_Info:\n  version: CLASSIC v9.1.0\n"
    }

    fn v2_0_payload() -> &'static str {
        "schema_version: \"2.0\"\nCLASSIC_Info:\n  version: CLASSIC vFuture\n"
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
}
