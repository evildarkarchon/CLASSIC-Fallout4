use super::*;
use classic_config_core::YamlDataContentIdentity;
use classic_scanlog_core::scan_run::contract::{
    InfrastructureError, InfrastructureErrorStage, LogDisposition, LogEvent, LogFailure,
    LogFailureStage, LogResult, RunResult,
};
use classic_scanlog_core::{CrashLogScanRejectedInput, CrashLogScanRunStatus};
// Imported here rather than in `scan_run.rs`: the module itself only projects
// labels through `crate::vocabulary::display_label`, so the trait is in scope
// only where these tests read `label()` off a core variant to derive their
// expectation from.
use classic_vocabulary::Vocabulary;

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

/// Loads the shared reset-outcome expectations used by Node rejection mapping tests.
fn shared_reset_outcomes() -> serde_json::Value {
    serde_json::from_str::<serde_json::Value>(SHARED_SCAN_RUN_MANIFEST)
        .expect("shared scan-run manifest should deserialize")["fixtures"]["installedYamlData"]
        ["resetOutcomes"]
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
        installation_root: "C:/CLASSIC".to_string(),
        game: crate::shared::JsGameId::Fallout4,
        game_version: "auto".to_string(),
        show_formid_values: false,
        simplify_logs: false,
        formid_database_paths: Vec::new(),
        unsolved_logs_destination: Some(" \t ".to_string()),
        max_concurrent: None,
    })
    .expect("configuration should convert");
    assert_eq!(configuration.installation_root, PathBuf::from("C:/CLASSIC"));
    assert_eq!(configuration.game, classic_shared_core::GameId::Fallout4);
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
fn installed_yaml_data_run_enums_cover_recovery_and_every_diagnostic() {
    assert!(matches!(
        local_ignore_run_state_to_js(contract::LocalIgnoreRunState::Existing),
        JsScanRunLocalIgnoreState::Existing
    ));
    assert!(matches!(
        local_ignore_run_state_to_js(contract::LocalIgnoreRunState::Generated),
        JsScanRunLocalIgnoreState::Generated
    ));
    assert!(matches!(
        local_ignore_run_state_to_js(contract::LocalIgnoreRunState::RecoveryRequired),
        JsScanRunLocalIgnoreState::RecoveryRequired
    ));
    assert!(matches!(
        local_ignore_run_state_to_js(contract::LocalIgnoreRunState::ProceedWithoutIgnore),
        JsScanRunLocalIgnoreState::ProceedWithoutIgnore
    ));
    assert!(matches!(
        local_ignore_run_state_to_js(contract::LocalIgnoreRunState::ResetToDefault),
        JsScanRunLocalIgnoreState::ResetToDefault
    ));
    assert_eq!(
        local_ignore_recovery_decision_to_core(
            JsScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore
        ),
        contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore
    );
    assert_eq!(
        local_ignore_recovery_decision_to_core(
            JsScanRunLocalIgnoreRecoveryDecision::ResetToDefault
        ),
        contract::LocalIgnoreRecoveryDecision::ResetToDefault
    );

    for (kind, expected) in [
        (
            contract::InstalledYamlDataRunDiagnosticKind::CacheUnavailable,
            JsScanRunInstalledYamlDataDiagnosticKind::CacheUnavailable,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::Missing,
            JsScanRunInstalledYamlDataDiagnosticKind::Missing,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::Read,
            JsScanRunInstalledYamlDataDiagnosticKind::Read,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::InvalidUtf8,
            JsScanRunInstalledYamlDataDiagnosticKind::InvalidUtf8,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::Parse,
            JsScanRunInstalledYamlDataDiagnosticKind::Parse,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::InvalidSchema,
            JsScanRunInstalledYamlDataDiagnosticKind::InvalidSchema,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::IncompatibleSchema,
            JsScanRunInstalledYamlDataDiagnosticKind::IncompatibleSchema,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::InvalidRoleData,
            JsScanRunInstalledYamlDataDiagnosticKind::InvalidRoleData,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated,
            JsScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated,
        ),
        (
            contract::InstalledYamlDataRunDiagnosticKind::LocalIgnoreReset,
            JsScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreReset,
        ),
    ] {
        let actual = installed_yaml_data_run_diagnostic_kind_to_js(kind);
        assert_eq!(
            std::mem::discriminant(&actual),
            std::mem::discriminant(&expected)
        );
    }
}

/// Replacement publication failure retains the shared Node rejection code, path, and stage.
#[test]
fn replacement_failure_projects_shared_node_rejection_metadata() {
    let expected = shared_reset_outcomes();
    let path = PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml");
    let projection =
        project_scan_run_resume_error(contract::ResumeError::LocalIgnoreResetReplacementFailure(
            contract::LocalIgnoreResetFailure {
                path: path.clone(),
                stage: Some(contract::LocalIgnoreResetFailureStage::Publish),
                message: "injected replacement publication failure".to_string(),
            },
        ));

    assert_eq!(
        projection.code,
        expected["replacementFailureCode"]
            .as_str()
            .expect("shared replacement code should be a string")
    );
    let ScanRunResumeErrorMetadata::OperationalFailure {
        path: projected_path,
        stage,
    } = projection.metadata
    else {
        panic!("replacement failure should retain operational metadata");
    };
    assert_eq!(PathBuf::from(projected_path), path);
    assert_eq!(stage, Some("publish"));
}

