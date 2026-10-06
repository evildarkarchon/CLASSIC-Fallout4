use super::*;
use tempfile::TempDir;

#[test]
fn test_xse_version_new() {
    let version = XseVersion::new("1.10.163.0");
    assert_eq!(version.full_version(), "1.10.163.0");
}

#[test]
fn test_xse_version_sanitized() {
    let version = XseVersion::new("1.10.163.0");
    assert_eq!(version.sanitized(), "1_10_163_0");
}

#[test]
fn test_backup_manager_new() {
    let manager = VersionBackupManager::new("Backups");
    assert_eq!(manager.backup_root(), Path::new("Backups"));
}

#[test]
fn test_extract_version_from_xse_log_success() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("f4se.log");

    // Create mock log with version
    let log_content = "F4SE version = 0.6.23\nruntime version = 1.10.163.0\n";
    fs::write(&log_path, log_content).unwrap();

    let manager = VersionBackupManager::new(temp_dir.path().join("backups"));
    let version = manager.extract_version_from_xse_log(&log_path).unwrap();

    // Should extract the first version found
    assert_eq!(version.full_version(), "0.6.23");
}

#[test]
fn test_extract_version_runtime_format() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("f4se.log");

    // Create log with runtime version format
    let log_content = "Some log line\nruntime version = 1.10.163.0\nOther content\n";
    fs::write(&log_path, log_content).unwrap();

    let manager = VersionBackupManager::new(temp_dir.path().join("backups"));
    let version = manager.extract_version_from_xse_log(&log_path).unwrap();

    assert_eq!(version.full_version(), "1.10.163.0");
}

#[test]
fn test_extract_version_not_found() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("f4se.log");

    // Create log without version
    fs::write(&log_path, "No version info here\n").unwrap();

    let manager = VersionBackupManager::new(temp_dir.path().join("backups"));
    let result = manager.extract_version_from_xse_log(&log_path);

    assert!(result.is_err());
    assert!(matches!(result, Err(VersionBackupError::VersionNotFound)));
}

#[test]
fn test_extract_version_log_not_found() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("nonexistent.log");

    let manager = VersionBackupManager::new(temp_dir.path().join("backups"));
    let result = manager.extract_version_from_xse_log(&log_path);

    assert!(result.is_err());
    assert!(matches!(result, Err(VersionBackupError::XseLogNotFound(_))));
}

#[test]
fn test_create_backup_success() {
    let temp_dir = TempDir::new().unwrap();

    // Create source file
    let source_file = temp_dir.path().join("Fallout4.ini");
    fs::write(&source_file, "[General]\ntest=value\n").unwrap();

    // Create backup
    let backup_root = temp_dir.path().join("backups");
    let manager = VersionBackupManager::new(&backup_root);
    let version = XseVersion::new("1.10.163.0");

    let backup_path = manager.create_backup(&source_file, &version).unwrap();

    // Verify backup was created
    assert!(backup_path.exists());
    assert_eq!(
        backup_path,
        backup_root.join("1_10_163_0").join("Fallout4.ini")
    );

    // Verify content matches
    let backup_content = fs::read_to_string(&backup_path).unwrap();
    assert_eq!(backup_content, "[General]\ntest=value\n");
}

#[test]
fn test_create_backup_source_not_found() {
    let temp_dir = TempDir::new().unwrap();
    let nonexistent = temp_dir.path().join("nonexistent.ini");

    let manager = VersionBackupManager::new(temp_dir.path().join("backups"));
    let version = XseVersion::new("1.10.163.0");

    let result = manager.create_backup(&nonexistent, &version);
    assert!(result.is_err());
    assert!(matches!(result, Err(VersionBackupError::SourceNotFound(_))));
}

#[test]
fn test_list_versions_empty() {
    let temp_dir = TempDir::new().unwrap();
    let backup_root = temp_dir.path().join("backups");

    let manager = VersionBackupManager::new(&backup_root);
    let versions = manager.list_versions().unwrap();

    assert_eq!(versions.len(), 0);
}

