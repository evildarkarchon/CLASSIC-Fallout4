//! Windows-specific path operations.
//!
//! This module provides Windows registry access for:
//! - Game installation paths (Bethesda, Steam, GOG)
//! - System documents folder detection

use crate::error::{
    DocsPathError, DocsPathResult, GamePathError, GamePathResult, PathError, PathResult,
};
use std::fs;
use std::path::{Path, PathBuf};
use winreg::RegKey;
use winreg::enums::*;

/// Query Windows registry for game installation path.
///
/// Searches multiple registry locations for game installations:
/// 1. Bethesda launcher: `HKLM\SOFTWARE\WOW6432Node\Bethesda Softworks\{Game}{VR}`
/// 2. Steam: `HKLM\SOFTWARE\WOW6432Node\Bethesda Softworks\{Game}{VR}`
/// 3. GOG: `HKLM\SOFTWARE\WOW6432Node\GOG.com\Games\1998527297` (Fallout 4)
///
/// # Arguments
///
/// * `game_name` - Game name for registry key (e.g., "Fallout4", "Skyrim")
/// * `vr_suffix` - VR suffix if applicable (e.g., " VR", empty string for non-VR)
/// * `try_gog` - Whether to try GOG registry as fallback
///
/// # Returns
///
/// The game installation path from registry, or an error if not found.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::query_game_registry;
///
/// // Find Fallout 4
/// let game_path = query_game_registry("Fallout4", "", true)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn query_game_registry(
    game_name: &str,
    vr_suffix: &str,
    try_gog: bool,
) -> GamePathResult<PathBuf> {
    // Try Bethesda/Steam registry
    let registry_path = format!(
        "SOFTWARE\\WOW6432Node\\Bethesda Softworks\\{}{}",
        game_name, vr_suffix
    );
    let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);

    if let Ok(path) = query_registry_path(&hklm, &registry_path, "installed path") {
        return Ok(path);
    }

    // Try GOG registry if enabled (Fallout 4 only)
    if try_gog && game_name == "Fallout4" {
        let gog_path = "SOFTWARE\\WOW6432Node\\GOG.com\\Games\\1998527297";
        if let Ok(path) = query_registry_path(&hklm, gog_path, "path") {
            return Ok(path);
        }
    }

    Err(GamePathError::RegistryNotFound)
}

/// Get the Windows documents folder path from registry.
///
/// Queries the Windows Shell Folders registry key for the "Personal" folder,
/// which corresponds to the user's Documents folder.
///
/// # Returns
///
/// The system documents path, or an error if registry query failed.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::get_system_documents_path;
///
/// let docs = get_system_documents_path()?;
/// println!("Documents: {}", docs.display());
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn get_documents_path() -> DocsPathResult<PathBuf> {
    let registry_path = "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders";
    let hkcu = RegKey::predef(HKEY_CURRENT_USER);

    query_registry_path(&hkcu, registry_path, "Personal")
        .map_err(|e| DocsPathError::RegistryError(e.to_string()))
}

/// Helper function to query a registry key for a string value.
///
/// # Arguments
///
/// * `hkey` - Registry hive reference (from RegKey::predef)
/// * `path` - Registry key path
/// * `value_name` - Name of the value to query
///
/// # Returns
///
/// The string value as a PathBuf, or a GamePathError if not found.
fn query_registry_path(hkey: &RegKey, path: &str, value_name: &str) -> GamePathResult<PathBuf> {
    let key = hkey.open_subkey_with_flags(path, KEY_READ).map_err(|e| {
        GamePathError::RegistryError(format!("Failed to open key '{}': {}", path, e))
    })?;

    let value: String = key.get_value(value_name).map_err(|e| {
        GamePathError::RegistryError(format!(
            "Failed to read value '{}' from '{}': {}",
            value_name, path, e
        ))
    })?;

    Ok(PathBuf::from(value))
}

/// Remove the read-only attribute from a file or directory (Windows only).
///
/// This function modifies the file permissions to remove the read-only flag.
/// If the operation fails (e.g., due to permissions), it logs a warning but
/// does not fail - this is a best-effort operation.
///
/// # Arguments
///
/// * `file_path` - Path to the file or directory
///
/// # Returns
///
/// `Ok(())` if successful or if the operation is not needed.
/// Returns an error only for serious filesystem errors (optional logging can be added).
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::remove_readonly;
/// use std::path::Path;
///
/// let file = Path::new("C:\\Games\\Fallout4\\Fallout4.ini");
/// remove_readonly(file)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
#[allow(clippy::permissions_set_readonly_false)]
pub fn remove_readonly(file_path: &Path) -> PathResult<()> {
    // Get current permissions
    let metadata = fs::metadata(file_path).map_err(|e| PathError::IoError {
        path: file_path.to_path_buf(),
        source: e,
    })?;

    let mut permissions = metadata.permissions();

    // Check if read-only bit is set
    if permissions.readonly() {
        // Clear the read-only flag
        permissions.set_readonly(false);

        // Apply the modified permissions
        fs::set_permissions(file_path, permissions).map_err(|e| {
            // Log warning to stderr - this is best-effort
            eprintln!(
                "Warning: Could not remove read-only attribute from {}: {}",
                file_path.display(),
                e
            );
            PathError::PermissionDenied(format!(
                "Failed to remove read-only attribute from {}: {}",
                file_path.display(),
                e
            ))
        })?;
    }

    Ok(())
}

#[cfg(test)]
#[path = "windows_tests.rs"]
mod tests;
