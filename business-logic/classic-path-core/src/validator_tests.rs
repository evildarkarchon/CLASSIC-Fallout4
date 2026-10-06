use super::*;
use std::fs;
use tempfile::TempDir;

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
fn test_validate_game_and_documents_paths() {
    let temp_dir = TempDir::new().unwrap();
    let game_dir = temp_dir.path().join("game");
    let docs_dir = temp_dir.path().join("docs");

    fs::create_dir(&game_dir).unwrap();
    fs::create_dir(&docs_dir).unwrap();
    fs::write(game_dir.join("Fallout4.exe"), "test").unwrap();

    // Should succeed with valid paths
    let result = validate_game_and_documents_paths(&game_dir, &docs_dir, "Fallout4.exe");
    assert!(result.is_ok());

    // Should fail with missing executable
    let invalid_game = temp_dir.path().join("invalid");
    fs::create_dir(&invalid_game).unwrap();
    let result = validate_game_and_documents_paths(&invalid_game, &docs_dir, "Missing.exe");
    assert!(result.is_err());

    // A missing documents folder is reported under its setting name
    let missing_docs = temp_dir.path().join("missing-docs");
    match validate_game_and_documents_paths(&game_dir, &missing_docs, "Fallout4.exe") {
        Err(ValidationError::ValidationFailed { setting, .. }) => {
            assert_eq!(setting, "Documents Path");
        }
        other => panic!("expected Documents Path failure, got {other:?}"),
    }
}
