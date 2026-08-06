use super::*;
// Imported here rather than in `contract.rs`: the module itself only projects
// labels through `crate::vocabulary::display_label`, so the trait is in scope
// only where the tests read `label()` off a core variant to derive their
// expectation from.
use classic_vocabulary::Vocabulary;
use tempfile::tempdir;

const FIXTURE_LOG_SMALL: &str = include_str!(
    "../../../../business-logic/classic-scanlog-core/benches/fixtures/crash-0DB9300.log"
);
const SHARED_SCAN_RUN_MANIFEST: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../tests/fixtures/crash_log_scan_run/manifest.json"
));

/// Loads the language-neutral structured-failure corpus for CXX mapping tests.
fn shared_failure_fixtures() -> serde_json::Value {
    serde_json::from_str::<serde_json::Value>(SHARED_SCAN_RUN_MANIFEST)
        .expect("shared scan-run manifest should deserialize")["failureFixtures"]
        .clone()
}

fn sample_configuration() -> ffi::ScanRunConfigurationDto {
    ffi::ScanRunConfigurationDto {
        installation_root: "root".to_string(),
        game: ffi::ScanRunGameId::Fallout4,
        game_version: "auto".to_string(),
        show_formid_values: false,
        simplify_logs: false,
        formid_database_paths: Vec::new(),
        has_configured_unsolved_logs_destination: false,
        configured_unsolved_logs_destination: String::new(),
        has_max_concurrent: false,
        max_concurrent: 0,
    }
}

fn sample_standard_source() -> ffi::ScanRunStandardSourceDto {
    ffi::ScanRunStandardSourceDto {
        base_directory: "root".to_string(),
        has_custom_scan_directory: false,
        custom_scan_directory: String::new(),
        has_configured_documents_root: false,
        configured_documents_root: String::new(),
    }
}

fn sample_targeted_source() -> ffi::ScanRunTargetedSourceDto {
    ffi::ScanRunTargetedSourceDto {
        inputs: vec!["first.log".to_string(), "second.log".to_string()],
    }
}

fn sample_setup_context() -> ffi::ScanRunSetupContextDto {
    ffi::ScanRunSetupContextDto {
        has_game_root: true,
        game_root: "game".to_string(),
        has_docs_root: true,
        docs_root: "docs".to_string(),
        has_game_exe_path: false,
        game_exe_path: String::new(),
        has_xse_log_path: false,
        xse_log_path: String::new(),
    }
}

fn write_minimal_scan_yaml_tree(_root: &std::path::Path, data: &std::path::Path) {
    std::fs::create_dir_all(data.join("databases")).unwrap();
    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        concat!(
            "schema_version: \"2.0\"\n",
            "CLASSIC_Info:\n",
            "  version: \"v9.1.0\"\n",
            "  version_date: \"2026-06-30\"\n",
            "  default_ignorefile: |\n",
            "    CLASSIC_Ignore_Fallout4:\n",
            "      - IgnoreThis.dll\n",
            "CLASSIC_Interface:\n",
            "  autoscan_text_Fallout4: \"Autoscan Fallout 4\"\n",
            "exclude_log_records:\n",
            "  - '(void*)'\n",
        ),
    )
    .unwrap();
    std::fs::write(
        data.join("databases").join("CLASSIC Fallout4.yaml"),
        concat!(
            "schema_version: \"1.0\"\n",
            "Game_Info:\n",
            "  XSE_Acronym: \"F4SE\"\n",
            "  GameVersion: \"1.10.163\"\n",
            "  CRASHGEN_LatestVer: \"1.28.6\"\n",
            "  CRASHGEN_LogName: \"Buffout 4\"\n",
            "  Main_Root_Name: \"Fallout4\"\n",
        ),
    )
    .unwrap();
    std::fs::write(
        data.join("CLASSIC Ignore.yaml"),
        "CLASSIC_Ignore_Fallout4: []\n",
    )
    .unwrap();
}

#[test]
fn standard_request_constructor_builds_non_fcx_leave_in_place_request() {
    let unsolved_logs = scan_run_unsolved_logs_leave_in_place();
    let request = scan_run_request_standard(
        &sample_configuration(),
        &sample_standard_source(),
        &unsolved_logs,
    )
    .expect("valid Standard request should be constructible");

    let contract::Request::Standard(request) = &request.inner else {
        panic!("expected Standard request tag");
    };
    assert!(!request.fcx_enabled());
    assert_eq!(request.configuration().installation_root, PathBuf::from("root"));
    assert_eq!(request.configuration().game, GameId::Fallout4);
    assert_eq!(
        request.unsolved_logs(),
        &classic_scanlog_core::StandardUnsolvedLogsIntent::LeaveInPlace
    );
}

#[test]
fn request_constructors_preserve_every_valid_tagged_combination() {
    let configured = scan_run_unsolved_logs_move_to_configured_or_default();
    let custom = scan_run_unsolved_logs_move_to_custom("custom-unsolved")
        .expect("non-empty custom destination should be accepted");

    let standard = scan_run_request_standard(
        &sample_configuration(),
        &sample_standard_source(),
        &configured,
    )
    .unwrap();
    let contract::Request::Standard(standard) = &standard.inner else {
        panic!("expected Standard request tag");
    };
    assert_eq!(
        standard.unsolved_logs(),
        &classic_scanlog_core::StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault
    );

    let standard_fcx = scan_run_request_standard_with_fcx(
        &sample_configuration(),
        &sample_standard_source(),
        &custom,
        &sample_setup_context(),
    )
    .unwrap();
    let contract::Request::Standard(standard_fcx) = &standard_fcx.inner else {
        panic!("expected Standard request tag");
    };
    assert!(standard_fcx.fcx_enabled());
    assert_eq!(
        standard_fcx.unsolved_logs(),
        &classic_scanlog_core::StandardUnsolvedLogsIntent::MoveToCustom(PathBuf::from(
            "custom-unsolved"
        ))
    );

    let targeted =
        scan_run_request_targeted(&sample_configuration(), &sample_targeted_source()).unwrap();
    let contract::Request::Targeted(targeted) = &targeted.inner else {
        panic!("expected Targeted request tag");
    };
    assert!(!targeted.fcx_enabled());
    assert_eq!(
        targeted.source().inputs,
        vec![PathBuf::from("first.log"), PathBuf::from("second.log")]
    );

    let targeted_fcx = scan_run_request_targeted_with_fcx(
        &sample_configuration(),
        &sample_targeted_source(),
        &sample_setup_context(),
    )
    .unwrap();
    let contract::Request::Targeted(targeted_fcx) = &targeted_fcx.inner else {
        panic!("expected Targeted request tag");
    };
    assert!(targeted_fcx.fcx_enabled());
}

#[test]
fn cancellation_is_monotonic_and_observable() {
    let cancellation = scan_run_cancellation_new();
    assert!(!scan_run_cancellation_is_cancelled(&cancellation));

    scan_run_cancellation_cancel(&cancellation);

    assert!(scan_run_cancellation_is_cancelled(&cancellation));
}

