use std::path::PathBuf;

use classic_config_core::{
    InstalledYamlDataProvenance, InstalledYamlDataRole, YamlDataContentIdentity,
};
use classic_scan_presentation::{
    DisplayLine, DisplaySegment, DisplaySeverity, RecoveryDecisionDescription, RecoveryPrompt,
    render_event, render_infrastructure_error, render_local_ignore_recovery, render_resume_error,
    render_run_result,
};
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanRejectedInput,
    CrashLogScanRunStatus, CrashLogScanSetupCheck, CrashLogScanSetupPathUpdate,
    CrashLogScanSetupResult, ScanProgressPhase,
};
use classic_vocabulary::Vocabulary;
use pyo3::Py;
use pyo3::PyResult;
use pyo3::Python;
use pyo3::types::PyAnyMethods;

use super::{
    PyScanRunConfiguration, PyScanRunLocalIgnoreRecoveryDecision, configuration_to_core,
    display_lines_to_py, display_segment_to_py, display_severity_to_string, disposition_to_string,
    event_to_py, failure_execution, local_ignore_recovery_decision_to_py, recovery_prompt_to_py,
    success_execution,
    infrastructure_error_stage_to_string, infrastructure_error_to_py,
    installed_yaml_data_diagnostic_kind_to_string, installed_yaml_data_provenance_to_string,
    installed_yaml_data_role_to_string, local_ignore_state_to_string, log_failure_stage_to_string,
    log_result_to_py, phase_to_string, reset_failure_stage_to_string, run_result_to_py,
    run_status_to_string, scan_run_infrastructure_error_stage_label,
    scan_run_installed_yaml_data_diagnostic_kind_label,
    scan_run_local_ignore_reset_failure_stage_label, scan_run_local_ignore_yaml_data_state_label,
    scan_run_log_disposition_label, scan_run_log_failure_stage_label, scan_run_resume_error_to_py,
    setup_to_py, ScanRunLocalIgnoreResetDurabilityUnknownError,
    ScanRunLocalIgnoreResetReplacementError,
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

/// Loads the shared reset-outcome expectations used by Python exception mapping tests.
fn shared_reset_outcomes() -> serde_json::Value {
    serde_json::from_str::<serde_json::Value>(SHARED_SCAN_RUN_MANIFEST)
        .expect("shared scan-run manifest should deserialize")["fixtures"]["installedYamlData"]
        ["resetOutcomes"]
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
    // Derived from `VARIANTS` like everything below it. The expected string was
    // already the core's own token rather than a second spelling of it; the
    // variant list used to be written out here because the run status had no
    // `VARIANTS` to iterate, and adopting the Vocabulary contract is what let
    // that hardcoded array go.
    for variant in <CrashLogScanRunStatus as Vocabulary>::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            run_status_to_string(variant),
            variant.as_str(),
            "the run surface must publish the core's own token",
        );
    }

    // Derived from `VARIANTS` for the same reason as the twins further down,
    // and the reason applies even though these two enums are not twins: the
    // strings they publish are the run crate's own, and this surface was the
    // second place they were written down.
    for variant in contract::LogDisposition::VARIANTS.iter().copied() {
        assert_eq!(
            disposition_to_string(variant),
            variant.as_str(),
            "the run surface must publish the core's own token",
        );
    }
    for variant in contract::LogFailureStage::VARIANTS.iter().copied() {
        assert_eq!(
            log_failure_stage_to_string(variant),
            variant.as_str(),
            "the run surface must publish the core's own token",
        );
    }
    for variant in contract::InfrastructureErrorStage::VARIANTS.iter().copied() {
        assert_eq!(
            infrastructure_error_stage_to_string(variant),
            variant.as_str(),
            "the run surface must publish the core's own token",
        );
    }
    for variant in contract::LocalIgnoreResetFailureStage::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            variant.as_str(),
            reset_failure_stage_to_string(variant),
            "the run surface must publish the core's own token",
        );
    }

    // These two were the arrays the note below warns about, comparing this file's
    // copy of the vocabulary against itself. Both enums have adopted the contract,
    // so the expectation now comes from the core and the literal spellings are
    // pinned once, in the crate that owns them.
    for variant in <ScanProgressPhase as Vocabulary>::VARIANTS.iter().copied() {
        assert_eq!(
            phase_to_string(variant),
            variant.as_str(),
            "the run surface must publish the core's own token",
        );
    }

    for variant in <InstalledYamlDataRole as Vocabulary>::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            installed_yaml_data_role_to_string(variant),
            variant.as_str(),
            "the run surface must publish the core's own token",
        );
    }
    // Derived from the core, not restated. A hand-written array here would pass
    // just as happily against a surface that had already drifted, because it
    // would only be comparing this file's copy of the vocabulary against
    // itself. Iterating `VARIANTS` also means a new provenance variant is
    // covered without anyone remembering to extend this test.
    for variant in InstalledYamlDataProvenance::VARIANTS.iter().copied() {
        assert_eq!(
            installed_yaml_data_provenance_to_string(variant),
            variant.as_str(),
            "the run surface must publish the configuration crate's own token",
        );
    }
    // Derived from the core for the same reason as the provenance loop above.
    // These two enums are contract-stability twins, so the strings they publish
    // are the configuration crate's; restating them here would have recorded
    // that agreement rather than checking it.
    for variant in contract::LocalIgnoreRunState::VARIANTS.iter().copied() {
        assert_eq!(
            local_ignore_state_to_string(variant),
            variant.as_str(),
            "the run surface must publish the core's own token",
        );
    }
    assert_eq!(
        super::PyScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore as u8,
        0
    );
    assert_eq!(
        super::PyScanRunLocalIgnoreRecoveryDecision::ResetToDefault as u8,
        1
    );
    assert_eq!(
        contract::ResumeErrorKind::ContinuationConsumed.as_str(),
        "scan_run_continuation_consumed"
    );
    assert_eq!(
        [
            contract::ResumeErrorKind::LocalIgnoreResetConflict,
            contract::ResumeErrorKind::LocalIgnoreResetBackupFailure,
            contract::ResumeErrorKind::LocalIgnoreResetReplacementFailure,
            contract::ResumeErrorKind::LocalIgnoreResetDurabilityUnknown,
        ]
        .map(contract::ResumeErrorKind::as_str),
        [
            "local_ignore_reset_conflict",
            "local_ignore_reset_backup_failure",
            "local_ignore_reset_replacement_failure",
            "local_ignore_reset_durability_unknown",
        ]
    );
    for variant in contract::InstalledYamlDataRunDiagnosticKind::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            installed_yaml_data_diagnostic_kind_to_string(variant),
            variant.as_str(),
            "the run surface must publish the core's own token",
        );
    }
}

