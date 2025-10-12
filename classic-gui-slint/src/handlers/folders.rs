// Folder selection handlers
use anyhow::Result;
use rfd::FileDialog;
use std::path::PathBuf;

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

/// Validates a folder path
///
/// # Arguments
/// * `path` - The folder path to validate
///
/// # Returns
/// Returns true if the path exists and is a directory
pub fn validate_folder_path(path: &str) -> bool {
    if path.is_empty() {
        return true; // Empty paths are valid (optional fields)
    }

    let path = PathBuf::from(path);
    path.exists() && path.is_dir()
}