#[test]
fn maps_every_core_enum_variant_to_a_typed_cxx_variant() {
    assert_eq!(
        map_run_status(CrashLogScanRunStatus::Completed),
        ffi::ScanRunContractStatus::Completed
    );
    assert_eq!(
        map_run_status(CrashLogScanRunStatus::NoCrashLogsFound),
        ffi::ScanRunContractStatus::NoCrashLogsFound
    );
    assert_eq!(
        map_run_status(CrashLogScanRunStatus::SetupFailed),
        ffi::ScanRunContractStatus::SetupFailed
    );
    assert_eq!(
        map_run_status(CrashLogScanRunStatus::CancelledBeforeDiscovery),
        ffi::ScanRunContractStatus::CancelledBeforeDiscovery
    );
    assert_eq!(
        map_run_status(CrashLogScanRunStatus::Cancelled),
        ffi::ScanRunContractStatus::Cancelled
    );
    assert_eq!(
        map_run_status(CrashLogScanRunStatus::LocalIgnoreRecoveryRequired),
        ffi::ScanRunContractStatus::LocalIgnoreRecoveryRequired
    );

    assert_eq!(
        map_discovery_source(CrashLogScanDiscoverySource::Standard),
        ffi::ScanRunContractDiscoverySource::Standard
    );
    assert_eq!(
        map_discovery_source(CrashLogScanDiscoverySource::Targeted),
        ffi::ScanRunContractDiscoverySource::Targeted
    );

    assert_eq!(
        map_log_disposition(contract::LogDisposition::Succeeded),
        ffi::ScanRunContractLogDisposition::Succeeded
    );
    assert_eq!(
        map_log_disposition(contract::LogDisposition::Failed),
        ffi::ScanRunContractLogDisposition::Failed
    );
    assert_eq!(
        map_log_disposition(contract::LogDisposition::CancelledBeforeStart),
        ffi::ScanRunContractLogDisposition::CancelledBeforeStart
    );

    assert_eq!(
        map_log_failure_stage(contract::LogFailureStage::Analysis),
        ffi::ScanRunContractLogFailureStage::Analysis
    );
    assert_eq!(
        map_log_failure_stage(contract::LogFailureStage::ReportWrite),
        ffi::ScanRunContractLogFailureStage::ReportWrite
    );
    assert_eq!(
        map_log_failure_stage(contract::LogFailureStage::UnsolvedLogsFinalization),
        ffi::ScanRunContractLogFailureStage::UnsolvedLogsFinalization
    );

    assert_eq!(
        map_infrastructure_error_stage(contract::InfrastructureErrorStage::RequestValidation),
        ffi::ScanRunContractInfrastructureErrorStage::RequestValidation
    );
    assert_eq!(
        map_infrastructure_error_stage(contract::InfrastructureErrorStage::Discovery),
        ffi::ScanRunContractInfrastructureErrorStage::Discovery
    );
    assert_eq!(
        map_infrastructure_error_stage(contract::InfrastructureErrorStage::Intake),
        ffi::ScanRunContractInfrastructureErrorStage::Intake
    );
    assert_eq!(
        map_infrastructure_error_stage(contract::InfrastructureErrorStage::FormIdDatabaseAccess),
        ffi::ScanRunContractInfrastructureErrorStage::FormIdDatabaseAccess
    );
    assert_eq!(
        map_infrastructure_error_stage(contract::InfrastructureErrorStage::Initialization),
        ffi::ScanRunContractInfrastructureErrorStage::Initialization
    );
    assert_eq!(
        map_infrastructure_error_stage(contract::InfrastructureErrorStage::InternalInvariant),
        ffi::ScanRunContractInfrastructureErrorStage::InternalInvariant
    );

    assert_eq!(
        map_phase(ScanProgressPhase::Setup),
        ffi::ScanRunContractProgressPhase::Setup
    );
    assert_eq!(
        map_phase(ScanProgressPhase::Parse),
        ffi::ScanRunContractProgressPhase::Parse
    );
    assert_eq!(
        map_phase(ScanProgressPhase::Analyze),
        ffi::ScanRunContractProgressPhase::Analyze
    );
    assert_eq!(
        map_phase(ScanProgressPhase::Finalize),
        ffi::ScanRunContractProgressPhase::Finalize
    );

    for (core, cxx) in [
        (
            classic_config_core::InstalledYamlDataRole::Main,
            ffi::ScanRunInstalledYamlDataRole::Main,
        ),
        (
            classic_config_core::InstalledYamlDataRole::Game,
            ffi::ScanRunInstalledYamlDataRole::Game,
        ),
    ] {
        assert_eq!(map_installed_yaml_data_role(core), cxx);
    }
    for (core, cxx) in [
        (
            classic_config_core::InstalledYamlDataProvenance::Updated,
            ffi::ScanRunInstalledYamlDataProvenance::Updated,
        ),
        (
            classic_config_core::InstalledYamlDataProvenance::Previous,
            ffi::ScanRunInstalledYamlDataProvenance::Previous,
        ),
        (
            classic_config_core::InstalledYamlDataProvenance::Bundled,
            ffi::ScanRunInstalledYamlDataProvenance::Bundled,
        ),
    ] {
        assert_eq!(map_installed_yaml_data_provenance(core), cxx);
    }
    for (core, cxx) in [
        (
            contract::LocalIgnoreRunState::Existing,
            ffi::ScanRunLocalIgnoreYamlDataState::Existing,
        ),
        (
            contract::LocalIgnoreRunState::Generated,
            ffi::ScanRunLocalIgnoreYamlDataState::Generated,
        ),
        (
            contract::LocalIgnoreRunState::RecoveryRequired,
            ffi::ScanRunLocalIgnoreYamlDataState::RecoveryRequired,
        ),
        (
            contract::LocalIgnoreRunState::ProceedWithoutIgnore,
            ffi::ScanRunLocalIgnoreYamlDataState::ProceedWithoutIgnore,
        ),
        (
            contract::LocalIgnoreRunState::ResetToDefault,
            ffi::ScanRunLocalIgnoreYamlDataState::ResetToDefault,
        ),
    ] {
        assert_eq!(map_local_ignore_yaml_data_state(core), cxx);
    }
    assert_eq!(
        map_local_ignore_recovery_decision(
            ffi::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
        ),
        Ok(contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore)
    );
    assert_eq!(
        map_local_ignore_recovery_decision(
            ffi::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault,
        ),
        Ok(contract::LocalIgnoreRecoveryDecision::ResetToDefault)
    );

    let diagnostic_pairs = [
        (
            contract::InstalledYamlDataRunDiagnosticKind::CacheUnavailable,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::CacheUnavailable,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::Missing,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::Missing,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::Read,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::Read,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::InvalidUtf8,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::InvalidUtf8,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::Parse,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::Parse,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::InvalidSchema,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::InvalidSchema,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::IncompatibleSchema,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::IncompatibleSchema,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::InvalidRoleData,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::InvalidRoleData,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::LocalIgnoreReset,
            ffi::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreReset,
        ),
    ];
    for (core, cxx) in diagnostic_pairs {
        assert_eq!(map_installed_yaml_data_diagnostic_kind(core), cxx);
    }
}

#[test]
fn structured_result_mapping_preserves_pairs_options_failures_and_paths() {
    let discovery = CrashLogScanDiscoveryResult {
        source: CrashLogScanDiscoverySource::Targeted,
        accepted_logs: vec![PathBuf::from("accepted-é.log")],
        rejected_inputs: vec![classic_scanlog_core::CrashLogScanRejectedInput {
            path: PathBuf::from("rejected.log"),
            reason: "unsupported".to_string(),
        }],
        searched_locations: vec![PathBuf::from("searched")],
    };
    let log = contract::LogResult {
        discovery_index: 4,
        crash_log: PathBuf::from("accepted-é.log"),
        autoscan_report: Some(PathBuf::from("accepted-é-AUTOSCAN.md")),
        disposition: contract::LogDisposition::Failed,
        failures: vec![
            contract::LogFailure {
                stage: contract::LogFailureStage::Analysis,
                message: "analysis failed".to_string(),
            },
            contract::LogFailure {
                stage: contract::LogFailureStage::ReportWrite,
                message: "write failed".to_string(),
            },
            contract::LogFailure {
                stage: contract::LogFailureStage::UnsolvedLogsFinalization,
                message: "move failed".to_string(),
            },
        ],
        message: Some("three failures".to_string()),
        moved_to_unsolved_logs: false,
        processing_time_us: 2_345,
        processing_time_ms: 2,
        formid_count: 3,
        plugin_count: 4,
        suspect_count: 5,
    };
    let dto = run_result_to_dto(contract::RunResult {
        status: CrashLogScanRunStatus::Completed,
        discovery: Some(discovery),
        setup: None,
        installed_yaml_data: None,
        effective_concurrency: Some(2),
        message: Some("completed with failures".to_string()),
        total: 1,
        succeeded: 0,
        failed: 1,
        cancelled: 0,
        logs: vec![log],
        continuation: None,
    });

    assert!(dto.has_discovery);
    assert_eq!(
        dto.discovery.source,
        ffi::ScanRunContractDiscoverySource::Targeted
    );
    assert_eq!(dto.discovery.accepted_logs, vec!["accepted-é.log"]);
    assert_eq!(dto.discovery.rejected_inputs.len(), 1);
    assert_eq!(dto.discovery.rejected_inputs[0].path, "rejected.log");
    assert_eq!(dto.discovery.rejected_inputs[0].reason, "unsupported");
    assert!(!dto.has_setup);
    assert!(!dto.has_installed_yaml_data);
    assert!(dto.has_effective_concurrency);
    assert_eq!(dto.effective_concurrency, 2);
    assert!(dto.has_message);
    assert_eq!(dto.message, "completed with failures");
    assert_eq!(dto.logs.len(), 1);
    assert_eq!(dto.logs[0].discovery_index, 4);
    assert!(dto.logs[0].has_autoscan_report);
    assert_eq!(dto.logs[0].autoscan_report, "accepted-é-AUTOSCAN.md");
    assert_eq!(
        dto.logs[0].disposition,
        ffi::ScanRunContractLogDisposition::Failed
    );
    assert_eq!(dto.logs[0].failures.len(), 3);
    assert_eq!(
        dto.logs[0].failures[2].stage,
        ffi::ScanRunContractLogFailureStage::UnsolvedLogsFinalization
    );
    assert_eq!(dto.logs[0].processing_time_us, 2_345);
    assert_eq!(dto.logs[0].processing_time_ms, 2);

    let error = infrastructure_error_to_dto(contract::InfrastructureError {
        stage: contract::InfrastructureErrorStage::FormIdDatabaseAccess,
        message: "database unavailable".to_string(),
        path: Some(PathBuf::from("database-é.db")),
    });
    assert_eq!(
        error.stage,
        ffi::ScanRunContractInfrastructureErrorStage::FormIdDatabaseAccess
    );
    assert_eq!(error.message, "database unavailable");
    assert!(error.has_path);
    assert_eq!(error.path, "database-é.db");
}

