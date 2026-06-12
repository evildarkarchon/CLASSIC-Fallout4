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
