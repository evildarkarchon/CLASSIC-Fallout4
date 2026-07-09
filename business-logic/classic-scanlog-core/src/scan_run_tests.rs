use super::*;
use crate::{AnalysisConfig, FormIdReadiness, SHORT_SCAN_CACHE_PROFILE};
use classic_shared_core::get_runtime;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use tempfile::tempdir;

const FIXTURE_LOG_SMALL: &str = include_str!("../benches/fixtures/crash-0DB9300.log");

fn make_ready_analysis() -> ScanReadyAnalysis {
    make_ready_analysis_with(None, None)
}

fn make_ready_analysis_with(
    paths: Option<crate::CrashLogScanIntakePaths>,
    unsolved_logs_destination: Option<std::path::PathBuf>,
) -> ScanReadyAnalysis {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    config.crashgen_latest = "1.26.2".to_string();
    config.game_version = "1.10.163".to_string();
    config.game_version_vr = "1.2.72".to_string();
    config.xse_acronym = "F4SE".to_string();

    ScanReadyAnalysis::new(
        config,
        FormIdReadiness {
            enabled: false,
            database_paths: Vec::new(),
        },
        SHORT_SCAN_CACHE_PROFILE,
        paths,
        unsolved_logs_destination,
    )
}

fn write_fixture_log(temp: &tempfile::TempDir, filename: &str) -> std::path::PathBuf {
    let log_path = temp.path().join(filename);
    std::fs::write(&log_path, FIXTURE_LOG_SMALL).expect("fixture log should be written");
    log_path
}

fn standard_request(
    log_path: std::path::PathBuf,
    unsolved_logs: StandardUnsolvedLogsIntent,
) -> CrashLogScanRunRequest {
    CrashLogScanRunRequest {
        logs: vec![log_path],
        intent: CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent { unsolved_logs }),
        max_concurrent: Some(1),
        cancellation: None,
        preserve_order: true,
    }
}

#[test]
fn standard_scan_run_writes_autoscan_report() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-success.log");
    let run = CrashLogScanRun::new(make_ready_analysis());
    let mut events = Vec::new();

    let result = get_runtime()
        .block_on(run.run(
            standard_request(log_path.clone(), StandardUnsolvedLogsIntent::LeaveInPlace),
            |event| {
                events.push(event);
            },
        ))
        .expect("scan run should succeed");

    let autoscan_path = temp.path().join("crash-success-AUTOSCAN.md");
    assert_eq!(result.total, 1);
    assert_eq!(result.succeeded, 1);
    assert_eq!(result.failed, 0);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Succeeded);
    assert!(!result.logs[0].report_write_failed);
    assert_eq!(result.logs[0].autoscan_report, Some(autoscan_path.clone()));
    assert!(autoscan_path.exists());
    assert!(
        events
            .iter()
            .any(|event| event.kind == CrashLogScanRunEventKind::Completed)
    );
}

#[test]
fn standard_scan_run_leave_in_place_does_not_move_failed_log() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-leave-fail.log");
    let autoscan_path = temp.path().join("crash-leave-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            standard_request(log_path.clone(), StandardUnsolvedLogsIntent::LeaveInPlace),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(result.logs[0].report_write_failed);
    assert!(!result.logs[0].moved_to_unsolved_logs);
    assert!(log_path.exists());
}

#[test]
fn standard_scan_run_configured_or_default_uses_canonical_destination_from_intake_paths() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-canonical-fail.log");
    let autoscan_path = temp.path().join("crash-canonical-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let unsolved_dir = temp.path().join("CLASSIC Backup").join("Unsolved Logs");
    let paths = crate::CrashLogScanIntakePaths::new(temp.path(), temp.path().join("CLASSIC Data"));
    let run = CrashLogScanRun::new(make_ready_analysis_with(Some(paths), None));

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
            ),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(result.logs[0].moved_to_unsolved_logs);
    assert!(!log_path.exists());
    assert!(unsolved_dir.join("crash-canonical-fail.log").exists());
}

#[test]
fn standard_scan_run_configured_or_default_uses_configured_destination() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-configured-fail.log");
    let autoscan_path = temp.path().join("crash-configured-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let configured_dir = temp.path().join("user-selected-unsolved");
    let paths = crate::CrashLogScanIntakePaths::new(temp.path(), temp.path().join("CLASSIC Data"));
    let run = CrashLogScanRun::new(make_ready_analysis_with(
        Some(paths),
        Some(configured_dir.clone()),
    ));

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
            ),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.failed, 1);
    assert!(result.logs[0].moved_to_unsolved_logs);
    assert!(!log_path.exists());
    assert!(configured_dir.join("crash-configured-fail.log").exists());
}

#[test]
fn standard_scan_run_configured_or_default_without_destination_source_fails_setup() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-no-destination-source.log");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let error = match get_runtime().block_on(run.run(
        standard_request(
            log_path.clone(),
            StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
        ),
        |_| {},
    )) {
        Ok(_) => panic!("missing destination source should fail setup"),
        Err(error) => error,
    };

    assert!(matches!(error, ScanLogError::InvalidInput(_)));
    assert!(log_path.exists());
}

#[test]
fn standard_scan_run_relative_custom_destination_fails_setup() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-relative-destination.log");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let error = match get_runtime().block_on(run.run(
        standard_request(
            log_path.clone(),
            StandardUnsolvedLogsIntent::MoveToCustom(std::path::PathBuf::from("relative")),
        ),
        |_| {},
    )) {
        Ok(_) => panic!("relative custom destination should fail setup"),
        Err(error) => error,
    };

    assert!(matches!(error, ScanLogError::InvalidInput(_)));
    assert!(log_path.exists());
}

