use super::*;
use crate::{AnalysisConfig, FormIdReadiness, SHORT_SCAN_CACHE_PROFILE};
use classic_shared_core::get_runtime;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use tempfile::tempdir;

const FIXTURE_LOG_SMALL: &str = include_str!("../benches/fixtures/crash-0DB9300.log");

fn make_ready_analysis() -> ScanReadyAnalysis {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    config.crashgen_latest = "1.26.2".to_string();
    config.game_version = "1.10.163".to_string();
    config.game_version_vr = "1.2.72".to_string();
    config.xse_acronym = "F4SE".to_string();

    ScanReadyAnalysis {
        analysis_config: config,
        formid_readiness: FormIdReadiness {
            enabled: false,
            database_paths: Vec::new(),
        },
        cache_profile: SHORT_SCAN_CACHE_PROFILE,
    }
}

fn write_fixture_log(temp: &tempfile::TempDir, filename: &str) -> std::path::PathBuf {
    let log_path = temp.path().join(filename);
    std::fs::write(&log_path, FIXTURE_LOG_SMALL).expect("fixture log should be written");
    log_path
}

fn standard_request(
    log_path: std::path::PathBuf,
    unsolved_dir: std::path::PathBuf,
) -> CrashLogScanRunRequest {
    CrashLogScanRunRequest {
        logs: vec![log_path],
        mode: CrashLogScanRunMode::Standard(StandardCrashLogScanRunOptions {
            unsolved_logs: UnsolvedLogsPolicy::MoveTo {
                directory: unsolved_dir,
            },
        }),
        max_concurrent: Some(1),
        cancellation: None,
        preserve_order: true,
    }
}

#[test]
fn standard_scan_run_writes_autoscan_report() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-success.log");
    let unsolved_dir = temp.path().join("CLASSIC Backup").join("Unsolved Logs");
    let run = CrashLogScanRun::new(make_ready_analysis());
    let mut events = Vec::new();

    let result = get_runtime()
        .block_on(
            run.run(standard_request(log_path.clone(), unsolved_dir), |event| {
                events.push(event);
            }),
        )
        .expect("scan run should succeed");

    let autoscan_path = temp.path().join("crash-success-AUTOSCAN.md");
    assert_eq!(result.total, 1);
    assert_eq!(result.succeeded, 1);
    assert_eq!(result.failed, 0);
    assert_eq!(result.logs[0].outcome, CrashLogScanOutcome::Succeeded);
    assert_eq!(result.logs[0].autoscan_report, Some(autoscan_path.clone()));
    assert!(autoscan_path.exists());
    assert!(
        events
            .iter()
            .any(|event| event.kind == CrashLogScanRunEventKind::Completed)
    );
}

#[test]
fn standard_scan_run_moves_failed_log_to_unsolved_logs() {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = write_fixture_log(&temp, "crash-write-fail.log");
    let autoscan_path = temp.path().join("crash-write-fail-AUTOSCAN.md");
    std::fs::create_dir(&autoscan_path).expect("directory should block report write");
    let unsolved_dir = temp.path().join("CLASSIC Backup").join("Unsolved Logs");
    let run = CrashLogScanRun::new(make_ready_analysis());

    let result = get_runtime()
        .block_on(run.run(
            standard_request(log_path.clone(), unsolved_dir.clone()),
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
                mode: CrashLogScanRunMode::Targeted,
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
                mode: CrashLogScanRunMode::Standard(StandardCrashLogScanRunOptions {
                    unsolved_logs: UnsolvedLogsPolicy::LeaveInPlace,
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
