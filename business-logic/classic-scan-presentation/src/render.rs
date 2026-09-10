//! The render entry points that decide what a Crash Log Scan Run says.
//!
//! Every function here is pure over a borrowed contract value, so wording can be pinned
//! without running a scan.

use crate::display::{
    BYTE, CONCURRENT_SCAN, CRASH_LOG, DisplayLine, DisplaySegment, DisplaySeverity, LOG,
    SEARCHED_LOCATION, TARGETED_INPUT, count, count_usize,
};
use classic_config_core::{
    InstalledYamlDataProvenance, InstalledYamlDataRole, YamlDataContentIdentity,
};
use classic_scanlog_core::scan_run::contract::{
    Event, InfrastructureError, InstalledYamlDataRunData, InstalledYamlDataRunDiagnosticKind,
    LocalIgnoreResetConflictError, LocalIgnoreResetDurabilityUnknownError, LocalIgnoreResetFailure,
    LocalIgnoreResetRunData, LocalIgnoreRunState, LogDisposition, LogEvent, LogResult, ResumeError,
    RunResult, RunStatus,
};
use classic_scanlog_core::{CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource};
use classic_vocabulary::Vocabulary;
use std::fmt;
use std::path::Path;

use DisplaySegment::{Emphasis, Label, Path as PathSegment, Text};
use DisplaySeverity::{Failure, Info, Notice, Success, Warning};

/// Renders a terminal Crash Log Scan Run Result.
///
/// # Continuation ordering
///
/// This takes a reference because a [`RunResult`] is not clonable — it retains a one-shot
/// Crash Log Scan Run Continuation. Take the continuation out of the result **before**
/// rendering:
///
/// ```ignore
/// let continuation = result.continuation.take();
/// let lines = render_run_result(&result);
/// ```
///
/// Rendering first and moving the continuation afterwards borrows the result across the
/// move and will not compile. All three native frontends already sequence it this way; this
/// note makes the ordering a contract rather than a coincidence.
///
/// # What is not rendered
///
/// The FCX Mode setup projection is deliberately absent. Its check state, check kind, issue
/// severity, and update kind are four types in a different subsystem that have not adopted
/// the shared vocabulary, so rendering them here would mean inventing prose for machine
/// identifiers — the exact failure this crate exists to remove. Adapters keep their existing
/// `Display`-based setup projection until those types adopt `Vocabulary` in their own change.
#[must_use]
pub fn render_run_result(result: &RunResult) -> Vec<DisplayLine> {
    let mut lines = vec![render_terminal_status(result)];

    if let Some(message) = result.message.as_deref() {
        lines.push(DisplayLine::new(
            Info,
            vec![Text("Message:"), Emphasis(message.to_string())],
        ));
    }
    if let Some(discovery) = result.discovery.as_ref() {
        append_discovery(discovery, &mut lines);
    }
    if let Some(effective_concurrency) = result.effective_concurrency {
        lines.push(DisplayLine::new(
            Info,
            vec![
                Text("Effective concurrency:"),
                count_usize(effective_concurrency, CONCURRENT_SCAN),
            ],
        ));
    }
    if let Some(installed) = result.installed_yaml_data.as_ref() {
        append_installed_yaml_data(installed, &mut lines);
    }

    lines.push(render_outcome_summary(result));
    for log in &result.logs {
        append_log_outcome(log, &mut lines);
    }
    lines
}

