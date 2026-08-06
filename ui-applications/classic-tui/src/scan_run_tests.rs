use super::{
    CANCEL_RECOVERY_CHOICE, LocalIgnoreRecoveryPrompt, PROCEED_WITHOUT_IGNORE_CHOICE,
    PresentedLine, RESET_TO_DEFAULT_CHOICE, ScanRunIntent, TerminalPresentation, build_request,
    describe_local_ignore_recovery, format_error, format_event, format_result, format_resume_error,
    join_presented, sentence_case,
};
use classic_config_core::YamlDataContentIdentity;
use classic_scan_presentation::{
    DisplayLine, DisplaySegment, render_event, render_infrastructure_error, render_resume_error,
    render_run_result,
};
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

/// Concatenates one display line's segments the way the adapter contract requires.
///
/// Written out here rather than reused from the module under test on purpose: an assertion that
/// called the same helper the code calls would pass no matter what that helper did. This is the
/// contract stated a second time, in a place a rewrite of the first cannot reach.
fn expected_text(line: &DisplayLine) -> String {
    line.segments
        .iter()
        .map(|segment| match segment {
            DisplaySegment::Text(text) | DisplaySegment::Label(text) => (*text).to_string(),
            DisplaySegment::Count { value, noun } => format!("{value} {noun}"),
            DisplaySegment::Path(path) => path.display().to_string(),
            DisplaySegment::Name(name) | DisplaySegment::Emphasis(name) => name.clone(),
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// Asserts that presented lines carry core's lines, in order, with neither words nor order changed.
///
/// `presented` may be longer than `rendered`: [`format_result`] groups the FCX Mode setup
/// projection in after the rendered lines, and that projection is deliberately still this
/// frontend's. What must hold is that every line core produced arrives unrewritten, in core's
/// order, at the front.
fn assert_renders_core_lines(presented: &[PresentedLine], rendered: &[DisplayLine]) {
    assert!(
        presented.len() >= rendered.len(),
        "every core line must reach the overlay: {} presented, {} rendered",
        presented.len(),
        rendered.len()
    );
    for (index, line) in rendered.iter().enumerate() {
        assert_eq!(
            presented[index].text,
            expected_text(line),
            "line {index} was reworded or its segments reordered"
        );
        assert_eq!(
            presented[index].severity, line.severity,
            "line {index} lost the severity core gave it"
        );
    }
}

/// Returns the overlay body as one plain-text block.
fn details_of(presentation: &TerminalPresentation) -> String {
    join_presented(&presentation.details)
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

/// Builds a mixed-outcome result rich enough to exercise every segment kind a run emits.
fn mixed_outcome_result() -> RunResult {
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

    RunResult {
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
    }
}

// ---------------------------------------------------------------------------
// Renderer conformance
//
// These do not pin wording. Wording is pinned once, in `classic-scan-presentation`, and asserting
// it again here would mean one rewording produced two diffs and two chances to disagree — the drift
// this consolidation removes, reintroduced in the test layer. What these prove is narrower: that
// the TUI renders what it was handed rather than rewriting it.
// ---------------------------------------------------------------------------

#[test]
fn a_run_result_renders_cores_lines_in_cores_order() {
    let result = mixed_outcome_result();

    assert_renders_core_lines(&format_result(&result).details, &render_run_result(&result));
}

#[test]
fn an_infrastructure_error_renders_cores_lines_in_cores_order() {
    let error = InfrastructureError {
        stage: InfrastructureErrorStage::Intake,
        message: "intake could not be prepared".to_string(),
        path: Some(PathBuf::from("C:/CLASSIC/CLASSIC Data")),
    };

    assert_renders_core_lines(
        &format_error(&error).details,
        &render_infrastructure_error(&error),
    );
}

/// Covers every resume failure category, because each renders a different line shape.
#[test]
fn every_resume_failure_renders_cores_lines_in_cores_order() {
    let identity = YamlDataContentIdentity::from_bytes(b"malformed");
    let errors = [
        ResumeError::ContinuationConsumed,
        ResumeError::LocalIgnoreResetConflict(LocalIgnoreResetConflictError {
            expected_identity: identity.clone(),
            actual_identity: Some(YamlDataContentIdentity::from_bytes(b"repaired")),
            backup_path: Some(PathBuf::from(
                "C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.yaml",
            )),
        }),
        // The removed-file conflict is a distinct branch: an absent current identity is a refusal
        // to overwrite rather than a failed write, and it renders its own line.
        ResumeError::LocalIgnoreResetConflict(LocalIgnoreResetConflictError {
            expected_identity: identity.clone(),
            actual_identity: None,
            backup_path: None,
        }),
        ResumeError::LocalIgnoreResetBackupFailure(LocalIgnoreResetFailure {
            path: PathBuf::from("C:/CLASSIC/CLASSIC Backup"),
            stage: None,
            message: "backup directory could not be created".to_string(),
        }),
        ResumeError::LocalIgnoreResetReplacementFailure(LocalIgnoreResetFailure {
            path: PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml"),
            stage: Some(LocalIgnoreResetFailureStage::Publish),
            message: "staged replacement could not be published".to_string(),
        }),
        ResumeError::LocalIgnoreResetDurabilityUnknown(Box::new(
            LocalIgnoreResetDurabilityUnknownError {
                path: PathBuf::from("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml"),
                backup_path: PathBuf::from("C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.yaml"),
                malformed_identity: identity.clone(),
                backup_identity: identity.clone(),
                replacement_identity: YamlDataContentIdentity::from_bytes(b"defaults"),
                message: "directory durability could not be confirmed".to_string(),
            },
        )),
        ResumeError::Infrastructure(InfrastructureError {
            stage: InfrastructureErrorStage::Intake,
            message: "intake could not be prepared".to_string(),
            path: Some(PathBuf::from("C:/CLASSIC/CLASSIC Data")),
        }),
    ];

    for error in errors {
        assert_renders_core_lines(
            &format_resume_error(&error).details,
            &render_resume_error(&error),
        );
    }
}

#[test]
fn an_event_renders_cores_lines_in_cores_order() {
    let event = Event::DiscoveryCompleted(CrashLogScanDiscoveryResult {
        source: CrashLogScanDiscoverySource::Targeted,
        accepted_logs: vec![PathBuf::from("C:/Crash Logs/crash-01.log")],
        rejected_inputs: vec![CrashLogScanRejectedInput {
            path: PathBuf::from("C:/Selected/readme.txt"),
            reason: "unsupported file".to_string(),
        }],
        searched_locations: vec![PathBuf::from("C:/Selected")],
    });

    // A discovery that rejected an input renders two lines. The status line is one row, so it
    // groups them — but in core's order, and with neither line reworded.
    let rendered = render_event(&event);
    assert_eq!(
        rendered.len(),
        2,
        "this fixture must exercise the two-line shape"
    );
    let status = format_event(&event).status;
    let accepted = status
        .find(&expected_text(&rendered[0])[1..])
        .expect("the acceptance line must reach the status row");
    let rejected = status
        .find(&expected_text(&rendered[1]))
        .expect("the rejection line must reach the status row");
    assert!(
        accepted < rejected,
        "the status row must keep core's line order: {status}"
    );
}

/// Verifies a count reaches the user with the noun core already agreed with its value.
///
/// The point of the assertion is the *pair*: a run of one Crash Log and a run of two are rendered
/// through the same code path, so a frontend that re-derived the noun — or reused a `plural` helper
/// with its arguments the wrong way round — fails one half or the other.
#[test]
fn a_count_prints_the_noun_core_resolved_for_its_value() {
    let one = RunResult {
        logs: vec![log_result(0, "only.log", LogDisposition::Succeeded)],
        total: 1,
        succeeded: 1,
        ..mixed_outcome_result()
    };
    let singular = details_of(&format_result(&one));
    assert!(
        singular.contains("1 log") && !singular.contains("1 logs"),
        "a single Crash Log must not read as a plural: {singular}"
    );

    let many = details_of(&format_result(&mixed_outcome_result()));
    assert!(
        many.contains("3 logs"),
        "a three-log run must read as a plural: {many}"
    );

    // Structural half: every count core emitted reaches the overlay as its value then its noun,
    // with nothing between them and no other form of the word substituted.
    for line in render_run_result(&one) {
        for segment in &line.segments {
            if let DisplaySegment::Count { value, noun } = segment {
                assert!(
                    singular.contains(&format!("{value} {noun}")),
                    "a count reached the overlay without core's noun: {value} {noun}"
                );
            }
        }
    }
}

/// Verifies the two path treatments are the deliberate Display Layout split they claim to be.
#[test]
fn a_path_is_whole_in_the_overlay_and_shortened_in_the_status_row() {
    let result = mixed_outcome_result();
    let presentation = format_result(&result);

    assert!(
        details_of(&presentation).contains("C:/Crash Logs/first.log"),
        "the overlay must keep the whole path a frontend would link to"
    );

    let event = Event::LogStarted(LogEvent {
        discovery_index: 0,
        crash_log: PathBuf::from("C:/Crash Logs/crash-01.log"),
        completed: 0,
        total: 2,
    });
    let status = format_event(&event).status;
    assert!(
        status.contains("crash-01.log") && !status.contains("C:/Crash Logs/crash-01.log"),
        "one absolute path fills the status row; it is shortened there: {status}"
    );
}

/// Verifies severity is mapped rather than reworded, and that failures are distinguishable.
#[test]
fn severity_reaches_the_frontend_without_changing_a_word() {
    let result = mixed_outcome_result();
    let presentation = format_result(&result);
    let rendered = render_run_result(&result);

    // The per-log lines carry the three dispositions, so a mixed run exercises the whole range a
    // terminal result can produce.
    let severities: Vec<_> = presentation
        .details
        .iter()
        .take(rendered.len())
        .map(|line| line.severity)
        .collect();
    assert!(
        severities.contains(&classic_scan_presentation::DisplaySeverity::Failure),
        "a failed Crash Log must reach the frontend marked as a failure"
    );
    assert!(
        severities.contains(&classic_scan_presentation::DisplaySeverity::Success),
        "a succeeded Crash Log must reach the frontend marked as a success"
    );

    // Colour is this frontend's answer to severity, and it is the only thing that differs between
    // a failure line and a success line: the words are core's either way.
    assert_ne!(
        crate::theme::severity_color(classic_scan_presentation::DisplaySeverity::Failure),
        crate::theme::severity_color(classic_scan_presentation::DisplaySeverity::Success),
        "a failure must be distinguishable from a success without rewording either"
    );
}

/// Verifies the FCX Mode setup projection is grouped in unchanged.
///
/// Explicitly out of scope for this migration: its check state, check kind, issue severity, and
/// update kind have not adopted the shared vocabulary, so the presentation crate does not render
/// them and this frontend keeps its existing `Display`-based projection.
#[test]
fn the_setup_projection_is_grouped_in_unchanged() {
    let mut result = mixed_outcome_result();
    result.setup = Some(CrashLogScanSetupResult {
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
    });

    let details = details_of(&format_result(&result));
    assert!(details.contains("Setup: ready"));
    assert!(details.contains("Setup check [passed] game_root: Game root is valid"));
}

// ---------------------------------------------------------------------------
// Display Layout the TUI still owns
// ---------------------------------------------------------------------------

/// Verifies the gauge weighting, which is this frontend's and not core's.
#[test]
fn event_progress_weighting_advances_the_gauge_by_lifecycle_step() {
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
                accepted_logs: vec![crash_log.clone()],
                rejected_inputs: Vec::new(),
                searched_locations: vec![PathBuf::from("C:/Selected")],
            }),
            0.0,
        ),
        (
            Event::EffectiveConcurrencySelected {
                effective_concurrency: 2,
            },
            0.0,
        ),
        (Event::LogQueued(log(0)), 0.0),
        (Event::LogStarted(log(0)), 4.0),
        (
            Event::LogPhase {
                log: log(0),
                phase: ScanProgressPhase::Analyze,
            },
            41.0,
        ),
        (
            Event::LogFinished {
                log: log(1),
                disposition: LogDisposition::Succeeded,
            },
            50.0,
        ),
    ];

    for (event, expected_percent) in cases {
        assert_eq!(format_event(&event).percent, expected_percent);
    }
}

