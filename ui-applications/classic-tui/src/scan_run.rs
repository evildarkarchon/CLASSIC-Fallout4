//! TUI projection and presentation for the final Crash Log Scan Run contract.

#[cfg(test)]
#[path = "scan_run_tests.rs"]
mod tests;

use classic_scanlog_core::scan_run::contract::{
    Configuration, Event, InfrastructureError, LogDisposition, LogEvent, LogFailureStage, Request,
    RunResult,
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
