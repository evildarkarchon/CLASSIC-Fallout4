// Backup operations handler for game file backups
use anyhow::{anyhow, Context, Result};
use classic_config_core::YamlSource;
use classic_shared::get_runtime;
use std::path::{Path, PathBuf};
use tokio::fs;
use yaml_rust2::Yaml;

use crate::app_state::SharedAppState;

/// Backup category representing different types of game files
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BackupCategory {
    Xse,
    Reshade,
    Vulkan,
    Enb,
}

impl BackupCategory {
    /// Returns the string identifier used in YAML settings
    pub fn yaml_key(&self) -> &'static str {
        match self {
            Self::Xse => "Backup XSE",
            Self::Reshade => "Backup RESHADE",
            Self::Vulkan => "Backup VULKAN",
            Self::Enb => "Backup ENB",
        }
    }

    /// Returns the display name for the category
    pub fn display_name(&self) -> &'static str {
        match self {
            Self::Xse => "XSE",
            Self::Reshade => "RESHADE",
            Self::Vulkan => "VULKAN",
            Self::Enb => "ENB",
        }
    }

    /// Returns the backup directory name for this category
    pub fn backup_dir(&self) -> PathBuf {
        PathBuf::from(format!("CLASSIC Backup/Game Files/Backup {}", self.display_name()))
    }
}

/// Backup operation type
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BackupOperation {
    Backup,
    Restore,
    Remove,
}

impl BackupOperation {
    pub fn verb(&self) -> &'static str {
        match self {
            Self::Backup => "BACKUP",
            Self::Restore => "RESTORE",
            Self::Remove => "REMOVE",
        }
    }
}

/// Result of a backup operation
#[derive(Debug)]
pub struct BackupResult {
    pub success: bool,
    pub message: String,
    pub files_processed: usize,
    pub errors: Vec<String>,
}

impl BackupResult {
    pub fn success(message: String, files_processed: usize) -> Self {
        Self {
            success: true,
            message,
            files_processed,
            errors: Vec::new(),
        }
    }

    pub fn error(message: String) -> Self {
        Self {
            success: false,
            message,
            files_processed: 0,
            errors: Vec::new(),
        }
    }
}

/// Check if a backup exists for a given category (async version)
/// Note: This must be called from within a Tokio runtime context
pub async fn check_backup_exists(category: BackupCategory) -> bool {
    let backup_path = category.backup_dir();

    // Check if directory exists and contains files
    if let Ok(mut entries) = fs::read_dir(&backup_path).await {
        // Try to get at least one entry
        if entries.next_entry().await.is_ok() {
            tracing::debug!("Backup exists for {}: {:?}", category.display_name(), backup_path);
            return true;
        }
    }

    tracing::debug!("No backup found for {}: {:?}", category.display_name(), backup_path);
    false
}

/// Performs a backup operation for a given category
/// Note: This must be called from within a Tokio runtime context
pub async fn perform_backup(category: BackupCategory, state: SharedAppState) -> Result<BackupResult> {
    tracing::info!("Starting backup operation for {}", category.display_name());

    // Load backup file list from YAML
    let backup_files = load_backup_file_list(category, state.clone()).await?;

    if backup_files.is_empty() {
        return Ok(BackupResult::error(format!(
            "No files configured for {} backup",
            category.display_name()
        )));
    }

    tracing::debug!(
        "Loaded {} file patterns for {}",
        backup_files.len(),
        category.display_name()
    );

    // Get game path from AppState
    let game_path = {
        let state_guard = state.read();
        state_guard.game_root().clone()
    };

    // Validate game path
    if !game_path.exists() || !game_path.is_dir() {
        return Ok(BackupResult::error(format!(
            "Game path not found: {}",
            game_path.display()
        )));
    }

    // Create backup directory
    let backup_dir = category.backup_dir();
    fs::create_dir_all(&backup_dir)
        .await
        .with_context(|| format!("Failed to create backup directory: {}", backup_dir.display()))?;

    tracing::debug!("Created backup directory: {}", backup_dir.display());

    // Track files processed and errors
    let mut files_processed = 0;
    let mut errors = Vec::new();

    // Get list of existing backup files to avoid duplicates
    let existing_backups: std::collections::HashSet<String> = match fs::read_dir(&backup_dir).await {
        Ok(mut entries) => {
            let mut set = std::collections::HashSet::new();
            while let Ok(Some(entry)) = entries.next_entry().await {
                if let Some(name) = entry.file_name().to_str() {
                    set.insert(name.to_string());
                }
            }
            set
        }
        Err(_) => std::collections::HashSet::new(),
    };

    // Process each file/directory in backup list
    for file_name in &backup_files {
        let source_path = game_path.join(file_name);

        // Skip if source doesn't exist
        if !source_path.exists() {
            tracing::debug!("Skipping {}: not found in game directory", file_name);
            continue;
        }

        // Skip if already backed up
        if existing_backups.contains(file_name) {
            tracing::debug!("Skipping {}: already backed up", file_name);
            continue;
        }

        // Copy file or directory
        let dest_path = backup_dir.join(file_name);
        match copy_path(&source_path, &dest_path).await {
            Ok(()) => {
                files_processed += 1;
                tracing::debug!("Backed up: {}", file_name);
            }
            Err(e) => {
                let error_msg = format!("Failed to backup {}: {}", file_name, e);
                tracing::warn!("{}", error_msg);
                errors.push(error_msg);
            }
        }
    }

    // Build result message
    let message = if files_processed > 0 {
        format!(
            "Successfully backed up {} {} file(s) to:\n{}",
            files_processed,
            category.display_name(),
            backup_dir.display()
        )
    } else if errors.is_empty() {
        format!(
            "All {} files are already backed up",
            category.display_name()
        )
    } else {
        format!(
            "Backup completed with {} error(s)",
            errors.len()
        )
    };

    Ok(BackupResult {
        success: files_processed > 0 || errors.is_empty(),
        message,
        files_processed,
        errors,
    })
}

