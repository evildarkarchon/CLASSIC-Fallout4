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

use crate::client_schemas;
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

// ---------------------------------------------------------------------------
// CLASSIC Main.yaml version extraction
// ---------------------------------------------------------------------------

/// Errors from [`load_main_yaml_version`] /
/// [`load_main_yaml_version_with_bundled_dir`].
///
/// `Load` wraps the generic shippable-loader error for the file-missing,
/// parse-failure, missing / malformed `schema_version`, and incompatible-
/// schema cases. The three `Version*` variants cover post-schema-gate
/// problems: the YAML loaded and passed the `client_schemas::MAIN_YAML`
/// gate, but the expected `CLASSIC_Info.version` scalar was missing,
/// blank, or of the wrong YAML type.
#[derive(Debug, Error)]
#[non_exhaustive]
pub enum MainYamlVersionError {
    /// Underlying shippable loader failure. Schema-incompatibility rejections
    /// surface here via [`YamlLoadError::NoCompatibleSource`], where the
    /// per-candidate `reason` string carries the formatted
    /// `incompatible MAJOR: file=... client_accepted=...` (or `MINOR`)
    /// diagnostic.
    #[error(transparent)]
    Load(#[from] YamlLoadError),

    /// `CLASSIC_Info.version` is absent or the `CLASSIC_Info` section
    /// itself is missing.
    ///
    /// The field is named `source_path` rather than `source` because
    /// `thiserror` reserves the `source` field name for the error-chain
    /// link (it would otherwise demand `StdError` on the field type).
    #[error("CLASSIC_Info.version is missing from `{}`", source_path.display())]
    VersionKeyMissing {
        /// Path of the loaded candidate (cache or bundled).
        source_path: PathBuf,
    },

    /// `CLASSIC_Info.version` is present but empty or whitespace-only.
    #[error("CLASSIC_Info.version is empty in `{}`", source_path.display())]
    VersionEmpty {
        /// Path of the loaded candidate.
        source_path: PathBuf,
    },

    /// `CLASSIC_Info.version` is present but not a YAML scalar string.
    #[error(
        "CLASSIC_Info.version has a non-string value in `{}`",
        source_path.display(),
    )]
    VersionNotString {
        /// Path of the loaded candidate.
        source_path: PathBuf,
    },

    /// `CLASSIC_Info.version` is a non-empty string but its shape does
    /// not match the schema-2.0 contract: an optional leading `v`/`V`
    /// prefix followed by strict release SemVer (`MAJOR.MINOR.PATCH`
    /// only, no pre-release suffix, no build metadata, no legacy
    /// `CLASSIC ` decoration). CLASSIC ships release-only versions by
    /// policy (see `set_version.ps1`, the CMake `project(VERSION)`
    /// guard, and `AGENTS.md`'s no-prerelease rule) and the loader
    /// enforces that policy here so a malformed publish cannot reach
    /// downstream update-check classification, where it would silently
    /// degrade into `Classification::Unknown` instead of failing fast.
    #[error(
        "CLASSIC_Info.version `{value}` in `{}` is not valid schema-2.0 release SemVer: {reason}",
        source_path.display(),
    )]
    VersionInvalid {
        /// Path of the loaded candidate.
        source_path: PathBuf,
        /// The raw trimmed value that failed validation, echoed for
        /// diagnostics.
        value: String,
        /// Human-readable reason the value failed the shape check —
        /// distinguishes the legacy `CLASSIC ` decoration from a
        /// prerelease/build suffix from a non-numeric component.
        reason: String,
    },
}

/// Load `CLASSIC Main.yaml` with [`client_schemas::MAIN_YAML`] schema gating
/// and return the trimmed `CLASSIC_Info.version` value.
///
/// Delegates to [`load_shippable_yaml`] so both the bundled file and a
/// cache override are considered, and both are rejected unless
/// `schema_version` satisfies `MAIN_YAML`. The function never returns the
/// empty string on success; see [`MainYamlVersionError`] for every
/// post-load failure shape.
///
/// Native frontends typically pass the install-tree directory they already
/// discovered via [`load_main_yaml_version_with_bundled_dir`]. The no-arg
/// form keeps the default relative path resolved against the process
/// working directory — correct for the repo-root tools and tests, but not
/// for packaged installs whose CWD may differ from the exe directory.
pub async fn load_main_yaml_version() -> Result<String, MainYamlVersionError> {
    load_main_yaml_version_with_bundled_dir(None).await
}

