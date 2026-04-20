use serde::{Deserialize, Serialize};

/// Enumeration for YAML configuration files used by CLASSIC.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum YamlFile {
    /// The main database-backed configuration file.
    Main,
    /// The user-editable settings file.
    Settings,
    /// The ignore-list configuration file.
    Ignore,
    /// The game-specific database file.
    Game,
    /// The local per-game override file.
    GameLocal,
    /// The test-only settings fixture.
    Test,
    /// The cached derived-settings file.
    Cache,
}

impl YamlFile {
    /// Return the stable identifier used for this YAML file kind.
    #[must_use]
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Main => "Main",
            Self::Settings => "Settings",
            Self::Ignore => "Ignore",
            Self::Game => "Game",
            Self::GameLocal => "GameLocal",
            Self::Test => "Test",
            Self::Cache => "Cache",
        }
    }

    /// Describe the canonical location or purpose of this YAML file.
    #[must_use]
    pub const fn description(&self) -> &'static str {
        match self {
            Self::Main => "CLASSIC Data/databases/CLASSIC Main.yaml",
            Self::Settings => "CLASSIC Settings.yaml",
            Self::Ignore => "CLASSIC Ignore.yaml",
            Self::Game => "CLASSIC Data/databases/CLASSIC {Game}.yaml",
            Self::GameLocal => "CLASSIC Data/CLASSIC {Game} Local.yaml",
            Self::Test => "tests/test_settings.yaml",
            Self::Cache => "User config dir/CLASSIC/cache.yaml",
        }
    }

    /// Return all supported YAML file kinds in a stable order.
    #[must_use]
    pub const fn all() -> [Self; 7] {
        [
            Self::Main,
            Self::Settings,
            Self::Ignore,
            Self::Game,
            Self::GameLocal,
            Self::Test,
            Self::Cache,
        ]
    }
}

impl std::fmt::Display for YamlFile {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

/// Settings keys that should not have `None` values.
pub const SETTINGS_IGNORE_NONE: &[&str] = &[
    "SCAN Custom Path",
    "MODS Folder Path",
    "INI Folder Path",
    "Root_Folder_Game",
    "Root_Folder_Docs",
];

/// Check if a settings key should not allow `None` values.
#[must_use]
pub fn must_not_be_none(key: &str) -> bool {
    SETTINGS_IGNORE_NONE.contains(&key)
}

#[cfg(test)]
#[path = "yaml_file_tests.rs"]
mod tests;
