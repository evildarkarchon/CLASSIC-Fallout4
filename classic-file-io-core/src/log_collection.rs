//! Log collection and organization utilities
//!
//! This module provides functionality to collect crash logs from various locations
//! (game documents folder, working directory, custom paths) and organize them into
//! a central Crash Logs directory for processing.

use std::path::{Path, PathBuf};
use tokio::fs;
use tracing::debug;

use crate::error::{FileIOError, Result};

/// File pattern constants
pub const CRASH_LOG_PATTERN: &str = "crash-*.log";
pub const CRASH_AUTOSCAN_PATTERN: &str = "crash-*-AUTOSCAN.md";

/// Log collector for organizing crash logs from multiple sources
///
/// The LogCollector handles:
/// - Creating necessary directory structure (Crash Logs, Pastebin)
/// - Moving logs from working directory to Crash Logs
/// - Copying logs from game's XSE folder (My Games) to Crash Logs
/// - Collecting logs from custom scan directories
///
/// # Example
///
/// ```no_run
/// use std::path::PathBuf;
/// use classic_file_io_core::LogCollector;
///
/// # async fn example() -> anyhow::Result<()> {
/// let collector = LogCollector::new(
///     PathBuf::from("."),
///     Some(PathBuf::from("C:/Users/.../My Games/Fallout4/F4SE")),
///     Some(PathBuf::from("D:/CustomLogs")),
/// );
///
/// // Collect and organize all logs
/// let log_files = collector.collect_all().await?;
/// println!("Found {} crash logs", log_files.len());
/// # Ok(())
/// # }
/// ```
pub struct LogCollector {
    /// Base working directory (usually current directory)
    base_folder: PathBuf,
    /// Crash Logs directory (base_folder/Crash Logs)
    crash_logs_dir: PathBuf,
    /// Pastebin subdirectory (crash_logs_dir/Pastebin)
    pastebin_dir: PathBuf,
    /// Game's XSE folder (e.g., My Games/Fallout4/F4SE) - logs are COPIED from here
    xse_folder: Option<PathBuf>,
    /// Custom scan folder - additional location to search for logs
    custom_folder: Option<PathBuf>,
}

impl LogCollector {
    /// Create a new LogCollector with the specified paths
    ///
    /// # Arguments
    ///
    /// * `base_folder` - Working directory where Crash Logs folder will be created
    /// * `xse_folder` - Optional path to game's XSE folder (e.g., My Games/Fallout4/F4SE)
    /// * `custom_folder` - Optional path to custom scan directory
    pub fn new(
        base_folder: PathBuf,
        xse_folder: Option<PathBuf>,
        custom_folder: Option<PathBuf>,
    ) -> Self {
        let crash_logs_dir = base_folder.join("Crash Logs");
        let pastebin_dir = crash_logs_dir.join("Pastebin");

        Self {
            base_folder,
            crash_logs_dir,
            pastebin_dir,
            xse_folder,
            custom_folder,
        }
    }

    /// Create a new LogCollector using the current directory as base
    pub fn with_current_dir(
        xse_folder: Option<PathBuf>,
        custom_folder: Option<PathBuf>,
    ) -> Self {
        Self::new(std::env::current_dir().unwrap_or_default(), xse_folder, custom_folder)
    }

    /// Ensure required directory structure exists
    ///
    /// Creates:
    /// - {base_folder}/Crash Logs
    /// - {base_folder}/Crash Logs/Pastebin
    async fn ensure_directories(&self) -> Result<()> {
        fs::create_dir_all(&self.crash_logs_dir).await.map_err(|e| {
            FileIOError::Io(format!(
                "Failed to create Crash Logs directory at {}: {}",
                self.crash_logs_dir.display(),
                e
            ))
        })?;

        fs::create_dir_all(&self.pastebin_dir).await.map_err(|e| {
            FileIOError::Io(format!(
                "Failed to create Pastebin directory at {}: {}",
                self.pastebin_dir.display(),
                e
            ))
        })?;

        debug!("Ensured directory structure exists");
        Ok(())
    }