/// Loads the shared reset-outcome codes used by CXX continuation mapping tests.
fn shared_reset_outcomes() -> serde_json::Value {
    serde_json::from_str::<serde_json::Value>(SHARED_SCAN_RUN_MANIFEST)
        .expect("shared scan-run manifest should deserialize")["fixtures"]["installedYamlData"]
        ["resetOutcomes"]
        .clone()
}

#[test]
fn shared_failure_fixture_maps_every_cxx_failure_field() {
    let fixtures = shared_failure_fixtures();
    let log = &fixtures["logResult"];
    let stages = [
        contract::LogFailureStage::Analysis,
        contract::LogFailureStage::ReportWrite,
        contract::LogFailureStage::UnsolvedLogsFinalization,
    ];
    let failures = log["failures"]
        .as_array()
        .expect("shared log failures should be an array");
    let mapped = log_result_to_dto(contract::LogResult {
        discovery_index: log["discoveryIndex"].as_u64().expect("discovery index") as usize,
        crash_log: PathBuf::from(log["crashLog"].as_str().expect("crash log")),
        autoscan_report: log["autoscanReport"].as_str().map(PathBuf::from),
        disposition: contract::LogDisposition::Failed,
        failures: stages
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
    assert!(!mapped.has_autoscan_report);
    assert_eq!(mapped.disposition, ffi::ScanRunContractLogDisposition::Failed);
    assert_eq!(mapped.failures.len(), failures.len());
    let expected_failure_stages = [
        ffi::ScanRunContractLogFailureStage::Analysis,
        ffi::ScanRunContractLogFailureStage::ReportWrite,
        ffi::ScanRunContractLogFailureStage::UnsolvedLogsFinalization,
    ];
    for ((mapped_failure, expected), expected_stage) in mapped
        .failures
        .iter()
        .zip(failures)
        .zip(expected_failure_stages)
    {
        assert_eq!(mapped_failure.stage, expected_stage);
        assert_eq!(
            mapped_failure.message,
            expected["message"].as_str().unwrap()
        );
    }
    assert_eq!(mapped.message, log["message"].as_str().unwrap());
    assert_eq!(
        mapped.moved_to_unsolved_logs,
        log["movedToUnsolvedLogs"].as_bool().unwrap()
    );

    let stage_pairs = [
        (
            contract::InfrastructureErrorStage::RequestValidation,
            ffi::ScanRunContractInfrastructureErrorStage::RequestValidation,
        ),
        (
            contract::InfrastructureErrorStage::Discovery,
            ffi::ScanRunContractInfrastructureErrorStage::Discovery,
        ),
        (
            contract::InfrastructureErrorStage::Intake,
            ffi::ScanRunContractInfrastructureErrorStage::Intake,
        ),
        (
            contract::InfrastructureErrorStage::FormIdDatabaseAccess,
            ffi::ScanRunContractInfrastructureErrorStage::FormIdDatabaseAccess,
        ),
        (
            contract::InfrastructureErrorStage::Initialization,
            ffi::ScanRunContractInfrastructureErrorStage::Initialization,
        ),
        (
            contract::InfrastructureErrorStage::InternalInvariant,
            ffi::ScanRunContractInfrastructureErrorStage::InternalInvariant,
        ),
    ];
    let infrastructure = fixtures["infrastructureErrors"]
        .as_array()
        .expect("shared infrastructure failures should be an array");
    assert_eq!(infrastructure.len(), stage_pairs.len());
    for ((core_stage, cxx_stage), expected) in stage_pairs.into_iter().zip(infrastructure) {
        let mapped = infrastructure_error_to_dto(contract::InfrastructureError {
            stage: core_stage,
            message: expected["message"].as_str().unwrap().to_string(),
            path: expected["path"].as_str().map(PathBuf::from),
        });
        assert_eq!(mapped.stage, cxx_stage);
        assert_eq!(mapped.message, expected["message"].as_str().unwrap());
        assert_eq!(mapped.has_path, !expected["path"].is_null());
        assert_eq!(
            mapped.path,
            expected["path"].as_str().unwrap_or_default()
        );
    }
}

#[test]
fn event_mapping_covers_discovery_concurrency_and_every_log_variant() {
    let discovery = CrashLogScanDiscoveryResult {
        source: CrashLogScanDiscoverySource::Standard,
        accepted_logs: vec![PathBuf::from("one.log")],
        rejected_inputs: Vec::new(),
        searched_locations: vec![PathBuf::from("root")],
    };
    let discovery_event = event_to_dto(contract::Event::DiscoveryCompleted(discovery));
    assert_eq!(
        discovery_event.kind,
        ffi::ScanRunContractEventKind::DiscoveryCompleted
    );
    assert_eq!(discovery_event.discovery.accepted_logs, vec!["one.log"]);

    let concurrency = event_to_dto(contract::Event::EffectiveConcurrencySelected {
        effective_concurrency: 3,
    });
    assert_eq!(
        concurrency.kind,
        ffi::ScanRunContractEventKind::EffectiveConcurrencySelected
    );
    assert_eq!(concurrency.effective_concurrency, 3);

    let log = contract::LogEvent {
        discovery_index: 7,
        crash_log: PathBuf::from("one.log"),
        completed: 0,
        total: 2,
    };
    let queued = event_to_dto(contract::Event::LogQueued(log.clone()));
    assert_eq!(queued.kind, ffi::ScanRunContractEventKind::LogQueued);
    assert_eq!(queued.discovery_index, 7);
    assert_eq!(queued.crash_log, "one.log");

    let started = event_to_dto(contract::Event::LogStarted(log.clone()));
    assert_eq!(started.kind, ffi::ScanRunContractEventKind::LogStarted);

    let phase = event_to_dto(contract::Event::LogPhase {
        log: log.clone(),
        phase: ScanProgressPhase::Analyze,
    });
    assert_eq!(phase.kind, ffi::ScanRunContractEventKind::LogPhase);
    assert_eq!(phase.phase, ffi::ScanRunContractProgressPhase::Analyze);

    for (disposition, expected) in [
        (
            contract::LogDisposition::Succeeded,
            ffi::ScanRunContractLogDisposition::Succeeded,
        ),
        (
            contract::LogDisposition::Failed,
            ffi::ScanRunContractLogDisposition::Failed,
        ),
        (
            contract::LogDisposition::CancelledBeforeStart,
            ffi::ScanRunContractLogDisposition::CancelledBeforeStart,
        ),
    ] {
        let finished = event_to_dto(contract::Event::LogFinished {
            log: log.clone(),
            disposition,
        });
        assert_eq!(finished.kind, ffi::ScanRunContractEventKind::LogFinished);
        assert_eq!(finished.disposition, expected);
    }
}

#[test]
fn execute_without_observer_returns_targeted_rejections_as_a_terminal_result() {
    let request =
        scan_run_request_targeted(&sample_configuration(), &sample_targeted_source()).unwrap();
    let cancellation = scan_run_cancellation_new();

    // SAFETY: null is the documented representation of an omitted observer.
    let mut operation =
        unsafe { scan_run_contract_execute(&request, &cancellation, std::ptr::null()) };
    let execution = scan_run_contract_execution_take_result(&mut operation);

    assert!(execution.has_result);
    assert!(!execution.has_error);
    assert_eq!(
        execution.result.status,
        ffi::ScanRunContractStatus::NoCrashLogsFound
    );
    assert!(execution.result.has_discovery);
    assert_eq!(execution.result.discovery.rejected_inputs.len(), 2);
    assert!(execution.result.logs.is_empty());
    assert!(!execution.result.has_installed_yaml_data);
}

#[test]
fn request_construction_rejects_invalid_values_and_preserves_empty_fcx_context() {
    assert!(scan_run_unsolved_logs_move_to_custom("  ").is_err());
    let mut invalid_game = sample_configuration();
    invalid_game.game = ffi::ScanRunGameId { repr: u8::MAX };
    let error = scan_run_request_targeted(&invalid_game, &sample_targeted_source())
        .err()
        .expect("unknown CXX game discriminants must fail request construction");
    assert!(error.contains("unsupported ScanRunGameId discriminant: 255"));

    let empty_setup = ffi::ScanRunSetupContextDto {
        has_game_root: false,
        game_root: String::new(),
        has_docs_root: false,
        docs_root: String::new(),
        has_game_exe_path: false,
        game_exe_path: String::new(),
        has_xse_log_path: false,
        xse_log_path: String::new(),
    };
    let request = scan_run_request_targeted_with_fcx(
        &sample_configuration(),
        &sample_targeted_source(),
        &empty_setup,
    )
    .unwrap();
    let contract::Request::Targeted(request) = &request.inner else {
        panic!("expected Targeted request tag");
    };
    assert!(request.fcx_enabled());
    let setup = request
        .setup_context()
        .expect("explicit empty setup context must remain present");
    assert!(setup.game_root.is_none());
    assert!(setup.docs_root.is_none());
    assert!(setup.game_exe_path.is_none());
    assert!(setup.xse_log_path.is_none());
}

#[test]
fn explicit_zero_concurrency_reaches_typed_request_validation_error() {
    let mut configuration = sample_configuration();
    configuration.has_max_concurrent = true;
    configuration.max_concurrent = 0;
    let request = scan_run_request_targeted(&configuration, &sample_targeted_source()).unwrap();

    // SAFETY: null is the documented representation of an omitted observer.
    let mut operation = unsafe {
        scan_run_contract_execute(&request, &scan_run_cancellation_new(), std::ptr::null())
    };
    let execution = scan_run_contract_execution_take_result(&mut operation);

    assert!(execution.has_error);
    assert_eq!(
        execution.error.stage,
        ffi::ScanRunContractInfrastructureErrorStage::RequestValidation
    );
    assert!(!execution.error.has_path);
    assert_eq!(
        execution.error.message,
        "max_concurrent must be greater than zero when supplied"
    );
}

#[test]
fn execute_covers_standard_no_logs_and_cancellation_before_discovery() {
    let temp = tempdir().unwrap();
    std::fs::create_dir_all(temp.path().join("Crash Logs").join("Pastebin")).unwrap();
    let mut configuration = sample_configuration();
    configuration.installation_root = temp.path().to_string_lossy().into_owned();
    write_minimal_scan_yaml_tree(temp.path(), &temp.path().join("CLASSIC Data"));
    let documents = temp.path().join("Documents");
    std::fs::create_dir_all(&documents).unwrap();
    let source = ffi::ScanRunStandardSourceDto {
        base_directory: temp.path().to_string_lossy().into_owned(),
        has_custom_scan_directory: false,
        custom_scan_directory: String::new(),
        has_configured_documents_root: true,
        configured_documents_root: documents.to_string_lossy().into_owned(),
    };
    let request = scan_run_request_standard(
        &configuration,
        &source,
        &scan_run_unsolved_logs_leave_in_place(),
    )
    .unwrap();
    let cancellation = scan_run_cancellation_new();

    // SAFETY: null is the documented representation of an omitted observer.
    let mut no_logs_operation =
        unsafe { scan_run_contract_execute(&request, &cancellation, std::ptr::null()) };
    let no_logs = scan_run_contract_execution_take_result(&mut no_logs_operation);
    assert!(no_logs.has_result, "{}", no_logs.error.message);
    assert_eq!(
        no_logs.result.status,
        ffi::ScanRunContractStatus::NoCrashLogsFound,
        "accepted={:?} logs={}",
        no_logs.result.discovery.accepted_logs,
        no_logs.result.logs.len()
    );
    assert_eq!(
        no_logs.result.discovery.source,
        ffi::ScanRunContractDiscoverySource::Standard
    );

    let cancelled = scan_run_cancellation_new();
    scan_run_cancellation_cancel(&cancelled);
    // SAFETY: null is the documented representation of an omitted observer.
    let mut cancelled_operation =
        unsafe { scan_run_contract_execute(&request, &cancelled, std::ptr::null()) };
    let cancelled_result = scan_run_contract_execution_take_result(&mut cancelled_operation);
    assert_eq!(
        cancelled_result.result.status,
        ffi::ScanRunContractStatus::CancelledBeforeDiscovery
    );
    assert!(!cancelled_result.result.has_discovery);
}

#[test]
fn setup_mapping_preserves_optional_message_checks_updates_and_configuration_issues() {
    let setup = CrashLogScanSetupResult {
        status: "action_required".to_string(),
        checks: vec![classic_scanlog_core::CrashLogScanSetupCheck {
            kind: "game_executable".to_string(),
            state: "failed".to_string(),
            message: "Executable mismatch".to_string(),
            details: vec!["detail".to_string()],
        }],
        path_updates: vec![classic_scanlog_core::CrashLogScanSetupPathUpdate {
            kind: "game_root".to_string(),
            path: PathBuf::from("detected-game"),
        }],
        configuration_issues: vec![
            classic_scanlog_core::ConfigIssue::new(
                "Fallout4.ini".to_string(),
                None,
                "setting".to_string(),
                "0".to_string(),
                "1".to_string(),
                "description".to_string(),
                "warning".to_string(),
            ),
            classic_scanlog_core::ConfigIssue::new(
                "Fallout4Custom.ini".to_string(),
                Some("Display".to_string()),
                "iPresentInterval".to_string(),
                "1".to_string(),
                "0".to_string(),
                "Disable VSync".to_string(),
                "error".to_string(),
            ),
        ],
        actions: vec!["Fix the executable".to_string()],
        fatal_errors: Vec::new(),
        message: Some("Setup needs attention".to_string()),
        rendered_report: "# Setup".to_string(),
    };

    let dto = setup_to_dto(setup);

    assert_eq!(dto.status, "action_required");
    assert!(dto.has_message);
    assert_eq!(dto.message, "Setup needs attention");
    assert_eq!(dto.checks[0].kind, "game_executable");
    assert_eq!(dto.path_updates[0].path, "detected-game");
    assert!(!dto.configuration_issues[0].has_section);
    assert_eq!(dto.configuration_issues[0].section_or_empty, "");
    assert!(dto.configuration_issues[1].has_section);
    assert_eq!(dto.configuration_issues[1].section_or_empty, "Display");
    assert_eq!(dto.configuration_issues[1].file_path, "Fallout4Custom.ini");
    assert_eq!(dto.configuration_issues[1].setting, "iPresentInterval");
    assert_eq!(dto.configuration_issues[1].current_value, "1");
    assert_eq!(dto.configuration_issues[1].recommended_value, "0");
    assert_eq!(dto.configuration_issues[1].description, "Disable VSync");
    assert_eq!(dto.configuration_issues[1].severity, "error");
    assert_eq!(dto.actions, vec!["Fix the executable"]);
}

#[test]
/// Verifies FCX execution preserves structured setup data with host-independent path fixtures.
fn execute_retains_structured_setup_result_data() {
    let temp = tempdir().unwrap();
    let data = temp.path().join("CLASSIC Data");
    write_minimal_scan_yaml_tree(temp.path(), &data);
    let log = temp.path().join("crash-bridge-fcx.log");
    std::fs::write(&log, FIXTURE_LOG_SMALL).unwrap();
    let documents = temp.path().join("Documents");
    std::fs::create_dir_all(&documents).unwrap();
    let game_root = temp.path().join("Fallout4");
    std::fs::create_dir_all(&game_root).unwrap();
    let game_exe = game_root.join("Fallout4.exe");
    std::fs::write(&game_exe, b"not a real PE").unwrap();

    let mut configuration = sample_configuration();
    configuration.installation_root = temp.path().to_string_lossy().into_owned();
    configuration.game_version = "Original".to_string();
    let source = ffi::ScanRunTargetedSourceDto {
        inputs: vec![log.to_string_lossy().into_owned()],
    };
    let setup = ffi::ScanRunSetupContextDto {
        has_game_root: true,
        game_root: game_root.to_string_lossy().into_owned(),
        has_docs_root: true,
        docs_root: documents.to_string_lossy().into_owned(),
        has_game_exe_path: true,
        game_exe_path: game_exe.to_string_lossy().into_owned(),
        has_xse_log_path: false,
        xse_log_path: String::new(),
    };
    let request =
        scan_run_request_targeted_with_fcx(&configuration, &source, &setup).unwrap();

    // SAFETY: null is the documented representation of an omitted observer.
    let mut operation = unsafe {
        scan_run_contract_execute(&request, &scan_run_cancellation_new(), std::ptr::null())
    };
    let execution = scan_run_contract_execution_take_result(&mut operation);

    assert!(execution.has_result, "{}", execution.error.message);
    assert_eq!(
        execution.result.status,
        ffi::ScanRunContractStatus::Completed
    );
    assert!(execution.result.has_setup);
    assert!(!execution.result.setup.status.is_empty());
    assert!(execution.result.has_installed_yaml_data);
    assert_eq!(
        execution.result.installed_yaml_data.local_ignore_state,
        ffi::ScanRunLocalIgnoreYamlDataState::Existing
    );
    assert_eq!(
        execution.result.installed_yaml_data.main.role,
        ffi::ScanRunInstalledYamlDataRole::Main
    );
    assert_eq!(
        execution.result.installed_yaml_data.main.provenance,
        ffi::ScanRunInstalledYamlDataProvenance::Bundled
    );
    assert_eq!(
        execution.result.installed_yaml_data.main.schema_version,
        "2.0"
    );
    assert!(!execution.result.installed_yaml_data.main.sha256.is_empty());
    assert!(execution.result.installed_yaml_data.main.byte_len > 0);
    assert_eq!(
        execution.result.installed_yaml_data.game_file.role,
        ffi::ScanRunInstalledYamlDataRole::Game
    );
    assert!(!execution
        .result
        .installed_yaml_data
        .local_ignore_identity
        .sha256
        .is_empty());
    assert!(
        execution
            .result
            .installed_yaml_data
            .local_ignore_identity
            .byte_len
            > 0
    );
}

#[test]
fn execute_projects_generated_local_ignore_metadata_and_diagnostic_at_the_final_seam() {
    let temp = tempdir().expect("create generated Local Ignore fixture root");
    let data = temp.path().join("CLASSIC Data");
    write_minimal_scan_yaml_tree(temp.path(), &data);
    std::fs::remove_file(data.join("CLASSIC Ignore.yaml"))
        .expect("fixture Local Ignore should be removable");
    let log = temp.path().join("crash-bridge-generated-ignore.log");
    std::fs::write(&log, FIXTURE_LOG_SMALL).expect("write accepted Crash Log fixture");
    let mut configuration = sample_configuration();
    configuration.installation_root = temp.path().to_string_lossy().into_owned();
    configuration.game_version = "Original".to_string();
    let source = ffi::ScanRunTargetedSourceDto {
        inputs: vec![log.to_string_lossy().into_owned()],
    };
    let request = scan_run_request_targeted(&configuration, &source)
        .expect("valid generated-ignore request should be constructible");

    // SAFETY: null is the documented representation of an omitted observer.
    let mut operation = unsafe {
        scan_run_contract_execute(&request, &scan_run_cancellation_new(), std::ptr::null())
    };
    let execution = scan_run_contract_execution_take_result(&mut operation);

    assert!(execution.has_result, "{}", execution.error.message);
    assert!(!execution.has_error);
    assert!(execution.result.has_installed_yaml_data);
    assert_eq!(
        execution.result.installed_yaml_data.local_ignore_state,
        ffi::ScanRunLocalIgnoreYamlDataState::Generated
    );
    assert!(
        execution
            .result
            .installed_yaml_data
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.kind
                == ffi::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated)
    );
    assert!(
        execution
            .result
            .installed_yaml_data
            .local_ignore_identity
            .byte_len
            > 0
    );
}

#[test]
fn cxx_continuation_resumes_retained_recovery_once_and_projects_typed_replay_failure() {
    let temp = tempdir().expect("create Local Ignore recovery fixture root");
    let data = temp.path().join("CLASSIC Data");
    write_minimal_scan_yaml_tree(temp.path(), &data);
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: [unterminated";
    let ignore_path = data.join("CLASSIC Ignore.yaml");
    std::fs::write(&ignore_path, malformed_ignore).expect("write malformed Local Ignore fixture");
    let log = temp.path().join("crash-bridge-recovery.log");
    std::fs::write(&log, FIXTURE_LOG_SMALL).expect("write accepted Crash Log fixture");
    let mut configuration = sample_configuration();
    configuration.installation_root = temp.path().to_string_lossy().into_owned();
    configuration.game_version = "Original".to_string();
    let source = ffi::ScanRunTargetedSourceDto {
        inputs: vec![log.to_string_lossy().into_owned()],
    };
    let request = scan_run_request_targeted(&configuration, &source)
        .expect("valid recovery request should be constructible");

    // SAFETY: null is the documented representation of an omitted observer.
    let mut initial_operation = unsafe {
        scan_run_contract_execute(&request, &scan_run_cancellation_new(), std::ptr::null())
    };
    assert!(scan_run_contract_execution_has_continuation(
        &initial_operation
    ));
    let initial = scan_run_contract_execution_take_result(&mut initial_operation);
    assert!(initial.has_result, "{}", initial.error.message);
    assert_eq!(
        initial.result.status,
        ffi::ScanRunContractStatus::LocalIgnoreRecoveryRequired
    );
    assert_eq!(
        initial.result.installed_yaml_data.local_ignore_state,
        ffi::ScanRunLocalIgnoreYamlDataState::RecoveryRequired
    );
    let retained_discovery = initial.result.discovery.accepted_logs.clone();
    let retained_main_identity = initial.result.installed_yaml_data.main.sha256.clone();
    let retained_game_identity = initial.result.installed_yaml_data.game_file.sha256.clone();
    let continuation = scan_run_contract_execution_take_continuation(&mut initial_operation)
        .expect("recovery result must expose its opaque continuation");

    // CXX enums can carry a non-exhaustive sentinel; rejecting it must not claim retained work.
    let invalid_decision = ffi::ScanRunLocalIgnoreRecoveryDecision { repr: u8::MAX };
    // SAFETY: null is the documented representation of an omitted observer.
    let invalid_error = unsafe {
        scan_run_continuation_resume(
            &continuation,
            invalid_decision,
            &scan_run_cancellation_new(),
            std::ptr::null(),
        )
    }
    .err()
    .expect("an unknown recovery decision must be rejected");
    assert!(invalid_error.contains("unsupported ScanRunLocalIgnoreRecoveryDecision discriminant"));

    // The resumed operation must use the retained snapshot rather than reading the now-invalid file.
    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        b"invalid: [unterminated",
    )
    .expect("mutate selected Main YAML after pause");
    // SAFETY: null is the documented representation of an omitted observer.
    let mut resumed_operation = unsafe {
        scan_run_continuation_resume(
            &continuation,
            ffi::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
            &scan_run_cancellation_new(),
            std::ptr::null(),
        )
    }
    .expect("the explicit recovery decision must resume retained work");
    let resumed = scan_run_contract_execution_take_result(&mut resumed_operation);
    assert!(resumed.has_result, "{}", resumed.error.message);
    assert_eq!(resumed.result.status, ffi::ScanRunContractStatus::Completed);
    assert_eq!(
        resumed.result.discovery.accepted_logs,
        retained_discovery
    );
    assert_eq!(
        resumed.result.installed_yaml_data.local_ignore_state,
        ffi::ScanRunLocalIgnoreYamlDataState::ProceedWithoutIgnore
    );
    assert_eq!(
        resumed.result.installed_yaml_data.main.sha256,
        retained_main_identity
    );
    assert_eq!(
        resumed.result.installed_yaml_data.game_file.sha256,
        retained_game_identity
    );
    assert_eq!(
        std::fs::read(&ignore_path).expect("read malformed Local Ignore after resume"),
        malformed_ignore
    );

    // SAFETY: null is the documented representation of an omitted observer.
    let mut replay_operation = unsafe {
        scan_run_continuation_resume(
            &continuation,
            ffi::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
            &scan_run_cancellation_new(),
            std::ptr::null(),
        )
    }
    .expect("the explicit recovery decision must reach the typed replay envelope");
    let replay = scan_run_contract_execution_take_result(&mut replay_operation);
    assert!(!replay.has_result);
    assert!(!replay.has_error);
    assert!(replay.has_resume_error);
    assert_eq!(
        replay.resume_error.kind,
        ffi::ScanRunContractResumeErrorKind::ContinuationConsumed
    );
    assert_eq!(replay.resume_error.code, "scan_run_continuation_consumed");
}

/// Reset backup and replacement failures retain stable CXX path and publication metadata.
#[test]
fn cxx_resume_operational_errors_preserve_every_stable_reset_outcome_field() {
    for (error, expected_kind, expected_code) in [
        (
            contract::ResumeError::LocalIgnoreResetBackupFailure(
                contract::LocalIgnoreResetFailure {
                    path: PathBuf::from("C:/backup"),
                    stage: None,
                    message: "backup failed".to_string(),
                },
            ),
            ffi::ScanRunContractResumeErrorKind::LocalIgnoreResetBackupFailure,
            "local_ignore_reset_backup_failure",
        ),
        (
            contract::ResumeError::LocalIgnoreResetReplacementFailure(
                contract::LocalIgnoreResetFailure {
                    path: PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml"),
                    stage: Some(contract::LocalIgnoreResetFailureStage::Publish),
                    message: "replacement failed".to_string(),
                },
            ),
            ffi::ScanRunContractResumeErrorKind::LocalIgnoreResetReplacementFailure,
            "local_ignore_reset_replacement_failure",
        ),
    ] {
        let projected = super::resume_error_to_dto(error);
        assert_eq!(projected.kind, expected_kind);
        assert_eq!(projected.code, expected_code);
        assert!(projected.has_path);
        if expected_kind
            == ffi::ScanRunContractResumeErrorKind::LocalIgnoreResetReplacementFailure
        {
            assert!(projected.has_stage);
            assert_eq!(
                projected.stage,
                ffi::ScanRunLocalIgnoreResetFailureStage::Publish
            );
        }
    }
}

/// Visible replacement durability uncertainty retains the complete CXX recovery receipt.
#[test]
fn cxx_resume_durability_unknown_preserves_recovery_receipt() {
    let expected = shared_reset_outcomes();
    let malformed_identity =
        classic_config_core::YamlDataContentIdentity::from_bytes(b"malformed");
    let backup_identity = malformed_identity.clone();
    let replacement_identity =
        classic_config_core::YamlDataContentIdentity::from_bytes(b"defaults");
    let projected = super::resume_error_to_dto(
        contract::ResumeError::LocalIgnoreResetDurabilityUnknown(Box::new(
            contract::LocalIgnoreResetDurabilityUnknownError {
                path: PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml"),
                backup_path: PathBuf::from("C:/CLASSIC/backups/local-ignore.bak"),
                malformed_identity: malformed_identity.clone(),
                backup_identity: backup_identity.clone(),
                replacement_identity: replacement_identity.clone(),
                message: "replacement visible; durability unknown".to_string(),
            },
        )),
    );

    assert_eq!(
        projected.kind,
        ffi::ScanRunContractResumeErrorKind::LocalIgnoreResetDurabilityUnknown
    );
    assert_eq!(
        projected.code,
        expected["durabilityUnknownCode"]
            .as_str()
            .expect("shared durability-unknown code should be a string")
    );
    assert!(projected.has_path);
    assert!(projected.has_backup_path);
    assert!(projected.has_durability_receipt);
    assert!(!projected.has_stage);
    assert_eq!(
        projected.malformed_identity.sha256,
        malformed_identity.sha256_hex()
    );
    assert_eq!(
        projected.backup_identity.sha256,
        backup_identity.sha256_hex()
    );
    assert_eq!(
        projected.replacement_identity.sha256,
        replacement_identity.sha256_hex()
    );
}

#[test]
fn execute_preserves_typed_intake_failure_stage_and_relevant_path() {
    let temp = tempdir().unwrap();
    let log = temp.path().join("crash-bridge-intake-failure.log");
    std::fs::write(&log, FIXTURE_LOG_SMALL).unwrap();
    let missing_data = temp.path().join("missing-data");
    let mut configuration = sample_configuration();
    configuration.installation_root = missing_data.to_string_lossy().into_owned();
    let source = ffi::ScanRunTargetedSourceDto {
        inputs: vec![log.to_string_lossy().into_owned()],
    };
    let request = scan_run_request_targeted(&configuration, &source).unwrap();

    // SAFETY: null is the documented representation of an omitted observer.
    let mut operation = unsafe {
        scan_run_contract_execute(&request, &scan_run_cancellation_new(), std::ptr::null())
    };
    let execution = scan_run_contract_execution_take_result(&mut operation);

    assert!(!execution.has_result);
    assert!(execution.has_error);
    assert_eq!(
        execution.error.stage,
        ffi::ScanRunContractInfrastructureErrorStage::Intake
    );
    assert!(execution.error.has_path);
    assert_eq!(
        execution.error.path,
        missing_data.join("CLASSIC Data").to_string_lossy()
    );
}

// --- Vocabulary projection ------------------------------------------------
//
// Expectations are derived from `classic-scanlog-core`, never restated. A
// hand-written array here would be another copy of the vocabulary: it would
// pass against a bridge that had already drifted, because it would only be
// comparing this file's copy against itself. Iterating `VARIANTS` also means a
// new variant is covered without anyone remembering to extend these tests.

#[test]
/// Every projected CXX variant resolves back to the core Display Label.
fn every_scan_run_twin_projects_its_core_display_label() {
    for variant in contract::InstalledYamlDataRunDiagnosticKind::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            scan_run_installed_yaml_data_diagnostic_kind_label(
                map_installed_yaml_data_diagnostic_kind(variant)
            ),
            variant.label(),
        );
    }

    for variant in contract::LocalIgnoreRunState::VARIANTS.iter().copied() {
        assert_eq!(
            scan_run_local_ignore_yaml_data_state_label(map_local_ignore_yaml_data_state(variant)),
            variant.label(),
        );
    }
}

