//! Log collection and organization utilities
//!
//! This module provides functionality to collect crash logs from various locations
//! (game documents folder, working directory, custom paths) and organize them into
//! a central Crash Logs directory for processing.

use std::collections::HashSet;
use std::path::{Path, PathBuf};
use tokio::fs;
use tracing::debug;

use classic_operation_context::cancellation_requested;
use classic_xse_core::resolve_xse_folder_for_scan;

use crate::error::{FileIOError, Result};

/// File pattern for standard crash log files
pub const CRASH_LOG_PATTERN: &str = "crash-*.log";
/// File pattern for AUTOSCAN report files generated during crash analysis
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

    /// Create a new LogCollector for the standard crash-scan workflow.
    ///
    /// This resolves the configured game XSE folder in Rust and keeps any
    /// custom scan folder additive instead of treating it as an XSE replacement.
    #[must_use]
    pub fn new_for_scan(
        base_folder: PathBuf,
        yaml_dir_data: impl AsRef<Path>,
        game: &str,
        selected_game_version: &str,
        configured_docs_root: Option<&Path>,
        custom_folder: Option<PathBuf>,
    ) -> Self {
        let xse_folder = resolve_xse_folder_for_scan(
            yaml_dir_data,
            game,
            selected_game_version,
            configured_docs_root,
        );

        Self::new(base_folder, xse_folder, custom_folder)
    }

    /// Create a new LogCollector using the current directory as base
    pub fn with_current_dir(xse_folder: Option<PathBuf>, custom_folder: Option<PathBuf>) -> Self {
        Self::new(
            std::env::current_dir().unwrap_or_default(),
            xse_folder,
            custom_folder,
        )
    }

    /// Ensure required directory structure exists
    ///
    /// Creates:
    /// - {base_folder}/Crash Logs
    /// - {base_folder}/Crash Logs/Pastebin
    ///
    /// Cancellation is checked only between completed directory operations.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] when either directory cannot be created.
    async fn ensure_directories(&self) -> Result<bool> {
        if cancellation_requested() {
            return Ok(false);
        }

        fs::create_dir_all(&self.crash_logs_dir)
            .await
            .map_err(|e| {
                FileIOError::Io(format!(
                    "Failed to create Crash Logs directory at {}: {}",
                    self.crash_logs_dir.display(),
                    e
                ))
            })?;
        if cancellation_requested() {
            return Ok(false);
        }

        fs::create_dir_all(&self.pastebin_dir).await.map_err(|e| {
            FileIOError::Io(format!(
                "Failed to create Pastebin directory at {}: {}",
                self.pastebin_dir.display(),
                e
            ))
        })?;
        if cancellation_requested() {
            return Ok(false);
        }

        debug!("Ensured directory structure exists");
        Ok(true)
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
    /// `Some` contains the number of files successfully moved. `None` means
    /// cancellation was observed after the current atomic rename completed.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] for invalid glob patterns, unreadable glob
    /// entries, or failed file renames.
    async fn move_files(
        &self,
        source_dir: &Path,
        target_dir: &Path,
        pattern: &str,
    ) -> Result<Option<usize>> {
        let mut moved_count = 0;

        if cancellation_requested() {
            return Ok(None);
        }
        if !source_dir.exists() {
            return Ok(Some(0));
        }

        // Use glob pattern matching
        let pattern_path = source_dir.join(pattern);
        let pattern_str = pattern_path.to_string_lossy();

        for entry in glob::glob(&pattern_str)
            .map_err(|e| FileIOError::Io(format!("Invalid glob pattern '{}': {}", pattern, e)))?
        {
            // Yield only between glob entries so cancellation never interrupts
            // an in-flight filesystem mutation.
            tokio::task::yield_now().await;
            if cancellation_requested() {
                return Ok(None);
            }
            let source_path =
                entry.map_err(|e| FileIOError::Io(format!("Failed to read glob entry: {}", e)))?;

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
                    debug!(
                        "Moved: {} -> {}",
                        source_path.display(),
                        target_path.display()
                    );
                    if cancellation_requested() {
                        return Ok(None);
                    }
                }
            }
        }

        if cancellation_requested() {
            Ok(None)
        } else {
            Ok(Some(moved_count))
        }
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
    /// `Some` contains the number of files successfully copied. `None` means
    /// cancellation was observed after the current file copy completed.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] for invalid glob patterns, unreadable glob
    /// entries, or failed file copies.
    async fn copy_files(
        &self,
        source_dir: Option<&Path>,
        target_dir: &Path,
        pattern: &str,
    ) -> Result<Option<usize>> {
        let mut copied_count = 0;

        if cancellation_requested() {
            return Ok(None);
        }
        let source_dir = match source_dir {
            Some(dir) if dir.exists() && dir.is_dir() => dir,
            _ => return Ok(Some(0)),
        };

        // Use glob pattern matching
        let pattern_path = source_dir.join(pattern);
        let pattern_str = pattern_path.to_string_lossy();

        for entry in glob::glob(&pattern_str)
            .map_err(|e| FileIOError::Io(format!("Invalid glob pattern '{}': {}", pattern, e)))?
        {
            // Yield only between glob entries so cancellation never interrupts
            // an in-flight filesystem mutation.
            tokio::task::yield_now().await;
            if cancellation_requested() {
                return Ok(None);
            }
            let source_path =
                entry.map_err(|e| FileIOError::Io(format!("Failed to read glob entry: {}", e)))?;

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
                    debug!(
                        "Copied: {} -> {}",
                        source_path.display(),
                        target_path.display()
                    );
                    if cancellation_requested() {
                        return Ok(None);
                    }
                }
            }
        }

        if cancellation_requested() {
            Ok(None)
        } else {
            Ok(Some(copied_count))
        }
    }

    /// Move crash logs and AUTOSCAN reports from base folder to Crash Logs directory
    ///
    /// This organizes logs that may have been generated in the working directory.
    ///
    /// # Returns
    ///
    /// Total number of files moved. Within a
    /// `classic-operation-context` cancellation scope, returns zero when
    /// cancellation is observed; the scope owner distinguishes that sentinel
    /// from an ordinary zero result by reading the same monotonic control.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] when a glob cannot be traversed or a matching
    /// base-folder file cannot be renamed.
    pub async fn move_from_base_folder(&self) -> Result<usize> {
        Ok(self
            .move_from_base_folder_until_cancelled()
            .await?
            .unwrap_or_default())
    }

    /// Moves base-folder artifacts while observing cancellation between
    /// completed file renames.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] when a glob entry cannot be read or a matching
    /// file cannot be moved.
    async fn move_from_base_folder_until_cancelled(&self) -> Result<Option<usize>> {
        let logs_moved = self
            .move_files(&self.base_folder, &self.crash_logs_dir, CRASH_LOG_PATTERN)
            .await?;
        let Some(logs_moved) = logs_moved else {
            return Ok(None);
        };

        let reports_moved = self
            .move_files(
                &self.base_folder,
                &self.crash_logs_dir,
                CRASH_AUTOSCAN_PATTERN,
            )
            .await?;
        let Some(reports_moved) = reports_moved else {
            return Ok(None);
        };

        let total = logs_moved + reports_moved;
        if total > 0 {
            debug!("Moved {} files from base folder to Crash Logs", total);
        }

        Ok(Some(total))
    }

    /// Copy crash logs from game's XSE folder (My Games directory) to Crash Logs
    ///
    /// This is where the game stores crash logs. We copy (not move) them to preserve
    /// the originals in case the user wants to reference them.
    ///
    /// # Returns
    ///
    /// Number of files copied. Within a `classic-operation-context`
    /// cancellation scope, returns zero when cancellation is observed; the
    /// scope owner distinguishes that sentinel from an ordinary zero result by
    /// reading the same monotonic control.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] when a glob cannot be traversed or a matching
    /// XSE file cannot be copied.
    pub async fn copy_from_xse_folder(&self) -> Result<usize> {
        Ok(self
            .copy_from_xse_folder_until_cancelled()
            .await?
            .unwrap_or_default())
    }

    /// Copies XSE Crash Logs while observing cancellation between completed
    /// file copies.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] when a glob entry cannot be read or a matching
    /// file cannot be copied.
    async fn copy_from_xse_folder_until_cancelled(&self) -> Result<Option<usize>> {
        let copied = self
            .copy_files(
                self.xse_folder.as_deref(),
                &self.crash_logs_dir,
                CRASH_LOG_PATTERN,
            )
            .await?;
        let Some(copied) = copied else {
            return Ok(None);
        };

        if copied > 0 {
            debug!("Copied {} crash logs from XSE folder", copied);
        }

        Ok(Some(copied))
    }

    /// Collect all crash log file paths for processing
    ///
    /// This searches for crash-*.log files in:
    /// - Crash Logs directory (after moving/copying operations)
    /// - Custom scan folder (if configured)
    ///
    /// # Returns
    ///
    /// Vector of paths to all crash log files found. Within a
    /// `classic-operation-context` cancellation scope, returns an empty vector
    /// when cancellation is observed; the scope owner discards that sentinel.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] when a recursive glob cannot be created or one
    /// of its entries cannot be read.
    pub async fn collect_crash_logs(&self) -> Result<Vec<PathBuf>> {
        Ok(self
            .collect_crash_logs_until_cancelled()
            .await?
            .unwrap_or_default())
    }

    /// Enumerates accepted Crash Logs and discards the accumulator when
    /// cancellation is observed between directory entries.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] when a recursive glob cannot be created or one
    /// of its directory entries cannot be read.
    async fn collect_crash_logs_until_cancelled(&self) -> Result<Option<Vec<PathBuf>>> {
        let mut crash_files = Vec::new();

        if cancellation_requested() {
            return Ok(None);
        }

        // Collect from Crash Logs directory (recursively)
        if self.crash_logs_dir.exists() {
            let pattern = self.crash_logs_dir.join("**").join(CRASH_LOG_PATTERN);
            let pattern_str = pattern.to_string_lossy();

            for entry in glob::glob(&pattern_str)
                .map_err(|e| FileIOError::Io(format!("Invalid glob pattern: {}", e)))?
            {
                tokio::task::yield_now().await;
                if cancellation_requested() {
                    return Ok(None);
                }
                let path = entry
                    .map_err(|e| FileIOError::Io(format!("Failed to read glob entry: {}", e)))?;
                crash_files.push(path);
            }
        }

        // Collect from custom folder if configured
        if let Some(custom_folder) = &self.custom_folder
            && custom_folder.exists()
            && custom_folder.is_dir()
        {
            let pattern = custom_folder.join(CRASH_LOG_PATTERN);
            let pattern_str = pattern.to_string_lossy();

            for entry in glob::glob(&pattern_str)
                .map_err(|e| FileIOError::Io(format!("Invalid glob pattern: {}", e)))?
            {
                tokio::task::yield_now().await;
                if cancellation_requested() {
                    return Ok(None);
                }
                let path = entry
                    .map_err(|e| FileIOError::Io(format!("Failed to read glob entry: {}", e)))?;
                crash_files.push(path);
            }
        }

        debug!("Collected {} crash log files", crash_files.len());
        if cancellation_requested() {
            Ok(None)
        } else {
            Ok(Some(crash_files))
        }
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
    /// Vector of paths to all crash log files ready for processing. Within a
    /// `classic-operation-context` cancellation scope, returns an empty vector
    /// when cancellation is observed; the scope owner discards that sentinel.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] when directory creation, glob traversal, a
    /// matching rename, or a matching copy fails.
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
        Ok(self
            .collect_all_until_cancelled()
            .await?
            .unwrap_or_default())
    }

    /// Executes the complete Standard collection workflow while cooperatively
    /// checking cancellation between completed filesystem operations and
    /// directory entries.
    ///
    /// This workspace-internal seam returns `None` instead of a partial path
    /// list when cancellation is observed. Completed moves or copies remain on
    /// disk so a later discovery run can observe their consistent end state.
    ///
    /// # Errors
    ///
    /// Returns [`FileIOError`] when directory creation, glob traversal, a move,
    /// or a copy fails before cancellation is observed.
    async fn collect_all_until_cancelled(&self) -> Result<Option<Vec<PathBuf>>> {
        debug!("Starting log collection workflow");

        // Step 1: Ensure directories exist
        if !self.ensure_directories().await? {
            return Ok(None);
        }

        // Step 2: Move logs from base folder
        let Some(moved) = self.move_from_base_folder_until_cancelled().await? else {
            return Ok(None);
        };
        if moved > 0 {
            debug!("Organized {} files into Crash Logs directory", moved);
        }

        // Step 3: Copy logs from XSE folder
        let Some(copied) = self.copy_from_xse_folder_until_cancelled().await? else {
            return Ok(None);
        };
        if copied > 0 {
            debug!("Retrieved {} crash logs from game directory", copied);
        }

        // Step 4: Collect all crash log paths
        let Some(crash_files) = self.collect_crash_logs_until_cancelled().await? else {
            return Ok(None);
        };

        debug!(
            "Log collection complete: {} crash logs ready for processing",
            crash_files.len()
        );

        Ok(Some(crash_files))
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

/// A user-supplied input path that could not be resolved for targeted scanning.
#[derive(Debug, Clone)]
pub struct RejectedInput {
    /// The original path the user supplied.
    pub path: PathBuf,
    /// Human-readable explanation of why this input was rejected.
    pub reason: String,
}

/// The result of resolving explicit user-supplied paths for targeted scanning.
#[derive(Debug, Clone)]
pub struct TargetedResolution {
    /// Deduplicated targeted log paths in first-seen order.
    pub logs: Vec<PathBuf>,
    /// Inputs that did not resolve to any targeted log paths.
    pub rejected: Vec<RejectedInput>,
}

#[cfg(test)]
fn matches_crash_log_pattern(path: &Path) -> bool {
    path.file_name()
        .and_then(|n| n.to_str())
        .map(|name| {
            name.starts_with("crash-") && name.ends_with(".log") && name.len() > "crash-.log".len()
        })
        .unwrap_or(false)
}

/// Resolve explicit user-supplied file and directory paths into a deduplicated
/// list of targeted log paths without creating directories or moving files.
///
/// Resolution policy (intentional split):
/// - **Regular file**: accept the path as-is — the user explicitly chose this file to analyze,
///   regardless of name or extension.
/// - **Directory**: recursively discover only `**/crash-*.log` files under the folder.
/// - **Other**: reject with a human-readable reason.
///
/// Paths are canonicalized and deduplicated while preserving first-seen order.
/// Within a `classic-operation-context` cancellation scope, cancellation
/// returns an empty resolution whose scope owner must discard after observing
/// the same monotonic control.
pub async fn resolve_targeted_inputs(inputs: Vec<PathBuf>) -> TargetedResolution {
    resolve_targeted_inputs_until_cancelled(inputs)
        .await
        .unwrap_or_else(|| TargetedResolution {
            logs: Vec::new(),
            rejected: Vec::new(),
        })
}

/// Resolves Targeted inputs while cooperatively checking cancellation between
/// metadata operations and recursive directory entries.
///
/// This workspace-internal seam returns `None` instead of a partial resolution
/// when cancellation is observed. It performs no filesystem mutations.
async fn resolve_targeted_inputs_until_cancelled(
    inputs: Vec<PathBuf>,
) -> Option<TargetedResolution> {
    let mut logs = Vec::new();
    let mut rejected = Vec::new();
    let mut seen: HashSet<PathBuf> = HashSet::new();

    if cancellation_requested() {
        return None;
    }

    for input in inputs {
        if cancellation_requested() {
            return None;
        }
        if !input.exists() {
            rejected.push(RejectedInput {
                reason: "path does not exist".to_string(),
                path: input,
            });
            if cancellation_requested() {
                return None;
            }
            continue;
        }

        let metadata = match fs::metadata(&input).await {
            Ok(m) => m,
            Err(e) => {
                rejected.push(RejectedInput {
                    reason: format!("cannot read path: {e}"),
                    path: input,
                });
                if cancellation_requested() {
                    return None;
                }
                continue;
            }
        };
        if cancellation_requested() {
            return None;
        }

        if metadata.is_file() {
            let canonical = input.canonicalize().unwrap_or_else(|_| input.clone());
            if seen.insert(canonical) {
                logs.push(input);
            }
            if cancellation_requested() {
                return None;
            }
        } else if metadata.is_dir() {
            let escaped_input = glob::Pattern::escape(input.to_string_lossy().as_ref());
            let pattern_str = format!(
                "{escaped_input}{}**{}{}",
                std::path::MAIN_SEPARATOR,
                std::path::MAIN_SEPARATOR,
                CRASH_LOG_PATTERN
            );

            let Ok(entries) = glob::glob(&pattern_str) else {
                rejected.push(RejectedInput {
                    reason: "failed to build glob pattern for directory".to_string(),
                    path: input,
                });
                continue;
            };

            let mut found_any = false;
            for entry in entries {
                // Recursive glob iteration is synchronous, so yield at the
                // entry boundary to let same-executor callers request cancel.
                tokio::task::yield_now().await;
                if cancellation_requested() {
                    return None;
                }
                let Ok(path) = entry else { continue };
                let canonical = path.canonicalize().unwrap_or_else(|_| path.clone());
                found_any = true;
                if seen.insert(canonical) {
                    logs.push(path);
                }
                if cancellation_requested() {
                    return None;
                }
            }

            if !found_any {
                rejected.push(RejectedInput {
                    reason: "directory contains no crash-*.log files".to_string(),
                    path: input,
                });
            }
        } else {
            rejected.push(RejectedInput {
                reason: "path is neither a file nor a directory".to_string(),
                path: input,
            });
        }
        if cancellation_requested() {
            return None;
        }
    }

    debug!(
        "Targeted input resolution: {} logs resolved, {} inputs rejected",
        logs.len(),
        rejected.len()
    );

    if cancellation_requested() {
        None
    } else {
        Some(TargetedResolution { logs, rejected })
    }
}

#[cfg(test)]
#[path = "log_collection_tests.rs"]
mod tests;
