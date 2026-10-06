//! Game Local facts: the per-game `CLASSIC Data/CLASSIC {game} Local.yaml`
//! document's recorded folders, and persistence for runtime-discovered paths.
//!
//! Config owns the Game Local document's location and keys. Consumers that
//! need its facts but must not depend on config — notably the XSE Folder
//! resolver in `classic-xse-core` — receive a [`GameLocalFacts`] value (or the
//! plain paths in it) from a composing caller instead of reading the YAML.

use anyhow::{Context, Result};
use classic_shared_core::yaml::YamlOperations;
use classic_shared_core::yaml::load_yaml_merged_async;
use std::path::{Path, PathBuf};
use tokio::fs;
use yaml_rust2::Yaml;

/// `Game_Info` key recording the game installation folder.
const ROOT_FOLDER_GAME_KEY: &str = "Game_Info.Root_Folder_Game";
/// `Game_Info` key recording the game's documents folder.
const ROOT_FOLDER_DOCS_KEY: &str = "Game_Info.Root_Folder_Docs";
/// `Game_Info` key recording an explicit XSE Folder override.
const DOCS_FOLDER_XSE_KEY: &str = "Game_Info.Docs_Folder_XSE";

/// The folders a Game Local document records for one game.
///
/// Each field is `None` when the key is absent, not a string, or blank after
/// trimming; present values are trimmed. The value carries no YAML and no
/// policy, so a crate that must not depend on config can accept it (or its
/// fields) as plain input.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct GameLocalFacts {
    /// `Game_Info.Root_Folder_Game`: the game installation folder.
    pub root_folder_game: Option<PathBuf>,
    /// `Game_Info.Root_Folder_Docs`: the game's documents folder
    /// (for example `Documents/My Games/Fallout4`).
    pub root_folder_docs: Option<PathBuf>,
    /// `Game_Info.Docs_Folder_XSE`: an explicit XSE Folder that takes
    /// precedence over one derived from the documents folder.
    pub docs_folder_xse: Option<PathBuf>,
}

impl GameLocalFacts {
    /// Extracts the Game Local facts from an already-loaded Game Local
    /// document.
    #[must_use]
    pub fn from_yaml(yaml: &Yaml) -> Self {
        let yaml_ops = YamlOperations::new();
        let path_at = |key: &str| clean_path_value(&yaml_ops.get_string_value(yaml, key, ""));
        Self {
            root_folder_game: path_at(ROOT_FOLDER_GAME_KEY),
            root_folder_docs: path_at(ROOT_FOLDER_DOCS_KEY),
            docs_folder_xse: path_at(DOCS_FOLDER_XSE_KEY),
        }
    }
}

/// Returns the Game Local document path for `game` inside `yaml_dir_data`
/// (the `CLASSIC Data` directory): `<yaml_dir_data>/CLASSIC {game} Local.yaml`.
///
/// `game` is used verbatim: unlike the shared game database, Fallout 4 VR
/// keeps its own `CLASSIC Fallout4VR Local.yaml`.
#[must_use]
pub fn game_local_yaml_path(yaml_dir_data: &Path, game: &str) -> PathBuf {
    yaml_dir_data.join(format!("CLASSIC {game} Local.yaml"))
}

/// Reads the Game Local facts for `game` from `yaml_dir_data`.
///
/// Fail-soft: a missing, unreadable, or malformed document yields
/// [`GameLocalFacts::default`] rather than an error, because these facts only
/// refine path discovery and must never block a scan. The document is read
/// through the default-scope path/mtime YAML-file cache
/// (`YamlOperations::new()`), so repeat reads of an unchanged file are cheap.
#[must_use]
pub fn read_game_local_facts(yaml_dir_data: &Path, game: &str) -> GameLocalFacts {
    YamlOperations::new()
        .load_yaml_file(&game_local_yaml_path(yaml_dir_data, game))
        .map(|yaml| GameLocalFacts::from_yaml(&yaml))
        .unwrap_or_default()
}

fn clean_path_value(value: &str) -> Option<PathBuf> {
    let trimmed = value.trim();
    (!trimmed.is_empty()).then(|| PathBuf::from(trimmed))
}

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
                ROOT_FOLDER_GAME_KEY,
                Yaml::String(game_root.to_string_lossy().to_string()),
            )
            .context("Failed to set Game_Info.Root_Folder_Game in Local.yaml")?;
    }

    if let Some(docs_root) = docs_root {
        yaml = yaml_ops
            .set_setting(
                &yaml,
                ROOT_FOLDER_DOCS_KEY,
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