/// Renders one observed Crash Log Scan Run event.
///
/// A single event can produce more than one line — a discovery that rejected some of its
/// targeted inputs states the rejection separately, so a frontend can style or suppress it
/// without losing the acceptance count.
#[must_use]
pub fn render_event(event: &Event) -> Vec<DisplayLine> {
    match event {
        Event::DiscoveryCompleted(discovery) => {
            let mut lines = vec![DisplayLine::new(
                Info,
                vec![
                    Text("Discovered"),
                    count_usize(discovery.accepted_logs.len(), CRASH_LOG),
                ],
            )];
            let rejected = discovery.rejected_inputs.len();
            if rejected > 0 {
                lines.push(DisplayLine::new(
                    Notice,
                    vec![Text("Rejected"), count_usize(rejected, TARGETED_INPUT)],
                ));
            }
            lines
        }
        Event::EffectiveConcurrencySelected {
            effective_concurrency,
        } => vec![DisplayLine::new(
            Info,
            vec![
                Text("Selected"),
                count_usize(*effective_concurrency, CONCURRENT_SCAN),
            ],
        )],
        Event::LogQueued(log) => vec![render_progress(log, Text("queued"), Info)],
        Event::LogStarted(log) => vec![render_progress(log, Text("scanning"), Info)],
        Event::LogPhase { log, phase } => vec![render_progress(log, Label(phase.label()), Info)],
        Event::LogFinished { log, disposition } => vec![render_progress(
            log,
            Label(disposition.label()),
            severity_for_disposition(*disposition),
        )],
    }
}

/// Renders a run-wide infrastructure failure.
///
/// The stage reads as its Display Label, never as its Vocabulary Token. A user should not
/// have to know that `formid_database_access` means "FormID database access".
#[must_use]
pub fn render_infrastructure_error(error: &InfrastructureError) -> Vec<DisplayLine> {
    let mut lines = vec![DisplayLine::new(
        Failure,
        vec![
            Text("Crash Log Scan Run failed during"),
            Label(error.stage.label()),
            Text("-"),
            Emphasis(error.message.clone()),
        ],
    )];
    if let Some(path) = error.path.as_ref() {
        lines.push(path_line(Info, "Path:", path));
    }
    lines
}

/// Renders a failure to resume a paused Crash Log Scan Run.
///
/// The stable resume error code is deliberately absent: it is a machine-facing identifier
/// and belongs in structured output, not in a sentence. Each category is instead
/// distinguished by prose, because the distinctions are what a user acts on — whether
/// nothing changed, whether a backup exists, or whether a repair landed but is unconfirmed.
#[must_use]
pub fn render_resume_error(error: &ResumeError) -> Vec<DisplayLine> {
    match error {
        ResumeError::ContinuationConsumed => vec![
            DisplayLine::new(
                Failure,
                vec![Text(
                    "Crash Log Scan recovery failed - this recovery decision was already applied",
                )],
            ),
            DisplayLine::new(
                Notice,
                vec![Text("Start the Crash Log Scan again to retry.")],
            ),
        ],
        ResumeError::LocalIgnoreResetConflict(conflict) => render_reset_conflict(conflict),
        ResumeError::LocalIgnoreResetBackupFailure(failure) => render_reset_failure(
            "Crash Log Scan recovery failed - Local Ignore could not be backed up before reset",
            failure,
        ),
        ResumeError::LocalIgnoreResetReplacementFailure(failure) => render_reset_failure(
            "Crash Log Scan recovery failed - the Local Ignore defaults could not be published",
            failure,
        ),
        ResumeError::LocalIgnoreResetDurabilityUnknown(failure) => {
            render_reset_durability_unknown(failure)
        }
        ResumeError::Infrastructure(infrastructure) => {
            let mut lines = vec![DisplayLine::new(
                Failure,
                vec![Text("Crash Log Scan recovery failed")],
            )];
            lines.extend(render_infrastructure_error(infrastructure));
            lines
        }
    }
}

