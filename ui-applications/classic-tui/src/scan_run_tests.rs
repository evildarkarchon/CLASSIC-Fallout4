use super::{ScanRunIntent, build_request, format_event, format_result};
use classic_scanlog_core::scan_run::contract::{
    Configuration, Event, LogDisposition, LogEvent, LogFailure, LogFailureStage, LogResult,
    Options, Request, RunResult,
};
use classic_scanlog_core::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanFacts,
    CrashLogScanRejectedInput, CrashLogScanRunStatus, CrashLogScanSetupCheck,
    CrashLogScanSetupResult, ScanProgressPhase, StandardCrashLogScanSource,
    StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
use classic_shared_core::GameId;
use classic_shared_core::get_runtime;
use std::path::PathBuf;

const VALID_CRASH_LOG: &str =
    include_str!("../../../business-logic/classic-scanlog-core/benches/fixtures/crash-0DB9300.log");

fn configuration() -> Configuration {
    Configuration {
        yaml_dir_root: PathBuf::from("C:/CLASSIC"),
        yaml_dir_data: PathBuf::from("C:/CLASSIC/CLASSIC Data"),
        game: GameId::Fallout4,
        game_version: "Regular".to_string(),
        options: Options::new(true, false),
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(4),
    }
}

fn executable_configuration(max_concurrent: usize) -> Configuration {
    let repository_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repository root should resolve");
    Configuration {
        yaml_dir_root: repository_root.clone(),
        yaml_dir_data: repository_root.join("CLASSIC Data"),
        game: GameId::Fallout4,
        game_version: "Original".to_string(),
        options: Options::new(false, false),
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(max_concurrent),
    }
}

#[test]
fn request_projection_preserves_tagged_standard_and_targeted_intent() {
    let standard = build_request(
        configuration(),
        ScanRunIntent::Standard {
            source: StandardCrashLogScanSource {
                base_directory: PathBuf::from("C:/CLASSIC"),
                custom_scan_directory: Some(PathBuf::from("C:/Custom Logs")),
                configured_documents_root: Some(PathBuf::from("C:/Documents")),
            },
            unsolved_logs: StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
        },
        None,
    );

    let Request::Standard(standard) = standard else {
        panic!("Standard TUI intent must produce a tagged Standard request");
    };
    assert!(!standard.fcx_enabled());
    assert_eq!(
        standard.unsolved_logs(),
        &StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault
    );
    assert_eq!(
        standard.source().custom_scan_directory,
        Some(PathBuf::from("C:/Custom Logs"))
    );

    let targeted = build_request(
        configuration(),
        ScanRunIntent::Targeted(TargetedCrashLogScanSource {
            inputs: vec![PathBuf::from("C:/Selected/crash.log")],
        }),
        None,
    );

    let Request::Targeted(targeted) = targeted else {
        panic!("Targeted TUI intent must produce a tagged Targeted request");
    };
    assert!(!targeted.fcx_enabled());
    assert_eq!(
        targeted.source().inputs,
        vec![PathBuf::from("C:/Selected/crash.log")]
    );

    let setup_context = classic_scanlog_core::CrashLogScanSetupContext {
        game_root: Some(PathBuf::from("C:/Games/Fallout 4")),
        docs_root: Some(PathBuf::from("C:/Documents/My Games/Fallout4")),
        game_exe_path: Some(PathBuf::from("C:/Games/Fallout 4/Fallout4.exe")),
        xse_log_path: None,
    };
    let standard_fcx = build_request(
        configuration(),
        ScanRunIntent::Standard {
            source: StandardCrashLogScanSource {
                base_directory: PathBuf::from("C:/CLASSIC"),
                custom_scan_directory: None,
                configured_documents_root: None,
            },
            unsolved_logs: StandardUnsolvedLogsIntent::LeaveInPlace,
        },
        Some(setup_context.clone()),
    );
    let targeted_fcx = build_request(
        configuration(),
        ScanRunIntent::Targeted(TargetedCrashLogScanSource {
            inputs: vec![PathBuf::from("C:/Selected/crash.log")],
        }),
        Some(setup_context),
    );

    assert!(matches!(standard_fcx, Request::Standard(request) if request.fcx_enabled()));
    assert!(matches!(targeted_fcx, Request::Targeted(request) if request.fcx_enabled()));
}

