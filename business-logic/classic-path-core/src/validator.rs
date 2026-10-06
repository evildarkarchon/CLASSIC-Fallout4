//! Path validation utilities.
//!
//! This module provides comprehensive path validation functionality:
//! - Settings path verification (Game and Documents paths)
//! - Required file validation
//!
//! Custom-scan folder policy (restricted-path rejection and custom-scan path
//! validation) is owned by `classic_scanlog_core::custom_scan` (#254
//! follow-up); path core does not re-export it.
//!
//! The generic existence, kind, permission, drive, and read-only primitives
//! these checks build on live in `classic_shared_core::path_core`.

use crate::error::{ValidationError, ValidationResult};
use classic_shared_core::path_core::validate_is_directory;
use std::path::Path;

/// Validate that required files exist in a directory.
///
/// # Arguments
///
/// * `directory` - The directory to check
/// * `required_files` - List of file names that must exist
///
/// # Returns
///
/// `Ok(())` if all required files exist, or a `ValidationError` if any are missing.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::validate_required_files;
/// use std::path::Path;
///
/// let game_dir = Path::new("C:\\Games\\Fallout4");
/// let required = vec!["Fallout4.exe".to_string(), "Data".to_string()];
/// validate_required_files(game_dir, &required)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn validate_required_files(
    directory: &Path,
    required_files: &[String],
) -> ValidationResult<()> {
    validate_is_directory(directory)?;

    for file_name in required_files {
        let file_path = directory.join(file_name);
        if !file_path.exists() {
            return Err(ValidationError::RequiredFileNotFound {
                path: directory.to_path_buf(),
                file: file_name.clone(),
            });
        }
    }

    Ok(())
}

/// Validate a settings path with optional required files.
///
/// This is a comprehensive validation function that:
/// 1. Checks if the path exists
/// 2. Validates it's a directory (if required files specified)
/// 3. Checks for required files if specified
///
/// # Arguments
///
/// * `path` - The path to validate
/// * `setting_name` - Name of the setting (for error messages)
/// * `required_files` - Optional list of required file names
///
/// # Returns
///
/// `Ok(())` if valid, or a `ValidationError` describing the issue.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::validate_settings_path;
/// use std::path::Path;
///
/// let game_path = Path::new("C:\\Games\\Fallout4");
/// let required = Some(vec!["Fallout4.exe".to_string()]);
/// validate_settings_path(game_path, "Game Path", required.as_deref())?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn validate_settings_path(
    path: &Path,
    setting_name: &str,
    required_files: Option<&[String]>,
) -> ValidationResult<()> {
    // Check existence
    if !path.exists() {
        return Err(ValidationError::ValidationFailed {
            setting: setting_name.to_string(),
            reason: format!("Path does not exist: {}", path.display()),
        });
    }

    // If required files specified, validate directory and files
    if let Some(files) = required_files {
        validate_is_directory(path)?;
        validate_required_files(path, files)?;
    }

    Ok(())
}

/// Validate the Game and Documents settings paths.
///
/// Checks, in order:
/// 1. The game root path exists, is a directory, and contains `game_exe`
///    (reported under the "Game Path" setting name)
/// 2. The documents path exists (reported under the "Documents Path" setting name)
///
/// Custom-scan folder policy is not part of path core: the combined
/// settings-path check that also validates a custom scan folder is
/// `classic_scanlog_core::validate_settings_paths`, which calls this first.
///
/// # Arguments
///
/// * `game_path` - Game installation path to validate
/// * `docs_path` - Documents folder path to validate
/// * `game_exe` - Game executable name (e.g., "Fallout4.exe")
///
/// # Returns
///
/// `Ok(())` if both paths are valid, or the first `ValidationError` encountered.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::validate_game_and_documents_paths;
/// use std::path::PathBuf;
///
/// let game = PathBuf::from("C:\\Games\\Fallout4");
/// let docs = PathBuf::from("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
/// validate_game_and_documents_paths(&game, &docs, "Fallout4.exe")?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn validate_game_and_documents_paths(
    game_path: &Path,
    docs_path: &Path,
    game_exe: &str,
) -> ValidationResult<()> {
    // Validate game root path
    validate_settings_path(game_path, "Game Path", Some(&[game_exe.to_string()]))?;

    // Validate documents path
    validate_settings_path(docs_path, "Documents Path", None)?;

    Ok(())
}

#[cfg(test)]
#[path = "validator_tests.rs"]
mod tests;
