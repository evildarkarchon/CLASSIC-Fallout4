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

/// A missing path is reported as `NotFound` before the kind check runs, so
/// directory/file validation never claims a missing path has the wrong kind.
#[test]
fn test_kind_validation_reports_missing_path_as_not_found() {
    let missing = PathBuf::from("nonexistent_kind_check_12345");

    assert!(matches!(
        validate_is_directory(&missing),
        Err(PathError::NotFound(_))
    ));
    assert!(matches!(
        validate_is_file(&missing),
        Err(PathError::NotFound(_))
    ));
}

#[test]
fn test_is_executable_file_path_accepts_exe_app_and_extensionless_files() {
    let temp_dir = TempDir::new().unwrap();
    for name in ["Game.exe", "Game.app", "game"] {
        let file = temp_dir.path().join(name);
        fs::write(&file, "binary").unwrap();
        assert!(is_executable_file_path(&file), "{name} should be accepted");
    }
}

#[test]
fn test_is_executable_file_path_rejects_other_extensions_dirs_and_missing() {
    let temp_dir = TempDir::new().unwrap();
    let yaml = temp_dir.path().join("CLASSIC Main.yaml");
    fs::write(&yaml, "data").unwrap();

    assert!(!is_executable_file_path(&yaml));
    // A directory is never an executable, even without an extension.
    assert!(!is_executable_file_path(temp_dir.path()));
    assert!(!is_executable_file_path(
        &temp_dir.path().join("missing.exe")
    ));
}

#[test]
fn test_check_read_permissions_rejects_missing_path_as_invalid() {
    let result = check_read_permissions(&PathBuf::from("nonexistent_read_check_12345"));
    match result {
        Err(PathError::InvalidPath(message)) => {
            assert!(message.starts_with("Path is neither a file nor directory: "));
        }
        other => panic!("Expected InvalidPath error, got {other:?}"),
    }
}

#[test]
fn test_check_write_permissions_leaves_no_probe_file_behind() {
    let temp_dir = TempDir::new().unwrap();

    assert!(check_write_permissions(temp_dir.path()).is_ok());
    assert!(!temp_dir.path().join(".classic_test_write").exists());
}

#[test]
fn test_validate_path_with_permissions_reports_missing_path_as_not_found() {
    let missing = PathBuf::from("nonexistent_permission_check_12345");

    assert!(matches!(
        validate_path_with_permissions(&missing, true, false),
        Err(PathError::NotFound(_))
    ));
}

#[test]
fn test_validate_path_with_permissions_accepts_readable_writable_dir() {
    let temp_dir = TempDir::new().unwrap();

    assert!(validate_path_with_permissions(temp_dir.path(), true, true).is_ok());
}

// ====================================================================
// Boolean wrapper tests
// ====================================================================

#[test]
fn test_drive_exists_current_dir() {
    // Current working directory's drive should always exist
    let cwd = std::env::current_dir().unwrap();
    assert!(drive_exists(&cwd));
}

#[test]
fn test_has_read_permission_temp() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("readable.txt");
    fs::write(&file_path, "content").unwrap();
    assert!(has_read_permission(&file_path));
}

#[test]
fn test_has_read_permission_nonexistent() {
    assert!(!has_read_permission(&PathBuf::from(
        "nonexistent_path_12345"
    )));
}

#[test]
fn test_has_write_permission_temp() {
    let temp_dir = TempDir::new().unwrap();
    assert!(has_write_permission(temp_dir.path()));
}

#[test]
fn test_has_write_permission_nonexistent() {
    // Use a path with a nonexistent parent chain to ensure write check fails
    assert!(!has_write_permission(&PathBuf::from(
        "Z:\\nonexistent_drive_12345\\deeply\\nested\\path"
    )));
}

#[test]
fn test_remove_readonly_attribute_normal_file() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("normal.txt");
    fs::write(&file_path, "content").unwrap();

    // Should succeed on a normal (non-readonly) file
    assert!(remove_readonly_attribute(&file_path).is_ok());
}

#[test]
fn test_remove_readonly_attribute_readonly_file() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("readonly.txt");
    fs::write(&file_path, "content").unwrap();

    // Set read-only
    let mut perms = fs::metadata(&file_path).unwrap().permissions();
    perms.set_readonly(true);
    fs::set_permissions(&file_path, perms).unwrap();

    // Remove read-only
    let result = remove_readonly_attribute(&file_path);
    assert!(
        result.is_ok(),
        "Failed to remove readonly: {:?}",
        result.err()
    );

    // Verify it's writable now
    let perms = fs::metadata(&file_path).unwrap().permissions();
    assert!(!perms.readonly());
}

#[test]
#[cfg(target_os = "windows")]
fn test_remove_readonly_attribute_nonexistent() {
    let result = remove_readonly_attribute(Path::new("nonexistent_12345.txt"));
    assert!(matches!(result, Err(PathError::IoError { .. })));
}

#[test]
#[cfg(target_os = "windows")]
fn test_remove_readonly_clears_flag_and_rejects_missing_file() {
    let temp_dir = TempDir::new().unwrap();
    let file_path = temp_dir.path().join("readonly.ini");
    fs::write(&file_path, "content").unwrap();
    let mut perms = fs::metadata(&file_path).unwrap().permissions();
    perms.set_readonly(true);
    fs::set_permissions(&file_path, perms).unwrap();

    remove_readonly(&file_path).unwrap();
    assert!(!fs::metadata(&file_path).unwrap().permissions().readonly());

    assert!(matches!(
        remove_readonly(Path::new("nonexistent_12345.ini")),
        Err(PathError::IoError { .. })
    ));
}

// ====================================================================
// Error contract — variants and messages are part of the binding surface
// ====================================================================

#[test]
fn test_path_error_messages_are_stable() {
    let path = PathBuf::from("some/where");

    assert_eq!(
        PathError::NotFound(path.clone()).to_string(),
        format!("Path does not exist: {}", path.display())
    );
    assert_eq!(
        PathError::NotADirectory(path.clone()).to_string(),
        format!("Path is not a directory: {}", path.display())
    );
    assert_eq!(
        PathError::NotAFile(path.clone()).to_string(),
        format!("Path is not a file: {}", path.display())
    );
    assert_eq!(
        PathError::PermissionDenied("nope".into()).to_string(),
        "Permission denied: nope"
    );
    assert_eq!(
        PathError::InvalidPath("bad".into()).to_string(),
        "Invalid path: bad"
    );
    let io = PathError::IoError {
        path: path.clone(),
        source: std::io::Error::new(std::io::ErrorKind::NotFound, "gone"),
    };
    assert_eq!(
        io.to_string(),
        format!("I/O error for path {}: gone", path.display())
    );
}
