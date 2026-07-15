//! Generic YAML document locations used outside the User Settings domain.

use anyhow::{Context, Result};
use classic_settings_core::load_yaml_merged_async;
use std::path::{Path, PathBuf};
use yaml_rust2::Yaml;

use crate::game_data::canonical_game_data_name;

fn resolve_application_dir(current_exe: Option<&Path>) -> Option<PathBuf> {
    current_exe.and_then(|path| path.parent().map(Path::to_path_buf))
}

fn application_dir() -> Option<PathBuf> {
    // Binding layers auto-register APP_DIR so cache paths resolve relative to
    // the launched application rather than the language runtime executable.
    classic_registry_core::get_application_dir().or_else(|| {
        std::env::current_exe()
            .ok()
            .and_then(|path| resolve_application_dir(Some(path.as_path())))
    })
}

fn resolve_user_config_dir(config_dir: Option<&Path>) -> Option<PathBuf> {
    config_dir.map(|dir| dir.join("CLASSIC"))
}

fn user_config_dir() -> Option<PathBuf> {
    let config_dir = dirs::config_dir();
    resolve_user_config_dir(config_dir.as_deref())
}

fn resolve_cache_path(user_dir: Option<&Path>, app_dir: Option<&Path>) -> PathBuf {
    user_dir
        .map(|dir| dir.join("cache.yaml"))
        .or_else(|| app_dir.map(|dir| dir.join("CLASSIC").join("cache.yaml")))
        .unwrap_or_else(|| PathBuf::from("CLASSIC").join("cache.yaml"))
}

/// Identifies generic CLASSIC YAML documents that are not User Settings.
///
/// User Settings locations and persistence belong exclusively to
/// `classic-user-settings-core` and are intentionally absent from this enum.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum YamlSource {
    /// Main database: `CLASSIC Data/databases/CLASSIC Main.yaml`.
    Main,
    /// Ignore list: `CLASSIC Ignore.yaml`.
    Ignore,
    /// Game database: `CLASSIC Data/databases/CLASSIC {game}.yaml`.
    ///
    /// Fallout 4 VR shares `CLASSIC Fallout4.yaml` with Fallout 4.
    Game,
    /// Game-local data: `CLASSIC Data/CLASSIC {game} Local.yaml`.
    GameLocal,
    /// Test fixture: `tests/test_settings.yaml`.
    Test,
    /// Derived cache: user config directory `CLASSIC/cache.yaml`.
    Cache,
}

impl YamlSource {
    /// Returns the path for this generic YAML source.
    ///
    /// # Panics
    ///
    /// Panics when `game` is empty for [`Self::Game`] or [`Self::GameLocal`].
    #[must_use]
    pub fn path(&self, game: &str) -> PathBuf {
        match self {
            Self::Main => PathBuf::from("CLASSIC Data/databases/CLASSIC Main.yaml"),
            Self::Ignore => PathBuf::from("CLASSIC Ignore.yaml"),
            Self::Game => {
                assert!(!game.is_empty(), "Game name required for YamlSource::Game");
                let game = canonical_game_data_name(game);
                PathBuf::from(format!("CLASSIC Data/databases/CLASSIC {game}.yaml"))
            }
            Self::GameLocal => {
                assert!(
                    !game.is_empty(),
                    "Game name required for YamlSource::GameLocal"
                );
                PathBuf::from(format!("CLASSIC Data/CLASSIC {game} Local.yaml"))
            }
            Self::Test => PathBuf::from("tests/test_settings.yaml"),
            Self::Cache => {
                let app_dir = application_dir();
                let user_dir = user_config_dir();
                resolve_cache_path(user_dir.as_deref(), app_dir.as_deref())
            }
        }
    }

    /// Returns a stable display name for this source kind.
    #[must_use]
    pub const fn display_name(&self) -> &'static str {
        match self {
            Self::Main => "Main Database",
            Self::Ignore => "Ignore List",
            Self::Game => "Game Database",
            Self::GameLocal => "Game Local Config",
            Self::Test => "Test Fixture",
            Self::Cache => "Cache",
        }
    }

    /// Returns a display name with the supplied game name substituted where relevant.
    #[must_use]
    pub fn display_name_with_game(&self, game: &str) -> String {
        match self {
            Self::Game => format!("{game} Database"),
            Self::GameLocal => format!("{game} Local Config"),
            _ => self.display_name().to_string(),
        }
    }

    /// Loads and merges this generic YAML document.
    ///
    /// Main and supported per-game databases use the shippable cache-aware
    /// loader; other sources load directly from [`Self::path`].
    ///
    /// # Errors
    ///
    /// Returns an error when the resolved source cannot be read, parsed, or
    /// accepted by its declared schema compatibility range.
    pub async fn load(&self, game: &str) -> Result<Yaml> {
        if let Some(loaded) = load_via_shippable(self, game).await? {
            return Ok(loaded);
        }

        let path = self.path(game);
        let display = if game.is_empty() {
            self.display_name().to_string()
        } else {
            self.display_name_with_game(game)
        };

        load_yaml_merged_async(&path)
            .await
            .with_context(|| format!("Failed to load {display}: {}", path.display()))
    }
}

/// Routes cache-eligible YAML data through the shippable loader.
async fn load_via_shippable(source: &YamlSource, game: &str) -> Result<Option<Yaml>> {
    use crate::client_schemas::{GAME_FALLOUT4_YAML, MAIN_YAML};
    use crate::shippable::{ShippableFile, load_shippable_yaml};

    let (file, compat, display) = match source {
        YamlSource::Main => (
            ShippableFile::main(),
            &MAIN_YAML,
            "Main Database".to_string(),
        ),
        YamlSource::Game if canonical_game_data_name(game) == "Fallout4" => (
            ShippableFile::game(game),
            &GAME_FALLOUT4_YAML,
            format!("{game} Database"),
        ),
        _ => return Ok(None),
    };

    load_shippable_yaml(file, compat)
        .await
        .map(|loaded| Some(loaded.yaml))
        .with_context(|| format!("Failed to load {display} (shippable)"))
}

#[cfg(test)]
#[path = "yaml_source_tests.rs"]
mod tests;
