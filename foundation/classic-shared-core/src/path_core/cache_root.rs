//! Per-user OS cache-root resolution.
//!
//! CLASSIC keeps per-user caches (the updated-YAML cache and the
//! app-notification cache) under one platform cache root. This module owns only
//! that root; each cache owner joins its own `CLASSIC/<cache>` subdirectories
//! and words its own error when the root cannot be resolved.
//!
//! # Location
//!
//! - **Windows** — `%LOCALAPPDATA%`, falling back to `%APPDATA%` when
//!   `LOCALAPPDATA` is not set (unusual but possible on stripped-down Windows
//!   environments).
//! - **Other targets (source portability)** — `${XDG_CACHE_HOME:-$HOME/.cache}`.
//!   This keeps the Rust workspace cross-compilable even though shipped
//!   binaries are Windows-only.
//!
//! # Testing
//!
//! The env-lookup seam is factored through [`user_cache_root_with_env`] so unit
//! tests can drive the resolver with a mocked environment without mutating
//! process-wide env (which is `unsafe` in edition 2024 and forbidden by this
//! crate's `unsafe_code = "deny"` lint).

use std::path::PathBuf;
use thiserror::Error;

/// Neither of the platform's cache-root environment variables is set.
///
/// `Display` names both variables (for example
/// `neither LOCALAPPDATA nor APPDATA is set`); cache owners append their own
/// context so existing error messages stay byte-identical.
#[derive(Error, Debug, Clone, Copy, PartialEq, Eq)]
#[error("neither {primary} nor {fallback} is set")]
pub struct CacheRootUnavailable {
    primary: &'static str,
    fallback: &'static str,
}

/// Resolve the per-user OS cache root from the process environment.
///
/// Pure resolution: the directory is neither created nor checked for
/// existence.
///
/// # Errors
///
/// Returns [`CacheRootUnavailable`] when neither platform variable is set to a
/// non-empty value.
pub fn user_cache_root() -> Result<PathBuf, CacheRootUnavailable> {
    user_cache_root_with_env(non_empty_env_var)
}

/// Testable form of [`user_cache_root`] that reads environment variables
/// through a caller-supplied closure.
///
/// The closure should return `None` for unset *or empty* variables, as
/// [`non_empty_env_var`] does; unit tests typically pass a closure backed by a
/// `HashMap`.
///
/// # Errors
///
/// Returns [`CacheRootUnavailable`] when the closure reports neither platform
/// variable.
#[cfg(target_os = "windows")]
pub fn user_cache_root_with_env<F>(env: F) -> Result<PathBuf, CacheRootUnavailable>
where
    F: Fn(&str) -> Option<String>,
{
    if let Some(local) = env("LOCALAPPDATA") {
        return Ok(PathBuf::from(local));
    }
    if let Some(roaming) = env("APPDATA") {
        return Ok(PathBuf::from(roaming));
    }
    Err(CacheRootUnavailable {
        primary: "LOCALAPPDATA",
        fallback: "APPDATA",
    })
}

/// Testable form of [`user_cache_root`] that reads environment variables
/// through a caller-supplied closure.
///
/// The closure should return `None` for unset *or empty* variables, as
/// [`non_empty_env_var`] does; unit tests typically pass a closure backed by a
/// `HashMap`.
///
/// # Errors
///
/// Returns [`CacheRootUnavailable`] when the closure reports neither platform
/// variable.
#[cfg(not(target_os = "windows"))]
pub fn user_cache_root_with_env<F>(env: F) -> Result<PathBuf, CacheRootUnavailable>
where
    F: Fn(&str) -> Option<String>,
{
    if let Some(xdg) = env("XDG_CACHE_HOME") {
        return Ok(PathBuf::from(xdg));
    }
    if let Some(home) = env("HOME") {
        return Ok(PathBuf::from(home).join(".cache"));
    }
    Err(CacheRootUnavailable {
        primary: "XDG_CACHE_HOME",
        fallback: "HOME",
    })
}

/// Read a process env var, returning `None` for unset *or* empty values so that
/// `%LOCALAPPDATA%=""` degrades to the next fallback rather than producing a
/// bogus empty path.
pub fn non_empty_env_var(name: &str) -> Option<String> {
    match std::env::var(name) {
        Ok(s) if !s.is_empty() => Some(s),
        _ => None,
    }
}

#[cfg(test)]
#[path = "cache_root_tests.rs"]
mod tests;