#[test]
fn event_formatter_covers_the_complete_final_contract_stream() {
    let crash_log = PathBuf::from("C:/Crash Logs/crash-01.log");
    let log = |completed| LogEvent {
        discovery_index: 0,
        crash_log: crash_log.clone(),
        completed,
        total: 2,
    };
    let cases = [
        (
            Event::DiscoveryCompleted(CrashLogScanDiscoveryResult {
                source: CrashLogScanDiscoverySource::Targeted,
                accepted_logs: vec![
                    crash_log.clone(),
                    PathBuf::from("C:/Crash Logs/crash-02.log"),
                ],
                rejected_inputs: vec![CrashLogScanRejectedInput {
                    path: PathBuf::from("C:/Selected/readme.txt"),
                    reason: "unsupported file".to_string(),
                }],
                searched_locations: vec![PathBuf::from("C:/Selected")],
            }),
            0.0,
            "Discovered 2 crash logs (1 targeted input rejected)",
        ),
        (
            Event::EffectiveConcurrencySelected {
                effective_concurrency: 2,
            },
            0.0,
            "Selected 2 concurrent scans",
        ),
        (
            Event::LogQueued(log(0)),
            0.0,
            "0% - Queued crash-01.log (1 of 2)",
        ),
        (
            Event::LogStarted(log(0)),
            4.0,
            "4% - Scanning crash-01.log (1 of 2)",
        ),
        (
            Event::LogPhase {
                log: log(0),
                phase: ScanProgressPhase::Analyze,
            },
            41.0,
            "41% - Analyzing crash-01.log (1 of 2)",
        ),
        (
            Event::LogFinished {
                log: log(1),
                disposition: LogDisposition::Succeeded,
            },
            50.0,
            "50% - Succeeded crash-01.log (1 of 2)",
        ),
    ];

    for (event, expected_percent, expected_status) in cases {
        let presentation = format_event(&event);
        assert_eq!(presentation.percent, expected_percent);
        assert_eq!(presentation.status, expected_status);
    }
}

fn log_result(index: usize, name: &str, disposition: LogDisposition) -> LogResult {
    LogResult {
        discovery_index: index,
        crash_log: PathBuf::from(format!("C:/Crash Logs/{name}")),
        autoscan_report: (disposition == LogDisposition::Succeeded)
            .then(|| PathBuf::from(format!("C:/Crash Logs/{name}-AUTOSCAN.md"))),
        disposition,
        failures: Vec::new(),
        message: None,
        moved_to_unsolved_logs: false,
        processing_time_us: 1_000,
        processing_time_ms: 1,
        formid_count: 1,
        plugin_count: 2,
        suspect_count: 3,
    }
}

