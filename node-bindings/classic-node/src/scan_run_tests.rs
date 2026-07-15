use super::*;
use classic_scanlog_core::scan_run::contract::{
    InfrastructureError, InfrastructureErrorStage, LogDisposition, LogEvent, LogFailure,
    LogFailureStage, LogResult, RunResult,
};
use classic_scanlog_core::{CrashLogScanRejectedInput, CrashLogScanRunStatus};

fn log_event() -> LogEvent {
    LogEvent {
        discovery_index: 7,
        crash_log: PathBuf::from("C:/logs/crash.log"),
        completed: 2,
        total: 4,
    }
}

#[test]
fn event_mapping_covers_every_variant_and_phase() {
    let discovery = CrashLogScanDiscoveryResult {
        source: CrashLogScanDiscoverySource::Targeted,
        accepted_logs: vec![PathBuf::from("C:/logs/crash.log")],
        rejected_inputs: vec![CrashLogScanRejectedInput {
            path: PathBuf::from("C:/logs/missing.log"),
            reason: "missing".to_string(),
        }],
        searched_locations: vec![PathBuf::from("C:/logs")],
    };
    let mapped_discovery = event_to_js(contract::Event::DiscoveryCompleted(discovery));
    assert_eq!(mapped_discovery.kind, "discovery_completed");
    let discovery = mapped_discovery.discovery.expect("discovery payload");
    assert_eq!(discovery.source, "targeted");
    assert_eq!(discovery.accepted_logs, ["C:/logs/crash.log"]);
    assert_eq!(discovery.rejected_inputs[0].reason, "missing");
    assert_eq!(discovery.searched_locations, ["C:/logs"]);

    let concurrency = event_to_js(contract::Event::EffectiveConcurrencySelected {
        effective_concurrency: 3,
    });
    assert_eq!(concurrency.kind, "effective_concurrency_selected");
    assert_eq!(concurrency.effective_concurrency, Some(3));

    let queued = event_to_js(contract::Event::LogQueued(log_event()));
    assert_eq!(queued.kind, "log_queued");
    let queued_log = queued.log.expect("queued log payload");
    assert_eq!(queued_log.discovery_index, 7);
    assert_eq!(queued_log.completed, 2);
    assert_eq!(queued_log.total, 4);

    assert_eq!(
        event_to_js(contract::Event::LogStarted(log_event())).kind,
        "log_started"
    );
    for (phase, expected) in [
        (ScanProgressPhase::Setup, "setup"),
        (ScanProgressPhase::Parse, "parse"),
        (ScanProgressPhase::Analyze, "analyze"),
        (ScanProgressPhase::Finalize, "finalize"),
    ] {
        let mapped = event_to_js(contract::Event::LogPhase {
            log: log_event(),
            phase,
        });
        assert_eq!(mapped.kind, "log_phase");
        assert_eq!(mapped.phase.as_deref(), Some(expected));
    }

    for (disposition, expected) in [
        (LogDisposition::Succeeded, "succeeded"),
        (LogDisposition::Failed, "failed"),
        (
            LogDisposition::CancelledBeforeStart,
            "cancelled_before_start",
        ),
    ] {
        let mapped = event_to_js(contract::Event::LogFinished {
            log: log_event(),
            disposition,
        });
        assert_eq!(mapped.kind, "log_finished");
        assert_eq!(mapped.disposition.as_deref(), Some(expected));
    }
}

#[test]
fn terminal_mapping_preserves_every_status_failure_and_optional_path() {
    for (status, expected) in [
        (CrashLogScanRunStatus::Completed, "completed"),
        (
            CrashLogScanRunStatus::NoCrashLogsFound,
            "no_crash_logs_found",
        ),
        (CrashLogScanRunStatus::SetupFailed, "setup_failed"),
        (
            CrashLogScanRunStatus::CancelledBeforeDiscovery,
            "cancelled_before_discovery",
        ),
        (CrashLogScanRunStatus::Cancelled, "cancelled"),
    ] {
        let mapped = run_result_to_js(RunResult {
            status,
            discovery: None,
            setup: None,
            effective_concurrency: Some(2),
            message: Some("terminal message".to_string()),
            total: 1,
            succeeded: 0,
            failed: 1,
            cancelled: 0,
            logs: vec![],
        });
        assert_eq!(mapped.status, expected);
        assert_eq!(mapped.effective_concurrency, Some(2));
        assert_eq!(mapped.message.as_deref(), Some("terminal message"));
    }

    let mapped_log = log_result_to_js(LogResult {
        discovery_index: 1,
        crash_log: PathBuf::from("C:/logs/crash.log"),
        autoscan_report: Some(PathBuf::from("C:/logs/crash-AUTOSCAN.md")),
        disposition: LogDisposition::Failed,
        failures: vec![
            LogFailure {
                stage: LogFailureStage::Analysis,
                message: "analysis".to_string(),
            },
            LogFailure {
                stage: LogFailureStage::ReportWrite,
                message: "report".to_string(),
            },
            LogFailure {
                stage: LogFailureStage::UnsolvedLogsFinalization,
                message: "finalization".to_string(),
            },
        ],
        message: Some("all failures".to_string()),
        moved_to_unsolved_logs: true,
        processing_time_us: u64::MAX,
        processing_time_ms: 4,
        formid_count: 5,
        plugin_count: 6,
        suspect_count: 7,
    });
    assert_eq!(mapped_log.disposition, "failed");
    assert_eq!(
        mapped_log
            .failures
            .iter()
            .map(|failure| failure.stage.as_str())
            .collect::<Vec<_>>(),
        ["analysis", "report_write", "unsolved_logs_finalization"]
    );
    assert_eq!(mapped_log.processing_time_us, i64::MAX);
    assert_eq!(
        mapped_log.autoscan_report.as_deref(),
        Some("C:/logs/crash-AUTOSCAN.md")
    );
}

#[test]
fn infrastructure_mapping_covers_every_stage_with_and_without_paths() {
    for (stage, expected) in [
        (
            InfrastructureErrorStage::RequestValidation,
            "request_validation",
        ),
        (InfrastructureErrorStage::Discovery, "discovery"),
        (InfrastructureErrorStage::Intake, "intake"),
        (
            InfrastructureErrorStage::FormIdDatabaseAccess,
            "formid_database_access",
        ),
        (InfrastructureErrorStage::Initialization, "initialization"),
        (
            InfrastructureErrorStage::InternalInvariant,
            "internal_invariant",
        ),
    ] {
        let mapped = infrastructure_error_to_js(InfrastructureError {
            stage,
            message: "failure".to_string(),
            path: Some(PathBuf::from("C:/failure/path")),
        });
        assert_eq!(mapped.stage, expected);
        assert_eq!(mapped.message, "failure");
        assert_eq!(mapped.path.as_deref(), Some("C:/failure/path"));
    }

    let mapped = infrastructure_error_to_js(InfrastructureError {
        stage: InfrastructureErrorStage::Discovery,
        message: "failure".to_string(),
        path: None,
    });
    assert!(mapped.path.is_none());
}
