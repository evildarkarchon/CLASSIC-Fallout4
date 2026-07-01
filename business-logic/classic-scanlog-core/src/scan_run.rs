//! Crash Log Scan Run execution.
//!
//! This module owns the post-intake transaction for selected Crash Logs: analysis,
//! Autoscan Report writing, progress and cancellation semantics, failed-log accounting,
//! and optional Unsolved Logs relocation.

use crate::error::{Result, ScanLogError};
use crate::report::autoscan_report_path;
use crate::{
    AnalysisResult, BatchScanEvent, BatchScanEventKind, BatchScanOptions, FcxModeHandler,
    FcxResetError, IndexedAnalysisResult, OrchestratorCore, ScanProgressPhase, ScanReadyAnalysis,
};
use classic_database_core::DatabasePool;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::AtomicBool;
use std::time::Duration;

const CANCELLED_BY_USER_MESSAGE: &str = "Cancelled by user";

/// Executes a Crash Log Scan Run after Crash Log Scan Intake.
#[derive(Clone)]
pub struct CrashLogScanRun {
    ready: ScanReadyAnalysis,
}

impl CrashLogScanRun {
    /// Creates a Crash Log Scan Run module from prepared Crash Log Scan Intake output.
    #[must_use]
    pub fn new(ready: ScanReadyAnalysis) -> Self {
        Self { ready }
    }

    /// Runs analysis for the selected Crash Logs and owns all run-level side effects.
    ///
    /// # Errors
    ///
    /// Returns an error for setup failures that prevent the run from starting, such as
    /// FCX reset failure, orchestrator initialization failure, or FormID database setup
    /// failure. Per-log analysis, Autoscan Report write, and Unsolved Logs relocation
    /// failures are returned as log outcomes instead.
    pub async fn run<F>(
        &self,
        request: CrashLogScanRunRequest,
        mut on_event: F,
    ) -> Result<CrashLogScanRunResult>
    where
        F: FnMut(CrashLogScanRunEvent),
    {
        reset_fcx_state()?;

        let total = request.logs.len();
        if total == 0 {
            return Ok(CrashLogScanRunResult::empty());
        }

        let CrashLogScanRunRequest {
            logs,
            mode,
            max_concurrent,
            cancellation,
            preserve_order,
        } = request;

        let mut orchestrator = self.build_orchestrator().await?;
        let log_paths: Vec<String> = logs
            .iter()
            .map(|path| path.to_string_lossy().to_string())
            .collect();

        let indexed_results = orchestrator
            .process_logs_batch_with_events(
                log_paths,
                BatchScanOptions {
                    max_concurrent,
                    preserve_order,
                    cancellation,
                },
                |event| {
                    if let Some(event) = CrashLogScanRunEvent::from_batch_event(event) {
                        on_event(event);
                    }
                },
            )
            .await;

        let mut outcomes = Vec::with_capacity(indexed_results.len());
        let mut completed = 0usize;
        for indexed in indexed_results {
            completed += 1;
            let outcome = finalize_log_outcome(indexed, &mode, &orchestrator).await;
            on_event(outcome.terminal_event(completed, total));
            outcomes.push(outcome);
        }

        orchestrator.async_exit().await?;

        Ok(CrashLogScanRunResult::from_outcomes(outcomes))
    }

    async fn build_orchestrator(&self) -> Result<OrchestratorCore> {
        let mut orchestrator = OrchestratorCore::new(self.ready.analysis_config.clone())?;

        if self.ready.should_initialize_formid_database() {
            let cache_profile = self.ready.cache_profile;
            let pool = Arc::new(DatabasePool::new(
                None,
                Duration::from_secs(cache_profile.cache_ttl_secs),
                self.ready.analysis_config.game.clone(),
            ));
            cache_profile.apply_to_pool(&pool);
            pool.initialize(self.ready.formid_readiness.database_paths.clone())
                .await
                .map_err(|error| ScanLogError::DatabaseError(error.to_string()))?;
            orchestrator.attach_database_pool(pool)?;
        }

        orchestrator.async_enter(None).await?;
        Ok(orchestrator)
    }
}