/// Performs a restore operation for a given category
/// Note: This must be called from within a Tokio runtime context
pub async fn perform_restore(category: BackupCategory, state: SharedAppState) -> Result<BackupResult> {
    tracing::info!("Starting restore operation for {}", category.display_name());

    // Check if backup exists
    let backup_dir = category.backup_dir();
    if !backup_dir.exists() || !backup_dir.is_dir() {
        return Ok(BackupResult::error(format!(
            "No backup found for {}. Please create a backup first.",
            category.display_name()
        )));
    }

    // Get game path from AppState
    let game_path = {
        let state_guard = state.read();
        state_guard.game_root().clone()
    };

    // Validate game path
    if !game_path.exists() || !game_path.is_dir() {
        return Ok(BackupResult::error(format!(
            "Game path not found: {}",
            game_path.display()
        )));
    }

    // Track files processed and errors
    let mut files_processed = 0;
    let mut errors = Vec::new();

    // Read backup directory
    let mut backup_entries = fs::read_dir(&backup_dir).await.with_context(|| {
        format!(
            "Failed to read backup directory: {}",
            backup_dir.display()
        )
    })?;

    // Restore each backed-up file/directory
    while let Some(entry) = backup_entries.next_entry().await? {
        let backup_item = entry.path();
        let file_name = entry.file_name();
        let dest_path = game_path.join(&file_name);

        tracing::debug!("Restoring {} to game directory", file_name.to_string_lossy());

        // Copy from backup to game directory
        match copy_path(&backup_item, &dest_path).await {
            Ok(()) => {
                files_processed += 1;
                tracing::debug!("Restored: {:?}", file_name);
            }
            Err(e) => {
                let error_msg = format!("Failed to restore {:?}: {}", file_name, e);
                tracing::warn!("{}", error_msg);
                errors.push(error_msg);
            }
        }
    }

    // Build result message
    let message = if files_processed > 0 {
        format!(
            "Successfully restored {} {} file(s) from backup",
            files_processed,
            category.display_name()
        )
    } else {
        format!("No files were restored from {} backup", category.display_name())
    };

    Ok(BackupResult {
        success: files_processed > 0 && errors.is_empty(),
        message,
        files_processed,
        errors,
    })
}

/// Performs a remove operation for a given category
/// Note: This must be called from within a Tokio runtime context
pub async fn perform_remove(category: BackupCategory, state: SharedAppState) -> Result<BackupResult> {
    tracing::info!("Starting remove operation for {}", category.display_name());

    // Load backup file list from YAML
    let backup_files = load_backup_file_list(category, state.clone()).await?;

    if backup_files.is_empty() {
        return Ok(BackupResult::error(format!(
            "No files configured for {} removal",
            category.display_name()
        )));
    }

    tracing::debug!(
        "Loaded {} file patterns for removal",
        backup_files.len()
    );

    // Get game path from AppState
    let game_path = {
        let state_guard = state.read();
        state_guard.game_root().clone()
    };

    // Validate game path
    if !game_path.exists() || !game_path.is_dir() {
        return Ok(BackupResult::error(format!(
            "Game path not found: {}",
            game_path.display()
        )));
    }

    // Track files processed and errors
    let mut files_processed = 0;
    let mut errors = Vec::new();

    // Process each file/directory in backup list
    for file_name in &backup_files {
        let target_path = game_path.join(file_name);

        // Skip if target doesn't exist
        if !target_path.exists() {
            tracing::debug!("Skipping {}: not found in game directory", file_name);
            continue;
        }

        // Remove file or directory
        match remove_path(&target_path).await {
            Ok(()) => {
                files_processed += 1;
                tracing::debug!("Removed: {}", file_name);
            }
            Err(e) => {
                let error_msg = format!("Failed to remove {}: {}", file_name, e);
                tracing::warn!("{}", error_msg);
                errors.push(error_msg);
            }
        }
    }

    // Build result message
    let message = if files_processed > 0 {
        format!(
            "Successfully removed {} {} file(s) from game directory",
            files_processed,
            category.display_name()
        )
    } else if errors.is_empty() {
        format!(
            "No {} files found to remove",
            category.display_name()
        )
    } else {
        format!(
            "Remove operation completed with {} error(s)",
            errors.len()
        )
    };

    Ok(BackupResult {
        success: files_processed > 0 || errors.is_empty(),
        message,
        files_processed,
        errors,
    })
}

