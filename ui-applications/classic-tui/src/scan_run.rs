//! TUI projection and presentation for the final Crash Log Scan Run contract.

#[cfg(test)]
#[path = "scan_run_tests.rs"]
mod tests;

use classic_config_core::InstalledYamlDataProvenance;
use classic_scanlog_core::scan_run::contract::{
    Configuration, Event, InfrastructureError, InstalledYamlDataRunData,
    InstalledYamlDataRunDiagnostic, InstalledYamlDataRunDiagnosticKind,
    LocalIgnoreResetFailureStage, LocalIgnoreRunState, LogDisposition, LogEvent, LogFailureStage,
    Request, ResumeError, RunResult,
};
use classic_scanlog_core::{
    CrashLogScanRunStatus, CrashLogScanSetupContext, ScanProgressPhase, StandardCrashLogScanSource,
    StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};

// Coarse weights make in-flight lifecycle events visibly advance the gauge without pretending
// that the phases are equal-cost; App keeps the resulting aggregate monotonic across concurrent logs.
const STARTED_CONTRIBUTION: f64 = 0.08;
const SETUP_CONTRIBUTION: f64 = 0.15;
const PARSE_CONTRIBUTION: f64 = 0.40;
const ANALYZE_CONTRIBUTION: f64 = 0.82;
const FINALIZE_CONTRIBUTION: f64 = 0.95;

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
    /// Rust-owned run message explaining why the run paused.
    pub(crate) message: String,
    /// Crash Logs already discovered, which the retained continuation will scan once decided.
    pub(crate) retained_logs: usize,
    /// Structured Installed YAML Data lines presented alongside the choice.
    pub(crate) diagnostics: Vec<String>,
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

    /// Renders the complete overlay body, including the expected outcome of every offered decision.
    ///
    /// The three choices are placed above the Installed YAML Data diagnostics on purpose. Every
    /// line here wraps, and identity digests plus a parser message run long enough to push the
    /// last choice past the bottom of the overlay. Supporting detail may sit below the fold; an
    /// option the user cannot see is not an option they were offered.
    pub(crate) fn overlay_text(&self) -> String {
        let mut lines = vec![self.message.clone(), String::new()];
        lines.push(format!(
            "Retained discovery: {} crash {} will be scanned once you decide.",
            self.retained_logs,
            plural(self.retained_logs, "log", "logs")
        ));
        lines.push(String::new());
        lines.push(PROCEED_WITHOUT_IGNORE_CHOICE.to_string());
        lines.push(RESET_TO_DEFAULT_CHOICE.to_string());
        lines.push(CANCEL_RECOVERY_CHOICE.to_string());
        if !self.diagnostics.is_empty() {
            lines.push(String::new());
            lines.extend(self.diagnostics.iter().cloned());
        }
        lines.join("\n")
    }
}

/// Projects the Rust-owned paused-run facts the TUI shows before asking for an explicit decision.
///
/// Every fact comes from the retained result; the TUI adds no policy and never inspects the
/// malformed file itself.
pub(crate) fn describe_local_ignore_recovery(result: &RunResult) -> LocalIgnoreRecoveryPrompt {
    let mut diagnostics = Vec::new();
    if let Some(installed) = result.installed_yaml_data.as_ref() {
        append_installed_yaml_data_details(installed, &mut diagnostics);
    }

    LocalIgnoreRecoveryPrompt {
        message: result.message.clone().unwrap_or_else(|| {
            "Local Ignore recovery is required before scanning can continue".to_string()
        }),
        retained_logs: result
            .discovery
            .as_ref()
            .map_or(result.total, |discovery| discovery.accepted_logs.len()),
        diagnostics,
    }
}

/// One status-line update derived from a final-contract event.
pub(crate) struct EventPresentation {
    /// Aggregate completed-work percentage.
    pub(crate) percent: f64,
    /// Concise lifecycle description for the TUI status line.
    pub(crate) status: String,
}