#[test]
fn test_list_versions_with_backups() {
    let temp_dir = TempDir::new().unwrap();
    let backup_root = temp_dir.path().join("backups");

    // Create version directories
    fs::create_dir_all(backup_root.join("1_10_163_0")).unwrap();
    fs::create_dir_all(backup_root.join("1_10_164_0")).unwrap();

    let manager = VersionBackupManager::new(&backup_root);
    let versions = manager.list_versions().unwrap();

    assert_eq!(versions.len(), 2);
    assert!(versions.contains(&"1_10_163_0".to_string()));
    assert!(versions.contains(&"1_10_164_0".to_string()));
}

#[test]
fn test_get_version_path() {
    let manager = VersionBackupManager::new("Backups");
    let version = XseVersion::new("1.10.163.0");

    let path = manager.get_version_path(&version);
    assert_eq!(path, PathBuf::from("Backups").join("1_10_163_0"));
}

#[test]
fn test_create_backup_same_label_overwrites_previous_copy() {
    // A second backup under the same version label replaces the earlier copy in
    // place instead of failing or creating a sibling; recovery reads that one file.
    let temp_dir = TempDir::new().unwrap();
    let source_file = temp_dir.path().join("settings.ini");
    let backup_root = temp_dir.path().join("backups");
    let manager = VersionBackupManager::new(&backup_root);
    let version = XseVersion::new("1.10.163.0");

    fs::write(&source_file, b"\x00first\xff").unwrap();
    let first = manager.create_backup(&source_file, &version).unwrap();
    fs::write(&source_file, b"\x00second\xfe").unwrap();
    let second = manager.create_backup(&source_file, &version).unwrap();

    assert_eq!(first, second);
    assert_eq!(fs::read(&second).unwrap(), b"\x00second\xfe");
    assert_eq!(manager.list_versions().unwrap(), vec!["1_10_163_0"]);
    assert_eq!(
        fs::read_dir(backup_root.join("1_10_163_0"))
            .unwrap()
            .count(),
        1
    );
}

#[test]
fn test_list_versions_sorted_directories_only() {
    let temp_dir = TempDir::new().unwrap();
    let backup_root = temp_dir.path().join("backups");
    fs::create_dir_all(backup_root.join("1_10_984_0")).unwrap();
    fs::create_dir_all(backup_root.join("1_10_163_0")).unwrap();
    fs::write(backup_root.join("stray.txt"), "not a version").unwrap();

    let manager = VersionBackupManager::new(&backup_root);

    assert_eq!(
        manager.list_versions().unwrap(),
        vec!["1_10_163_0", "1_10_984_0"]
    );
}

#[test]
fn test_error_messages_are_unchanged_by_the_move() {
    // Bindings forward these strings verbatim, so the owner move must not alter them.
    assert_eq!(
        VersionBackupError::XseLogNotFound(PathBuf::from("f4se.log")).to_string(),
        "XSE log file not found: f4se.log"
    );
    assert_eq!(
        VersionBackupError::VersionNotFound.to_string(),
        "Version string not found in XSE log"
    );
    assert_eq!(
        VersionBackupError::SourceNotFound(PathBuf::from("Fallout4.ini")).to_string(),
        "Source file not found: Fallout4.ini"
    );
    assert_eq!(
        VersionBackupError::InvalidVersionFormat("No filename".to_string()).to_string(),
        "Invalid version format: No filename"
    );
}

#[test]
fn test_create_backup_without_file_name_reports_invalid_format() {
    let temp_dir = TempDir::new().unwrap();
    let manager = VersionBackupManager::new(temp_dir.path().join("backups"));
    let version = XseVersion::new("1.10.163.0");

    // `..` exists but has no final file-name component.
    let result = manager.create_backup(&temp_dir.path().join(".."), &version);

    assert!(matches!(
        result,
        Err(VersionBackupError::InvalidVersionFormat(ref message)) if message == "No filename"
    ));
}
