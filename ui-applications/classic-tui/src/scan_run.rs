//! TUI projection and Display Layout for the final Crash Log Scan Run contract.
//!
//! *What* a Crash Log Scan Run says is decided by [`classic_scan_presentation`], which turns a run
//! result, a run event, an infrastructure failure, or a resume failure into an ordered sequence of
//! display lines. This module decides only *how* the TUI shows them: which lines to group where,
//! how far to truncate a path, where a percentage goes, and — through [`crate::theme`] — what
//! colour a severity takes. It composes no sentence about a run of its own.
//!
//! The rules it must follow are the crate's, not this frontend's:
//!
//! 1. A line's segments are concatenated in core's order and never reordered within the line.
//! 2. Whole lines may be reordered, grouped, or omitted — and [`format_result`] does group.
//! 3. A Display Label already carried in a segment is never re-derived. No non-test code in this
//!    crate calls `Vocabulary::label()` at all now, because every label the TUI shows arrives
//!    inside a [`DisplaySegment::Label`] — which is why `classic-vocabulary` became a dev
//!    dependency. The tests still call it, to prove the label rather than the token is what
//!    reaches the user.
//! 4. A [`DisplaySegment::Count`] prints its value and then core's noun, which already agrees with
//!    that value. This frontend's `plural` helper survives only for the Local Ignore recovery
//!    prompt, whose renderer lands with the gated recovery phase.
//!
//! `tests/shared_runtime_audit.rs` fails the build if a naming table reappears here.

#[cfg(test)]
#[path = "scan_run_tests.rs"]
mod tests;

use classic_scan_presentation::{
    DisplayLine, DisplaySegment, DisplaySeverity, render_event, render_infrastructure_error,
    render_resume_error, render_run_result,
};
use classic_scanlog_core::scan_run::contract::{
    Configuration, Event, InfrastructureError, LogEvent, Request, ResumeError, RunResult,
};
use classic_scanlog_core::{
    CrashLogScanSetupContext, ScanProgressPhase, StandardCrashLogScanSource,
    StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};

// Coarse weights make in-flight lifecycle events visibly advance the gauge without pretending
// that the phases are equal-cost; App keeps the resulting aggregate monotonic across concurrent logs.
const STARTED_CONTRIBUTION: f64 = 0.08;
const SETUP_CONTRIBUTION: f64 = 0.15;
const PARSE_CONTRIBUTION: f64 = 0.40;
const ANALYZE_CONTRIBUTION: f64 = 0.82;
const FINALIZE_CONTRIBUTION: f64 = 0.95;

/// One core display line, flattened into the text this frontend will draw.
///
/// The severity travels alongside the text rather than being resolved to a colour here, so the
/// palette stays in [`crate::theme`] and a test can assert what a line *is* without asserting how
/// it looks.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PresentedLine {
    /// How gravely core says this line reads.
    pub severity: DisplaySeverity,
    /// The line's segments, concatenated in core's order.
    pub text: String,
}

impl PresentedLine {
    /// Builds a line the TUI owns outright, at the neutral severity.
    ///
    /// Three kinds of line reach this, and none of them is leftover Display Content. The FCX Mode
    /// setup projection is out of scope for the presentation crate — its check state, check kind,
    /// issue severity, and update kind have not adopted the shared vocabulary, so rendering it
    /// there would mean inventing prose for machine identifiers. The Local Ignore recovery prompt's
    /// choices are out of scope too, until the prompt renderer lands with the gated recovery phase.
    /// Blank spacers are pure Display Layout and say nothing at all.
    fn local(text: String) -> Self {
        Self {
            severity: DisplaySeverity::Info,
            text,
        }
    }
}

/// How much of a path a flattened line keeps.
#[derive(Clone, Copy)]
enum PathDetail {
    /// The whole path. Used in the scrollable overlay, which wraps and can afford it — and which is
    /// where a user looks for the Autoscan Report a run actually wrote.
    Full,
    /// The final component alone. Used in the single-row status line, where one absolute path
    /// pushes the ordinal, the total, and the outcome off the end of the row.
    FileName,
}

