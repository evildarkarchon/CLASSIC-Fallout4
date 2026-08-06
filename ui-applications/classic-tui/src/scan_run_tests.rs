use super::{
    CANCEL_RECOVERY_CHOICE, LocalIgnoreRecoveryPrompt, PROCEED_WITHOUT_IGNORE_CHOICE,
    RESET_TO_DEFAULT_CHOICE, ScanRunIntent, build_request, describe_local_ignore_recovery,
    format_error, format_event, format_result, format_resume_error,
};
use classic_config_core::YamlDataContentIdentity;
use classic_scanlog_core::scan_run::contract::{
    Configuration, Event, InfrastructureError, InfrastructureErrorStage,
    LocalIgnoreResetConflictError, LocalIgnoreResetDurabilityUnknownError, LocalIgnoreResetFailure,
    LocalIgnoreResetFailureStage, LogDisposition, LogEvent, LogFailure, LogFailureStage, LogResult,
    Options, Request, ResumeError, RunResult,
};
use classic_scanlog_core::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanFacts,
    CrashLogScanRejectedInput, CrashLogScanRunStatus, CrashLogScanSetupCheck,
    CrashLogScanSetupResult, ScanProgressPhase, StandardCrashLogScanSource,
    StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
use classic_shared_core::GameId;
use classic_shared_core::get_runtime;
use classic_vocabulary::Vocabulary;
use std::path::PathBuf;

const VALID_CRASH_LOG: &str =
    include_str!("../../../business-logic/classic-scanlog-core/benches/fixtures/crash-0DB9300.log");

fn configuration() -> Configuration {
    Configuration {
        installation_root: PathBuf::from("C:/CLASSIC"),
        game: GameId::Fallout4,
        game_version: "Regular".to_string(),
        options: Options::new(true, false),
        scan_facts: CrashLogScanFacts::default(),
        max_concurrent: Some(4),
    }
}

