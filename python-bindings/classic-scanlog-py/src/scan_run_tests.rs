use std::path::PathBuf;

use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanRejectedInput,
    CrashLogScanRunStatus, CrashLogScanSetupCheck, CrashLogScanSetupPathUpdate,
    CrashLogScanSetupResult, ScanProgressPhase,
};

use super::{
    disposition_to_string, event_to_py, infrastructure_error_to_py, log_failure_stage_to_string,
    log_result_to_py, phase_to_string, run_result_to_py, run_status_to_string, setup_to_py,
};

fn discovery() -> CrashLogScanDiscoveryResult {
    CrashLogScanDiscoveryResult {
        source: CrashLogScanDiscoverySource::Targeted,
        accepted_logs: vec![PathBuf::from("accepted/crash.log")],
        rejected_inputs: vec![CrashLogScanRejectedInput {
            path: PathBuf::from("rejected/input.txt"),
            reason: "not a Crash Log".to_string(),
        }],
        searched_locations: vec![PathBuf::from("searched")],
    }
}

fn log_event() -> contract::LogEvent {
    contract::LogEvent {
        discovery_index: 7,
        crash_log: PathBuf::from("logs/crash.log"),
        completed: 2,
        total: 5,
    }
}

#[test]
fn maps_every_stable_enum_identifier() {
    let statuses = [
        CrashLogScanRunStatus::Completed,
        CrashLogScanRunStatus::NoCrashLogsFound,
        CrashLogScanRunStatus::SetupFailed,
        CrashLogScanRunStatus::CancelledBeforeDiscovery,
        CrashLogScanRunStatus::Cancelled,
    ];
    assert_eq!(
        statuses.map(run_status_to_string),
        [
            "completed",
            "no_crash_logs_found",
            "setup_failed",
            "cancelled_before_discovery",
            "cancelled",
        ]
        .map(str::to_string),
    );

    let dispositions = [
        contract::LogDisposition::Succeeded,
        contract::LogDisposition::Failed,
        contract::LogDisposition::CancelledBeforeStart,
    ];
    assert_eq!(
        dispositions.map(disposition_to_string),
        ["succeeded", "failed", "cancelled_before_start"].map(str::to_string),
    );

    let failure_stages = [
        contract::LogFailureStage::Analysis,
        contract::LogFailureStage::ReportWrite,
        contract::LogFailureStage::UnsolvedLogsFinalization,
    ];
    assert_eq!(
        failure_stages.map(log_failure_stage_to_string),
        ["analysis", "report_write", "unsolved_logs_finalization"].map(str::to_string),
    );

    let phases = [
        ScanProgressPhase::Setup,
        ScanProgressPhase::Parse,
        ScanProgressPhase::Analyze,
        ScanProgressPhase::Finalize,
    ];
    assert_eq!(
        phases.map(phase_to_string),
        ["setup", "parse", "analyze", "finalize"].map(str::to_string),
    );
}

#[test]
fn maps_every_infrastructure_stage_and_optional_path() {
    let cases = [
        (
            contract::InfrastructureErrorStage::RequestValidation,
            "request_validation",
        ),
        (contract::InfrastructureErrorStage::Discovery, "discovery"),
        (contract::InfrastructureErrorStage::Intake, "intake"),
        (
            contract::InfrastructureErrorStage::FormIdDatabaseAccess,
            "formid_database_access",
        ),
        (
            contract::InfrastructureErrorStage::Initialization,
            "initialization",
        ),
        (
            contract::InfrastructureErrorStage::InternalInvariant,
            "internal_invariant",
        ),
    ];

    for (index, (stage, expected)) in cases.into_iter().enumerate() {
        let path = (index % 2 == 0).then(|| PathBuf::from(format!("failure-{index}")));
        let mapped = infrastructure_error_to_py(contract::InfrastructureError {
            stage,
            message: format!("failure {index}"),
            path: path.clone(),
        });
        assert_eq!(mapped.stage, expected);
        assert_eq!(mapped.message, format!("failure {index}"));
        assert_eq!(
            mapped.path,
            path.map(|value| value.to_string_lossy().into_owned())
        );
    }
}

#[test]
fn maps_every_event_variant_and_variant_payload() {
    let events = [
        contract::Event::DiscoveryCompleted(discovery()),
        contract::Event::EffectiveConcurrencySelected {
            effective_concurrency: 4,
        },
        contract::Event::LogQueued(log_event()),
        contract::Event::LogStarted(log_event()),
        contract::Event::LogPhase {
            log: log_event(),
            phase: ScanProgressPhase::Analyze,
        },
        contract::Event::LogFinished {
            log: log_event(),
            disposition: contract::LogDisposition::Failed,
        },
    ];
    let mapped = events.map(event_to_py);

    assert_eq!(
        mapped.each_ref().map(|event| event.kind.as_str()),
        [
            "discovery_completed",
            "effective_concurrency_selected",
            "log_queued",
            "log_started",
            "log_phase",
            "log_finished",
        ],
    );
    let retained = mapped[0].discovery.as_ref().expect("discovery payload");
    assert_eq!(retained.source, "targeted");
    assert_eq!(retained.accepted_logs, ["accepted/crash.log"]);
    assert_eq!(retained.rejected_inputs[0].path, "rejected/input.txt");
    assert_eq!(retained.searched_locations, ["searched"]);
    assert_eq!(mapped[1].effective_concurrency, Some(4));
    assert_eq!(
        mapped[2].log.as_ref().expect("queued log").discovery_index,
        7
    );
    assert_eq!(mapped[4].phase.as_deref(), Some("analyze"));
    assert_eq!(mapped[5].disposition.as_deref(), Some("failed"));
}