/// Renders the one line that states how the run as a whole ended.
///
/// Every branch leads with the status Display Label, so the six outcomes are named from one
/// place instead of being described in prose each frontend invented. Counts follow only
/// where they say something the label cannot.
fn render_terminal_status(result: &RunResult) -> DisplayLine {
    let label = Label(result.status.label());
    let completed = result.succeeded + result.failed;

    match result.status {
        // `total` counts what discovery accepted, which is not the same as what was scanned
        // once some of it was never started — so this branch says "discovered" and lets the
        // two following counts account for the difference. Saying "scanned" here alongside a
        // not-started count would claim more logs than the run had.
        RunStatus::Completed if result.failed > 0 || result.cancelled > 0 => DisplayLine::new(
            Warning,
            vec![
                label,
                Text("-"),
                count_usize(result.total, LOG),
                Text("discovered,"),
                count_usize(result.failed, LOG),
                Text("failed and"),
                count_usize(result.cancelled, LOG),
                Text("not started"),
            ],
        ),
        RunStatus::Completed => DisplayLine::new(
            Success,
            vec![
                label,
                Text("-"),
                count_usize(result.total, LOG),
                Text("scanned"),
            ],
        ),
        RunStatus::NoCrashLogsFound => DisplayLine::new(Notice, vec![label]),
        RunStatus::SetupFailed => DisplayLine::new(Failure, vec![label]),
        RunStatus::LocalIgnoreRecoveryRequired => DisplayLine::new(Warning, vec![label]),
        RunStatus::CancelledBeforeDiscovery => DisplayLine::new(Notice, vec![label]),
        RunStatus::Cancelled => DisplayLine::new(
            Notice,
            vec![
                label,
                Text("-"),
                count_usize(completed, LOG),
                Text("completed and"),
                count_usize(result.cancelled, LOG),
                Text("not started"),
            ],
        ),
    }
}

/// Renders the aggregate per-disposition tally.
fn render_outcome_summary(result: &RunResult) -> DisplayLine {
    DisplayLine::new(
        Info,
        vec![
            Text("Outcomes:"),
            count_usize(result.succeeded, LOG),
            Text("succeeded,"),
            count_usize(result.failed, LOG),
            Text("failed,"),
            count_usize(result.cancelled, LOG),
            Text("not started"),
        ],
    )
}

/// Appends discovery's summary, its refusals, and the locations it searched.
fn append_discovery(discovery: &CrashLogScanDiscoveryResult, lines: &mut Vec<DisplayLine>) {
    // Discovery source has no Display Label — it never adopted the shared vocabulary — so its
    // prose is written here rather than derived from a token. There is no naming table to
    // duplicate, because this crate is the only place the source is ever described.
    let source = match discovery.source {
        CrashLogScanDiscoverySource::Standard => Text("standard discovery"),
        CrashLogScanDiscoverySource::Targeted => Text("targeted discovery"),
    };

    lines.push(DisplayLine::new(
        Info,
        vec![
            Text("Discovery:"),
            source,
            Text("-"),
            count_usize(discovery.accepted_logs.len(), CRASH_LOG),
            Text("accepted,"),
            count_usize(discovery.rejected_inputs.len(), TARGETED_INPUT),
            Text("rejected,"),
            count_usize(discovery.searched_locations.len(), SEARCHED_LOCATION),
            Text("searched"),
        ],
    ));
    for rejection in &discovery.rejected_inputs {
        lines.push(DisplayLine::new(
            Notice,
            vec![
                Text("Rejected:"),
                PathSegment(rejection.path.clone()),
                Text("-"),
                Emphasis(rejection.reason.clone()),
            ],
        ));
    }
    for location in &discovery.searched_locations {
        lines.push(path_line(Info, "Searched:", location));
    }
}

/// Appends the complete run-level Installed YAML Data block.
///
/// These are operational diagnostics. Nothing here reaches Autoscan Report content, which
/// stays byte-identical for equivalent accepted data.
///
/// The four line renderers below are `pub(crate)` rather than private because
/// `InspectedYamlDataFile` and `InstalledYamlDataRunDiagnostic` are accessor-only with no
/// public constructor: no test can assemble an [`InstalledYamlDataRunData`] to feed through
/// [`render_run_result`], so pinning this block means calling its line renderers with the
/// same facts this function reads out of those types.
fn append_installed_yaml_data(data: &InstalledYamlDataRunData, lines: &mut Vec<DisplayLine>) {
    lines.push(render_installed_yaml_data_header());
    lines.push(render_yaml_data_file(
        data.main.role(),
        data.main.provenance(),
        data.main.schema_version(),
        data.main.identity(),
    ));
    lines.push(render_yaml_data_file(
        data.game_file.role(),
        data.game_file.provenance(),
        data.game_file.schema_version(),
        data.game_file.identity(),
    ));
    lines.push(render_local_ignore(
        data.local_ignore_state,
        &data.local_ignore_identity,
    ));
    if let Some(reset) = data.local_ignore_reset.as_ref() {
        lines.extend(render_local_ignore_reset(reset));
    }
    for diagnostic in &data.diagnostics {
        lines.push(render_installed_yaml_data_diagnostic(
            diagnostic.role(),
            diagnostic.candidate(),
            diagnostic.path(),
            diagnostic.kind(),
            diagnostic.message(),
        ));
    }
}

