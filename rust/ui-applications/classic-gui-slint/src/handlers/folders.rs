// Folder selection handlers
use anyhow::Result;
use classic_ui_shared::folder_validation;
use rfd::FileDialog;
use std::path::{Path, PathBuf};

/// Opens a native folder browser dialog for selecting the mods folder
///
/// # Returns
/// Returns the selected folder path, or None if the user cancelled
pub fn browse_mods_folder() -> Result<Option<PathBuf>> {
    tracing::info!("Opening mods folder browser...");

    // Open native folder picker dialog
    let result = FileDialog::new()
        .set_title("Select Staging Mods Folder")
        .pick_folder();

    if let Some(path) = &result {
        tracing::info!("Mods folder selected: {}", path.display());
    } else {
        tracing::debug!("Mods folder selection cancelled");
    }

    Ok(result)
}

/// Opens a native folder browser dialog for selecting the custom scan folder
///
/// # Returns
/// Returns the selected folder path, or None if the user cancelled
pub fn browse_scan_folder() -> Result<Option<PathBuf>> {
    tracing::info!("Opening scan folder browser...");

    // Open native folder picker dialog
    let result = FileDialog::new()
        .set_title("Select Custom Scan Folder")
        .pick_folder();

    if let Some(path) = &result {
        tracing::info!("Scan folder selected: {}", path.display());
    } else {
        tracing::debug!("Scan folder selection cancelled");
    }

    Ok(result)
}

/// Validates a folder path (wrapper around shared validation).
///
/// This is a convenience wrapper that allows empty paths (for optional fields).
///
/// # Arguments
/// * `path` - The folder path to validate (as string)
///
/// # Returns
/// Returns true if the path is valid or empty, false otherwise
#[allow(dead_code)]
pub fn validate_folder_path(path: &str) -> bool {
    if path.is_empty() {
        return true; // Empty paths are valid (optional fields)
    }

    let path = Path::new(path);
    folder_validation::validate_folder_path(path, true).is_valid()
}
