//! Folder selection handler for managing folder pickers
//!
//! This module handles folder selection interactions, including:
//! - Managing folder picker state
//! - Saving selected paths to configuration
//! - Validating folder paths
//! - Persisting configuration to YAML

use crate::app::App;
use crate::widgets::FolderPickerState;
use anyhow::Result;
use classic_ui_shared::folder_validation::validate_folder_path_result;
use std::path::PathBuf;

/// Type of folder being selected
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FolderType {
    /// Staging mods folder
    Staging,
    /// Custom scan folder
    Custom,
}

/// Handle folder selection and save to configuration
///
/// # Arguments
///
/// * `app` - Application state containing configuration
/// * `folder_type` - Type of folder being selected (Staging or Custom)
/// * `selected_path` - The path that was selected
///
/// # Returns
///
/// Result indicating success or error message
///
/// # Errors
///
/// Returns error if:
/// - Path validation fails
/// - Configuration save fails
/// - Path does not exist or is not a directory
pub async fn handle_folder_selection(
    app: &mut App,
    folder_type: FolderType,
    selected_path: PathBuf,
) -> Result<()> {
    // Validate the path
    validate_folder_path(&selected_path)?;

    // Update app state based on folder type
    match folder_type {
        FolderType::Staging => {
            app.set_staging_folder(selected_path.clone());
            app.add_output(format!(
                "Staging folder updated: {}",
                selected_path.display()
            ));
        }
        FolderType::Custom => {
            app.set_custom_folder(selected_path.clone());
            app.add_output(format!(
                "Custom scan folder updated: {}",
                selected_path.display()
            ));
        }
    }

    // Save configuration to YAML
    app.save_config().await?;

    Ok(())
}

/// Validate that a folder path is suitable for use.
///
/// This is a wrapper around [`classic_ui_shared::folder_validation::validate_folder_path_result`].
///
/// # Arguments
///
/// * `path` - Path to validate
///
/// # Returns
///
/// Result indicating success or error with descriptive message
///
/// # Errors
///
/// Returns error if:
/// - Path does not exist
/// - Path is not a directory
/// - Path is not readable
///
/// # Examples
///
/// ```no_run
/// use std::path::PathBuf;
/// use classic_tui::handlers::folder_handler::validate_folder_path;
///
/// let path = PathBuf::from("/valid/directory");
/// assert!(validate_folder_path(&path).is_ok());
/// ```
pub fn validate_folder_path(path: &PathBuf) -> Result<()> {
    validate_folder_path_result(path, false)
}

/// Create folder picker state for a given folder type
///
/// # Arguments
///
/// * `app` - Application state
/// * `folder_type` - Type of folder to create picker for
///
/// # Returns
///
/// Folder picker state initialized with the current path for that folder type
#[allow(dead_code)]
pub fn create_picker_for_folder(app: &App, folder_type: FolderType) -> FolderPickerState {
    let start_dir = match folder_type {
        FolderType::Staging => app.staging_folder.clone(),
        FolderType::Custom => app.custom_folder.clone(),
    };

    FolderPickerState::new(start_dir)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_validate_existing_directory() {
        let temp_dir = TempDir::new().unwrap();
        let result = validate_folder_path(&temp_dir.path().to_path_buf());
        assert!(result.is_ok());
    }

    #[test]
    fn test_validate_nonexistent_path() {
        let path = PathBuf::from("/nonexistent/path/that/should/not/exist");
        let result = validate_folder_path(&path);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("does not exist"));
    }

    #[test]
    fn test_validate_file_not_directory() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("test_file.txt");
        fs::write(&file_path, "test").unwrap();

        let result = validate_folder_path(&file_path);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("not a directory"));
    }

    #[test]
    fn test_folder_type_equality() {
        assert_eq!(FolderType::Staging, FolderType::Staging);
        assert_eq!(FolderType::Custom, FolderType::Custom);
        assert_ne!(FolderType::Staging, FolderType::Custom);
    }

    #[test]
    fn test_create_picker_for_staging() {
        let app = App::new();
        let picker = create_picker_for_folder(&app, FolderType::Staging);
        // Should create picker without panicking
        assert!(!picker.is_active());
    }

    #[test]
    fn test_create_picker_for_custom() {
        let app = App::new();
        let picker = create_picker_for_folder(&app, FolderType::Custom);
        // Should create picker without panicking
        assert!(!picker.is_active());
    }
}
