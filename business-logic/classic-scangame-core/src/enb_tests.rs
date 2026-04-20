use super::*;
use std::fs;
use tempfile::TempDir;

fn create_test_game_dir(files: &[&str]) -> TempDir {
    let temp_dir = TempDir::new().unwrap();
    for file in files {
        let file_path = temp_dir.path().join(file);
        fs::write(file_path, b"test content").unwrap();
    }
    temp_dir
}

#[test]
fn test_enb_not_installed() {
    let temp_dir = create_test_game_dir(&[]);
    let checker = EnbChecker::new(temp_dir.path());

    assert_eq!(checker.check_binaries(), EnbResult::NotInstalled);
    assert_eq!(checker.check_config(), EnbConfigResult::NotFound);
}

#[test]
fn test_enb_present() {
    let temp_dir = create_test_game_dir(&["d3d11.dll", "d3dcompiler_46e.dll", "enbseries.ini"]);
    let checker = EnbChecker::new(temp_dir.path());

    assert_eq!(checker.check_binaries(), EnbResult::Present);
    assert_eq!(checker.check_config(), EnbConfigResult::Valid);

    let result = checker.validate();
    assert!(result.is_present());
    assert!(result.is_fully_configured());
}

#[test]
fn test_enb_partial() {
    let temp_dir = create_test_game_dir(&["d3d11.dll"]); // Missing d3dcompiler
    let checker = EnbChecker::new(temp_dir.path());

    assert_eq!(checker.check_binaries(), EnbResult::Partial);
}

#[test]
fn test_enb_partial_is_present() {
    let temp_dir = create_test_game_dir(&["d3d11.dll"]);
    let checker = EnbChecker::new(temp_dir.path());

    let result = checker.validate();
    assert!(result.is_present()); // Partial is still "present"
    assert!(!result.is_fully_configured()); // But not fully configured
}

#[test]
fn test_enb_present_no_config() {
    let temp_dir = create_test_game_dir(&["d3d11.dll", "d3dcompiler_46e.dll"]);
    let checker = EnbChecker::new(temp_dir.path());

    let result = checker.validate();
    assert!(result.is_present());
    assert!(!result.is_fully_configured()); // Missing config
    assert_eq!(result.config, EnbConfigResult::NotFound);
}

#[test]
fn test_format_message_present() {
    let temp_dir = create_test_game_dir(&["d3d11.dll", "d3dcompiler_46e.dll", "enbseries.ini"]);
    let checker = EnbChecker::new(temp_dir.path());

    let result = checker.validate();
    let message = checker.format_message(&result);
    assert!(message.contains("ENB is installed and configured"));
}

#[test]
fn test_format_message_not_installed() {
    let temp_dir = create_test_game_dir(&[]);
    let checker = EnbChecker::new(temp_dir.path());

    let result = checker.validate();
    let message = checker.format_message(&result);
    assert!(message.contains("ENB is not installed"));
}

#[test]
fn test_format_message_partial() {
    let temp_dir = create_test_game_dir(&["d3d11.dll"]);
    let checker = EnbChecker::new(temp_dir.path());

    let result = checker.validate();
    let message = checker.format_message(&result);
    assert!(message.contains("Partial ENB installation"));
}