/// Replacement publication failure maps to the dedicated Python exception and shared metadata.
#[test]
fn replacement_failure_maps_shared_outcome_to_typed_python_exception() {
    let expected = shared_reset_outcomes();
    Python::initialize();
    Python::attach(|py| {
        let path = PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml");
        let error = scan_run_resume_error_to_py(
            py,
            contract::ResumeError::LocalIgnoreResetReplacementFailure(
                contract::LocalIgnoreResetFailure {
                    path: path.clone(),
                    stage: Some(contract::LocalIgnoreResetFailureStage::Publish),
                    message: "injected replacement publication failure".to_string(),
                },
            ),
        );

        assert!(error.is_instance_of::<ScanRunLocalIgnoreResetReplacementError>(py));
        let value = error.value(py);
        assert_eq!(
            value
                .getattr("code")
                .expect("replacement exception should expose code")
                .extract::<String>()
                .expect("replacement code should be a string"),
            expected["replacementFailureCode"]
                .as_str()
                .expect("shared replacement code should be a string")
        );
        assert_eq!(
            value
                .getattr("path")
                .expect("replacement exception should expose path")
                .extract::<PathBuf>()
                .expect("replacement path should remain pathlib-compatible"),
            path
        );
        assert_eq!(
            value
                .getattr("stage")
                .expect("replacement exception should expose stage")
                .extract::<String>()
                .expect("replacement stage should be a string"),
            "publish"
        );
    });
}