/// Builds an executable request configuration from the tracked scan-run YAML corpus.
fn executable_configuration(max_concurrent: usize) -> Configuration {
    let fixture_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../tests/fixtures/crash_log_scan_run")
        .canonicalize()
        .expect("scan-run fixture root should resolve");

    Configuration {
        installation_root: fixture_root,
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
        installed_yaml_data: None,
        effective_concurrency: None,
        message: None,
        total: 0,
        succeeded: 0,
        failed: 0,
        cancelled: 0,
        logs: Vec::new(),
        continuation: None,
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
        installed_yaml_data: None,
        effective_concurrency: Some(1),
        message: None,
        total: 2,
        succeeded: 1,
        failed: 0,
        cancelled: 1,
        logs: vec![admitted, not_started],
        continuation: None,
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

/// Verifies Local Ignore recovery remains a distinct expected TUI terminal status.
#[test]
fn terminal_presentation_distinguishes_local_ignore_recovery() {
    let result = RunResult {
        status: CrashLogScanRunStatus::LocalIgnoreRecoveryRequired,
        discovery: Some(CrashLogScanDiscoveryResult {
            source: CrashLogScanDiscoverySource::Targeted,
            accepted_logs: vec![PathBuf::from("C:/Selected/crash-one.log")],
            rejected_inputs: Vec::new(),
            searched_locations: vec![PathBuf::from("C:/Selected")],
        }),
        setup: None,
        installed_yaml_data: None,
        continuation: None,
        effective_concurrency: None,
        message: Some("Local Ignore recovery is required".to_string()),
        total: 1,
        succeeded: 0,
        failed: 0,
        cancelled: 0,
        logs: Vec::new(),
    };

    let presentation = format_result(&result);

    assert_eq!(presentation.percent, 0.0);
    assert_eq!(presentation.status, "Local Ignore recovery is required");
    assert!(
        presentation
            .details
            .contains("Run status: local_ignore_recovery_required")
    );
    assert!(
        presentation
            .details
            .contains("Discovery: targeted; 1 accepted")
    );
}

/// Builds a paused-run projection carrying retained discovery but no fabricated continuation.
fn paused_recovery_result(message: Option<&str>) -> RunResult {
    RunResult {
        status: CrashLogScanRunStatus::LocalIgnoreRecoveryRequired,
        discovery: Some(CrashLogScanDiscoveryResult {
            source: CrashLogScanDiscoverySource::Standard,
            accepted_logs: vec![
                PathBuf::from("C:/Crash Logs/crash-one.log"),
                PathBuf::from("C:/Crash Logs/crash-two.log"),
            ],
            rejected_inputs: Vec::new(),
            searched_locations: vec![PathBuf::from("C:/Crash Logs")],
        }),
        setup: None,
        installed_yaml_data: None,
        continuation: None,
        effective_concurrency: None,
        message: message.map(str::to_string),
        total: 2,
        succeeded: 0,
        failed: 0,
        cancelled: 0,
        logs: Vec::new(),
    }
}

/// Verifies the recovery overlay offers both Rust-defined decisions and a non-mutating cancel.
#[test]
fn recovery_prompt_offers_both_decisions_and_a_non_mutating_cancel() {
    let result = paused_recovery_result(Some("Local Ignore recovery is required"));

    let prompt = describe_local_ignore_recovery(&result);
    let text = prompt.overlay_text();

    assert_eq!(prompt.retained_logs, 2);
    assert_eq!(prompt.message, "Local Ignore recovery is required");
    assert!(text.contains("Local Ignore recovery is required"));
    assert!(text.contains("Retained discovery: 2 crash logs will be scanned once you decide."));
    assert!(text.contains(PROCEED_WITHOUT_IGNORE_CHOICE));
    assert!(text.contains(RESET_TO_DEFAULT_CHOICE));
    assert!(text.contains(CANCEL_RECOVERY_CHOICE));
    // Each choice must state its expected outcome, not merely advertise a key.
    assert!(text.contains("left exactly as it is"));
    assert!(text.contains("back up your malformed file byte-exactly"));
    assert!(text.contains("Local Ignore is not modified"));
}

/// Verifies an unavailable Reset To Default is omitted from the overlay and explained.
///
/// Constructed directly rather than through `describe_local_ignore_recovery`, because
/// `InspectedYamlDataFile` exposes no public constructor and a paused-run fixture therefore cannot
/// carry Installed YAML Data. The presentation rule is what changed, so that is what is pinned.
#[test]
fn recovery_prompt_omits_reset_when_the_contract_says_it_cannot_succeed() {
    let prompt = LocalIgnoreRecoveryPrompt {
        message: "Local Ignore recovery is required".to_string(),
        retained_logs: 2,
        diagnostics: Vec::new(),
        reset_available: false,
    };

    let text = prompt.overlay_text();

    assert!(text.contains(PROCEED_WITHOUT_IGNORE_CHOICE));
    assert!(text.contains(CANCEL_RECOVERY_CHOICE));
    assert!(
        !text.contains(RESET_TO_DEFAULT_CHOICE),
        "an impossible choice must not be advertised, got:\n{text}"
    );
    assert!(
        text.contains("Reset To Default is unavailable"),
        "the omission must be explained rather than left as a silent gap, got:\n{text}"
    );
}

/// Verifies a paused run without a Rust message still explains why a decision is needed.
#[test]
fn recovery_prompt_falls_back_to_an_explicit_default_explanation() {
    let prompt = describe_local_ignore_recovery(&paused_recovery_result(None));

    assert_eq!(
        prompt.message,
        "Local Ignore recovery is required before scanning can continue"
    );
    assert!(prompt.diagnostics.is_empty());
}

/// Verifies replay is presented with its own stable code rather than as a reset failure.
#[test]
fn resume_presentation_keeps_consumed_replay_distinct() {
    let presentation = format_resume_error(&ResumeError::ContinuationConsumed);

    assert_eq!(presentation.percent, 0.0);
    assert!(
        presentation
            .status
            .contains("Crash Log Scan recovery failed (scan_run_continuation_consumed)")
    );
    assert!(
        presentation
            .details
            .contains("This recovery decision was already applied")
    );
}

/// Verifies a reset conflict keeps both identities and states that nothing was replaced.
#[test]
fn resume_presentation_preserves_typed_reset_conflict_context() {
    let expected = YamlDataContentIdentity::from_bytes(b"malformed");
    let actual = YamlDataContentIdentity::from_bytes(b"repaired while deciding");
    let presentation = format_resume_error(&ResumeError::LocalIgnoreResetConflict(
        LocalIgnoreResetConflictError {
            expected_identity: expected.clone(),
            actual_identity: Some(actual.clone()),
            backup_path: Some(PathBuf::from(
                "C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.yaml",
            )),
        },
    ));

    assert!(
        presentation
            .status
            .contains("Crash Log Scan recovery failed (local_ignore_reset_conflict)")
    );
    assert!(presentation.details.contains(&format!(
        "Expected identity: sha256 {}",
        expected.sha256_hex()
    )));
    assert!(
        presentation
            .details
            .contains(&format!("Actual identity: sha256 {}", actual.sha256_hex()))
    );
    assert!(
        presentation
            .details
            .contains("Verified backup: C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.yaml")
    );
    assert!(
        presentation
            .details
            .contains("Your Local Ignore file was not replaced.")
    );
}

/// Verifies a conflict raised by removal is reported as a refusal, not a missing identity.
#[test]
fn resume_presentation_explains_a_removed_malformed_file() {
    let presentation = format_resume_error(&ResumeError::LocalIgnoreResetConflict(
        LocalIgnoreResetConflictError {
            expected_identity: YamlDataContentIdentity::from_bytes(b"malformed"),
            actual_identity: None,
            backup_path: None,
        },
    ));

    assert!(
        presentation
            .details
            .contains("the malformed file was removed while you decided")
    );
}

/// Verifies operational reset failures surface their path and publication stage.
#[test]
fn resume_presentation_makes_typed_reset_failures_actionable() {
    let backup = format_resume_error(&ResumeError::LocalIgnoreResetBackupFailure(
        LocalIgnoreResetFailure {
            path: PathBuf::from("C:/CLASSIC/CLASSIC Backup"),
            stage: None,
            message: "backup directory could not be created".to_string(),
        },
    ));
    let replacement = format_resume_error(&ResumeError::LocalIgnoreResetReplacementFailure(
        LocalIgnoreResetFailure {
            path: PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml"),
            stage: Some(LocalIgnoreResetFailureStage::Publish),
            message: "staged replacement could not be published".to_string(),
        },
    ));

    assert!(
        backup
            .status
            .contains("Crash Log Scan recovery failed (local_ignore_reset_backup_failure)")
    );
    assert!(backup.details.contains("Path: C:/CLASSIC/CLASSIC Backup"));
    assert!(!backup.details.contains("Stage:"));
    assert!(
        replacement
            .status
            .contains("Crash Log Scan recovery failed (local_ignore_reset_replacement_failure)")
    );
    assert!(replacement.details.contains("Stage: publish"));
}

/// Verifies durability uncertainty reports a recovery receipt instead of a plain failure.
#[test]
fn resume_presentation_reports_a_durability_recovery_receipt() {
    let malformed = YamlDataContentIdentity::from_bytes(b"malformed");
    let backup = YamlDataContentIdentity::from_bytes(b"malformed");
    let replacement = YamlDataContentIdentity::from_bytes(b"defaults");
    let presentation = format_resume_error(&ResumeError::LocalIgnoreResetDurabilityUnknown(
        Box::new(LocalIgnoreResetDurabilityUnknownError {
            path: PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml"),
            backup_path: PathBuf::from("C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.yaml"),
            malformed_identity: malformed.clone(),
            backup_identity: backup.clone(),
            replacement_identity: replacement.clone(),
            message: "directory durability could not be confirmed".to_string(),
        }),
    ));

    assert!(
        presentation
            .status
            .contains("Crash Log Scan recovery failed (local_ignore_reset_durability_unknown)")
    );
    assert!(
        presentation
            .details
            .contains("Verified backup: C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.yaml")
    );
    assert!(presentation.details.contains(&format!(
        "Malformed identity: sha256 {}",
        malformed.sha256_hex()
    )));
    assert!(
        presentation
            .details
            .contains(&format!("Backup identity: sha256 {}", backup.sha256_hex()))
    );
    assert!(presentation.details.contains(&format!(
        "Replacement identity: sha256 {}",
        replacement.sha256_hex()
    )));
}

/// Verifies a post-resume infrastructure failure keeps its stage and path.
#[test]
fn resume_presentation_preserves_infrastructure_stage_and_path() {
    let presentation = format_resume_error(&ResumeError::Infrastructure(InfrastructureError {
        stage: InfrastructureErrorStage::Intake,
        message: "intake could not be prepared".to_string(),
        path: Some(PathBuf::from("C:/CLASSIC/CLASSIC Data")),
    }));

    assert!(presentation.details.contains("Stage: intake"));
    assert!(
        presentation
            .details
            .contains("Path: C:/CLASSIC/CLASSIC Data")
    );
}

/// Verifies every infrastructure stage reaches the user as prose rather than as its identifier.
///
/// Exhaustive over `VARIANTS` and derived from the core rather than from a literal table, so a pass
/// means agreement with the owning crate instead of a matching restatement of it. The negative half
/// is what carries the weight: for the three stages whose two forms differ it asserts the Vocabulary
/// Token is *absent*, because a frontend printing `formid_database_access` mid-sentence is leaking
/// an identifier into a message meant to be read.
///
/// `resume_presentation_preserves_infrastructure_stage_and_path` above is why this exists rather
/// than being assumed. It pins `Intake`, whose token and label are the same word, so it stayed green
/// for as long as this frontend rendered tokens — structurally unable to notice the drift nearest
/// to it.
#[test]
fn every_infrastructure_stage_renders_its_display_label() {
    for stage in <InfrastructureErrorStage as Vocabulary>::VARIANTS
        .iter()
        .copied()
    {
        let presentation = format_error(&InfrastructureError {
            stage,
            message: "the run could not continue".to_string(),
            path: None,
        });

        let label = stage.label();
        assert!(
            presentation
                .status
                .contains(&format!("failed during {label}")),
            "the status line for {stage:?} should name the Display Label: {}",
            presentation.status
        );
        assert!(
            presentation
                .details
                .contains(&format!("failed during {label}")),
            "the overlay for {stage:?} should name the Display Label: {}",
            presentation.details
        );

        let token = Vocabulary::as_str(stage);
        if token != label {
            assert!(
                !presentation.status.contains(token),
                "the status line for {stage:?} still carries the token `{token}`: {}",
                presentation.status
            );
            assert!(
                !presentation.details.contains(token),
                "the overlay for {stage:?} still carries the token `{token}`: {}",
                presentation.details
            );
        }
    }
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
        installed_yaml_data: None,
        effective_concurrency: Some(2),
        message: None,
        total: 3,
        succeeded: 1,
        failed: 1,
        cancelled: 1,
        logs: vec![succeeded, failed, cancelled],
        continuation: None,
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
