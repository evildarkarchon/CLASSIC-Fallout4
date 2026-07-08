use super::*;
use tempfile::TempDir;

#[tokio::test]
async fn test_ensure_directories() {
    let temp = TempDir::new().unwrap();
    let collector = LogCollector::new(temp.path().to_path_buf(), None, None);

    collector.ensure_directories().await.unwrap();

    assert!(collector.crash_logs_dir().exists());
    assert!(collector.pastebin_dir().exists());
}

#[tokio::test]
async fn test_move_files() {
    let temp = TempDir::new().unwrap();
    let base = temp.path();

    // Create a test crash log file
    let test_log = base.join("crash-2024-01-01-12-00-00.log");
    tokio::fs::write(&test_log, b"test crash log")
        .await
        .unwrap();

    let crash_logs = base.join("Crash Logs");
    tokio::fs::create_dir_all(&crash_logs).await.unwrap();

    let collector = LogCollector::new(base.to_path_buf(), None, None);
    let moved = collector.move_from_base_folder().await.unwrap();

    assert_eq!(moved, 1);
    assert!(!test_log.exists()); // Original should be gone
    assert!(crash_logs.join("crash-2024-01-01-12-00-00.log").exists()); // Moved to Crash Logs
}

#[tokio::test]
async fn test_copy_files() {
    let temp = TempDir::new().unwrap();
    let base = temp.path();

    // Create XSE folder with test log
    let xse_folder = base.join("XSE");
    tokio::fs::create_dir_all(&xse_folder).await.unwrap();
    let xse_log = xse_folder.join("crash-2024-01-01-12-00-00.log");
    tokio::fs::write(&xse_log, b"test xse log").await.unwrap();

    let crash_logs = base.join("Crash Logs");
    tokio::fs::create_dir_all(&crash_logs).await.unwrap();

    let collector = LogCollector::new(base.to_path_buf(), Some(xse_folder.clone()), None);
    let copied = collector.copy_from_xse_folder().await.unwrap();

    assert_eq!(copied, 1);
    assert!(xse_log.exists()); // Original should still exist
    assert!(crash_logs.join("crash-2024-01-01-12-00-00.log").exists()); // Copied to Crash Logs
}

#[tokio::test]
async fn test_collect_all() {
    let temp = TempDir::new().unwrap();
    let base = temp.path();

    // Create test logs in various locations
    let log1 = base.join("crash-2024-01-01-12-00-00.log");
    tokio::fs::write(&log1, b"log1").await.unwrap();

    let xse_folder = base.join("XSE");
    tokio::fs::create_dir_all(&xse_folder).await.unwrap();
    let log2 = xse_folder.join("crash-2024-01-01-13-00-00.log");
    tokio::fs::write(&log2, b"log2").await.unwrap();

    let custom_folder = base.join("Custom");
    tokio::fs::create_dir_all(&custom_folder).await.unwrap();
    let log3 = custom_folder.join("crash-2024-01-01-14-00-00.log");
    tokio::fs::write(&log3, b"log3").await.unwrap();

    let collector = LogCollector::new(
        base.to_path_buf(),
        Some(xse_folder),
        Some(custom_folder.clone()),
    );

    let logs = collector.collect_all().await.unwrap();

    // Should find all 3 logs
    assert_eq!(logs.len(), 3);

    // log1 should be moved to Crash Logs
    assert!(!log1.exists());

    // log2 should be copied to Crash Logs (original still exists)
    assert!(log2.exists());

    // log3 should remain in custom folder
    assert!(log3.exists());
}