/// Verifies only log-scoped events lead their status row with a percentage.
///
/// A discovery and a concurrency selection report no completed work, so a percentage beside them
/// would claim progress the run has not made.
#[test]
fn only_log_scoped_events_lead_the_status_row_with_progress() {
    let log_event = Event::LogStarted(LogEvent {
        discovery_index: 0,
        crash_log: PathBuf::from("C:/Crash Logs/crash-01.log"),
        completed: 0,
        total: 2,
    });
    assert!(format_event(&log_event).status.starts_with("4% - "));

    let concurrency = Event::EffectiveConcurrencySelected {
        effective_concurrency: 2,
    };
    let status = format_event(&concurrency).status;
    assert!(
        !status.contains('%'),
        "a concurrency selection reports no progress: {status}"
    );
}

/// Verifies a status row opens on a capital, which is this frontend's sentence position.
///
/// Core labels a phase as a lower-case participle precisely so a frontend can place it anywhere;
/// upper-casing it here is a capitalization rule, not a second copy of the word.
#[test]
fn the_status_row_is_sentence_cased() {
    let status = format_event(&Event::LogPhase {
        log: LogEvent {
            discovery_index: 0,
            crash_log: PathBuf::from("C:/Crash Logs/crash-01.log"),
            completed: 0,
            total: 2,
        },
        phase: ScanProgressPhase::Analyze,
    })
    .status;

    assert!(status.contains(&sentence_case(ScanProgressPhase::Analyze.label())));
}