#[test]
fn terminal_presentation_distinguishes_cancellation_around_discovery_and_admission() {
    let before = RunResult {
        status: CrashLogScanRunStatus::CancelledBeforeDiscovery,
        discovery: None,
        setup: None,
        effective_concurrency: None,
        message: None,
        total: 0,
        succeeded: 0,
        failed: 0,
        cancelled: 0,
        logs: Vec::new(),
    };

    let before_presentation = format_result(&before);
    assert_eq!(
        before_presentation.status,
        "Scan cancelled safely before discovery completed"
    );
    assert_eq!(before_presentation.percent, 0.0);
    assert!(!before_presentation.details.contains("Discovery:"));

    let admitted = log_result(0, "admitted.log", LogDisposition::Succeeded);
    let not_started = log_result(1, "queued.log", LogDisposition::CancelledBeforeStart);
    let after = RunResult {
        status: CrashLogScanRunStatus::Cancelled,
        discovery: Some(CrashLogScanDiscoveryResult {
            source: CrashLogScanDiscoverySource::Standard,
            accepted_logs: vec![admitted.crash_log.clone(), not_started.crash_log.clone()],
            rejected_inputs: Vec::new(),
            searched_locations: vec![PathBuf::from("C:/Crash Logs")],
        }),
        setup: Some(CrashLogScanSetupResult {
            status: "ready".to_string(),
            checks: vec![CrashLogScanSetupCheck {
                kind: "game_root".to_string(),
                state: "passed".to_string(),
                message: "Game root is valid".to_string(),
                details: Vec::new(),
            }],
            path_updates: Vec::new(),
            configuration_issues: Vec::new(),
            actions: Vec::new(),
            fatal_errors: Vec::new(),
            message: None,
            rendered_report: String::new(),
        }),
        effective_concurrency: Some(1),
        message: None,
        total: 2,
        succeeded: 1,
        failed: 0,
        cancelled: 1,
        logs: vec![admitted, not_started],
    };

    let after_presentation = format_result(&after);
    assert_eq!(
        after_presentation.status,
        "Cancelled (1 of 2 logs completed; 1 not started)"
    );
    assert_eq!(after_presentation.percent, 50.0);
    assert!(
        after_presentation
            .details
            .contains("Discovery: standard; 2 accepted; 0 rejected; 1 searched")
    );
    assert!(
        after_presentation
            .details
            .contains("Effective concurrency: 1")
    );
    assert!(after_presentation.details.contains("Setup: ready"));
    assert!(
        after_presentation
            .details
            .contains("1. admitted.log - succeeded")
    );
    assert!(
        after_presentation
            .details
            .contains("report: C:/Crash Logs/admitted.log-AUTOSCAN.md")
    );
    assert!(
        after_presentation
            .details
            .contains("2. queued.log - cancelled before start")
    );
}

#[test]
fn terminal_presentation_lists_mixed_outcomes_in_discovery_order() {
    let succeeded = log_result(0, "first.log", LogDisposition::Succeeded);
    let mut failed = log_result(1, "second.log", LogDisposition::Failed);
    failed.failures = vec![
        LogFailure {
            stage: LogFailureStage::Analysis,
            message: "analysis failed".to_string(),
        },
        LogFailure {
            stage: LogFailureStage::ReportWrite,
            message: "report write failed".to_string(),
        },
    ];
    let cancelled = log_result(2, "third.log", LogDisposition::CancelledBeforeStart);
    let result = RunResult {
        status: CrashLogScanRunStatus::Completed,
        discovery: Some(CrashLogScanDiscoveryResult {
            source: CrashLogScanDiscoverySource::Targeted,
            accepted_logs: vec![
                succeeded.crash_log.clone(),
                failed.crash_log.clone(),
                cancelled.crash_log.clone(),
            ],
            rejected_inputs: vec![CrashLogScanRejectedInput {
                path: PathBuf::from("C:/Selected/not-a-log.txt"),
                reason: "unsupported file".to_string(),
            }],
            searched_locations: vec![PathBuf::from("C:/Selected")],
        }),
        setup: None,
        effective_concurrency: Some(2),
        message: None,
        total: 3,
        succeeded: 1,
        failed: 1,
        cancelled: 1,
        logs: vec![succeeded, failed, cancelled],
    };

    let presentation = format_result(&result);
    let first = presentation
        .details
        .find("1. first.log - succeeded")
        .unwrap();
    let second = presentation.details.find("2. second.log - failed").unwrap();
    let third = presentation
        .details
        .find("3. third.log - cancelled before start")
        .unwrap();

    assert!(first < second && second < third);
    assert!(presentation.details.contains("analysis: analysis failed"));
    assert!(
        presentation
            .details
            .contains("report write: report write failed")
    );
    assert!(
        presentation
            .details
            .contains("Rejected: C:/Selected/not-a-log.txt (unsupported file)")
    );
}

