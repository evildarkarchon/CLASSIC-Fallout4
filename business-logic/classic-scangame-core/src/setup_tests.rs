use super::*;

// ========================================================================
// Settings Migration Tests
// ========================================================================

#[test]
fn test_migrate_game_version_setting_new_takes_precedence() {
    assert_eq!(
        migrate_game_version_setting(Some("Original"), Some(true)),
        Some("Original".to_string())
    );
    assert_eq!(
        migrate_game_version_setting(Some("NextGen"), Some(false)),
        Some("NextGen".to_string())
    );
    assert_eq!(
        migrate_game_version_setting(Some("AnniversaryEdition"), Some(false)),
        Some("AnniversaryEdition".to_string())
    );
    assert_eq!(
        migrate_game_version_setting(Some("AE"), Some(false)),
        Some("AnniversaryEdition".to_string())
    );
    assert_eq!(
        migrate_game_version_setting(Some("VR"), None),
        Some("VR".to_string())
    );
}

#[test]
fn test_migrate_game_version_setting_legacy_migration() {
    assert_eq!(
        migrate_game_version_setting(None, Some(true)),
        Some("VR".to_string())
    );
    assert_eq!(
        migrate_game_version_setting(Some("auto"), Some(true)),
        Some("VR".to_string())
    );
}

#[test]
fn test_migrate_game_version_setting_no_migration_needed() {
    assert_eq!(
        migrate_game_version_setting(Some("auto"), Some(false)),
        Some("auto".to_string())
    );
    assert_eq!(
        migrate_game_version_setting(Some("auto"), None),
        Some("auto".to_string())
    );
}

#[test]
fn test_migrate_game_version_setting_nothing_set() {
    assert_eq!(migrate_game_version_setting(None, None), None);
    assert_eq!(migrate_game_version_setting(None, Some(false)), None);
}

// ========================================================================
// Game Version Resolution Tests
// ========================================================================

#[test]
fn test_resolve_known_versions() {
    assert_eq!(resolve_effective_game_version(Some("Original")), "Original");
    assert_eq!(resolve_effective_game_version(Some("NextGen")), "NextGen");
    assert_eq!(
        resolve_effective_game_version(Some("AnniversaryEdition")),
        "AnniversaryEdition"
    );
    assert_eq!(
        resolve_effective_game_version(Some("AE")),
        "AnniversaryEdition"
    );
    assert_eq!(resolve_effective_game_version(Some("VR")), "VR");
    assert_eq!(resolve_effective_game_version(Some("auto")), "auto");
}

#[test]
fn test_resolve_unknown_defaults_to_auto() {
    assert_eq!(resolve_effective_game_version(Some("invalid")), "auto");
    assert_eq!(resolve_effective_game_version(Some("")), "auto");
    assert_eq!(resolve_effective_game_version(None), "auto");
}

// ========================================================================
// Path Detection Tests
// ========================================================================

#[test]
fn test_needs_path_detection_both_missing() {
    assert_eq!(needs_path_detection(None, None), (true, true));
}

#[test]
fn test_needs_path_detection_both_set() {
    assert_eq!(
        needs_path_detection(Some("C:\\Games"), Some("C:\\Docs")),
        (false, false)
    );
}

#[test]
fn test_needs_path_detection_partial() {
    assert_eq!(needs_path_detection(Some("C:\\Games"), None), (false, true));
    assert_eq!(needs_path_detection(None, Some("C:\\Docs")), (true, false));
}

#[test]
fn test_needs_path_detection_empty_strings() {
    assert_eq!(needs_path_detection(Some(""), Some("")), (true, true));
}

// ========================================================================
// SetupCheckResults Tests
// ========================================================================

#[test]
fn test_results_default_empty() {
    let results = SetupCheckResults::default();
    assert!(!results.has_errors());
    assert_eq!(results.total_checks(), 0);
    assert!(results.combined().is_empty());
}

#[test]
fn test_results_combined() {
    let results = SetupCheckResults {
        integrity_results: vec!["check1".into()],
        xse_results: vec!["check2".into()],
        docs_results: vec!["check3".into()],
        errors: vec![],
    };
    assert_eq!(results.combined(), "check1check2check3");
    assert_eq!(results.total_checks(), 3);
    assert!(!results.has_errors());
}

#[test]
fn test_results_with_errors() {
    let results = SetupCheckResults {
        integrity_results: vec![],
        xse_results: vec![],
        docs_results: vec![],
        errors: vec!["something failed".into()],
    };
    assert!(results.has_errors());
}