/// Verifies the gauge reports completed work rather than discovered work.
#[test]
fn a_terminal_result_reports_completed_work_as_its_percentage() {
    // Two of three logs reached a terminal outcome; the third was never started.
    assert_eq!(
        format_result(&mixed_outcome_result()).percent,
        (2.0_f64 / 3.0) * 100.0
    );

    let empty = RunResult {
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
    assert_eq!(format_result(&empty).percent, 0.0);
    assert_eq!(format_error(&intake_error()).percent, 0.0);
    assert_eq!(
        format_resume_error(&ResumeError::ContinuationConsumed).percent,
        0.0
    );
}

fn intake_error() -> InfrastructureError {
    InfrastructureError {
        stage: InfrastructureErrorStage::Intake,
        message: "the run could not continue".to_string(),
        path: None,
    }
}

/// Verifies the per-log lines stay in discovery order, which is the order core emits them in.
#[test]
fn per_log_lines_stay_in_discovery_order() {
    let details = details_of(&format_result(&mixed_outcome_result()));
    let first = details.find("C:/Crash Logs/first.log").unwrap();
    let second = details.find("C:/Crash Logs/second.log").unwrap();
    let third = details.find("C:/Crash Logs/third.log").unwrap();

    assert!(first < second && second < third);
}

// ---------------------------------------------------------------------------
// Display Label audit, runtime half
// ---------------------------------------------------------------------------

/// Verifies every scan progress phase reaches the user as its core Display Label.
///
/// Exhaustive over `VARIANTS` and derived from the core rather than from a literal table, so a pass
/// means agreement with the owning crate instead of a matching restatement of it. The negative half
/// asserts the Vocabulary Token is absent: a progress line reading `analyze crash-01.log` would be
/// an identifier standing in for prose.
#[test]
fn every_scan_progress_phase_renders_its_display_label() {
    for phase in <ScanProgressPhase as Vocabulary>::VARIANTS.iter().copied() {
        let presentation = format_event(&Event::LogPhase {
            log: LogEvent {
                discovery_index: 0,
                crash_log: PathBuf::from("C:/Crash Logs/crash-01.log"),
                completed: 0,
                total: 2,
            },
            phase,
        });

        // Sentence-initial in the status line, which is this frontend's capitalization rule rather
        // than part of the phase's name. Calling `sentence_case` rather than reimplementing it
        // keeps that rule single-sourced for the same reason the words themselves are.
        let expected = sentence_case(phase.label());
        assert!(
            presentation.status.contains(&expected),
            "the status line for {phase:?} should name the Display Label: {}",
            presentation.status
        );
        assert!(
            !presentation.status.contains(Vocabulary::as_str(phase)),
            "the status line for {phase:?} still carries its Vocabulary Token: {}",
            presentation.status
        );
    }
}

/// Verifies every infrastructure stage reaches the user as prose rather than as its identifier.
///
/// Exhaustive over `VARIANTS` and derived from the core rather than from a literal table. The
/// negative half is what carries the weight: for the three stages whose two forms differ it asserts
/// the Vocabulary Token is *absent*, because a frontend printing `formid_database_access`
/// mid-sentence is leaking an identifier into a message meant to be read.
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
        let details = details_of(&presentation);

        let label = stage.label();
        assert!(
            presentation.status.contains(label),
            "the status line for {stage:?} should name the Display Label: {}",
            presentation.status
        );
        assert!(
            details.contains(label),
            "the overlay for {stage:?} should name the Display Label: {details}"
        );

        let token = Vocabulary::as_str(stage);
        if token != label {
            assert!(
                !presentation.status.contains(token),
                "the status line for {stage:?} still carries the token `{token}`: {}",
                presentation.status
            );
            assert!(
                !details.contains(token),
                "the overlay for {stage:?} still carries the token `{token}`: {details}"
            );
        }
    }
}