/// Request to execute a Crash Log Scan Run for selected Crash Logs.
pub struct CrashLogScanRunRequest {
    /// Selected Crash Logs. Adapters own selection; this module owns execution.
    pub logs: Vec<PathBuf>,
    /// Standard or Targeted Crash Log Scan Run behavior.
    pub mode: CrashLogScanRunMode,
    /// Optional maximum number of concurrently processed Crash Logs.
    pub max_concurrent: Option<usize>,
    /// Optional cooperative cancellation flag checked before each Crash Log starts.
    pub cancellation: Option<Arc<AtomicBool>>,
    /// Return log outcomes in input order instead of completion order.
    pub preserve_order: bool,
}

/// Crash Log Scan Run mode.
pub enum CrashLogScanRunMode {
    /// A Standard Crash Log Scan Run may move failed logs to Unsolved Logs.
    Standard(StandardCrashLogScanRunOptions),
    /// A Targeted Crash Log Scan Run never moves failed logs to Unsolved Logs.
    Targeted,
}

/// Options for a Standard Crash Log Scan Run.
pub struct StandardCrashLogScanRunOptions {
    /// Unsolved Logs policy for failed Crash Logs and related Autoscan Reports.
    pub unsolved_logs: UnsolvedLogsPolicy,
}

/// Unsolved Logs relocation policy.
pub enum UnsolvedLogsPolicy {
    /// Leave failed Crash Logs and Autoscan Reports in place.
    LeaveInPlace,
    /// Move failed Crash Logs and Autoscan Reports to the provided directory.
    MoveTo {
        /// Destination directory for Unsolved Logs.
        directory: PathBuf,
    },
}

/// Result of a completed Crash Log Scan Run.
pub struct CrashLogScanRunResult {
    /// Total selected Crash Logs.
    pub total: usize,
    /// Number of successfully scanned Crash Logs with written Autoscan Reports when present.
    pub succeeded: usize,
    /// Number of failed Crash Logs, excluding cancelled entries.
    pub failed: usize,
    /// Number of Crash Logs cancelled before analysis started.
    pub cancelled: usize,
    /// Per-log outcomes.
    pub logs: Vec<CrashLogScanRunLogOutcome>,
}

impl CrashLogScanRunResult {
    fn empty() -> Self {
        Self {
            total: 0,
            succeeded: 0,
            failed: 0,
            cancelled: 0,
            logs: Vec::new(),
        }
    }

    fn from_outcomes(logs: Vec<CrashLogScanRunLogOutcome>) -> Self {
        let total = logs.len();
        let succeeded = logs
            .iter()
            .filter(|outcome| outcome.outcome == CrashLogScanOutcome::Succeeded)
            .count();
        let cancelled = logs
            .iter()
            .filter(|outcome| outcome.outcome == CrashLogScanOutcome::CancelledBeforeStart)
            .count();
        let failed = total.saturating_sub(succeeded + cancelled);

        Self {
            total,
            succeeded,
            failed,
            cancelled,
            logs,
        }
    }
}

/// Per-Crash Log outcome from a Crash Log Scan Run.
pub struct CrashLogScanRunLogOutcome {
    /// Stable index in the adapter-selected Crash Log list.
    pub input_index: usize,
    /// Crash Log path selected for this entry.
    pub crash_log: PathBuf,
    /// Autoscan Report path when one was successfully written.
    pub autoscan_report: Option<PathBuf>,
    /// Outcome kind.
    pub outcome: CrashLogScanOutcome,
    /// Whether the Crash Log or Autoscan Report was moved to Unsolved Logs.
    pub moved_to_unsolved_logs: bool,
    /// Error message for failed or cancelled outcomes.
    pub error: Option<String>,
    /// Processing time in microseconds.
    pub processing_time_us: u64,
    /// Processing time in milliseconds.
    pub processing_time_ms: u64,
    /// Number of FormIDs found.
    pub formid_count: usize,
    /// Number of plugins detected.
    pub plugin_count: usize,
    /// Number of suspect patterns matched.
    pub suspect_count: usize,
}