/// Visible replacement durability uncertainty maps every recovery receipt field.
#[test]
fn durability_unknown_maps_shared_outcome_to_typed_python_exception() {
    let expected = shared_reset_outcomes();
    Python::initialize();
    Python::attach(|py| {
        let path = PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml");
        let backup_path = PathBuf::from("C:/CLASSIC/backups/local-ignore.bak");
        let malformed_identity = YamlDataContentIdentity::from_bytes(b"malformed");
        let backup_identity = malformed_identity.clone();
        let replacement_identity = YamlDataContentIdentity::from_bytes(b"defaults");
        let error = scan_run_resume_error_to_py(
            py,
            contract::ResumeError::LocalIgnoreResetDurabilityUnknown(
                Box::new(contract::LocalIgnoreResetDurabilityUnknownError {
                    path: path.clone(),
                    backup_path: backup_path.clone(),
                    malformed_identity: malformed_identity.clone(),
                    backup_identity: backup_identity.clone(),
                    replacement_identity: replacement_identity.clone(),
                    message: "replacement visible; durability unknown".to_string(),
                }),
            ),
        );

        assert!(error.is_instance_of::<ScanRunLocalIgnoreResetDurabilityUnknownError>(py));
        let value = error.value(py);
        assert_eq!(
            value
                .getattr("code")
                .expect("durability exception should expose code")
                .extract::<String>()
                .expect("durability code should be a string"),
            expected["durabilityUnknownCode"]
                .as_str()
                .expect("shared durability-unknown code should be a string")
        );
        assert_eq!(
            value
                .getattr("path")
                .expect("durability exception should expose path")
                .extract::<PathBuf>()
                .expect("canonical path should remain pathlib-compatible"),
            path
        );
        assert_eq!(
            value
                .getattr("backup_path")
                .expect("durability exception should expose backup path")
                .extract::<PathBuf>()
                .expect("backup path should remain pathlib-compatible"),
            backup_path
        );
        for (attribute, expected_sha256) in [
            ("malformed_identity", malformed_identity.sha256_hex()),
            ("backup_identity", backup_identity.sha256_hex()),
            ("replacement_identity", replacement_identity.sha256_hex()),
        ] {
            let identity = value
                .getattr(attribute)
                .expect("durability exception should expose every receipt identity");
            assert_eq!(
                identity
                    .getattr("sha256")
                    .expect("receipt identity should expose sha256")
                    .extract::<String>()
                    .expect("receipt sha256 should be a string"),
                expected_sha256
            );
        }
    });
}

#[test]
fn maps_every_infrastructure_stage_and_optional_path() {
    // Iterated over `VARIANTS` and compared against the core token rather than
    // a hand-written pair list. The list this replaced was a second copy of the
    // six strings, one file away from the mapper's own copy - so the two could
    // only ever have agreed with each other, never with the core.
    for (index, stage) in contract::InfrastructureErrorStage::VARIANTS
        .iter()
        .copied()
        .enumerate()
    {
        let path = (index % 2 == 0).then(|| PathBuf::from(format!("failure-{index}")));
        let mapped = infrastructure_error_to_py(contract::InfrastructureError {
            stage,
            message: format!("failure {index}"),
            path: path.clone(),
        });
        assert_eq!(mapped.stage, stage.as_str());
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
        // Built from `VARIANTS` so that "all failure stages" in this test's name
        // stays true when a stage is added, rather than quietly narrowing to
        // "the three that were current when it was written".
        failures: contract::LogFailureStage::VARIANTS
            .iter()
            .copied()
            .map(|stage| contract::LogFailure {
                stage,
                message: format!("{} failed", stage.as_str()),
            })
            .collect(),
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
        contract::LogFailureStage::VARIANTS
            .iter()
            .copied()
            .map(Vocabulary::as_str)
            .collect::<Vec<_>>(),
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

// --- Vocabulary projection ------------------------------------------------
//
// Expectations are derived from `classic-scanlog-core`, never restated. A
// hand-written array here would be another copy of the vocabulary: it would
// pass against a surface that had already drifted, because it would only be
// comparing this file's copy against itself. Iterating `VARIANTS` also means a
// new variant is covered without anyone remembering to extend these tests.

#[test]
/// Every Display Label this surface resolves is the core label for that token.
fn every_scan_run_vocabulary_token_resolves_to_the_core_display_label() {
    for variant in contract::InstalledYamlDataRunDiagnosticKind::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            scan_run_installed_yaml_data_diagnostic_kind_label(variant.as_str())
                .expect("a published token must resolve"),
            variant.label(),
        );
    }

    for variant in contract::LocalIgnoreRunState::VARIANTS.iter().copied() {
        assert_eq!(
            scan_run_local_ignore_yaml_data_state_label(variant.as_str())
                .expect("a published token must resolve"),
            variant.label(),
        );
    }
}

