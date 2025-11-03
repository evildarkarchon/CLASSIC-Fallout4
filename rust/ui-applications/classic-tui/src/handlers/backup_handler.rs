//! Backup operations handler for TUI
//!
//! This module provides backup/restore/remove functionality for game files
//! using the BackupManager from classic-file-io-core.

use anyhow::Result;
use classic_file_io_core::{BackupInfo, BackupManager, BackupType};
use std::collections::HashMap;
use std::path::PathBuf;

/// Backup operation result message
#[derive(Debug, Clone)]
#[allow(dead_code)]
pub enum BackupMessage {
    /// Backup status updated
    StatusUpdate(HashMap<BackupType, BackupInfo>),
    /// Backup operation completed successfully
    OperationComplete(String),
    /// Backup operation failed
    OperationError(String),
}

/// Handler for backup operations
pub struct BackupHandler {
    manager: BackupManager,
    status_cache: HashMap<BackupType, BackupInfo>,
}

impl BackupHandler {
    /// Create a new backup handler
    ///
    /// # Arguments
    /// * `game_root` - Root directory of the game
    pub fn new(game_root: PathBuf) -> Self {
        let manager = BackupManager::new(game_root, None);
        Self {
            manager,
            status_cache: HashMap::new(),
        }
    }

    /// Refresh backup status for all types
    pub async fn refresh_status(&mut self) -> Result<HashMap<BackupType, BackupInfo>> {
        let mut status = HashMap::new();

        for backup_type in BackupType::all() {
            let info = self.manager.get_backup_info(backup_type).await?;
            status.insert(backup_type, info);
        }

        self.status_cache = status.clone();
        Ok(status)
    }

    /// Get current backup status from cache
    #[allow(dead_code)]
    pub fn get_status(&self) -> &HashMap<BackupType, BackupInfo> {
        &self.status_cache
    }

    /// Create a backup of the specified type
    pub async fn create_backup(&mut self, backup_type: BackupType) -> Result<BackupInfo> {
        let info = self.manager.create_backup(backup_type).await?;
        self.status_cache.insert(backup_type, info.clone());
        Ok(info)
    }

    /// Restore a backup of the specified type
    pub async fn restore_backup(&mut self, backup_type: BackupType) -> Result<usize> {
        let count = self.manager.restore_backup(backup_type).await?;
        Ok(count)
    }

    /// Remove a backup of the specified type
    pub async fn remove_backup(&mut self, backup_type: BackupType) -> Result<()> {
        self.manager.remove_backup(backup_type).await?;
        // Update cache to reflect removal
        if let Ok(info) = self.manager.get_backup_info(backup_type).await {
            self.status_cache.insert(backup_type, info);
        }
        Ok(())
    }

    /// Check if a backup exists for the given type
    pub fn backup_exists(&self, backup_type: BackupType) -> bool {
        self.status_cache
            .get(&backup_type)
            .map(|info| info.exists)
            .unwrap_or(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use tokio::fs;

    #[tokio::test]
    async fn test_backup_handler_creation() {
        let temp_dir = tempdir().unwrap();
        let game_root = temp_dir.path().to_path_buf();

        let handler = BackupHandler::new(game_root);
        assert!(handler.status_cache.is_empty());
    }

    #[tokio::test]
    async fn test_refresh_status() {
        let temp_dir = tempdir().unwrap();
        let game_root = temp_dir.path().to_path_buf();

        let mut handler = BackupHandler::new(game_root);
        let status = handler.refresh_status().await.unwrap();

        // Should have status for all backup types
        assert_eq!(status.len(), 4);
        assert!(status.contains_key(&BackupType::XSE));
        assert!(status.contains_key(&BackupType::ReShade));
        assert!(status.contains_key(&BackupType::Vulkan));
        assert!(status.contains_key(&BackupType::ENB));
    }

    #[tokio::test]
    async fn test_backup_workflow() {
        let temp_dir = tempdir().unwrap();
        let game_root = temp_dir.path().to_path_buf();

        // Create test file
        let test_file = game_root.join("f4se_1_10_163.dll");
        fs::write(&test_file, b"test content").await.unwrap();

        let mut handler = BackupHandler::new(game_root.clone());
        handler.refresh_status().await.unwrap();

        // Initially no backup exists
        assert!(!handler.backup_exists(BackupType::XSE));

        // Create backup
        let info = handler.create_backup(BackupType::XSE).await.unwrap();
        assert!(info.exists);
        assert_eq!(info.file_count, 1);

        // Now backup should exist in cache
        assert!(handler.backup_exists(BackupType::XSE));

        // Delete original file
        fs::remove_file(&test_file).await.unwrap();
        assert!(!test_file.exists());

        // Restore backup
        let restored = handler.restore_backup(BackupType::XSE).await.unwrap();
        assert_eq!(restored, 1);
        assert!(test_file.exists());

        // Remove backup
        handler.remove_backup(BackupType::XSE).await.unwrap();
        assert!(!handler.backup_exists(BackupType::XSE));
    }
}
