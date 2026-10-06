use super::*;
use classic_path_core::ValidationError;
use std::fs;
use std::path::PathBuf;
use tempfile::TempDir;

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

/// An existing restricted directory reports the typed restricted-path error
/// with the exact message every binding projects.
#[test]
fn test_validate_custom_scan_path_restricted_message() {
    let temp_dir = TempDir::new().unwrap();
    let restricted = temp_dir.path().join("Program Files").join("Mods");
    fs::create_dir_all(&restricted).unwrap();

    match validate_custom_scan_path(&restricted) {
        Err(error @ ValidationError::RestrictedPath(_)) => assert_eq!(
            error.to_string(),
            format!(
                "Path is restricted for custom scans: {}",
                restricted.display()
            )
        ),
        other => panic!("expected RestrictedPath, got {other:?}"),
    }
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

/// Game and Documents failures are reported before the custom-scan policy
/// runs, and a restricted custom-scan folder fails the combined check.
#[test]
fn test_validate_settings_paths_checks_game_docs_then_custom_scan() {
    let temp_dir = TempDir::new().unwrap();
    let game_dir = temp_dir.path().join("game");
    let docs_dir = temp_dir.path().join("docs");
    let restricted_scan = temp_dir.path().join("Program Files").join("Mods");
    fs::create_dir(&game_dir).unwrap();
    fs::create_dir(&docs_dir).unwrap();
    fs::create_dir_all(&restricted_scan).unwrap();
    fs::write(game_dir.join("Fallout4.exe"), "test").unwrap();

    let missing_docs = temp_dir.path().join("missing-docs");
    match validate_settings_paths(
        &game_dir,
        &missing_docs,
        Some(&restricted_scan),
        "Fallout4.exe",
    ) {
        Err(ValidationError::ValidationFailed { setting, .. }) => {
            assert_eq!(setting, "Documents Path");
        }
        other => panic!("expected Documents Path failure first, got {other:?}"),
    }

    assert!(matches!(
        validate_settings_paths(&game_dir, &docs_dir, Some(&restricted_scan), "Fallout4.exe"),
        Err(ValidationError::RestrictedPath(_))
    ));
}
