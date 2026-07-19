use std::path::PathBuf;

use classic_config_core::{InstalledYamlDataProvenance, InstalledYamlDataRole};
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanRejectedInput,
    CrashLogScanRunStatus, CrashLogScanSetupCheck, CrashLogScanSetupPathUpdate,
    CrashLogScanSetupResult, ScanProgressPhase,
};
use pyo3::Python;

use super::{
    PyScanRunConfiguration, configuration_to_core, disposition_to_string, event_to_py,
    infrastructure_error_to_py, installed_yaml_data_diagnostic_kind_to_string,
    installed_yaml_data_provenance_to_string, installed_yaml_data_role_to_string,
    local_ignore_state_to_string, log_failure_stage_to_string, log_result_to_py, phase_to_string,
    run_result_to_py, run_status_to_string, setup_to_py,
};

const SHARED_SCAN_RUN_MANIFEST: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/crash_log_scan_run/manifest.json"
));

/// Loads the language-neutral structured-failure corpus for Python mapping tests.
fn shared_failure_fixtures() -> serde_json::Value {
    serde_json::from_str::<serde_json::Value>(SHARED_SCAN_RUN_MANIFEST)
        .expect("shared scan-run manifest should deserialize")["failureFixtures"]
        .clone()
}

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
fn configuration_conversion_treats_blank_destination_as_absent() {
    let configuration = PyScanRunConfiguration {
        installation_root: "C:/CLASSIC".to_string(),
        game: classic_shared_core::GameId::Fallout4,
        game_version: "auto".to_string(),
        show_formid_values: false,
        simplify_logs: false,
        formid_database_paths: Vec::new(),
        unsolved_logs_destination: Some(" \t ".to_string()),
        max_concurrent: None,
    };

    let converted = configuration_to_core(&configuration).expect("configuration should convert");
    assert_eq!(converted.installation_root, PathBuf::from("C:/CLASSIC"));
    assert_eq!(converted.game, classic_shared_core::GameId::Fallout4);
    assert!(converted.scan_facts.unsolved_logs_destination.is_none());
}

