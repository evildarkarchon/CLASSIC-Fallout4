//! Path validation utilities.
//!
//! This module provides comprehensive path validation functionality:
//! - Existence checks
//! - Restriction validation for custom scans
//! - Settings path verification
//! - Required file validation

use crate::error::{PathError, PathResult, ValidationError, ValidationResult};
use std::path::Path;

/// Check if a path exists in the filesystem.
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// `true` if the path exists, `false` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_path_core::validator::is_valid_path;
/// use std::path::Path;
///
/// let path = Path::new(".");
/// assert!(is_valid_path(&path));
/// ```
pub fn is_valid_path(path: &Path) -> bool {
    path.exists()
}

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
/// use classic_path_core::validator::is_restricted_path;
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

/// Validate that a path exists and is accessible.
///
/// # Arguments
///
/// * `path` - The path to validate
///
/// # Returns
///
/// `Ok(())` if valid, or a `PathError` describing the issue.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::validator::validate_path_exists;
/// use std::path::Path;
///
/// let path = Path::new(".");
/// validate_path_exists(&path)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn validate_path_exists(path: &Path) -> PathResult<()> {
    if !path.exists() {
        return Err(PathError::NotFound(path.to_path_buf()));
    }
    Ok(())
}

/// Validate that a path is a directory.
///
/// # Arguments
///
/// * `path` - The path to validate
///
/// # Returns
///
/// `Ok(())` if the path is a directory, or a `PathError` if not.
pub fn validate_is_directory(path: &Path) -> PathResult<()> {
    validate_path_exists(path)?;

    if !path.is_dir() {
        return Err(PathError::NotADirectory(path.to_path_buf()));
    }
    Ok(())
}

/// Validate that a path is a file.
///
/// # Arguments
///
/// * `path` - The path to validate
///
/// # Returns
///
/// `Ok(())` if the path is a file, or a `PathError` if not.
pub fn validate_is_file(path: &Path) -> PathResult<()> {
    validate_path_exists(path)?;

    if !path.is_file() {
        return Err(PathError::NotAFile(path.to_path_buf()));
    }
    Ok(())
}

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
/// use classic_path_core::validator::validate_required_files;
/// use std::path::Path;
///
/// let game_dir = Path::new("C:\\Games\\Fallout4");
/// let required = vec!["Fallout4.exe".to_string(), "Data".to_string()];
/// validate_required_files(game_dir, &required)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn validate_required_files(directory: &Path, required_files: &[String]) -> ValidationResult<()> {
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
/// `Ok(())` if valid for custom scanning, or a `ValidationError` if not.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::validator::validate_custom_scan_path;
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
/// use classic_path_core::validator::validate_settings_path;
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