/// Formats every stable final-contract event for the TUI progress display.
pub(crate) fn format_event(event: &Event) -> EventPresentation {
    match event {
        Event::DiscoveryCompleted(discovery) => {
            let accepted = discovery.accepted_logs.len();
            let rejected = discovery.rejected_inputs.len();
            let mut status = format!(
                "Discovered {accepted} crash {}",
                plural(accepted, "log", "logs")
            );
            if rejected > 0 {
                status.push_str(&format!(
                    " ({rejected} targeted {} rejected)",
                    plural(rejected, "input", "inputs")
                ));
            }
            EventPresentation {
                percent: 0.0,
                status,
            }
        }
        Event::EffectiveConcurrencySelected {
            effective_concurrency,
        } => EventPresentation {
            percent: 0.0,
            status: format!(
                "Selected {effective_concurrency} concurrent {}",
                plural(*effective_concurrency, "scan", "scans")
            ),
        },
        Event::LogQueued(log) => format_log_event(log, "Queued", 0.0),
        Event::LogStarted(log) => format_log_event(log, "Scanning", STARTED_CONTRIBUTION),
        Event::LogPhase { log, phase } => {
            let (action, contribution) = match phase {
                ScanProgressPhase::Setup => ("Preparing", SETUP_CONTRIBUTION),
                ScanProgressPhase::Parse => ("Parsing", PARSE_CONTRIBUTION),
                ScanProgressPhase::Analyze => ("Analyzing", ANALYZE_CONTRIBUTION),
                ScanProgressPhase::Finalize => ("Finalizing", FINALIZE_CONTRIBUTION),
            };
            format_log_event(log, action, contribution)
        }
        Event::LogFinished { log, disposition } => {
            format_log_event(log, disposition_presentation(*disposition).event, 0.0)
        }
    }
}

/// Formats the shared path, ordinal, and aggregate progress carried by log events.
fn format_log_event(
    log: &LogEvent,
    action: &str,
    in_flight_contribution: f64,
) -> EventPresentation {
    let percent = if log.total == 0 {
        0.0
    } else {
        ((log.completed as f64 + in_flight_contribution) / log.total as f64) * 100.0
    };
    let filename = log
        .crash_log
        .file_name()
        .map(|name| name.to_string_lossy())
        .unwrap_or_else(|| "unknown".into());

    EventPresentation {
        percent,
        status: format!(
            "{percent:.0}% - {action} {filename} ({} of {})",
            log.discovery_index + 1,
            log.total
        ),
    }
}

const fn plural<'a>(count: usize, singular: &'a str, plural: &'a str) -> &'a str {
    if count == 1 { singular } else { plural }
}

/// Durable terminal text and gauge state derived without discarding the typed result.
pub(crate) struct TerminalPresentation {
    /// Final aggregate progress percentage.
    pub(crate) percent: f64,
    /// Concise status-line summary.
    pub(crate) status: String,
    /// Multi-line discovery, setup, concurrency, and outcome presentation.
    pub(crate) details: String,
}