#[test]
/// No scan-run Display Label reaches C++ empty.
fn no_scan_run_display_label_reaches_cxx_empty() {
    // The label functions fall back to an empty string for a value the forward
    // projection cannot produce. That fallback must stay unreachable for every
    // real variant, because an empty label is exactly the "variant that renders
    // as nothing" the naming contract exists to prevent.
    for variant in contract::InstalledYamlDataRunDiagnosticKind::VARIANTS
        .iter()
        .copied()
    {
        assert!(
            !scan_run_installed_yaml_data_diagnostic_kind_label(
                map_installed_yaml_data_diagnostic_kind(variant)
            )
            .is_empty()
        );
    }

    for variant in contract::LocalIgnoreRunState::VARIANTS.iter().copied() {
        assert!(
            !scan_run_local_ignore_yaml_data_state_label(map_local_ignore_yaml_data_state(variant))
                .is_empty()
        );
    }
}

/// Asserts one enum's CXX label projection agrees with the core, for every variant.
///
/// Written once and applied per enum because the four run-owned enums differ
/// only in their types: repeating the loop four times would be four chances to
/// paste the wrong `label_of` beside the right `project`, which is the class of
/// mistake a test cannot catch about itself.
///
/// Both clauses matter and neither implies the other. The equality is the real
/// check. The non-empty assertion pins the `display_label` `""` fallback as
/// unreachable for a real variant — an empty label is exactly the "variant that
/// renders as nothing" the naming contract exists to prevent, and core
/// conformance guarantees it only on the core side of the seam.
fn assert_cxx_labels_match_the_core<Core, Cxx>(project: fn(Core) -> Cxx, label_of: fn(Cxx) -> String)
where
    Core: Vocabulary,
    Cxx: Copy + PartialEq,
{
    for variant in Core::VARIANTS.iter().copied() {
        let label = label_of(project(variant));
        assert_eq!(label, variant.label());
        assert!(!label.is_empty());
    }
}

