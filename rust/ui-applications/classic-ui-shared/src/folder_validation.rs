//! Folder path validation utilities.
//!
//! This module provides cross-platform folder validation functionality
//! for validating user-selected paths before using them in the application.
//!
//! # Examples
//!
//! ```no_run
//! use std::path::PathBuf;
//! use classic_ui_shared::folder_validation::{validate_folder_path, FolderValidationResult};
//!
//! let path = PathBuf::from("C:\\Games\\Fallout4\\Data");
//! match validate_folder_path(&path, false) {
//!     FolderValidationResult::Valid => println!("Path is valid"),
//!     FolderValidationResult::Invalid(reason) => println!("Invalid: {}", reason),
//!     FolderValidationResult::Empty => println!("No path provided"),
//! }
//! ```

use std::path::Path;

/// Result of folder path validation
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FolderValidationResult {
    /// Path is valid and can be used
    Valid,
    /// Path is empty (only valid if `allow_empty` is true)
    Empty,
    /// Path is invalid with a specific reason
    Invalid(String),
}

impl FolderValidationResult {
    /// Check if the validation result indicates a valid path
    pub fn is_valid(&self) -> bool {
        matches!(self, FolderValidationResult::Valid)
    }

    /// Check if the validation result indicates an empty path
    pub fn is_empty(&self) -> bool {
        matches!(self, FolderValidationResult::Empty)
    }

    /// Check if the validation result indicates an invalid path
    pub fn is_invalid(&self) -> bool {
        matches!(self, FolderValidationResult::Invalid(_))
    }

    /// Get the error message if the path is invalid
    pub fn error_message(&self) -> Option<&str> {
        match self {
            FolderValidationResult::Invalid(msg) => Some(msg),
            _ => None,
        }
    }

    /// Convert to Result type for error handling
    pub fn into_result(self) -> anyhow::Result<()> {
        match self {
            FolderValidationResult::Valid | FolderValidationResult::Empty => Ok(()),
            FolderValidationResult::Invalid(reason) => Err(anyhow::anyhow!(reason)),
        }
    }
}

/// Validate that a folder path is suitable for use.
///
/// This function performs comprehensive validation including:
/// - Checking if the path is empty (and if that's allowed)
/// - Verifying the path exists
/// - Confirming the path is a directory
/// - Testing read permissions
///
/// # Arguments
///
/// * `path` - Path to validate
/// * `allow_empty` - Whether empty paths are considered valid (useful for optional fields)
///
/// # Returns
///
/// Returns a [`FolderValidationResult`] indicating the validation outcome.
///
/// # Examples
///
/// ```no_run
/// use std::path::PathBuf;
/// use classic_ui_shared::folder_validation::validate_folder_path;
///
/// let path = PathBuf::from("/valid/directory");
/// let result = validate_folder_path(&path, false);
/// assert!(result.is_valid());
///
/// // Empty paths can be allowed
/// let empty_path = PathBuf::from("");
/// let result = validate_folder_path(&empty_path, true);
/// assert!(result.is_empty());
/// ```
pub fn validate_folder_path<P: AsRef<Path>>(path: P, allow_empty: bool) -> FolderValidationResult {
    let path = path.as_ref();

    // Convert path to string for empty check
    let path_str = path.to_string_lossy();

    // Check if path is empty
    if path_str.is_empty() {
        return if allow_empty {
            FolderValidationResult::Empty
        } else {
            FolderValidationResult::Invalid("Path cannot be empty".to_string())
        };
    }

    // Check if path exists
    if !path.exists() {
        return FolderValidationResult::Invalid(format!("Path does not exist: {}", path.display()));
    }

    // Check if path is a directory
    if !path.is_dir() {
        return FolderValidationResult::Invalid(format!(
            "Path is not a directory: {}",
            path.display()
        ));
    }

    // Check if path is readable by attempting to read the directory
    match std::fs::read_dir(path) {
        Ok(_) => FolderValidationResult::Valid,
        Err(e) => FolderValidationResult::Invalid(format!(
            "Cannot read directory {}: {}",
            path.display(),
            e
        )),
    }
}

