use super::*;
use classic_database_core::DatabasePool;
use classic_scanlog_core::{ConfigIssue, GLOBAL_FCX_HANDLER};
use std::time::Duration;
use tempfile::tempdir;

fn sample_issue() -> ConfigIssue {
    ConfigIssue::new(
        "test.ini".to_string(),
        Some("General".to_string()),
        "bExample".to_string(),
        "0".to_string(),
        "1".to_string(),
        "Example issue".to_string(),
        "warning".to_string(),
    )
}

fn seed_dirty_fcx_state() {
    let mut handler = GLOBAL_FCX_HANDLER.lock();
    handler.fcx_mode = true;
    handler.set_main_files_result("Main files OK\n".to_string());
    handler.set_game_files_result("Game files OK\n".to_string());
    handler.set_detected_issues(vec![sample_issue()]);
    handler.checks_run = true;
}

fn assert_clean_fcx_state() {
    let handler = GLOBAL_FCX_HANDLER.lock();
    assert!(handler.main_files_check.is_none());
    assert!(handler.game_files_check.is_none());
    assert!(handler.detected_issues.is_empty());
    assert!(!handler.checks_run);
}

#[test]
fn test_orchestrator_new_minimal() {
    let result = orchestrator_new_minimal("Fallout4", "auto", "Buffout 4", "F4SE");
    assert!(result.is_ok());
}

#[test]
#[serial_test::serial]
fn test_fcx_reset_global_state_treats_unnecessary_as_success() {
    {
        let mut handler = GLOBAL_FCX_HANDLER.lock();
        handler.reset();
    }

    assert!(fcx_reset_global_state().is_ok());
    assert_clean_fcx_state();
}

#[test]
#[serial_test::serial]
fn test_fcx_reset_global_state_clears_dirty_state() {
    seed_dirty_fcx_state();

    assert!(fcx_reset_global_state().is_ok());
    assert_clean_fcx_state();
}

#[test]
#[serial_test::serial]
fn test_orchestrator_process_log_resets_fcx_before_scan_start() {
    let orchestrator = orchestrator_new_minimal("Fallout4", "auto", "Buffout 4", "F4SE").unwrap();
    seed_dirty_fcx_state();

    let result = orchestrator_process_log(&orchestrator, "missing.log");
    assert!(result.is_err());
    assert_clean_fcx_state();
}

#[test]
#[serial_test::serial]
fn test_orchestrator_process_logs_batch_resets_fcx_before_scan_start() {
    let orchestrator = orchestrator_new_minimal("Fallout4", "auto", "Buffout 4", "F4SE").unwrap();
    seed_dirty_fcx_state();

    let results = orchestrator_process_logs_batch(&orchestrator, &["missing.log".to_string()], 1);
    assert_eq!(results.len(), 1);
    assert!(!results[0].success);
    assert_clean_fcx_state();
}

#[test]
fn test_parse_db_counter_interval() {
    assert_eq!(
        parse_db_counter_interval(None),
        DB_COUNTER_LOG_INTERVAL_DEFAULT
    );
    assert_eq!(
        parse_db_counter_interval(Some(" 50 ")),
        50,
        "Valid positive interval should be accepted"
    );
    assert_eq!(
        parse_db_counter_interval(Some("0")),
        DB_COUNTER_LOG_INTERVAL_DEFAULT,
        "Zero should fall back to default"
    );
    assert_eq!(
        parse_db_counter_interval(Some("not-a-number")),
        DB_COUNTER_LOG_INTERVAL_DEFAULT,
        "Invalid values should fall back to default"
    );
}

#[test]
fn test_build_full_scan_config_invalid_dirs() {
    let result = build_full_scan_config(
        "nonexistent_root",
        "nonexistent_data",
        "Fallout4",
        "auto",
        false,
        false,
        false,
    );
    assert!(result.is_err());
}

#[test]
fn test_resolve_formid_db_paths_includes_main_and_hardcoded_folon() {
    let temp = tempdir().unwrap();
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    std::fs::create_dir_all(data.join("databases")).unwrap();

    // Explicit empty user list should still include hardcoded FOLON path.
    std::fs::write(
        root.join("CLASSIC Settings.yaml"),
        "CLASSIC_Settings:\n  FormID Databases:\n    Fallout4: []\n",
    )
    .unwrap();

    let paths =
        resolve_formid_db_paths(&root.to_string_lossy(), &data.to_string_lossy(), "Fallout4");
    let main = data.join("databases").join("Fallout4 FormIDs Main.db");
    let folon = data.join("databases").join("FOLON FormIDs.db");

    assert_eq!(paths, vec![main, folon]);
}

