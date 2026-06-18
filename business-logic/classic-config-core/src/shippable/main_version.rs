//! `CLASSIC Main.yaml` version extraction on top of the shippable loader.

use super::loader::{
    CandidateRejection, LoadSource, LoadedShippable, ShippableFile, YamlLoadError,
    load_shippable_yaml, load_shippable_yaml_with_env, try_candidate,
};
use crate::client_schemas;
use std::path::{Path, PathBuf};
use thiserror::Error;
use yaml_rust2::Yaml;

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
#[path = "main_version_tests.rs"]
mod tests;
