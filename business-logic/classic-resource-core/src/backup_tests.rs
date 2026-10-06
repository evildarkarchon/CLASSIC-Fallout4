use super::*;
use tempfile::tempdir;

#[test]
fn test_backup_type_display_names() {
    assert_eq!(BackupType::XSE.display_name(), "XSE (F4SE/SKSE)");
    assert_eq!(BackupType::ReShade.display_name(), "ReShade");
    assert_eq!(BackupType::Vulkan.display_name(), "Vulkan");
    assert_eq!(BackupType::ENB.display_name(), "ENB");
}

#[test]
fn test_backup_type_patterns() {
    let xse_patterns = BackupType::XSE.file_patterns();
    assert!(xse_patterns.contains(&"f4se_*.dll"));

    let reshade_patterns = BackupType::ReShade.file_patterns();
    assert!(reshade_patterns.contains(&"dxgi.dll"));
}

#[test]
fn test_pattern_matching() {
    assert!(BackupManager::matches_pattern(
        "f4se_1_10_163.dll",
        "f4se_*.dll"
    ));
    assert!(BackupManager::matches_pattern("dxgi.dll", "dxgi.dll"));
    assert!(!BackupManager::matches_pattern("other.dll", "f4se_*.dll"));
}

#[tokio::test]
async fn test_backup_manager_creation() {
    let temp_dir = tempdir().unwrap();
    let game_root = temp_dir.path().to_path_buf();

    let manager = BackupManager::new(game_root.clone(), None);
    assert_eq!(manager.game_root, game_root);
    assert_eq!(manager.backup_base, game_root.join("CLASSIC_Backups"));
}

#[tokio::test]
async fn test_backup_exists_empty() {
    let temp_dir = tempdir().unwrap();
    let game_root = temp_dir.path().to_path_buf();

    let manager = BackupManager::new(game_root, None);
    let exists = manager.backup_exists(BackupType::XSE).await.unwrap();
    assert!(!exists);
}

#[tokio::test]
async fn test_create_and_restore_backup() {
    let temp_dir = tempdir().unwrap();
    let game_root = temp_dir.path().to_path_buf();

    // Create test files
    let test_file = game_root.join("f4se_1_10_163.dll");
    fs::write(&test_file, b"test content").await.unwrap();

    let manager = BackupManager::new(game_root.clone(), None);

    // Create backup
    let backup_info = manager.create_backup(BackupType::XSE).await.unwrap();
    assert!(backup_info.exists);
    assert_eq!(backup_info.file_count, 1);

    // Delete original file
    fs::remove_file(&test_file).await.unwrap();
    assert!(!test_file.exists());

    // Restore backup
    let restored_count = manager.restore_backup(BackupType::XSE).await.unwrap();
    assert_eq!(restored_count, 1);
    assert!(test_file.exists());

    // Verify content
    let content = fs::read(&test_file).await.unwrap();
    assert_eq!(content, b"test content");
}

#[tokio::test]
async fn test_remove_backup() {
    let temp_dir = tempdir().unwrap();
    let game_root = temp_dir.path().to_path_buf();

    // Create test file
    let test_file = game_root.join("f4se_1_10_163.dll");
    fs::write(&test_file, b"test").await.unwrap();

    let manager = BackupManager::new(game_root, None);

    // Create backup
    manager.create_backup(BackupType::XSE).await.unwrap();
    assert!(manager.backup_exists(BackupType::XSE).await.unwrap());

    // Remove backup
    manager.remove_backup(BackupType::XSE).await.unwrap();
    assert!(!manager.backup_exists(BackupType::XSE).await.unwrap());
}