    /// Move files matching a pattern from source to target directory
    ///
    /// Files are only moved if they don't already exist in the target directory.
    /// This prevents overwriting existing files.
    ///
    /// # Arguments
    ///
    /// * `source_dir` - Source directory to search
    /// * `target_dir` - Target directory to move files to
    /// * `pattern` - Glob pattern to match files (e.g., "crash-*.log")
    ///
    /// # Returns
    ///
    /// Number of files successfully moved
    async fn move_files(
        &self,
        source_dir: &Path,
        target_dir: &Path,
        pattern: &str,
    ) -> Result<usize> {
        let mut moved_count = 0;

        if !source_dir.exists() {
            return Ok(0);
        }

        // Use glob pattern matching
        let pattern_path = source_dir.join(pattern);
        let pattern_str = pattern_path.to_string_lossy();

        for entry in glob::glob(&pattern_str).map_err(|e| {
            FileIOError::Io(format!("Invalid glob pattern '{}': {}", pattern, e))
        })? {
            let source_path = entry.map_err(|e| {
                FileIOError::Io(format!("Failed to read glob entry: {}", e))
            })?;

            if let Some(filename) = source_path.file_name() {
                let target_path = target_dir.join(filename);

                // Only move if target doesn't exist
                if !target_path.exists() {
                    fs::rename(&source_path, &target_path).await.map_err(|e| {
                        FileIOError::Io(format!(
                            "Failed to move {} to {}: {}",
                            source_path.display(),
                            target_path.display(),
                            e
                        ))
                    })?;
                    moved_count += 1;
                    debug!("Moved: {} -> {}", source_path.display(), target_path.display());
                }
            }
        }

        Ok(moved_count)
    }

    /// Copy files matching a pattern from source to target directory
    ///
    /// Files are only copied if they don't already exist in the target directory.
    /// Uses `copy2` semantics to preserve file metadata (timestamps, permissions).
    ///
    /// # Arguments
    ///
    /// * `source_dir` - Source directory to search (optional)
    /// * `target_dir` - Target directory to copy files to
    /// * `pattern` - Glob pattern to match files (e.g., "crash-*.log")
    ///
    /// # Returns
    ///
    /// Number of files successfully copied
    async fn copy_files(
        &self,
        source_dir: Option<&Path>,
        target_dir: &Path,
        pattern: &str,
    ) -> Result<usize> {
        let mut copied_count = 0;

        let source_dir = match source_dir {
            Some(dir) if dir.exists() && dir.is_dir() => dir,
            _ => return Ok(0),
        };

        // Use glob pattern matching
        let pattern_path = source_dir.join(pattern);
        let pattern_str = pattern_path.to_string_lossy();

        for entry in glob::glob(&pattern_str).map_err(|e| {
            FileIOError::Io(format!("Invalid glob pattern '{}': {}", pattern, e))
        })? {
            let source_path = entry.map_err(|e| {
                FileIOError::Io(format!("Failed to read glob entry: {}", e))
            })?;

            if let Some(filename) = source_path.file_name() {
                let target_path = target_dir.join(filename);

                // Only copy if target doesn't exist
                if !target_path.exists() {
                    fs::copy(&source_path, &target_path).await.map_err(|e| {
                        FileIOError::Io(format!(
                            "Failed to copy {} to {}: {}",
                            source_path.display(),
                            target_path.display(),
                            e
                        ))
                    })?;
                    copied_count += 1;
                    debug!("Copied: {} -> {}", source_path.display(), target_path.display());
                }
            }
        }

        Ok(copied_count)
    }

    /// Move crash logs and AUTOSCAN reports from base folder to Crash Logs directory
    ///
    /// This organizes logs that may have been generated in the working directory.
    ///
    /// # Returns
    ///
    /// Total number of files moved
    pub async fn move_from_base_folder(&self) -> Result<usize> {
        let logs_moved = self
            .move_files(&self.base_folder, &self.crash_logs_dir, CRASH_LOG_PATTERN)
            .await?;

        let reports_moved = self
            .move_files(&self.base_folder, &self.crash_logs_dir, CRASH_AUTOSCAN_PATTERN)
            .await?;

        let total = logs_moved + reports_moved;
        if total > 0 {
            debug!("Moved {} files from base folder to Crash Logs", total);
        }

        Ok(total)
    }

