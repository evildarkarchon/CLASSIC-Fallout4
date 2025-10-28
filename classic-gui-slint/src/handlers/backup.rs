// Backup operations handler for game file backups
use anyhow::{anyhow, Context, Result};
use classic_config_core::YamlSource;
use classic_file_io_core::backup::{BackupManager, BackupType};
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

/// Convert BackupCategory to BackupType from core library
impl From<BackupCategory> for BackupType {
    fn from(category: BackupCategory) -> Self {
        match category {
            BackupCategory::Xse => BackupType::XSE,
            BackupCategory::Reshade => BackupType::ReShade,
            BackupCategory::Vulkan => BackupType::Vulkan,
            BackupCategory::Enb => BackupType::ENB,
        }
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
    /// Returns the uppercase verb string for display in UI messages
    ///
    /// # Returns
    ///
    /// - `"BACKUP"` for backup operations
    /// - `"RESTORE"` for restore operations
    /// - `"REMOVE"` for remove operations
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
    #[allow(dead_code)]
    pub files_processed: usize,
    #[allow(dead_code)]
    pub errors: Vec<String>,
}

impl BackupResult {
    /// Creates a successful backup result
    ///
    /// # Arguments
    ///
    /// * `message` - Success message to display to the user
    /// * `files_processed` - Number of files successfully processed
    #[allow(dead_code)]
    pub fn success(message: String, files_processed: usize) -> Self {
        Self {
            success: true,
            message,
            files_processed,
            errors: Vec::new(),
        }
    }

    /// Creates an error backup result
    ///
    /// # Arguments
    ///
    /// * `message` - Error message to display to the user
    pub fn error(message: String) -> Self {
        Self {
            success: false,
            message,
            files_processed: 0,
            errors: Vec::new(),
        }
    }
}

/// Check if a backup exists for a given category
///
/// Checks if the backup directory exists and contains at least one file.
///
/// # Arguments
///
/// * `category` - The backup category to check (XSE, ENB, etc.)
///
/// # Returns
///
/// `true` if a backup directory exists and contains files, `false` otherwise.
///
/// # Runtime Context
///
/// **IMPORTANT**: This function is async and must be called from within a Tokio runtime context.
/// When calling from Slint UI callbacks, use `AsyncBridge::run_with_ui_update()`.
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
///
/// Backs up game files according to the YAML configuration for the specified category.
/// Only files that don't already exist in the backup are copied.
///
/// # Arguments
///
/// * `category` - The backup category (XSE, ENB, etc.)
/// * `state` - Shared application state containing game paths and configuration
///
/// # Returns
///
/// A `BackupResult` containing the operation status, message, and statistics.
///
/// # Runtime Context
///
/// **IMPORTANT**: This function is async and must be called from within a Tokio runtime context.
/// When calling from Slint UI callbacks, use `AsyncBridge::run_with_ui_update()`.
pub async fn perform_backup(category: BackupCategory, state: SharedAppState) -> Result<BackupResult> {
    tracing::info!("Starting backup operation for {}", category.display_name());

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

    // Convert category to BackupType and create manager
    let backup_type = BackupType::from(category);
    let manager = BackupManager::new(game_path.clone(), Some(game_path.join("CLASSIC Backup/Game Files")));

    // Perform backup using BackupManager
    match manager.create_backup(backup_type).await {
        Ok(info) => {
            let message = format!(
                "Successfully backed up {} {} file(s) to:\n{}",
                info.file_count,
                category.display_name(),
                info.backup_dir.display()
            );
            tracing::info!("Backup completed: {} files", info.file_count);
            Ok(BackupResult::success(message, info.file_count))
        }
        Err(e) => {
            let error_msg = format!("Backup failed: {}", e);
            tracing::error!("{}", error_msg);
            Ok(BackupResult::error(error_msg))
        }
    }
}

/// Performs a restore operation for a given category
///
/// Restores backed-up game files from the backup directory to the game directory.
/// All files in the backup directory are copied back to their original locations.
///
/// # Arguments
///
/// * `category` - The backup category to restore (XSE, ENB, etc.)
/// * `state` - Shared application state containing game paths
///
/// # Returns
///
/// A `BackupResult` containing the operation status, message, and statistics.
///
/// # Runtime Context
///
/// **IMPORTANT**: This function is async and must be called from within a Tokio runtime context.
/// When calling from Slint UI callbacks, use `AsyncBridge::run_with_ui_update()`.
pub async fn perform_restore(category: BackupCategory, state: SharedAppState) -> Result<BackupResult> {
    tracing::info!("Starting restore operation for {}", category.display_name());

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

    // Convert category to BackupType and create manager
    let backup_type = BackupType::from(category);
    let manager = BackupManager::new(game_path.clone(), Some(game_path.join("CLASSIC Backup/Game Files")));

    // Perform restore using BackupManager
    match manager.restore_backup(backup_type).await {
        Ok(file_count) => {
            let message = format!(
                "Successfully restored {} {} file(s) from backup",
                file_count,
                category.display_name()
            );
            tracing::info!("Restore completed: {} files", file_count);
            Ok(BackupResult::success(message, file_count))
        }
        Err(e) => {
            let error_msg = format!("Restore failed: {}", e);
            tracing::error!("{}", error_msg);
            Ok(BackupResult::error(error_msg))
        }
    }
}

/// Performs a remove operation for a given category
///
/// Removes game files from the game directory according to the YAML configuration
/// for the specified category. This is typically used to remove mods or tweaks
/// that were backed up.
///
/// # Arguments
///
/// * `category` - The backup category whose files should be removed (XSE, ENB, etc.)
/// * `state` - Shared application state containing game paths and configuration
///
/// # Returns
///
/// A `BackupResult` containing the operation status, message, and statistics.
///
/// # Runtime Context
///
/// **IMPORTANT**: This function is async and must be called from within a Tokio runtime context.
/// When calling from Slint UI callbacks, use `AsyncBridge::run_with_ui_update()`.
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