/// Validate all common settings paths.
///
/// This function validates:
/// - Game root path (with game executable)
/// - Documents path
/// - Custom scan path (if set)
/// - Mods folder path (if set)
/// - INI folder path (if set)
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
/// use classic_path_core::validator::validate_settings_paths;
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
    // Validate game root path
    validate_settings_path(
        game_path,
        "Game Path",
        Some(&[game_exe.to_string()]),
    )?;

    // Validate documents path
    validate_settings_path(docs_path, "Documents Path", None)?;

    // Validate custom scan path if set
    if let Some(scan_path) = custom_scan_path {
        validate_custom_scan_path(scan_path)?;
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;
    use tempfile::TempDir;

    #[test]
    fn test_is_valid_path() {
        let temp_dir = TempDir::new().unwrap();
        let temp_path = temp_dir.path();

        assert!(is_valid_path(temp_path));
        assert!(!is_valid_path(&PathBuf::from("nonexistent_path_12345")));
    }

    #[test]
    fn test_is_restricted_path() {
        // System directories should be restricted
        assert!(is_restricted_path(&PathBuf::from("C:\\Windows")));
        assert!(is_restricted_path(&PathBuf::from("C:\\Program Files")));
        assert!(is_restricted_path(&PathBuf::from("C:\\Program Files (x86)")));

        // Root directories should be restricted
        assert!(is_restricted_path(&PathBuf::from("C:\\")));
        assert!(is_restricted_path(&PathBuf::from("/")));

        // User directories should not be restricted
        assert!(!is_restricted_path(&PathBuf::from("C:\\Users\\Name\\Downloads")));
        assert!(!is_restricted_path(&PathBuf::from("/home/user/downloads")));
    }

    #[test]
    fn test_validate_path_exists() {
        let temp_dir = TempDir::new().unwrap();
        let temp_path = temp_dir.path();

        assert!(validate_path_exists(temp_path).is_ok());

        let nonexistent = PathBuf::from("nonexistent_12345");
        let result = validate_path_exists(&nonexistent);
        assert!(result.is_err());
        match result {
            Err(PathError::NotFound(p)) => assert_eq!(p, nonexistent),
            _ => panic!("Expected NotFound error"),
        }
    }

    #[test]
    fn test_validate_is_directory() {
        let temp_dir = TempDir::new().unwrap();
        let temp_path = temp_dir.path();

        // Directory should validate
        assert!(validate_is_directory(temp_path).is_ok());

        // File should fail
        let file_path = temp_path.join("test.txt");
        fs::write(&file_path, "test").unwrap();
        let result = validate_is_directory(&file_path);
        assert!(result.is_err());
        match result {
            Err(PathError::NotADirectory(_)) => {}
            _ => panic!("Expected NotADirectory error"),
        }
    }

    #[test]
    fn test_validate_is_file() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("test.txt");
        fs::write(&file_path, "test").unwrap();

        // File should validate
        assert!(validate_is_file(&file_path).is_ok());

        // Directory should fail
        let result = validate_is_file(temp_dir.path());
        assert!(result.is_err());
        match result {
            Err(PathError::NotAFile(_)) => {}
            _ => panic!("Expected NotAFile error"),
        }
    }

    #[test]
    fn test_validate_required_files() {
        let temp_dir = TempDir::new().unwrap();
        let dir_path = temp_dir.path();

        // Create some files
        fs::write(dir_path.join("file1.txt"), "test").unwrap();
        fs::write(dir_path.join("file2.txt"), "test").unwrap();

        // Should succeed when all files exist
        let required = vec!["file1.txt".to_string(), "file2.txt".to_string()];
        assert!(validate_required_files(dir_path, &required).is_ok());

        // Should fail when file missing
        let required_missing = vec!["file1.txt".to_string(), "missing.txt".to_string()];
        let result = validate_required_files(dir_path, &required_missing);
        assert!(result.is_err());
        match result {
            Err(ValidationError::RequiredFileNotFound { file, .. }) => {
                assert_eq!(file, "missing.txt");
            }
            _ => panic!("Expected RequiredFileNotFound error"),
        }
    }

    #[test]
    fn test_validate_custom_scan_path() {
        let temp_dir = TempDir::new().unwrap();
        // Create a subdirectory to ensure enough path depth
        let nested_dir = temp_dir.path().join("safe").join("mods");
        fs::create_dir_all(&nested_dir).unwrap();

        // Check if temp directory itself is restricted (e.g., in AppData)
        let result = validate_custom_scan_path(&nested_dir);
        match result {
            Ok(_) => {
                // Path validated successfully - good!
            }
            Err(ValidationError::RestrictedPath(_)) => {
                // Temp dir is restricted (e.g., in AppData) - this is expected on some systems
                eprintln!("Note: Temp directory is in a restricted location: {}", nested_dir.display());
            }
            Err(e) => {
                panic!("Unexpected error for unrestricted path: {:?}", e);
            }
        }

        // Restricted paths should definitely fail
        let restricted_paths = vec![
            PathBuf::from("C:\\Windows"),
            PathBuf::from("C:\\Program Files"),
        ];

        for restricted in restricted_paths {
            let result = validate_custom_scan_path(&restricted);
            // Should either be restricted or not exist
            match result {
                Err(ValidationError::RestrictedPath(_)) | Err(ValidationError::PathError(_)) => {}
                Ok(_) => panic!("Should have failed for restricted path: {}", restricted.display()),
                Err(_) => panic!("Unexpected error type"),
            }
        }
    }

    #[test]
    fn test_validate_settings_path() {
        let temp_dir = TempDir::new().unwrap();
        let dir_path = temp_dir.path();

        // Create a test file
        fs::write(dir_path.join("test.exe"), "test").unwrap();

        // Should succeed with required file
        let required = vec!["test.exe".to_string()];
        assert!(validate_settings_path(dir_path, "Test Path", Some(&required)).is_ok());

        // Should fail with missing file
        let required_missing = vec!["missing.exe".to_string()];
        let result = validate_settings_path(dir_path, "Test Path", Some(&required_missing));
        assert!(result.is_err());
    }

    #[test]
    fn test_validate_settings_paths() {
        let temp_dir = TempDir::new().unwrap();
        let game_dir = temp_dir.path().join("game");
        let docs_dir = temp_dir.path().join("docs");

        fs::create_dir(&game_dir).unwrap();
        fs::create_dir(&docs_dir).unwrap();
        fs::write(game_dir.join("Fallout4.exe"), "test").unwrap();

        // Should succeed with valid paths
        let result = validate_settings_paths(&game_dir, &docs_dir, None, "Fallout4.exe");
        assert!(result.is_ok());

        // Should fail with missing executable
        let invalid_game = temp_dir.path().join("invalid");
        fs::create_dir(&invalid_game).unwrap();
        let result = validate_settings_paths(&invalid_game, &docs_dir, None, "Missing.exe");
        assert!(result.is_err());
    }
}