/// Concatenates one display line's segments, in core's order, into drawable text.
///
/// Truncation is Display Layout, which is the only reason `detail` exists: core deliberately hands
/// over the whole path so a frontend that wants to link to a report has one, and shortening it for
/// a narrow row is this frontend's decision to make. Nothing else about the line is this frontend's
/// to decide — segments keep their order, a label keeps its words, and a count keeps the noun core
/// already agreed with its value.
fn flatten_line(line: &DisplayLine, detail: PathDetail) -> String {
    line.segments
        .iter()
        .map(|segment| segment_text(segment, detail))
        .collect::<Vec<_>>()
        .join(" ")
}

/// Renders one segment's payload.
fn segment_text(segment: &DisplaySegment, detail: PathDetail) -> String {
    match segment {
        DisplaySegment::Text(text) | DisplaySegment::Label(text) => (*text).to_string(),
        // Value then noun, never a re-derived form: `noun` already agrees with `value`, and the
        // pluralization helper this frontend used to keep is what that agreement replaced.
        DisplaySegment::Count { value, noun } => format!("{value} {noun}"),
        DisplaySegment::Path(path) => match detail {
            PathDetail::Full => path.display().to_string(),
            PathDetail::FileName => path
                .file_name()
                .map(|name| name.to_string_lossy().into_owned())
                // A path with no final component is a root or an empty path. Neither reaches a
                // scan-run line in practice, and naming the state beats drawing nothing.
                .unwrap_or_else(|| "unknown".to_string()),
        },
        DisplaySegment::Name(name) | DisplaySegment::Emphasis(name) => name.clone(),
    }
}

/// Flattens rendered lines for the scrollable overlay, keeping every line and every path whole.
fn present_lines(lines: &[DisplayLine]) -> Vec<PresentedLine> {
    lines
        .iter()
        .map(|line| PresentedLine {
            severity: line.severity,
            text: flatten_line(line, PathDetail::Full),
        })
        .collect()
}

/// Collapses every rendered line onto the single sentence-cased row the status line shows.
///
/// Grouping lines onto one row is Display Layout, and it is the right call for a run *event*: an
/// event renders to at most two short lines — a discovery that rejected some of its targeted
/// inputs states the rejection separately — and both are live progress facts with nowhere else to
/// appear. Their order stays core's.
fn present_status(lines: &[DisplayLine]) -> String {
    let joined = lines
        .iter()
        .map(|line| flatten_line(line, PathDetail::FileName))
        .collect::<Vec<_>>()
        .join(" - ");
    sentence_case(&joined)
}

/// Takes the sentence-cased first rendered line as the status row.
///
/// Used where the remaining lines have somewhere better to be. A run result and a failure both
/// open on the line that states the outcome and can run to a dozen supporting lines behind it —
/// identity digests, searched locations, a per-log tally — which belong in the scrollable overlay
/// rather than crushed into one row. Omitting whole lines from one surface is Display Layout; every
/// one of them is still shown by [`present_lines`].
fn present_headline(lines: &[DisplayLine]) -> String {
    lines
        .first()
        .map(|line| sentence_case(&flatten_line(line, PathDetail::FileName)))
        .unwrap_or_default()
}

/// Returns how gravely the status row should read for a rendered surface.
///
/// The first line's severity, because the first line is the one stating the outcome — the same line
/// [`present_headline`] takes its words from, and the one [`present_status`] leads with. Taking the
/// gravest severity across all lines instead would let a run that completed successfully read as a
/// failure because one of its many detail lines mentioned one.
fn present_severity(lines: &[DisplayLine]) -> DisplaySeverity {
    lines
        .first()
        .map_or(DisplaySeverity::Info, |line| line.severity)
}

/// Typed scan intent projected by the TUI before execution.
pub(crate) enum ScanRunIntent {
    /// Normal discovery with the Standard-only Unsolved Logs policy.
    Standard {
        source: StandardCrashLogScanSource,
        unsolved_logs: StandardUnsolvedLogsIntent,
    },
    /// Explicit user-selected inputs without relocation capability.
    Targeted(TargetedCrashLogScanSource),
}