/// Renders the header that opens the Installed YAML Data block.
///
/// Split out rather than inlined so that this line — the block's only fixed prose that is not
/// a Display Label — reaches the tests through the same call the renderer makes, instead of
/// being unreachable behind a struct no test can build.
pub(crate) fn render_installed_yaml_data_header() -> DisplayLine {
    DisplayLine::new(Info, vec![Text("Installed YAML Data")])
}

/// Renders one selected update-eligible YAML Data file.
///
/// This takes the file's facts rather than the `InspectedYamlDataFile` that carries them.
/// That type is accessor-only with no public constructor, so a struct-taking renderer could
/// not be pinned by a test at all; taking the facts also narrows the renderer to exactly
/// what it reads.
///
/// `schema_version` is borrowed as a `Display` rather than named as `SchemaVersion`, so
/// rendering a version does not pull this crate's dependency graph out to the settings crate
/// that owns the type.
///
/// # Why the line opens on fixed prose
///
/// `Selected` leads so the role's Display Label never lands line-initially. That label is
/// asymmetric by design — `Main` names a glossary domain term while `game` is the ordinary
/// adjective in "selected-game YAML Data" — and its owning crate keeps the lowercase form
/// deliberately, because the same label reads correctly mid-sentence in
/// `no usable Installed YAML Data source for game`. Opening a line with it produced
/// `game YAML Data: bundled …` beside `Main YAML Data: bundled …`, which reads as a
/// capitalization bug rather than as the distinction it is. The fix belongs here, in the
/// sentence, rather than in a label that is correct everywhere it was designed to appear.
pub(crate) fn render_yaml_data_file(
    role: InstalledYamlDataRole,
    provenance: InstalledYamlDataProvenance,
    schema_version: impl fmt::Display,
    identity: &YamlDataContentIdentity,
) -> DisplayLine {
    DisplayLine::new(
        Info,
        vec![
            Text("Selected"),
            Label(role.label()),
            Text("YAML Data:"),
            Label(provenance.label()),
            Text("- schema"),
            Emphasis(schema_version.to_string()),
            Text("- sha256"),
            Emphasis(identity.sha256_hex()),
            Text("-"),
            count(identity.byte_len(), BYTE),
        ],
    )
}

/// Renders how Local Ignore YAML Data entered the run snapshot.
pub(crate) fn render_local_ignore(
    state: LocalIgnoreRunState,
    identity: &YamlDataContentIdentity,
) -> DisplayLine {
    let severity = match state {
        LocalIgnoreRunState::RecoveryRequired => Warning,
        LocalIgnoreRunState::Existing
        | LocalIgnoreRunState::Generated
        | LocalIgnoreRunState::ProceedWithoutIgnore
        | LocalIgnoreRunState::ResetToDefault => Info,
    };

    DisplayLine::new(
        severity,
        vec![
            Text("Local Ignore:"),
            Label(state.label()),
            Text("- sha256"),
            Emphasis(identity.sha256_hex()),
            Text("-"),
            count(identity.byte_len(), BYTE),
        ],
    )
}

/// Renders the durable backup and replacement a completed reset published.
pub(crate) fn render_local_ignore_reset(reset: &LocalIgnoreResetRunData) -> [DisplayLine; 2] {
    [
        DisplayLine::new(
            Info,
            vec![
                Text("Local Ignore backup:"),
                PathSegment(reset.backup_path.clone()),
                Text("- sha256"),
                Emphasis(reset.backup_identity.sha256_hex()),
            ],
        ),
        DisplayLine::new(
            Info,
            vec![
                Text("Local Ignore replacement:"),
                PathSegment(reset.local_ignore_path.clone()),
                Text("- sha256"),
                Emphasis(reset.replacement_identity.sha256_hex()),
            ],
        ),
    ]
}

