//! Pins every item of the locked Display Content subset to an exact segment sequence.
//!
//! Wording is pinned here and only here. Per-frontend golden suites are deliberately not
//! used: they would assert the same wording four times, so one rewording would produce four
//! diffs and four chances to disagree — reintroducing, in the test layer, exactly the drift
//! this crate exists to remove. What a frontend must prove is narrower and belongs at the
//! audit seam it already has: that it did not reword what core handed it.
//!
//! No test here runs a scan. Every render function is pure over a borrowed contract value.

use super::{
    DisplayLine, DisplaySegment, DisplaySeverity, RecoveryDecisionDescription, render_event,
    render_infrastructure_error, render_local_ignore_recovery, render_resume_error,
    render_run_result,
};
use crate::display::{
    BYTE, CONCURRENT_SCAN, CRASH_LOG, CountedNoun, LOG, SEARCHED_LOCATION, TARGETED_INPUT,
};
use crate::recovery::render_recovery_prompt;
use crate::render::{
    render_installed_yaml_data_diagnostic, render_installed_yaml_data_header, render_local_ignore,
    render_local_ignore_reset, render_yaml_data_file,
};
use classic_config_core::{
    InstalledYamlDataProvenance, InstalledYamlDataRole, YamlDataContentIdentity,
};
use classic_scanlog_core::scan_run::contract::{
    Event, InfrastructureError, InfrastructureErrorStage, InstalledYamlDataRunDiagnosticKind,
    LocalIgnoreRecoveryDecision, LocalIgnoreResetConflictError,
    LocalIgnoreResetDurabilityUnknownError, LocalIgnoreResetFailure, LocalIgnoreResetFailureStage,
    LocalIgnoreResetRunData, LocalIgnoreRunState, LogDisposition, LogEvent, LogFailure,
    LogFailureStage, LogResult, ResumeError, RunResult, RunStatus,
};
use classic_scanlog_core::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanRejectedInput,
    ScanProgressPhase,
};
use classic_vocabulary::Vocabulary;
use std::path::PathBuf;

use DisplaySegment::{Count, Emphasis, Label, Path, Text};
use DisplaySeverity::{Failure, Info, Notice, Success, Warning};

/// Every noun this crate is allowed to count with.
///
/// The grammatical-number tests walk rendered output against this list, so a noun that
/// reaches a segment without appearing here fails rather than escaping — which is the one
/// gap the `CountedNoun` type cannot close on its own.
const COUNTED_NOUNS: &[CountedNoun] = &[
    LOG,
    CRASH_LOG,
    TARGETED_INPUT,
    SEARCHED_LOCATION,
    CONCURRENT_SCAN,
    BYTE,
];

/// Returns the registered noun pair carrying `noun` in either grammatical number.
fn registered_noun(noun: &str) -> Option<CountedNoun> {
    COUNTED_NOUNS
        .iter()
        .copied()
        .find(|pair| pair.for_value(1) == noun || pair.for_value(2) == noun)
}

// -- fixtures ---------------------------------------------------------------------------

/// Builds an otherwise-empty run result carrying one terminal status.
fn run_result(status: RunStatus) -> RunResult {
    RunResult {
        status,
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
    }
}

/// Builds a per-log result with the given disposition and no failures.
fn log_result(disposition: LogDisposition) -> LogResult {
    LogResult {
        discovery_index: 2,
        crash_log: PathBuf::from("C:/logs/crash-2024.log"),
        autoscan_report: None,
        disposition,
        failures: Vec::new(),
        message: None,
        moved_to_unsolved_logs: false,
        processing_time_us: 0,
        processing_time_ms: 0,
        formid_count: 0,
        plugin_count: 0,
        suspect_count: 0,
    }
}

/// Builds the shared facts every log-scoped event carries.
fn log_event(total: usize) -> LogEvent {
    LogEvent {
        discovery_index: 2,
        crash_log: PathBuf::from("C:/logs/crash-2024.log"),
        completed: 2,
        total,
    }
}

/// Builds a discovery result with the given accepted, rejected, and searched counts.
fn discovery(accepted: usize, rejected: usize, searched: usize) -> CrashLogScanDiscoveryResult {
    CrashLogScanDiscoveryResult {
        source: CrashLogScanDiscoverySource::Targeted,
        accepted_logs: (0..accepted)
            .map(|index| PathBuf::from(format!("C:/logs/accepted-{index}.log")))
            .collect(),
        rejected_inputs: (0..rejected)
            .map(|index| CrashLogScanRejectedInput {
                path: PathBuf::from(format!("C:/logs/rejected-{index}.txt")),
                reason: "not a Crash Log".to_string(),
            })
            .collect(),
        searched_locations: (0..searched)
            .map(|index| PathBuf::from(format!("C:/logs/location-{index}")))
            .collect(),
    }
}

/// Builds a reset failure with a durable-publication stage.
fn reset_failure() -> LocalIgnoreResetFailure {
    LocalIgnoreResetFailure {
        path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml"),
        stage: Some(LocalIgnoreResetFailureStage::Write),
        message: "the replacement could not be written".to_string(),
    }
}

// -- terminal status prose --------------------------------------------------------------

/// Verifies a clean completion states the outcome and how much it scanned.
#[test]
fn terminal_status_pins_a_clean_completion() {
    let mut result = run_result(RunStatus::Completed);
    result.total = 5;
    result.succeeded = 5;

    assert_eq!(
        render_run_result(&result)[0],
        DisplayLine {
            severity: Success,
            segments: vec![
                Label("completed"),
                Text("-"),
                Count {
                    value: 5,
                    noun: "logs"
                },
                Text("scanned"),
            ],
        }
    );
}

