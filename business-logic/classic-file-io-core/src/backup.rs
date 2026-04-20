//! Backup management for game files
//!
//! This module provides backup/restore functionality for various game file types
//! including XSE (F4SE/SKSE), ReShade, Vulkan, and ENB files.

use crate::error::FileIOError;
use chrono::{DateTime, Local};
use std::path::{Path, PathBuf};
use tokio::fs;

/// Types of backups supported
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum BackupType {
    /// XSE (F4SE/SKSE) backups
    XSE,
    /// ReShade backups
    ReShade,
    /// Vulkan backups
    Vulkan,
    /// ENB backups
    ENB,
}

impl BackupType {
    /// Get the display name for this backup type
    pub fn display_name(&self) -> &'static str {
        match self {
            BackupType::XSE => "XSE (F4SE/SKSE)",
            BackupType::ReShade => "ReShade",
            BackupType::Vulkan => "Vulkan",
            BackupType::ENB => "ENB",
        }
    }

    /// Get the file patterns for this backup type
    pub fn file_patterns(&self) -> Vec<&'static str> {
        match self {
            BackupType::XSE => vec!["f4se_*.dll", "skse_*.dll", "xse_*.dll"],
            BackupType::ReShade => vec!["dxgi.dll", "d3d11.dll", "ReShade.ini", "ReShade*.ini"],
            BackupType::Vulkan => vec!["vulkan-1.dll", "VkLayer_*.dll"],
            BackupType::ENB => vec![
                "d3d11.dll",
                "d3dcompiler_*.dll",
                "enbseries.ini",
                "enblocal.ini",
                "enbseries",
            ],
        }
    }

    /// Get the backup directory name for this type
    pub fn backup_dir_name(&self) -> &'static str {
        match self {
            BackupType::XSE => "XSE_Backup",
            BackupType::ReShade => "ReShade_Backup",
            BackupType::Vulkan => "Vulkan_Backup",
            BackupType::ENB => "ENB_Backup",
        }
    }

    /// All backup types
    pub fn all() -> Vec<BackupType> {
        vec![
            BackupType::XSE,
            BackupType::ReShade,
            BackupType::Vulkan,
            BackupType::ENB,
        ]
    }
}

/// Backup metadata
#[derive(Debug, Clone)]
pub struct BackupInfo {
    /// Backup type
    pub backup_type: BackupType,
    /// Backup directory path
    pub backup_dir: PathBuf,
    /// Backup creation timestamp
    pub created_at: Option<DateTime<Local>>,
    /// Number of files backed up
    pub file_count: usize,
    /// Whether backup exists
    pub exists: bool,
}

/// Backup manager for game files
pub struct BackupManager {
    /// Game root directory
    game_root: PathBuf,
    /// Backup base directory (defaults to game_root/CLASSIC_Backups)
    backup_base: PathBuf,
}

impl BackupManager {
    /// Create a new backup manager
    ///
    /// # Arguments
    /// * `game_root` - Root directory of the game
    /// * `backup_base` - Optional custom backup directory (defaults to game_root/CLASSIC_Backups)
    pub fn new(game_root: PathBuf, backup_base: Option<PathBuf>) -> Self {
        let backup_base = backup_base.unwrap_or_else(|| game_root.join("CLASSIC_Backups"));
        Self {
            game_root,
            backup_base,
        }
    }

    /// Get the backup directory for a specific backup type
    fn get_backup_dir(&self, backup_type: BackupType) -> PathBuf {
        self.backup_base.join(backup_type.backup_dir_name())
    }

    /// Check if a backup exists for the given type
    pub async fn backup_exists(&self, backup_type: BackupType) -> Result<bool, FileIOError> {
        let backup_dir = self.get_backup_dir(backup_type);
        Ok(backup_dir.exists() && fs::read_dir(&backup_dir).await.is_ok())
    }

