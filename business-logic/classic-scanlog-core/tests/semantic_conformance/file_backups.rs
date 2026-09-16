//! Managed backup lifecycles observed through public core APIs.

use super::{RunnerResult, text};
use classic_file_io_core::{
    GameFilesManager,
    backup::{BackupManager, BackupType},
};
use serde_json::{Value, json};
use std::{fs, path::Path};

/// Retain every owned file after handles close.
fn inventory(
    root: &Path,
    directory: &Path,
    result: &mut serde_json::Map<String, Value>,
) -> RunnerResult<()> {
    for entry in fs::read_dir(directory)? {
        let path = entry?.path();
        if path.is_dir() {
            inventory(root, &path, result)?;
        } else {
            result.insert(
                path.strip_prefix(root)?
                    .to_string_lossy()
                    .replace('\\', "/"),
                json!(fs::read_to_string(path)?),
            );
        }
    }
    Ok(())
}

/// Use the shared runtime to back up, overwrite and restore owned fixture files.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    classic_shared_core::get_runtime().block_on(async {
        let temporary = tempfile::tempdir()?;
        let root = temporary.path();
        let kind = text(&fixture["kind"])?;
        let game = if kind == "game-files" { root.join("game") } else { root.to_path_buf() };
        fs::create_dir_all(&game)?;
        let source = game.join("f4se_fixture.dll");
        fs::write(&source, text(&fixture["content"])?)?;
        fs::write(game.join("sentinel.txt"), "keep\n")?;
        let mut files = serde_json::Map::new();
        if kind != "game-files" {
            let manager = BackupManager::new(game, None);
            let initial = manager.backup_exists(BackupType::XSE).await?;
            let info = manager.create_backup(BackupType::XSE).await?;
            let exists = manager.backup_exists(BackupType::XSE).await?;
            let copy = fs::read_to_string(info.backup_dir.join("f4se_fixture.dll"))?;
            fs::write(&source, "changed\n")?;
            let restored = manager.restore_backup(BackupType::XSE).await?;
            if kind == "remove" {
                manager.remove_backup(BackupType::XSE).await?;
                inventory(root, root, &mut files)?;
                return Ok(json!({"exists":manager.backup_exists(BackupType::XSE).await?,"files":files}));
            }
            inventory(root, root, &mut files)?;
            return Ok(json!({"initial":initial,"exists":exists,"created":format!("Backed up {} files",info.file_count),"restored":restored,"copy":copy,"source":fs::read_to_string(source)?,"files":files}));
        }
        let manager = GameFilesManager::new(game, root.join("backups"));
        let patterns = vec!["f4se_".to_owned()];
        let summarize = |value: classic_file_io_core::game_files::FileOperationResult| format!("{} files affected, {} errors", value.files_affected, value.errors.len());
        let backup = summarize(manager.backup("fixture", &patterns).await?);
        fs::write(&source, "changed\n")?;
        let restore = summarize(manager.restore("fixture", &patterns).await?);
        let restored = fs::read_to_string(source)?;
        let remove = summarize(manager.remove("fixture", &patterns).await?);
        inventory(root, root, &mut files)?;
        Ok(json!({"backup":backup,"restore":restore,"remove":remove,"restored":restored,"files":files}))
    })
}