/// Renders one structured selection, validation, generation, or reset diagnostic.
///
/// Like [`render_yaml_data_file`] this takes facts rather than the diagnostic struct, which
/// is accessor-only with no public constructor.
pub(crate) fn render_installed_yaml_data_diagnostic(
    role: Option<InstalledYamlDataRole>,
    candidate: Option<InstalledYamlDataProvenance>,
    path: Option<&Path>,
    kind: InstalledYamlDataRunDiagnosticKind,
    message: &str,
) -> DisplayLine {
    let severity = match kind {
        InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated
        | InstalledYamlDataRunDiagnosticKind::LocalIgnoreReset => Notice,
        InstalledYamlDataRunDiagnosticKind::CacheUnavailable
        | InstalledYamlDataRunDiagnosticKind::Missing
        | InstalledYamlDataRunDiagnosticKind::Read
        | InstalledYamlDataRunDiagnosticKind::InvalidUtf8
        | InstalledYamlDataRunDiagnosticKind::Parse
        | InstalledYamlDataRunDiagnosticKind::InvalidSchema
        | InstalledYamlDataRunDiagnosticKind::IncompatibleSchema
        | InstalledYamlDataRunDiagnosticKind::InvalidRoleData => Warning,
    };

    let mut segments = vec![
        Label(kind.label()),
        Text("-"),
        Emphasis(message.to_string()),
    ];
    if let Some(role) = role {
        segments.push(Text("- role"));
        segments.push(Label(role.label()));
    }
    if let Some(candidate) = candidate {
        segments.push(Text("- candidate"));
        segments.push(Label(candidate.label()));
    }
    if let Some(path) = path {
        segments.push(Text("- path"));
        segments.push(PathSegment(path.to_path_buf()));
    }
    DisplayLine::new(severity, segments)
}

/// Appends one Crash Log's terminal outcome and any structured failures beneath it.
fn append_log_outcome(log: &LogResult, lines: &mut Vec<DisplayLine>) {
    let mut segments = vec![
        // The ordinal is the log's discovery position, not a count of anything, so it is
        // emphasised rather than counted — a `Count` here would need a noun it does not have.
        Emphasis((log.discovery_index + 1).to_string()),
        Text("-"),
        PathSegment(log.crash_log.clone()),
        Text("-"),
        Label(log.disposition.label()),
    ];
    if let Some(report) = log.autoscan_report.as_ref() {
        segments.push(Text("- report"));
        segments.push(PathSegment(report.clone()));
    }
    if log.moved_to_unsolved_logs {
        segments.push(Text("- moved to Unsolved Logs"));
    }
    lines.push(DisplayLine::new(
        severity_for_disposition(log.disposition),
        segments,
    ));

    for failure in &log.failures {
        lines.push(DisplayLine::new(
            Failure,
            vec![
                Label(failure.stage.label()),
                Text("-"),
                Emphasis(failure.message.clone()),
            ],
        ));
    }
    // A message without structured failures is the only detail that log carries, so it is
    // stated rather than dropped. With failures present it duplicates them.
    if log.failures.is_empty()
        && let Some(message) = log.message.as_deref()
    {
        lines.push(DisplayLine::new(
            Notice,
            vec![Emphasis(message.to_string())],
        ));
    }
}

/// Renders the progress line shared by every log-scoped event.
///
/// `action` leads the line: fixed prose for the two lifecycle steps that have no enum behind
/// them, and a Display Label for the phase and disposition that do. Both read as lowercase
/// participles, so a frontend that upper-cases a line-initial word applies one rule to all
/// four rather than compensating for two shapes.
fn render_progress(
    log: &LogEvent,
    action: DisplaySegment,
    severity: DisplaySeverity,
) -> DisplayLine {
    DisplayLine::new(
        severity,
        vec![
            action,
            PathSegment(log.crash_log.clone()),
            Text("-"),
            Emphasis((log.discovery_index + 1).to_string()),
            Text("of"),
            count_usize(log.total, LOG),
        ],
    )
}

