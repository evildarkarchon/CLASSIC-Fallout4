use super::*;
use classic_scanlog_core::scan_run::contract::{
    InfrastructureError, InfrastructureErrorStage, LogDisposition, LogEvent, LogFailure,
    LogFailureStage, LogResult, RunResult,
};
use classic_scanlog_core::{CrashLogScanRejectedInput, CrashLogScanRunStatus};

const SHARED_SCAN_RUN_MANIFEST: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/crash_log_scan_run/manifest.json"
));

/// Loads the language-neutral structured-failure corpus for Node mapping tests.
fn shared_failure_fixtures() -> serde_json::Value {
    serde_json::from_str::<serde_json::Value>(SHARED_SCAN_RUN_MANIFEST)
        .expect("shared scan-run manifest should deserialize")["failureFixtures"]
        .clone()
}

fn log_event() -> LogEvent {
    LogEvent {
        discovery_index: 7,
        crash_log: PathBuf::from("C:/logs/crash.log"),
        completed: 2,
        total: 4,
    }
}

#[test]
fn request_conversion_treats_blank_optional_paths_as_absent() {
    let configuration = configuration_to_core(JsScanRunConfiguration {
        yaml_dir_root: "C:/CLASSIC".to_string(),
        yaml_dir_data: "C:/CLASSIC/CLASSIC Data".to_string(),
        game: "Fallout4".to_string(),
        game_version: "auto".to_string(),
        show_formid_values: false,
        simplify_logs: false,
        formid_database_paths: Vec::new(),
        unsolved_logs_destination: Some(" \t ".to_string()),
        max_concurrent: None,
    })
    .expect("configuration should convert");
    assert!(configuration.scan_facts.unsolved_logs_destination.is_none());

    let source = standard_source_to_core(JsScanRunStandardSource {
        base_directory: "C:/CLASSIC".to_string(),
        custom_scan_directory: Some(String::new()),
        configured_documents_root: Some(" \t ".to_string()),
    })
    .expect("standard source should convert");
    assert!(source.custom_scan_directory.is_none());
    assert!(source.configured_documents_root.is_none());
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

#[test]
fn shared_failure_fixture_maps_every_node_failure_field() {
    let fixtures = shared_failure_fixtures();
    let log = &fixtures["logResult"];
    let core_stages = [
        LogFailureStage::Analysis,
        LogFailureStage::ReportWrite,
        LogFailureStage::UnsolvedLogsFinalization,
    ];
    let failures = log["failures"]
        .as_array()
        .expect("shared log failures should be an array");
    let mapped = log_result_to_js(LogResult {
        discovery_index: log["discoveryIndex"].as_u64().expect("discovery index") as usize,
        crash_log: PathBuf::from(log["crashLog"].as_str().expect("crash log")),
        autoscan_report: log["autoscanReport"].as_str().map(PathBuf::from),
        disposition: LogDisposition::Failed,
        failures: core_stages
            .into_iter()
            .zip(failures)
            .map(|(stage, failure)| LogFailure {
                stage,
                message: failure["message"]
                    .as_str()
                    .expect("failure message")
                    .to_string(),
            })
            .collect(),
        message: Some(
            log["message"]
                .as_str()
                .expect("aggregate message")
                .to_string(),
        ),
        moved_to_unsolved_logs: log["movedToUnsolvedLogs"].as_bool().expect("movement flag"),
        processing_time_us: log["processingTimeUs"].as_u64().expect("microseconds"),
        processing_time_ms: log["processingTimeMs"].as_u64().expect("milliseconds"),
        formid_count: log["formidCount"].as_u64().expect("FormID count") as usize,
        plugin_count: log["pluginCount"].as_u64().expect("plugin count") as usize,
        suspect_count: log["suspectCount"].as_u64().expect("suspect count") as usize,
    });

    assert_eq!(
        mapped.discovery_index,
        log["discoveryIndex"].as_u64().unwrap() as u32
    );
    assert_eq!(mapped.crash_log, log["crashLog"].as_str().unwrap());
    assert!(mapped.autoscan_report.is_none());
    assert_eq!(mapped.disposition, log["disposition"].as_str().unwrap());
    assert_eq!(mapped.failures.len(), failures.len());
    for (mapped_failure, expected) in mapped.failures.iter().zip(failures) {
        assert_eq!(mapped_failure.stage, expected["stage"].as_str().unwrap());
        assert_eq!(
            mapped_failure.message,
            expected["message"].as_str().unwrap()
        );
    }
    assert_eq!(mapped.message.as_deref(), log["message"].as_str());
    assert_eq!(
        mapped.moved_to_unsolved_logs,
        log["movedToUnsolvedLogs"].as_bool().unwrap()
    );
    assert_eq!(
        mapped.processing_time_us,
        log["processingTimeUs"].as_u64().unwrap() as i64
    );

    let stages = [
        InfrastructureErrorStage::RequestValidation,
        InfrastructureErrorStage::Discovery,
        InfrastructureErrorStage::Intake,
        InfrastructureErrorStage::FormIdDatabaseAccess,
        InfrastructureErrorStage::Initialization,
        InfrastructureErrorStage::InternalInvariant,
    ];
    let infrastructure = fixtures["infrastructureErrors"]
        .as_array()
        .expect("shared infrastructure failures should be an array");
    assert_eq!(infrastructure.len(), stages.len());
    for (stage, expected) in stages.into_iter().zip(infrastructure) {
        let mapped = infrastructure_error_to_js(InfrastructureError {
            stage,
            message: expected["message"].as_str().unwrap().to_string(),
            path: expected["path"].as_str().map(PathBuf::from),
        });
        assert_eq!(mapped.stage, expected["stage"].as_str().unwrap());
        assert_eq!(mapped.message, expected["message"].as_str().unwrap());
        assert_eq!(mapped.path.as_deref(), expected["path"].as_str());
    }
}