/// Constructs one invariant-preserving final-contract request.
pub(crate) fn build_request(
    configuration: Configuration,
    intent: ScanRunIntent,
    setup_context: Option<CrashLogScanSetupContext>,
) -> Request {
    match (intent, setup_context) {
        (
            ScanRunIntent::Standard {
                source,
                unsolved_logs,
            },
            Some(setup_context),
        ) => Request::standard_with_fcx(configuration, source, unsolved_logs, setup_context),
        (
            ScanRunIntent::Standard {
                source,
                unsolved_logs,
            },
            None,
        ) => Request::standard(configuration, source, unsolved_logs),
        (ScanRunIntent::Targeted(source), Some(setup_context)) => {
            Request::targeted_with_fcx(configuration, source, setup_context)
        }
        (ScanRunIntent::Targeted(source), None) => Request::targeted(configuration, source),
    }
}

/// Expected-outcome line for the operation-scoped Proceed Without Ignore decision.
pub(crate) const PROCEED_WITHOUT_IGNORE_CHOICE: &str = "[P] Proceed Without Ignore - scan now with an empty ignore list. Your malformed file is left exactly as it is, and this choice applies only to this scan.";
/// Expected-outcome line for the durable Reset To Default decision.
pub(crate) const RESET_TO_DEFAULT_CHOICE: &str = "[R] Reset To Default - back up your malformed file byte-exactly, replace it with the selected Main defaults, then scan.";
/// Expected-outcome line for dismissing the decision without mutation or analysis.
///
/// Both dismissal keys are advertised because both are live; an unadvertised binding is exactly
/// the kind of surprise this overlay must not have.
pub(crate) const CANCEL_RECOVERY_CHOICE: &str = "[Esc] or [C] Cancel - stop this scan. Nothing is analyzed, nothing is backed up, and Local Ignore is not modified.";

/// Cloneable presentation facts for one Crash Log Scan Run paused on Local Ignore recovery.
///
/// This type deliberately carries no continuation. The opaque single-use continuation stays in
/// non-cloneable application state, so presentation can never duplicate, persist, or replay it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct LocalIgnoreRecoveryPrompt {
    /// The Rust-owned run message explaining why the run paused, when the run supplied one.
    ///
    /// `None` when it did not, and the headline is then omitted rather than replaced with a
    /// sentence this frontend wrote. [`Self::run_detail`] always opens on the status Display Label,
    /// so nothing is left unexplained — and a locally invented fallback would have contradicted
    /// core's own wording two lines further down the same overlay.
    pub(crate) message: Option<String>,
    /// Crash Logs already discovered, which the retained continuation will scan once decided.
    pub(crate) retained_logs: usize,
    /// The paused run as core describes it, including the Installed YAML Data block.
    ///
    /// This is the whole rendered run result rather than the Installed YAML Data lines alone.
    /// Core exposes that block only through `render_run_result`, and picking it back out by
    /// position would be a structural assumption about a flat sequence that carries no structure —
    /// exactly the guess this consolidation exists to remove. Showing the surrounding facts is no
    /// loss: every one of them describes the run the user is being asked to decide about.
    pub(crate) run_detail: Vec<PresentedLine>,
    /// Whether Reset To Default is a choice this run can actually satisfy.
    ///
    /// False when the selected Main YAML retained no usable `default_ignorefile`. The contract
    /// projects this so the overlay can omit an option that would consume the one-shot
    /// continuation and fail, leaving the user with no scan and no second attempt.
    pub(crate) reset_available: bool,
}

impl LocalIgnoreRecoveryPrompt {
    /// Returns the status line describing how much retained work an accepted decision resumes.
    pub(crate) fn resume_status(&self) -> String {
        format!(
            "Resuming {} discovered crash {}...",
            self.retained_logs,
            plural(self.retained_logs, "log", "logs")
        )
    }

    /// Returns the one-row status line a paused run shows while the question is open.
    ///
    /// The run's own message when it supplied one, and core's rendered status line otherwise. Both
    /// are core-owned prose; the only thing decided here is which of the two to show, which is a
    /// question about one narrow row rather than about what the run says.
    pub(crate) fn status_line(&self) -> String {
        self.message
            .clone()
            .or_else(|| self.run_detail.first().map(|line| line.text.clone()))
            .unwrap_or_default()
    }

