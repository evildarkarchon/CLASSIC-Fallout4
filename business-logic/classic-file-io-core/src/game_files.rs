//! Game files management - backup, restore, and remove operations.
//!
//! This module provides async file management operations for game files,
//! matching the behavior of the Python `GameFilesManagerCore`. It supports:
//!
//! - **Backup**: Copy matching files/directories from game root to a backup location
//! - **Restore**: Copy matching files/directories from backup back to game root
//! - **Remove**: Delete matching files/directories from game root
//!
//! Pattern matching uses case-insensitive substring matching: a pattern `"reshade"`
//! will match any file whose name contains `"reshade"` (case-insensitive).

use std::fmt;
use std::future::Future;
use std::path::{Path, PathBuf};

use tokio::fs;
use tokio::task::JoinSet;
use tracing::{error, info, warn};

use crate::error::FileIOError;

/// Maximum number of concurrent file operations.
const MAX_CONCURRENT_OPS: usize = 8;

/// The type of file operation being performed.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FileOperation {
    /// Back up files from game directory to backup directory
    Backup,
    /// Restore files from backup directory to game directory
    Restore,
    /// Remove files from game directory
    Remove,
}

impl fmt::Display for FileOperation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FileOperation::Backup => write!(f, "BACKUP"),
            FileOperation::Restore => write!(f, "RESTORE"),
            FileOperation::Remove => write!(f, "REMOVE"),
        }
    }
}

/// Summary of a completed file operation.
#[derive(Debug, Clone)]
pub struct FileOperationResult {
    /// The operation that was performed
    pub operation: FileOperation,
    /// Label identifying which file group was targeted
    pub label: String,
    /// Number of files/directories successfully affected
    pub files_affected: usize,
    /// Errors encountered during the operation (non-fatal)
    pub errors: Vec<String>,
}

impl FileOperationResult {
    /// Whether the operation completed without any errors.
    pub fn is_success(&self) -> bool {
        self.errors.is_empty()
    }

    /// Whether the operation had partial failures (some succeeded, some failed).
    pub fn is_partial(&self) -> bool {
        !self.errors.is_empty() && self.files_affected > 0
    }
}

/// Manages game file backup, restore, and remove operations.
///
/// This struct is the Rust equivalent of the Python `GameFilesManagerCore`.
/// It operates on a game root directory and a backup root directory, matching
/// files using case-insensitive substring patterns.
///
/// # Example
/// ```no_run
/// use std::path::PathBuf;
/// use classic_file_io_core::game_files::GameFilesManager;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let manager = GameFilesManager::new(
///     PathBuf::from("C:/Games/Fallout4"),
///     PathBuf::from("CLASSIC Backup/Game Files"),
/// );
///
/// let patterns = vec!["reshade".to_string(), "enb".to_string()];
/// let result = manager.backup("Graphics Mods", &patterns).await?;
/// println!("Backed up {} files", result.files_affected);
/// # Ok(())
/// # }
/// ```
pub struct GameFilesManager {
    /// Root directory of the game installation
    game_root: PathBuf,
    /// Root directory for backups
    backup_root: PathBuf,
}

impl GameFilesManager {
    /// Create a new `GameFilesManager`.
    ///
    /// # Arguments
    /// * `game_root` - Path to the game installation directory
    /// * `backup_root` - Path to the backup root directory
    pub fn new(game_root: PathBuf, backup_root: PathBuf) -> Self {
        Self {
            game_root,
            backup_root,
        }
    }

