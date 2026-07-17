use super::*;
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
        yaml_dir_root: "root".to_string(),
        yaml_dir_data: "data".to_string(),
        game: "Fallout4".to_string(),
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

fn write_minimal_scan_yaml_tree(root: &std::path::Path, data: &std::path::Path) {
    std::fs::create_dir_all(data.join("databases")).unwrap();
    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        concat!(
            "CLASSIC_Info:\n",
            "  version: \"v9.1.0\"\n",
            "  version_date: \"2026-06-30\"\n",
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
        root.join("CLASSIC Ignore.yaml"),
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
        effective_concurrency: Some(2),
        message: Some("completed with failures".to_string()),
        total: 1,
        succeeded: 0,
        failed: 1,
        cancelled: 0,
        logs: vec![log],
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
    let execution = unsafe { scan_run_contract_execute(&request, &cancellation, std::ptr::null()) };

    assert!(execution.has_result);
    assert!(!execution.has_error);
    assert_eq!(
        execution.result.status,
        ffi::ScanRunContractStatus::NoCrashLogsFound
    );
    assert!(execution.result.has_discovery);
    assert_eq!(execution.result.discovery.rejected_inputs.len(), 2);
    assert!(execution.result.logs.is_empty());
}

#[test]
fn request_construction_rejects_invalid_values_and_preserves_empty_fcx_context() {
    let mut invalid_game = sample_configuration();
    invalid_game.game = "UnknownGame".to_string();
    assert!(
        scan_run_request_targeted(&invalid_game, &sample_targeted_source()).is_err(),
        "unknown games must not reach the tagged core request"
    );
    assert!(scan_run_unsolved_logs_move_to_custom("  ").is_err());

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
    let execution = unsafe {
        scan_run_contract_execute(&request, &scan_run_cancellation_new(), std::ptr::null())
    };

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
    configuration.yaml_dir_root = temp.path().to_string_lossy().into_owned();
    configuration.yaml_dir_data = temp
        .path()
        .join("CLASSIC Data")
        .to_string_lossy()
        .into_owned();
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
    let no_logs = unsafe { scan_run_contract_execute(&request, &cancellation, std::ptr::null()) };
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
    let cancelled_result =
        unsafe { scan_run_contract_execute(&request, &cancelled, std::ptr::null()) };
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
    configuration.yaml_dir_root = temp.path().to_string_lossy().into_owned();
    configuration.yaml_dir_data = data.to_string_lossy().into_owned();
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
    let execution = unsafe {
        scan_run_contract_execute(&request, &scan_run_cancellation_new(), std::ptr::null())
    };

    assert!(execution.has_result, "{}", execution.error.message);
    assert_eq!(
        execution.result.status,
        ffi::ScanRunContractStatus::Completed
    );
    assert!(execution.result.has_setup);
    assert!(!execution.result.setup.status.is_empty());
}

#[test]
fn execute_preserves_typed_intake_failure_stage_and_relevant_path() {
    let temp = tempdir().unwrap();
    let log = temp.path().join("crash-bridge-intake-failure.log");
    std::fs::write(&log, FIXTURE_LOG_SMALL).unwrap();
    let missing_data = temp.path().join("missing-data");
    let mut configuration = sample_configuration();
    configuration.yaml_dir_root = temp.path().to_string_lossy().into_owned();
    configuration.yaml_dir_data = missing_data.to_string_lossy().into_owned();
    let source = ffi::ScanRunTargetedSourceDto {
        inputs: vec![log.to_string_lossy().into_owned()],
    };
    let request = scan_run_request_targeted(&configuration, &source).unwrap();

    // SAFETY: null is the documented representation of an omitted observer.
    let execution = unsafe {
        scan_run_contract_execute(&request, &scan_run_cancellation_new(), std::ptr::null())
    };

    assert!(!execution.has_result);
    assert!(execution.has_error);
    assert_eq!(
        execution.error.stage,
        ffi::ScanRunContractInfrastructureErrorStage::Intake
    );
    assert!(execution.error.has_path);
    assert_eq!(execution.error.path, missing_data.to_string_lossy());
}