/// Visible replacement durability uncertainty retains every recovery receipt field.
#[test]
fn durability_unknown_projects_shared_node_recovery_receipt() {
    let expected = shared_reset_outcomes();
    let path = PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml");
    let backup_path = PathBuf::from("C:/CLASSIC/backups/local-ignore.bak");
    let malformed_identity = YamlDataContentIdentity::from_bytes(b"malformed");
    let backup_identity = malformed_identity.clone();
    let replacement_identity = YamlDataContentIdentity::from_bytes(b"defaults");
    let projection =
        project_scan_run_resume_error(contract::ResumeError::LocalIgnoreResetDurabilityUnknown(
            Box::new(contract::LocalIgnoreResetDurabilityUnknownError {
                path: path.clone(),
                backup_path: backup_path.clone(),
                malformed_identity: malformed_identity.clone(),
                backup_identity: backup_identity.clone(),
                replacement_identity: replacement_identity.clone(),
                message: "replacement visible; durability unknown".to_string(),
            }),
        ));

    assert_eq!(
        projection.code,
        expected["durabilityUnknownCode"]
            .as_str()
            .expect("shared durability-unknown code should be a string")
    );
    let ScanRunResumeErrorMetadata::DurabilityUnknown {
        path: projected_path,
        backup_path: projected_backup_path,
        malformed_identity: projected_malformed,
        backup_identity: projected_backup,
        replacement_identity: projected_replacement,
    } = projection.metadata
    else {
        panic!("durability uncertainty should retain a recovery receipt");
    };
    assert_eq!(PathBuf::from(projected_path), path);
    assert_eq!(PathBuf::from(projected_backup_path), backup_path);
    assert_eq!(projected_malformed.sha256, malformed_identity.sha256_hex());
    assert_eq!(projected_backup.sha256, backup_identity.sha256_hex());
    assert_eq!(
        projected_replacement.sha256,
        replacement_identity.sha256_hex()
    );
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

    // Iterated over `VARIANTS` and compared against the core token rather than
    // a hand-written pair list. The list this replaced was correct, and that is
    // the problem: a correct copy is indistinguishable from a drifted one until
    // someone edits the other side, so it recorded the agreement instead of
    // checking it. Iterating also covers a variant added later for free.
    for disposition in LogDisposition::VARIANTS.iter().copied() {
        let mapped = event_to_js(contract::Event::LogFinished {
            log: log_event(),
            disposition,
        });
        assert_eq!(mapped.kind, "log_finished");
        assert_eq!(mapped.disposition.as_deref(), Some(disposition.as_str()));
    }
}

#[test]
fn terminal_mapping_preserves_every_status_failure_and_optional_path() {
    // The variant list stays written out - the run status does not implement
    // the Vocabulary contract, so there is no `VARIANTS` to iterate - but the
    // expected string is the core's own token rather than a second spelling of
    // it. That is the half of the check that can actually fail.
    for status in [
        CrashLogScanRunStatus::Completed,
        CrashLogScanRunStatus::NoCrashLogsFound,
        CrashLogScanRunStatus::SetupFailed,
        CrashLogScanRunStatus::LocalIgnoreRecoveryRequired,
        CrashLogScanRunStatus::CancelledBeforeDiscovery,
        CrashLogScanRunStatus::Cancelled,
    ] {
        let mapped = run_result_to_js(RunResult {
            status,
            discovery: None,
            setup: None,
            installed_yaml_data: None,
            continuation: None,
            effective_concurrency: Some(2),
            message: Some("terminal message".to_string()),
            total: 1,
            succeeded: 0,
            failed: 1,
            cancelled: 0,
            logs: vec![],
        });
        assert_eq!(mapped.status, status.as_str());
        assert_eq!(mapped.effective_concurrency, Some(2));
        assert_eq!(mapped.message.as_deref(), Some("terminal message"));
    }

    let mapped_log = log_result_to_js(LogResult {
        discovery_index: 1,
        crash_log: PathBuf::from("C:/logs/crash.log"),
        autoscan_report: Some(PathBuf::from("C:/logs/crash-AUTOSCAN.md")),
        disposition: LogDisposition::Failed,
        // Built from `VARIANTS` so that "every failure stage" stays true when a
        // stage is added, rather than meaning "the three that were current when
        // this test was written".
        failures: LogFailureStage::VARIANTS
            .iter()
            .copied()
            .map(|stage| LogFailure {
                stage,
                message: format!("{} failed", stage.as_str()),
            })
            .collect(),
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
        LogFailureStage::VARIANTS
            .iter()
            .copied()
            .map(Vocabulary::as_str)
            .collect::<Vec<_>>()
    );
    assert_eq!(mapped_log.processing_time_us, i64::MAX);
    assert_eq!(
        mapped_log.autoscan_report.as_deref(),
        Some("C:/logs/crash-AUTOSCAN.md")
    );
}

#[test]
fn infrastructure_mapping_covers_every_stage_with_and_without_paths() {
    // Derived from `VARIANTS` and the core token, for the same reason as the
    // disposition loop above.
    for stage in InfrastructureErrorStage::VARIANTS.iter().copied() {
        let mapped = infrastructure_error_to_js(InfrastructureError {
            stage,
            message: "failure".to_string(),
            path: Some(PathBuf::from("C:/failure/path")),
        });
        assert_eq!(mapped.stage, stage.as_str());
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

// --- Vocabulary projection ------------------------------------------------
//
// Expectations are derived from `classic-scanlog-core`, never restated. A
// hand-written array here would be another copy of the vocabulary: it would
// pass against a surface that had already drifted, because it would only be
// comparing this file's copy against itself. Iterating `VARIANTS` also means a
// new variant is covered without anyone remembering to extend these tests.

#[test]
/// Every projected JavaScript variant resolves back to the core Display Label.
fn every_scan_run_twin_projects_its_core_display_label() {
    for variant in contract::InstalledYamlDataRunDiagnosticKind::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            scan_run_installed_yaml_data_diagnostic_kind_label(
                installed_yaml_data_run_diagnostic_kind_to_js(variant)
            ),
            variant.label(),
        );
    }

    for variant in contract::LocalIgnoreRunState::VARIANTS.iter().copied() {
        assert_eq!(
            scan_run_local_ignore_yaml_data_state_label(local_ignore_run_state_to_js(variant)),
            variant.label(),
        );
    }
}

#[test]
/// No scan-run Display Label reaches JavaScript empty.
fn no_scan_run_display_label_reaches_javascript_empty() {
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
                installed_yaml_data_run_diagnostic_kind_to_js(variant)
            )
            .is_empty()
        );
    }

    for variant in contract::LocalIgnoreRunState::VARIANTS.iter().copied() {
        assert!(
            !scan_run_local_ignore_yaml_data_state_label(local_ignore_run_state_to_js(variant))
                .is_empty()
        );
    }
}