/// Presents every expected terminal status and all retained final-contract outcomes.
pub(crate) fn format_result(result: &RunResult) -> TerminalPresentation {
    let completed = result.succeeded + result.failed;
    let percent = if result.total == 0 {
        0.0
    } else {
        (completed as f64 / result.total as f64) * 100.0
    };
    let status = match result.status {
        CrashLogScanRunStatus::Completed if result.failed > 0 || result.cancelled > 0 => format!(
            "Scanned {} logs ({} errors, {} cancelled)",
            result.total, result.failed, result.cancelled
        ),
        CrashLogScanRunStatus::Completed => format!(
            "Scanned {} {}",
            result.total,
            plural(result.total, "log", "logs")
        ),
        CrashLogScanRunStatus::NoCrashLogsFound => result
            .message
            .clone()
            .unwrap_or_else(|| "No crash logs found".to_string()),
        CrashLogScanRunStatus::SetupFailed => result
            .message
            .clone()
            .unwrap_or_else(|| "Crash Log Scan setup failed".to_string()),
        CrashLogScanRunStatus::LocalIgnoreRecoveryRequired => {
            result.message.clone().unwrap_or_else(|| {
                "Local Ignore recovery is required before scanning can continue".to_string()
            })
        }
        CrashLogScanRunStatus::CancelledBeforeDiscovery => {
            "Scan cancelled safely before discovery completed".to_string()
        }
        CrashLogScanRunStatus::Cancelled => format!(
            "Cancelled ({completed} of {} logs completed; {} not started)",
            result.total, result.cancelled
        ),
    };

    let mut lines = vec![format!("Run status: {}", result.status.as_str())];
    if let Some(message) = result.message.as_deref() {
        lines.push(format!("Message: {message}"));
    }
    if let Some(discovery) = result.discovery.as_ref() {
        lines.push(format!(
            "Discovery: {}; {} accepted; {} rejected; {} searched",
            discovery.source.as_str(),
            discovery.accepted_logs.len(),
            discovery.rejected_inputs.len(),
            discovery.searched_locations.len()
        ));
        for rejection in &discovery.rejected_inputs {
            lines.push(format!(
                "Rejected: {} ({})",
                rejection.path.display(),
                rejection.reason
            ));
        }
        for location in &discovery.searched_locations {
            lines.push(format!("Searched: {}", location.display()));
        }
    }
    if let Some(effective_concurrency) = result.effective_concurrency {
        lines.push(format!("Effective concurrency: {effective_concurrency}"));
    }
    if let Some(setup) = result.setup.as_ref() {
        append_setup_details(setup, &mut lines);
    }
    if let Some(installed) = result.installed_yaml_data.as_ref() {
        append_installed_yaml_data_details(installed, &mut lines);
    }

    lines.push(format!(
        "Outcomes: {} succeeded; {} failed; {} cancelled before start",
        result.succeeded, result.failed, result.cancelled
    ));
    for log in &result.logs {
        let filename = log
            .crash_log
            .file_name()
            .map(|name| name.to_string_lossy())
            .unwrap_or_else(|| "unknown".into());
        let disposition = disposition_presentation(log.disposition).terminal;
        let mut line = format!("{}. {filename} - {disposition}", log.discovery_index + 1);
        if let Some(report) = log.autoscan_report.as_ref() {
            line.push_str(&format!("; report: {}", report.display()));
        }
        if log.moved_to_unsolved_logs {
            line.push_str("; moved to Unsolved Logs");
        }
        lines.push(line);
        for failure in &log.failures {
            let stage = match failure.stage {
                LogFailureStage::Analysis => "analysis",
                LogFailureStage::ReportWrite => "report write",
                LogFailureStage::UnsolvedLogsFinalization => "Unsolved Logs finalization",
            };
            lines.push(format!("   {stage}: {}", failure.message));
        }
        if log.failures.is_empty()
            && let Some(message) = log.message.as_deref()
        {
            lines.push(format!("   {message}"));
        }
    }

    TerminalPresentation {
        percent,
        status,
        details: lines.join("\n"),
    }
}

/// Presents a run-wide infrastructure error consistently in the status line and overlay.
pub(crate) fn format_error(error: &InfrastructureError) -> TerminalPresentation {
    let status_path = error
        .path
        .as_ref()
        .map(|path| format!(" (path: {})", path.display()))
        .unwrap_or_default();
    let detail_path = error
        .path
        .as_ref()
        .map(|path| format!("\nPath: {}", path.display()))
        .unwrap_or_default();

    TerminalPresentation {
        percent: 0.0,
        status: format!(
            "Crash Log Scan Run failed during {}: {}{}",
            error.stage, error.message, status_path
        ),
        details: format!(
            "Crash Log Scan Run failed during {}\n{}{}",
            error.stage, error.message, detail_path
        ),
    }
}

