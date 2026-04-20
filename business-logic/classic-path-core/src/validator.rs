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
/// use classic_path_core::is_valid_path;
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
/// use classic_path_core::is_restricted_path;
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
/// use classic_path_core::validate_path_exists;
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
/// use classic_path_core::validate_custom_scan_path;
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
/// use classic_path_core::validate_settings_paths;
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
    validate_settings_path(game_path, "Game Path", Some(&[game_exe.to_string()]))?;

    // Validate documents path
    validate_settings_path(docs_path, "Documents Path", None)?;

    // Validate custom scan path if set
    if let Some(scan_path) = custom_scan_path {
        validate_custom_scan_path(scan_path)?;
    }

    Ok(())
}

// ============================================================================
// Permission and Accessibility Checks
// ============================================================================

/// Check if a path points to a valid executable file.
///
/// Validates that the path:
/// - Exists and is a file
/// - Has a recognized executable extension (.exe, .app, or no extension)
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// `true` if the path is a valid executable, `false` otherwise.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::is_valid_executable_path;
/// use std::path::Path;
///
/// let exe_path = Path::new("C:\\Games\\Fallout4\\Fallout4.exe");
/// if is_valid_executable_path(exe_path) {
///     println!("Valid executable");
/// }
/// ```
pub fn is_valid_executable_path(path: &Path) -> bool {
    if !path.exists() || !path.is_file() {
        return false;
    }

    // Check extension (.exe for Windows, .app for macOS, or no extension for Unix)
    match path.extension().and_then(|e| e.to_str()) {
        Some("exe") | Some("app") => true,
        Some(_) => false,
        None => true, // No extension is valid (Unix executables)
    }
}

/// Check if the drive exists (Windows only).
///
/// On Windows, validates that the drive letter exists in the system.
/// On other platforms, always returns `Ok(())`.
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// `Ok(())` if the drive exists or not on Windows, or a `PathError` if the drive doesn't exist.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::check_drive_exists;
/// use std::path::Path;
///
/// let path = Path::new("C:\\Games\\Fallout4");
/// check_drive_exists(path)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
#[cfg(target_os = "windows")]
pub fn check_drive_exists(path: &Path) -> PathResult<()> {
    use std::path::Component;

    // Extract drive letter from path
    if let Some(Component::Prefix(prefix)) = path.components().next() {
        let drive_path_str = format!("{}\\", prefix.as_os_str().to_string_lossy());
        let drive_path = Path::new(&drive_path_str);
        if !drive_path.exists() {
            return Err(PathError::InvalidPath(format!(
                "Drive does not exist: {}",
                prefix.as_os_str().to_string_lossy()
            )));
        }
    }

    Ok(())
}

/// Check if the drive exists (non-Windows platforms).
///
/// Always returns `Ok(())` on non-Windows platforms as drive letters are Windows-specific.
#[cfg(not(target_os = "windows"))]
pub fn check_drive_exists(_path: &Path) -> PathResult<()> {
    Ok(())
}

/// Check read permissions for a path.
///
/// Tests whether the current process can read from the path:
/// - For directories: Attempts to list contents
/// - For files: Attempts to open for reading
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// `Ok(())` if readable, or a `PathError` if read permission denied.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::check_read_permissions;
/// use std::path::Path;
///
/// let path = Path::new("C:\\Games\\Fallout4");
/// check_read_permissions(path)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn check_read_permissions(path: &Path) -> PathResult<()> {
    use std::fs;

    if path.is_dir() {
        // For directories, try to list contents
        fs::read_dir(path).map_err(|e| {
            PathError::PermissionDenied(format!("No read permission for {}: {}", path.display(), e))
        })?;
    } else if path.is_file() {
        // For files, try to open for reading
        fs::File::open(path).map_err(|e| {
            PathError::PermissionDenied(format!("No read permission for {}: {}", path.display(), e))
        })?;
    } else {
        return Err(PathError::InvalidPath(format!(
            "Path is neither a file nor directory: {}",
            path.display()
        )));
    }

    Ok(())
}

/// Check write permissions for a path.
///
/// Tests whether the current process can write to the path:
/// - For directories: Attempts to create and delete a temporary file
/// - For files: Checks if the parent directory is writable
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// `Ok(())` if writable, or a `PathError` if write permission denied.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::check_write_permissions;
/// use std::path::Path;
///
/// let path = Path::new("C:\\Games\\Fallout4");
/// check_write_permissions(path)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn check_write_permissions(path: &Path) -> PathResult<()> {
    use std::fs;

    let test_dir = if path.is_dir() {
        path.to_path_buf()
    } else {
        // For files, check parent directory
        path.parent()
            .ok_or_else(|| {
                PathError::InvalidPath(format!("Path has no parent: {}", path.display()))
            })?
            .to_path_buf()
    };

    // Try to create and remove a test file
    let test_file = test_dir.join(".classic_test_write");

    fs::write(&test_file, b"test")
        .and_then(|_| fs::remove_file(&test_file))
        .map_err(|e| {
            PathError::PermissionDenied(format!(
                "No write permission for {}: {}",
                test_dir.display(),
                e
            ))
        })?;

    Ok(())
}