/// Variant of [`load_main_yaml_version`] that accepts an explicit
/// install-tree directory containing `CLASSIC Main.yaml`.
///
/// `bundled_dir` is the directory that holds the shippable YAML files
/// (e.g. `<install>/CLASSIC Data/databases`). `None` preserves the
/// no-arg behavior (relative path resolved against process CWD).
///
/// # Bundled fallback for structurally-unusable cache
///
/// The shippable loader picks a source using only `schema_version`
/// compatibility; it has no opinion on the inner `CLASSIC_Info.version`
/// scalar. When a cache copy is schema-compatible but its
/// `CLASSIC_Info.version` is absent, blank, or non-string, a naive
/// extraction would hard-error here even though the bundled file is
/// still valid. That is exactly the class of per-user cache corruption
/// the bundled file exists to survive, so this function retries the
/// bundled candidate explicitly on
/// [`MainYamlVersionError::VersionKeyMissing`] /
/// [`MainYamlVersionError::VersionEmpty`] /
/// [`MainYamlVersionError::VersionNotString`] when the original load
/// came from the cache. The retry preserves the cache file on disk
/// (matching the spec's "never delete rejected candidates" rule) and
/// logs a single `warn!` line naming the offending cache path.
pub async fn load_main_yaml_version_with_bundled_dir(
    bundled_dir: Option<&Path>,
) -> Result<String, MainYamlVersionError> {
    let file = main_yaml_file_with_bundled_dir(bundled_dir);
    let loaded = load_shippable_yaml(file.clone(), &client_schemas::MAIN_YAML).await?;
    resolve_main_yaml_version_with_bundled_fallback(loaded, &file).await
}

/// Env-injectable variant used by tests to redirect the cache-dir lookup
/// without touching process env. Production code uses the two wrappers above.
///
/// Shares the cache → bundled structural-fallback behavior documented on
/// [`load_main_yaml_version_with_bundled_dir`]; the `env` closure is only
/// consulted for cache-dir resolution on the initial load. The retry
/// path reads the bundled file directly and never reconsults `env`.
pub async fn load_main_yaml_version_with_env<F>(
    bundled_dir: Option<&Path>,
    env: F,
) -> Result<String, MainYamlVersionError>
where
    F: Fn(&str) -> Option<String>,
{
    let file = main_yaml_file_with_bundled_dir(bundled_dir);
    let loaded =
        load_shippable_yaml_with_env(file.clone(), &client_schemas::MAIN_YAML, env).await?;
    resolve_main_yaml_version_with_bundled_fallback(loaded, &file).await
}

fn main_yaml_file_with_bundled_dir(bundled_dir: Option<&Path>) -> ShippableFile {
    let mut file = ShippableFile::main();
    if let Some(dir) = bundled_dir {
        file.bundled_path = dir.join(&file.file_name);
    }
    file
}

async fn resolve_main_yaml_version_with_bundled_fallback(
    loaded: LoadedShippable,
    file: &ShippableFile,
) -> Result<String, MainYamlVersionError> {
    let cache_sourced = matches!(loaded.source, LoadSource::Cache(_));
    match extract_main_yaml_version(&loaded) {
        Ok(version) => Ok(version),
        Err(err) if cache_sourced && is_structural_version_error(&err) => {
            let cache_path = match &loaded.source {
                LoadSource::Cache(p) => p.display().to_string(),
                LoadSource::Bundled(_) => {
                    unreachable!("cache_sourced guard guarantees LoadSource::Cache on this branch")
                }
            };
            log::warn!(
                "cache copy `{}` is schema-compatible but structurally unusable \
                 for `CLASSIC_Info.version`: {}; retrying bundled candidate",
                cache_path,
                err,
            );
            let bundled_only = load_main_yaml_from_bundled_only(file).await?;
            extract_main_yaml_version(&bundled_only)
        }
        Err(err) => Err(err),
    }
}

fn is_structural_version_error(err: &MainYamlVersionError) -> bool {
    matches!(
        err,
        MainYamlVersionError::VersionKeyMissing { .. }
            | MainYamlVersionError::VersionEmpty { .. }
            | MainYamlVersionError::VersionNotString { .. }
            // A cache copy whose `CLASSIC_Info.version` fails the
            // schema-2.0 shape check is just as "cache corrupted" as
            // the other structural variants — a valid bundled file
            // must still be reachable, not locked out behind a
            // malformed user-cache write.
            | MainYamlVersionError::VersionInvalid { .. }
    )
}

/// Force-load only the bundled `CLASSIC Main.yaml` candidate, bypassing
/// the cache precedence. Used by the structural-fallback retry path so a
/// structurally-unusable cache copy cannot lock out a valid bundled
/// file. Reuses [`try_candidate`] so the schema-compat gate and the
/// rejection-reason formatting stay identical to the primary loader.
async fn load_main_yaml_from_bundled_only(
    file: &ShippableFile,
) -> Result<LoadedShippable, YamlLoadError> {
    match try_candidate(
        &file.bundled_path,
        &client_schemas::MAIN_YAML,
        &file.file_name,
    )
    .await
    {
        Ok(Some(loaded)) => Ok(LoadedShippable {
            source: LoadSource::Bundled(file.bundled_path.clone()),
            ..loaded
        }),
        Ok(None) => Err(YamlLoadError::NoCompatibleSource {
            file_name: file.file_name.clone(),
            candidates: vec![CandidateRejection {
                path: file.bundled_path.clone(),
                reason: "bundled YAML not found on disk".to_string(),
            }],
        }),
        Err(rejection) => Err(YamlLoadError::NoCompatibleSource {
            file_name: file.file_name.clone(),
            candidates: vec![rejection],
        }),
    }
}

