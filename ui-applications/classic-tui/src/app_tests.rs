use super::{App, AsyncMessage, TabIndex};
use crate::widgets::path_input::PathValidationState;
use classic_scanlog_core::CrashLogScanRunStatus;
use classic_scanlog_core::scan_run::contract::{
    Cancellation, Event as ScanRunEvent, LogDisposition, LogEvent, RunResult,
};
use std::path::PathBuf;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

/// Opens a filesystem-backed TUI against one canonical User Settings document.
fn app_with_settings_yaml(yaml: &str) -> (tempfile::TempDir, App) {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(root.path().join("CLASSIC Settings.yaml"), yaml).unwrap();
    let app = App::new_with_settings_root(root.path(), None);
    (root, app)
}

#[test]
fn custom_validation_marks_crash_logs_path_invalid() {
    let mut app = App::new_for_testing();
    let crash_logs = std::env::current_dir()
        .expect("current directory")
        .join("Crash Logs");
    app.custom_scan_input
        .set_value(crash_logs.to_string_lossy().to_string());

    assert_eq!(app.custom_validation_state(), PathValidationState::Invalid);
}

#[test]
fn startup_projects_paths_and_presentation_from_one_canonical_snapshot() {
    let (_root, app) = app_with_settings_yaml(
        r#"schema_version: "1.0"
CLASSIC_Settings:
  MODS Folder Path: 'D:/Mods'
  SCAN Custom Path: 'D:/Crash Logs'
UI:
  tui:
    active_tab: 2
    results_panel_width: 42
    sort_ascending: true
"#,
    );

    assert_eq!(app.staging_mods_input.value, "D:/Mods");
    assert_eq!(app.custom_scan_input.value, "D:/Crash Logs");
    assert_eq!(app.active_tab, TabIndex::Articles);
    assert_eq!(app.results.list_panel_width, 42);
    assert!(app.results.sort_ascending);
}

#[test]
fn explicit_path_save_preserves_unknown_settings_entries() {
    let (root, mut app) = app_with_settings_yaml(
        r#"schema_version: "1.0"
CLASSIC_Settings:
  MODS Folder Path: null
  SCAN Custom Path: null
ThirdPartyPlugin:
  retained: true
"#,
    );
    let mods = root.path().join("mods");
    std::fs::create_dir_all(&mods).unwrap();
    app.staging_mods_input
        .set_value(mods.to_string_lossy().to_string());

    app.save_paths_from_inputs().unwrap();

    let reopened = classic_user_settings_core::UserSettings::open(root.path());
    assert_eq!(
        reopened.game_setup_settings().mods_root(),
        Some(mods.to_string_lossy().as_ref())
    );
    let persisted = std::fs::read_to_string(root.path().join("CLASSIC Settings.yaml")).unwrap();
    assert!(persisted.contains("ThirdPartyPlugin"));
    assert!(persisted.contains("retained: true"));
}

#[test]
fn migration_required_and_invalid_values_use_existing_status_conventions() {
    let (_flat_root, flat) = app_with_settings_yaml("fcx_mode: true\n");
    assert!(flat.scan_status.contains("migration required"));
    assert!(flat.settings_overlay_text().contains("Press M"));

    let (_invalid_root, invalid) = app_with_settings_yaml(
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Max Concurrent Scans: nope\n",
    );
    assert!(
        invalid
            .settings
            .diagnostics()
            .iter()
            .any(|diagnostic| { diagnostic.code() == "invalid_type_max_concurrent_scans" })
    );
}

#[test]
fn legacy_state_is_imported_only_by_the_explicit_settings_action() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        "schema_version: \"1.0\"\nUI:\n  tui:\n    active_tab: 0\n",
    )
    .unwrap();
    let legacy_path = root.path().join("state.json");
    let legacy_bytes = br#"{"active_tab":3,"results_panel_width":42,"sort_ascending":true}"#;
    std::fs::write(&legacy_path, legacy_bytes).unwrap();
    let mut app = App::new_with_settings_root(root.path(), Some(legacy_path.clone()));

    assert_eq!(app.active_tab, TabIndex::MainOptions);
    assert!(app.scan_status.contains("available"));

    app.import_legacy_tui_state();

    assert_eq!(app.active_tab, TabIndex::Results);
    assert_eq!(app.results.list_panel_width, 42);
    assert!(app.results.sort_ascending);
    assert!(app.scan_status.contains("verified backup retained"));
    assert_eq!(std::fs::read(&legacy_path).unwrap(), legacy_bytes);
}

