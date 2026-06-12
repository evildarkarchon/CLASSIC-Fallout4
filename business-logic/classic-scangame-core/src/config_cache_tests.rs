use super::*;
use std::fs;
use tempfile::TempDir;

/// Helper: create a game root with some INI files
fn setup_game_root(files: &[(&str, &str)]) -> TempDir {
    let temp = TempDir::new().unwrap();
    for (name, content) in files {
        fs::write(temp.path().join(name), content).unwrap();
    }
    temp
}

#[test]
fn test_cache_creation_and_contains() {
    let root = setup_game_root(&[
        ("enblocal.ini", "[ENGINE]\nForceVSync=true\n"),
        ("epo.ini", "[Particles]\niMaxDesired=10000\n"),
    ]);

    let cache = ConfigFileCache::new(root.path(), &[]).unwrap();
    assert!(cache.contains("enblocal.ini"));
    assert!(cache.contains("epo.ini"));
    assert!(!cache.contains("nonexistent.ini"));
}

#[test]
fn test_get_str() {
    let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=10000\n")]);
    let mut cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    let val = cache.get_str("epo.ini", "Particles", "iMaxDesired");
    assert_eq!(val.as_deref(), Some("10000"));
}

#[test]
fn test_get_bool() {
    let root = setup_game_root(&[("enblocal.ini", "[ENGINE]\nForceVSync=true\n")]);
    let mut cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    assert_eq!(
        cache.get_bool("enblocal.ini", "ENGINE", "ForceVSync"),
        Some(true)
    );
}

#[test]
fn test_get_int() {
    let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=5000\n")]);
    let mut cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    assert_eq!(
        cache.get_int("epo.ini", "Particles", "iMaxDesired"),
        Some(5000)
    );
}

#[test]
fn test_get_float() {
    let root = setup_game_root(&[(
        "highfpsphysicsfix.ini",
        "[Limiter]\nLoadingScreenFPS=600.0\n",
    )]);
    let mut cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    assert_eq!(
        cache.get_float("highfpsphysicsfix.ini", "Limiter", "LoadingScreenFPS"),
        Some(600.0)
    );
}

#[test]
fn test_get_nonexistent_file() {
    let root = setup_game_root(&[]);
    let mut cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    assert!(cache.get_str("nope.ini", "S", "K").is_none());
}

#[test]
fn test_get_nonexistent_section() {
    let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=10000\n")]);
    let mut cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    assert!(cache.get_str("epo.ini", "NoSection", "K").is_none());
}

#[test]
fn test_has_setting() {
    let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=10000\n")]);
    let mut cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    assert!(cache.has_setting("epo.ini", "Particles", "iMaxDesired"));
    assert!(!cache.has_setting("epo.ini", "Particles", "nope"));
    assert!(!cache.has_setting("nope.ini", "S", "K"));
}

#[test]
fn test_detect_issue_triggered() {
    let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=10000\n")]);
    let mut cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    let issue = cache.detect_issue(
        "epo.ini",
        "Particles",
        "iMaxDesired",
        "5000",
        "Particle count too high",
        |val| val.trim().parse::<i64>().is_ok_and(|v| v > 5000),
        IssueSeverity::Warning,
    );

    assert!(issue.is_some());
    let issue = issue.unwrap();
    assert_eq!(issue.setting, "iMaxDesired");
    assert_eq!(issue.current_value, "10000");
    assert_eq!(issue.recommended_value, "5000");
}

#[test]
fn test_detect_issue_not_triggered() {
    let root = setup_game_root(&[("epo.ini", "[Particles]\niMaxDesired=3000\n")]);
    let mut cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    let issue = cache.detect_issue(
        "epo.ini",
        "Particles",
        "iMaxDesired",
        "5000",
        "Particle count too high",
        |val| val.trim().parse::<i64>().is_ok_and(|v| v > 5000),
        IssueSeverity::Warning,
    );

    assert!(issue.is_none());
}

#[test]
fn test_duplicate_detection() {
    let root = TempDir::new().unwrap();
    let sub1 = root.path().join("dir1");
    let sub2 = root.path().join("dir2");
    fs::create_dir(&sub1).unwrap();
    fs::create_dir(&sub2).unwrap();

    // Write identical content to detect as duplicate
    let content = "[Section]\nkey=value\n";
    fs::write(sub1.join("test.ini"), content).unwrap();
    fs::write(sub2.join("test.ini"), content).unwrap();

    let cache = ConfigFileCache::new(root.path(), &[]).unwrap();
    assert!(cache.duplicate_files.contains_key("test.ini"));
}

#[test]
fn test_game_root_not_found() {
    let result = ConfigFileCache::new(Path::new("/nonexistent/game/root"), &[]);
    assert!(result.is_err());
}

#[test]
fn test_iter() {
    let root = setup_game_root(&[("one.ini", "[S]\nk=v\n"), ("two.ini", "[S]\nk=v\n")]);
    let cache = ConfigFileCache::new(root.path(), &[]).unwrap();

    let names: Vec<&str> = cache.iter().map(|(name, _)| name).collect();
    assert_eq!(names.len(), 2);
    assert!(names.contains(&"one.ini"));
    assert!(names.contains(&"two.ini"));
}

#[test]
fn test_read_toml_value() {
    let root = TempDir::new().unwrap();
    let toml_path = root.path().join("config.toml");
    fs::write(
        &toml_path,
        "[Patches]\nAchievements = true\nMaxStdIO = 2048\n",
    )
    .unwrap();

    let val = read_toml_value(&toml_path, "Patches", "Achievements").unwrap();
    assert_eq!(val, Some(toml::Value::Boolean(true)));

    let val = read_toml_value(&toml_path, "Patches", "MaxStdIO").unwrap();
    assert_eq!(val, Some(toml::Value::Integer(2048)));

    let val = read_toml_value(&toml_path, "Patches", "Nonexistent").unwrap();
    assert!(val.is_none());

    let val = read_toml_value(&toml_path, "NoSection", "Key").unwrap();
    assert!(val.is_none());
}

#[test]
fn test_decode_with_detection_utf8() {
    let text = "Hello, world!";
    let (decoded, _encoding) = decode_with_detection(text.as_bytes());
    assert_eq!(decoded, "Hello, world!");
}
