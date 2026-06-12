use super::*;
use tempfile::tempdir;

// -- Helper to create test files --

async fn create_test_file(dir: &Path, name: &str, content: &[u8]) -> PathBuf {
    let path = dir.join(name);
    fs::write(&path, content).await.unwrap();
    path
}

async fn create_test_dir(parent: &Path, name: &str) -> PathBuf {
    let dir = parent.join(name);
    fs::create_dir_all(&dir).await.unwrap();
    // Add a file inside so it's not empty
    fs::write(dir.join("inner.txt"), b"inner content")
        .await
        .unwrap();
    dir
}

fn make_manager(game: &Path, backup: &Path) -> GameFilesManager {
    GameFilesManager::new(game.to_path_buf(), backup.to_path_buf())
}

// -- Pattern matching tests --

#[test]
fn test_matches_any_pattern_case_insensitive() {
    let patterns = vec!["reshade".to_string(), "enb".to_string()];
    assert!(matches_any_pattern("ReShade.ini", &patterns));
    assert!(matches_any_pattern("RESHADE.DLL", &patterns));
    assert!(matches_any_pattern("enbseries.ini", &patterns));
    assert!(matches_any_pattern("ENBLocal.ini", &patterns));
    assert!(!matches_any_pattern("d3d11.dll", &patterns));
}

#[test]
fn test_matches_any_pattern_substring() {
    let patterns = vec!["shade".to_string()];
    assert!(matches_any_pattern("ReShade.ini", &patterns));
    assert!(matches_any_pattern("MyShader.fx", &patterns));
    assert!(!matches_any_pattern("render.dll", &patterns));
}

#[test]
fn test_matches_any_pattern_empty_patterns() {
    assert!(!matches_any_pattern("anything.txt", &[]));
}

// -- Backup tests --

#[tokio::test]
async fn test_backup_files() {
    let temp = tempdir().unwrap();
    let game = temp.path().join("game");
    let backup = temp.path().join("backup");
    fs::create_dir_all(&game).await.unwrap();

    create_test_file(&game, "ReShade.ini", b"reshade config").await;
    create_test_file(&game, "enbseries.ini", b"enb config").await;
    create_test_file(&game, "other.dll", b"unrelated").await;

    let manager = make_manager(&game, &backup);
    let patterns = vec!["reshade".to_string(), "enb".to_string()];

    let result = manager.backup("Graphics", &patterns).await.unwrap();

    assert_eq!(result.operation, FileOperation::Backup);
    assert_eq!(result.files_affected, 2);
    assert!(result.is_success());
    assert_eq!(result.label, "Graphics");

    // Verify backup files exist
    assert!(backup.join("Graphics/ReShade.ini").exists());
    assert!(backup.join("Graphics/enbseries.ini").exists());
    // Unmatched file should NOT be backed up
    assert!(!backup.join("Graphics/other.dll").exists());
}

#[tokio::test]
async fn test_backup_directories() {
    let temp = tempdir().unwrap();
    let game = temp.path().join("game");
    let backup = temp.path().join("backup");
    fs::create_dir_all(&game).await.unwrap();

    create_test_dir(&game, "enbseries").await;

    let manager = make_manager(&game, &backup);
    let patterns = vec!["enbseries".to_string()];

    let result = manager.backup("ENB", &patterns).await.unwrap();

    assert_eq!(result.files_affected, 1);
    assert!(result.is_success());
    assert!(backup.join("ENB/enbseries/inner.txt").exists());
}

#[tokio::test]
async fn test_backup_no_matches() {
    let temp = tempdir().unwrap();
    let game = temp.path().join("game");
    let backup = temp.path().join("backup");
    fs::create_dir_all(&game).await.unwrap();

    create_test_file(&game, "unrelated.dll", b"data").await;

    let manager = make_manager(&game, &backup);
    let patterns = vec!["reshade".to_string()];

    let result = manager.backup("Graphics", &patterns).await.unwrap();

    assert_eq!(result.files_affected, 0);
    assert!(result.is_success());
}

// -- Restore tests --

#[tokio::test]
async fn test_restore_files() {
    let temp = tempdir().unwrap();
    let game = temp.path().join("game");
    let backup = temp.path().join("backup");
    fs::create_dir_all(&game).await.unwrap();

    // Create game files and back them up
    create_test_file(&game, "ReShade.ini", b"original").await;
    create_test_file(&game, "other.dll", b"unrelated").await;

    let manager = make_manager(&game, &backup);
    let patterns = vec!["reshade".to_string()];

    manager.backup("Graphics", &patterns).await.unwrap();

    // Modify the game file
    fs::write(game.join("ReShade.ini"), b"modified")
        .await
        .unwrap();

    // Restore
    let result = manager.restore("Graphics", &patterns).await.unwrap();

    assert_eq!(result.operation, FileOperation::Restore);
    assert_eq!(result.files_affected, 1);
    assert!(result.is_success());

    // Verify content was restored
    let content = fs::read(game.join("ReShade.ini")).await.unwrap();
    assert_eq!(content, b"original");
}