/// Asserts one resolver agrees with the core Display Label, for every variant.
///
/// Written once and applied per enum because the four resolvers differ only in
/// their type parameter: repeating the loop four times would be four chances to
/// paste the wrong core enum beside the right resolver, which is the class of
/// mistake a test cannot catch about itself.
fn assert_labels_match_the_core<T: Vocabulary>(
    resolver: fn(&str) -> PyResult<&'static str>,
) {
    for variant in T::VARIANTS.iter().copied() {
        let label = resolver(variant.as_str()).expect("a published token must resolve");
        assert_eq!(label, variant.label());
        assert!(!label.is_empty());
    }
}

#[test]
/// Every run-owned scan-run token resolves to the core Display Label.
///
/// Separate from the twin test above because these four have no configuration
/// counterpart: their prose has exactly one definition site, in the run crate,
/// and there is no second surface to compare against.
fn every_run_owned_scan_run_token_resolves_to_the_core_display_label() {
    assert_labels_match_the_core::<contract::LogDisposition>(scan_run_log_disposition_label);
    assert_labels_match_the_core::<contract::LogFailureStage>(scan_run_log_failure_stage_label);
    assert_labels_match_the_core::<contract::InfrastructureErrorStage>(
        scan_run_infrastructure_error_stage_label,
    );
    assert_labels_match_the_core::<contract::LocalIgnoreResetFailureStage>(
        scan_run_local_ignore_reset_failure_stage_label,
    );
}

#[test]
/// A label a frontend could not have derived from the token reaches Python.
fn glossary_capitalization_survives_the_python_boundary() {
    // The two labels in this change that a mechanical transform of the token
    // could not produce. Quoted as literals deliberately: this is the one thing
    // a derived expectation cannot prove, since deriving it from `label()`
    // would pass just as happily if the core had lowercased both.
    assert_eq!(
        scan_run_log_failure_stage_label("unsolved_logs_finalization")
            .expect("a published token must resolve"),
        "Unsolved Logs finalization"
    );
    assert_eq!(
        scan_run_infrastructure_error_stage_label("formid_database_access")
            .expect("a published token must resolve"),
        "FormID database access"
    );
}

// --- Display Content ------------------------------------------------------
//
// These tests pin the *flattening*, never a sentence. Wording is pinned once, in
// `classic-scan-presentation`; restating a sentence here would be a second copy
// of it, which is the drift this whole effort removes. What this surface owes is
// narrower: that every segment kind fills exactly its own fields, that order
// survives, that every severity crosses distinctly, and that each carrier hands
// over the lines the renderer actually produced.

/// Returns one fabricated line carrying every segment kind, in a fixed order.
///
/// Fabricated rather than rendered because no single real run emits all six
/// kinds in one line — and because the flattening is what is under test here,
/// not which segments a given run happens to produce.
fn every_segment_kind() -> DisplayLine {
    DisplayLine {
        severity: DisplaySeverity::Notice,
        segments: vec![
            DisplaySegment::Text("scanned"),
            DisplaySegment::Label("discovery"),
            DisplaySegment::Count {
                value: 3,
                noun: "logs",
            },
            DisplaySegment::Path(PathBuf::from("logs/crash.log")),
            DisplaySegment::Name("Buffout 4".to_string()),
            DisplaySegment::Emphasis("parse failure".to_string()),
        ],
    }
}

#[test]
/// Every segment kind fills exactly the fields its kind selects, and no others.
fn every_display_segment_kind_fills_exactly_its_own_fields() {
    let segments: Vec<_> = every_segment_kind()
        .segments
        .iter()
        .map(display_segment_to_py)
        .collect();

    let observed: Vec<(&str, &str, &str, u64)> = segments
        .iter()
        .map(|segment| {
            (
                segment.kind.as_str(),
                segment.text.as_str(),
                segment.path.as_str(),
                segment.count,
            )
        })
        .collect();

    assert_eq!(
        observed,
        vec![
            ("text", "scanned", "", 0),
            ("label", "discovery", "", 0),
            // A count rides in two fields at once: the quantity in `count` and the
            // noun Rust already agreed with it in `text`.
            ("count", "logs", "", 3),
            ("path", "", "logs/crash.log", 0),
            ("name", "Buffout 4", "", 0),
            ("emphasis", "parse failure", "", 0),
        ],
    );
}