    /// Get backup information
    pub async fn get_backup_info(
        &self,
        backup_type: BackupType,
    ) -> Result<BackupInfo, FileIOError> {
        let backup_dir = self.get_backup_dir(backup_type);
        let exists = backup_dir.exists();

        let (created_at, file_count) = if exists {
            // Get metadata from backup directory
            let metadata = fs::metadata(&backup_dir).await?;
            let created_at = metadata
                .created()
                .ok()
                .and_then(|t| DateTime::from(t).into());

            // Count files in backup directory
            let mut count = 0;
            let mut entries = fs::read_dir(&backup_dir).await?;
            while entries.next_entry().await?.is_some() {
                count += 1;
            }

            (created_at, count)
        } else {
            (None, 0)
        };

        Ok(BackupInfo {
            backup_type,
            backup_dir,
            created_at,
            file_count,
            exists,
        })
    }

    /// Create a backup of the specified type
    ///
    /// Copies matching files from game root to backup directory with timestamp
    pub async fn create_backup(&self, backup_type: BackupType) -> Result<BackupInfo, FileIOError> {
        let backup_dir = self.get_backup_dir(backup_type);

        // Remove existing backup if present
        if backup_dir.exists() {
            fs::remove_dir_all(&backup_dir).await?;
        }

        // Create backup directory
        fs::create_dir_all(&backup_dir).await?;

        // Find and copy matching files
        let patterns = backup_type.file_patterns();
        let mut file_count = 0;

        for pattern in patterns {
            let matches = self.find_matching_files(&self.game_root, pattern).await?;
            for source_path in matches {
                let file_name = source_path
                    .file_name()
                    .ok_or_else(|| FileIOError::InvalidPath(source_path.display().to_string()))?;
                let dest_path = backup_dir.join(file_name);

                // Copy file
                fs::copy(&source_path, &dest_path).await?;
                file_count += 1;
            }
        }

        if file_count == 0 {
            // No files found to backup
            fs::remove_dir(&backup_dir).await?;
            return Err(FileIOError::NotFound(format!(
                "No files found matching {} patterns",
                backup_type.display_name()
            )));
        }

        self.get_backup_info(backup_type).await
    }

    /// Restore a backup of the specified type
    ///
    /// Copies files from backup directory back to game root
    pub async fn restore_backup(&self, backup_type: BackupType) -> Result<usize, FileIOError> {
        let backup_dir = self.get_backup_dir(backup_type);

        if !backup_dir.exists() {
            return Err(FileIOError::NotFound(format!(
                "Backup not found: {}",
                backup_dir.display()
            )));
        }

        let mut file_count = 0;
        let mut entries = fs::read_dir(&backup_dir).await?;

        while let Some(entry) = entries.next_entry().await? {
            let source_path = entry.path();
            if source_path.is_file() {
                let file_name = source_path
                    .file_name()
                    .ok_or_else(|| FileIOError::InvalidPath(source_path.display().to_string()))?;
                let dest_path = self.game_root.join(file_name);

                // Copy file back
                fs::copy(&source_path, &dest_path).await?;
                file_count += 1;
            }
        }

        Ok(file_count)
    }

    /// Remove a backup of the specified type
    pub async fn remove_backup(&self, backup_type: BackupType) -> Result<(), FileIOError> {
        let backup_dir = self.get_backup_dir(backup_type);

        if backup_dir.exists() {
            fs::remove_dir_all(&backup_dir).await?;
        }

        Ok(())
    }

    /// Find files matching a glob pattern in a directory
    async fn find_matching_files(
        &self,
        dir: &Path,
        pattern: &str,
    ) -> Result<Vec<PathBuf>, FileIOError> {
        let mut matches = Vec::new();

        if !dir.exists() {
            return Ok(matches);
        }

        let mut entries = fs::read_dir(dir).await?;

        while let Some(entry) = entries.next_entry().await? {
            let path = entry.path();
            if path.is_file() {
                let file_name = path
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or_default();

                // Simple glob matching (supports * wildcard)
                if Self::matches_pattern(file_name, pattern) {
                    matches.push(path);
                }
            }
        }

        Ok(matches)
    }

    /// Simple glob pattern matching
    fn matches_pattern(name: &str, pattern: &str) -> bool {
        // Handle wildcard patterns
        if pattern.contains('*') {
            let parts: Vec<&str> = pattern.split('*').collect();
            if parts.len() == 2 {
                let prefix = parts[0];
                let suffix = parts[1];
                return name.starts_with(prefix) && name.ends_with(suffix);
            }
        }

        // Exact match
        name == pattern
    }
}

#[cfg(test)]
#[path = "backup_tests.rs"]
mod tests;
