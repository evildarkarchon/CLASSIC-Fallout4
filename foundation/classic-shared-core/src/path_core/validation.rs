//! Generic path existence, kind, permission, drive, and read-only primitives.
//!
//! These moved unchanged from `classic-path-core` (`validator.rs` and the
//! Windows `remove_readonly` helper) so callers that only need a neutral path
//! check no longer depend on the game/documents discovery crate. Custom-scan
//! restrictions, settings-path validation, and required-file checks are setup
//! and scan policy; they stay with `classic-path-core` and the workflows above
//! it rather than moving here.

use super::error::{PathError, PathResult};
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
/// use classic_shared_core::path_core::is_valid_path;
/// use std::path::Path;
///
/// let path = Path::new(".");
/// assert!(is_valid_path(&path));
/// ```
pub fn is_valid_path(path: &Path) -> bool {
    path.exists()
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
/// use classic_shared_core::path_core::validate_path_exists;
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

// ============================================================================
// Permission and Accessibility Checks
// ============================================================================

/// Check if a path points to an existing file with a launchable extension.
///
/// Validates that the path:
/// - Exists and is a file
/// - Has a recognized executable extension (.exe, .app, or no extension)
///
/// This was `classic_path_core::is_valid_executable_path`. It is named
/// differently here because shared core already owns
/// [`crate::version::pe_version::is_valid_executable_path`], which answers a
/// different question (is this a `.exe`/`.dll` whose PE version can be read?).
/// The path adapters keep their existing `is_valid_executable_path` /
/// `isValidExecutablePath` export names.
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
/// use classic_shared_core::path_core::is_executable_file_path;
/// use std::path::Path;
///
/// let exe_path = Path::new("C:\\Games\\Fallout4\\Fallout4.exe");
/// if is_executable_file_path(exe_path) {
///     println!("Valid executable");
/// }
/// ```
pub fn is_executable_file_path(path: &Path) -> bool {
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
/// use classic_shared_core::path_core::check_drive_exists;
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
/// use classic_shared_core::path_core::check_read_permissions;
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
/// use classic_shared_core::path_core::check_write_permissions;
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
/// use classic_shared_core::path_core::validate_path_with_permissions;
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
/// use classic_shared_core::path_core::drive_exists;
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
/// use classic_shared_core::path_core::has_read_permission;
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
/// use classic_shared_core::path_core::has_write_permission;
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
/// use classic_shared_core::path_core::remove_readonly_attribute;
/// use std::path::Path;
///
/// let file = Path::new("config.ini");
/// remove_readonly_attribute(file)?;
/// # Ok::<(), classic_shared_core::path_core::PathError>(())
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

/// Remove the read-only attribute from a file or directory (Windows only).
///
/// This function modifies the file permissions to remove the read-only flag.
/// When clearing the flag fails it writes a warning to stderr *and* returns
/// the error to the caller.
///
/// Unlike [`remove_readonly_attribute`], this writes that stderr warning; the
/// Node and Python `remove_readonly` exports rely on the existing behavior, so
/// the two helpers are kept distinct.
///
/// # Arguments
///
/// * `file_path` - Path to the file or directory
///
/// # Returns
///
/// `Ok(())` if the flag was cleared or was not set.
///
/// # Errors
///
/// - [`PathError::IoError`] when the path's metadata cannot be read (for
///   example, the path does not exist).
/// - [`PathError::PermissionDenied`] when the permissions cannot be updated.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_shared_core::path_core::remove_readonly;
/// use std::path::Path;
///
/// let file = Path::new("C:\\Games\\Fallout4\\Fallout4.ini");
/// remove_readonly(file)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
#[cfg(target_os = "windows")]
#[allow(clippy::permissions_set_readonly_false)]
pub fn remove_readonly(file_path: &Path) -> PathResult<()> {
    use std::fs;

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
#[path = "validation_tests.rs"]
mod tests;