#[test]
fn test_resolve_formid_db_paths_deduplicates_hardcoded_and_user_paths() {
    let temp = tempdir().unwrap();
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    std::fs::create_dir_all(data.join("databases")).unwrap();
    let custom = data.join("databases").join("custom.db");

    let settings_yaml = "CLASSIC_Settings:\n  FormID Databases:\n    Fallout4:\n      - databases/FOLON FormIDs.db\n      - databases/custom.db\n";
    std::fs::write(root.join("CLASSIC Settings.yaml"), settings_yaml).unwrap();

    let paths =
        resolve_formid_db_paths(&root.to_string_lossy(), &data.to_string_lossy(), "Fallout4");
    let main = data.join("databases").join("Fallout4 FormIDs Main.db");
    let folon = data.join("databases").join("FOLON FormIDs.db");

    assert_eq!(paths, vec![main, folon, custom]);
}

#[test]
fn test_load_user_formid_db_paths_ignores_legacy_underscore_settings_filename() {
    let temp = tempdir().unwrap();
    let root = temp.path();
    let data = root.join("CLASSIC Data");
    std::fs::create_dir_all(data.join("databases")).unwrap();

    let settings_yaml =
        "CLASSIC_Settings:\n  FormID Databases:\n    Fallout4:\n      - databases/custom.db\n";
    std::fs::write(root.join("CLASSIC_Settings.yaml"), settings_yaml).unwrap();

    let paths =
        load_user_formid_db_paths(&root.to_string_lossy(), &data.to_string_lossy(), "Fallout4");

    assert!(paths.is_empty());
}

#[test]
fn test_load_exclude_log_records_reads_main_yaml_setting() {
    let temp = tempdir().unwrap();
    let data = temp.path();
    std::fs::create_dir_all(data.join("databases")).unwrap();

    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        "exclude_log_records:\n  - '(void*)'\n  - 'Basic Render Driver'\n",
    )
    .unwrap();

    let records = load_exclude_log_records(&data.to_string_lossy());
    assert_eq!(
        records,
        vec!["(void*)".to_string(), "Basic Render Driver".to_string()]
    );
}

#[test]
fn test_apply_short_scan_db_profile_sets_pool_knobs() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "Fallout4".to_string());
    apply_short_scan_db_profile(&pool);

    assert_eq!(pool.get_cache_capacity(), SHORT_SCAN_CACHE_CAPACITY);
    assert_eq!(
        pool.get_cache_ttl(),
        Duration::from_secs(SHORT_SCAN_CACHE_TTL_SECS)
    );
    assert_eq!(
        pool.get_cache_cleanup_threshold(),
        SHORT_SCAN_CLEANUP_THRESHOLD
    );
    assert_eq!(
        pool.get_cache_cleanup_interval(),
        Duration::from_secs(SHORT_SCAN_CLEANUP_INTERVAL_SECS)
    );
}

/// Empty-state contract: after reset, get_fcx_config_issues() returns empty Vec.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_after_reset_returns_empty() {
    let _ = fcx_reset_global_state();
    let issues = get_fcx_config_issues();
    assert!(
        issues.is_empty(),
        "Expected empty Vec after reset, got {} issues",
        issues.len()
    );
}

/// Fresh-state contract: before any scan, handler lazy-inits with empty detected_issues.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_fresh_state_returns_empty() {
    // Reset to known-clean state first
    let _ = fcx_reset_global_state();
    let issues = get_fcx_config_issues();
    assert!(
        issues.is_empty(),
        "Expected empty Vec on fresh state, got {} issues",
        issues.len()
    );
}

/// Idempotence: calling get_fcx_config_issues() twice without state change returns same length.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_idempotent() {
    let _ = fcx_reset_global_state();
    let issues1 = get_fcx_config_issues();
    let issues2 = get_fcx_config_issues();
    assert_eq!(
        issues1.len(),
        issues2.len(),
        "get_fcx_config_issues() must be read-only; repeated calls should return same length"
    );
}

