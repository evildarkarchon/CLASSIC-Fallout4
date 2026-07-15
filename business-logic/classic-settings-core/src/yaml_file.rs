use serde::{Deserialize, Serialize};

/// Enumeration for YAML configuration files used by CLASSIC.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum YamlFile {
    /// The main database-backed configuration file.
    Main,
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
            Self::Ignore => "CLASSIC Ignore.yaml",
            Self::Game => "CLASSIC Data/databases/CLASSIC {Game}.yaml",
            Self::GameLocal => "CLASSIC Data/CLASSIC {Game} Local.yaml",
            Self::Test => "tests/test_settings.yaml",
            Self::Cache => "User config dir/CLASSIC/cache.yaml",
        }
    }

    /// Return all supported YAML file kinds in a stable order.
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
}

impl std::fmt::Display for YamlFile {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

#[cfg(test)]
#[path = "yaml_file_tests.rs"]
mod tests;
