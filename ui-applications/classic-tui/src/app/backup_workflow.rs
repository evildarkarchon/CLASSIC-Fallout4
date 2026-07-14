use std::path::PathBuf;
use std::time::{Duration, Instant};

use classic_file_io_core::{BackupManager, BackupType};
use classic_shared_core::get_runtime;

use super::{App, AsyncMessage, BACKUP_TYPES, Overlay, STATUS_CLEAR_SECONDS};

impl App {
    pub fn backup_select_next(&mut self) {
        self.backup_selected_row = (self.backup_selected_row + 1) % BACKUP_TYPES.len();
    }

    pub fn backup_select_prev(&mut self) {
        self.backup_selected_row = if self.backup_selected_row == 0 {
            BACKUP_TYPES.len() - 1
        } else {
            self.backup_selected_row - 1
        };
    }

    pub fn backup_select_row(&mut self, row: usize) {
        self.backup_selected_row = row.min(BACKUP_TYPES.len() - 1);
    }

    pub fn refresh_backup_statuses(&mut self) {
        let tx = self.async_tx.clone();
        let game_root = self.game_root_for_backup();

        get_runtime().spawn(async move {
            let manager = BackupManager::new(game_root, None);
            let mut statuses = [false; 4];
            for (index, backup_type) in BACKUP_TYPES.iter().enumerate() {
                statuses[index] = manager.backup_exists(*backup_type).await.unwrap_or(false);
            }
            let _ = tx.send(AsyncMessage::BackupStatuses(statuses));
        });
    }

    pub fn backup_create_selected(&mut self) {
        self.run_backup_operation(self.selected_backup_type(), BackupOperation::Create);
    }

    pub fn backup_restore_selected(&mut self) {
        if !self.backup_exists[self.backup_selected_row] {
            self.scan_status = "No backup exists for selected type".to_string();
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            return;
        }

        self.run_backup_operation(self.selected_backup_type(), BackupOperation::Restore);
    }

    pub fn backup_request_remove_selected(&mut self) {
        let backup_type = self.selected_backup_type();
        if !self.backup_exists[self.backup_selected_row] {
            self.scan_status = "No backup exists for selected type".to_string();
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            return;
        }

        self.pending_backup_remove = Some(backup_type);
        self.active_overlay = Some(Overlay::ConfirmRemoveBackup(backup_type));
    }

    pub fn confirm_backup_remove(&mut self) {
        if let Some(backup_type) = self.pending_backup_remove {
            self.run_backup_operation(backup_type, BackupOperation::Remove);
        }
        self.pending_backup_remove = None;
        self.active_overlay = None;
    }

    pub fn open_backups_folder(&mut self) {
        let folder = self.game_root_for_backup().join("CLASSIC_Backups");
        if let Err(error) = std::fs::create_dir_all(&folder) {
            self.scan_status = format!("Failed to prepare backups folder: {error}");
            self.status_clear_at = Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            return;
        }

        match open::that(folder) {
            Ok(_) => {
                self.scan_status = "Opened CLASSIC backups folder".to_string();
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            }
            Err(error) => {
                self.scan_status = format!("Failed to open backups folder: {error}");
                self.status_clear_at =
                    Some(Instant::now() + Duration::from_secs(STATUS_CLEAR_SECONDS));
            }
        }
    }

    fn selected_backup_type(&self) -> BackupType {
        BACKUP_TYPES[self.backup_selected_row.min(BACKUP_TYPES.len() - 1)]
    }

    fn game_root_for_backup(&self) -> PathBuf {
        self.settings
            .game_setup_settings()
            .game_root()
            .map(PathBuf::from)
            .unwrap_or_else(|| self.classic_root.clone())
    }

    fn run_backup_operation(&mut self, backup_type: BackupType, operation: BackupOperation) {
        let tx = self.async_tx.clone();
        let game_root = self.game_root_for_backup();

        let status = match operation {
            BackupOperation::Create => format!("Creating {} backup...", backup_type.display_name()),
            BackupOperation::Restore => {
                format!("Restoring {} backup...", backup_type.display_name())
            }
            BackupOperation::Remove => format!("Removing {} backup...", backup_type.display_name()),
        };
        self.scan_status = status;
        self.status_clear_at = None;

        get_runtime().spawn(async move {
            let manager = BackupManager::new(game_root, None);

            let result_message = match operation {
                BackupOperation::Create => match manager.create_backup(backup_type).await {
                    Ok(info) => Ok(format!(
                        "{} backup created ({} files)",
                        backup_type.display_name(),
                        info.file_count
                    )),
                    Err(error) => Err(format!(
                        "Failed to create {} backup: {}",
                        backup_type.display_name(),
                        error
                    )),
                },
                BackupOperation::Restore => match manager.restore_backup(backup_type).await {
                    Ok(count) => Ok(format!(
                        "{} backup restored ({} files)",
                        backup_type.display_name(),
                        count
                    )),
                    Err(error) => Err(format!(
                        "Failed to restore {} backup: {}",
                        backup_type.display_name(),
                        error
                    )),
                },
                BackupOperation::Remove => match manager.remove_backup(backup_type).await {
                    Ok(()) => Ok(format!("{} backup removed", backup_type.display_name())),
                    Err(error) => Err(format!(
                        "Failed to remove {} backup: {}",
                        backup_type.display_name(),
                        error
                    )),
                },
            };

            match result_message {
                Ok(message) => {
                    let _ = tx.send(AsyncMessage::BackupComplete(message));
                }
                Err(message) => {
                    let _ = tx.send(AsyncMessage::BackupError(message));
                }
            }

            let mut statuses = [false; 4];
            for (index, backup_type) in BACKUP_TYPES.iter().enumerate() {
                statuses[index] = manager.backup_exists(*backup_type).await.unwrap_or(false);
            }
            let _ = tx.send(AsyncMessage::BackupStatuses(statuses));
        });
    }
}

#[derive(Clone, Copy)]
enum BackupOperation {
    Create,
    Restore,
    Remove,
}