#[test]
/// Segments cross in reading order, and a line keeps its severity.
fn display_segments_cross_the_boundary_in_reading_order() {
    let line = every_segment_kind();
    let crossed = display_lines_to_py(std::slice::from_ref(&line));

    assert_eq!(crossed.len(), 1);
    assert_eq!(crossed[0].severity, "notice");
    assert_eq!(
        crossed[0]
            .segments
            .iter()
            .map(|segment| segment.kind.as_str())
            .collect::<Vec<_>>(),
        ["text", "label", "count", "path", "name", "emphasis"],
    );
}

#[test]
/// Every severity crosses as its own token; none collapses onto another.
fn every_display_severity_crosses_as_a_distinct_token() {
    let severities = [
        DisplaySeverity::Info,
        DisplaySeverity::Notice,
        DisplaySeverity::Warning,
        DisplaySeverity::Failure,
        DisplaySeverity::Success,
    ];
    let tokens: Vec<&str> = severities
        .iter()
        .copied()
        .map(display_severity_to_string)
        .collect();

    assert_eq!(
        tokens,
        ["info", "notice", "warning", "failure", "success"],
        "each severity must publish its own token",
    );
}

#[test]
/// A count crosses with the noun Rust resolved, in both grammatical numbers.
///
/// The value and the noun travel as separate fields precisely so no consumer can
/// re-decide the form. Pinning both numbers is what proves this surface carries
/// what it was handed rather than deriving a plural of its own.
fn a_count_crosses_with_the_noun_rust_agreed_with() {
    let singular = display_segment_to_py(&DisplaySegment::Count {
        value: 1,
        noun: "log",
    });
    let plural = display_segment_to_py(&DisplaySegment::Count {
        value: 2,
        noun: "logs",
    });

    assert_eq!((singular.count, singular.text.as_str()), (1, "log"));
    assert_eq!((plural.count, plural.text.as_str()), (2, "logs"));
}

#[test]
/// An observed event carries the lines the renderer produced, in its order.
fn an_event_carries_the_lines_the_renderer_produced() {
    let event = contract::Event::LogFinished {
        log: log_event(),
        disposition: contract::LogDisposition::Failed,
    };
    let expected = display_lines_to_py(&render_event(&event));
    let mapped = event_to_py(event);

    assert!(!expected.is_empty(), "a finished log must say something");
    assert_eq!(
        mapped
            .display_lines
            .iter()
            .map(|line| (line.severity.clone(), line.segments.len()))
            .collect::<Vec<_>>(),
        expected
            .iter()
            .map(|line| (line.severity.clone(), line.segments.len()))
            .collect::<Vec<_>>(),
    );
}

#[test]
/// A completed run's envelope carries the lines rendered from that run.
fn an_execution_carries_the_lines_rendered_from_its_run() {
    Python::initialize();
    Python::attach(|py| {
        let facts = || contract::RunResult {
            status: CrashLogScanRunStatus::Completed,
            discovery: Some(discovery()),
            setup: None,
            installed_yaml_data: None,
            continuation: None,
            effective_concurrency: Some(2),
            message: None,
            total: 1,
            succeeded: 1,
            failed: 0,
            cancelled: 0,
            logs: Vec::new(),
        };
        let expected = display_lines_to_py(&render_run_result(&facts()));
        let execution = super::success_execution(py, facts(), None).expect("envelope should build");

        assert!(!expected.is_empty(), "a completed run must say something");
        assert_eq!(execution.display_lines.len(), expected.len());
        assert_eq!(
            execution.display_lines[0].segments[0].kind,
            expected[0].segments[0].kind,
        );
    });
}

#[test]
/// An infrastructure failure states its stage in prose and keeps its token.
///
/// The token assertion is the point: the rendered lines are for a person and the
/// `stage` field is for a consumer matching on it, and this surface must publish
/// both rather than choosing between them.
fn an_infrastructure_failure_carries_lines_beside_its_frozen_token() {
    let facts = || contract::InfrastructureError {
        stage: contract::InfrastructureErrorStage::FormIdDatabaseAccess,
        message: "database is locked".to_string(),
        path: None,
    };
    let expected = display_lines_to_py(&render_infrastructure_error(&facts()));
    let execution = super::failure_execution(facts(), None);

    assert!(!expected.is_empty(), "a failure must say something");
    assert_eq!(execution.display_lines.len(), expected.len());
    assert_eq!(
        execution
            .error
            .as_ref()
            .expect("a failure envelope carries its typed error")
            .stage,
        "formid_database_access",
    );
    assert!(
        !execution.display_lines.iter().any(|line| {
            line.segments
                .iter()
                .any(|segment| segment.text == "formid_database_access")
        }),
        "a Vocabulary Token must never reach a rendered line as prose",
    );
}