#[test]
fn crash_logs_nesting_check_handles_forward_slash_absolute_paths() {
    let root = tempfile::tempdir().unwrap();
    let app = App::new_with_settings_root(root.path(), None);
    let forward_slash_base = root.path().to_string_lossy().replace('\\', "/");
    let custom_path = PathBuf::from(format!("{forward_slash_base}/Crash Logs/nested"));

    assert!(app.is_inside_crash_logs(&custom_path));
}

#[test]
fn path_validation_and_result_discovery_use_the_apps_canonical_root() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        "schema_version: \"1.0\"\n",
    )
    .unwrap();
    let nested = root.path().join("Crash Logs").join("nested");
    std::fs::create_dir_all(&nested).unwrap();
    std::fs::write(root.path().join("Crash Logs").join("report.md"), "# Report").unwrap();
    let mut app = App::new_with_settings_root(root.path(), None);
    app.custom_scan_input
        .set_value(nested.to_string_lossy().to_string());

    assert_eq!(app.custom_validation_state(), PathValidationState::Invalid);
    app.refresh_results_reports();
    assert_eq!(app.results.reports.len(), 1);
}

#[test]
fn scan_projection_uses_the_managed_game_and_its_formid_database() {
    let (_root, app) = app_with_settings_yaml(
        r#"schema_version: "1.0"
CLASSIC_Settings:
  Managed Game: Skyrim SE
  FormID Databases:
    Fallout4:
      - databases/fallout4.db
    Skyrim:
      - databases/skyrim.db
"#,
    );

    let (game, databases) = app.scan_game_projection();

    assert_eq!(game, classic_shared_core::GameId::Skyrim);
    assert_eq!(databases, vec![PathBuf::from("databases/skyrim.db")]);
}

#[test]
fn scan_projection_reuses_fallout4_formid_databases_for_vr() {
    let (_root, app) = app_with_settings_yaml(
        r#"schema_version: "1.0"
CLASSIC_Settings:
  Managed Game: Fallout 4 VR
  FormID Databases:
    Fallout4:
      - databases/fallout4.db
    Fallout4VR:
      - databases/vr-only.db
"#,
    );

    let (game, databases) = app.scan_game_projection();

    assert_eq!(game, classic_shared_core::GameId::Fallout4VR);
    assert_eq!(databases, vec![PathBuf::from("databases/fallout4.db")]);
}

#[test]
fn scan_complete_with_errors_updates_status_message() {
    let mut app = App::new_for_testing();
    app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(RunResult {
        status: CrashLogScanRunStatus::Completed,
        discovery: None,
        setup: None,
        installed_yaml_data: None,
        effective_concurrency: Some(2),
        message: None,
        total: 3,
        succeeded: 2,
        failed: 1,
        cancelled: 0,
        logs: Vec::new(),
    }))));

    assert_eq!(app.scan_status, "Scanned 3 logs (1 errors, 0 cancelled)");
    assert_eq!(app.scan_progress, 100.0);
    assert!(app.last_scan_run.is_some());
    assert!(app.status_clear_at.is_some());
}

#[test]
fn scan_run_event_updates_progress_from_the_final_contract() {
    let mut app = App::new_for_testing();
    let event = ScanRunEvent::LogFinished {
        log: LogEvent {
            discovery_index: 1,
            crash_log: PathBuf::from("Crash Logs/crash-02.log"),
            completed: 2,
            total: 4,
        },
        disposition: LogDisposition::Succeeded,
    };

    app.handle_async_message(AsyncMessage::ScanEvent(event));

    assert_eq!(app.scan_progress, 50.0);
    assert_eq!(app.scan_status, "50% - Succeeded crash-02.log (2 of 4)");
}