    /// Copy crash logs from game's XSE folder (My Games directory) to Crash Logs
    ///
    /// This is where the game stores crash logs. We copy (not move) them to preserve
    /// the originals in case the user wants to reference them.
    ///
    /// # Returns
    ///
    /// Number of files copied
    pub async fn copy_from_xse_folder(&self) -> Result<usize> {
        let copied = self
            .copy_files(
                self.xse_folder.as_deref(),
                &self.crash_logs_dir,
                CRASH_LOG_PATTERN,
            )
            .await?;

        if copied > 0 {
            debug!("Copied {} crash logs from XSE folder", copied);
        }

        Ok(copied)
    }

    /// Collect all crash log file paths for processing
    ///
    /// This searches for crash-*.log files in:
    /// - Crash Logs directory (after moving/copying operations)
    /// - Custom scan folder (if configured)
    ///
    /// # Returns
    ///
    /// Vector of paths to all crash log files found
    pub async fn collect_crash_logs(&self) -> Result<Vec<PathBuf>> {
        let mut crash_files = Vec::new();

        // Collect from Crash Logs directory (recursively)
        if self.crash_logs_dir.exists() {
            let pattern = self.crash_logs_dir.join("**").join(CRASH_LOG_PATTERN);
            let pattern_str = pattern.to_string_lossy();

            for entry in glob::glob(&pattern_str).map_err(|e| {
                FileIOError::Io(format!("Invalid glob pattern: {}", e))
            })? {
                let path = entry.map_err(|e| {
                    FileIOError::Io(format!("Failed to read glob entry: {}", e))
                })?;
                crash_files.push(path);
            }
        }

        // Collect from custom folder if configured
        if let Some(custom_folder) = &self.custom_folder {
            if custom_folder.exists() && custom_folder.is_dir() {
                let pattern = custom_folder.join(CRASH_LOG_PATTERN);
                let pattern_str = pattern.to_string_lossy();

                for entry in glob::glob(&pattern_str).map_err(|e| {
                    FileIOError::Io(format!("Invalid glob pattern: {}", e))
                })? {
                    let path = entry.map_err(|e| {
                        FileIOError::Io(format!("Failed to read glob entry: {}", e))
                    })?;
                    crash_files.push(path);
                }
            }
        }

        debug!("Collected {} crash log files", crash_files.len());
        Ok(crash_files)
    }

    /// Execute full log collection workflow
    ///
    /// This performs all log collection steps in order:
    /// 1. Ensure directory structure exists
    /// 2. Move logs from base folder to Crash Logs
    /// 3. Copy logs from XSE folder to Crash Logs
    /// 4. Collect all crash log paths for processing
    ///
    /// # Returns
    ///
    /// Vector of paths to all crash log files ready for processing
    ///
    /// # Example
    ///
    /// ```no_run
    /// use std::path::PathBuf;
    /// use classic_file_io_core::LogCollector;
    ///
    /// # async fn example() -> anyhow::Result<()> {
    /// let collector = LogCollector::new(
    ///     PathBuf::from("."),
    ///     Some(PathBuf::from("C:/Users/.../My Games/Fallout4/F4SE")),
    ///     None,
    /// );
    ///
    /// let logs = collector.collect_all().await?;
    /// println!("Ready to process {} crash logs", logs.len());
    /// # Ok(())
    /// # }
    /// ```
    pub async fn collect_all(&self) -> Result<Vec<PathBuf>> {
        debug!("Starting log collection workflow");

        // Step 1: Ensure directories exist
        self.ensure_directories().await?;

        // Step 2: Move logs from base folder
        let moved = self.move_from_base_folder().await?;
        if moved > 0 {
            debug!("Organized {} files into Crash Logs directory", moved);
        }

        // Step 3: Copy logs from XSE folder
        let copied = self.copy_from_xse_folder().await?;
        if copied > 0 {
            debug!("Retrieved {} crash logs from game directory", copied);
        }

        // Step 4: Collect all crash log paths
        let crash_files = self.collect_crash_logs().await?;

        debug!(
            "Log collection complete: {} crash logs ready for processing",
            crash_files.len()
        );

        Ok(crash_files)
    }

    /// Get the path to the Crash Logs directory
    pub fn crash_logs_dir(&self) -> &Path {
        &self.crash_logs_dir
    }

    /// Get the path to the Pastebin subdirectory
    pub fn pastebin_dir(&self) -> &Path {
        &self.pastebin_dir
    }
}

#[cfg(test)]
mod tests {
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
        tokio::fs::write(&test_log, b"test crash log").await.unwrap();

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
}
