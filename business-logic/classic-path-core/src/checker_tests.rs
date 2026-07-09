use super::*;
use std::fs;
use tempfile::TempDir;

fn create_test_docs(temp_dir: &Path, game_name: &str) -> std::path::PathBuf {
    let docs_path = temp_dir.join("My Games").join(game_name);
    fs::create_dir_all(&docs_path).unwrap();
    docs_path
}

fn create_test_ini(docs_path: &Path, ini_name: &str, content: &str) {
    let ini_path = docs_path.join(ini_name);
    fs::write(&ini_path, content).unwrap();
}

#[test]
fn test_new() {
    let checker = DocumentsChecker::new("Fallout4");
    assert_eq!(checker.game_name(), "Fallout4");
}

#[test]
fn test_check_onedrive_not_present() {
    let checker = DocumentsChecker::new("Fallout4");
    let path = Path::new("C:\\Users\\Name\\Documents\\My Games\\Fallout4");
    assert!(checker.check_onedrive_in_path(path).is_none());
}

#[test]
fn test_check_onedrive_present() {
    let checker = DocumentsChecker::new("Fallout4");
    let path = Path::new("C:\\Users\\Name\\OneDrive\\Documents\\My Games\\Fallout4");
    let warning = checker.check_onedrive_in_path(path);
    assert!(warning.is_some());
    assert!(warning.unwrap().contains("OneDrive"));
}

#[test]
fn test_check_onedrive_result_uses_warning_state() {
    let checker = DocumentsChecker::new("Fallout4");
    let path = Path::new("C:\\Users\\Name\\OneDrive\\Documents\\My Games\\Fallout4");

    let warning = checker
        .check_onedrive_in_path_result(path)
        .expect("OneDrive path should produce a warning");

    assert_eq!(warning.state, DocumentsCheckState::Warning);
    assert!(warning.message.contains("OneDrive"));
}

#[test]
fn test_validate_ini_file_missing() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs(temp_dir.path(), "Fallout4");

    let checker = DocumentsChecker::new("Fallout4");
    let result = checker
        .validate_ini_file(&docs_path, "Fallout4.ini")
        .unwrap();

    assert!(!result.exists);
    assert!(!result.is_valid);
    assert!(result.has_issue());
    assert_eq!(result.issue, Some("missing".to_string()));
}

#[test]
fn test_validate_ini_file_exists_valid() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
    create_test_ini(&docs_path, "Fallout4.ini", "[General]\nkey=value\n");

    let checker = DocumentsChecker::new("Fallout4");
    let result = checker
        .validate_ini_file(&docs_path, "Fallout4.ini")
        .unwrap();

    assert!(result.exists);
    assert!(result.is_valid);
    assert!(!result.has_issue());
    assert!(result.message.contains("✔️"));
}

#[test]
fn test_validate_ini_file_corrupted() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
    // Create invalid INI with malformed section header
    create_test_ini(&docs_path, "Fallout4.ini", "[General\nkey=value\n");

    let checker = DocumentsChecker::new("Fallout4");
    let result = checker
        .validate_ini_file(&docs_path, "Fallout4.ini")
        .unwrap();

    assert!(result.exists);
    assert!(!result.is_valid);
    assert!(result.has_issue());
    assert_eq!(result.issue, Some("corrupted".to_string()));
}

#[test]
fn test_validate_custom_ini_missing_archive() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
    create_test_ini(&docs_path, "Fallout4Custom.ini", "[General]\nkey=value\n");

    let checker = DocumentsChecker::new("Fallout4");
    let result = checker
        .validate_ini_file(&docs_path, "Fallout4Custom.ini")
        .unwrap();

    assert!(result.exists);
    assert!(result.is_valid);
    assert!(result.has_issue());
    assert_eq!(result.issue, Some("missing_archive_section".to_string()));
    assert!(result.message.contains("Archive Invalidation"));
}

#[test]
fn test_validate_custom_ini_has_archive() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
    create_test_ini(
        &docs_path,
        "Fallout4Custom.ini",
        "[Archive]\nbInvalidateOlderFiles=1\n",
    );

    let checker = DocumentsChecker::new("Fallout4");
    let result = checker
        .validate_ini_file(&docs_path, "Fallout4Custom.ini")
        .unwrap();

    assert!(result.exists);
    assert!(result.is_valid);
    assert!(!result.has_issue());
    assert!(result.message.contains("enabled"));
}

#[test]
fn test_run_all_checks() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
    create_test_ini(&docs_path, "Fallout4.ini", "[General]\nkey=value\n");
    create_test_ini(
        &docs_path,
        "Fallout4Custom.ini",
        "[Archive]\nbInvalidateOlderFiles=1\n",
    );
    create_test_ini(&docs_path, "Fallout4Prefs.ini", "[Display]\niSize W=1920\n");

    let checker = DocumentsChecker::new("Fallout4");
    let messages = checker.run_all_checks(&docs_path).unwrap();

    // Should have 3 messages (all OK)
    assert_eq!(messages.len(), 3);
    assert!(
        messages
            .iter()
            .all(|m| m.contains("✔️") || m.contains("enabled"))
    );
}

#[test]
fn test_run_all_checks_with_issues() {
    let temp_dir = TempDir::new().unwrap();
    let docs_path = create_test_docs(temp_dir.path(), "Fallout4");
    // Only create main INI, missing Custom and Prefs

    create_test_ini(&docs_path, "Fallout4.ini", "[General]\nkey=value\n");

    let checker = DocumentsChecker::new("Fallout4");
    let results = checker.run_all_check_results(&docs_path).unwrap();
    let messages = checker.run_all_checks(&docs_path).unwrap();

    // Should have 3 messages (1 OK, 2 missing)
    assert_eq!(messages.len(), 3);
    assert_eq!(results.len(), 3);
    assert_eq!(results[0].state, DocumentsCheckState::Passed);
    assert_eq!(results[1].state, DocumentsCheckState::Failed);
    assert_eq!(results[2].state, DocumentsCheckState::Failed);
    assert!(messages[0].contains("✔️")); // Main INI OK
    assert!(messages[1].contains("❌")); // Custom INI missing
    assert!(messages[2].contains("❌")); // Prefs INI missing
}
