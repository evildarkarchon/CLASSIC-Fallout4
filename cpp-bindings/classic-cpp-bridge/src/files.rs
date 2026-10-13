//! File operations bridge for CXX FFI.
//!
//! Bridges `classic_file_io_core` for encoding-aware file I/O, and
//! `classic_resource_core` for the game-target backup (moved from file I/O in
//! #250), plus the GUI's AUTOSCAN report discovery. The bridge is
//! consumer-driven: game-file operations, Crash Log collection, file
//! similarity and hash-cache controls stay Rust-only until a frontend calls
//! them.

use crate::runtime_support::block_on_result;
use classic_file_io_core::FileIOCore;
use classic_resource_core::backup::{BackupManager, BackupType};
use std::path::{Path, PathBuf};

/// Opaque wrapper around BackupManager.
pub struct CxxBackupManager {
    inner: BackupManager,
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

// ── Standalone file utilities ───────────────────────────────────────

fn write_file_string(path: &str, content: &str) -> Result<(), String> {
    let io = FileIOCore::new("utf-8", "replace", 4, 8);
    block_on_result(io.write_file(Path::new(path), content))
}

// ── Report file helpers ───────────────────────────────────────────

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
            let metadata = e.metadata().ok()?;
            if !metadata.is_file() {
                return None;
            }
            let modified = metadata.modified().ok()?;
            Some((modified, path.to_string_lossy().to_string()))
        })
        .collect();

    // Sort newest first
    files.sort_by_key(|b| std::cmp::Reverse(b.0));
    files.into_iter().map(|(_, path)| path).collect()
}

/// Read a report file with encoding detection (UTF-8, replacing invalid bytes).
fn read_report_file(path: &str) -> Result<String, String> {
    let io = FileIOCore::new("utf-8", "replace", 4, 8);
    block_on_result(io.read_file(Path::new(path)))
}

#[cxx::bridge(namespace = "classic::files")]
mod ffi {
    extern "Rust" {
        type CxxBackupManager;

        // BackupManager
        fn backup_manager_new(game_root: &str) -> Box<CxxBackupManager>;
        fn backup_manager_exists(mgr: &CxxBackupManager, backup_type: &str) -> Result<bool>;
        fn backup_manager_create(mgr: &CxxBackupManager, backup_type: &str) -> Result<String>;
        fn backup_manager_restore(mgr: &CxxBackupManager, backup_type: &str) -> Result<u32>;
        fn backup_manager_remove(mgr: &CxxBackupManager, backup_type: &str) -> Result<()>;

        // Standalone utilities
        fn write_file_string(path: &str, content: &str) -> Result<()>;

        // Report file helpers
        fn discover_report_files(directory: &str) -> Vec<String>;
        fn read_report_file(path: &str) -> Result<String>;
    }
}

#[cfg(test)]
#[path = "files_tests.rs"]
mod tests;