#[test]
/// Every enum the run crate owns outright projects its core Display Label to C++.
///
/// Separate from the twin test above because these four have no counterpart to
/// delegate to: the run crate is the single definition site for their prose, so
/// what this pins is only that the bridge relays it unchanged.
fn every_scan_run_run_owned_enum_projects_its_core_display_label() {
    assert_cxx_labels_match_the_core(map_log_disposition, scan_run_log_disposition_label);
    assert_cxx_labels_match_the_core(map_log_failure_stage, scan_run_log_failure_stage_label);
    assert_cxx_labels_match_the_core(
        map_infrastructure_error_stage,
        scan_run_infrastructure_error_stage_label,
    );
    // A twin of the shared durable publication stage vocabulary rather than
    // run-owned, but it needs no separate twin assertion here: the core-side
    // delegation is what `classic-scanlog-core` proves, and all this seam owes
    // is that the bridge relays whatever the core settled on.
    assert_cxx_labels_match_the_core(
        map_reset_failure_stage,
        scan_run_local_ignore_reset_failure_stage_label,
    );
}

#[test]
/// The scanner-local provenance mirror projects the configuration Display Label.
///
/// `InstalledYamlDataProvenance` is not a twin — the run contract reuses the
/// configuration type outright rather than declaring its own. What is
/// scanner-local is only the *CXX mirror*, because `#[cxx::bridge]` namespaces
/// its shared enums per module, so `classic::config::installed_yaml_data_provenance_label`
/// cannot accept the value a scan-run result carries. Node and Python have no
/// such split and needed no second entry point; this one exists so a C++
/// frontend resolves all seven scan-run labels the same way rather than
/// hand-mapping one mirror onto another.
fn the_scanner_provenance_mirror_projects_its_core_display_label() {
    assert_cxx_labels_match_the_core(
        map_installed_yaml_data_provenance,
        scan_run_installed_yaml_data_provenance_label,
    );
}