/// Appends the complete run-level Installed YAML Data projection to terminal detail lines.
///
/// These are operational diagnostics only. Nothing here contributes to Autoscan Report content,
/// which stays byte-identical for equivalent accepted data.
fn append_installed_yaml_data_details(data: &InstalledYamlDataRunData, lines: &mut Vec<String>) {
    lines.push("Installed YAML Data:".to_string());
    lines.push(format!(
        "  Main: {} schema {} (sha256 {}, {} bytes)",
        provenance_label(data.main.provenance()),
        data.main.schema_version(),
        data.main.identity().sha256_hex(),
        data.main.identity().byte_len()
    ));
    lines.push(format!(
        "  Game: {} schema {} (sha256 {}, {} bytes)",
        provenance_label(data.game_file.provenance()),
        data.game_file.schema_version(),
        data.game_file.identity().sha256_hex(),
        data.game_file.identity().byte_len()
    ));
    lines.push(format!(
        "  Local Ignore: {} (sha256 {}, {} bytes)",
        local_ignore_state_label(data.local_ignore_state),
        data.local_ignore_identity.sha256_hex(),
        data.local_ignore_identity.byte_len()
    ));
    if let Some(reset) = data.local_ignore_reset.as_ref() {
        lines.push(format!(
            "  Local Ignore backup: {} (sha256 {}, {} bytes)",
            reset.backup_path.display(),
            reset.backup_identity.sha256_hex(),
            reset.backup_identity.byte_len()
        ));
        lines.push(format!(
            "  Local Ignore replacement: {} (sha256 {})",
            reset.local_ignore_path.display(),
            reset.replacement_identity.sha256_hex()
        ));
    }
    for diagnostic in &data.diagnostics {
        lines.push(format!(
            "  {}",
            format_installed_yaml_data_diagnostic(diagnostic)
        ));
    }
}

/// Formats one structured selection, validation, generation, or reset diagnostic.
fn format_installed_yaml_data_diagnostic(diagnostic: &InstalledYamlDataRunDiagnostic) -> String {
    let mut context = Vec::new();
    if let Some(role) = diagnostic.role() {
        context.push(format!("{role}"));
    }
    if let Some(candidate) = diagnostic.candidate() {
        context.push(provenance_label(candidate).to_string());
    }
    if let Some(path) = diagnostic.path() {
        context.push(path.display().to_string());
    }

    let mut line = format!(
        "{}: {}",
        diagnostic_kind_label(diagnostic.kind()),
        diagnostic.message()
    );
    if !context.is_empty() {
        line.push_str(&format!(" [{}]", context.join(", ")));
    }
    line
}

/// Returns the user-facing label for one selected candidate's provenance.
const fn provenance_label(provenance: InstalledYamlDataProvenance) -> &'static str {
    match provenance {
        InstalledYamlDataProvenance::Updated => "updated",
        InstalledYamlDataProvenance::Previous => "previous",
        InstalledYamlDataProvenance::Bundled => "bundled",
    }
}

/// Returns the user-facing label for how Local Ignore YAML Data entered the run.
const fn local_ignore_state_label(state: LocalIgnoreRunState) -> &'static str {
    match state {
        LocalIgnoreRunState::Existing => "existing",
        LocalIgnoreRunState::Generated => "generated from selected Main defaults",
        LocalIgnoreRunState::RecoveryRequired => "recovery required",
        LocalIgnoreRunState::ProceedWithoutIgnore => "proceeded without ignore entries",
        LocalIgnoreRunState::ResetToDefault => "reset to default",
    }
}

/// Returns the user-facing label for one stable diagnostic category.
const fn diagnostic_kind_label(kind: InstalledYamlDataRunDiagnosticKind) -> &'static str {
    match kind {
        InstalledYamlDataRunDiagnosticKind::CacheUnavailable => "update cache unavailable",
        InstalledYamlDataRunDiagnosticKind::Missing => "missing candidate",
        InstalledYamlDataRunDiagnosticKind::Read => "read failure",
        InstalledYamlDataRunDiagnosticKind::InvalidUtf8 => "invalid UTF-8",
        InstalledYamlDataRunDiagnosticKind::Parse => "parse failure",
        InstalledYamlDataRunDiagnosticKind::InvalidSchema => "invalid schema",
        InstalledYamlDataRunDiagnosticKind::IncompatibleSchema => "incompatible schema",
        InstalledYamlDataRunDiagnosticKind::InvalidRoleData => "invalid role data",
        InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated => "local ignore generated",
        InstalledYamlDataRunDiagnosticKind::LocalIgnoreReset => "local ignore reset",
    }
}

