use super::*;
use std::fs;
use tempfile::TempDir;

#[test]
fn test_game_path_finder_new() {
    let finder =
        GamePathFinder::new("Fallout4.exe", Some("f4se_loader.exe"), "Fallout4", false);

    assert_eq!(finder.game_exe(), "Fallout4.exe");
    assert_eq!(finder.xse_loader(), Some("f4se_loader.exe"));
    assert!(!finder.is_vr());
}

#[test]
fn test_game_path_finder_vr() {
    let finder = GamePathFinder::new("Fallout4VR.exe", None::<&str>, "Fallout4", true);

    assert_eq!(finder.game_exe(), "Fallout4VR.exe");
    assert_eq!(finder.xse_loader(), None);
    assert!(finder.is_vr());
}

#[test]
fn test_validate_game_path_success() {
    let temp_dir = TempDir::new().unwrap();
    let game_dir = temp_dir.path();

    // Create mock game files
    fs::write(game_dir.join("Fallout4.exe"), "mock exe").unwrap();
    fs::write(game_dir.join("f4se_loader.exe"), "mock loader").unwrap();

    let finder =
        GamePathFinder::new("Fallout4.exe", Some("f4se_loader.exe"), "Fallout4", false);

    let result = finder.validate_game_path(game_dir);
    assert!(result.is_ok());
}

#[test]
fn test_validate_game_path_missing_exe() {
    let temp_dir = TempDir::new().unwrap();
    let game_dir = temp_dir.path();

    let finder = GamePathFinder::new("Fallout4.exe", None::<&str>, "Fallout4", false);

    let result = finder.validate_game_path(game_dir);
    assert!(result.is_err());
    match result {
        Err(GamePathError::ValidationFailed(msg)) => {
            assert!(msg.contains("Fallout4.exe"));
        }
        _ => panic!("Expected ValidationFailed error"),
    }
}

#[test]
fn test_validate_game_path_missing_loader() {
    let temp_dir = TempDir::new().unwrap();
    let game_dir = temp_dir.path();

    // Create only the game exe, not the loader
    fs::write(game_dir.join("Fallout4.exe"), "mock exe").unwrap();

    let finder =
        GamePathFinder::new("Fallout4.exe", Some("f4se_loader.exe"), "Fallout4", false);

    let result = finder.validate_game_path(game_dir);
    assert!(result.is_err());
}

#[test]
fn test_find_game_path_cached() {
    let temp_dir = TempDir::new().unwrap();
    let game_dir = temp_dir.path();

    // Create mock game files
    fs::write(game_dir.join("Fallout4.exe"), "mock exe").unwrap();

    let finder = GamePathFinder::new("Fallout4.exe", None::<&str>, "Fallout4", false);

    let result = finder.find_game_path(Some(game_dir), None);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), game_dir);
}

#[test]
fn test_find_game_path_invalid_cached() {
    let temp_dir = TempDir::new().unwrap();
    let invalid_dir = temp_dir.path().join("nonexistent");

    // Use a fake game name that won't be in registry
    let finder = GamePathFinder::new("FakeGame.exe", None::<&str>, "FakeGame123", false);

    let result = finder.find_game_path(Some(&invalid_dir), None);
    assert!(result.is_err());
}

#[test]
fn test_parse_xse_log_success() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("f4se.log");

    // Create mock XSE log with plugin directory line
    let log_content = r#"
F4SE version = 0.6.23
plugin directory = C:\Games\Fallout4\Data\F4SE\Plugins\
checking plugin C:\Games\Fallout4\Data\F4SE\Plugins\example.dll
"#;
    fs::write(&log_path, log_content).unwrap();

    let result = parse_xse_log(&log_path);
    assert!(result.is_ok());

    let game_path = result.unwrap();
    assert_eq!(game_path, PathBuf::from("C:\\Games\\Fallout4"));
}

#[test]
fn test_parse_xse_log_with_quotes() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("f4se.log");

    // Create mock XSE log with quoted path
    let log_content = r#"
plugin directory = "C:\Program Files\Fallout4\Data\F4SE\Plugins\"
"#;
    fs::write(&log_path, log_content).unwrap();

    let result = parse_xse_log(&log_path);
    assert!(result.is_ok());

    let game_path = result.unwrap();
    assert_eq!(game_path, PathBuf::from("C:\\Program Files\\Fallout4"));
}

#[test]
fn test_parse_xse_log_missing_line() {
    let temp_dir = TempDir::new().unwrap();
    let log_path = temp_dir.path().join("f4se.log");

    // Create log without plugin directory line
    let log_content = "F4SE version = 0.6.23\nloading plugins...\n";
    fs::write(&log_path, log_content).unwrap();

    let result = parse_xse_log(&log_path);
    assert!(result.is_err());
    match result {
        Err(GamePathError::XseLogParseError(_)) => {}
        _ => panic!("Expected XseLogParseError"),
    }
}

#[test]
fn test_parse_xse_log_not_found() {
    let nonexistent = PathBuf::from("nonexistent_log.txt");

    let result = parse_xse_log(&nonexistent);
    assert!(result.is_err());
    match result {
        Err(GamePathError::XseLogNotFound(path)) => {
            assert_eq!(path, nonexistent);
        }
        _ => panic!("Expected XseLogNotFound error"),
    }
}

#[test]
fn test_find_via_xse_log_integration() {
    let temp_dir = TempDir::new().unwrap();

    // Create game directory with exe
    let game_dir = temp_dir.path().join("Games").join("Fallout4");
    fs::create_dir_all(&game_dir).unwrap();
    fs::write(game_dir.join("Fallout4.exe"), "mock exe").unwrap();

    // Create XSE log pointing to this game
    let log_path = temp_dir.path().join("f4se.log");
    let plugin_path = game_dir.join("Data").join("F4SE").join("Plugins");
    let log_content = format!("plugin directory = {}\\", plugin_path.display());
    fs::write(&log_path, log_content).unwrap();

    let finder = GamePathFinder::new("Fallout4.exe", None::<&str>, "Fallout4", false);

    let result = finder.find_via_xse_log(&log_path);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), game_dir);
}
