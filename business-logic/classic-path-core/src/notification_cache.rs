//! Per-user app-notification cache directory resolver.
//!
//! CLASSIC publishes a small JSON manifest describing the current published
//! binary release (see `docs/api/app-update-notification-delivery.md`) and
//! the client fetches it Pages-first with an ETag. The cached body and ETag
//! land in this resolver's directory, deliberately disjoint from the
//! shippable YAML cache so diagnostic cleanups of one cache cannot
//! accidentally nuke the other (design decision D-06).
//!
//! # Owner/repo namespacing
//!
//! The cache directory is namespaced by `<owner>/<repo>` so a check against
//! repo A cannot seed repo B's ETag/body/marker. Without that scoping a
//! later Pages outage on repo B could reuse repo A's cached fallback
//! manifest instead of hitting repo B's Releases API, returning the wrong
//! notification status without any obvious signal. Owner and repo segments
//! are validated against the GitHub-allowed character set (`A-Za-z0-9._-`)
//! and rejected when they contain path separators, traversal segments, or
//! null bytes — defense in depth against an upstream caller that might
//! forward an unsanitized identifier.
//!
//! # Location
//!
//! - **Windows** — `%LOCALAPPDATA%\CLASSIC\app-notification\<owner>\<repo>\`,
//!   falling back to `%APPDATA%\CLASSIC\app-notification\<owner>\<repo>\`
//!   when `LOCALAPPDATA` is not set.
//! - **Other targets (source portability)** —
//!   `${XDG_CACHE_HOME:-$HOME/.cache}/CLASSIC/app-notification/<owner>/<repo>/`.
//!
//! Pre-namespacing caches landed at `.../app-notification/` (no subdirs).
//! Those orphaned files are deliberately ignored rather than migrated:
//! they are per-user disk cache (a few KB), the next successful check
//! repopulates the new namespaced location, and a migration path would
//! introduce its own correctness surface for what is essentially throwaway
//! state.
//!
//! # Helpers
//!
//! - [`notification_cache_dir`] — pure resolution, never touches the filesystem.
//! - [`ensure_notification_cache_dir`] — resolves and creates the directory (idempotent).
//!
//! # Testing
//!
//! The env-lookup seam is factored through [`notification_cache_dir_with_env`]
//! and [`ensure_notification_cache_dir_with_env`] so unit tests can drive the
//! resolver with a mocked environment without mutating process-wide env
//! (which is `unsafe` in edition 2024 and forbidden by this crate's
//! `unsafe_code = "deny"` lint).

use crate::error::PathError;
use std::path::PathBuf;

/// The per-user cache subdirectory name, relative to the platform cache root.
const CACHE_SUBDIR: &str = "CLASSIC";
/// The notification-specific cache directory name inside [`CACHE_SUBDIR`].
/// Intentionally different from [`crate::yaml_cache`]'s `yaml-cache/` so
/// the two caches remain structurally disjoint on disk.
const NOTIFICATION_CACHE_DIR: &str = "app-notification";

/// Defensive cap on owner/repo segment length. GitHub usernames max out at
/// 39 characters and repo names at 100; 100 covers both with margin and
/// keeps a single resolver's path well under any platform's path-component
/// limit.
const MAX_SEGMENT_LEN: usize = 100;

/// Resolve the absolute path of the per-user app-notification cache directory
/// for the given GitHub `owner`/`repo` slug.
///
/// This does not create the directory; use [`ensure_notification_cache_dir`]
/// to resolve and mkdir in one call.
///
/// # Errors
///
/// - [`PathError::InvalidPath`] when none of the expected environment
///   variables are set (e.g., Windows without `LOCALAPPDATA` and `APPDATA`,
///   or a Unix environment without `HOME` and without `XDG_CACHE_HOME`).
/// - [`PathError::InvalidPath`] when `owner` or `repo` is empty, exceeds
///   [`MAX_SEGMENT_LEN`], contains a character outside `A-Za-z0-9._-`, or
///   matches a traversal segment (`.` or `..`).
pub fn notification_cache_dir(owner: &str, repo: &str) -> Result<PathBuf, PathError> {
    notification_cache_dir_with_env(owner, repo, process_env_lookup)
}

