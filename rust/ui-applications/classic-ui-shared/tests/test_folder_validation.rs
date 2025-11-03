//! Tests for folder validation module

use classic_ui_shared::folder_validation::{
    FolderValidationResult, validate_folder_path, validate_folder_path_result,
};
use std::path::Path;
use tempfile::TempDir;

#[test]
fn test_valid_existing_directory() {
    let temp_dir = TempDir::new().unwrap();
    let result = validate_folder_path(temp_dir.path(), false);
    assert!(result.is_valid(), "Existing directory should be valid");
}

#[test]
fn test_empty_path_allowed() {
    let empty_path = Path::new("");
    let result = validate_folder_path(empty_path, true);
    assert!(
        matches!(result, FolderValidationResult::Empty),
        "Empty path should return Empty when allowed"
    );
}

#[test]
fn test_empty_path_not_allowed() {
    let empty_path = Path::new("");
    let result = validate_folder_path(empty_path, false);
    assert!(
        result.is_invalid(),
        "Empty path should be invalid when not allowed"
    );
}

#[test]
fn test_nonexistent_path() {
    let nonexistent = Path::new("/this/path/does/not/exist/anywhere");
    let result = validate_folder_path(nonexistent, false);
    assert!(result.is_invalid(), "Nonexistent path should be invalid");

    if let FolderValidationResult::Invalid(msg) = result {
        assert!(
            msg.contains("does not exist") || msg.contains("not found"),
            "Error message should mention path doesn't exist"
        );
    }
}

#[test]
fn test_file_instead_of_directory() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("test_file.txt");
    std::fs::write(&file_path, "test content").unwrap();

    let result = validate_folder_path(&file_path, false);
    assert!(
        result.is_invalid(),
        "File path should be invalid when expecting directory"
    );

    if let FolderValidationResult::Invalid(msg) = result {
        assert!(
            msg.contains("not a directory") || msg.contains("is a file"),
            "Error message should mention it's not a directory"
        );
    }
}

#[test]
fn test_validate_folder_path_result_valid() {
    let temp_dir = TempDir::new().unwrap();
    let result = validate_folder_path_result(temp_dir.path(), false);
    assert!(result.is_ok(), "Valid directory should return Ok");
}

#[test]
fn test_validate_folder_path_result_invalid() {
    let nonexistent = Path::new("/this/path/does/not/exist");
    let result = validate_folder_path_result(nonexistent, false);
    assert!(result.is_err(), "Invalid path should return Err");
}

#[test]
fn test_validate_folder_path_result_empty_allowed() {
    let empty_path = Path::new("");
    let result = validate_folder_path_result(empty_path, true);
    assert!(result.is_ok(), "Empty path should be Ok when allowed");
}

#[test]
fn test_validate_folder_path_result_empty_not_allowed() {
    let empty_path = Path::new("");
    let result = validate_folder_path_result(empty_path, false);
    assert!(result.is_err(), "Empty path should be Err when not allowed");
}

#[test]
fn test_whitespace_only_path() {
    let whitespace = Path::new("   ");
    let result = validate_folder_path(whitespace, false);
    assert!(
        result.is_invalid(),
        "Whitespace-only path should be invalid"
    );
}

#[cfg(unix)]
#[test]
fn test_readonly_directory() {
    use std::fs::{self, Permissions};
    use std::os::unix::fs::PermissionsExt;

    let temp_dir = TempDir::new().unwrap();
    let readonly_dir = temp_dir.path().join("readonly");
    fs::create_dir(&readonly_dir).unwrap();

    // Make directory read-only (no write permission)
    let perms = Permissions::from_mode(0o444);
    fs::set_permissions(&readonly_dir, perms).unwrap();

    // Should still be valid (we only check if it's a readable directory)
    let result = validate_folder_path(&readonly_dir, false);
    assert!(
        result.is_valid(),
        "Read-only directory should still be valid for validation"
    );

    // Restore write permissions for cleanup
    let perms = Permissions::from_mode(0o755);
    fs::set_permissions(&readonly_dir, perms).unwrap();
}

#[test]
fn test_nested_valid_directory() {
    let temp_dir = TempDir::new().unwrap();
    let nested = temp_dir.path().join("level1").join("level2").join("level3");
    std::fs::create_dir_all(&nested).unwrap();

    let result = validate_folder_path(&nested, false);
    assert!(result.is_valid(), "Nested directory should be valid");
}
