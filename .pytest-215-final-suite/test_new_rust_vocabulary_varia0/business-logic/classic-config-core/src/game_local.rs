//! Persistence for runtime-discovered paths in the Game Local YAML document.

use anyhow::{Context, Result};
use classic_settings_core::{YamlOperations, load_yaml_merged_async};
use std::path::Path;
use tokio::fs;
use yaml_rust2::Yaml;

/// Persist supplied runtime paths to an explicit Game Local YAML document.
///
/// `None` leaves the corresponding key unchanged. When neither path is supplied,
/// the operation is a no-op and does not create the document. Existing unrelated
/// YAML content is preserved, and the User Settings document is never consulted.
pub async fn persist_game_local_paths(
    path: &Path,
    game_root: Option<&Path>,
    docs_root: Option<&Path>,
) -> Result<()> {
    if game_root.is_none() && docs_root.is_none() {
        return Ok(());
    }

    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .await
            .with_context(|| format!("Failed to create directory: {}", parent.display()))?;
    }

    let yaml_ops = YamlOperations::new();
    let mut yaml = if path.exists() {
        load_yaml_merged_async(path).await.with_context(|| {
            format!(
                "Failed to load Local.yaml file for save: {}",
                path.display()
            )
        })?
    } else {
        Yaml::Hash(yaml_rust2::yaml::Hash::new())
    };

    if let Some(game_root) = game_root {
        yaml = yaml_ops
            .set_setting(
                &yaml,
                "Game_Info.Root_Folder_Game",
                Yaml::String(game_root.to_string_lossy().to_string()),
            )
            .context("Failed to set Game_Info.Root_Folder_Game in Local.yaml")?;
    }

    if let Some(docs_root) = docs_root {
        yaml = yaml_ops
            .set_setting(
                &yaml,
                "Game_Info.Root_Folder_Docs",
                Yaml::String(docs_root.to_string_lossy().to_string()),
            )
            .context("Failed to set Game_Info.Root_Folder_Docs in Local.yaml")?;
    }

    let path = path.to_path_buf();
    tokio::task::spawn_blocking(move || {
        // Build a fresh helper on the blocking worker so the synchronous save
        // stays fully owned by that thread.
        let yaml_ops = YamlOperations::new();
        yaml_ops
            .save_yaml_file(&path, &yaml)
            .map_err(anyhow::Error::new)
    })
    .await
    .context("Local.yaml save task panicked")??;

    Ok(())
}

#[cfg(test)]
#[path = "game_local_tests.rs"]
mod tests;