#[tokio::test]
async fn test_new_for_scan_keeps_custom_folder_additive_to_xse_folder() {
    let temp = TempDir::new().unwrap();
    let base = temp.path().join("app");
    let data = temp.path().join("CLASSIC Data");
    let xse_folder = temp.path().join("docs").join("F4SE");
    let custom_folder = temp.path().join("custom");

    tokio::fs::create_dir_all(&base).await.unwrap();
    tokio::fs::create_dir_all(&data).await.unwrap();
    tokio::fs::create_dir_all(&xse_folder).await.unwrap();
    tokio::fs::create_dir_all(&custom_folder).await.unwrap();

    let xse_path_for_yaml = xse_folder.to_string_lossy().replace('\\', "/");
    tokio::fs::write(
        data.join("CLASSIC Fallout4 Local.yaml"),
        format!("Game_Info:\n  Docs_Folder_XSE: {xse_path_for_yaml}\n"),
    )
    .await
    .unwrap();

    let xse_log = xse_folder.join("crash-2024-01-01-13-00-00.log");
    let custom_log = custom_folder.join("crash-2024-01-01-14-00-00.log");
    tokio::fs::write(&xse_log, b"xse log").await.unwrap();
    tokio::fs::write(&custom_log, b"custom log").await.unwrap();

    let collector = LogCollector::new_for_scan(
        base.clone(),
        &data,
        "Fallout4",
        "auto",
        None,
        Some(custom_folder.clone()),
    );

    let logs = collector.collect_all().await.unwrap();

    assert_eq!(logs.len(), 2);
    assert!(
        xse_log.exists(),
        "XSE source log should be copied, not moved"
    );
    assert!(
        base.join("Crash Logs")
            .join("crash-2024-01-01-13-00-00.log")
            .exists(),
        "standard XSE crash logs should still be imported"
    );
    assert!(
        logs.contains(&custom_log),
        "custom folder logs should remain part of discovery"
    );
}

// ── Targeted input resolution tests ─────────────────────────────

#[tokio::test]
async fn test_targeted_explicit_file() {
    let temp = TempDir::new().unwrap();
    let log = temp.path().join("crash-2024-01-01-12-00-00.log");
    tokio::fs::write(&log, b"log data").await.unwrap();

    let res = resolve_targeted_inputs(vec![log.clone()]).await;
    assert_eq!(res.logs.len(), 1);
    assert_eq!(res.logs[0], log);
    assert!(res.rejected.is_empty());
}

#[tokio::test]
async fn test_targeted_directory_recursive() {
    let temp = TempDir::new().unwrap();
    let sub = temp.path().join("a").join("b");
    tokio::fs::create_dir_all(&sub).await.unwrap();
    tokio::fs::write(sub.join("crash-2024-01-01-12-00-00.log"), b"log1")
        .await
        .unwrap();
    tokio::fs::write(temp.path().join("crash-2024-01-01-13-00-00.log"), b"log2")
        .await
        .unwrap();
    tokio::fs::write(sub.join("Buffout4.log"), b"explicit files only")
        .await
        .unwrap();

    let res = resolve_targeted_inputs(vec![temp.path().to_path_buf()]).await;
    assert_eq!(res.logs.len(), 2);
    assert!(res.rejected.is_empty());
    assert!(
        res.logs
            .iter()
            .all(|path| matches_crash_log_pattern(path.as_path())),
        "directory inputs should still resolve only crash-*.log files"
    );
}

#[tokio::test]
async fn test_targeted_directory_with_glob_metacharacters() {
    let temp = TempDir::new().unwrap();
    let sub = temp.path().join("mods[1]").join("nested");
    tokio::fs::create_dir_all(&sub).await.unwrap();
    let log = sub.join("crash-2024-01-01-12-00-00.log");
    tokio::fs::write(&log, b"log1").await.unwrap();

    let res = resolve_targeted_inputs(vec![temp.path().join("mods[1]")]).await;
    assert_eq!(res.logs, vec![log]);
    assert!(res.rejected.is_empty());
}

