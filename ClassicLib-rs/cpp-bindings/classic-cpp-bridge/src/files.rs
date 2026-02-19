//! File operations bridge for CXX FFI.
//!
//! Bridges `classic_file_io_core` for backup management, game files,
//! log collection, file similarity, and encoding-aware file I/O.

use classic_file_io_core::FileIOCore;
use classic_file_io_core::backup::{BackupManager, BackupType};
use classic_file_io_core::game_files::GameFilesManager;
use classic_file_io_core::log_collection::LogCollector;
use classic_file_io_core::similarity::calculate_similarity;
use classic_shared_core::get_runtime;
use std::path::{Path, PathBuf};

/// Opaque wrapper around BackupManager.
pub struct CxxBackupManager {
    inner: BackupManager,
}

/// Opaque wrapper around GameFilesManager.
pub struct CxxGameFilesManager {
    inner: GameFilesManager,
}

/// Opaque wrapper around LogCollector.
pub struct CxxLogCollector {
    inner: LogCollector,
}

// ── BackupType mapping ──────────────────────────────────────────────

fn backup_type_from_str(s: &str) -> Result<BackupType, String> {
    match s.to_lowercase().as_str() {
        "xse" => Ok(BackupType::XSE),
        "reshade" => Ok(BackupType::ReShade),
        "vulkan" => Ok(BackupType::Vulkan),
        "enb" => Ok(BackupType::ENB),
        _ => Err(format!("Unknown backup type: {s}")),
    }
}

// ── BackupManager ───────────────────────────────────────────────────

fn backup_manager_new(game_root: &str) -> Box<CxxBackupManager> {
    Box::new(CxxBackupManager {
        inner: BackupManager::new(PathBuf::from(game_root), None),
    })
}

fn backup_manager_exists(mgr: &CxxBackupManager, backup_type: &str) -> Result<bool, String> {
    let bt = backup_type_from_str(backup_type)?;
    get_runtime()
        .block_on(mgr.inner.backup_exists(bt))
        .map_err(|e| format!("{e}"))
}

fn backup_manager_create(mgr: &CxxBackupManager, backup_type: &str) -> Result<String, String> {
    let bt = backup_type_from_str(backup_type)?;
    let info = get_runtime()
        .block_on(mgr.inner.create_backup(bt))
        .map_err(|e| format!("{e}"))?;
    Ok(format!("Backed up {} files", info.file_count))
}

fn backup_manager_restore(mgr: &CxxBackupManager, backup_type: &str) -> Result<u32, String> {
    let bt = backup_type_from_str(backup_type)?;
    let count = get_runtime()
        .block_on(mgr.inner.restore_backup(bt))
        .map_err(|e| format!("{e}"))?;
    Ok(count as u32)
}

fn backup_manager_remove(mgr: &CxxBackupManager, backup_type: &str) -> Result<(), String> {
    let bt = backup_type_from_str(backup_type)?;
    get_runtime()
        .block_on(mgr.inner.remove_backup(bt))
        .map_err(|e| format!("{e}"))
}

// ── GameFilesManager ────────────────────────────────────────────────

fn game_files_manager_new(game_root: &str, backup_root: &str) -> Box<CxxGameFilesManager> {
    Box::new(CxxGameFilesManager {
        inner: GameFilesManager::new(PathBuf::from(game_root), PathBuf::from(backup_root)),
    })
}

fn game_files_backup(
    mgr: &CxxGameFilesManager,
    label: &str,
    patterns: &[String],
) -> Result<String, String> {
    let result = get_runtime()
        .block_on(mgr.inner.backup(label, patterns))
        .map_err(|e| format!("{e}"))?;
    Ok(format!(
        "{} files affected, {} errors",
        result.files_affected,
        result.errors.len()
    ))
}

fn game_files_restore(
    mgr: &CxxGameFilesManager,
    label: &str,
    patterns: &[String],
) -> Result<String, String> {
    let result = get_runtime()
        .block_on(mgr.inner.restore(label, patterns))
        .map_err(|e| format!("{e}"))?;
    Ok(format!(
        "{} files affected, {} errors",
        result.files_affected,
        result.errors.len()
    ))
}

fn game_files_remove(
    mgr: &CxxGameFilesManager,
    label: &str,
    patterns: &[String],
) -> Result<String, String> {
    let result = get_runtime()
        .block_on(mgr.inner.remove(label, patterns))
        .map_err(|e| format!("{e}"))?;
    Ok(format!(
        "{} files affected, {} errors",
        result.files_affected,
        result.errors.len()
    ))
}

// ── LogCollector ────────────────────────────────────────────────────

fn log_collector_new(
    crash_logs_dir: &str,
    xse_folder: &str,
    custom_folder: &str,
) -> Box<CxxLogCollector> {
    let xse = if xse_folder.is_empty() {
        None
    } else {
        Some(PathBuf::from(xse_folder))
    };
    let custom = if custom_folder.is_empty() {
        None
    } else {
        Some(PathBuf::from(custom_folder))
    };
    Box::new(CxxLogCollector {
        inner: LogCollector::new(PathBuf::from(crash_logs_dir), xse, custom),
    })
}

fn log_collector_collect_all(collector: &CxxLogCollector) -> Result<Vec<String>, String> {
    let paths = get_runtime()
        .block_on(collector.inner.collect_all())
        .map_err(|e| format!("{e}"))?;
    Ok(paths
        .into_iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect())
}