#[test]
fn active_scan_cancellation_uses_the_opaque_contract_control() {
    let mut app = App::new_for_testing();
    let cancellation = Cancellation::new();
    app.scan_in_progress = true;
    app.scan_cancellation = Some(cancellation.clone());

    app.start_or_cancel_crash_scan();

    assert!(cancellation.is_cancelled());
    assert_eq!(
        app.scan_status,
        "Cancellation requested; admitted logs will finish safely..."
    );
}

#[test]
fn crash_scan_saves_edited_paths_before_projecting_settings() {
    let (root, mut app) = app_with_settings_yaml(
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  SCAN Custom Path: null\n",
    );
    let custom_root = tempfile::tempdir_in(std::env::current_dir().unwrap()).unwrap();
    let custom_scan = custom_root.path().join("Edited Custom Scan");
    std::fs::create_dir_all(&custom_scan).unwrap();
    app.custom_scan_input
        .set_value(custom_scan.to_string_lossy().to_string());

    app.start_or_cancel_crash_scan();

    let reopened = classic_user_settings_core::UserSettings::open(root.path());
    assert_eq!(
        reopened.crash_log_scan_settings().custom_scan_input(),
        Some(custom_scan.to_string_lossy().as_ref())
    );
    app.start_or_cancel_crash_scan();
}

#[test]
fn scan_complete_switches_to_results_when_enabled() {
    let (_root, mut app) = app_with_settings_yaml(
        "schema_version: \"1.0\"\nUI:\n  preferences:\n    auto_switch_after_scan: true\n",
    );
    app.active_tab = TabIndex::MainOptions;

    app.handle_async_message(AsyncMessage::ScanFinished(Box::new(Ok(RunResult {
        status: CrashLogScanRunStatus::Completed,
        discovery: None,
        setup: None,
        installed_yaml_data: None,
        effective_concurrency: Some(1),
        message: None,
        total: 1,
        succeeded: 1,
        failed: 0,
        cancelled: 0,
        logs: Vec::new(),
    }))));

    assert!(matches!(app.active_tab, TabIndex::Results));
}

#[test]
fn articles_open_uses_url_opener_abstraction() {
    fn fail_open(_url: &str) -> Result<(), String> {
        Err("blocked".to_string())
    }

    let mut app = App::new_for_testing();
    app.set_url_opener(fail_open);
    app.articles_selected = 0;
    app.open_selected_article();

    assert!(
        app.scan_status
            .contains("Failed to open BUFFOUT 4 INSTALLATION")
    );
}

#[test]
fn results_filter_is_case_insensitive() {
    let mut app = App::new_for_testing();
    app.results.reports = vec![
        super::ReportEntry::new_for_test("Crash-Alpha.md"),
        super::ReportEntry::new_for_test("gamefiles-beta.md"),
    ];
    app.results.search_query = "crash".to_string();

    app.apply_results_filter_sort();

    assert_eq!(app.results.filtered_indices.len(), 1);
    let index = app.results.filtered_indices[0];
    assert_eq!(app.results.reports[index].filename, "Crash-Alpha.md");
}

#[test]
fn results_refresh_preserves_selected_path_when_still_present() {
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let dir = std::env::temp_dir().join(format!("classic-tui-results-preserve-{unique}"));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    let file_a = dir.join("preserve-a.md");
    let file_b = dir.join("preserve-b.md");
    std::fs::write(&file_a, "# A").expect("write a");
    std::fs::write(&file_b, "# B").expect("write b");

    let canonical_dir = dir.to_string_lossy().replace('\\', "/");
    let settings = format!(
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  SCAN Custom Path: '{canonical_dir}'\n"
    );
    let (_root, mut app) = app_with_settings_yaml(&settings);
    app.active_tab = TabIndex::Results;
    app.results.search_query = "preserve-".to_string();
    app.refresh_results_reports_with_status(false);

    let selected = app
        .results
        .filtered_indices
        .iter()
        .enumerate()
        .find(|(_, index)| app.results.reports[**index].filename.contains("preserve-b"))
        .map(|(i, _)| i)
        .expect("selected row");
    app.results_select_filtered_index(selected);
    let selected_path = app
        .results
        .selected_report_path
        .clone()
        .expect("path selected");

    let file_c = dir.join("preserve-c.md");
    std::fs::write(&file_c, "# C").expect("write c");
    app.refresh_results_reports_with_status(false);

    assert_eq!(app.results.selected_report_path, Some(selected_path));
}