/// Returns the user-facing label for a durable-publication stage in a reset failure.
const fn reset_failure_stage_label(stage: LocalIgnoreResetFailureStage) -> &'static str {
    match stage {
        LocalIgnoreResetFailureStage::Create => "create",
        LocalIgnoreResetFailureStage::Write => "write",
        LocalIgnoreResetFailureStage::Flush => "flush",
        LocalIgnoreResetFailureStage::Sync => "sync",
        LocalIgnoreResetFailureStage::Publish => "publish",
    }
}

/// Presents a typed continuation-resume failure without collapsing its actionable context.
///
/// Replay, reset conflict, backup failure, replacement failure, and durability uncertainty stay
/// distinguishable by their stable code so a user can tell "nothing changed" from "act now".
pub(crate) fn format_resume_error(error: &ResumeError) -> TerminalPresentation {
    let code = error.kind().as_str();
    let message = error.to_string();
    let mut lines = vec![
        format!("Crash Log Scan recovery failed ({code})"),
        message.clone(),
    ];

    match error {
        ResumeError::ContinuationConsumed => {
            lines.push(
                "This recovery decision was already applied. Start the scan again to retry."
                    .to_string(),
            );
        }
        ResumeError::LocalIgnoreResetConflict(conflict) => {
            lines.push(format!(
                "Expected identity: sha256 {}",
                conflict.expected_identity.sha256_hex()
            ));
            match conflict.actual_identity.as_ref() {
                Some(actual) => {
                    lines.push(format!("Actual identity: sha256 {}", actual.sha256_hex()));
                }
                // An absent current identity means another actor removed the file while the user
                // was deciding, which is still a refusal to overwrite rather than a failed write.
                None => lines.push(
                    "Actual identity: the malformed file was removed while you decided".to_string(),
                ),
            }
            if let Some(backup) = conflict.backup_path.as_ref() {
                lines.push(format!("Verified backup: {}", backup.display()));
            }
            lines.push("Your Local Ignore file was not replaced.".to_string());
        }
        ResumeError::LocalIgnoreResetBackupFailure(failure)
        | ResumeError::LocalIgnoreResetReplacementFailure(failure) => {
            lines.push(format!("Path: {}", failure.path.display()));
            if let Some(stage) = failure.stage {
                lines.push(format!("Stage: {}", reset_failure_stage_label(stage)));
            }
        }
        ResumeError::LocalIgnoreResetDurabilityUnknown(failure) => {
            // The replacement is already visible and the backup is verified, so this reports a
            // recovery receipt rather than telling the user that nothing happened.
            lines.push(format!("Path: {}", failure.path.display()));
            lines.push(format!(
                "Verified backup: {}",
                failure.backup_path.display()
            ));
            lines.push(format!(
                "Malformed identity: sha256 {}",
                failure.malformed_identity.sha256_hex()
            ));
            lines.push(format!(
                "Backup identity: sha256 {}",
                failure.backup_identity.sha256_hex()
            ));
            lines.push(format!(
                "Replacement identity: sha256 {}",
                failure.replacement_identity.sha256_hex()
            ));
        }
        ResumeError::Infrastructure(infrastructure) => {
            lines.push(format!("Stage: {}", infrastructure.stage));
            if let Some(path) = infrastructure.path.as_ref() {
                lines.push(format!("Path: {}", path.display()));
            }
        }
    }

    TerminalPresentation {
        percent: 0.0,
        status: format!("Crash Log Scan recovery failed ({code}): {message}"),
        details: lines.join("\n"),
    }
}

struct DispositionPresentation {
    event: &'static str,
    terminal: &'static str,
}

/// Returns both capitalization forms from one exhaustive disposition mapping.
const fn disposition_presentation(disposition: LogDisposition) -> DispositionPresentation {
    match disposition {
        LogDisposition::Succeeded => DispositionPresentation {
            event: "Succeeded",
            terminal: "succeeded",
        },
        LogDisposition::Failed => DispositionPresentation {
            event: "Failed",
            terminal: "failed",
        },
        LogDisposition::CancelledBeforeStart => DispositionPresentation {
            event: "Cancelled before start",
            terminal: "cancelled before start",
        },
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