fn log_collector_collect_crash_logs(collector: &CxxLogCollector) -> Result<Vec<String>, String> {
    let paths = get_runtime()
        .block_on(collector.inner.collect_crash_logs())
        .map_err(|e| format!("{e}"))?;
    Ok(paths
        .into_iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect())
}

// ── Standalone file utilities ───────────────────────────────────────

fn calculate_file_similarity(path1: &str, path2: &str) -> Result<f64, String> {
    calculate_similarity(Path::new(path1), Path::new(path2)).map_err(|e| format!("{e}"))
}

fn read_file_with_encoding(path: &str) -> Result<String, String> {
    let io = FileIOCore::new("utf-8", "replace", 4, 8);
    get_runtime()
        .block_on(io.read_file(Path::new(path)))
        .map_err(|e| format!("{e}"))
}

fn write_file_string(path: &str, content: &str) -> Result<(), String> {
    let io = FileIOCore::new("utf-8", "replace", 4, 8);
    get_runtime()
        .block_on(io.write_file(Path::new(path), content))
        .map_err(|e| format!("{e}"))
}

// ── Report file helpers ───────────────────────────────────────────

/// Write an AUTOSCAN report adjacent to the source crash log.
///
/// Derives output path as:
/// `.../crash-*.log` -> `.../crash-*-AUTOSCAN.md`
/// and writes the provided markdown content using encoding-aware FileIOCore.
fn write_autoscan_report(log_path: &str, content: &str) -> Result<String, String> {
    let log_path = Path::new(log_path);
    let stem = log_path
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("unknown");
    let autoscan_name = format!("{}-AUTOSCAN.md", stem);
    let autoscan_path = log_path.with_file_name(autoscan_name);

    let io = FileIOCore::new("utf-8", "replace", 4, 8);
    get_runtime()
        .block_on(io.write_file(&autoscan_path, content))
        .map_err(|e| format!("{e}"))?;

    Ok(autoscan_path.to_string_lossy().to_string())
}

/// Discover AUTOSCAN report files in a directory.
///
/// Scans the given directory (non-recursively) for files matching
/// `*-AUTOSCAN.md` and returns their full paths sorted by modification
/// time (newest first).
fn discover_report_files(directory: &str) -> Vec<String> {
    let dir = Path::new(directory);
    let Ok(entries) = std::fs::read_dir(dir) else {
        return Vec::new();
    };

    let mut files: Vec<(std::time::SystemTime, String)> = entries
        .filter_map(|e| e.ok())
        .filter(|e| {
            let name = e.file_name();
            let name = name.to_string_lossy();
            name.ends_with("-AUTOSCAN.md")
        })
        .filter_map(|e| {
            let path = e.path();
            let modified = e.metadata().ok()?.modified().ok()?;
            Some((modified, path.to_string_lossy().to_string()))
        })
        .collect();

    // Sort newest first
    files.sort_by(|a, b| b.0.cmp(&a.0));
    files.into_iter().map(|(_, path)| path).collect()
}

/// Read a report file with encoding detection.
///
/// Thin wrapper over `read_file_with_encoding` that provides a
/// domain-specific name for the CXX bridge API.
fn read_report_file(path: &str) -> Result<String, String> {
    read_file_with_encoding(path)
}

#[cxx::bridge(namespace = "classic::files")]
mod ffi {
    extern "Rust" {
        type CxxBackupManager;
        type CxxGameFilesManager;
        type CxxLogCollector;

        // BackupManager
        fn backup_manager_new(game_root: &str) -> Box<CxxBackupManager>;
        fn backup_manager_exists(mgr: &CxxBackupManager, backup_type: &str) -> Result<bool>;
        fn backup_manager_create(mgr: &CxxBackupManager, backup_type: &str) -> Result<String>;
        fn backup_manager_restore(mgr: &CxxBackupManager, backup_type: &str) -> Result<u32>;
        fn backup_manager_remove(mgr: &CxxBackupManager, backup_type: &str) -> Result<()>;

        // GameFilesManager
        fn game_files_manager_new(game_root: &str, backup_root: &str) -> Box<CxxGameFilesManager>;
        fn game_files_backup(
            mgr: &CxxGameFilesManager,
            label: &str,
            patterns: &[String],
        ) -> Result<String>;
        fn game_files_restore(
            mgr: &CxxGameFilesManager,
            label: &str,
            patterns: &[String],
        ) -> Result<String>;
        fn game_files_remove(
            mgr: &CxxGameFilesManager,
            label: &str,
            patterns: &[String],
        ) -> Result<String>;

        // LogCollector
        fn log_collector_new(
            crash_logs_dir: &str,
            xse_folder: &str,
            custom_folder: &str,
        ) -> Box<CxxLogCollector>;
        fn log_collector_collect_all(collector: &CxxLogCollector) -> Result<Vec<String>>;
        fn log_collector_collect_crash_logs(collector: &CxxLogCollector) -> Result<Vec<String>>;

        // Standalone utilities
        fn calculate_file_similarity(path1: &str, path2: &str) -> Result<f64>;
        fn read_file_with_encoding(path: &str) -> Result<String>;
        fn write_file_string(path: &str, content: &str) -> Result<()>;

        // Report file helpers
        fn write_autoscan_report(log_path: &str, content: &str) -> Result<String>;
        fn discover_report_files(directory: &str) -> Vec<String>;
        fn read_report_file(path: &str) -> Result<String>;
    }
}

#[cfg(test)]
mod tests {
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

        let sim =
            calculate_file_similarity(file1.to_str().unwrap(), file2.to_str().unwrap()).unwrap();
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
}
