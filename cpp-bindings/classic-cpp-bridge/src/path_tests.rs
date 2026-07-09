use super::*;
use std::fs;
use tempfile::TempDir;

// ── Existing tests (regression guard) ────────────────────────────────────

#[test]
fn test_detect_fallout4_game_path_empty_input() {
    let result = detect_fallout4_game_path("", "Original");
    // May be empty on systems without game installation.
    assert!(!result.contains('\0'));
}

#[test]
fn test_resolve_fallout4_exe_name_uses_registry_metadata() {
    assert_eq!(resolve_fallout4_exe_name("Original"), "Fallout4.exe");
    assert_eq!(resolve_fallout4_exe_name("VR"), "Fallout4VR.exe");
}

#[test]
fn test_detect_fallout4_docs_path_empty_input() {
    let result = detect_fallout4_docs_path("", "Original");
    // May be empty on non-Windows test hosts or missing docs dir.
    assert!(!result.contains('\0'));
}

#[test]
fn test_fallout4_docs_relative_path_uses_proton_safe_separator() {
    assert_eq!(fallout4_docs_relative_path("Fallout4"), "My Games/Fallout4");
    assert_eq!(
        fallout4_docs_relative_path("Fallout4VR"),
        "My Games/Fallout4VR"
    );
}

// ── New tests for widened CXXS-08 surface ────────────────────────────────

#[test]
fn test_is_valid_path_on_manifest_dir() {
    let p = env!("CARGO_MANIFEST_DIR");
    assert!(is_valid_path(p));
    assert!(validate_path(p)); // alias
}

#[test]
fn test_is_restricted_path_false_on_manifest_dir() {
    let p = env!("CARGO_MANIFEST_DIR");
    assert!(!is_restricted_path(p));
    assert!(!check_restricted_path(p)); // alias
}

#[test]
fn test_is_restricted_path_true_on_windows_dir() {
    assert!(is_restricted_path("C:\\Windows"));
    assert!(is_restricted_path("C:\\Program Files\\SomeGame"));
}

#[test]
fn test_path_validate_exists_empty_returns_err() {
    assert!(path_validate_exists("").is_err());
}

#[test]
fn test_path_validate_exists_manifest_dir_ok() {
    assert!(path_validate_exists(env!("CARGO_MANIFEST_DIR")).is_ok());
}

#[test]
fn test_path_validate_is_directory_manifest_dir_ok() {
    assert!(path_validate_is_directory(env!("CARGO_MANIFEST_DIR")).is_ok());
}

#[test]
fn test_path_validate_is_directory_empty_returns_err() {
    assert!(path_validate_is_directory("").is_err());
}

#[test]
fn test_path_validate_is_file_empty_returns_err() {
    assert!(path_validate_is_file("").is_err());
}

#[test]
fn test_docs_checker_validate_ini_file_missing_real_shape() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = temp_dir.path().to_string_lossy().to_string();
    let result = docs_checker_validate_ini_file(&docs_path, "Fallout4", "Fallout4.ini");
    assert!(!result.exists);
    assert!(!result.is_valid);
    assert!(result.has_issue);
    assert_eq!(result.issue_or_empty, "missing");
    assert_eq!(result.ini_name, "Fallout4.ini");
    assert!(!result.message.is_empty());
}

#[test]
fn test_docs_checker_validate_ini_file_empty_path_fail_soft() {
    let result = docs_checker_validate_ini_file("", "Fallout4", "Fallout4.ini");
    assert!(!result.exists);
    assert!(result.has_issue);
}

#[test]
fn test_docs_checker_validate_ini_file_existing_valid() {
    let temp_dir = TempDir::new().unwrap();
    fs::write(
        temp_dir.path().join("Fallout4.ini"),
        "[General]\nkey=value\n",
    )
    .unwrap();
    let docs_path = temp_dir.path().to_string_lossy().to_string();
    let result = docs_checker_validate_ini_file(&docs_path, "Fallout4", "Fallout4.ini");
    assert!(result.exists);
    assert!(result.is_valid);
    assert!(!result.has_issue);
}

#[test]
fn test_docs_checker_run_all_checks_empty_path_returns_empty() {
    assert!(docs_checker_run_all_checks("", "Fallout4").is_empty());
}

#[test]
fn test_docs_checker_run_all_checks_returns_messages_for_missing_inis() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = temp_dir.path().to_string_lossy().to_string();
    let messages = docs_checker_run_all_checks(&docs_path, "Fallout4");
    // Three checks (Main, Custom, Prefs) all missing → at least 3 messages
    assert!(messages.len() >= 3);
    for msg in &messages {
        assert!(!msg.is_empty());
    }
}

#[test]
fn test_backup_list_existing_missing_source_returns_empty() {
    let result = backup_list_existing("nonexistent\\path\\file.ini", "Fallout4");
    assert!(result.is_empty());
}

#[test]
fn test_backup_list_existing_empty_path_returns_empty() {
    let result = backup_list_existing("", "Fallout4");
    assert!(result.is_empty());
}

#[test]
fn test_parse_xse_log_nonexistent_returns_err() {
    let result = parse_xse_log("nonexistent.log");
    assert!(result.is_err());
}

#[test]
fn test_parse_xse_log_empty_returns_err() {
    let result = parse_xse_log("");
    assert!(result.is_err());
}

#[test]
fn test_find_game_path_empty_inputs_returns_empty_string() {
    let result = find_game_path("", "", "", false, "", "");
    assert!(result.is_empty());
}