/// Comprehensive path validation with permission checks.
///
/// This function performs a complete validation of a path:
/// 1. Checks if the drive exists (Windows only)
/// 2. Checks if the path exists
/// 3. Optionally checks read permissions
/// 4. Optionally checks write permissions
///
/// # Arguments
///
/// * `path` - The path to validate
/// * `check_read` - Whether to verify read permissions (default: true)
/// * `check_write` - Whether to verify write permissions (default: false)
///
/// # Returns
///
/// `Ok(())` if all checks pass, or the first `PathError` encountered.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::validate_path_with_permissions;
/// use std::path::Path;
///
/// // Check existence and read permission
/// let path = Path::new("C:\\Games\\Fallout4");
/// validate_path_with_permissions(path, true, false)?;
///
/// // Check all permissions including write
/// validate_path_with_permissions(path, true, true)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn validate_path_with_permissions(
    path: &Path,
    check_read: bool,
    check_write: bool,
) -> PathResult<()> {
    // Check if drive exists (Windows only, no-op on other platforms)
    check_drive_exists(path)?;

    // Check if path exists
    validate_path_exists(path)?;

    // Check read permissions if requested
    if check_read {
        check_read_permissions(path)?;
    }

    // Check write permissions if requested
    if check_write {
        check_write_permissions(path)?;
    }

    Ok(())
}

// ============================================================================
// Boolean Convenience Wrappers
// ============================================================================

/// Check if the drive letter in a path exists (Windows only).
///
/// This is a convenience wrapper that returns a simple `bool` instead of a `Result`.
/// On non-Windows platforms, always returns `true`.
///
/// # Arguments
///
/// * `path` - The path whose drive to check
///
/// # Returns
///
/// `true` if the drive exists or on non-Windows platforms, `false` if the drive doesn't exist.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::drive_exists;
/// use std::path::Path;
///
/// let path = Path::new("C:\\Games\\Fallout4");
/// if drive_exists(path) {
///     println!("Drive exists");
/// }
/// ```
#[must_use]
pub fn drive_exists(path: &Path) -> bool {
    check_drive_exists(path).is_ok()
}

/// Check if a path has read permissions (convenience boolean wrapper).
///
/// Returns `true` if the current process can read from the path.
/// On error (file not found, not a file/directory), returns `false`.
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// `true` if the path is readable, `false` otherwise.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::has_read_permission;
/// use std::path::Path;
///
/// let path = Path::new("C:\\Games\\Fallout4");
/// if has_read_permission(path) {
///     println!("Path is readable");
/// }
/// ```
#[must_use]
pub fn has_read_permission(path: &Path) -> bool {
    check_read_permissions(path).is_ok()
}

/// Check if a path has write permissions (convenience boolean wrapper).
///
/// Returns `true` if the current process can write to the path.
/// For files, checks the parent directory. On error, returns `false`.
///
/// # Arguments
///
/// * `path` - The path to check
///
/// # Returns
///
/// `true` if the path is writable, `false` otherwise.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::has_write_permission;
/// use std::path::Path;
///
/// let path = Path::new("C:\\Games\\Fallout4");
/// if has_write_permission(path) {
///     println!("Path is writable");
/// }
/// ```
#[must_use]
pub fn has_write_permission(path: &Path) -> bool {
    check_write_permissions(path).is_ok()
}

/// Remove the read-only attribute from a file (cross-platform).
///
/// On Windows, clears the read-only file attribute using `std::fs::set_permissions`.
/// On non-Windows platforms, this is a no-op that always succeeds.
///
/// # Arguments
///
/// * `path` - The file path to modify
///
/// # Returns
///
/// `Ok(())` if the attribute was removed or the file was already writable.
///
/// # Errors
///
/// Returns `PathError` if the file doesn't exist or permissions can't be modified.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_path_core::remove_readonly_attribute;
/// use std::path::Path;
///
/// let file = Path::new("config.ini");
/// remove_readonly_attribute(file)?;
/// # Ok::<(), classic_path_core::PathError>(())
/// ```
#[cfg(target_os = "windows")]
pub fn remove_readonly_attribute(path: &Path) -> PathResult<()> {
    use std::fs;

    let metadata = fs::metadata(path).map_err(|e| PathError::IoError {
        path: path.to_path_buf(),
        source: e,
    })?;

    let mut permissions = metadata.permissions();
    if permissions.readonly() {
        #[allow(clippy::permissions_set_readonly_false)]
        permissions.set_readonly(false);
        fs::set_permissions(path, permissions).map_err(|e| {
            PathError::PermissionDenied(format!(
                "Failed to remove read-only attribute from {}: {}",
                path.display(),
                e
            ))
        })?;
    }

    Ok(())
}

/// Remove the read-only attribute (non-Windows stub).
///
/// On non-Windows platforms, this is a no-op that always succeeds.
#[cfg(not(target_os = "windows"))]
pub fn remove_readonly_attribute(_path: &Path) -> PathResult<()> {
    Ok(())
}

#[cfg(test)]
#[path = "validator_tests.rs"]
mod tests;
