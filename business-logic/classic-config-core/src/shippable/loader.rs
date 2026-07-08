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
pub(super) async fn try_candidate(
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
#[path = "loader_tests.rs"]
mod tests;