#[test]
/// A fabricated CXX enum value yields nothing rather than an invented label.
fn an_out_of_range_scan_run_cxx_enum_value_yields_an_empty_display_label() {
    // CXX shared enums are open at the FFI boundary: C++ can hand back any
    // `u8`. The bridge never produces one of these, but returning some other
    // variant's label - or a hand-written "unknown" string - would put
    // vocabulary back in the adapter, which is what this work removes.
    assert_eq!(
        scan_run_installed_yaml_data_diagnostic_kind_label(
            ffi::ScanRunInstalledYamlDataDiagnosticKind { repr: u8::MAX }
        ),
        ""
    );
    // Both twins, because both are open at the boundary. Covering only one
    // would leave the other free to grow a fallback that invents a label.
    assert_eq!(
        scan_run_local_ignore_yaml_data_state_label(ffi::ScanRunLocalIgnoreYamlDataState {
            repr: u8::MAX
        }),
        ""
    );
    // Every enum with a label projection, for the same reason: each one is a
    // separate `display_label` call site, and each could independently grow a
    // fallback that invents a label instead of rendering nothing.
    assert_eq!(
        scan_run_log_disposition_label(ffi::ScanRunContractLogDisposition { repr: u8::MAX }),
        ""
    );
    assert_eq!(
        scan_run_log_failure_stage_label(ffi::ScanRunContractLogFailureStage { repr: u8::MAX }),
        ""
    );
    assert_eq!(
        scan_run_infrastructure_error_stage_label(ffi::ScanRunContractInfrastructureErrorStage {
            repr: u8::MAX
        }),
        ""
    );
    assert_eq!(
        scan_run_local_ignore_reset_failure_stage_label(ffi::ScanRunLocalIgnoreResetFailureStage {
            repr: u8::MAX
        }),
        ""
    );
    assert_eq!(
        scan_run_installed_yaml_data_provenance_label(ffi::ScanRunInstalledYamlDataProvenance {
            repr: u8::MAX
        }),
        ""
    );
}

