// Results tab handlers - Report list management and operations
//
// This module handles all operations for the Results tab including:
// - Scanning for AUTOSCAN reports in multiple locations
// - Deleting reports (both .md and .log files)
// - Opening the reports folder in file explorer
// - File watching with debouncing for auto-refresh

use anyhow::{Context, Result};
use notify::{Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver};
use std::time::Duration;
use walkdir::WalkDir;

use crate::app_state::SharedAppState;
use crate::models::ReportItem;

/// Scan for AUTOSCAN report files in multiple locations
///
/// Searches for *-AUTOSCAN.md files in:
/// - {local_dir}/Crash Logs/
/// - Custom scan path from settings
/// - {local_dir}/CLASSIC Backup/Unsolved Logs/
///
/// Reports are sorted by FILENAME descending (not date modified)
/// to maintain correct chronological order even with parallel processing.
///
/// # Arguments
/// * `state` - Shared application state for path configuration
///
/// # Returns
/// * `Ok(Vec<ReportItem>)` - List of reports sorted by filename descending
/// * `Err(anyhow::Error)` - Failed to scan for reports
pub fn scan_reports(state: SharedAppState) -> Result<Vec<ReportItem>> {
    tracing::info!("Scanning for AUTOSCAN reports...");

    let state_guard = state.read();
    let mut report_paths: HashSet<PathBuf> = HashSet::new();

    // Location 1: Crash Logs folder in local directory
    if let Some(docs_root) = state_guard.docs_root() {
        let crash_logs_dir = docs_root.join("Crash Logs");
        if crash_logs_dir.exists() {
            tracing::debug!("Scanning: {}", crash_logs_dir.display());
            scan_directory(&crash_logs_dir, &mut report_paths)?;
        }
    }

    // Location 2: Custom scan folder from settings
    if let Some(scan_folder) = state_guard.scan_folder() {
        if scan_folder.exists() {
            tracing::debug!("Scanning custom path: {}", scan_folder.display());
            scan_directory(scan_folder, &mut report_paths)?;
        }
    }

    // Location 3: Backup folder for unsolved logs
    if let Some(docs_root) = state_guard.docs_root() {
        let backup_dir = docs_root.join("CLASSIC Backup").join("Unsolved Logs");
        if backup_dir.exists() {
            tracing::debug!("Scanning backup: {}", backup_dir.display());
            scan_directory(&backup_dir, &mut report_paths)?;
        }
    }

    // Convert paths to ReportItem structs
    let mut reports: Vec<ReportItem> = report_paths
        .into_iter()
        .filter_map(|path| match ReportItem::from_path(path) {
            Ok(item) => Some(item),
            Err(e) => {
                tracing::warn!("Failed to create ReportItem: {}", e);
                None
            }
        })
        .collect();

    // IMPORTANT: Sort by FILENAME descending (not date modified)
    // Filenames contain the actual crash timestamp, which is the true chronological order
    // This ensures correct ordering even when parallel processing causes analysis to finish out of order
    reports.sort_by(|a, b| b.filename.cmp(&a.filename));

    tracing::info!("Found {} report(s)", reports.len());
    Ok(reports)
}

/// Scan a directory for AUTOSCAN reports
///
/// Searches for files matching "*-AUTOSCAN.md" pattern
fn scan_directory(dir: &Path, reports: &mut HashSet<PathBuf>) -> Result<()> {
    for entry in WalkDir::new(dir)
        .max_depth(2)  // Don't recurse too deep
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let path = entry.path();

        // Check if it's an AUTOSCAN report
        if let Some(filename) = path.file_name().and_then(|n| n.to_str()) {
            if filename.ends_with("-AUTOSCAN.md") {
                reports.insert(path.to_path_buf());
            }
        }
    }

    Ok(())
}

/// Delete a report file
///
/// Deletes both the .md report file and the corresponding .log file if it exists.
///
/// # Arguments
/// * `report_path` - Path to the report file to delete
///
/// # Returns
/// * `Ok(())` - Successfully deleted report
/// * `Err(anyhow::Error)` - Failed to delete report
pub fn delete_report(report_path: &Path) -> Result<()> {
    tracing::info!("Deleting report: {}", report_path.display());

    // Delete the .md file
    if report_path.exists() {
        std::fs::remove_file(report_path)
            .with_context(|| format!("Failed to delete report: {}", report_path.display()))?;
        tracing::debug!("Deleted: {}", report_path.display());
    }

    // Also delete the corresponding .log file if it exists
    let log_path = report_path.with_extension("log");
    if log_path.exists() {
        std::fs::remove_file(&log_path)
            .with_context(|| format!("Failed to delete log: {}", log_path.display()))?;
        tracing::debug!("Deleted: {}", log_path.display());
    }

    tracing::info!("Report deleted successfully");
    Ok(())
}