/// Validate a folder path and return a Result for error handling.
///
/// This is a convenience wrapper around [`validate_folder_path`] that returns
/// a standard `Result` type for easier integration with error handling code.
///
/// # Arguments
///
/// * `path` - Path to validate
/// * `allow_empty` - Whether empty paths are considered valid
///
/// # Returns
///
/// Returns `Ok(())` if valid, or an error with a descriptive message.
///
/// # Examples
///
/// ```no_run
/// use std::path::PathBuf;
/// use classic_ui_shared::folder_validation::validate_folder_path_result;
///
/// let path = PathBuf::from("/valid/directory");
/// validate_folder_path_result(&path, false)?;
/// # Ok::<(), anyhow::Error>(())
/// ```
///
/// # Errors
///
/// Returns an error if:
/// - Path is empty and `allow_empty` is false
/// - Path does not exist
/// - Path is not a directory
/// - Path is not readable
pub fn validate_folder_path_result<P: AsRef<Path>>(
    path: P,
    allow_empty: bool,
) -> anyhow::Result<()> {
    validate_folder_path(path, allow_empty).into_result()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_validate_empty_path_allowed() {
        let path = PathBuf::from("");
        let result = validate_folder_path(&path, true);
        assert!(result.is_empty());
        assert!(!result.is_invalid());
    }

    #[test]
    fn test_validate_empty_path_disallowed() {
        let path = PathBuf::from("");
        let result = validate_folder_path(&path, false);
        assert!(result.is_invalid());
        assert!(result.error_message().unwrap().contains("cannot be empty"));
    }

    #[test]
    fn test_validate_nonexistent_path() {
        let path = PathBuf::from("/this/path/should/not/exist/hopefully/12345");
        let result = validate_folder_path(&path, false);
        assert!(result.is_invalid());
        assert!(result.error_message().unwrap().contains("does not exist"));
    }

    #[test]
    fn test_validate_file_not_directory() {
        use std::fs::File;
        use tempfile::tempdir;

        let dir = tempdir().expect("Failed to create temp dir");
        let file_path = dir.path().join("test_file.txt");
        File::create(&file_path).expect("Failed to create test file");

        let result = validate_folder_path(&file_path, false);
        assert!(result.is_invalid());
        assert!(result.error_message().unwrap().contains("not a directory"));
    }

    #[test]
    fn test_validate_valid_directory() {
        use tempfile::tempdir;

        let dir = tempdir().expect("Failed to create temp dir");
        let result = validate_folder_path(dir.path(), false);
        assert!(result.is_valid());
    }

    #[test]
    fn test_validate_folder_path_result() {
        use tempfile::tempdir;

        let dir = tempdir().expect("Failed to create temp dir");
        let result = validate_folder_path_result(dir.path(), false);
        assert!(result.is_ok());

        let invalid_path = PathBuf::from("/this/does/not/exist");
        let result = validate_folder_path_result(&invalid_path, false);
        assert!(result.is_err());
    }

    #[test]
    fn test_validation_result_methods() {
        let valid = FolderValidationResult::Valid;
        assert!(valid.is_valid());
        assert!(!valid.is_empty());
        assert!(!valid.is_invalid());
        assert!(valid.error_message().is_none());

        let empty = FolderValidationResult::Empty;
        assert!(!empty.is_valid());
        assert!(empty.is_empty());
        assert!(!empty.is_invalid());
        assert!(empty.error_message().is_none());

        let invalid = FolderValidationResult::Invalid("test error".to_string());
        assert!(!invalid.is_valid());
        assert!(!invalid.is_empty());
        assert!(invalid.is_invalid());
        assert_eq!(invalid.error_message(), Some("test error"));
    }
}