/// Verifies every terminal run status reaches the user as prose rather than as its identifier.
///
/// This is the site the shared runtime audit deferred `CrashLogScanRunStatus` for. The detail block
/// used to open on `Run status: <token>`; the status line used to be a sentence this frontend wrote
/// per variant. Both are now one Display Label inside a segment core owns.
#[test]
fn every_terminal_run_status_renders_its_display_label() {
    for status in <CrashLogScanRunStatus as Vocabulary>::VARIANTS
        .iter()
        .copied()
    {
        let result = RunResult {
            status,
            ..mixed_outcome_result()
        };
        let presentation = format_result(&result);
        let details = details_of(&presentation);

        let label = status.label();
        assert!(
            presentation.status.contains(&sentence_case(label)),
            "the status line for {status:?} should name the Display Label: {}",
            presentation.status
        );

        // Scoped to the tokens a substring search can actually distinguish from prose. `Cancelled`
        // spells its token `cancelled` and its label `cancelled after discovery`, so the token is a
        // prefix of its own label and searching for it can only ever find the label. An underscore
        // is the shape that cannot appear in a sentence, which is exactly the leak worth catching:
        // a user reading `local_ignore_recovery_required` is reading an identifier.
        let token = Vocabulary::as_str(status);
        if token.contains('_') {
            assert!(
                !details.contains(token),
                "the overlay for {status:?} still carries the token `{token}`: {details}"
            );
        }
    }
}