// --- Display Content flattening --------------------------------------------------------
//
// These do not pin wording. Wording is pinned once, in `classic-scan-presentation`, and
// asserting it again here would mean one rewording produced two diffs and two chances to
// disagree. What these prove is narrower: that a typed segment reaches C++ with its payload
// in the field its kind selects, that the fields the kind does not select stay empty, and
// that a count's noun is the one Rust already agreed with the value.

/// Builds a line carrying one segment of every kind, in taxonomy order.
///
/// `Name` is included even though no render path emits one yet: the taxonomy is fixed for
/// this version, so the flattening for a kind that arrives later is settled now rather than
/// bolted on then.
fn every_segment_kind() -> DisplayLine {
    DisplayLine {
        severity: DisplaySeverity::Warning,
        segments: vec![
            DisplaySegment::Text("fixed prose"),
            DisplaySegment::Label("a display label"),
            DisplaySegment::Count {
                value: 1,
                noun: "log",
            },
            DisplaySegment::Path(PathBuf::from("crash-é.log")),
            DisplaySegment::Name("a domain name".to_string()),
            DisplaySegment::Emphasis("set apart".to_string()),
        ],
    }
}

#[test]
/// Every segment kind crosses with its payload in the field the tag selects.
fn each_display_segment_kind_flattens_into_exactly_its_own_fields() {
    let lines = display_lines_to_dto(&[every_segment_kind()]);
    assert_eq!(lines.len(), 1);
    let line = &lines[0];
    assert_eq!(line.severity, ffi::ScanRunDisplaySeverity::Warning);
    assert_eq!(line.segments.len(), 6, "segments must not be dropped");

    let expected = [
        (
            ffi::ScanRunDisplaySegmentKind::Text,
            "fixed prose",
            "",
            0_u64,
        ),
        (
            ffi::ScanRunDisplaySegmentKind::Label,
            "a display label",
            "",
            0,
        ),
        // The noun rides in `text` because CXX has no payload-carrying enum to put it in.
        (ffi::ScanRunDisplaySegmentKind::Count, "log", "", 1),
        (ffi::ScanRunDisplaySegmentKind::Path, "", "crash-é.log", 0),
        (
            ffi::ScanRunDisplaySegmentKind::Name,
            "a domain name",
            "",
            0,
        ),
        (
            ffi::ScanRunDisplaySegmentKind::Emphasis,
            "set apart",
            "",
            0,
        ),
    ];
    for (index, (kind, text, path, count)) in expected.into_iter().enumerate() {
        let segment = &line.segments[index];
        assert_eq!(segment.kind, kind, "segment {index} changed kind");
        assert_eq!(segment.text, text, "segment {index} text");
        assert_eq!(segment.path, path, "segment {index} path");
        assert_eq!(segment.count, count, "segment {index} count");
    }
}

#[test]
/// Segments keep the order Rust put them in, so a frontend can concatenate blindly.
fn display_segments_cross_in_reading_order() {
    let lines = display_lines_to_dto(&[every_segment_kind()]);
    let kinds: Vec<_> = lines[0]
        .segments
        .iter()
        .map(|segment| segment.kind)
        .collect();
    assert_eq!(
        kinds,
        vec![
            ffi::ScanRunDisplaySegmentKind::Text,
            ffi::ScanRunDisplaySegmentKind::Label,
            ffi::ScanRunDisplaySegmentKind::Count,
            ffi::ScanRunDisplaySegmentKind::Path,
            ffi::ScanRunDisplaySegmentKind::Name,
            ffi::ScanRunDisplaySegmentKind::Emphasis,
        ]
    );
}

#[test]
/// A count crosses with the noun Rust resolved, not one the adapter could re-derive.
fn a_count_crosses_with_the_noun_that_agrees_with_its_value() {
    let one = DisplayLine {
        severity: DisplaySeverity::Info,
        segments: vec![DisplaySegment::Count {
            value: 1,
            noun: "log",
        }],
    };
    let many = DisplayLine {
        severity: DisplaySeverity::Info,
        segments: vec![DisplaySegment::Count {
            value: 0,
            noun: "logs",
        }],
    };
    let lines = display_lines_to_dto(&[one, many]);
    assert_eq!(lines[0].segments[0].count, 1);
    assert_eq!(lines[0].segments[0].text, "log");
    assert_eq!(lines[1].segments[0].count, 0);
    assert_eq!(lines[1].segments[0].text, "logs");
}

#[test]
/// Every severity has a distinct CXX twin, so no line arrives more or less grave.
fn every_display_severity_maps_to_its_own_cxx_twin() {
    for (core, expected) in [
        (DisplaySeverity::Info, ffi::ScanRunDisplaySeverity::Info),
        (DisplaySeverity::Notice, ffi::ScanRunDisplaySeverity::Notice),
        (
            DisplaySeverity::Warning,
            ffi::ScanRunDisplaySeverity::Warning,
        ),
        (
            DisplaySeverity::Failure,
            ffi::ScanRunDisplaySeverity::Failure,
        ),
        (
            DisplaySeverity::Success,
            ffi::ScanRunDisplaySeverity::Success,
        ),
    ] {
        let lines = display_lines_to_dto(&[DisplayLine {
            severity: core,
            segments: Vec::new(),
        }]);
        assert_eq!(lines[0].severity, expected);
    }
}