impl CrashLogScanRunLogOutcome {
    fn terminal_event(&self, completed: usize, total: usize) -> CrashLogScanRunEvent {
        CrashLogScanRunEvent {
            input_index: self.input_index,
            crash_log: self.crash_log.clone(),
            kind: if self.outcome == CrashLogScanOutcome::Succeeded {
                CrashLogScanRunEventKind::Completed
            } else {
                CrashLogScanRunEventKind::Failed
            },
            phase: ScanProgressPhase::Finalize,
            completed,
            total,
            success: self.outcome == CrashLogScanOutcome::Succeeded,
        }
    }
}

/// Per-log outcome kind.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CrashLogScanOutcome {
    /// Analysis completed and required Autoscan Report work succeeded.
    Succeeded,
    /// Analysis, Autoscan Report writing, or Unsolved Logs movement failed.
    Failed,
    /// Cancellation was requested before this Crash Log started analysis.
    CancelledBeforeStart,
}

/// Progress event emitted by a Crash Log Scan Run.
pub struct CrashLogScanRunEvent {
    /// Stable index in the adapter-selected Crash Log list.
    pub input_index: usize,
    /// Crash Log path associated with the event.
    pub crash_log: PathBuf,
    /// Event kind.
    pub kind: CrashLogScanRunEventKind,
    /// Coarse scan progress phase.
    pub phase: ScanProgressPhase,
    /// Number of completed Crash Logs at event time.
    pub completed: usize,
    /// Total selected Crash Logs.
    pub total: usize,
    /// Whether a terminal event represents success.
    pub success: bool,
}

impl CrashLogScanRunEvent {
    fn from_batch_event(event: BatchScanEvent) -> Option<Self> {
        let kind = match event.kind {
            BatchScanEventKind::Queued => CrashLogScanRunEventKind::Queued,
            BatchScanEventKind::Started => CrashLogScanRunEventKind::Started,
            BatchScanEventKind::Phase => CrashLogScanRunEventKind::Phase,
            BatchScanEventKind::Completed | BatchScanEventKind::Failed => return None,
        };

        Some(Self {
            input_index: event.input_index,
            crash_log: PathBuf::from(event.log_path),
            kind,
            phase: event.phase,
            completed: event.completed,
            total: event.total,
            success: event.success,
        })
    }
}

/// Crash Log Scan Run progress event kind.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CrashLogScanRunEventKind {
    /// The Crash Log has been accepted into the run.
    Queued,
    /// The Crash Log has started processing.
    Started,
    /// The Crash Log reported a coarse analysis phase.
    Phase,
    /// The Crash Log completed successfully.
    Completed,
    /// The Crash Log failed or was cancelled.
    Failed,
}

async fn finalize_log_outcome(
    indexed: IndexedAnalysisResult,
    mode: &CrashLogScanRunMode,
    orchestrator: &OrchestratorCore,
) -> CrashLogScanRunLogOutcome {
    let input_index = indexed.input_index;
    let result = indexed.result;
    let crash_log = PathBuf::from(result.log_path.clone());
    let mut outcome = outcome_from_analysis(&result);
    let mut error = result.error.clone();
    let mut autoscan_report = None;

    if result.success && !result.report_lines.is_empty() {
        match orchestrator
            .write_autoscan_report(&crash_log, &result.report_lines)
            .await
        {
            Ok(path) => autoscan_report = Some(path),
            Err(write_error) => {
                outcome = CrashLogScanOutcome::Failed;
                error = Some(write_error.to_string());
            }
        }
    }

    let mut moved_to_unsolved_logs = false;
    if outcome == CrashLogScanOutcome::Failed
        && let Some(directory) = unsolved_logs_directory(mode)
    {
        match move_unsolved_artifacts(&crash_log, directory).await {
            Ok(moved) => moved_to_unsolved_logs = moved,
            Err(move_error) => {
                error = Some(match error {
                    Some(existing) => format!("{existing}; {move_error}"),
                    None => move_error.to_string(),
                });
            }
        }
    }

    CrashLogScanRunLogOutcome {
        input_index,
        crash_log,
        autoscan_report,
        outcome,
        moved_to_unsolved_logs,
        error,
        processing_time_us: result.processing_time_us,
        processing_time_ms: result.processing_time_ms,
        formid_count: result.formid_count,
        plugin_count: result.plugin_count,
        suspect_count: result.suspect_count,
    }
}