/// Asserts one token-taking label function agrees with the core, for every variant.
///
/// Written once and applied per enum because the four differ only in their type
/// parameter: repeating the loop four times would be four chances to paste the
/// wrong core enum beside the right resolver, which is the class of mistake a
/// test cannot catch about itself.
fn assert_token_labels_match_the_core<T: Vocabulary>(
    label_of: fn(String) -> napi::Result<String>,
) {
    for variant in T::VARIANTS.iter().copied() {
        let label = label_of(variant.as_str().to_string())
            .expect("a token this surface publishes must resolve");
        assert_eq!(label, variant.label());
        assert!(!label.is_empty());
    }
}

#[test]
/// Every published scan-run token resolves to the core Display Label.
///
/// Separate from the twin test above because these four are not modelled as
/// `string_enum` types on this surface - they are published as bare token
/// strings - so their label functions take a `string` and are checked by
/// round-tripping the token rather than by projecting an enum value.
fn every_published_scan_run_token_resolves_to_the_core_display_label() {
    assert_token_labels_match_the_core::<contract::LogDisposition>(scan_run_log_disposition_label);
    assert_token_labels_match_the_core::<contract::LogFailureStage>(
        scan_run_log_failure_stage_label,
    );
    assert_token_labels_match_the_core::<contract::InfrastructureErrorStage>(
        scan_run_infrastructure_error_stage_label,
    );
    assert_token_labels_match_the_core::<contract::LocalIgnoreResetFailureStage>(
        scan_run_local_ignore_reset_failure_stage_label,
    );
}

#[test]
/// An unrecognized token is rejected rather than resolved to a placeholder.
fn an_unknown_scan_run_token_is_rejected_rather_than_labelled() {
    // Reachable here in a way it is not for the two `string_enum` twins, which
    // N-API rejects at the boundary. Returning `""` instead would surface as a
    // blank cell in a frontend with nothing to diagnose it by.
    for label_of in [
        scan_run_log_disposition_label,
        scan_run_log_failure_stage_label,
        scan_run_infrastructure_error_stage_label,
        scan_run_local_ignore_reset_failure_stage_label,
    ] {
        assert!(label_of("not_a_real_token".to_string()).is_err());
    }
}

#[test]
/// A label a frontend could not have derived from the token reaches JavaScript.
fn glossary_capitalization_survives_the_javascript_boundary() {
    // The two labels in this change that a mechanical transform of the token
    // could not produce. Quoted as literals deliberately: this is the one thing
    // a derived expectation cannot prove, since deriving it from `label()`
    // would pass just as happily if the core had lowercased both.
    assert_eq!(
        scan_run_log_failure_stage_label("unsolved_logs_finalization".to_string())
            .expect("a published token must resolve"),
        "Unsolved Logs finalization"
    );
    assert_eq!(
        scan_run_infrastructure_error_stage_label("formid_database_access".to_string())
            .expect("a published token must resolve"),
        "FormID database access"
    );
}