/// Opens the CLASSIC Backups folder in the system file explorer
pub fn open_backups_folder() -> Result<()> {
    tracing::info!("Opening CLASSIC Backups folder...");

    let backup_root = PathBuf::from("CLASSIC Backup/Game Files");

    // Create directory if it doesn't exist
    if !backup_root.exists() {
        std::fs::create_dir_all(&backup_root)
            .context("Failed to create backup directory")?;
    }

    // Open in file explorer using 'open' crate
    open::that(&backup_root)
        .context("Failed to open backup folder in file explorer")?;

    tracing::debug!("Opened backup folder: {:?}", backup_root);
    Ok(())
}

/// Load backup file list from YAML configuration
///
/// This loads the game-specific YAML file and extracts the list of files
/// to backup for the given category (e.g., "Backup XSE", "Backup ENB").
///
/// Uses `YamlSource::Game` enum for single source of truth for YAML paths.
async fn load_backup_file_list(category: BackupCategory, state: SharedAppState) -> Result<Vec<String>> {
    // Get game name from AppState
    let game = {
        let state_guard = state.read();
        state_guard.game_name().to_string()
    };

    // Load game YAML using YamlSource enum (single source of truth)
    let yaml_data = YamlSource::Game
        .load(&game)
        .await
        .context("Failed to load game YAML configuration")?;

    // Get backup list for category
    let backup_key = category.yaml_key();
    let backup_list = &yaml_data[backup_key];

    // Extract file names from YAML array
    match backup_list {
        Yaml::Array(arr) => {
            let files: Vec<String> = arr
                .iter()
                .filter_map(|item| item.as_str().map(String::from))
                .collect();

            if files.is_empty() {
                tracing::warn!("No files found in {} backup list", backup_key);
            }

            Ok(files)
        }
        _ => {
            tracing::warn!("Backup list for {} is not an array", backup_key);
            Ok(Vec::new())
        }
    }
}

/// Recursively copy a file or directory
///
/// This handles both files and directories, copying recursively
/// using async I/O operations.
async fn copy_path(source: &Path, dest: &Path) -> Result<()> {
    if source.is_file() {
        // Copy single file
        if let Some(parent) = dest.parent() {
            fs::create_dir_all(parent).await?;
        }
        fs::copy(source, dest).await?;
        Ok(())
    } else if source.is_dir() {
        // Copy directory recursively
        copy_dir_recursive(source, dest).await
    } else {
        Err(anyhow!("Source path is neither file nor directory"))
    }
}

/// Recursively copy a directory and all its contents
fn copy_dir_recursive<'a>(
    source: &'a Path,
    dest: &'a Path,
) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<()>> + Send + 'a>> {
    Box::pin(async move {
        // Create destination directory
        fs::create_dir_all(dest).await?;

        // Read source directory entries
        let mut entries = fs::read_dir(source).await?;

        // Process each entry
        while let Some(entry) = entries.next_entry().await? {
            let source_path = entry.path();
            let file_name = entry.file_name();
            let dest_path = dest.join(&file_name);

            if source_path.is_file() {
                fs::copy(&source_path, &dest_path).await?;
            } else if source_path.is_dir() {
                copy_dir_recursive(&source_path, &dest_path).await?;
            }
        }

        Ok(())
    })
}

/// Remove a file or directory
///
/// This handles both files and directories, removing recursively if needed.
async fn remove_path(path: &Path) -> Result<()> {
    if path.is_file() {
        fs::remove_file(path).await?;
        Ok(())
    } else if path.is_dir() {
        fs::remove_dir_all(path).await?;
        Ok(())
    } else {
        Err(anyhow!("Path is neither file nor directory"))
    }
}