    /// Renders the complete overlay body, including the expected outcome of every offered decision.
    ///
    /// The three choices are placed above the run detail on purpose. Every line here wraps, and
    /// identity digests plus a parser message run long enough to push the last choice past the
    /// bottom of the overlay. Supporting detail may sit below the fold; an option the user cannot
    /// see is not an option they were offered.
    ///
    /// The body opens on the retained-discovery line rather than on a headline restating why the
    /// run paused. Three things were saying that at once: the overlay's own title, and then core's
    /// status line and its `Message:` line, adjacent to each other in [`Self::run_detail`]. Two of
    /// those are core's and one is the window chrome, so the one worth dropping was the copy this
    /// frontend was making.
    ///
    /// The choices themselves are still written here. The Local Ignore recovery prompt renderer
    /// lands with the gated recovery phase, so until it exists there is nothing in core to render
    /// them from — which is also why `plural` still has one caller.
    pub(crate) fn overlay_lines(&self) -> Vec<PresentedLine> {
        let mut lines = Vec::from([
            PresentedLine::local(format!(
                "Retained discovery: {} crash {} will be scanned once you decide.",
                self.retained_logs,
                plural(self.retained_logs, "log", "logs")
            )),
            PresentedLine::local(String::new()),
            PresentedLine::local(PROCEED_WITHOUT_IGNORE_CHOICE.to_string()),
        ]);
        // Omitted rather than shown-and-disabled: this overlay is plain text with no affordance for
        // an inert entry, and listing a key that does nothing reads as a bug.
        if self.reset_available {
            lines.push(PresentedLine::local(RESET_TO_DEFAULT_CHOICE.to_string()));
        }
        lines.push(PresentedLine::local(CANCEL_RECOVERY_CHOICE.to_string()));
        if !self.reset_available {
            lines.push(PresentedLine::local(String::new()));
            lines.push(PresentedLine {
                severity: DisplaySeverity::Notice,
                text: "Reset To Default is unavailable: the selected Main YAML Data retains no \
                       usable default Local Ignore to publish."
                    .to_string(),
            });
        }
        if !self.run_detail.is_empty() {
            lines.push(PresentedLine::local(String::new()));
            lines.extend(self.run_detail.iter().cloned());
        }
        lines
    }
}

/// Joins presented lines into one plain-text block, dropping the severities.
pub(crate) fn join_presented(lines: &[PresentedLine]) -> String {
    lines
        .iter()
        .map(|line| line.text.as_str())
        .collect::<Vec<_>>()
        .join("\n")
}

/// Projects the Rust-owned paused-run facts the TUI shows before asking for an explicit decision.
///
/// Every fact comes from the retained result; the TUI adds no policy and never inspects the
/// malformed file itself.
pub(crate) fn describe_local_ignore_recovery(result: &RunResult) -> LocalIgnoreRecoveryPrompt {
    LocalIgnoreRecoveryPrompt {
        run_detail: present_lines(&render_run_result(result)),
        message: result.message.clone(),
        retained_logs: result
            .discovery
            .as_ref()
            .map_or(result.total, |discovery| discovery.accepted_logs.len()),
        // Absent Installed YAML Data means the contract told us nothing about reset availability,
        // which a recovery-required result never does in practice. Keep offering the choice in that
        // case rather than hiding it: an unknown answer must not silently remove an option that may
        // well work, and offering is exactly the behaviour that shipped before this fact existed.
        reset_available: result
            .installed_yaml_data
            .as_ref()
            .is_none_or(|installed| installed.local_ignore_reset_available),
    }
}

/// One status-line update derived from a final-contract event.
pub(crate) struct EventPresentation {
    /// Aggregate completed-work percentage.
    pub(crate) percent: f64,
    /// Concise lifecycle description for the TUI status line.
    pub(crate) status: String,
    /// How gravely the status line reads, taken from core's first rendered line.
    pub(crate) severity: DisplaySeverity,
}

