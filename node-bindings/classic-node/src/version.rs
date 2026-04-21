//! Version parsing and comparison bindings (classic-version-core)
//!
//! Exposes version parsing, comparison, extraction, and formatting functions
//! to JavaScript/TypeScript. All business logic is delegated to `classic_version_core`.
//!
//! The core crate works with `semver::Version` objects internally; this binding layer
//! converts between JS strings and `Version` at the boundary.

use napi::bindgen_prelude::*;

/// Convert a VersionError to a napi::Error
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// Parse and normalize a version string.
///
/// Accepts formats like "1.10.163", "v1.10.163", "1.10.163.0".
/// The fourth component (build number) is dropped if present.
///
/// @throws if the input is not a valid version string.
#[napi]
pub fn parse_version(input: String) -> Result<String> {
    let version = classic_version_core::parse_version(&input).map_err(to_napi_err)?;
    Ok(version.to_string())
}

/// Try to parse a version string, returning null on failure.
///
/// Non-throwing variant of `parseVersion`.
#[napi]
pub fn try_parse_version(input: String) -> Option<String> {
    classic_version_core::try_parse_version(&input).map(|v| v.to_string())
}

/// Compare two version strings.
///
/// Returns -1 if a < b, 0 if a == b, 1 if a > b.
///
/// @throws if either version string is invalid.
#[napi]
pub fn compare_versions(a: String, b: String) -> Result<i32> {
    let va = classic_version_core::parse_version(&a).map_err(to_napi_err)?;
    let vb = classic_version_core::parse_version(&b).map_err(to_napi_err)?;
    let ord = classic_version_core::compare_versions(&va, &vb);
    Ok(match ord {
        std::cmp::Ordering::Less => -1,
        std::cmp::Ordering::Equal => 0,
        std::cmp::Ordering::Greater => 1,
    })
}

/// Check whether a version string matches a known Fallout 4 game version.
///
/// @throws if the version string is invalid.
#[napi]
pub fn is_known_fallout4_version(version: String) -> Result<bool> {
    let v = classic_version_core::parse_version(&version).map_err(to_napi_err)?;
    Ok(classic_version_core::is_known_fallout4_version(&v))
}

/// Extract a version from a filename.
///
/// Recognizes patterns like "MyMod-v1.2.3.esp", "MyMod_1.2.3.esp", etc.
/// Returns the version string, or null if no version is found.
#[napi]
pub fn extract_version_from_filename(filename: String) -> Option<String> {
    classic_version_core::extract_version_from_filename(&filename).map(|v| v.to_string())
}

/// Extract the first version from log file content.
///
/// Looks for patterns like "version: 1.2.3", "v1.2.3", "Version 1.2.3.4".
/// Returns the version string, or null if no version is found.
#[napi]
pub fn extract_version_from_log(content: String) -> Option<String> {
    classic_version_core::extract_version_from_log(&content).map(|v| v.to_string())
}

/// Find all version strings in the given content.
///
/// Returns an array of normalized version strings.
#[napi]
pub fn extract_all_versions(content: String) -> Vec<String> {
    classic_version_core::extract_all_versions(&content)
        .into_iter()
        .map(|v| v.to_string())
        .collect()
}

/// Pretty-print a version string (parse then format without prefix).
///
/// @throws if the version string is invalid.
#[napi]
pub fn format_version(version: String) -> Result<String> {
    let v = classic_version_core::parse_version(&version).map_err(to_napi_err)?;
    Ok(classic_version_core::format_version(&v, None))
}

// ============================================================================
// PE Version Extraction
// ============================================================================

use std::path::Path;

/// PE file version components (4-part file version from VS_VERSIONINFO).
///
/// Returned by `extractPeVersion`. All fields are `u16` in the underlying Rust
/// crate but widened to `u32` for NAPI convention. JavaScript receives plain numbers.
#[napi(object)]
pub struct JsPeVersion {
    pub major: u32,
    pub minor: u32,
    pub patch: u32,
    pub build: u32,
}

/// Extract a PE file's version from its VS_VERSIONINFO resource.
///
/// Accepts `.exe` and `.dll` files. Delegates to
/// `classic_version_core::pe_version::extract_pe_version`.
///
/// @param path  Filesystem path to a PE file (absolute or relative).
/// @returns     Object `{ major, minor, patch, build }`.
/// @throws      napi::Error if the path is not a valid PE file, the file
///              cannot be read, or no version resource is present.
#[napi]
pub fn extract_pe_version(path: String) -> Result<JsPeVersion> {
    let (major, minor, patch, build) =
        classic_version_core::pe_version::extract_pe_version(Path::new(&path))
            .map_err(to_napi_err)?;
    Ok(JsPeVersion {
        major: u32::from(major),
        minor: u32::from(minor),
        patch: u32::from(patch),
        build: u32::from(build),
    })
}

/// Check whether a path points to a valid executable or DLL file.
///
/// Delegates to `classic_version_core::pe_version::is_valid_executable_path`.
/// Never throws — returns `false` for unreadable, non-existent, or
/// wrong-extension paths.
///
/// @param path  Filesystem path to check.
/// @returns     `true` if the path exists, is a file, and ends in `.exe` or `.dll`.
#[napi]
pub fn is_valid_pe_path(path: String) -> bool {
    classic_version_core::pe_version::is_valid_executable_path(Path::new(&path))
}
