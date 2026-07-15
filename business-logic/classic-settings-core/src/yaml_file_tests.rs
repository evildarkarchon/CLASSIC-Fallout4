use super::*;

#[test]
fn test_yaml_file_as_str() {
    assert_eq!(YamlFile::Main.as_str(), "Main");
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
}

#[test]
fn test_yaml_file_all() {
    let all = YamlFile::all();
    assert_eq!(all.len(), 6);
    assert!(all.contains(&YamlFile::Main));
    assert!(all.iter().all(|file| file.as_str() != "Settings"));
}

#[test]
fn test_yaml_file_display() {
    assert_eq!(format!("{}", YamlFile::Main), "Main");
}

#[test]
fn test_yaml_file_serialization() {
    let yaml = YamlFile::Main;
    let json = serde_json::to_string(&yaml).unwrap();
    let deserialized: YamlFile = serde_json::from_str(&json).unwrap();
    assert_eq!(yaml, deserialized);
}