/// Renders a reset that refused to overwrite newer or removed canonical state.
fn render_reset_conflict(conflict: &LocalIgnoreResetConflictError) -> Vec<DisplayLine> {
    let mut lines = vec![
        DisplayLine::new(
            Failure,
            vec![Text(
                "Crash Log Scan recovery failed - Local Ignore reset conflicted with the current file on disk",
            )],
        ),
        DisplayLine::new(
            Info,
            vec![
                Text("Expected sha256"),
                Emphasis(conflict.expected_identity.sha256_hex()),
            ],
        ),
    ];
    match conflict.actual_identity.as_ref() {
        Some(actual) => lines.push(DisplayLine::new(
            Info,
            vec![Text("Actual sha256"), Emphasis(actual.sha256_hex())],
        )),
        // An absent current identity means another actor removed the file while the user was
        // deciding, which is still a refusal to overwrite rather than a failed write.
        None => lines.push(DisplayLine::new(
            Notice,
            vec![Text(
                "The malformed Local Ignore file was removed while you decided.",
            )],
        )),
    }
    if let Some(backup) = conflict.backup_path.as_ref() {
        lines.push(path_line(Info, "Verified backup:", backup));
    }
    lines.push(DisplayLine::new(
        Notice,
        vec![Text("Your Local Ignore file was not replaced.")],
    ));
    lines
}

/// Renders a reset that failed before or during publication, under a caller-chosen headline.
fn render_reset_failure(
    headline: &'static str,
    failure: &LocalIgnoreResetFailure,
) -> Vec<DisplayLine> {
    let mut lines = vec![
        DisplayLine::new(Failure, vec![Text(headline)]),
        DisplayLine::new(Failure, vec![Emphasis(failure.message.clone())]),
        path_line(Info, "Path:", &failure.path),
    ];
    if let Some(stage) = failure.stage {
        lines.push(DisplayLine::new(
            Info,
            vec![Text("Stage:"), Label(stage.label())],
        ));
    }
    lines
}

/// Renders a reset whose replacement is visible and backed up but not confirmed durable.
///
/// This reports a recovery receipt rather than telling the user nothing happened: the
/// replacement is already on disk and the backup is verified, so the actionable facts are
/// where the original bytes went and what identities to compare.
fn render_reset_durability_unknown(
    failure: &LocalIgnoreResetDurabilityUnknownError,
) -> Vec<DisplayLine> {
    vec![
        DisplayLine::new(
            Warning,
            vec![Text(
                "Local Ignore was reset, but the replacement is not confirmed durable",
            )],
        ),
        DisplayLine::new(Warning, vec![Emphasis(failure.message.clone())]),
        path_line(Info, "Path:", &failure.path),
        path_line(Info, "Verified backup:", &failure.backup_path),
        DisplayLine::new(
            Info,
            vec![
                Text("Malformed sha256"),
                Emphasis(failure.malformed_identity.sha256_hex()),
            ],
        ),
        DisplayLine::new(
            Info,
            vec![
                Text("Backup sha256"),
                Emphasis(failure.backup_identity.sha256_hex()),
            ],
        ),
        DisplayLine::new(
            Info,
            vec![
                Text("Replacement sha256"),
                Emphasis(failure.replacement_identity.sha256_hex()),
            ],
        ),
    ]
}

/// Builds a two-segment line that labels a path.
fn path_line(severity: DisplaySeverity, lead: &'static str, path: &Path) -> DisplayLine {
    DisplayLine::new(severity, vec![Text(lead), PathSegment(path.to_path_buf())])
}

/// Maps a terminal per-log disposition onto how gravely its line should read.
const fn severity_for_disposition(disposition: LogDisposition) -> DisplaySeverity {
    match disposition {
        LogDisposition::Succeeded => Success,
        LogDisposition::Failed => Failure,
        LogDisposition::CancelledBeforeStart => Notice,
    }
}