/// Formats every stable final-contract event for the TUI progress display.
///
/// The words are core's. What is decided here is the gauge: which lifecycle step advances the bar
/// and by how much, and whether the resulting percentage leads the status line at all. A discovery
/// or a concurrency selection reports no progress, so neither carries a percentage.
pub(crate) fn format_event(event: &Event) -> EventPresentation {
    let lines = render_event(event);
    let status = present_status(&lines);
    let severity = present_severity(&lines);

    match event {
        Event::DiscoveryCompleted(_) | Event::EffectiveConcurrencySelected { .. } => {
            EventPresentation {
                percent: 0.0,
                status,
                severity,
            }
        }
        Event::LogQueued(log) => log_progress(log, 0.0, status, severity),
        Event::LogStarted(log) => log_progress(log, STARTED_CONTRIBUTION, status, severity),
        // Only the gauge weighting is decided here. The words come from the core crate that owns
        // the phase, so this frontend cannot drift from the CLI and the GUI about what a phase is
        // called — the phase reaches the line as a Display Label inside a segment.
        Event::LogPhase { log, phase } => {
            log_progress(log, phase_contribution(*phase), status, severity)
        }
        Event::LogFinished { log, .. } => log_progress(log, 0.0, status, severity),
    }
}

/// Returns the share of one Crash Log's work that reaching `phase` represents.
///
/// Coarse and deliberately unequal: the phases are not equal-cost, and a gauge that pretended
/// otherwise would stall visibly through analysis.
const fn phase_contribution(phase: ScanProgressPhase) -> f64 {
    match phase {
        ScanProgressPhase::Setup => SETUP_CONTRIBUTION,
        ScanProgressPhase::Parse => PARSE_CONTRIBUTION,
        ScanProgressPhase::Analyze => ANALYZE_CONTRIBUTION,
        ScanProgressPhase::Finalize => FINALIZE_CONTRIBUTION,
    }
}

/// Prefixes a log-scoped status line with the aggregate progress its event implies.
fn log_progress(
    log: &LogEvent,
    in_flight_contribution: f64,
    status: String,
    severity: DisplaySeverity,
) -> EventPresentation {
    let percent = if log.total == 0 {
        0.0
    } else {
        ((log.completed as f64 + in_flight_contribution) / log.total as f64) * 100.0
    };

    EventPresentation {
        percent,
        status: format!("{percent:.0}% - {status}"),
        severity,
    }
}

/// Chooses a noun's singular or plural form.
///
/// One caller remains: the Local Ignore recovery overlay, whose prompt renderer lands with the
/// gated recovery phase. Every other count the TUI prints now arrives as a
/// [`DisplaySegment::Count`] whose noun core already agreed with its value, which is what retires
/// the copy of this helper each frontend used to keep.
const fn plural<'a>(count: usize, singular: &'a str, plural: &'a str) -> &'a str {
    if count == 1 { singular } else { plural }
}

/// Returns `label` with its first character upper-cased.
///
/// A disposition appears twice in this frontend: sentence-initial in the status line, and
/// mid-sentence in the terminal detail list. Only the second form matches the core Display Label,
/// and the status line has always shown the capitalized one. Deriving that form here keeps the
/// vocabulary single-sourced — this owns a capitalization rule, not a second copy of the words —
/// where a second table would be free to disagree with the first about what happened.
///
/// A scan progress phase reaches the status line the same way and for the same reason, which is
/// why the core labels it in the lower-case participle rather than pre-capitalizing it: the
/// capitalization is this frontend's sentence position, not part of the phase's name.
///
/// A label already opening on a capitalized domain term passes through unchanged.
fn sentence_case(label: &str) -> String {
    let mut characters = label.chars();
    match characters.next() {
        Some(first) => first.to_uppercase().collect::<String>() + characters.as_str(),
        None => String::new(),
    }
}

/// Durable terminal text and gauge state derived without discarding the typed result.
pub(crate) struct TerminalPresentation {
    /// Final aggregate progress percentage.
    pub(crate) percent: f64,
    /// Concise status-line summary.
    pub(crate) status: String,
    /// How gravely the status line reads, taken from core's first rendered line.
    pub(crate) severity: DisplaySeverity,
    /// The run as core describes it, flattened for the scrollable overlay.
    pub(crate) details: Vec<PresentedLine>,
}

