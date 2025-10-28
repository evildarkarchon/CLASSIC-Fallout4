//! Scan coordination utilities for log scanning operations.
//!
//! This module provides common functionality for coordinating crash log
//! scanning across different UI interfaces (CLI, TUI, GUI). It handles
//! the shared logic for XSE folder discovery, configuration building,
//! and statistics collection.
//!
//! # Examples
//!
//! ```no_run
//! use classic_ui_shared::scan_coordinator::{discover_xse_folder, ScanStatistics};
//! use std::path::PathBuf;
//!
//! # tokio_test::block_on(async {
//! let game_root = PathBuf::from("C:\\Games\\Fallout4");
//! let xse_folder = discover_xse_folder(&game_root).await?;
//! println!("Found XSE folder: {}", xse_folder.display());
//! # Ok::<(), anyhow::Error>(())
//! # });
//! ```

use anyhow::{Context, Result};
use std::path::{Path, PathBuf};

/// Statistics collected during a scan operation
#[derive(Debug, Clone, Default)]
pub struct ScanStatistics {
    /// Total number of crash logs processed
    pub total_logs: usize,
    /// Number of logs successfully analyzed
    pub analyzed_logs: usize,
    /// Number of logs that failed to analyze
    pub failed_logs: usize,
    /// Total number of plugins found across all logs
    pub total_plugins: usize,
    /// Total number of records found across all logs
    pub total_records: usize,
    /// Duration of the scan operation in milliseconds
    pub duration_ms: u64,
}

impl ScanStatistics {
    /// Create a new statistics instance
    pub fn new() -> Self {
        Self::default()
    }

    /// Get the success rate as a percentage
    pub fn success_rate(&self) -> f64 {
        if self.total_logs == 0 {
            0.0
        } else {
            (self.analyzed_logs as f64 / self.total_logs as f64) * 100.0
        }
    }

    /// Get the failure rate as a percentage
    pub fn failure_rate(&self) -> f64 {
        if self.total_logs == 0 {
            0.0
        } else {
            (self.failed_logs as f64 / self.total_logs as f64) * 100.0
        }
    }

    /// Format the statistics as a human-readable string
    pub fn format(&self) -> String {
        format!(
            "Scanned {} logs ({} analyzed, {} failed) - {} plugins, {} records - Duration: {}ms",
            self.total_logs,
            self.analyzed_logs,
            self.failed_logs,
            self.total_plugins,
            self.total_records,
            self.duration_ms
        )
    }
}

/// Discover the XSE folder (F4SE/SKSE) in the game directory.
///
/// This function searches for script extender folders in the game root directory
/// and returns the path to the crash logs folder.
///
/// # Arguments
///
/// * `game_root` - The root directory of the game installation
///
/// # Returns
///
/// Returns the path to the XSE crash logs folder, or an error if not found.
///
/// # Errors
///
/// Returns an error if:
/// - Game root directory doesn't exist
/// - No XSE folder is found (F4SE or SKSE64)
/// - XSE folder exists but doesn't contain a Logs directory
///
/// # Examples
///
/// ```no_run
/// use classic_ui_shared::scan_coordinator::discover_xse_folder;
/// use std::path::PathBuf;
///
/// # tokio_test::block_on(async {
/// let game_root = PathBuf::from("C:\\Games\\Fallout4");
/// let xse_folder = discover_xse_folder(&game_root).await?;
/// # Ok::<(), anyhow::Error>(())
/// # });
/// ```
pub async fn discover_xse_folder<P: AsRef<Path>>(game_root: P) -> Result<PathBuf> {
    let game_root = game_root.as_ref();

    // Verify game root exists
    if !game_root.exists() {
        return Err(anyhow::anyhow!(
            "Game root directory does not exist: {}",
            game_root.display()
        ));
    }

    tracing::debug!("Searching for XSE folder in: {}", game_root.display());

    // Try F4SE first (Fallout 4)
    let f4se_logs = game_root.join("Data").join("F4SE").join("Logs");
    if f4se_logs.exists() && f4se_logs.is_dir() {
        tracing::info!("Found F4SE logs folder: {}", f4se_logs.display());
        return Ok(f4se_logs);
    }

    // Try SKSE64 (Skyrim Special Edition)
    let skse_logs = game_root.join("Data").join("SKSE").join("Logs");
    if skse_logs.exists() && skse_logs.is_dir() {
        tracing::info!("Found SKSE logs folder: {}", skse_logs.display());
        return Ok(skse_logs);
    }

    // Try SKSE (Skyrim LE)
    let skse_le_logs = game_root.join("Data").join("SKSE").join("Logs");
    if skse_le_logs.exists() && skse_le_logs.is_dir() {
        tracing::info!("Found SKSE (LE) logs folder: {}", skse_le_logs.display());
        return Ok(skse_le_logs);
    }

    Err(anyhow::anyhow!(
        "No script extender (F4SE/SKSE) folder found in game directory: {}",
        game_root.display()
    ))
}

