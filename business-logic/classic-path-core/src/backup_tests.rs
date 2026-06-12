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
    let manager = BackupManager::new("Backups");
    assert_eq!(manager.backup_root(), Path::new("Backups"));
}

#[test]
fn test_extract_version_from_xse_log_success() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("f4se.log");

    // Create mock log with version
    let log_content = "F4SE version = 0.6.23\nruntime version = 1.10.163.0\n";
    fs::write(&log_path, log_content).unwrap();

    let manager = BackupManager::new(temp_dir.path().join("backups"));
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

    let manager = BackupManager::new(temp_dir.path().join("backups"));
    let version = manager.extract_version_from_xse_log(&log_path).unwrap();

    assert_eq!(version.full_version(), "1.10.163.0");
}

#[test]
fn test_extract_version_not_found() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("f4se.log");

    // Create log without version
    fs::write(&log_path, "No version info here\n").unwrap();

    let manager = BackupManager::new(temp_dir.path().join("backups"));
    let result = manager.extract_version_from_xse_log(&log_path);

    assert!(result.is_err());
    assert!(matches!(result, Err(BackupError::VersionNotFound)));
}

#[test]
fn test_extract_version_log_not_found() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("nonexistent.log");

    let manager = BackupManager::new(temp_dir.path().join("backups"));
    let result = manager.extract_version_from_xse_log(&log_path);

    assert!(result.is_err());
    assert!(matches!(result, Err(BackupError::XseLogNotFound(_))));
}

#[test]
fn test_create_backup_success() {
    let temp_dir = TempDir::new().unwrap();

    // Create source file
    let source_file = temp_dir.path().join("Fallout4.ini");
    fs::write(&source_file, "[General]\ntest=value\n").unwrap();

    // Create backup
    let backup_root = temp_dir.path().join("backups");
    let manager = BackupManager::new(&backup_root);
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

    let manager = BackupManager::new(temp_dir.path().join("backups"));
    let version = XseVersion::new("1.10.163.0");

    let result = manager.create_backup(&nonexistent, &version);
    assert!(result.is_err());
    assert!(matches!(result, Err(BackupError::SourceNotFound(_))));
}

#[test]
fn test_list_versions_empty() {
    let temp_dir = TempDir::new().unwrap();
    let backup_root = temp_dir.path().join("backups");

    let manager = BackupManager::new(&backup_root);
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

    let manager = BackupManager::new(&backup_root);
    let versions = manager.list_versions().unwrap();

    assert_eq!(versions.len(), 2);
    assert!(versions.contains(&"1_10_163_0".to_string()));
    assert!(versions.contains(&"1_10_164_0".to_string()));
}

#[test]
fn test_get_version_path() {
    let manager = BackupManager::new("Backups");
    let version = XseVersion::new("1.10.163.0");

    let path = manager.get_version_path(&version);
    assert_eq!(path, PathBuf::from("Backups").join("1_10_163_0"));
}
