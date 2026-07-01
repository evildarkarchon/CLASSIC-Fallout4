use super::{App, AsyncMessage, TabIndex};
use crate::widgets::path_input::PathValidationState;
use std::path::PathBuf;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

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
fn crash_logs_nesting_check_handles_forward_slash_absolute_paths() {
    let app = App::new_for_testing();
    let current_dir = std::env::current_dir().expect("current directory");
    let forward_slash_base = current_dir.to_string_lossy().replace('\\', "/");
    let custom_path = PathBuf::from(format!("{forward_slash_base}/Crash Logs/nested"));

    assert!(app.is_inside_crash_logs(&custom_path));
}

#[test]
fn scan_complete_with_errors_updates_status_message() {
    let mut app = App::new_for_testing();
    app.handle_async_message(AsyncMessage::ScanComplete {
        processed: 3,
        total: 3,
        errors: 1,
        cancelled: false,
    });

    assert_eq!(app.scan_status, "Scanned 3 logs (1 errors)");
    assert_eq!(app.scan_progress, 100.0);
    assert!(app.status_clear_at.is_some());
}

#[test]
fn scan_complete_switches_to_results_when_enabled() {
    let mut app = App::new_for_testing();
    app.config.auto_switch_to_results = true;
    app.active_tab = TabIndex::MainOptions;

    app.handle_async_message(AsyncMessage::ScanComplete {
        processed: 1,
        total: 1,
        errors: 0,
        cancelled: false,
    });

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

    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Results;
    app.config.paths.scan_custom = Some(dir.clone());
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

    let mut app = App::new_for_testing();
    app.active_tab = TabIndex::Results;
    app.config.paths.scan_custom = Some(dir.clone());
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
fn resolve_xse_folder_uses_docs_root_for_fo4() {
    let mut app = App::new_for_testing();
    app.config.paths.docs_root = Some(PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4"));
    app.config.game_version = "auto".to_string();

    let folder = super::resolve_xse_folder_for_scan(
        "CLASSIC Data",
        "Fallout4",
        &app.config.game_version,
        app.config.paths.docs_root.as_deref(),
    )
    .expect("expected xse folder");
    assert_eq!(
        folder,
        PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4\F4SE")
    );
}

#[test]
fn resolve_xse_folder_uses_docs_root_for_fo4_vr() {
    let mut app = App::new_for_testing();
    app.config.paths.docs_root = Some(PathBuf::from(
        r"C:\Users\Test\Documents\My Games\Fallout4VR",
    ));
    app.config.game_version = "VR".to_string();

    let folder = super::resolve_xse_folder_for_scan(
        "CLASSIC Data",
        "Fallout4",
        &app.config.game_version,
        app.config.paths.docs_root.as_deref(),
    )
    .expect("expected xse folder");
    assert_eq!(
        folder,
        PathBuf::from(r"C:\Users\Test\Documents\My Games\Fallout4VR\F4SE")
    );
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