#[test]
fn maps_every_stable_enum_identifier() {
    let statuses = [
        CrashLogScanRunStatus::Completed,
        CrashLogScanRunStatus::NoCrashLogsFound,
        CrashLogScanRunStatus::SetupFailed,
        CrashLogScanRunStatus::LocalIgnoreRecoveryRequired,
        CrashLogScanRunStatus::CancelledBeforeDiscovery,
        CrashLogScanRunStatus::Cancelled,
    ];
    assert_eq!(
        statuses.map(run_status_to_string),
        [
            "completed",
            "no_crash_logs_found",
            "setup_failed",
            "local_ignore_recovery_required",
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

    assert_eq!(
        [InstalledYamlDataRole::Main, InstalledYamlDataRole::Game]
            .map(installed_yaml_data_role_to_string),
        ["main", "game"],
    );
    assert_eq!(
        [
            InstalledYamlDataProvenance::Updated,
            InstalledYamlDataProvenance::Previous,
            InstalledYamlDataProvenance::Bundled,
        ]
        .map(installed_yaml_data_provenance_to_string),
        ["updated", "previous", "bundled"],
    );
    assert_eq!(
        [
            contract::LocalIgnoreRunState::Existing,
            contract::LocalIgnoreRunState::Generated,
            contract::LocalIgnoreRunState::RecoveryRequired,
            contract::LocalIgnoreRunState::ProceedWithoutIgnore,
        ]
        .map(local_ignore_state_to_string),
        [
            "existing",
            "generated",
            "recovery_required",
            "proceed_without_ignore",
        ],
    );
    assert_eq!(
        super::PyScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore as u8,
        0
    );
    assert_eq!(
        contract::ResumeErrorKind::ContinuationConsumed.as_str(),
        "scan_run_continuation_consumed"
    );
    assert_eq!(
        [
            contract::InstalledYamlDataRunDiagnosticKind::CacheUnavailable,
            contract::InstalledYamlDataRunDiagnosticKind::Missing,
            contract::InstalledYamlDataRunDiagnosticKind::Read,
            contract::InstalledYamlDataRunDiagnosticKind::InvalidUtf8,
            contract::InstalledYamlDataRunDiagnosticKind::Parse,
            contract::InstalledYamlDataRunDiagnosticKind::InvalidSchema,
            contract::InstalledYamlDataRunDiagnosticKind::IncompatibleSchema,
            contract::InstalledYamlDataRunDiagnosticKind::InvalidRoleData,
            contract::InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated,
        ]
        .map(installed_yaml_data_diagnostic_kind_to_string),
        [
            "cache_unavailable",
            "missing",
            "read",
            "invalid_utf8",
            "parse",
            "invalid_schema",
            "incompatible_schema",
            "invalid_role_data",
            "local_ignore_generated",
        ],
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
fn shared_failure_fixture_maps_every_python_failure_field() {
    let fixtures = shared_failure_fixtures();
    let log = &fixtures["logResult"];
    let core_stages = [
        contract::LogFailureStage::Analysis,
        contract::LogFailureStage::ReportWrite,
        contract::LogFailureStage::UnsolvedLogsFinalization,
    ];
    let failures = log["failures"]
        .as_array()
        .expect("shared log failures should be an array");
    let mapped = log_result_to_py(contract::LogResult {
        discovery_index: log["discoveryIndex"].as_u64().expect("discovery index") as usize,
        crash_log: PathBuf::from(log["crashLog"].as_str().expect("crash log")),
        autoscan_report: log["autoscanReport"].as_str().map(PathBuf::from),
        disposition: contract::LogDisposition::Failed,
        failures: core_stages
            .into_iter()
            .zip(failures)
            .map(|(stage, failure)| contract::LogFailure {
                stage,
                message: failure["message"]
                    .as_str()
                    .expect("failure message")
                    .to_string(),
            })
            .collect(),
        message: Some(log["message"].as_str().expect("aggregate message").to_string()),
        moved_to_unsolved_logs: log["movedToUnsolvedLogs"].as_bool().expect("movement flag"),
        processing_time_us: log["processingTimeUs"].as_u64().expect("microseconds"),
        processing_time_ms: log["processingTimeMs"].as_u64().expect("milliseconds"),
        formid_count: log["formidCount"].as_u64().expect("FormID count") as usize,
        plugin_count: log["pluginCount"].as_u64().expect("plugin count") as usize,
        suspect_count: log["suspectCount"].as_u64().expect("suspect count") as usize,
    });

    assert_eq!(mapped.discovery_index, log["discoveryIndex"].as_u64().unwrap() as usize);
    assert_eq!(mapped.crash_log, log["crashLog"].as_str().unwrap());
    assert!(mapped.autoscan_report.is_none());
    assert_eq!(mapped.disposition, log["disposition"].as_str().unwrap());
    assert_eq!(mapped.failures.len(), failures.len());
    for (mapped_failure, expected) in mapped.failures.iter().zip(failures) {
        assert_eq!(mapped_failure.stage, expected["stage"].as_str().unwrap());
        assert_eq!(mapped_failure.message, expected["message"].as_str().unwrap());
    }
    assert_eq!(mapped.message.as_deref(), log["message"].as_str());
    assert_eq!(
        mapped.moved_to_unsolved_logs,
        log["movedToUnsolvedLogs"].as_bool().unwrap()
    );
    assert_eq!(mapped.processing_time_us, log["processingTimeUs"].as_u64().unwrap());

    let stages = [
        contract::InfrastructureErrorStage::RequestValidation,
        contract::InfrastructureErrorStage::Discovery,
        contract::InfrastructureErrorStage::Intake,
        contract::InfrastructureErrorStage::FormIdDatabaseAccess,
        contract::InfrastructureErrorStage::Initialization,
        contract::InfrastructureErrorStage::InternalInvariant,
    ];
    let infrastructure = fixtures["infrastructureErrors"]
        .as_array()
        .expect("shared infrastructure failures should be an array");
    assert_eq!(infrastructure.len(), stages.len());
    for (stage, expected) in stages.into_iter().zip(infrastructure) {
        let mapped = infrastructure_error_to_py(contract::InfrastructureError {
            stage,
            message: expected["message"].as_str().unwrap().to_string(),
            path: expected["path"].as_str().map(PathBuf::from),
        });
        assert_eq!(mapped.stage, expected["stage"].as_str().unwrap());
        assert_eq!(mapped.message, expected["message"].as_str().unwrap());
        assert_eq!(mapped.path.as_deref(), expected["path"].as_str());
    }
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

    Python::attach(|py| {
        let with_values = run_result_to_py(py, contract::RunResult {
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
            installed_yaml_data: None,
            continuation: None,
            effective_concurrency: Some(2),
            message: Some("run message".to_string()),
            total: 4,
            succeeded: 1,
            failed: 2,
            cancelled: 1,
            logs: Vec::new(),
        })
        .expect("mapped result should allocate");
        let with_values = with_values.borrow(py);
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

        let without_values = run_result_to_py(py, contract::RunResult {
            status: CrashLogScanRunStatus::CancelledBeforeDiscovery,
            discovery: None,
            setup: None,
            installed_yaml_data: None,
            continuation: None,
            effective_concurrency: None,
            message: None,
            total: 0,
            succeeded: 0,
            failed: 0,
            cancelled: 0,
            logs: Vec::new(),
        })
        .expect("mapped result should allocate");
        let without_values = without_values.borrow(py);
        assert!(without_values.discovery.is_none());
        assert!(without_values.setup.is_none());
        assert!(without_values.effective_concurrency.is_none());
        assert!(without_values.message.is_none());
    });
}
