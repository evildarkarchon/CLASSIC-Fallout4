//! Custom-scan folder policy.
//!
//! The custom-scan folder is an extra Crash Log discovery root, so the rule
//! for which folders a user may point it at belongs to the Crash Log Scan Run
//! owner. This module decides restricted-path rejection and custom-scan path
//! validation, and composes path core's Game/Documents settings checks with
//! that policy for the combined settings-path check.
//!
//! The policy moved here from `classic-path-core` (#254 follow-up); path core
//! keeps only Game and Documents path behavior and does not re-export these
//! functions. Failures keep path core's typed
//! [`ValidationError`](classic_path_core::ValidationError) values — including
//! `RestrictedPath` and its message — so every binding error projection stays
//! the same.

use classic_path_core::{ValidationError, ValidationResult, validate_game_and_documents_paths};
use classic_shared_core::path_core::validate_is_directory;
use std::path::Path;

/// Check if a path is restricted for custom scans.
///
/// Restricted paths include:
/// - Game installation directory
/// - Documents folder
/// - System directories
/// - Root directories
///
/// This prevents users from accidentally scanning sensitive or system directories.
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// `true` if the path is restricted, `false` if it's safe for custom scans.
///
/// # Examples
///
/// ```rust
/// use classic_scanlog_core::is_restricted_path;
/// use std::path::Path;
///
/// let safe_path = Path::new("C:\\Users\\Name\\Downloads\\Mods");
/// assert!(!is_restricted_path(&safe_path));
///
/// let restricted = Path::new("C:\\Windows");
/// assert!(is_restricted_path(&restricted));
/// ```
pub fn is_restricted_path(path: &Path) -> bool {
    let path_str = path.to_string_lossy().to_lowercase();

    // Check for system directories
    let restricted_patterns = [
        "windows",
        "program files",
        "program files (x86)",
        "programdata",
        "system32",
        "syswow64",
        "appdata",
    ];

    for pattern in &restricted_patterns {
        if path_str.contains(pattern) {
            return true;
        }
    }

    // Check if it's a root directory (e.g., C:\, D:\, /)
    if path.parent().is_none() || path.components().count() <= 2 {
        return true;
    }

    false
}

/// Validate a custom scan path.
///
/// Ensures the path exists, is a directory, and is not restricted.
///
/// # Arguments
///
/// * `path` - The path to validate for custom scanning
///
/// # Returns
///
/// `Ok(())` if valid for custom scanning, or a `ValidationError` if not:
/// `PathError` when the path is missing or not a directory, otherwise
/// `RestrictedPath` when [`is_restricted_path`] rejects it.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_scanlog_core::validate_custom_scan_path;
/// use std::path::Path;
///
/// let scan_path = Path::new("C:\\Users\\Name\\Downloads\\Mods");
/// validate_custom_scan_path(scan_path)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn validate_custom_scan_path(path: &Path) -> ValidationResult<()> {
    validate_is_directory(path)?;

    if is_restricted_path(path) {
        return Err(ValidationError::RestrictedPath(path.to_path_buf()));
    }

    Ok(())
}

/// Validate all common settings paths.
///
/// This function validates, in order:
/// - Game root path (with game executable) and Documents path, through
///   `classic_path_core::validate_game_and_documents_paths`
/// - Custom scan path (if set), through [`validate_custom_scan_path`]
///
/// **Note**: This function requires external configuration to get the actual paths
/// and settings. In the Rust-only context, you'd pass these as parameters. When
/// called from Python, the Python layer handles loading settings from YAML.
///
/// # Arguments
///
/// * `game_path` - Game installation path to validate
/// * `docs_path` - Documents folder path to validate
/// * `custom_scan_path` - Optional custom scan path
/// * `game_exe` - Game executable name (e.g., "Fallout4.exe")
///
/// # Returns
///
/// `Ok(())` if all paths are valid, or the first `ValidationError` encountered.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_scanlog_core::validate_settings_paths;
/// use std::path::PathBuf;
///
/// let game = PathBuf::from("C:\\Games\\Fallout4");
/// let docs = PathBuf::from("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
/// validate_settings_paths(&game, &docs, None, "Fallout4.exe")?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn validate_settings_paths(
    game_path: &Path,
    docs_path: &Path,
    custom_scan_path: Option<&Path>,
    game_exe: &str,
) -> ValidationResult<()> {
    // Game and Documents rules stay with path core and run first, so their
    // failures keep precedence over the custom-scan policy as before the move.
    validate_game_and_documents_paths(game_path, docs_path, game_exe)?;

    // Validate custom scan path if set
    if let Some(scan_path) = custom_scan_path {
        validate_custom_scan_path(scan_path)?;
    }

    Ok(())
}

#[cfg(test)]
#[path = "custom_scan_tests.rs"]
mod tests;
