//! The canonical CLASSIC YAML file identity and its per-file policy.
//!
//! [`YamlSource`] is the one six-kind identity for CLASSIC's YAML documents
//! outside the User Settings domain. Each kind carries its stable token
//! ([`YamlSource::as_str`], also its `Display` and serde form), its documented
//! location ([`YamlSource::description`]), its resolved path
//! ([`YamlSource::path`]), its human-facing label
//! ([`YamlSource::display_name`]), and the schema range this client accepts
//! for it ([`YamlSource::schema_compat`]). The former
//! `classic_settings_core::YamlFile` projected the same six kinds; its tokens,
//! descriptions, order, display, and serialization are preserved here.

use anyhow::{Context, Result};
use classic_registry_core::RegistryScope;
use classic_shared_core::yaml::{SchemaCompat, load_yaml_merged_async};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use yaml_rust2::Yaml;

use crate::client_schemas;
use crate::game_data::canonical_game_data_name;

fn resolve_application_dir(current_exe: Option<&Path>) -> Option<PathBuf> {
    current_exe.and_then(|path| path.parent().map(Path::to_path_buf))
}

/// Application directory from `registry`'s override, falling back to the
/// executable directory.
///
/// The fallback never consults another scope, so a facade-owned scope without
/// an override behaves like a fresh process rather than inheriting the
/// default scope's value.
fn application_dir_in(registry: &RegistryScope) -> Option<PathBuf> {
    // Binding layers auto-register APP_DIR so cache paths resolve relative to
    // the launched application rather than the language runtime executable.
    registry.get_application_dir().or_else(|| {
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
///
/// Serializes as its bare variant name (`"Main"`, `"GameLocal"`, ...), which is
/// also [`Self::as_str`] and the `Display` form.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
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
    /// Returns every YAML file kind in a stable order: Main, Ignore, Game,
    /// GameLocal, Test, Cache.
    #[must_use]
    pub const fn all() -> [Self; 6] {
        [
            Self::Main,
            Self::Ignore,
            Self::Game,
            Self::GameLocal,
            Self::Test,
            Self::Cache,
        ]
    }

    /// Returns the stable identifier for this kind (its variant name).
    ///
    /// This is the token bindings and conformance observe, and it matches the
    /// `Display` and serde forms. It is not the human-facing
    /// [`Self::display_name`].
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Main => "Main",
            Self::Ignore => "Ignore",
            Self::Game => "Game",
            Self::GameLocal => "GameLocal",
            Self::Test => "Test",
            Self::Cache => "Cache",
        }
    }

    /// Describes the canonical location of this kind with `{Game}` left as a
    /// placeholder; use [`Self::path`] for a resolved path.
    #[must_use]
    pub const fn description(&self) -> &'static str {
        match self {
            Self::Main => "CLASSIC Data/databases/CLASSIC Main.yaml",
            Self::Ignore => "CLASSIC Ignore.yaml",
            Self::Game => "CLASSIC Data/databases/CLASSIC {Game}.yaml",
            Self::GameLocal => "CLASSIC Data/CLASSIC {Game} Local.yaml",
            Self::Test => "tests/test_settings.yaml",
            Self::Cache => "User config dir/CLASSIC/cache.yaml",
        }
    }

    /// Returns the `schema_version` range this client accepts for this file,
    /// or `None` when the file declares no client schema range.
    ///
    /// Only update-eligible YAML Data carries a range: [`Self::Main`] and the
    /// [`Self::Game`] database of a game whose data set has a declared range
    /// (Fallout 4, shared by Fallout 4 VR). The ranges themselves are the
    /// [`crate::client_schemas`] constants; this is the per-file lookup.
    #[must_use]
    pub fn schema_compat(&self, game: &str) -> Option<SchemaCompat> {
        match self {
            Self::Main => Some(client_schemas::MAIN_YAML),
            Self::Game if canonical_game_data_name(game) == "Fallout4" => {
                Some(client_schemas::GAME_FALLOUT4_YAML)
            }
            _ => None,
        }
    }

    /// Returns the path for this generic YAML source.
    ///
    /// [`Self::Cache`] reads the application-directory override from the
    /// default registry scope; see [`Self::path_in_registry_scope`].
    ///
    /// # Panics
    ///
    /// Panics when `game` is empty for [`Self::Game`] or [`Self::GameLocal`].
    #[must_use]
    pub fn path(&self, game: &str) -> PathBuf {
        self.path_in_registry_scope(game, &RegistryScope::default_scope())
    }

    /// Returns the path for this generic YAML source, reading any
    /// application-directory override from `registry`.
    ///
    /// Only [`Self::Cache`] consults the registry, and only as a fallback when
    /// no user config directory is available. A binding facade that owns its
    /// own registry scope passes it here so its override (or absence of one)
    /// is the one that applies; other scopes are never read.
    ///
    /// # Panics
    ///
    /// Panics when `game` is empty for [`Self::Game`] or [`Self::GameLocal`].
    #[must_use]
    pub fn path_in_registry_scope(&self, game: &str, registry: &RegistryScope) -> PathBuf {
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
                let app_dir = application_dir_in(registry);
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
    /// loader; other sources load directly from [`Self::path`], so
    /// [`Self::Cache`] resolves against the default registry scope.
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

impl std::fmt::Display for YamlSource {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Routes cache-eligible YAML data through the shippable loader.
///
/// A file is cache-eligible exactly when [`YamlSource::schema_compat`]
/// declares a range for it, so the loader and the range lookup cannot drift.
async fn load_via_shippable(source: &YamlSource, game: &str) -> Result<Option<Yaml>> {
    use crate::shippable::{ShippableFile, load_shippable_yaml};

    let Some(compat) = source.schema_compat(game) else {
        return Ok(None);
    };
    let (file, display) = match source {
        YamlSource::Main => (ShippableFile::main(), "Main Database".to_string()),
        YamlSource::Game => (ShippableFile::game(game), format!("{game} Database")),
        // `schema_compat` only declares ranges for Main and Game.
        _ => return Ok(None),
    };

    load_shippable_yaml(file, &compat)
        .await
        .map(|loaded| Some(loaded.yaml))
        .with_context(|| format!("Failed to load {display} (shippable)"))
}

#[cfg(test)]
#[path = "yaml_source_tests.rs"]
mod tests;