/// Verifies a completion carrying failures or cancellations accounts for every discovered log.
///
/// The leading count says "discovered", not "scanned": `total` is what discovery accepted, and
/// a run that never started some of it did not scan all of it. Saying "5 logs scanned" beside
/// "1 log not started" would claim six logs out of five.
#[test]
fn terminal_status_pins_a_completion_with_failures() {
    let mut result = run_result(RunStatus::Completed);
    result.total = 5;
    result.succeeded = 2;
    result.failed = 2;
    result.cancelled = 1;

    assert_eq!(
        render_run_result(&result)[0],
        DisplayLine {
            severity: Warning,
            segments: vec![
                Label("completed"),
                Text("-"),
                Count {
                    value: 5,
                    noun: "logs"
                },
                Text("discovered,"),
                Count {
                    value: 2,
                    noun: "logs"
                },
                Text("failed and"),
                Count {
                    value: 1,
                    noun: "log"
                },
                Text("not started"),
            ],
        }
    );
}

/// Verifies the aggregate tally counts logs, matching the terminal status line's noun.
///
/// Both lines describe `result.failed`. Counting it as logs in one and as errors in the other
/// would have two adjacent lines of the same run describe one number differently — and a
/// failed log is one log, however many structured failures it carries.
#[test]
fn outcome_summary_pins_the_aggregate_tally() {
    let mut result = run_result(RunStatus::Completed);
    result.total = 4;
    result.succeeded = 1;
    result.failed = 2;
    result.cancelled = 1;

    assert_eq!(
        render_run_result(&result)[1],
        DisplayLine {
            severity: Info,
            segments: vec![
                Text("Outcomes:"),
                Count {
                    value: 1,
                    noun: "log"
                },
                Text("succeeded,"),
                Count {
                    value: 2,
                    noun: "logs"
                },
                Text("failed,"),
                Count {
                    value: 1,
                    noun: "log"
                },
                Text("not started"),
            ],
        }
    );
}

/// Verifies the discovery summary states its source and all three of its tallies.
#[test]
fn discovery_summary_pins_its_source_and_tallies() {
    let mut result = run_result(RunStatus::Completed);
    result.discovery = Some(discovery(1, 2, 3));

    assert_eq!(
        render_run_result(&result)[1],
        DisplayLine {
            severity: Info,
            segments: vec![
                Text("Discovery:"),
                Text("targeted discovery"),
                Text("-"),
                Count {
                    value: 1,
                    noun: "crash log"
                },
                Text("accepted,"),
                Count {
                    value: 2,
                    noun: "targeted inputs"
                },
                Text("rejected,"),
                Count {
                    value: 3,
                    noun: "locations"
                },
                Text("searched"),
            ],
        }
    );
}

/// Verifies the four count-free statuses read as their Display Label alone.
///
/// This is what `CrashLogScanRunStatus` adopting the shared vocabulary bought: the six
/// outcomes are now named once, where every frontend previously invented its own prose.
#[test]
fn terminal_status_pins_the_label_only_outcomes() {
    let cases = [
        (RunStatus::NoCrashLogsFound, Notice, "no Crash Logs found"),
        (RunStatus::SetupFailed, Failure, "setup failed"),
        (
            RunStatus::LocalIgnoreRecoveryRequired,
            Warning,
            "Local Ignore recovery required",
        ),
        (
            RunStatus::CancelledBeforeDiscovery,
            Notice,
            "cancelled before discovery",
        ),
    ];

    for (status, severity, label) in cases {
        assert_eq!(
            render_run_result(&run_result(status))[0],
            DisplayLine {
                severity,
                segments: vec![Label(label)],
            },
            "unexpected terminal status line for {status:?}"
        );
    }
}

/// Verifies a post-discovery cancellation distinguishes finished work from work never started.
#[test]
fn terminal_status_pins_a_post_discovery_cancellation() {
    let mut result = run_result(RunStatus::Cancelled);
    result.total = 4;
    result.succeeded = 1;
    result.failed = 0;
    result.cancelled = 3;

    assert_eq!(
        render_run_result(&result)[0],
        DisplayLine {
            severity: Notice,
            segments: vec![
                Label("cancelled after discovery"),
                Text("-"),
                Count {
                    value: 1,
                    noun: "log"
                },
                Text("completed and"),
                Count {
                    value: 3,
                    noun: "logs"
                },
                Text("not started"),
            ],
        }
    );
}

// -- infrastructure error prose ---------------------------------------------------------

/// Verifies the failing stage reads as prose, never as its Vocabulary Token.
///
/// `formid_database_access` reaching a user was the original drift this whole effort
/// started from, so the stage that spells differently in its two forms is the one pinned.
#[test]
fn infrastructure_error_pins_its_prose_and_path() {
    let error = InfrastructureError {
        stage: InfrastructureErrorStage::FormIdDatabaseAccess,
        message: "the FormID database is locked".to_string(),
        path: Some(PathBuf::from("C:/CLASSIC/databases/Fallout4 FormIDs.db")),
    };

    assert_eq!(
        render_infrastructure_error(&error),
        vec![
            DisplayLine {
                severity: Failure,
                segments: vec![
                    Text("Crash Log Scan Run failed during"),
                    Label("FormID database access"),
                    Text("-"),
                    Emphasis("the FormID database is locked".to_string()),
                ],
            },
            DisplayLine {
                severity: Info,
                segments: vec![
                    Text("Path:"),
                    Path(PathBuf::from("C:/CLASSIC/databases/Fallout4 FormIDs.db")),
                ],
            },
        ]
    );
}

/// Verifies an error without an attributable path omits the path line entirely.
#[test]
fn infrastructure_error_omits_an_absent_path() {
    let error = InfrastructureError {
        stage: InfrastructureErrorStage::InternalInvariant,
        message: "scheduling reached an impossible state".to_string(),
        path: None,
    };

    assert_eq!(
        render_infrastructure_error(&error),
        vec![DisplayLine {
            severity: Failure,
            segments: vec![
                Text("Crash Log Scan Run failed during"),
                Label("internal invariant validation"),
                Text("-"),
                Emphasis("scheduling reached an impossible state".to_string()),
            ],
        }]
    );
}

// -- resume error prose -----------------------------------------------------------------