    /// Back up matching files from the game directory to a labeled backup subdirectory.
    ///
    /// Creates `backup_root/label/` and copies all matching files/directories into it.
    /// Files already existing in the backup will be overwritten.
    ///
    /// # Arguments
    /// * `label` - A label for this backup group (used as subdirectory name)
    /// * `patterns` - Case-insensitive substring patterns to match against filenames
    ///
    /// # Errors
    /// Returns `FileIOError` if the game root doesn't exist or directory creation fails.
    pub async fn backup(
        &self,
        label: &str,
        patterns: &[String],
    ) -> Result<FileOperationResult, FileIOError> {
        let backup_dir = self.backup_root.join(label);
        fs::create_dir_all(&backup_dir).await.map_err(|source| {
            FileIOError::CreateDirectoryError {
                path: backup_dir.clone(),
                source,
            }
        })?;

        let matching = self.find_matching_entries(patterns).await?;

        info!(
            "Backing up {} matching entries for '{}'",
            matching.len(),
            label
        );

        let backup_entries: Vec<(PathBuf, PathBuf)> = matching
            .into_iter()
            .map(|source| {
                let dest = backup_dir.join(source.file_name().unwrap_or_default());
                (source, dest)
            })
            .collect();
        let (files_affected, errors) =
            process_entries_chunked(&backup_entries, "Backup", |(source, dest)| async move {
                copy_entry(&source, &dest).await
            })
            .await;

        Ok(FileOperationResult {
            operation: FileOperation::Backup,
            label: label.to_string(),
            files_affected,
            errors,
        })
    }

    /// Restore matching files from a labeled backup subdirectory back to the game directory.
    ///
    /// Only restores files that exist in the backup AND match the patterns AND
    /// have a corresponding entry in the game directory.
    ///
    /// # Arguments
    /// * `label` - The backup group label (subdirectory name under backup_root)
    /// * `patterns` - Case-insensitive substring patterns to match against filenames
    ///
    /// # Errors
    /// Returns `FileIOError` if the game root doesn't exist.
    pub async fn restore(
        &self,
        label: &str,
        patterns: &[String],
    ) -> Result<FileOperationResult, FileIOError> {
        let backup_dir = self.backup_root.join(label);

        let matching = self.find_matching_entries(patterns).await?;

        info!(
            "Restoring {} matching entries for '{}'",
            matching.len(),
            label
        );

        // Only restore files that exist in the backup
        let mut restore_entries = Vec::new();
        for game_entry in &matching {
            let file_name = match game_entry.file_name() {
                Some(name) => name,
                None => continue,
            };
            let backup_entry = backup_dir.join(file_name);
            if backup_entry.exists() {
                restore_entries.push((backup_entry, game_entry.clone()));
            }
        }

        let (files_affected, errors) =
            process_entries_chunked(&restore_entries, "Restore", |(source, dest)| async move {
                copy_entry(&source, &dest).await
            })
            .await;

        Ok(FileOperationResult {
            operation: FileOperation::Restore,
            label: label.to_string(),
            files_affected,
            errors,
        })
    }

    /// Remove matching files/directories from the game directory.
    ///
    /// # Arguments
    /// * `label` - A label identifying the file group (for result tracking)
    /// * `patterns` - Case-insensitive substring patterns to match against filenames
    ///
    /// # Errors
    /// Returns `FileIOError` if the game root doesn't exist.
    pub async fn remove(
        &self,
        label: &str,
        patterns: &[String],
    ) -> Result<FileOperationResult, FileIOError> {
        let matching = self.find_matching_entries(patterns).await?;

        info!(
            "Removing {} matching entries for '{}'",
            matching.len(),
            label
        );

        let (files_affected, errors) =
            process_entries_chunked(&matching, "Remove", |entry| async move {
                remove_entry(&entry).await
            })
            .await;

        Ok(FileOperationResult {
            operation: FileOperation::Remove,
            label: label.to_string(),
            files_affected,
            errors,
        })
    }

    /// Find all entries (files and directories) in game_root that match any pattern.
    ///
    /// Matching is case-insensitive substring: pattern `"reshade"` matches `"ReShade.ini"`.
    async fn find_matching_entries(
        &self,
        patterns: &[String],
    ) -> Result<Vec<PathBuf>, FileIOError> {
        if !self.game_root.exists() {
            return Err(FileIOError::NotFound(format!(
                "Game root directory not found: {}",
                self.game_root.display()
            )));
        }

        let mut entries = fs::read_dir(&self.game_root).await?;
        let mut matching = Vec::new();

        while let Some(entry) = entries.next_entry().await? {
            let path = entry.path();
            let name = match path.file_name().and_then(|n| n.to_str()) {
                Some(n) => n.to_string(),
                None => continue,
            };

            if matches_any_pattern(&name, patterns) {
                matching.push(path);
            }
        }

        Ok(matching)
    }
}