fn extract_main_yaml_version(loaded: &LoadedShippable) -> Result<String, MainYamlVersionError> {
    let source_path: PathBuf = match &loaded.source {
        LoadSource::Cache(p) | LoadSource::Bundled(p) => p.clone(),
    };

    let Some(root) = loaded.yaml.as_hash() else {
        return Err(MainYamlVersionError::VersionKeyMissing { source_path });
    };

    let classic_info = match root
        .iter()
        .find_map(|(k, v)| (k.as_str() == Some("CLASSIC_Info")).then_some(v))
    {
        Some(value) => value,
        None => {
            return Err(MainYamlVersionError::VersionKeyMissing { source_path });
        }
    };

    let classic_info_map = match classic_info {
        Yaml::Hash(h) => h,
        _ => {
            return Err(MainYamlVersionError::VersionNotString { source_path });
        }
    };

    let version_node = match classic_info_map
        .iter()
        .find_map(|(k, v)| (k.as_str() == Some("version")).then_some(v))
    {
        Some(value) => value,
        None => {
            return Err(MainYamlVersionError::VersionKeyMissing { source_path });
        }
    };

    let raw = match version_node {
        Yaml::String(s) => s.as_str(),
        // Treat explicit nulls as "missing", matching how the rest of this
        // crate folds `null` into the absent case.
        Yaml::Null | Yaml::BadValue => {
            return Err(MainYamlVersionError::VersionKeyMissing { source_path });
        }
        _ => {
            return Err(MainYamlVersionError::VersionNotString { source_path });
        }
    };

    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err(MainYamlVersionError::VersionEmpty { source_path });
    }

    // Enforce schema-2.0 release-semver policy at the loader so a
    // malformed publish (legacy `CLASSIC v...` prefix, a stray
    // `-beta.1` suffix, or a typo like `9.1`) cannot flow through to
    // `check_app_notification` / `classify`, where `semver::Version::parse`
    // of a decorated string would silently degrade to
    // `Classification::Unknown` and the user would see nothing wrong.
    validate_release_semver_shape(trimmed).map_err(|reason| {
        MainYamlVersionError::VersionInvalid {
            source_path: source_path.clone(),
            value: trimmed.to_string(),
            reason,
        }
    })?;

    Ok(trimmed.to_string())
}

/// Validate that `value` matches the schema-2.0 version-field contract:
/// an optional leading `v`/`V` followed by three non-empty all-digit
/// components separated by `.`. Deliberately does NOT accept SemVer
/// prerelease (`-beta.1`) or build-metadata (`+build.5`) suffixes — the
/// app policy (see `AGENTS.md`, `set_version.ps1`, and
/// `project_no_semver_prerelease.md` memory) is that CLASSIC ships
/// release-only versions. The legacy `CLASSIC v...` decoration was
/// dropped in schema_version 2.0 and is explicitly rejected here so a
/// stale bundled file surfaces the policy mismatch instead of leaking
/// into update classification.
fn validate_release_semver_shape(value: &str) -> std::result::Result<(), String> {
    // Explicitly reject the pre-2.0 `CLASSIC v...` / `CLASSIC ...` form
    // so the diagnostic is specific instead of the generic
    // "missing MAJOR.MINOR.PATCH".
    if let Some(rest) = value.strip_prefix("CLASSIC") {
        if rest.starts_with(' ') || rest.is_empty() {
            return Err(
                "schema-2.0 dropped the legacy `CLASSIC ` prefix; store the bare `vX.Y.Z` form"
                    .into(),
            );
        }
    }

    let body = value
        .strip_prefix('v')
        .or_else(|| value.strip_prefix('V'))
        .unwrap_or(value);

    let parts: Vec<&str> = body.split('.').collect();
    if parts.len() != 3 {
        return Err(format!(
            "expected exactly three dot-separated components (MAJOR.MINOR.PATCH), got {}",
            parts.len()
        ));
    }
    for part in &parts {
        if part.is_empty() {
            return Err("MAJOR.MINOR.PATCH components must each be non-empty".into());
        }
        if !part.bytes().all(|b| b.is_ascii_digit()) {
            // Catches prerelease (`-beta.1` → middle component would
            // contain `-`), build metadata (`+build.5` → component
            // contains `+`), or any non-digit garbage.
            return Err(format!(
                "component `{part}` contains non-digit characters; prerelease suffixes and build metadata are not allowed"
            ));
        }
        // SemVer §2: numeric identifiers MUST NOT include leading zeros.
        // Must be rejected here because `u32::parse` silently strips
        // leading zeros, and the downstream `semver::Version::parse` in
        // `classic_update_core::notification::classify` rejects them
        // strictly — which would otherwise degrade the publish to
        // `Classification::Unknown` instead of failing fast at load time.
        if part.len() > 1 && part.starts_with('0') {
            return Err(format!(
                "component `{part}` has a leading zero; strict SemVer numeric identifiers must not include leading zeros"
            ));
        }
        if part.parse::<u32>().is_err() {
            return Err(format!(
                "component `{part}` does not fit in a 32-bit version number"
            ));
        }
    }
    Ok(())
}

#[cfg(test)]
#[path = "shippable_tests.rs"]
mod tests;