/// Discover all crash log files in a directory.
///
/// This function scans a directory for crash log files matching the expected
/// naming patterns (e.g., "crash-*.log").
///
/// # Arguments
///
/// * `logs_dir` - Directory to scan for crash logs
///
/// # Returns
///
/// Returns a vector of paths to crash log files, or an error if the directory
/// cannot be read.
///
/// # Errors
///
/// Returns an error if:
/// - Directory doesn't exist
/// - Directory cannot be read
///
/// # Examples
///
/// ```no_run
/// use classic_ui_shared::scan_coordinator::discover_crash_logs;
/// use std::path::PathBuf;
///
/// # tokio_test::block_on(async {
/// let logs_dir = PathBuf::from("C:\\Games\\Fallout4\\Data\\F4SE\\Logs");
/// let log_files = discover_crash_logs(&logs_dir).await?;
/// println!("Found {} crash logs", log_files.len());
/// # Ok::<(), anyhow::Error>(())
/// # });
/// ```
pub async fn discover_crash_logs<P: AsRef<Path>>(logs_dir: P) -> Result<Vec<PathBuf>> {
    let logs_dir = logs_dir.as_ref();

    if !logs_dir.exists() {
        return Err(anyhow::anyhow!(
            "Logs directory does not exist: {}",
            logs_dir.display()
        ));
    }

    tracing::debug!("Scanning for crash logs in: {}", logs_dir.display());

    let mut log_files = Vec::new();

    // Read directory entries
    let entries = tokio::fs::read_dir(logs_dir)
        .await
        .with_context(|| format!("Failed to read logs directory: {}", logs_dir.display()))?;

    let mut entries = entries;
    while let Some(entry) = entries
        .next_entry()
        .await
        .with_context(|| format!("Failed to read directory entry in: {}", logs_dir.display()))?
    {
        let path = entry.path();

        // Check if it's a file
        if !path.is_file() {
            continue;
        }

        // Check if filename matches crash log pattern
        if let Some(filename) = path.file_name() {
            let filename_str = filename.to_string_lossy();
            if filename_str.starts_with("crash-") && filename_str.ends_with(".log") {
                tracing::trace!("Found crash log: {}", path.display());
                log_files.push(path);
            }
        }
    }

    tracing::info!("Found {} crash log files", log_files.len());
    Ok(log_files)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scan_statistics_new() {
        let stats = ScanStatistics::new();
        assert_eq!(stats.total_logs, 0);
        assert_eq!(stats.analyzed_logs, 0);
        assert_eq!(stats.failed_logs, 0);
        assert_eq!(stats.total_plugins, 0);
        assert_eq!(stats.total_records, 0);
        assert_eq!(stats.duration_ms, 0);
    }

    #[test]
    fn test_scan_statistics_success_rate() {
        let stats = ScanStatistics {
            total_logs: 10,
            analyzed_logs: 8,
            failed_logs: 2,
            ..Default::default()
        };

        assert_eq!(stats.success_rate(), 80.0);
        assert_eq!(stats.failure_rate(), 20.0);
    }

    #[test]
    fn test_scan_statistics_zero_logs() {
        let stats = ScanStatistics::new();
        assert_eq!(stats.success_rate(), 0.0);
        assert_eq!(stats.failure_rate(), 0.0);
    }

    #[test]
    fn test_scan_statistics_format() {
        let stats = ScanStatistics {
            total_logs: 5,
            analyzed_logs: 4,
            failed_logs: 1,
            total_plugins: 120,
            total_records: 450,
            duration_ms: 1500,
        };

        let formatted = stats.format();
        assert!(formatted.contains("5 logs"));
        assert!(formatted.contains("4 analyzed"));
        assert!(formatted.contains("1 failed"));
        assert!(formatted.contains("120 plugins"));
        assert!(formatted.contains("450 records"));
        assert!(formatted.contains("1500ms"));
    }

    #[tokio::test]
    async fn test_discover_xse_folder_nonexistent() {
        let result = discover_xse_folder("/nonexistent/path").await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_discover_crash_logs_nonexistent() {
        let result = discover_crash_logs("/nonexistent/path").await;
        assert!(result.is_err());
    }

    // Note: More comprehensive tests would require setting up temporary
    // directory structures with mock game installations. Those should be
    // in integration tests.
}