#[test]
fn maps_complete_log_result_and_all_failure_stages() {
    let mapped = log_result_to_py(contract::LogResult {
        discovery_index: 3,
        crash_log: PathBuf::from("logs/crash.log"),
        autoscan_report: Some(PathBuf::from("logs/crash-AUTOSCAN.md")),
        disposition: contract::LogDisposition::Failed,
        failures: vec![
            contract::LogFailure {
                stage: contract::LogFailureStage::Analysis,
                message: "analysis".to_string(),
            },
            contract::LogFailure {
                stage: contract::LogFailureStage::ReportWrite,
                message: "write".to_string(),
            },
            contract::LogFailure {
                stage: contract::LogFailureStage::UnsolvedLogsFinalization,
                message: "move".to_string(),
            },
        ],
        message: Some("failed".to_string()),
        moved_to_unsolved_logs: true,
        processing_time_us: 1_500,
        processing_time_ms: 1,
        formid_count: 2,
        plugin_count: 3,
        suspect_count: 4,
    });

    assert_eq!(mapped.discovery_index, 3);
    assert_eq!(mapped.crash_log, "logs/crash.log");
    assert_eq!(
        mapped.autoscan_report.as_deref(),
        Some("logs/crash-AUTOSCAN.md")
    );
    assert_eq!(mapped.disposition, "failed");
    assert_eq!(
        mapped
            .failures
            .iter()
            .map(|failure| failure.stage.as_str())
            .collect::<Vec<_>>(),
        ["analysis", "report_write", "unsolved_logs_finalization"],
    );
    assert_eq!(mapped.message.as_deref(), Some("failed"));
    assert!(mapped.moved_to_unsolved_logs);
    assert_eq!(
        (mapped.processing_time_us, mapped.processing_time_ms),
        (1_500, 1)
    );
    assert_eq!(
        (
            mapped.formid_count,
            mapped.plugin_count,
            mapped.suspect_count
        ),
        (2, 3, 4)
    );

    let empty = log_result_to_py(contract::LogResult {
        discovery_index: 0,
        crash_log: PathBuf::from("empty.log"),
        autoscan_report: None,
        disposition: contract::LogDisposition::CancelledBeforeStart,
        failures: Vec::new(),
        message: None,
        moved_to_unsolved_logs: false,
        processing_time_us: 0,
        processing_time_ms: 0,
        formid_count: 0,
        plugin_count: 0,
        suspect_count: 0,
    });
    assert_eq!(empty.autoscan_report, None);
    assert_eq!(empty.message, None);
    assert_eq!(empty.disposition, "cancelled_before_start");
}

#[test]
fn maps_setup_and_run_optional_fields_without_loss() {
    let setup = setup_to_py(CrashLogScanSetupResult {
        status: "action_required".to_string(),
        checks: vec![CrashLogScanSetupCheck {
            kind: "game_root".to_string(),
            state: "missing".to_string(),
            message: "select a game root".to_string(),
            details: vec!["detail".to_string()],
        }],
        path_updates: vec![CrashLogScanSetupPathUpdate {
            kind: "docs_root".to_string(),
            path: PathBuf::from("documents"),
        }],
        configuration_issues: Vec::new(),
        actions: vec!["choose path".to_string()],
        fatal_errors: vec!["fatal".to_string()],
        message: Some("setup failed".to_string()),
        rendered_report: "report".to_string(),
    });
    assert_eq!(setup.status, "action_required");
    assert_eq!(setup.message.as_deref(), Some("setup failed"));
    assert_eq!(setup.checks[0].details, ["detail"]);
    assert_eq!(setup.path_updates[0].path, "documents");
    assert_eq!(setup.actions, ["choose path"]);
    assert_eq!(setup.fatal_errors, ["fatal"]);

    let with_values = run_result_to_py(contract::RunResult {
        status: CrashLogScanRunStatus::SetupFailed,
        discovery: Some(discovery()),
        setup: Some(CrashLogScanSetupResult {
            status: setup.status.clone(),
            checks: Vec::new(),
            path_updates: Vec::new(),
            configuration_issues: Vec::new(),
            actions: Vec::new(),
            fatal_errors: Vec::new(),
            message: setup.message.clone(),
            rendered_report: setup.rendered_report.clone(),
        }),
        effective_concurrency: Some(2),
        message: Some("run message".to_string()),
        total: 4,
        succeeded: 1,
        failed: 2,
        cancelled: 1,
        logs: Vec::new(),
    });
    assert_eq!(with_values.status, "setup_failed");
    assert!(with_values.discovery.is_some());
    assert!(with_values.setup.is_some());
    assert_eq!(with_values.effective_concurrency, Some(2));
    assert_eq!(with_values.message.as_deref(), Some("run message"));
    assert_eq!(
        (
            with_values.total,
            with_values.succeeded,
            with_values.failed,
            with_values.cancelled,
        ),
        (4, 1, 2, 1),
    );

    let without_values = run_result_to_py(contract::RunResult {
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
    });
    assert!(without_values.discovery.is_none());
    assert!(without_values.setup.is_none());
    assert!(without_values.effective_concurrency.is_none());
    assert!(without_values.message.is_none());
}
