use super::*;
use std::io::Write;
use tempfile::NamedTempFile;

#[test]
fn test_integrity_config_creation() {
    let config = IntegrityConfig::new(
        PathBuf::from("/path/to/game.exe"),
        vec!["hash1".to_string(), "hash2".to_string()],
        "Test Game".to_string(),
    );

    assert_eq!(config.game_exe_path, PathBuf::from("/path/to/game.exe"));
    assert_eq!(config.valid_exe_hashes.len(), 2);
    assert!(config.valid_exe_hashes.contains(&"hash1".to_string()));
    assert!(config.valid_exe_hashes.contains(&"hash2".to_string()));
    assert_eq!(config.root_name, "Test Game");
    assert!(config.steam_ini_path.is_none());
    assert!(config.root_warn.is_none());
}

#[test]
fn test_integrity_config_builders() {
    let config = IntegrityConfig::new(
        PathBuf::from("/path/to/game.exe"),
        vec!["hash1".to_string(), "hash2".to_string()],
        "Test Game".to_string(),
    )
    .with_steam_ini(PathBuf::from("/path/to/steam.ini"))
    .with_root_warn("Warning message".to_string());

    assert_eq!(
        config.steam_ini_path,
        Some(PathBuf::from("/path/to/steam.ini"))
    );
    assert_eq!(config.root_warn, Some("Warning message".to_string()));
}

#[test]
fn test_calculate_sha256_file() {
    let mut temp_file = NamedTempFile::new().unwrap();
    writeln!(temp_file, "Test content").unwrap();
    temp_file.flush().unwrap();

    let hash = calculate_sha256_file(temp_file.path()).unwrap();

    // SHA256 of "Test content\n" (with newline)
    assert!(!hash.is_empty());
    assert_eq!(hash.len(), 64); // SHA256 produces 64 hex characters
}

#[test]
fn test_calculate_sha256_nonexistent_file() {
    let result = calculate_sha256_file(Path::new("/nonexistent/file.exe"));
    assert!(result.is_err());
    assert!(matches!(result, Err(IntegrityError::FileNotFound(_))));
}

#[test]
fn test_check_installation_location() {
    // Create a temporary file to simulate game executable
    let temp_file = NamedTempFile::new().unwrap();
    let temp_path = temp_file.path().to_path_buf();

    let config = IntegrityConfig::new(
        temp_path,
        vec!["hash1".to_string(), "hash2".to_string()],
        "Test Game".to_string(),
    );

    let checker = GameIntegrityChecker::new(config);
    let result = checker.check_installation_location().unwrap();

    // Temporary file should not be in Program Files
    assert!(result.is_valid);
    assert!(
        result
            .message
            .contains("outside of the Program Files folder")
    );
}

#[test]
fn test_check_installation_location_nonexistent() {
    let config = IntegrityConfig::new(
        PathBuf::from("/nonexistent/game.exe"),
        vec!["hash1".to_string()],
        "Test Game".to_string(),
    );

    let checker = GameIntegrityChecker::new(config);
    let result = checker.check_installation_location().unwrap();

    assert!(!result.is_valid);
    assert!(result.message.is_empty());
}

#[test]
fn test_integrity_check_result() {
    let result = IntegrityCheckResult::new(
        true,
        "Test message".to_string(),
        CheckType::ExecutableVersion,
    );

    assert!(result.is_valid);
    assert_eq!(result.message, "Test message");
    assert_eq!(result.check_type, CheckType::ExecutableVersion);
}