/// Presents a terminal Crash Log Scan Run Result from core's display lines.
///
/// The status line is the first rendered line, which is the one stating how the run as a whole
/// ended. Reading it by position is safe here in a way that picking a section out of the middle
/// would not be: core documents the terminal status as the line the run result opens with, and
/// every branch of that renderer emits it first.
///
/// The FCX Mode setup projection is grouped in **after** the rendered lines rather than at the
/// position it used to hold. Regrouping whole lines is Display Layout and explicitly allowed;
/// splicing into the middle of core's sequence is not something a flat list of lines supports, and
/// guessing an index would be the structural assumption this consolidation removes.
pub(crate) fn format_result(result: &RunResult) -> TerminalPresentation {
    let lines = render_run_result(result);
    let completed = result.succeeded + result.failed;
    let percent = if result.total == 0 {
        0.0
    } else {
        (completed as f64 / result.total as f64) * 100.0
    };
    let status = present_headline(&lines);
    let severity = present_severity(&lines);

    let mut details = present_lines(&lines);
    if let Some(setup) = result.setup.as_ref() {
        let mut setup_lines = Vec::new();
        append_setup_details(setup, &mut setup_lines);
        details.extend(setup_lines.into_iter().map(PresentedLine::local));
    }

    TerminalPresentation {
        percent,
        status,
        severity,
        details,
    }
}

/// Presents a run-wide infrastructure error consistently in the status line and overlay.
///
/// The stage reaches the user as a Display Label because core puts one in the line, not because
/// this frontend asks for one. That is the whole difference: the token spellings this used to
/// print — `formid_database_access` and the rest — were an identifier leaking into a sentence, and
/// there is no longer a sentence here to leak into.
pub(crate) fn format_error(error: &InfrastructureError) -> TerminalPresentation {
    present_error(&render_infrastructure_error(error))
}

/// Presents a typed continuation-resume failure without collapsing its actionable context.
///
/// The stable resume error code is deliberately absent from the prose. It is a machine-facing
/// identifier and belongs in structured output; core distinguishes replay, reset conflict, backup
/// failure, replacement failure, and durability uncertainty by what a user acts on instead.
pub(crate) fn format_resume_error(error: &ResumeError) -> TerminalPresentation {
    present_error(&render_resume_error(error))
}

/// Shares the failure-presentation shape between the two error renderers.
///
/// The gauge is zeroed rather than left mid-run: a failure has no completed-work fraction to
/// report, and a bar frozen at the last percentage it happened to reach would read as progress the
/// run is still making.
fn present_error(lines: &[DisplayLine]) -> TerminalPresentation {
    TerminalPresentation {
        percent: 0.0,
        status: present_headline(lines),
        severity: present_severity(lines),
        details: present_lines(lines),
    }
}

/// Appends the full structured FCX setup projection to terminal detail lines.
fn append_setup_details(
    setup: &classic_scanlog_core::CrashLogScanSetupResult,
    lines: &mut Vec<String>,
) {
    lines.push(format!("Setup: {}", setup.status));
    if let Some(message) = setup.message.as_deref() {
        lines.push(format!("Setup message: {message}"));
    }
    for check in &setup.checks {
        lines.push(format!(
            "Setup check [{}] {}: {}",
            check.state, check.kind, check.message
        ));
        for detail in &check.details {
            lines.push(format!("   {detail}"));
        }
    }
    for update in &setup.path_updates {
        lines.push(format!(
            "Proposed {} path: {}",
            update.kind,
            update.path.display()
        ));
    }
    for issue in &setup.configuration_issues {
        let section = issue
            .section
            .as_deref()
            .map(|section| format!("/[{section}]"))
            .unwrap_or_default();
        lines.push(format!(
            "Setup issue [{}] {}{} {}: {} (current: {}, recommended: {})",
            issue.severity,
            issue.file_path,
            section,
            issue.setting,
            issue.description,
            issue.current_value,
            issue.recommended_value
        ));
    }
    for action in &setup.actions {
        lines.push(format!("Setup action: {action}"));
    }
    for error in &setup.fatal_errors {
        lines.push(format!("Setup error: {error}"));
    }
    if !setup.rendered_report.trim().is_empty() {
        lines.push(setup.rendered_report.clone());
    }
}