/// Verifies replay is stated as prose rather than as its stable code.
#[test]
fn resume_error_pins_a_consumed_continuation() {
    assert_eq!(
        render_resume_error(&ResumeError::ContinuationConsumed),
        vec![
            DisplayLine {
                severity: Failure,
                segments: vec![Text(
                    "Crash Log Scan recovery failed - this recovery decision was already applied"
                )],
            },
            DisplayLine {
                severity: Notice,
                segments: vec![Text("Start the Crash Log Scan again to retry.")],
            },
        ]
    );
}

/// Verifies a reset conflict keeps both identities and says nothing was replaced.
#[test]
fn resume_error_pins_a_reset_conflict() {
    let conflict = LocalIgnoreResetConflictError {
        expected_identity: YamlDataContentIdentity::from_bytes(b"malformed"),
        actual_identity: Some(YamlDataContentIdentity::from_bytes(b"repaired")),
        backup_path: Some(PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml.bak")),
    };
    let expected_hex = conflict.expected_identity.sha256_hex();
    let actual_hex = YamlDataContentIdentity::from_bytes(b"repaired").sha256_hex();

    assert_eq!(
        render_resume_error(&ResumeError::LocalIgnoreResetConflict(conflict)),
        vec![
            DisplayLine {
                severity: Failure,
                segments: vec![Text(
                    "Crash Log Scan recovery failed - Local Ignore reset conflicted with the current file on disk"
                )],
            },
            DisplayLine {
                severity: Info,
                segments: vec![Text("Expected sha256"), Emphasis(expected_hex)],
            },
            DisplayLine {
                severity: Info,
                segments: vec![Text("Actual sha256"), Emphasis(actual_hex)],
            },
            DisplayLine {
                severity: Info,
                segments: vec![
                    Text("Verified backup:"),
                    Path(PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml.bak")),
                ],
            },
            DisplayLine {
                severity: Notice,
                segments: vec![Text("Your Local Ignore file was not replaced.")],
            },
        ]
    );
}

/// Verifies a file removed mid-decision reads as a refusal to overwrite, not a failed write.
#[test]
fn resume_error_pins_a_conflict_whose_file_vanished() {
    let conflict = LocalIgnoreResetConflictError {
        expected_identity: YamlDataContentIdentity::from_bytes(b"malformed"),
        actual_identity: None,
        backup_path: None,
    };

    let lines = render_resume_error(&ResumeError::LocalIgnoreResetConflict(conflict));

    assert_eq!(
        lines[2],
        DisplayLine {
            severity: Notice,
            segments: vec![Text(
                "The malformed Local Ignore file was removed while you decided."
            )],
        }
    );
    assert_eq!(lines.len(), 4, "an absent backup must not produce a line");
}

/// Verifies backup and replacement failures are told apart by their headline.
///
/// The two carry the same payload type, so only the prose distinguishes "nothing was
/// touched" from "the repair started and did not finish".
#[test]
fn resume_error_pins_both_reset_failure_headlines() {
    let backup = render_resume_error(&ResumeError::LocalIgnoreResetBackupFailure(reset_failure()));
    let replacement = render_resume_error(&ResumeError::LocalIgnoreResetReplacementFailure(
        reset_failure(),
    ));

    assert_eq!(
        backup,
        vec![
            DisplayLine {
                severity: Failure,
                segments: vec![Text(
                    "Crash Log Scan recovery failed - Local Ignore could not be backed up before reset"
                )],
            },
            DisplayLine {
                severity: Failure,
                segments: vec![Emphasis("the replacement could not be written".to_string())],
            },
            DisplayLine {
                severity: Info,
                segments: vec![
                    Text("Path:"),
                    Path(PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml")),
                ],
            },
            DisplayLine {
                severity: Info,
                segments: vec![Text("Stage:"), Label("write")],
            },
        ]
    );
    assert_eq!(
        replacement[0],
        DisplayLine {
            severity: Failure,
            segments: vec![Text(
                "Crash Log Scan recovery failed - the Local Ignore defaults could not be published"
            )],
        }
    );
}

/// Verifies an unconfirmed-durability reset reads as a receipt, not as "nothing happened".
#[test]
fn resume_error_pins_unconfirmed_durability() {
    let failure = LocalIgnoreResetDurabilityUnknownError {
        path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml"),
        backup_path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml.bak"),
        malformed_identity: YamlDataContentIdentity::from_bytes(b"malformed"),
        backup_identity: YamlDataContentIdentity::from_bytes(b"malformed"),
        replacement_identity: YamlDataContentIdentity::from_bytes(b"defaults"),
        message: "the directory sync did not confirm".to_string(),
    };
    let malformed_hex = failure.malformed_identity.sha256_hex();
    let replacement_hex = failure.replacement_identity.sha256_hex();

    let lines = render_resume_error(&ResumeError::LocalIgnoreResetDurabilityUnknown(Box::new(
        failure,
    )));

    assert_eq!(
        lines,
        vec![
            DisplayLine {
                severity: Warning,
                segments: vec![Text(
                    "Local Ignore was reset, but the replacement is not confirmed durable"
                )],
            },
            DisplayLine {
                severity: Warning,
                segments: vec![Emphasis("the directory sync did not confirm".to_string())],
            },
            DisplayLine {
                severity: Info,
                segments: vec![
                    Text("Path:"),
                    Path(PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml")),
                ],
            },
            DisplayLine {
                severity: Info,
                segments: vec![
                    Text("Verified backup:"),
                    Path(PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml.bak")),
                ],
            },
            DisplayLine {
                severity: Info,
                segments: vec![Text("Malformed sha256"), Emphasis(malformed_hex.clone())],
            },
            DisplayLine {
                severity: Info,
                segments: vec![Text("Backup sha256"), Emphasis(malformed_hex)],
            },
            DisplayLine {
                severity: Info,
                segments: vec![Text("Replacement sha256"), Emphasis(replacement_hex)],
            },
        ]
    );
}

/// Verifies an infrastructure resume failure reuses the infrastructure prose beneath its own
/// headline, rather than restating the stage in a second sentence.
#[test]
fn resume_error_pins_an_infrastructure_failure() {
    let error = ResumeError::Infrastructure(InfrastructureError {
        stage: InfrastructureErrorStage::Intake,
        message: "intake could not reopen the snapshot".to_string(),
        path: None,
    });

    assert_eq!(
        render_resume_error(&error),
        vec![
            DisplayLine {
                severity: Failure,
                segments: vec![Text("Crash Log Scan recovery failed")],
            },
            DisplayLine {
                severity: Failure,
                segments: vec![
                    Text("Crash Log Scan Run failed during"),
                    Label("intake"),
                    Text("-"),
                    Emphasis("intake could not reopen the snapshot".to_string()),
                ],
            },
        ]
    );
}

// -- per-log outcome line ---------------------------------------------------------------

/// Verifies a successful log states its position, whole path, disposition, and report.
///
/// The path is carried whole. Truncating it to a filename is Display Layout, and a frontend
/// that wants to link to the Autoscan Report needs the path that reaches it.
#[test]
fn per_log_outcome_pins_a_success_with_a_report() {
    let mut result = run_result(RunStatus::Completed);
    let mut log = log_result(LogDisposition::Succeeded);
    log.autoscan_report = Some(PathBuf::from("C:/logs/crash-2024-AUTOSCAN.md"));
    log.moved_to_unsolved_logs = true;
    result.total = 1;
    result.succeeded = 1;
    result.logs = vec![log];

    let lines = render_run_result(&result);

    assert_eq!(
        lines[2],
        DisplayLine {
            severity: Success,
            segments: vec![
                Emphasis("3".to_string()),
                Text("-"),
                Path(PathBuf::from("C:/logs/crash-2024.log")),
                Text("-"),
                Label("succeeded"),
                Text("- report"),
                Path(PathBuf::from("C:/logs/crash-2024-AUTOSCAN.md")),
                Text("- moved to Unsolved Logs"),
            ],
        }
    );
}

/// Verifies a failed log states each structured failure by stage beneath its outcome line.
#[test]
fn per_log_outcome_pins_a_failure_and_its_stages() {
    let mut result = run_result(RunStatus::Completed);
    let mut log = log_result(LogDisposition::Failed);
    log.failures = vec![LogFailure {
        stage: LogFailureStage::UnsolvedLogsFinalization,
        message: "the destination directory is read-only".to_string(),
    }];
    result.total = 1;
    result.failed = 1;
    result.logs = vec![log];

    let lines = render_run_result(&result);

    assert_eq!(
        lines[2],
        DisplayLine {
            severity: Failure,
            segments: vec![
                Emphasis("3".to_string()),
                Text("-"),
                Path(PathBuf::from("C:/logs/crash-2024.log")),
                Text("-"),
                Label("failed"),
            ],
        }
    );
    assert_eq!(
        lines[3],
        DisplayLine {
            severity: Failure,
            segments: vec![
                Label("Unsolved Logs finalization"),
                Text("-"),
                Emphasis("the destination directory is read-only".to_string()),
            ],
        }
    );
}

/// Verifies a log carrying only a message states it, since nothing else would.
#[test]
fn per_log_outcome_states_a_message_without_structured_failures() {
    let mut result = run_result(RunStatus::Cancelled);
    let mut log = log_result(LogDisposition::CancelledBeforeStart);
    log.message = Some("cancelled before admission".to_string());
    result.total = 1;
    result.cancelled = 1;
    result.logs = vec![log];

    let lines = render_run_result(&result);

    assert_eq!(lines[2].severity, Notice);
    assert_eq!(
        lines[3],
        DisplayLine {
            severity: Notice,
            segments: vec![Emphasis("cancelled before admission".to_string())],
        }
    );
}

// -- Installed YAML Data block ----------------------------------------------------------

/// Verifies the block opens with its header.
///
/// The header is the block's only fixed prose that is not a Display Label, so without this it
/// would be the one core-owned sentence no invariant test ever sees.
#[test]
fn installed_yaml_data_pins_its_header() {
    assert_eq!(
        render_installed_yaml_data_header(),
        DisplayLine {
            severity: Info,
            segments: vec![Text("Installed YAML Data")],
        }
    );
}

/// Verifies a selected YAML Data file states its role, provenance, schema, and identity.
#[test]
fn installed_yaml_data_pins_a_selected_file_line() {
    let identity = YamlDataContentIdentity::from_bytes(b"main bytes");

    assert_eq!(
        render_yaml_data_file(
            InstalledYamlDataRole::Main,
            InstalledYamlDataProvenance::Bundled,
            "9.0",
            &identity,
        ),
        DisplayLine {
            severity: Info,
            segments: vec![
                // `Selected` leads so the role label is never line-initial. See
                // `role_labels_are_never_line_initial` for why that matters.
                Text("Selected"),
                Label("Main"),
                Text("YAML Data:"),
                Label("bundled"),
                Text("- schema"),
                Emphasis("9.0".to_string()),
                Text("- sha256"),
                Emphasis(identity.sha256_hex()),
                Text("-"),
                Count {
                    value: 10,
                    noun: "bytes"
                },
            ],
        }
    );
}

/// Verifies the Local Ignore line states how the file entered the run, and warns on recovery.
#[test]
fn installed_yaml_data_pins_the_local_ignore_line() {
    let identity = YamlDataContentIdentity::from_bytes(b"x");

    assert_eq!(
        render_local_ignore(LocalIgnoreRunState::RecoveryRequired, &identity),
        DisplayLine {
            severity: Warning,
            segments: vec![
                Text("Local Ignore:"),
                Label("recovery required"),
                Text("- sha256"),
                Emphasis(identity.sha256_hex()),
                Text("-"),
                Count {
                    value: 1,
                    noun: "byte"
                },
            ],
        }
    );
    assert_eq!(
        render_local_ignore(LocalIgnoreRunState::Existing, &identity).severity,
        Info
    );
}

/// Verifies a completed reset reports where the user's original bytes went.
#[test]
fn installed_yaml_data_pins_the_reset_receipt_lines() {
    let reset = LocalIgnoreResetRunData {
        local_ignore_path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml"),
        backup_path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml.bak"),
        malformed_identity: YamlDataContentIdentity::from_bytes(b"malformed"),
        backup_identity: YamlDataContentIdentity::from_bytes(b"malformed"),
        replacement_identity: YamlDataContentIdentity::from_bytes(b"defaults"),
    };

    assert_eq!(
        render_local_ignore_reset(&reset),
        [
            DisplayLine {
                severity: Info,
                segments: vec![
                    Text("Local Ignore backup:"),
                    Path(PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml.bak")),
                    Text("- sha256"),
                    Emphasis(reset.backup_identity.sha256_hex()),
                ],
            },
            DisplayLine {
                severity: Info,
                segments: vec![
                    Text("Local Ignore replacement:"),
                    Path(PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml")),
                    Text("- sha256"),
                    Emphasis(reset.replacement_identity.sha256_hex()),
                ],
            },
        ]
    );
}

/// Verifies a diagnostic states its category and message, then only the context it has.
#[test]
fn installed_yaml_data_pins_a_diagnostic_line() {
    let path = PathBuf::from("C:/CLASSIC/CLASSIC Data/databases/CLASSIC Fallout4.yaml");

    assert_eq!(
        render_installed_yaml_data_diagnostic(
            Some(InstalledYamlDataRole::Game),
            Some(InstalledYamlDataProvenance::Updated),
            Some(path.as_path()),
            InstalledYamlDataRunDiagnosticKind::IncompatibleSchema,
            "schema 10.0 is newer than this client understands",
        ),
        DisplayLine {
            severity: Warning,
            segments: vec![
                Label("incompatible schema"),
                Text("-"),
                Emphasis("schema 10.0 is newer than this client understands".to_string()),
                Text("- role"),
                Label("game"),
                Text("- candidate"),
                Label("updated"),
                Text("- path"),
                Path(path),
            ],
        }
    );
}

/// Verifies a context-free diagnostic renders exactly three segments.
#[test]
fn installed_yaml_data_omits_absent_diagnostic_context() {
    let line = render_installed_yaml_data_diagnostic(
        None,
        None,
        None,
        InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated,
        "Local Ignore was generated from Main defaults",
    );

    assert_eq!(line.severity, Notice);
    assert_eq!(line.segments.len(), 3);
}

// -- per-event progress line ------------------------------------------------------------

/// Verifies each log-scoped event states its action, path, and position in the run.
///
/// The two lifecycle steps with no enum behind them use fixed prose; the phase and the
/// disposition use their Display Labels. All four read as lowercase participles, so a
/// frontend that upper-cases a line-initial word applies one rule rather than two.
#[test]
fn per_event_progress_pins_every_log_scoped_event() {
    let log = log_event(12);
    let position = vec![
        Text("-"),
        Emphasis("3".to_string()),
        Text("of"),
        Count {
            value: 12,
            noun: "logs",
        },
    ];
    let cases = [
        (Event::LogQueued(log.clone()), Text("queued"), Info),
        (Event::LogStarted(log.clone()), Text("scanning"), Info),
        (
            Event::LogPhase {
                log: log.clone(),
                phase: ScanProgressPhase::Analyze,
            },
            Label("analyzing"),
            Info,
        ),
        (
            Event::LogFinished {
                log: log.clone(),
                disposition: LogDisposition::CancelledBeforeStart,
            },
            Label("cancelled before start"),
            Notice,
        ),
    ];

    for (event, action, severity) in cases {
        let mut segments = vec![action, Path(PathBuf::from("C:/logs/crash-2024.log"))];
        segments.extend(position.clone());

        assert_eq!(
            render_event(&event),
            vec![DisplayLine { severity, segments }],
            "unexpected progress line for {event:?}"
        );
    }
}

/// Verifies a discovery event states acceptance and rejection on separate lines.
///
/// Two lines rather than one parenthetical, so a frontend can style or suppress the
/// rejection without losing the acceptance count. Grouping them back together is Display
/// Layout.
#[test]
fn per_event_progress_pins_discovery_completion() {
    assert_eq!(
        render_event(&Event::DiscoveryCompleted(discovery(1, 2, 0))),
        vec![
            DisplayLine {
                severity: Info,
                segments: vec![
                    Text("Discovered"),
                    Count {
                        value: 1,
                        noun: "crash log"
                    },
                ],
            },
            DisplayLine {
                severity: Notice,
                segments: vec![
                    Text("Rejected"),
                    Count {
                        value: 2,
                        noun: "targeted inputs"
                    },
                ],
            },
        ]
    );
}

/// Verifies a discovery that rejected nothing produces no rejection line.
#[test]
fn per_event_progress_omits_an_empty_rejection_line() {
    assert_eq!(
        render_event(&Event::DiscoveryCompleted(discovery(3, 0, 0))).len(),
        1
    );
}

/// Verifies the selected concurrency is stated as a count with its own noun.
#[test]
fn per_event_progress_pins_selected_concurrency() {
    assert_eq!(
        render_event(&Event::EffectiveConcurrencySelected {
            effective_concurrency: 1
        }),
        vec![DisplayLine {
            severity: Info,
            segments: vec![
                Text("Selected"),
                Count {
                    value: 1,
                    noun: "concurrent scan"
                },
            ],
        }]
    );
}

// -- Local Ignore recovery decision descriptions -----------------------------------------

/// Verifies the prompt states why the run paused and names the file being decided about.
#[test]
fn recovery_prompt_pins_its_situation_lines() {
    let identity = YamlDataContentIdentity::from_bytes(b"malformed");

    let prompt = render_recovery_prompt(
        Some((LocalIgnoreRunState::RecoveryRequired, &identity)),
        true,
    );

    assert_eq!(
        prompt.lines,
        vec![
            DisplayLine {
                severity: Warning,
                segments: vec![Text(
                    "Your Local Ignore file is malformed, so this Crash Log Scan is paused until you choose how to continue."
                )],
            },
            render_local_ignore(LocalIgnoreRunState::RecoveryRequired, &identity),
        ]
    );
}

/// Verifies both decisions are described, in the contract's own variant order.
///
/// The descriptions are the locked Display Content this ticket exists to produce: pinned
/// once here, and identical in every frontend and on every binding surface.
#[test]
fn recovery_prompt_pins_both_decision_descriptions() {
    let identity = YamlDataContentIdentity::from_bytes(b"malformed");

    let prompt = render_recovery_prompt(
        Some((LocalIgnoreRunState::RecoveryRequired, &identity)),
        true,
    );

    assert_eq!(
        prompt.decisions,
        vec![
            RecoveryDecisionDescription {
                decision: LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
                label: "Proceed Without Ignore",
                description: vec![Text(
                    "Scan now with an empty ignore list. Your malformed Local Ignore file is left exactly as it is, and this choice applies to this scan only."
                )],
                available: true,
            },
            RecoveryDecisionDescription {
                decision: LocalIgnoreRecoveryDecision::ResetToDefault,
                label: "Reset To Default",
                description: vec![Text(
                    "Back up your malformed Local Ignore file byte-exactly, replace it with the selected Main defaults, then scan."
                )],
                available: true,
            },
        ]
    );
}

/// Verifies an unavailable reset stays listed, marked unavailable, and says why.
///
/// Listed rather than dropped on purpose. A frontend must be able to explain the absence it
/// is about to create, and it can only do that if core tells it what it is withholding.
#[test]
fn recovery_prompt_marks_an_unavailable_reset_and_explains_it() {
    let identity = YamlDataContentIdentity::from_bytes(b"malformed");

    let prompt = render_recovery_prompt(
        Some((LocalIgnoreRunState::RecoveryRequired, &identity)),
        false,
    );

    assert_eq!(
        prompt.lines.last(),
        Some(&DisplayLine {
            severity: Notice,
            segments: vec![Text(
                "Reset To Default is unavailable: the selected Main YAML Data retains no usable default Local Ignore to publish."
            )],
        })
    );
    let unavailable: Vec<LocalIgnoreRecoveryDecision> = prompt
        .decisions
        .iter()
        .filter(|description| !description.available)
        .map(|description| description.decision)
        .collect();
    assert_eq!(
        unavailable,
        vec![LocalIgnoreRecoveryDecision::ResetToDefault]
    );
}

/// Verifies proceeding is never withdrawn, whatever the run reported about reset.
///
/// This is the asymmetry that makes availability a per-decision field rather than one flag
/// beside the prompt: Proceed Without Ignore needs nothing from the installation, so nothing
/// can make it unavailable.
#[test]
fn recovery_prompt_never_withdraws_proceeding() {
    let identity = YamlDataContentIdentity::from_bytes(b"malformed");

    for reset_available in [true, false] {
        let prompt = render_recovery_prompt(
            Some((LocalIgnoreRunState::RecoveryRequired, &identity)),
            reset_available,
        );
        let proceed = prompt
            .decisions
            .iter()
            .find(|description| {
                description.decision == LocalIgnoreRecoveryDecision::ProceedWithoutIgnore
            })
            .expect("Proceed Without Ignore is always described");
        assert!(proceed.available);
    }
}

/// Verifies the prompt describes exactly the decisions the continuation contract accepts.
///
/// Backing out is deliberately not among them: it is spelled as the *absence* of a decision
/// and reaches the contract through `abandon`, so a frontend's cancel affordance is its own.
#[test]
fn recovery_prompt_describes_every_contract_decision_and_no_others() {
    let identity = YamlDataContentIdentity::from_bytes(b"malformed");

    let prompt = render_recovery_prompt(
        Some((LocalIgnoreRunState::RecoveryRequired, &identity)),
        true,
    );

    let described: Vec<LocalIgnoreRecoveryDecision> = prompt
        .decisions
        .iter()
        .map(|description| description.decision)
        .collect();
    assert_eq!(described, LocalIgnoreRecoveryDecision::VARIANTS.to_vec());
    assert_eq!(LocalIgnoreRecoveryDecision::VARIANTS.len(), 2);
}

/// Verifies a run that reported no Installed YAML Data keeps every decision on offer.
///
/// A run that reported nothing has not reported a denial. Withdrawing an option on silence
/// would regress the behaviour that shipped before the availability fact existed, and this
/// is the one place that rule is now written — the three frontends each used to write it.
#[test]
fn recovery_prompt_treats_absent_installed_yaml_data_as_available() {
    let prompt = render_local_ignore_recovery(None);

    assert!(
        prompt
            .decisions
            .iter()
            .all(|description| description.available)
    );
    // Nothing is claimed about a file whose identity the run never reported.
    assert_eq!(prompt.lines.len(), 1);
}

// -- crate-wide invariants --------------------------------------------------------------

/// Renders every path this crate has, so the invariant tests below see all of its output.
///
/// Values are chosen to exercise both grammatical numbers: each count appears somewhere with
/// a value of one and somewhere with a value that is not one.
fn rendered_corpus() -> Vec<DisplayLine> {
    let mut lines = Vec::new();

    for status in [
        RunStatus::Completed,
        RunStatus::NoCrashLogsFound,
        RunStatus::SetupFailed,
        RunStatus::LocalIgnoreRecoveryRequired,
        RunStatus::CancelledBeforeDiscovery,
        RunStatus::Cancelled,
    ] {
        for (total, succeeded, failed, cancelled) in [(1, 1, 0, 0), (3, 1, 1, 1), (5, 2, 2, 1)] {
            let mut result = run_result(status);
            result.total = total;
            // The `(3, 1, 1, 1)` case is what renders a singular error count; without it the
            // grammatical-number test would never see `1 error`.
            result.succeeded = succeeded;
            result.failed = failed;
            result.cancelled = cancelled;
            result.message = Some("a run-level message".to_string());
            result.effective_concurrency = Some(if total == 1 { 1 } else { 4 });
            result.discovery = Some(discovery(total, cancelled, total));
            result.logs = [
                LogDisposition::Succeeded,
                LogDisposition::Failed,
                LogDisposition::CancelledBeforeStart,
            ]
            .into_iter()
            .map(|disposition| {
                let mut log = log_result(disposition);
                log.autoscan_report = Some(PathBuf::from("C:/logs/report.md"));
                log.moved_to_unsolved_logs = true;
                log.message = Some("a log-level message".to_string());
                log.failures = vec![LogFailure {
                    stage: LogFailureStage::Analysis,
                    message: "analysis failed".to_string(),
                }];
                log
            })
            .collect();
            lines.extend(render_run_result(&result));

            // A log carrying no structured failure takes the message branch instead.
            let mut bare = run_result(status);
            bare.logs = vec![log_result(LogDisposition::Failed)];
            lines.extend(render_run_result(&bare));
        }
    }

    for total in [1, 12] {
        let log = log_event(total);
        for event in [
            Event::LogQueued(log.clone()),
            Event::LogStarted(log.clone()),
            Event::LogFinished {
                log: log.clone(),
                disposition: LogDisposition::Succeeded,
            },
        ] {
            lines.extend(render_event(&event));
        }
        for phase in [
            ScanProgressPhase::Setup,
            ScanProgressPhase::Parse,
            ScanProgressPhase::Analyze,
            ScanProgressPhase::Finalize,
        ] {
            lines.extend(render_event(&Event::LogPhase {
                log: log.clone(),
                phase,
            }));
        }
        lines.extend(render_event(&Event::EffectiveConcurrencySelected {
            effective_concurrency: total,
        }));
        lines.extend(render_event(&Event::DiscoveryCompleted(discovery(
            total, total, total,
        ))));
    }

    for stage in [
        InfrastructureErrorStage::RequestValidation,
        InfrastructureErrorStage::Discovery,
        InfrastructureErrorStage::Intake,
        InfrastructureErrorStage::FormIdDatabaseAccess,
        InfrastructureErrorStage::Initialization,
        InfrastructureErrorStage::InternalInvariant,
    ] {
        for path in [None, Some(PathBuf::from("C:/CLASSIC/data"))] {
            lines.extend(render_infrastructure_error(&InfrastructureError {
                stage,
                message: "a diagnostic".to_string(),
                path,
            }));
        }
    }

    let identity = YamlDataContentIdentity::from_bytes(b"contents");
    for error in [
        ResumeError::ContinuationConsumed,
        ResumeError::LocalIgnoreResetConflict(LocalIgnoreResetConflictError {
            expected_identity: identity.clone(),
            actual_identity: Some(identity.clone()),
            backup_path: Some(PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml.bak")),
        }),
        ResumeError::LocalIgnoreResetConflict(LocalIgnoreResetConflictError {
            expected_identity: identity.clone(),
            actual_identity: None,
            backup_path: None,
        }),
        ResumeError::LocalIgnoreResetBackupFailure(reset_failure()),
        ResumeError::LocalIgnoreResetReplacementFailure(LocalIgnoreResetFailure {
            path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml"),
            stage: None,
            message: "no stage was reached".to_string(),
        }),
        ResumeError::LocalIgnoreResetDurabilityUnknown(Box::new(
            LocalIgnoreResetDurabilityUnknownError {
                path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml"),
                backup_path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml.bak"),
                malformed_identity: identity.clone(),
                backup_identity: identity.clone(),
                replacement_identity: identity.clone(),
                message: "durability unconfirmed".to_string(),
            },
        )),
        ResumeError::Infrastructure(InfrastructureError {
            stage: InfrastructureErrorStage::Discovery,
            message: "a diagnostic".to_string(),
            path: None,
        }),
    ] {
        lines.extend(render_resume_error(&error));
    }

    // The Installed YAML Data block, whose contract types have no public constructor and so
    // cannot reach `render_run_result` from a test. Its line renderers are called here for the
    // same reason, so that the invariant tests below see the block's prose at all.
    lines.push(render_installed_yaml_data_header());
    for role in [InstalledYamlDataRole::Main, InstalledYamlDataRole::Game] {
        for provenance in [
            InstalledYamlDataProvenance::Updated,
            InstalledYamlDataProvenance::Previous,
            InstalledYamlDataProvenance::Bundled,
        ] {
            for bytes in [b"x".as_slice(), b"longer contents".as_slice()] {
                lines.push(render_yaml_data_file(
                    role,
                    provenance,
                    "9.0",
                    &YamlDataContentIdentity::from_bytes(bytes),
                ));
            }
        }
    }
    for state in [
        LocalIgnoreRunState::Existing,
        LocalIgnoreRunState::Generated,
        LocalIgnoreRunState::RecoveryRequired,
        LocalIgnoreRunState::ProceedWithoutIgnore,
        LocalIgnoreRunState::ResetToDefault,
    ] {
        for bytes in [b"x".as_slice(), b"longer contents".as_slice()] {
            lines.push(render_local_ignore(
                state,
                &YamlDataContentIdentity::from_bytes(bytes),
            ));
        }
    }
    lines.extend(render_local_ignore_reset(&LocalIgnoreResetRunData {
        local_ignore_path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml"),
        backup_path: PathBuf::from("C:/CLASSIC/CLASSIC Ignore.yaml.bak"),
        malformed_identity: identity.clone(),
        backup_identity: identity.clone(),
        replacement_identity: identity,
    }));
    for kind in [
        InstalledYamlDataRunDiagnosticKind::CacheUnavailable,
        InstalledYamlDataRunDiagnosticKind::Missing,
        InstalledYamlDataRunDiagnosticKind::Read,
        InstalledYamlDataRunDiagnosticKind::InvalidUtf8,
        InstalledYamlDataRunDiagnosticKind::Parse,
        InstalledYamlDataRunDiagnosticKind::InvalidSchema,
        InstalledYamlDataRunDiagnosticKind::IncompatibleSchema,
        InstalledYamlDataRunDiagnosticKind::InvalidRoleData,
        InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated,
        InstalledYamlDataRunDiagnosticKind::LocalIgnoreReset,
    ] {
        lines.push(render_installed_yaml_data_diagnostic(
            Some(InstalledYamlDataRole::Main),
            Some(InstalledYamlDataProvenance::Bundled),
            Some(std::path::Path::new("C:/CLASSIC/main.yaml")),
            kind,
            "a diagnostic",
        ));
        lines.push(render_installed_yaml_data_diagnostic(
            None,
            None,
            None,
            kind,
            "a diagnostic",
        ));
    }

    // The Local Ignore recovery prompt, in all three shapes it takes. Its decision
    // descriptions are segment lists rather than lines, so they are wrapped as lines here:
    // the invariant tests below read segments, and prose reaching a user through a
    // description must be held to the same rule as prose reaching one through a line.
    let mut prompts = vec![render_local_ignore_recovery(None)];
    for reset_available in [true, false] {
        prompts.push(render_recovery_prompt(
            Some((
                LocalIgnoreRunState::RecoveryRequired,
                &YamlDataContentIdentity::from_bytes(b"malformed"),
            )),
            reset_available,
        ));
    }
    for prompt in prompts {
        lines.extend(prompt.lines);
        lines.extend(prompt.decisions.into_iter().map(|description| DisplayLine {
            severity: Notice,
            segments: description.description,
        }));
    }

    lines
}

/// Verifies no fixed-prose segment carries a placeholder character.
///
/// A placeholder in core-owned prose would mean core had gone back to interpolating, which
/// is the practice that produced the duplicated pluralization helpers this crate replaces.
/// Counts, paths, and names travel as their own segments precisely so no sentence has a hole
/// in it for an adapter to fill.
#[test]
fn fixed_prose_never_carries_a_placeholder() {
    const PLACEHOLDERS: [char; 4] = ['{', '}', '%', '$'];

    for line in rendered_corpus() {
        for segment in line.segments {
            let prose = match segment {
                Text(text) | Label(text) => text,
                Count { .. } | Path(_) | DisplaySegment::Name(_) | Emphasis(_) => continue,
            };
            assert!(
                !prose.contains(PLACEHOLDERS),
                "fixed prose {prose:?} carries a placeholder character"
            );
        }
    }
}

/// Verifies the selected-file line never opens on the role's Display Label.
///
/// `InstalledYamlDataRole`'s label is asymmetric on purpose: `Main` names a glossary domain
/// term and `game` is the ordinary adjective in "selected-game YAML Data". That is correct
/// where the label was designed to appear — mid-sentence, as in
/// `no usable Installed YAML Data source for game` — and wrong at the start of a line, where
/// `game YAML Data: bundled …` sitting under `Main YAML Data: bundled …` reads as a
/// capitalization bug rather than as the distinction it is.
///
/// Deliberately narrow. A general "no line opens on a lowercase label" rule would be wrong:
/// the per-event progress lines open on lowercase participles by design, so that a frontend
/// which upper-cases a line-initial word applies one rule to all four rather than
/// compensating for two shapes.
#[test]
fn a_selected_file_line_never_opens_on_its_role_label() {
    for role in [InstalledYamlDataRole::Main, InstalledYamlDataRole::Game] {
        let line = render_yaml_data_file(
            role,
            InstalledYamlDataProvenance::Bundled,
            "9.0",
            &YamlDataContentIdentity::from_bytes(b"bytes"),
        );
        assert_eq!(
            line.segments.first(),
            Some(&Text("Selected")),
            "the {role:?} line opens on something other than fixed prose"
        );
    }
}

/// Verifies every count's noun agrees with its value's grammatical number.
///
/// This is what stops a run reporting "1 logs". Agreement is already structural — a renderer
/// names a noun pair and never picks between its forms — so this test guards the seam that
/// structure cannot: a noun reaching a segment without being registered as a pair at all.
#[test]
fn every_count_agrees_with_its_value() {
    let mut counted = 0_usize;

    for line in rendered_corpus() {
        for segment in line.segments {
            let DisplaySegment::Count { value, noun } = segment else {
                continue;
            };
            let pair = registered_noun(noun)
                .unwrap_or_else(|| panic!("{noun:?} is not a registered counted noun"));
            assert_eq!(
                noun,
                pair.for_value(value),
                "{value} does not agree with the noun {noun:?}"
            );
            counted += 1;
        }
    }

    assert!(counted > 0, "the corpus rendered no counts to check");
}

/// Verifies every registered noun reaches the corpus in both grammatical numbers.
///
/// The agreement test above can only check the counts it is shown, so a noun the corpus
/// never renders in the singular would let it pass while checking nothing about the form a
/// user is most likely to notice. This is the test that fails when a fixture stops covering
/// a form — or when a noun is registered and then never counted with at all.
#[test]
fn the_corpus_exercises_every_noun_in_both_numbers() {
    let mut seen: Vec<&'static str> = Vec::new();
    for line in rendered_corpus() {
        for segment in line.segments {
            if let DisplaySegment::Count { noun, .. } = segment {
                seen.push(noun);
            }
        }
    }

    for noun in COUNTED_NOUNS {
        let singular = noun.for_value(1);
        let plural = noun.for_value(2);
        assert!(
            seen.contains(&singular),
            "no fixture renders {singular:?} in the singular"
        );
        assert!(
            seen.contains(&plural),
            "no fixture renders {plural:?} in the plural"
        );
    }
}
