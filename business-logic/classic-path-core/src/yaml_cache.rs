//! Per-user YAML cache directory resolver.
//!
//! Shippable CLASSIC YAML files (`CLASSIC Main.yaml`, `CLASSIC Fallout4.yaml`,
//! future additions) are bundled into the install directory at build time but
//! are also allowed to be *updated in place* at runtime via the YAML update
//! delivery flow. Updated copies never overwrite the bundled install tree (which
//! may be read-only or under `Program Files`). Instead, they land in a per-user
//! cache directory resolved here.
//!
//! # Location
//!
//! - **Windows** — `%LOCALAPPDATA%\CLASSIC\yaml-cache\`, falling back to
//!   `%APPDATA%\CLASSIC\yaml-cache\` when `LOCALAPPDATA` is not set (unusual but
//!   possible on stripped-down Windows environments).
//! - **Other targets (source portability)** —
//!   `${XDG_CACHE_HOME:-$HOME/.cache}/CLASSIC/yaml-cache/`. This keeps the Rust
//!   workspace cross-compilable even though shipped binaries are Windows-only.
//!
//! # Helpers
//!
//! - [`yaml_cache_dir`] — pure resolution, never touches the filesystem.
//! - [`ensure_yaml_cache_dir`] — resolves and creates the directory (idempotent).
//!
//! # Testing
//!
//! The env-lookup seam is factored through [`yaml_cache_dir_with_env`] and
//! [`ensure_yaml_cache_dir_with_env`] so unit tests can drive the resolver with a
//! mocked environment without mutating process-wide env (which is `unsafe` in
//! edition 2024 and forbidden by this crate's `unsafe_code = "deny"` lint).

use crate::error::PathError;
use std::path::PathBuf;

/// The per-user cache subdirectory name, relative to the platform cache root.
const CACHE_SUBDIR: &str = "CLASSIC";
/// The YAML-specific cache directory name inside [`CACHE_SUBDIR`].
const YAML_CACHE_DIR: &str = "yaml-cache";

/// Resolve the absolute path of the per-user YAML cache directory.
///
/// This does not create the directory; use [`ensure_yaml_cache_dir`] to resolve
/// and mkdir in one call.
///
/// # Errors
///
/// Returns [`PathError::InvalidPath`] when none of the expected environment
/// variables are set (e.g., Windows without `LOCALAPPDATA` and `APPDATA`, or a
/// Unix environment without `HOME` and without `XDG_CACHE_HOME`).
pub fn yaml_cache_dir() -> Result<PathBuf, PathError> {
    yaml_cache_dir_with_env(process_env_lookup)
}

/// Testable form of [`yaml_cache_dir`] that reads environment variables through
/// a caller-supplied closure. Production code calls [`yaml_cache_dir`], which
/// threads `std::env::var` through this function.
///
/// The closure should return `None` for unset *or empty* variables; unit tests
/// typically pass a closure backed by a `HashMap`.
pub fn yaml_cache_dir_with_env<F>(env: F) -> Result<PathBuf, PathError>
where
    F: Fn(&str) -> Option<String>,
{
    let root = cache_root(&env)?;
    Ok(root.join(CACHE_SUBDIR).join(YAML_CACHE_DIR))
}

/// Resolve the per-user YAML cache directory and create it (and parents) if
/// missing. Idempotent — returns `Ok` even when the directory already exists.
///
/// # Errors
///
/// - [`PathError::InvalidPath`] when the cache root cannot be resolved
///   (see [`yaml_cache_dir`]).
/// - [`PathError::IoError`] when directory creation fails after resolution.
pub fn ensure_yaml_cache_dir() -> Result<PathBuf, PathError> {
    ensure_yaml_cache_dir_with_env(process_env_lookup)
}

/// Testable form of [`ensure_yaml_cache_dir`] that reads environment variables
/// through a caller-supplied closure.
pub fn ensure_yaml_cache_dir_with_env<F>(env: F) -> Result<PathBuf, PathError>
where
    F: Fn(&str) -> Option<String>,
{
    let dir = yaml_cache_dir_with_env(env)?;
    std::fs::create_dir_all(&dir).map_err(|source| PathError::IoError {
        path: dir.clone(),
        source,
    })?;
    Ok(dir)
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
        "neither LOCALAPPDATA nor APPDATA is set; cannot resolve YAML cache directory".into(),
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
        "neither XDG_CACHE_HOME nor HOME is set; cannot resolve YAML cache directory".into(),
    ))
}

/// Read a process env var, returning `None` for unset *or* empty values so that
/// `%LOCALAPPDATA%=""` degrades to the next fallback rather than producing a
/// bogus empty path.
fn process_env_lookup(name: &str) -> Option<String> {
    match std::env::var(name) {
        Ok(s) if !s.is_empty() => Some(s),
        _ => None,
    }
}

#[cfg(test)]
#[path = "yaml_cache_tests.rs"]
mod tests;
