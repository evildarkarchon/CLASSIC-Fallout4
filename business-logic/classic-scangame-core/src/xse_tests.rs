use super::*;
use std::fs;
use tempfile::TempDir;

/// Helper to create a test plugins directory with optional files.
fn setup_test_plugins_dir(files: &[&str]) -> TempDir {
    let temp_dir = TempDir::new().unwrap();

    for file in files {
        let file_path = temp_dir.path().join(file);
        fs::write(file_path, b"test content").unwrap();
    }

    temp_dir
}

#[test]
fn test_game_version_is_null() {
    assert!(GameVersion::Null.is_null());
    assert!(!GameVersion::Original.is_null());
    assert!(!GameVersion::NextGen.is_null());
    assert!(!GameVersion::AnniversaryEdition.is_null());
    assert!(!GameVersion::Vr.is_null());
}

#[test]
fn test_address_lib_info_creation() {
    let vr_info = AddressLibInfo::vr();
    assert_eq!(vr_info.version, GameVersion::Vr);
    assert_eq!(vr_info.filename, "version-1-2-72-0.csv");

    let og_info = AddressLibInfo::original();
    assert_eq!(og_info.version, GameVersion::Original);
    assert_eq!(og_info.filename, "version-1-10-163-0.bin");

    let ng_info = AddressLibInfo::next_gen();
    assert_eq!(ng_info.version, GameVersion::NextGen);
    assert_eq!(ng_info.filename, "version-1-10-984-0.bin");

    let ae_info = AddressLibInfo::anniversary_edition();
    assert_eq!(ae_info.version, GameVersion::AnniversaryEdition);
    assert_eq!(ae_info.filename, "version-1-11-191-0.bin");
}

#[test]
fn test_correct_version_non_vr_ae() {
    let temp_dir = setup_test_plugins_dir(&["version-1-11-191-0.bin"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::AnniversaryEdition).unwrap();

    let result = checker.check();
    assert_eq!(result, ValidationResult::CorrectVersion);
}

#[test]
fn test_correct_version_vr_mode() {
    let temp_dir = setup_test_plugins_dir(&["version-1-2-72-0.csv"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Vr).unwrap();

    let result = checker.check();
    assert_eq!(result, ValidationResult::CorrectVersion);
}

#[test]
fn test_correct_version_non_vr_og() {
    let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Original).unwrap();

    let result = checker.check();
    assert_eq!(result, ValidationResult::CorrectVersion);
}

#[test]
fn test_correct_version_non_vr_ng() {
    let temp_dir = setup_test_plugins_dir(&["version-1-10-984-0.bin"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::NextGen).unwrap();

    let result = checker.check();
    assert_eq!(result, ValidationResult::CorrectVersion);
}

#[test]
fn test_wrong_version_vr_has_og() {
    let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Vr).unwrap();

    let result = checker.check();
    assert_eq!(result, ValidationResult::WrongVersion);
}

#[test]
fn test_wrong_version_non_vr_has_vr() {
    let temp_dir = setup_test_plugins_dir(&["version-1-2-72-0.csv"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Original).unwrap();

    let result = checker.check();
    assert_eq!(result, ValidationResult::WrongVersion);
}

#[test]
fn test_not_found() {
    let temp_dir = setup_test_plugins_dir(&[]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Original).unwrap();

    let result = checker.check();
    assert_eq!(result, ValidationResult::NotFound);
}

#[test]
fn test_version_not_detected() {
    let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Null).unwrap();

    let result = checker.check();
    assert_eq!(result, ValidationResult::VersionNotDetected);
}

#[test]
fn test_invalid_plugins_path() {
    let result = XseChecker::new("/nonexistent/path", GameVersion::Original);
    assert!(result.is_err());
}

#[test]
fn test_message_formatting_correct() {
    let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Original).unwrap();

    let message = checker.validate();
    assert!(message.contains("✔️"));
    assert!(message.contains("correct version"));
}

#[test]
fn test_message_formatting_wrong() {
    let temp_dir = setup_test_plugins_dir(&["version-1-2-72-0.csv"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Original).unwrap();

    let message = checker.validate();
    assert!(message.contains("❌"));
    assert!(message.contains("wrong version"));
    // Description from VersionRegistry: "Fallout 4 Original (OG)"
    assert!(message.contains("Fallout 4 Original"));
}

#[test]
fn test_message_formatting_not_found() {
    let temp_dir = setup_test_plugins_dir(&[]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Original).unwrap();

    let message = checker.validate();
    assert!(message.contains("❓"));
    assert!(message.contains("not found"));
}

#[test]
fn test_message_formatting_version_not_detected() {
    let temp_dir = setup_test_plugins_dir(&["version-1-10-163-0.bin"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Null).unwrap();

    let message = checker.validate();
    assert!(message.contains("❓"));
    assert!(message.contains("Unable to locate"));
}

#[test]
fn test_multiple_correct_versions_non_vr() {
    // Non-VR can have either OG or NG - both are correct
    let temp_dir =
        setup_test_plugins_dir(&["version-1-10-163-0.bin", "version-1-10-984-0.bin"]);
    let checker = XseChecker::new(temp_dir.path(), GameVersion::Original).unwrap();

    let result = checker.check();
    assert_eq!(result, ValidationResult::CorrectVersion);
}