/// Testable form of [`notification_cache_dir`] that reads environment
/// variables through a caller-supplied closure. Production code calls
/// [`notification_cache_dir`], which threads `std::env::var` through this
/// function.
///
/// The closure should return `None` for unset *or empty* variables; unit
/// tests typically pass a closure backed by a `HashMap`.
pub fn notification_cache_dir_with_env<F>(
    owner: &str,
    repo: &str,
    env: F,
) -> Result<PathBuf, PathError>
where
    F: Fn(&str) -> Option<String>,
{
    let owner = validate_segment("owner", owner)?;
    let repo = validate_segment("repo", repo)?;
    let root = cache_root(&env)?;
    Ok(root
        .join(CACHE_SUBDIR)
        .join(NOTIFICATION_CACHE_DIR)
        .join(owner)
        .join(repo))
}

/// Resolve the per-user app-notification cache directory and create it
/// (and parents) if missing. Idempotent — returns `Ok` even when the
/// directory already exists.
///
/// # Errors
///
/// - [`PathError::InvalidPath`] when the cache root cannot be resolved or
///   when `owner`/`repo` fail validation (see [`notification_cache_dir`]).
/// - [`PathError::IoError`] when directory creation fails after resolution.
pub fn ensure_notification_cache_dir(owner: &str, repo: &str) -> Result<PathBuf, PathError> {
    ensure_notification_cache_dir_with_env(owner, repo, process_env_lookup)
}

/// Testable form of [`ensure_notification_cache_dir`] that reads
/// environment variables through a caller-supplied closure.
pub fn ensure_notification_cache_dir_with_env<F>(
    owner: &str,
    repo: &str,
    env: F,
) -> Result<PathBuf, PathError>
where
    F: Fn(&str) -> Option<String>,
{
    let dir = notification_cache_dir_with_env(owner, repo, env)?;
    std::fs::create_dir_all(&dir).map_err(|source| PathError::IoError {
        path: dir.clone(),
        source,
    })?;
    Ok(dir)
}

/// Validate a single owner-or-repo path segment.
///
/// Accepts only `A-Za-z0-9._-` (a strict superset of GitHub's allowed
/// owner/repo character set), rejects empty values, traversal segments,
/// and anything longer than [`MAX_SEGMENT_LEN`]. The caller-facing label
/// (`"owner"` or `"repo"`) is folded into the error message so a binding
/// surfacing the failure can show *which* identifier was rejected.
fn validate_segment<'a>(label: &str, segment: &'a str) -> Result<&'a str, PathError> {
    if segment.is_empty() {
        return Err(PathError::InvalidPath(format!(
            "notification cache {label} segment must not be empty"
        )));
    }
    if segment.len() > MAX_SEGMENT_LEN {
        return Err(PathError::InvalidPath(format!(
            "notification cache {label} segment exceeds {MAX_SEGMENT_LEN} characters: `{segment}`"
        )));
    }
    if segment == "." || segment == ".." {
        return Err(PathError::InvalidPath(format!(
            "notification cache {label} segment must not be a traversal segment: `{segment}`"
        )));
    }
    if !segment
        .bytes()
        .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_' || b == b'.')
    {
        return Err(PathError::InvalidPath(format!(
            "notification cache {label} segment contains characters outside `A-Za-z0-9._-`: `{segment}`"
        )));
    }
    Ok(segment)
}

#[cfg(target_os = "windows")]
fn cache_root<F>(env: &F) -> Result<PathBuf, PathError>
where
    F: Fn(&str) -> Option<String>,
{
    if let Some(local) = env("LOCALAPPDATA") {
        return Ok(PathBuf::from(local));
    }
    if let Some(roaming) = env("APPDATA") {
        return Ok(PathBuf::from(roaming));
    }
    Err(PathError::InvalidPath(
        "neither LOCALAPPDATA nor APPDATA is set; cannot resolve notification cache directory"
            .into(),
    ))
}

#[cfg(not(target_os = "windows"))]
fn cache_root<F>(env: &F) -> Result<PathBuf, PathError>
where
    F: Fn(&str) -> Option<String>,
{
    if let Some(xdg) = env("XDG_CACHE_HOME") {
        return Ok(PathBuf::from(xdg));
    }
    if let Some(home) = env("HOME") {
        return Ok(PathBuf::from(home).join(".cache"));
    }
    Err(PathError::InvalidPath(
        "neither XDG_CACHE_HOME nor HOME is set; cannot resolve notification cache directory"
            .into(),
    ))
}

/// Read a process env var, returning `None` for unset *or* empty values so
/// that `%LOCALAPPDATA%=""` degrades to the next fallback rather than
/// producing a bogus empty path.
fn process_env_lookup(name: &str) -> Option<String> {
    match std::env::var(name) {
        Ok(s) if !s.is_empty() => Some(s),
        _ => None,
    }
}

#[cfg(test)]
#[path = "notification_cache_tests.rs"]
mod tests;