// ---------------------------------------------------------------------------
// Local Ignore recovery prompt
//
// Still this frontend's prose: the recovery prompt renderer lands with the gated recovery phase.
// ---------------------------------------------------------------------------

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
    let text = join_presented(&prompt.overlay_lines());

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

/// Verifies the paused run is described to the user by core rather than by this frontend.
#[test]
fn recovery_prompt_carries_the_run_as_core_describes_it() {
    let result = paused_recovery_result(Some("Local Ignore recovery is required"));
    let prompt = describe_local_ignore_recovery(&result);

    assert_renders_core_lines(&prompt.run_detail, &render_run_result(&result));
    // The detail sits below the choices, because a choice the user cannot see is not a choice they
    // were offered and every line here wraps.
    let text = join_presented(&prompt.overlay_lines());
    assert!(text.find(CANCEL_RECOVERY_CHOICE) < text.find(&prompt.run_detail[0].text));
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
        run_detail: Vec::new(),
        reset_available: false,
    };

    let text = join_presented(&prompt.overlay_lines());

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
}

// ---------------------------------------------------------------------------
// End-to-end through the real contract
// ---------------------------------------------------------------------------

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
    assert_renders_core_lines(&format_result(&before).details, &render_run_result(&before));

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
    // A single accepted Crash Log, so the noun must be singular wherever discovery is counted.
    assert!(
        event_statuses
            .iter()
            .any(|status| status.contains("1 crash log") && !status.contains("1 crash logs"))
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
            .any(|status| status.contains("crash-admitted.log"))
    );

    let details = details_of(&format_result(&result));
    assert!(details.contains("crash-admitted.log"));
    assert!(details.contains("crash-queued.log"));
    assert_renders_core_lines(&format_result(&result).details, &render_run_result(&result));
}