#[test]
/// Every resume failure reaches Python with lines beside its stable code.
fn every_resume_failure_carries_lines_beside_its_stable_code() {
    Python::initialize();
    Python::attach(|py| {
        for error in [
            contract::ResumeError::ContinuationConsumed,
            contract::ResumeError::LocalIgnoreResetBackupFailure(contract::LocalIgnoreResetFailure {
                path: PathBuf::from("CLASSIC Ignore.yaml"),
                stage: Some(contract::LocalIgnoreResetFailureStage::Write),
                message: "disk is full".to_string(),
            }),
        ] {
            let code = error.kind().as_str();
            let rendered = display_lines_to_py(&render_resume_error(&error));
            let py_error = super::scan_run_resume_error_to_py(py, error);
            let value = py_error.value(py);

            let lines: Vec<Py<super::PyScanRunDisplayLine>> = value
                .getattr("display_lines")
                .expect("every resume failure publishes display lines")
                .extract()
                .expect("display lines extract as their own class");
            assert_eq!(lines.len(), rendered.len());
            assert!(!rendered.is_empty(), "a resume failure must say something");
            assert_eq!(
                value
                    .getattr("code")
                    .expect("every resume failure publishes its code")
                    .extract::<String>()
                    .expect("a code is a string"),
                code,
            );
        }
    });
}

#[test]
/// The replay rejection keeps the exact code and message it published before.
///
/// Quoted as literals rather than derived from the same core call the projection
/// makes: deriving them would prove only that the surface agrees with itself.
fn the_replay_rejection_keeps_its_published_code_and_message() {
    Python::initialize();
    Python::attach(|py| {
        let py_error =
            super::scan_run_resume_error_to_py(py, contract::ResumeError::ContinuationConsumed);
        let value = py_error.value(py);

        assert_eq!(
            value
                .getattr("code")
                .expect("the replay rejection publishes its code")
                .extract::<String>()
                .expect("a code is a string"),
            "scan_run_continuation_consumed",
        );
        assert_eq!(
            value.to_string(),
            "Crash Log Scan Run continuation was already consumed",
        );
    });
}

#[test]
/// An unrecognized token is rejected rather than resolved to a default label.
fn an_unknown_scan_run_token_raises_rather_than_returning_a_placeholder_label() {
    Python::initialize();
    Python::attach(|py| {
        for error in [
            scan_run_installed_yaml_data_diagnostic_kind_label("not_a_kind").unwrap_err(),
            scan_run_local_ignore_yaml_data_state_label("not_a_state").unwrap_err(),
            scan_run_log_disposition_label("not_a_disposition").unwrap_err(),
            scan_run_log_failure_stage_label("not_a_stage").unwrap_err(),
            scan_run_infrastructure_error_stage_label("not_a_stage").unwrap_err(),
            scan_run_local_ignore_reset_failure_stage_label("not_a_stage").unwrap_err(),
        ] {
            assert!(error.is_instance_of::<pyo3::exceptions::PyValueError>(py));
        }
    });
}

// --- Local Ignore recovery prompt -----------------------------------------
//
// These pin no wording either. What they prove is that the prompt crosses whole:
// the decision Rust named, the label it resolved, the description it wrote, and -
// the fact this type exists for - whether this run can honor the decision.

#[test]
/// Every recovery decision crosses with its own availability rather than a shared flag.
///
/// This is the whole point of the type. A consumer reading `available` off the
/// decision it is about to offer cannot repeat the gap this closed, where the fact
/// lived beside the prompt and two frontends never looked at it.
fn each_recovery_decision_crosses_with_its_own_availability() {
    let prompt = recovery_prompt_to_py(&RecoveryPrompt {
        lines: Vec::new(),
        decisions: vec![
            RecoveryDecisionDescription {
                decision: contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
                label: "Proceed Without Ignore",
                description: vec![DisplaySegment::Text("proceed")],
                available: true,
            },
            RecoveryDecisionDescription {
                decision: contract::LocalIgnoreRecoveryDecision::ResetToDefault,
                label: "Reset To Default",
                description: vec![DisplaySegment::Text("reset")],
                available: false,
            },
        ],
    });

    assert_eq!(prompt.decisions.len(), 2);
    assert_eq!(
        prompt.decisions[0].decision,
        PyScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore
    );
    assert_eq!(prompt.decisions[0].label, "Proceed Without Ignore");
    assert!(prompt.decisions[0].available);
    assert_eq!(
        prompt.decisions[1].decision,
        PyScanRunLocalIgnoreRecoveryDecision::ResetToDefault
    );
    assert_eq!(prompt.decisions[1].label, "Reset To Default");
    assert!(!prompt.decisions[1].available);
}

