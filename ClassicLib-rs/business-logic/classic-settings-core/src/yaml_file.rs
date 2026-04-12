use serde::{Deserialize, Serialize};

/// Enumeration for YAML configuration files used by CLASSIC.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum YamlFile {
    Main,
    Settings,
    Ignore,
    Game,
    GameLocal,
    Test,
    Cache,
}

impl YamlFile {
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
mod tests {
    use super::*;

    #[test]
    fn test_yaml_file_as_str() {
        assert_eq!(YamlFile::Main.as_str(), "Main");
        assert_eq!(YamlFile::Settings.as_str(), "Settings");
        assert_eq!(YamlFile::Ignore.as_str(), "Ignore");
        assert_eq!(YamlFile::Game.as_str(), "Game");
        assert_eq!(YamlFile::GameLocal.as_str(), "GameLocal");
        assert_eq!(YamlFile::Test.as_str(), "Test");
        assert_eq!(YamlFile::Cache.as_str(), "Cache");
    }

    #[test]
    fn test_yaml_file_description() {
        let desc = YamlFile::Main.description();
        assert!(desc.contains("CLASSIC Main.yaml"));

        let desc = YamlFile::Settings.description();
        assert!(desc.contains("CLASSIC Settings.yaml"));
    }

    #[test]
    fn test_yaml_file_all() {
        let all = YamlFile::all();
        assert_eq!(all.len(), 7);
        assert!(all.contains(&YamlFile::Main));
        assert!(all.contains(&YamlFile::Settings));
    }

    #[test]
    fn test_yaml_file_display() {
        assert_eq!(format!("{}", YamlFile::Main), "Main");
        assert_eq!(format!("{}", YamlFile::Settings), "Settings");
    }

    #[test]
    fn test_settings_ignore_none() {
        assert_eq!(SETTINGS_IGNORE_NONE.len(), 5);
        assert!(SETTINGS_IGNORE_NONE.contains(&"SCAN Custom Path"));
        assert!(SETTINGS_IGNORE_NONE.contains(&"Root_Folder_Game"));
    }

    #[test]
    fn test_must_not_be_none() {
        assert!(must_not_be_none("SCAN Custom Path"));
        assert!(must_not_be_none("Root_Folder_Game"));
        assert!(!must_not_be_none("Some Other Setting"));
    }

    #[test]
    fn test_yaml_file_serialization() {
        let yaml = YamlFile::Settings;
        let json = serde_json::to_string(&yaml).unwrap();
        let deserialized: YamlFile = serde_json::from_str(&json).unwrap();
        assert_eq!(yaml, deserialized);
    }
}