#[test]
/// Every event kind reaches C++ already carrying what Rust says about it.
fn every_event_crosses_with_the_lines_core_rendered_for_it() {
    let log = contract::LogEvent {
        discovery_index: 0,
        crash_log: PathBuf::from("one.log"),
        completed: 0,
        total: 2,
    };
    let events = [
        contract::Event::DiscoveryCompleted(CrashLogScanDiscoveryResult {
            source: CrashLogScanDiscoverySource::Targeted,
            accepted_logs: vec![PathBuf::from("one.log")],
            rejected_inputs: vec![classic_scanlog_core::CrashLogScanRejectedInput {
                path: PathBuf::from("rejected.log"),
                reason: "unsupported".to_string(),
            }],
            searched_locations: Vec::new(),
        }),
        contract::Event::EffectiveConcurrencySelected {
            effective_concurrency: 3,
        },
        contract::Event::LogQueued(log.clone()),
        contract::Event::LogStarted(log.clone()),
        contract::Event::LogPhase {
            log: log.clone(),
            phase: ScanProgressPhase::Analyze,
        },
        contract::Event::LogFinished {
            log: log.clone(),
            disposition: contract::LogDisposition::Succeeded,
        },
    ];

    for event in events {
        let expected = display_lines_to_dto(&render_event(&event));
        let dto = event_to_dto(event);
        assert!(
            !dto.display_lines.is_empty(),
            "an event reached C++ with nothing to say"
        );
        assert_display_lines_match(&dto.display_lines, &expected);
    }
}

#[test]
/// A discovery that refused inputs states the refusal on its own line.
///
/// This is the one event that renders more than one line, so it is what proves the field is
/// a sequence rather than a single sentence in disguise.
fn a_discovery_with_rejections_crosses_as_more_than_one_line() {
    let event = contract::Event::DiscoveryCompleted(CrashLogScanDiscoveryResult {
        source: CrashLogScanDiscoverySource::Targeted,
        accepted_logs: vec![PathBuf::from("one.log")],
        rejected_inputs: vec![classic_scanlog_core::CrashLogScanRejectedInput {
            path: PathBuf::from("rejected.log"),
            reason: "unsupported".to_string(),
        }],
        searched_locations: Vec::new(),
    });
    assert!(event_to_dto(event).display_lines.len() > 1);
}

#[test]
/// A terminal result crosses with the lines Rust rendered for it.
fn a_run_result_envelope_carries_the_lines_core_rendered() {
    let build = || contract::RunResult {
        status: CrashLogScanRunStatus::Completed,
        discovery: None,
        setup: None,
        installed_yaml_data: None,
        effective_concurrency: Some(2),
        message: Some("completed".to_string()),
        total: 1,
        succeeded: 1,
        failed: 0,
        cancelled: 0,
        logs: Vec::new(),
        continuation: None,
    };
    let expected = display_lines_to_dto(&render_run_result(&build()));
    let envelope = success_execution_result_dto(build());

    assert!(envelope.has_result);
    assert_display_lines_match(&envelope.display_lines, &expected);
}

#[test]
/// An infrastructure failure crosses with the lines Rust rendered for it.
fn an_infrastructure_error_envelope_carries_the_lines_core_rendered() {
    let build = || contract::InfrastructureError {
        stage: contract::InfrastructureErrorStage::FormIdDatabaseAccess,
        message: "database unavailable".to_string(),
        path: Some(PathBuf::from("database.db")),
    };
    let expected = display_lines_to_dto(&render_infrastructure_error(&build()));
    let envelope = infrastructure_execution_result_dto(build());

    assert!(envelope.has_error);
    assert_display_lines_match(&envelope.display_lines, &expected);
}

/// Builds one resume failure of every kind, so no variant reaches C++ untested.
///
/// `Infrastructure` is deliberately absent: `execution_from_resume_result` routes it into the
/// infrastructure arm rather than the resume arm, and
/// [`an_infrastructure_error_envelope_carries_the_lines_core_rendered`] covers that path.
fn every_resume_failure() -> Vec<contract::ResumeError> {
    let identity = classic_config_core::YamlDataContentIdentity::from_bytes(b"malformed");
    vec![
        contract::ResumeError::ContinuationConsumed,
        contract::ResumeError::LocalIgnoreResetConflict(contract::LocalIgnoreResetConflictError {
            expected_identity: identity.clone(),
            actual_identity: Some(classic_config_core::YamlDataContentIdentity::from_bytes(
                b"changed",
            )),
            backup_path: Some(PathBuf::from("C:/CLASSIC/backups/local-ignore.bak")),
        }),
        contract::ResumeError::LocalIgnoreResetBackupFailure(contract::LocalIgnoreResetFailure {
            path: PathBuf::from("C:/backup"),
            stage: None,
            message: "backup failed".to_string(),
        }),
        contract::ResumeError::LocalIgnoreResetReplacementFailure(
            contract::LocalIgnoreResetFailure {
                path: PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml"),
                stage: Some(contract::LocalIgnoreResetFailureStage::Publish),
                message: "replacement failed".to_string(),
            },
        ),
        contract::ResumeError::LocalIgnoreResetDurabilityUnknown(Box::new(
            contract::LocalIgnoreResetDurabilityUnknownError {
                path: PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml"),
                backup_path: PathBuf::from("C:/CLASSIC/backups/local-ignore.bak"),
                malformed_identity: identity.clone(),
                backup_identity: identity.clone(),
                replacement_identity: classic_config_core::YamlDataContentIdentity::from_bytes(
                    b"defaults",
                ),
                message: "replacement visible; durability unknown".to_string(),
            },
        )),
    ]
}

#[test]
/// Every resume failure crosses with the lines Rust rendered for it, and keeps its stable code.
///
/// The code stays on the DTO because it is machine-facing identity a consumer matches on; it
/// stays out of the rendered lines because a sentence is not where a code belongs.
///
/// Every variant, not just the simplest, because each carries different retained facts — a
/// conflict's two identities, a failure's publication stage, a durability receipt's three
/// hashes — and a frontend that renders nothing but these lines has no second route to them.
fn every_resume_error_envelope_carries_the_lines_core_rendered_without_the_code() {
    for error in every_resume_failure() {
        let code = error.kind().as_str();
        let expected = display_lines_to_dto(&render_resume_error(&error));
        let execution = execution_from_resume_result(Err(error));

        assert!(execution.result.has_resume_error, "{code} lost its payload");
        assert_eq!(execution.result.resume_error.code, code);
        assert!(
            !execution.result.display_lines.is_empty(),
            "{code} reached C++ with nothing to say"
        );
        assert_display_lines_match(&execution.result.display_lines, &expected);
        for line in &execution.result.display_lines {
            for segment in &line.segments {
                assert_ne!(
                    segment.text, code,
                    "the stable resume error code reached a sentence"
                );
            }
        }
    }
}

#[test]
/// A moved-from envelope says nothing, rather than repeating what was already taken.
fn an_emptied_execution_envelope_carries_no_display_lines() {
    assert!(empty_execution_result_dto().display_lines.is_empty());
}

/// Asserts two flattened line sequences are the same line for line and segment for segment.
///
/// Written out rather than derived, because the CXX shared structs implement no equality.
fn assert_display_lines_match(
    actual: &[ffi::ScanRunDisplayLine],
    expected: &[ffi::ScanRunDisplayLine],
) {
    assert_eq!(actual.len(), expected.len(), "line count changed");
    for (index, (actual_line, expected_line)) in actual.iter().zip(expected).enumerate() {
        assert_eq!(
            actual_line.severity, expected_line.severity,
            "line {index} lost the severity core gave it"
        );
        assert_eq!(
            actual_line.segments.len(),
            expected_line.segments.len(),
            "line {index} changed segment count"
        );
        for (position, (actual_segment, expected_segment)) in actual_line
            .segments
            .iter()
            .zip(&expected_line.segments)
            .enumerate()
        {
            assert_eq!(
                actual_segment.kind, expected_segment.kind,
                "line {index} segment {position} kind"
            );
            assert_eq!(
                actual_segment.text, expected_segment.text,
                "line {index} segment {position} text"
            );
            assert_eq!(
                actual_segment.path, expected_segment.path,
                "line {index} segment {position} path"
            );
            assert_eq!(
                actual_segment.count, expected_segment.count,
                "line {index} segment {position} count"
            );
        }
    }
}