#[tokio::test]
async fn test_restore_only_existing_backups() {
    let temp = tempdir().unwrap();
    let game = temp.path().join("game");
    let backup = temp.path().join("backup");
    fs::create_dir_all(&game).await.unwrap();

    // Create two game files but only back up one
    create_test_file(&game, "ReShade.ini", b"reshade").await;
    create_test_file(&game, "ReShadePreset.ini", b"preset").await;

    let manager = make_manager(&game, &backup);

    // Back up only ReShade.ini by using an exact-ish pattern
    let backup_patterns = vec!["reshade".to_string()];
    manager.backup("Graphics", &backup_patterns).await.unwrap();

    // Delete the backup for ReShadePreset.ini manually
    let _ = fs::remove_file(backup.join("Graphics/ReShadePreset.ini")).await;

    // Restore -- should only restore the file that exists in backup
    let result = manager.restore("Graphics", &backup_patterns).await.unwrap();

    // ReShade.ini should be restored (backup exists), ReShadePreset.ini backup was deleted
    assert!(result.files_affected >= 1);
}

// -- Remove tests --

#[tokio::test]
async fn test_remove_files() {
    let temp = tempdir().unwrap();
    let game = temp.path().join("game");
    fs::create_dir_all(&game).await.unwrap();

    create_test_file(&game, "ReShade.ini", b"reshade").await;
    create_test_file(&game, "other.dll", b"keep me").await;

    let manager = make_manager(&game, &temp.path().join("backup"));
    let patterns = vec!["reshade".to_string()];

    let result = manager.remove("Graphics", &patterns).await.unwrap();

    assert_eq!(result.operation, FileOperation::Remove);
    assert_eq!(result.files_affected, 1);
    assert!(result.is_success());

    // Matched file removed
    assert!(!game.join("ReShade.ini").exists());
    // Unmatched file still present
    assert!(game.join("other.dll").exists());
}

#[tokio::test]
async fn test_remove_directories() {
    let temp = tempdir().unwrap();
    let game = temp.path().join("game");
    fs::create_dir_all(&game).await.unwrap();

    create_test_dir(&game, "enbseries").await;
    create_test_file(&game, "other.dll", b"keep").await;

    let manager = make_manager(&game, &temp.path().join("backup"));
    let patterns = vec!["enbseries".to_string()];

    let result = manager.remove("ENB", &patterns).await.unwrap();

    assert_eq!(result.files_affected, 1);
    assert!(!game.join("enbseries").exists());
    assert!(game.join("other.dll").exists());
}

// -- Error handling tests --

#[tokio::test]
async fn test_backup_nonexistent_game_root() {
    let temp = tempdir().unwrap();
    let fake_game = temp.path().join("nonexistent");
    let backup = temp.path().join("backup");

    let manager = make_manager(&fake_game, &backup);
    let patterns = vec!["anything".to_string()];

    let result = manager.backup("Test", &patterns).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_remove_nonexistent_game_root() {
    let temp = tempdir().unwrap();
    let fake_game = temp.path().join("nonexistent");

    let manager = make_manager(&fake_game, &temp.path().join("backup"));
    let patterns = vec!["anything".to_string()];

    let result = manager.remove("Test", &patterns).await;
    assert!(result.is_err());
}

// -- Integration: full backup-modify-restore cycle --

#[tokio::test]
async fn test_full_backup_restore_cycle() {
    let temp = tempdir().unwrap();
    let game = temp.path().join("game");
    let backup = temp.path().join("backup");
    fs::create_dir_all(&game).await.unwrap();

    // Set up files
    create_test_file(&game, "ReShade.ini", b"original reshade").await;
    create_test_file(&game, "enbseries.ini", b"original enb").await;
    create_test_dir(&game, "enbseries").await;

    let manager = make_manager(&game, &backup);
    let patterns = vec!["reshade".to_string(), "enb".to_string()];

    // Step 1: Backup
    let backup_result = manager.backup("Mods", &patterns).await.unwrap();
    assert_eq!(backup_result.files_affected, 3); // 2 files + 1 directory

    // Step 2: Modify originals
    fs::write(game.join("ReShade.ini"), b"modified reshade")
        .await
        .unwrap();
    fs::write(game.join("enbseries.ini"), b"modified enb")
        .await
        .unwrap();
    fs::write(game.join("enbseries/inner.txt"), b"modified inner")
        .await
        .unwrap();

    // Step 3: Restore
    let restore_result = manager.restore("Mods", &patterns).await.unwrap();
    assert_eq!(restore_result.files_affected, 3);

    // Step 4: Verify originals restored
    let reshade = fs::read(game.join("ReShade.ini")).await.unwrap();
    assert_eq!(reshade, b"original reshade");

    let enb = fs::read(game.join("enbseries.ini")).await.unwrap();
    assert_eq!(enb, b"original enb");

    let inner = fs::read(game.join("enbseries/inner.txt")).await.unwrap();
    assert_eq!(inner, b"inner content");
}

// -- Display and trait tests --

#[test]
fn test_file_operation_display() {
    assert_eq!(FileOperation::Backup.to_string(), "BACKUP");
    assert_eq!(FileOperation::Restore.to_string(), "RESTORE");
    assert_eq!(FileOperation::Remove.to_string(), "REMOVE");
}

#[test]
fn test_file_operation_result_status() {
    let success = FileOperationResult {
        operation: FileOperation::Backup,
        label: "test".to_string(),
        files_affected: 5,
        errors: vec![],
    };
    assert!(success.is_success());
    assert!(!success.is_partial());

    let partial = FileOperationResult {
        operation: FileOperation::Backup,
        label: "test".to_string(),
        files_affected: 3,
        errors: vec!["some error".to_string()],
    };
    assert!(!partial.is_success());
    assert!(partial.is_partial());

    let total_fail = FileOperationResult {
        operation: FileOperation::Remove,
        label: "test".to_string(),
        files_affected: 0,
        errors: vec!["all failed".to_string()],
    };
    assert!(!total_fail.is_success());
    assert!(!total_fail.is_partial());
}