#[tokio::test]
async fn test_targeted_duplicate_file() {
    let temp = TempDir::new().unwrap();
    let log = temp.path().join("crash-2024-01-01-12-00-00.log");
    tokio::fs::write(&log, b"data").await.unwrap();

    let res = resolve_targeted_inputs(vec![log.clone(), log.clone()]).await;
    assert_eq!(res.logs.len(), 1, "duplicate file should be deduplicated");
    assert!(res.rejected.is_empty());
}

#[tokio::test]
async fn test_targeted_file_plus_parent_dir_deduplicates() {
    let temp = TempDir::new().unwrap();
    let log = temp.path().join("crash-2024-01-01-12-00-00.log");
    tokio::fs::write(&log, b"data").await.unwrap();

    let res = resolve_targeted_inputs(vec![log.clone(), temp.path().to_path_buf()]).await;
    assert_eq!(
        res.logs.len(),
        1,
        "file + parent dir should deduplicate to one entry"
    );
}

#[tokio::test]
async fn test_targeted_explicit_regular_file_accepts_any_name() {
    let temp = TempDir::new().unwrap();
    let txt = temp.path().join("notes.txt");
    tokio::fs::write(&txt, b"not a log").await.unwrap();

    let res = resolve_targeted_inputs(vec![txt.clone()]).await;
    assert_eq!(res.logs, vec![txt]);
    assert!(res.rejected.is_empty());
}

#[tokio::test]
async fn test_targeted_missing_path_rejected() {
    let missing = PathBuf::from("nonexistent_dir_xyz_123/crash-foo.log");
    let res = resolve_targeted_inputs(vec![missing]).await;
    assert!(res.logs.is_empty());
    assert_eq!(res.rejected.len(), 1);
    assert!(res.rejected[0].reason.contains("does not exist"));
}

#[tokio::test]
async fn test_targeted_empty_dir_rejected() {
    let temp = TempDir::new().unwrap();
    let res = resolve_targeted_inputs(vec![temp.path().to_path_buf()]).await;
    assert!(res.logs.is_empty());
    assert_eq!(res.rejected.len(), 1);
    assert!(res.rejected[0].reason.contains("no crash-*.log"));
}

#[tokio::test]
async fn test_targeted_explicit_file_and_directory_resolve_independently() {
    let temp = TempDir::new().unwrap();
    let arbitrary = temp.path().join("my-notes.txt");
    tokio::fs::write(&arbitrary, b"explicit file intent")
        .await
        .unwrap();

    let nested = temp.path().join("logs");
    tokio::fs::create_dir_all(&nested).await.unwrap();
    let crash_log = nested.join("crash-2024-01-01-12-00-00.log");
    tokio::fs::write(&crash_log, b"crash data").await.unwrap();

    let res = resolve_targeted_inputs(vec![arbitrary.clone(), nested]).await;
    assert_eq!(
        res.logs.len(),
        2,
        "explicit file and directory crash log should both resolve"
    );
    assert!(
        res.logs.contains(&arbitrary),
        "explicit files keep arbitrary names"
    );
    assert!(
        res.logs.contains(&crash_log),
        "directories still filter to crash-*.log"
    );
    assert!(res.rejected.is_empty());
}

#[tokio::test]
async fn test_targeted_empty_inputs() {
    let res = resolve_targeted_inputs(vec![]).await;
    assert!(res.logs.is_empty());
    assert!(res.rejected.is_empty());
}

#[tokio::test]
async fn test_collect_all_unchanged_regression() {
    let temp = TempDir::new().unwrap();
    let base = temp.path();

    let log = base.join("crash-2024-06-01-10-00-00.log");
    tokio::fs::write(&log, b"regression test").await.unwrap();

    let collector = LogCollector::new(base.to_path_buf(), None, None);
    let logs = collector.collect_all().await.unwrap();

    assert_eq!(logs.len(), 1);
    assert!(!log.exists(), "log should be moved into Crash Logs");
    assert!(
        base.join("Crash Logs")
            .join("crash-2024-06-01-10-00-00.log")
            .exists()
    );
}