#[test]
/// A decision's description flattens the same way the lines beside it do.
fn a_recovery_decision_description_flattens_like_any_other_segments() {
    let prompt = recovery_prompt_to_py(&RecoveryPrompt {
        lines: vec![every_segment_kind()],
        decisions: vec![RecoveryDecisionDescription {
            decision: contract::LocalIgnoreRecoveryDecision::ResetToDefault,
            label: "Reset To Default",
            description: vec![
                DisplaySegment::Text("back up"),
                DisplaySegment::Path(PathBuf::from("CLASSIC Ignore.yaml")),
                DisplaySegment::Count {
                    value: 1,
                    noun: "file",
                },
            ],
            available: true,
        }],
    });

    assert_eq!(prompt.lines.len(), 1);
    assert_eq!(prompt.lines[0].segments.len(), 6);

    let observed: Vec<(&str, &str, &str, u64)> = prompt.decisions[0]
        .description
        .iter()
        .map(|segment| {
            (
                segment.kind.as_str(),
                segment.text.as_str(),
                segment.path.as_str(),
                segment.count,
            )
        })
        .collect();
    assert_eq!(
        observed,
        vec![
            ("text", "back up", "", 0),
            ("path", "", "CLASSIC Ignore.yaml", 0),
            ("count", "file", "", 1),
        ],
    );
}

#[test]
/// Both contract decisions cross as distinct Python twins.
///
/// The enum crosses rather than a token, unlike every other tag on this surface,
/// because `scan_run_resume` takes the enum: a consumer answers with exactly what it
/// was offered rather than mapping a string back.
fn every_recovery_decision_crosses_as_its_own_python_twin() {
    assert_eq!(
        local_ignore_recovery_decision_to_py(
            contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore
        ),
        PyScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore
    );
    assert_eq!(
        local_ignore_recovery_decision_to_py(contract::LocalIgnoreRecoveryDecision::ResetToDefault),
        PyScanRunLocalIgnoreRecoveryDecision::ResetToDefault
    );
}

#[test]
/// A run paused on Local Ignore recovery carries the prompt Rust rendered for it.
fn the_execution_envelope_carries_the_recovery_prompt_core_rendered() {
    Python::attach(|py| {
        let build = || contract::RunResult {
            status: CrashLogScanRunStatus::LocalIgnoreRecoveryRequired,
            discovery: None,
            setup: None,
            installed_yaml_data: None,
            continuation: None,
            effective_concurrency: None,
            message: Some("Local Ignore requires a recovery decision".to_string()),
            total: 0,
            succeeded: 0,
            failed: 0,
            cancelled: 0,
            logs: Vec::new(),
        };
        let expected = recovery_prompt_to_py(&render_local_ignore_recovery(None));
        let execution = success_execution(py, build(), None).expect("envelope should build");

        let prompt = execution
            .recovery_prompt()
            .expect("a paused run carries a prompt");
        assert_eq!(prompt.lines.len(), expected.lines.len());
        assert_eq!(prompt.decisions.len(), expected.decisions.len());
        for (actual, expected) in prompt.decisions.iter().zip(&expected.decisions) {
            assert_eq!(actual.decision, expected.decision);
            assert_eq!(actual.label, expected.label);
            assert_eq!(actual.available, expected.available);
        }
    });
}

#[test]
/// A run that is not waiting on a decision carries no prompt for a consumer to show.
fn a_terminal_envelope_carries_no_recovery_prompt() {
    Python::attach(|py| {
        let completed = success_execution(
            py,
            contract::RunResult {
                status: CrashLogScanRunStatus::Completed,
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
            },
            None,
        )
        .expect("envelope should build");
        assert!(completed.recovery_prompt().is_none());

        let failed = failure_execution(
            contract::InfrastructureError {
                stage: contract::InfrastructureErrorStage::Discovery,
                message: "discovery failed".to_string(),
                path: None,
            },
            None,
        );
        assert!(failed.recovery_prompt().is_none());
    });
}