#[test]
fn standard_scan_run_custom_destination_moves_failed_log_to_unsolved_logs() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-write-fail.log");
    let autoscan_path = temp.path().join("crash-write-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let unsolved_dir = temp.path().join("custom-unsolved");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToCustom(unsolved_dir.clone()),
            ),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(result.logs[0].moved_to_unsolved_logs);
    assert!(!log_path.exists());
    assert!(unsolved_dir.join("crash-write-fail.log").exists());
}

#[test]
fn standard_scan_run_unwritable_custom_destination_remains_per_log_failure() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-unwritable-fail.log");
    let autoscan_path = temp.path().join("crash-unwritable-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let blocked_destination = temp.path().join("blocked-destination");
    std::fs::write(&blocked_destination, "not a directory")
        .expect("destination blocker should be written");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToCustom(blocked_destination.clone()),
            ),
            |_| {},
        ))
        .expect("unwritable destination should be a per-log failure");

    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(!result.logs[0].moved_to_unsolved_logs);
    assert!(result.logs[0].error.is_some());
    assert!(log_path.exists());
    assert!(blocked_destination.is_file());
}

#[test]
fn standard_scan_run_preserves_existing_unsolved_log() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-overwrite-fail.log");
    let autoscan_path = temp.path().join("crash-overwrite-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let unsolved_dir = temp.path().join("custom-unsolved");
    std::fs::create_dir_all(&unsolved_dir).expect("unsolved directory should be created");
    let unsolved_log_path = unsolved_dir.join("crash-overwrite-fail.log");
    std::fs::write(&unsolved_log_path, "stale unsolved log")
        .expect("stale unsolved log should be written");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            standard_request(
                log_path.clone(),
                StandardUnsolvedLogsIntent::MoveToCustom(unsolved_dir.clone()),
            ),
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(result.logs[0].moved_to_unsolved_logs);
    assert!(!log_path.exists());
    assert_eq!(
        std::fs::read_to_string(&unsolved_log_path).expect("stale log should be readable"),
        "stale unsolved log"
    );
    assert_eq!(
        std::fs::read_to_string(unsolved_dir.join("crash-overwrite-fail-1.log"))
            .expect("moved log should be readable"),
        FIXTURE_LOG_SMALL
    );
}

#[test]
fn move_unsolved_artifacts_preserves_existing_log_and_report_destinations() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = temp.path().join("crash-overwrite-artifacts.log");
    let report_path = temp.path().join("crash-overwrite-artifacts-AUTOSCAN.md");
    let unsolved_dir = temp.path().join("custom-unsolved");
    std::fs::create_dir_all(&unsolved_dir).expect("unsolved directory should be created");
    let unsolved_log_path = unsolved_dir.join("crash-overwrite-artifacts.log");
    let unsolved_report_path = unsolved_dir.join("crash-overwrite-artifacts-AUTOSCAN.md");
    std::fs::write(&log_path, "new log contents").expect("source log should be written");
    std::fs::write(&report_path, "new report contents").expect("source report should be written");
    std::fs::write(&unsolved_log_path, "stale log contents").expect("stale log should be written");
    std::fs::write(&unsolved_report_path, "stale report contents")
        .expect("stale report should be written");

    let moved = get_runtime()
        .block_on(move_unsolved_artifacts(&log_path, &unsolved_dir))
        .expect("artifacts should move to unique destinations");

    assert!(moved);
    assert!(!log_path.exists());
    assert!(!report_path.exists());
    assert_eq!(
        std::fs::read_to_string(&unsolved_log_path).expect("stale log should be readable"),
        "stale log contents"
    );
    assert_eq!(
        std::fs::read_to_string(&unsolved_report_path).expect("stale report should be readable"),
        "stale report contents"
    );
    assert_eq!(
        std::fs::read_to_string(unsolved_dir.join("crash-overwrite-artifacts-1.log"))
            .expect("moved log should be readable"),
        "new log contents"
    );
    assert_eq!(
        std::fs::read_to_string(unsolved_dir.join("crash-overwrite-artifacts-AUTOSCAN-1.md"))
            .expect("moved report should be readable"),
        "new report contents"
    );
}

#[test]
fn targeted_scan_run_does_not_move_failed_log_to_unsolved_logs() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-targeted-fail.log");
    let autoscan_path = temp.path().join("crash-targeted-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let unsolved_dir = temp.path().join("CLASSIC Backup").join("Unsolved Logs");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            CrashLogScanRunRequest {
                logs: vec![log_path.clone()],
                intent: CrashLogScanRunIntent::Targeted,
                max_concurrent: Some(1),
                cancellation: None,
                preserve_order: true,
            },
            |_| {},
        ))
        .expect("scan run should return per-log failure");

    assert_eq!(result.failed, 1);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Failed);
    assert!(!result.logs[0].moved_to_unsolved_logs);
    assert!(log_path.exists());
    assert!(!unsolved_dir.exists());
}

#[test]
fn cancellation_before_start_is_counted_separately() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-cancelled.log");
    let cancellation = Arc::new(AtomicBool::new(true));
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            CrashLogScanRunRequest {
                logs: vec![log_path],
                intent: CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
                    unsolved_logs: StandardUnsolvedLogsIntent::LeaveInPlace,
                }),
                max_concurrent: Some(1),
                cancellation: Some(Arc::clone(&cancellation)),
                preserve_order: true,
            },
            |_| {},
        ))
        .expect("scan run should complete with cancellation outcome");

    assert!(cancellation.load(Ordering::Relaxed));
    assert_eq!(result.succeeded, 0);
    assert_eq!(result.failed, 0);
    assert_eq!(result.cancelled, 1);
    assert_eq!(
        result.logs[0].outcome,
        CrashLogScanOutcome::CancelledBeforeStart
    );
}
