use super::*;

#[test]
fn test_backup_type_from_str() {
    assert!(backup_type_from_str("xse").is_ok());
    assert!(backup_type_from_str("reshade").is_ok());
    assert!(backup_type_from_str("vulkan").is_ok());
    assert!(backup_type_from_str("enb").is_ok());
    assert!(backup_type_from_str("unknown").is_err());
}

#[test]
fn test_backup_manager_new() {
    let _mgr = backup_manager_new("C:\\Games\\Fallout4");
}

#[test]
fn test_file_similarity_identical() {
    let dir = tempfile::tempdir().unwrap();
    let file1 = dir.path().join("a.txt");
    let file2 = dir.path().join("b.txt");
    std::fs::write(&file1, "hello world").unwrap();
    std::fs::write(&file2, "hello world").unwrap();

    let sim = calculate_file_similarity(file1.to_str().unwrap(), file2.to_str().unwrap()).unwrap();
    assert!((sim - 1.0).abs() < f64::EPSILON);
}

#[test]
fn test_file_read_write_round_trip() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("test.txt");
    let path_str = path.to_str().unwrap();

    write_file_string(path_str, "test content").unwrap();
    let content = read_file_with_encoding(path_str).unwrap();
    assert_eq!(content.trim(), "test content");
}

#[test]
fn test_hash_cache_helpers_forward_core_surface() {
    hash_cache_clear();
    reset_hash_cache_stats();

    let initial = hash_cache_stats();
    assert_eq!(initial.size, 0);
    assert_eq!(initial.capacity, 1024);
    assert_eq!(hash_cache_size(), 0);

    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("hash-target.txt");
    std::fs::write(&path, "hash me").unwrap();

    FileHasher::hash_file(&path).unwrap();

    let populated = hash_cache_stats();
    assert_eq!(populated.size, 1);
    assert_eq!(hash_cache_size(), 1);
}

#[test]
fn test_read_nonexistent_file() {
    let result = read_file_with_encoding("nonexistent_file_xyz.txt");
    assert!(result.is_err());
}

#[test]
fn test_log_collector_empty_dir() {
    let dir = tempfile::tempdir().unwrap();
    let collector = log_collector_new(dir.path().to_str().unwrap(), "", "");
    let logs = log_collector_collect_crash_logs(&collector);
    if let Ok(v) = logs {
        assert!(v.is_empty());
    }
}

#[test]
fn test_log_collector_new_for_scan_preserves_xse_with_custom_folder() {
    let dir = tempfile::tempdir().unwrap();
    let base = dir.path().join("app");
    let data = dir.path().join("CLASSIC Data");
    let xse = dir.path().join("docs").join("F4SE");
    let custom = dir.path().join("custom");
    std::fs::create_dir_all(&base).unwrap();
    std::fs::create_dir_all(&data).unwrap();
    std::fs::create_dir_all(&xse).unwrap();
    std::fs::create_dir_all(&custom).unwrap();

    let xse_path_for_yaml = xse.to_string_lossy().replace('\\', "/");
    std::fs::write(
        data.join("CLASSIC Fallout4 Local.yaml"),
        format!("Game_Info:\n  Docs_Folder_XSE: {xse_path_for_yaml}\n"),
    )
    .unwrap();
    std::fs::write(xse.join("crash-2024-01-01-13-00-00.log"), "xse").unwrap();
    std::fs::write(custom.join("crash-2024-01-01-14-00-00.log"), "custom").unwrap();

    let collector = log_collector_new_for_scan(
        base.to_str().unwrap(),
        data.to_str().unwrap(),
        "Fallout4",
        "auto",
        "",
        custom.to_str().unwrap(),
    );

    let logs = log_collector_collect_all(&collector).unwrap();

    assert_eq!(logs.len(), 2);
    assert!(
        base.join("Crash Logs")
            .join("crash-2024-01-01-13-00-00.log")
            .exists()
    );
}

#[test]
fn test_game_files_manager_new() {
    let dir = tempfile::tempdir().unwrap();
    let _mgr = game_files_manager_new(
        dir.path().to_str().unwrap(),
        dir.path().join("backups").to_str().unwrap(),
    );
}

#[test]
fn test_discover_report_files_empty_dir() {
    let dir = tempfile::tempdir().unwrap();
    let reports = discover_report_files(dir.path().to_str().unwrap());
    assert!(reports.is_empty());
}

#[test]
fn test_discover_report_files_finds_autoscan() {
    let dir = tempfile::tempdir().unwrap();
    // Create matching and non-matching files
    std::fs::write(dir.path().join("crash-2025-01-01-AUTOSCAN.md"), "report1").unwrap();
    std::fs::write(dir.path().join("crash-2025-01-02-AUTOSCAN.md"), "report2").unwrap();
    std::fs::write(dir.path().join("notes.md"), "not a report").unwrap();
    std::fs::write(dir.path().join("crash.log"), "raw log").unwrap();

    let reports = discover_report_files(dir.path().to_str().unwrap());
    assert_eq!(reports.len(), 2, "Should find exactly 2 AUTOSCAN.md files");
    for r in &reports {
        assert!(r.contains("-AUTOSCAN.md"), "Path should match pattern: {r}");
    }
}

#[test]
fn test_discover_report_files_nonexistent_dir() {
    let reports = discover_report_files("nonexistent_directory_xyz_123");
    assert!(reports.is_empty());
}

#[test]
fn test_read_report_file_round_trip() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("test-AUTOSCAN.md");
    let path_str = path.to_str().unwrap();
    std::fs::write(&path, "# Report\n\nSome content").unwrap();

    let content = read_report_file(path_str).unwrap();
    assert!(content.contains("# Report"));
    assert!(content.contains("Some content"));
}

#[test]
fn test_read_report_file_nonexistent() {
    let result = read_report_file("nonexistent_report_xyz.md");
    assert!(result.is_err());
}

#[test]
fn test_write_autoscan_report_writes_next_to_source_log() {
    let dir = tempfile::tempdir().unwrap();
    let custom_dir = dir.path().join("CustomScan");
    std::fs::create_dir_all(&custom_dir).unwrap();

    let log_path = custom_dir.join("crash-2026-02-19-00-00-00.log");
    std::fs::write(&log_path, "raw log").unwrap();

    let out_path = write_autoscan_report(log_path.to_str().unwrap(), "# report body").unwrap();
    let out_path = std::path::PathBuf::from(out_path);

    assert_eq!(out_path.parent(), log_path.parent());
    assert_eq!(
        out_path.file_name().and_then(|n| n.to_str()),
        Some("crash-2026-02-19-00-00-00-AUTOSCAN.md")
    );
    assert!(out_path.exists());
}