#[test]
fn public_contract_cancellation_before_and_after_discovery_flows_through_tui_projection() {
    let temp = tempfile::tempdir().expect("tempdir should succeed");
    let target = temp.path().join("crash-selected.log");
    std::fs::write(&target, VALID_CRASH_LOG).expect("fixture log should be written");

    let before_cancellation = classic_scanlog_core::scan_run::contract::Cancellation::new();
    before_cancellation.cancel();
    let before_request = build_request(
        executable_configuration(1),
        ScanRunIntent::Targeted(TargetedCrashLogScanSource {
            inputs: vec![target.clone()],
        }),
        None,
    );
    let before = get_runtime()
        .block_on(classic_scanlog_core::scan_run::contract::execute(
            before_request,
            &before_cancellation,
            None,
        ))
        .expect("pre-discovery cancellation should be expected result data");

    assert_eq!(
        before.status,
        CrashLogScanRunStatus::CancelledBeforeDiscovery
    );
    assert!(before.discovery.is_none());
    assert!(!format_result(&before).details.contains("Discovery:"));

    let after_cancellation = classic_scanlog_core::scan_run::contract::Cancellation::new();
    let observer_cancellation = after_cancellation.clone();
    let after_request = build_request(
        executable_configuration(1),
        ScanRunIntent::Targeted(TargetedCrashLogScanSource {
            inputs: vec![target.clone()],
        }),
        None,
    );
    let mut event_statuses = Vec::new();
    let after = {
        let mut observer = |event| {
            event_statuses.push(format_event(&event).status);
            if matches!(event, Event::DiscoveryCompleted(_)) {
                observer_cancellation.cancel();
            }
        };
        get_runtime()
            .block_on(classic_scanlog_core::scan_run::contract::execute(
                after_request,
                &after_cancellation,
                Some(&mut observer),
            ))
            .expect("post-discovery cancellation should be expected result data")
    };

    assert_eq!(after.status, CrashLogScanRunStatus::Cancelled);
    assert_eq!(
        after
            .discovery
            .as_ref()
            .expect("discovery should be retained")
            .accepted_logs,
        vec![target]
    );
    assert!(after.effective_concurrency.is_none());
    assert_eq!(after.cancelled, 1);
    assert_eq!(
        after.logs[0].disposition,
        LogDisposition::CancelledBeforeStart
    );
    assert!(
        event_statuses
            .iter()
            .any(|status| status.starts_with("Discovered 1 crash log"))
    );
}

#[test]
fn public_contract_cancellation_after_admission_retains_durable_tui_outcomes() {
    let temp = tempfile::tempdir().expect("tempdir should succeed");
    let first = temp.path().join("crash-admitted.log");
    let second = temp.path().join("crash-queued.log");
    std::fs::write(&first, VALID_CRASH_LOG).expect("first fixture log should be written");
    std::fs::write(&second, VALID_CRASH_LOG).expect("second fixture log should be written");
    let request = build_request(
        executable_configuration(1),
        ScanRunIntent::Targeted(TargetedCrashLogScanSource {
            inputs: vec![first, second],
        }),
        None,
    );
    let cancellation = classic_scanlog_core::scan_run::contract::Cancellation::new();
    let observer_cancellation = cancellation.clone();
    let mut event_statuses = Vec::new();
    let result = {
        let mut observer = |event| {
            event_statuses.push(format_event(&event).status);
            if matches!(event, Event::LogStarted(_)) {
                observer_cancellation.cancel();
            }
        };
        get_runtime()
            .block_on(classic_scanlog_core::scan_run::contract::execute(
                request,
                &cancellation,
                Some(&mut observer),
            ))
            .expect("admitted cancellation should be expected result data")
    };

    assert_eq!(result.status, CrashLogScanRunStatus::Cancelled);
    assert_eq!(result.succeeded, 1);
    assert_eq!(result.cancelled, 1);
    assert_eq!(result.logs[0].disposition, LogDisposition::Succeeded);
    assert!(
        result.logs[0]
            .autoscan_report
            .as_ref()
            .is_some_and(|report| report.exists()),
        "the admitted log must finish durable report persistence"
    );
    assert_eq!(
        result.logs[1].disposition,
        LogDisposition::CancelledBeforeStart
    );
    assert!(
        event_statuses
            .iter()
            .any(|status| status.contains("Succeeded crash-admitted.log"))
    );
    let details = format_result(&result).details;
    assert!(details.contains("1. crash-admitted.log - succeeded"));
    assert!(details.contains("2. crash-queued.log - cancelled before start"));
}
