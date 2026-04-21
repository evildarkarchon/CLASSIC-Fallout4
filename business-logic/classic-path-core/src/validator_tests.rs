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
    assert!(is_restricted_path(&PathBuf::from(
        "C:\\Program Files (x86)"
    )));

    // Root directories should be restricted
    assert!(is_restricted_path(&PathBuf::from("C:\\")));
    assert!(is_restricted_path(&PathBuf::from("/")));

    // User directories should not be restricted
    assert!(!is_restricted_path(&PathBuf::from(
        "C:\\Users\\Name\\Downloads"
    )));
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
            eprintln!(
                "Note: Temp directory is in a restricted location: {}",
                nested_dir.display()
            );
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
            Ok(_) => panic!(
                "Should have failed for restricted path: {}",
                restricted.display()
            ),
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
fn test_remove_readonly_attribute_nonexistent() {
    let result = remove_readonly_attribute(Path::new("nonexistent_12345.txt"));
    assert!(result.is_err());
}