#[test]
fn poll_results_refreshes_when_snapshot_changes() {
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let dir = std::env::temp_dir().join(format!("classic-tui-results-poll-{unique}"));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    std::fs::write(dir.join("poll-a.md"), "# A").expect("write a");

    let canonical_dir = dir.to_string_lossy().replace('\\', "/");
    let settings = format!(
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  SCAN Custom Path: '{canonical_dir}'\nUI:\n  preferences:\n    auto_refresh_interval_ms: 1\n"
    );
    let (_root, mut app) = app_with_settings_yaml(&settings);
    app.active_tab = TabIndex::Results;
    app.results.search_query = "poll-".to_string();
    app.refresh_results_reports_with_status(false);
    let before = app.results.filtered_indices.len();

    std::fs::write(dir.join("poll-b.md"), "# B").expect("write b");
    app.results.last_poll_at = Some(Instant::now() - Duration::from_secs(3));
    app.poll_results_if_due();

    let after = app.results.filtered_indices.len();
    assert!(after > before);
}

#[test]
fn update_result_ok_update_available_stores_status_and_formats_message() {
    use classic_update_core::{AppNotificationDisplay, Classification, NotificationStatus};

    let status = NotificationStatus {
        classification: Classification::UpdateAvailable,
        latest_version: "9.2.0".to_string(),
        published_at: "2026-05-01T12:00:00Z".to_string(),
        min_supported_version: None,
        display: Some(AppNotificationDisplay {
            title: "Security hotfix".to_string(),
            body: "Fixes CVE-1234.".to_string(),
            cta_url: Some("https://example.test/releases".to_string()),
        }),
        parse_error: None,
    };

    let mut app = App::new_for_testing();
    app.update_checking = true;
    app.handle_async_message(AsyncMessage::UpdateResult(Ok(status.clone())));

    assert_eq!(
        app.scan_status, "Update available: v9.2.0 — Security hotfix",
        "status bar should carry classification + title"
    );
    assert!(!app.update_checking, "update_checking should be cleared");
    assert_eq!(
        app.last_update_notification,
        Some(status),
        "structured notification should persist on the App",
    );
    assert!(app.status_clear_at.is_some());
}

#[test]
fn update_result_ok_up_to_date_formats_message() {
    use classic_update_core::{Classification, NotificationStatus};

    let status = NotificationStatus {
        classification: Classification::UpToDate,
        latest_version: "9.1.0".to_string(),
        published_at: "2026-03-01T00:00:00Z".to_string(),
        min_supported_version: None,
        display: None,
        parse_error: None,
    };

    let mut app = App::new_for_testing();
    app.handle_async_message(AsyncMessage::UpdateResult(Ok(status)));

    assert_eq!(app.scan_status, "You are up to date");
}

#[test]
fn update_result_ok_not_published_formats_benign_message() {
    use classic_update_core::{Classification, NotificationStatus};

    let status = NotificationStatus {
        classification: Classification::NotPublished,
        latest_version: String::new(),
        published_at: String::new(),
        min_supported_version: None,
        display: None,
        parse_error: None,
    };

    let mut app = App::new_for_testing();
    app.update_checking = true;
    app.handle_async_message(AsyncMessage::UpdateResult(Ok(status.clone())));

    assert_eq!(app.scan_status, "No update information available");
    assert!(!app.scan_status.contains("failed"));
    assert!(!app.update_checking);
    assert_eq!(app.last_update_notification, Some(status));
}

#[test]
fn update_result_err_formats_failure_and_clears_last_notification() {
    let mut app = App::new_for_testing();
    app.handle_async_message(AsyncMessage::UpdateResult(Err(
        "network unreachable".to_string()
    )));

    assert_eq!(
        app.scan_status, "Update check failed: network unreachable",
        "err branch should surface the underlying message"
    );
    assert_eq!(app.last_update_notification, None);
}