/// Round-trip: section None maps to section_or_empty="" + has_section=false;
/// section Some("Display") maps to section_or_empty="Display" + has_section=true.
/// Also verifies all other fields are correctly mapped.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_round_trips_section_none_and_some() {
    let _ = fcx_reset_global_state();

    // Inject two issues: one with section: None, one with section: Some("Display")
    {
        let mut handler = GLOBAL_FCX_HANDLER.lock();
        handler.set_detected_issues(vec![
            ConfigIssue::new(
                "Fallout4.ini".to_string(),
                None,
                "iNumThreads".to_string(),
                "4".to_string(),
                "8".to_string(),
                "thread count too low".to_string(),
                "warning".to_string(),
            ),
            ConfigIssue::new(
                "Fallout4Prefs.ini".to_string(),
                Some("Display".to_string()),
                "iSize W".to_string(),
                "640".to_string(),
                "1920".to_string(),
                "resolution too low".to_string(),
                "info".to_string(),
            ),
        ]);
    }

    let issues = get_fcx_config_issues();
    assert_eq!(issues.len(), 2, "Expected exactly 2 issues after injection");

    // First issue: section None → section_or_empty="" + has_section=false
    assert_eq!(issues[0].file_path, "Fallout4.ini");
    assert_eq!(
        issues[0].section_or_empty, "",
        "section: None must produce section_or_empty = \"\""
    );
    assert!(
        !issues[0].has_section,
        "section: None must produce has_section = false"
    );
    assert_eq!(issues[0].setting, "iNumThreads");
    assert_eq!(issues[0].current_value, "4");
    assert_eq!(issues[0].recommended_value, "8");
    assert_eq!(issues[0].description, "thread count too low");
    assert_eq!(issues[0].severity, "warning");

    // Second issue: section Some("Display") → section_or_empty="Display" + has_section=true
    assert_eq!(issues[1].file_path, "Fallout4Prefs.ini");
    assert_eq!(
        issues[1].section_or_empty, "Display",
        "section: Some(\"Display\") must produce section_or_empty = \"Display\""
    );
    assert!(
        issues[1].has_section,
        "section: Some(\"Display\") must produce has_section = true"
    );
    assert_eq!(issues[1].setting, "iSize W");
    assert_eq!(issues[1].current_value, "640");
    assert_eq!(issues[1].recommended_value, "1920");
    assert_eq!(issues[1].description, "resolution too low");
    assert_eq!(issues[1].severity, "info");

    // Cleanup
    let _ = fcx_reset_global_state();
}

/// Regression: fcx_reset_global_state() still works correctly (D-08 preserved).
#[test]
#[serial_test::serial]
fn test_fcx_reset_clears_issues_visible_to_getter() {
    // Seed some issues
    {
        let mut handler = GLOBAL_FCX_HANDLER.lock();
        handler.set_detected_issues(vec![ConfigIssue::new(
            "file.ini".to_string(),
            None,
            "key".to_string(),
            "old".to_string(),
            "new".to_string(),
            "desc".to_string(),
            "info".to_string(),
        )]);
    }

    // Verify issues are present
    let before_reset = get_fcx_config_issues();
    assert_eq!(before_reset.len(), 1, "Expected 1 issue before reset");

    // Reset clears everything
    let _ = fcx_reset_global_state();

    // Getter must now return empty Vec
    let after_reset = get_fcx_config_issues();
    assert!(
        after_reset.is_empty(),
        "Expected empty Vec after reset, got {} issues",
        after_reset.len()
    );
}

/// Order preservation: Vec returned by getter matches injection order.
#[test]
#[serial_test::serial]
fn test_get_fcx_config_issues_preserves_order() {
    let _ = fcx_reset_global_state();

    {
        let mut handler = GLOBAL_FCX_HANDLER.lock();
        handler.set_detected_issues(vec![
            ConfigIssue::new(
                "first.ini".to_string(),
                None,
                "alpha".to_string(),
                "a".to_string(),
                "b".to_string(),
                "first issue".to_string(),
                "error".to_string(),
            ),
            ConfigIssue::new(
                "second.ini".to_string(),
                None,
                "beta".to_string(),
                "c".to_string(),
                "d".to_string(),
                "second issue".to_string(),
                "warning".to_string(),
            ),
        ]);
    }

    let issues = get_fcx_config_issues();
    assert_eq!(issues.len(), 2);
    assert_eq!(issues[0].file_path, "first.ini");
    assert_eq!(issues[1].file_path, "second.ini");

    let _ = fcx_reset_global_state();
}