/// Open the reports folder in file explorer
///
/// Opens the Crash Logs folder in the system file explorer.
///
/// # Arguments
/// * `state` - Shared application state for path configuration
///
/// # Returns
/// * `Ok(())` - Successfully opened folder
/// * `Err(anyhow::Error)` - Failed to open folder
pub fn open_reports_folder(state: SharedAppState) -> Result<()> {
    let state_guard = state.read();

    let crash_logs_dir = state_guard
        .docs_root()
        .map(|docs| docs.join("Crash Logs"))
        .context("Documents root not configured")?;

    if !crash_logs_dir.exists() {
        anyhow::bail!("Crash Logs folder does not exist: {}", crash_logs_dir.display());
    }

    tracing::info!("Opening folder: {}", crash_logs_dir.display());

    open::that(&crash_logs_dir)
        .with_context(|| format!("Failed to open folder: {}", crash_logs_dir.display()))?;

    Ok(())
}

/// File watcher for auto-refresh functionality
///
/// Monitors report directories for changes and triggers refresh callbacks.
#[allow(dead_code)]
pub struct ReportWatcher {
    _watcher: RecommendedWatcher,
    receiver: Receiver<notify::Result<Event>>,
}

impl ReportWatcher {
    /// Create a new file watcher for report directories
    ///
    /// Sets up file system monitoring for all report locations.
    ///
    /// # Arguments
    /// * `state` - Shared application state for path configuration
    ///
    /// # Returns
    /// * `Ok(ReportWatcher)` - File watcher ready to receive events
    /// * `Err(anyhow::Error)` - Failed to create watcher
    #[allow(dead_code)]
    pub fn new(state: SharedAppState) -> Result<Self> {
        let (tx, receiver) = channel();

        let mut watcher = notify::recommended_watcher(tx)
            .context("Failed to create file system watcher")?;

        // Watch all report locations
        let state_guard = state.read();

        // Location 1: Crash Logs folder
        if let Some(docs_root) = state_guard.docs_root() {
            let crash_logs_dir = docs_root.join("Crash Logs");
            if crash_logs_dir.exists() {
                watcher.watch(&crash_logs_dir, RecursiveMode::NonRecursive)
                    .with_context(|| format!("Failed to watch: {}", crash_logs_dir.display()))?;
                tracing::debug!("Watching: {}", crash_logs_dir.display());
            }
        }

        // Location 2: Custom scan folder
        if let Some(scan_folder) = state_guard.scan_folder() {
            if scan_folder.exists() {
                watcher.watch(scan_folder, RecursiveMode::NonRecursive)
                    .with_context(|| format!("Failed to watch: {}", scan_folder.display()))?;
                tracing::debug!("Watching: {}", scan_folder.display());
            }
        }

        // Location 3: Backup folder
        if let Some(docs_root) = state_guard.docs_root() {
            let backup_dir = docs_root.join("CLASSIC Backup").join("Unsolved Logs");
            if backup_dir.exists() {
                watcher.watch(&backup_dir, RecursiveMode::NonRecursive)
                    .with_context(|| format!("Failed to watch: {}", backup_dir.display()))?;
                tracing::debug!("Watching: {}", backup_dir.display());
            }
        }

        Ok(Self {
            _watcher: watcher,
            receiver,
        })
    }

    /// Check for file system events (non-blocking)
    ///
    /// Returns true if there were any relevant changes (file creation, modification, deletion)
    #[allow(dead_code)]
    pub fn check_for_changes(&self) -> bool {
        let mut has_changes = false;

        // Drain all pending events
        while let Ok(result) = self.receiver.try_recv() {
            if let Ok(event) = result {
                // Only care about file create, modify, and delete events
                if matches!(
                    event.kind,
                    EventKind::Create(_) | EventKind::Modify(_) | EventKind::Remove(_)
                ) {
                    has_changes = true;
                    tracing::debug!("File system event: {:?}", event.kind);
                }
            }
        }

        has_changes
    }
}

/// Debounced refresh helper
///
/// Prevents rapid successive refreshes by tracking the last refresh time
#[allow(dead_code)]
pub struct RefreshDebouncer {
    last_refresh: std::time::Instant,
    debounce_duration: Duration,
}

impl RefreshDebouncer {
    /// Create a new debouncer with specified debounce duration
    #[allow(dead_code)]
    pub fn new(debounce_duration: Duration) -> Self {
        Self {
            last_refresh: std::time::Instant::now() - debounce_duration,  // Allow immediate first refresh
            debounce_duration,
        }
    }

    /// Check if enough time has passed since last refresh
    ///
    /// Returns true if a refresh should be performed
    #[allow(dead_code)]
    pub fn should_refresh(&mut self) -> bool {
        let elapsed = self.last_refresh.elapsed();
        if elapsed >= self.debounce_duration {
            self.last_refresh = std::time::Instant::now();
            true
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_debouncer() {
        let mut debouncer = RefreshDebouncer::new(Duration::from_millis(500));

        // First refresh should be allowed immediately
        assert!(debouncer.should_refresh());

        // Immediate second refresh should be blocked
        assert!(!debouncer.should_refresh());

        // After waiting, should be allowed
        std::thread::sleep(Duration::from_millis(600));
        assert!(debouncer.should_refresh());
    }
}