fn outcome_from_analysis(result: &AnalysisResult) -> CrashLogScanOutcome {
    if result.success {
        CrashLogScanOutcome::Succeeded
    } else if result.error.as_deref() == Some(CANCELLED_BY_USER_MESSAGE) {
        CrashLogScanOutcome::CancelledBeforeStart
    } else {
        CrashLogScanOutcome::Failed
    }
}

fn unsolved_logs_directory(mode: &CrashLogScanRunMode) -> Option<&Path> {
    match mode {
        CrashLogScanRunMode::Standard(StandardCrashLogScanRunOptions {
            unsolved_logs: UnsolvedLogsPolicy::MoveTo { directory },
        }) => Some(directory),
        CrashLogScanRunMode::Standard(StandardCrashLogScanRunOptions {
            unsolved_logs: UnsolvedLogsPolicy::LeaveInPlace,
        })
        | CrashLogScanRunMode::Targeted => None,
    }
}

async fn move_unsolved_artifacts(log_path: &Path, destination_dir: &Path) -> Result<bool> {
    let autoscan_path = autoscan_report_path(log_path);
    let moved_log = move_file_if_exists(log_path, destination_dir).await?;
    let moved_report = move_file_if_exists(&autoscan_path, destination_dir).await?;
    Ok(moved_log || moved_report)
}

async fn move_file_if_exists(source: &Path, destination_dir: &Path) -> Result<bool> {
    match tokio::fs::metadata(source).await {
        Ok(metadata) if metadata.is_file() => {}
        Ok(_) => return Ok(false),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(false),
        Err(error) => return Err(ScanLogError::IoError(error)),
    }

    tokio::fs::create_dir_all(destination_dir).await?;
    let file_name = source.file_name().ok_or_else(|| {
        ScanLogError::InvalidInput(format!(
            "Cannot move path without file name: {}",
            source.display()
        ))
    })?;
    let destination = destination_dir.join(file_name);
    if source == destination {
        return Ok(false);
    }
    let destination = next_available_destination(destination).await?;

    match tokio::fs::rename(source, &destination).await {
        Ok(()) => Ok(true),
        Err(_) => {
            tokio::fs::copy(source, &destination).await?;
            tokio::fs::remove_file(source).await?;
            Ok(true)
        }
    }
}

async fn next_available_destination(destination: PathBuf) -> Result<PathBuf> {
    if !path_exists(&destination).await? {
        return Ok(destination);
    }

    let parent = destination.parent().unwrap_or_else(|| Path::new(""));
    let stem = destination
        .file_stem()
        .map(|stem| stem.to_string_lossy())
        .unwrap_or_else(|| "artifact".into());
    let extension = destination
        .extension()
        .map(|extension| extension.to_string_lossy());

    for suffix in 1.. {
        let candidate_name = match extension.as_ref() {
            Some(extension) if !extension.is_empty() => format!("{stem}-{suffix}.{extension}"),
            _ => format!("{stem}-{suffix}"),
        };
        let candidate = parent.join(candidate_name);
        if !path_exists(&candidate).await? {
            return Ok(candidate);
        }
    }

    Err(ScanLogError::Internal(format!(
        "Could not find available Unsolved Logs destination for {}",
        destination.display()
    )))
}

async fn path_exists(path: &Path) -> Result<bool> {
    match tokio::fs::metadata(path).await {
        Ok(_) => Ok(true),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(ScanLogError::IoError(error)),
    }
}

fn reset_fcx_state() -> Result<()> {
    match FcxModeHandler::reset_global_state() {
        Ok(()) | Err(FcxResetError::Unnecessary) => Ok(()),
        Err(error) => Err(ScanLogError::Internal(format!(
            "Failed to reset FCX state before Crash Log Scan Run: {error}"
        ))),
    }
}

#[cfg(test)]
#[path = "scan_run_tests.rs"]
mod tests;
