//! File operations bridge for CXX FFI.
//!
//! Bridges `classic_file_io_core` for backup management, game files,
//! log collection, file similarity, and encoding-aware file I/O.

use crate::runtime_support::{block_on, block_on_result};
use classic_file_io_core::FileIOCore;
use classic_file_io_core::backup::{BackupManager, BackupType};
use classic_file_io_core::game_files::GameFilesManager;
use classic_file_io_core::hash::FileHasher;
use classic_file_io_core::log_collection::LogCollector;
use classic_file_io_core::similarity::calculate_similarity;
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
    block_on_result(mgr.inner.backup_exists(bt))
}

fn backup_manager_create(mgr: &CxxBackupManager, backup_type: &str) -> Result<String, String> {
    let bt = backup_type_from_str(backup_type)?;
    let info = block_on_result(mgr.inner.create_backup(bt))?;
    Ok(format!("Backed up {} files", info.file_count))
}

fn backup_manager_restore(mgr: &CxxBackupManager, backup_type: &str) -> Result<u32, String> {
    let bt = backup_type_from_str(backup_type)?;
    let count = block_on_result(mgr.inner.restore_backup(bt))?;
    Ok(count as u32)
}

fn backup_manager_remove(mgr: &CxxBackupManager, backup_type: &str) -> Result<(), String> {
    let bt = backup_type_from_str(backup_type)?;
    block_on_result(mgr.inner.remove_backup(bt))
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
    let result = block_on_result(mgr.inner.backup(label, patterns))?;
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
    let result = block_on_result(mgr.inner.restore(label, patterns))?;
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
    let result = block_on_result(mgr.inner.remove(label, patterns))?;
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

fn log_collector_new_for_scan(
    base_folder: &str,
    yaml_dir_data: &str,
    game: &str,
    selected_game_version: &str,
    configured_docs_root: &str,
    custom_folder: &str,
) -> Box<CxxLogCollector> {
    let configured_docs_root = if configured_docs_root.trim().is_empty() {
        None
    } else {
        Some(Path::new(configured_docs_root))
    };
    let custom = if custom_folder.is_empty() {
        None
    } else {
        Some(PathBuf::from(custom_folder))
    };

    Box::new(CxxLogCollector {
        inner: LogCollector::new_for_scan(
            PathBuf::from(base_folder),
            Path::new(yaml_dir_data),
            game,
            selected_game_version,
            configured_docs_root,
            custom,
        ),
    })
}

fn log_collector_collect_all(collector: &CxxLogCollector) -> Result<Vec<String>, String> {
    let paths = block_on_result(collector.inner.collect_all())?;
    Ok(paths
        .into_iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect())
}

fn log_collector_collect_crash_logs(collector: &CxxLogCollector) -> Result<Vec<String>, String> {
    let paths = block_on_result(collector.inner.collect_crash_logs())?;
    Ok(paths
        .into_iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect())
}

// ── Targeted input resolution ───────────────────────────────────────

fn resolve_targeted_inputs(input_paths: &[String]) -> ffi::TargetedResolutionDto {
    let paths: Vec<PathBuf> = input_paths.iter().map(PathBuf::from).collect();
    let resolution = block_on(classic_file_io_core::log_collection::resolve_targeted_inputs(paths));
    ffi::TargetedResolutionDto {
        logs: resolution
            .logs
            .into_iter()
            .map(|p| p.to_string_lossy().to_string())
            .collect(),
        rejected_paths: resolution
            .rejected
            .iter()
            .map(|r| r.path.to_string_lossy().to_string())
            .collect(),
        rejected_reasons: resolution.rejected.into_iter().map(|r| r.reason).collect(),
    }
}

// ── Standalone file utilities ───────────────────────────────────────

fn calculate_file_similarity(path1: &str, path2: &str) -> Result<f64, String> {
    calculate_similarity(Path::new(path1), Path::new(path2)).map_err(|e| format!("{e}"))
}

fn read_file_with_encoding(path: &str) -> Result<String, String> {
    let io = FileIOCore::new("utf-8", "replace", 4, 8);
    block_on_result(io.read_file(Path::new(path)))
}

fn write_file_string(path: &str, content: &str) -> Result<(), String> {
    let io = FileIOCore::new("utf-8", "replace", 4, 8);
    block_on_result(io.write_file(Path::new(path), content))
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
    block_on_result(io.write_file(&autoscan_path, content))?;

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
    files.sort_by_key(|b| std::cmp::Reverse(b.0));
    files.into_iter().map(|(_, path)| path).collect()
}

/// Read a report file with encoding detection.
///
/// Thin wrapper over `read_file_with_encoding` that provides a
/// domain-specific name for the CXX bridge API.
fn read_report_file(path: &str) -> Result<String, String> {
    read_file_with_encoding(path)
}

fn hash_cache_clear() {
    FileHasher::clear_cache();
}

fn hash_cache_size() -> usize {
    hash_cache_stats().size
}

fn hash_cache_stats() -> ffi::CacheStats {
    let stats = FileHasher::cache_stats();
    ffi::CacheStats {
        hits: stats.hits,
        misses: stats.misses,
        hit_rate: stats.hit_rate,
        size: stats.size,
        capacity: stats.capacity,
    }
}

fn reset_hash_cache_stats() {
    FileHasher::reset_cache_stats();
}

#[cxx::bridge(namespace = "classic::files")]
mod ffi {
    struct CacheStats {
        hits: u64,
        misses: u64,
        hit_rate: f64,
        size: usize,
        capacity: usize,
    }

    /// Resolved targeted-input result passed across the FFI boundary.
    struct TargetedResolutionDto {
        /// Deduplicated crash-log paths that were accepted.
        logs: Vec<String>,
        /// Original paths of rejected inputs (parallel with `rejected_reasons`).
        rejected_paths: Vec<String>,
        /// Human-readable rejection reasons (parallel with `rejected_paths`).
        rejected_reasons: Vec<String>,
    }

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
        fn log_collector_new_for_scan(
            base_folder: &str,
            yaml_dir_data: &str,
            game: &str,
            selected_game_version: &str,
            configured_docs_root: &str,
            custom_folder: &str,
        ) -> Box<CxxLogCollector>;
        fn log_collector_collect_all(collector: &CxxLogCollector) -> Result<Vec<String>>;
        fn log_collector_collect_crash_logs(collector: &CxxLogCollector) -> Result<Vec<String>>;

        // Targeted input resolution
        fn resolve_targeted_inputs(input_paths: &[String]) -> TargetedResolutionDto;

        // Standalone utilities
        fn calculate_file_similarity(path1: &str, path2: &str) -> Result<f64>;
        fn hash_cache_clear();
        fn hash_cache_size() -> usize;
        fn hash_cache_stats() -> CacheStats;
        fn reset_hash_cache_stats();
        fn read_file_with_encoding(path: &str) -> Result<String>;
        fn write_file_string(path: &str, content: &str) -> Result<()>;

        // Report file helpers
        fn write_autoscan_report(log_path: &str, content: &str) -> Result<String>;
        fn discover_report_files(directory: &str) -> Vec<String>;
        fn read_report_file(path: &str) -> Result<String>;
    }
}

#[cfg(test)]
#[path = "files_tests.rs"]
mod tests;