async fn process_entries_chunked<T, F, Fut>(
    entries: &[T],
    operation_label: &str,
    mut task_for: F,
) -> (usize, Vec<String>)
where
    T: Clone + Send + 'static,
    F: FnMut(T) -> Fut,
    Fut: Future<Output = Result<(), FileIOError>> + Send + 'static,
{
    let mut files_affected = 0usize;
    let mut errors = Vec::new();

    for chunk in entries.chunks(MAX_CONCURRENT_OPS) {
        let mut join_set = JoinSet::new();

        for entry in chunk {
            join_set.spawn(task_for(entry.clone()));
        }

        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(Ok(())) => files_affected += 1,
                Ok(Err(e)) => {
                    let msg = format!("{e}");
                    error!("{operation_label} operation failed: {msg}");
                    errors.push(msg);
                }
                Err(e) => {
                    let msg = format!("Task join error: {e}");
                    error!("{msg}");
                    errors.push(msg);
                }
            }
        }
    }

    (files_affected, errors)
}

/// Check if a filename matches any of the given patterns (case-insensitive substring).
fn matches_any_pattern(file_name: &str, patterns: &[String]) -> bool {
    let name_lower = file_name.to_lowercase();
    patterns
        .iter()
        .any(|pattern| name_lower.contains(&pattern.to_lowercase()))
}

/// Copy a file or directory from source to destination.
///
/// - If source is a file, copies it (overwriting destination if it exists).
/// - If source is a directory, removes the destination first (if any), then
///   recursively copies the directory tree.
async fn copy_entry(source: &Path, dest: &Path) -> Result<(), FileIOError> {
    let metadata = fs::metadata(source).await?;

    if metadata.is_file() {
        fs::copy(source, dest).await?;
    } else if metadata.is_dir() {
        // Remove destination if it exists (matches Python's shutil.copytree behavior)
        if dest.exists() {
            fs::remove_dir_all(dest).await.map_err(|e| {
                warn!(
                    "Failed to remove existing destination dir {}: {e}",
                    dest.display()
                );
                e
            })?;
        }
        copy_dir_recursive(source, dest).await?;
    }

    Ok(())
}

/// Recursively copy a directory tree from source to destination.
async fn copy_dir_recursive(source: &Path, dest: &Path) -> Result<(), FileIOError> {
    fs::create_dir_all(dest).await?;

    let mut entries = fs::read_dir(source).await?;
    while let Some(entry) = entries.next_entry().await? {
        let entry_path = entry.path();
        let file_name = match entry_path.file_name() {
            Some(name) => name,
            None => continue,
        };
        let dest_path = dest.join(file_name);

        let metadata = fs::metadata(&entry_path).await?;
        if metadata.is_file() {
            fs::copy(&entry_path, &dest_path).await?;
        } else if metadata.is_dir() {
            // Box::pin for recursive async
            Box::pin(copy_dir_recursive(&entry_path, &dest_path)).await?;
        }
    }

    Ok(())
}

/// Remove a file or directory.
async fn remove_entry(path: &Path) -> Result<(), FileIOError> {
    let metadata = match fs::metadata(path).await {
        Ok(m) => m,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            // Already gone -- not an error
            return Ok(());
        }
        Err(e) => return Err(e.into()),
    };

    if metadata.is_file() {
        fs::remove_file(path).await?;
    } else if metadata.is_dir() {
        fs::remove_dir_all(path).await?;
    }

    Ok(())
}

#[cfg(test)]
#[path = "game_files_tests.rs"]
mod tests;
