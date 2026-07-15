//! Crash Log Scan Run execution.
//!
//! This module owns the post-intake transaction for selected Crash Logs: analysis,
//! Autoscan Report writing, progress and cancellation semantics, failed-log accounting,
//! and optional Unsolved Logs relocation.

pub mod contract;

use crate::error::{Result, ScanLogError};
use crate::report::autoscan_report_path;
use crate::{
    AnalysisResult, BatchScanEvent, BatchScanEventKind, BatchScanOptions, ConfigIssue,
    CrashLogScanFacts, CrashLogScanIntake, CrashLogScanOptions, OrchestratorCore,
    ScanProgressPhase, ScanReadyAnalysis, resolve_batch_concurrency,
};
use classic_database_core::DatabasePool;
use classic_file_io_core::{LogCollector, RejectedInput, resolve_targeted_inputs};
use classic_operation_context::scope_cancellation;
use classic_scangame_core::{
    ConfigFileCache, GameSetupCheckState, GameSetupIntake, GameSetupIntakeResult, ModIniScanner,
};
use classic_shared_core::GameId;
use futures::stream::{FuturesUnordered, StreamExt};
use std::collections::VecDeque;
use std::future::Future;
use std::path::{Path, PathBuf};
use std::pin::Pin;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;
use tokio::sync::mpsc;

#[cfg(test)]
use self::test_support::{InfrastructureFault, ScanRunTestHooks};

const CANCELLED_BY_USER_MESSAGE: &str = "Cancelled by user";

/// High-level facade for complete Crash Log Scan Runs.
///
/// This boundary owns source discovery, optional FCX setup validation, intake
/// preparation, execution, and result assembly. Lower-level tests and internal
/// callers can still use [`CrashLogScanRun`] when they already have prepared
/// intake and accepted Crash Logs.
pub struct CrashLogScanRunService;

impl CrashLogScanRunService {
    /// Executes a complete Crash Log Scan Run from typed request data.
    ///
    /// Expected lifecycle outcomes such as no logs, setup failure, and
    /// cancellation before discovery are returned as structured result data.
    ///
    /// # Errors
    ///
    /// Returns errors for infrastructure failures such as YAML loading, log
    /// discovery I/O failures, orchestrator setup, or unexpected analysis setup.
    pub async fn execute<F>(
        request: CrashLogScanRunServiceRequest,
        on_event: F,
    ) -> Result<CrashLogScanRunResult>
    where
        F: FnMut(CrashLogScanRunEvent),
    {
        let mut on_event = on_event;
        execute_service(request, |event| {
            if let CrashLogScanRunServiceEvent::Log(event) = event {
                on_event(event);
            }
        })
        .await
        .map_err(CrashLogScanRunServiceError::into_source)
    }
}

/// Transitional lifecycle events used to route the final contract through the
/// provisional service without delaying observation until the run has ended.
pub(super) enum CrashLogScanRunServiceEvent {
    /// Discovery completed with a retainable result.
    DiscoveryCompleted(CrashLogScanDiscoveryResult),
    /// Rust selected the effective concurrency for the discovered work volume.
    EffectiveConcurrencySelected(usize),
    /// Existing log-scoped progress event.
    Log(CrashLogScanRunEvent),
}

/// Stage-aware internal error used by the final contract without changing the
/// temporary public service facade's legacy `ScanLogError` surface.
pub(super) struct CrashLogScanRunServiceError {
    pub(super) stage: contract::InfrastructureErrorStage,
    pub(super) message: String,
    pub(super) path: Option<PathBuf>,
    source: ScanLogError,
}

impl CrashLogScanRunServiceError {
    /// Captures the lifecycle stage and relevant path at the point an error occurs.
    fn new(
        stage: contract::InfrastructureErrorStage,
        path: Option<PathBuf>,
        source: ScanLogError,
    ) -> Self {
        Self {
            stage,
            message: source.to_string(),
            path,
            source,
        }
    }

    /// Restores the compatibility error expected by the transitional public facade.
    fn into_source(self) -> ScanLogError {
        self.source
    }
}

/// Executes the provisional service while exposing complete lifecycle hooks to
/// the final expand-step contract.
pub(super) async fn execute_service<F>(
    request: CrashLogScanRunServiceRequest,
    mut on_event: F,
) -> std::result::Result<CrashLogScanRunResult, CrashLogScanRunServiceError>
where
    F: FnMut(CrashLogScanRunServiceEvent),
{
    let discovery_path = discovery_relevant_path(&request.source);
    #[cfg(test)]
    if let Some(error) = request
        .test_hooks
        .infrastructure_failure(InfrastructureFault::Discovery)
    {
        return Err(CrashLogScanRunServiceError::new(
            contract::InfrastructureErrorStage::Discovery,
            discovery_path,
            error,
        ));
    }

    if cancellation_requested(request.cancellation.as_ref()) {
        return Ok(CrashLogScanRunResult::cancelled_before_discovery());
    }

    // File-I/O owns the discovery loops, while the unpublished task context
    // carries this run's control across that crate boundary without creating a
    // new binding-facing API or process-global cancellation state.
    let Some(discovery) =
        scope_cancellation(request.cancellation.clone(), discover_scan_source(&request))
            .await
            .map_err(|error| {
                CrashLogScanRunServiceError::new(
                    contract::InfrastructureErrorStage::Discovery,
                    discovery_path,
                    error,
                )
            })?
    else {
        return Ok(CrashLogScanRunResult::cancelled_before_discovery());
    };
    on_event(CrashLogScanRunServiceEvent::DiscoveryCompleted(
        discovery.clone(),
    ));
    if discovery.accepted_logs.is_empty() {
        return Ok(CrashLogScanRunResult::no_logs_found(discovery));
    }
    if cancellation_requested(request.cancellation.as_ref()) {
        return Ok(CrashLogScanRunResult::cancelled_after_discovery(discovery));
    }

    let intake_path = request
        .setup_context
        .as_ref()
        .and_then(|context| context.game_root.clone())
        .or_else(|| Some(request.yaml_dir_data.clone()));
    #[cfg(test)]
    if let Some(error) = request
        .test_hooks
        .infrastructure_failure(InfrastructureFault::Intake)
    {
        return Err(CrashLogScanRunServiceError::new(
            contract::InfrastructureErrorStage::Intake,
            intake_path,
            error,
        ));
    }
    let (setup, setup_failed) = evaluate_setup_for_scan(&request).map_err(|error| {
        CrashLogScanRunServiceError::new(
            contract::InfrastructureErrorStage::Intake,
            intake_path.clone(),
            error,
        )
    })?;
    if setup_failed {
        let message = setup
            .as_ref()
            .and_then(|setup| setup.message.clone())
            .unwrap_or_else(|| "Crash Log Scan setup failed".to_string());
        return Ok(CrashLogScanRunResult::setup_failed(
            discovery, setup, message,
        ));
    }

    let targeted_mode = matches!(&request.source, CrashLogScanSource::Targeted(_));
    let mut scan_facts = request.scan_facts.clone();
    if targeted_mode || !request.move_unsolved_logs {
        // Intake validates configured destinations eagerly, so omit this fact
        // when the accepted run intent guarantees relocation cannot occur.
        scan_facts.unsolved_logs_destination = None;
    }

    let ready = CrashLogScanIntake::from_yaml_paths(
        request.yaml_dir_root.clone(),
        request.yaml_dir_data.clone(),
        request.game.clone(),
        request.game_version.clone(),
        request.options,
    )
    .with_scan_facts(scan_facts)
    .prepare()
    .await
    .map_err(|error| {
        CrashLogScanRunServiceError::new(
            contract::InfrastructureErrorStage::Intake,
            intake_path,
            error,
        )
    })?;

    let database_path = ready.formid_readiness().database_paths().first().cloned();
    #[cfg(test)]
    if let Some(error) = request
        .test_hooks
        .infrastructure_failure(InfrastructureFault::FormIdDatabaseAccess)
    {
        return Err(service_execution_error(error, database_path));
    }
    #[cfg(test)]
    if let Some(error) = request
        .test_hooks
        .infrastructure_failure(InfrastructureFault::Initialization)
    {
        return Err(service_execution_error(error, database_path));
    }

    let effective_concurrency = resolve_batch_concurrency(
        discovery.accepted_logs.len(),
        normalize_scan_run_concurrency(request.max_concurrent),
    )
    .min(discovery.accepted_logs.len());
    on_event(CrashLogScanRunServiceEvent::EffectiveConcurrencySelected(
        effective_concurrency,
    ));

    let configured_unsolved_logs_destination = ready
        .unsolved_logs_destination()
        .map(std::path::Path::to_path_buf);
    let intent = CrashLogScanRunIntent::from_configured_flags(
        targeted_mode,
        request.move_unsolved_logs,
        configured_unsolved_logs_destination,
    );
    let setup_snapshot = setup.map(Arc::new);
    let run = CrashLogScanRun::with_setup(ready, setup_snapshot.clone());
    #[cfg(test)]
    let run = run.with_test_hooks(request.test_hooks.clone());
    let mut result = run
        .run_scheduled(
            discovery.accepted_logs.clone(),
            intent,
            effective_concurrency,
            request.cancellation.clone(),
            request.preserve_order,
            |event| on_event(CrashLogScanRunServiceEvent::Log(event)),
        )
        .await
        .map_err(|error| service_execution_error(error, database_path.clone()))?;

    #[cfg(test)]
    if let Some(error) = request
        .test_hooks
        .infrastructure_failure(InfrastructureFault::InternalInvariant)
    {
        return Err(service_execution_error(error, database_path));
    }
    result.discovery = Some(discovery);
    result.setup = setup_snapshot.as_deref().cloned();
    Ok(result)
}

/// Returns the most useful path for a failure while discovering the requested source.
fn discovery_relevant_path(source: &CrashLogScanSource) -> Option<PathBuf> {
    match source {
        CrashLogScanSource::Standard(source) => Some(source.base_directory.clone()),
        CrashLogScanSource::Targeted(source) => source.inputs.first().cloned(),
    }
}

/// Classifies failures after intake at the exact execution boundary that produced them.
fn service_execution_error(
    error: ScanLogError,
    database_path: Option<PathBuf>,
) -> CrashLogScanRunServiceError {
    let (stage, path) = match &error {
        ScanLogError::InvalidInput(_) | ScanLogError::ValidationError(_) => {
            (contract::InfrastructureErrorStage::RequestValidation, None)
        }
        ScanLogError::DatabaseError(_) => (
            contract::InfrastructureErrorStage::FormIdDatabaseAccess,
            database_path,
        ),
        ScanLogError::Internal(_) => (contract::InfrastructureErrorStage::InternalInvariant, None),
        ScanLogError::IoError(_)
        | ScanLogError::FileIOError(_)
        | ScanLogError::ConfigError(_)
        | ScanLogError::ParseError(_)
        | ScanLogError::InvalidFormID(_)
        | ScanLogError::AnalysisError(_)
        | ScanLogError::RegexError(_)
        | ScanLogError::PatternError(_)
        | ScanLogError::ReportError(_)
        | ScanLogError::GpuError(_) => (contract::InfrastructureErrorStage::Initialization, None),
    };
    CrashLogScanRunServiceError::new(stage, path, error)
}

/// Request for a complete Crash Log Scan Run.
pub struct CrashLogScanRunServiceRequest {
    /// Root directory containing settings and ignore YAML.
    pub yaml_dir_root: PathBuf,
    /// `CLASSIC Data` directory containing shippable YAML databases.
    pub yaml_dir_data: PathBuf,
    /// Game identifier, e.g. `Fallout4`.
    pub game: String,
    /// Selected game-version mode.
    pub game_version: String,
    /// Scan options used by Crash Log Scan Intake.
    pub options: CrashLogScanOptions,
    /// Typed source to discover accepted Crash Logs from.
    pub source: CrashLogScanSource,
    /// Explicit setup facts supplied by adapters when FCX Mode is enabled.
    pub setup_context: Option<CrashLogScanSetupContext>,
    /// Whether failed Standard runs move logs and reports to Unsolved Logs.
    pub move_unsolved_logs: bool,
    /// Typed User Settings facts supplied by the caller's settings adapter.
    pub scan_facts: CrashLogScanFacts,
    /// Optional maximum number of concurrently processed Crash Logs.
    pub max_concurrent: Option<usize>,
    /// Optional cooperative cancellation flag.
    pub cancellation: Option<Arc<AtomicBool>>,
    /// Return log outcomes in input order instead of completion order.
    pub preserve_order: bool,
    /// Request-scoped deterministic hooks used only by internal behavior tests.
    #[cfg(test)]
    pub(crate) test_hooks: ScanRunTestHooks,
}

/// Source to discover Crash Logs for a complete scan run.
#[derive(Clone, Debug)]
pub enum CrashLogScanSource {
    /// Standard discovery from CLASSIC's normal scan locations.
    Standard(StandardCrashLogScanSource),
    /// Targeted discovery from explicit user-selected paths.
    Targeted(TargetedCrashLogScanSource),
}

/// Standard Crash Log Scan Run discovery request.
#[derive(Clone, Debug)]
pub struct StandardCrashLogScanSource {
    /// Base directory where `Crash Logs/` and `Crash Logs/Pastebin/` are managed.
    pub base_directory: PathBuf,
    /// Optional custom scan directory. It is additive and non-recursive.
    pub custom_scan_directory: Option<PathBuf>,
    /// Optional configured documents root used to resolve the game XSE folder.
    pub configured_documents_root: Option<PathBuf>,
}

/// Targeted Crash Log Scan Run discovery request.
#[derive(Clone, Debug)]
pub struct TargetedCrashLogScanSource {
    /// User-selected file or directory inputs.
    pub inputs: Vec<PathBuf>,
}

/// Explicit setup facts supplied to a Crash Log Scan Run when FCX Mode is enabled.
#[derive(Clone, Debug, Default)]
pub struct CrashLogScanSetupContext {
    /// Saved or caller-provided game installation root.
    pub game_root: Option<PathBuf>,
    /// Saved or caller-provided documents root.
    pub docs_root: Option<PathBuf>,
    /// Saved or caller-provided game executable path.
    pub game_exe_path: Option<PathBuf>,
    /// Optional XSE log path used as a game-root detection hint.
    pub xse_log_path: Option<PathBuf>,
}

/// Lifecycle status for a complete Crash Log Scan Run.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CrashLogScanRunStatus {
    /// The run reached the end, even if one or more per-log outcomes failed.
    Completed,
    /// Discovery completed and found no accepted Crash Logs.
    NoCrashLogsFound,
    /// FCX setup validation required caller action before analysis could start.
    SetupFailed,
    /// Cancellation was requested before discovery began.
    CancelledBeforeDiscovery,
    /// Cancellation was requested after accepted Crash Logs were known.
    Cancelled,
}

impl CrashLogScanRunStatus {
    /// Returns the stable adapter-facing status identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Completed => "completed",
            Self::NoCrashLogsFound => "no_crash_logs_found",
            Self::SetupFailed => "setup_failed",
            Self::CancelledBeforeDiscovery => "cancelled_before_discovery",
            Self::Cancelled => "cancelled",
        }
    }
}

/// Source kind recorded by Crash Log Scan Discovery Result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CrashLogScanDiscoverySource {
    /// Standard discovery from normal scan locations.
    Standard,
    /// Targeted discovery from explicit user-selected paths.
    Targeted,
}

impl CrashLogScanDiscoverySource {
    /// Returns the stable adapter-facing source identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Standard => "standard",
            Self::Targeted => "targeted",
        }
    }
}

/// Structured discovery data for a Crash Log Scan Run.
#[derive(Clone, Debug)]
pub struct CrashLogScanDiscoveryResult {
    /// Source kind that produced the discovery result.
    pub source: CrashLogScanDiscoverySource,
    /// Accepted Crash Logs in discovery order.
    pub accepted_logs: Vec<PathBuf>,
    /// Targeted inputs rejected during discovery.
    pub rejected_inputs: Vec<CrashLogScanRejectedInput>,
    /// Locations or inputs searched during discovery.
    pub searched_locations: Vec<PathBuf>,
}

/// Targeted input that did not resolve to an accepted Crash Log.
#[derive(Clone, Debug)]
pub struct CrashLogScanRejectedInput {
    /// Original path supplied by the user.
    pub path: PathBuf,
    /// Human-readable rejection reason.
    pub reason: String,
}

impl From<RejectedInput> for CrashLogScanRejectedInput {
    fn from(value: RejectedInput) -> Self {
        Self {
            path: value.path,
            reason: value.reason,
        }
    }
}

/// Structured setup validation data attached to a Crash Log Scan Run Result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CrashLogScanSetupResult {
    /// Adapter-facing setup status identifier.
    pub status: String,
    /// Typed setup checks.
    pub checks: Vec<CrashLogScanSetupCheck>,
    /// Proposed path updates that callers may persist.
    pub path_updates: Vec<CrashLogScanSetupPathUpdate>,
    /// Read-only FCX configuration issues detected from game files.
    pub configuration_issues: Vec<ConfigIssue>,
    /// User actions required before setup can complete.
    pub actions: Vec<String>,
    /// Fatal setup errors.
    pub fatal_errors: Vec<String>,
    /// Optional concise message for adapters.
    pub message: Option<String>,
    /// Canonical setup report text.
    pub rendered_report: String,
}

/// One typed setup check attached to a Crash Log Scan Setup Result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CrashLogScanSetupCheck {
    /// Stable check kind identifier.
    pub kind: String,
    /// Stable check state identifier.
    pub state: String,
    /// Short human-readable summary.
    pub message: String,
    /// Optional detail lines.
    pub details: Vec<String>,
}

/// Proposed setup path update.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CrashLogScanSetupPathUpdate {
    /// Stable path kind, currently `game_root` or `docs_root`.
    pub kind: String,
    /// Proposed path value.
    pub path: PathBuf,
}

/// Executes a Crash Log Scan Run after Crash Log Scan Intake.
#[derive(Clone)]
pub struct CrashLogScanRun {
    ready: ScanReadyAnalysis,
    setup: Option<Arc<CrashLogScanSetupResult>>,
    #[cfg(test)]
    test_hooks: ScanRunTestHooks,
}

/// One phase notification produced by an admitted single-log analysis.
struct ScheduledLogPhase {
    input_index: usize,
    crash_log: PathBuf,
    phase: ScanProgressPhase,
}

/// Internal engine for one admitted log's analysis and durable finalization.
struct SingleLogAnalysisEngine<'a> {
    orchestrator: &'a OrchestratorCore,
    unsolved_logs_destination: Option<&'a Path>,
    #[cfg(test)]
    test_hooks: &'a ScanRunTestHooks,
}

impl SingleLogAnalysisEngine<'_> {
    /// Analyzes and finalizes one admitted Crash Log without consulting cancellation again.
    async fn analyze_and_finalize(
        &self,
        input_index: usize,
        crash_log: PathBuf,
        phase_tx: mpsc::UnboundedSender<ScheduledLogPhase>,
    ) -> CrashLogScanRunLogOutcome {
        let log_path = crash_log.to_string_lossy().to_string();
        #[cfg(test)]
        if let Some(delay) = self.test_hooks.analysis_delay(input_index) {
            tokio::time::sleep(delay).await;
        }
        #[cfg(test)]
        let injected_result = self
            .test_hooks
            .analysis_failure(input_index)
            .map(|message| AnalysisResult::failure(log_path.clone(), message.to_string()));
        #[cfg(not(test))]
        let injected_result: Option<AnalysisResult> = None;
        let result = if let Some(result) = injected_result {
            result
        } else {
            match self
                .orchestrator
                .process_log_with_progress(log_path.clone(), |phase| {
                    let _ = phase_tx.send(ScheduledLogPhase {
                        input_index,
                        crash_log: crash_log.clone(),
                        phase,
                    });
                })
                .await
            {
                Ok(result) => result,
                Err(error) => AnalysisResult::failure(log_path, error.to_string()),
            }
        };

        finalize_log_outcome(
            input_index,
            result,
            self.unsolved_logs_destination,
            self.orchestrator,
            #[cfg(test)]
            self.test_hooks,
        )
        .await
    }
}

impl CrashLogScanRun {
    /// Creates a Crash Log Scan Run module from prepared Crash Log Scan Intake output.
    #[must_use]
    pub fn new(ready: ScanReadyAnalysis) -> Self {
        Self {
            ready,
            setup: None,
            #[cfg(test)]
            test_hooks: ScanRunTestHooks::default(),
        }
    }

    /// Creates a run whose immutable FCX setup result is shared with every log analysis.
    fn with_setup(ready: ScanReadyAnalysis, setup: Option<Arc<CrashLogScanSetupResult>>) -> Self {
        Self {
            ready,
            setup,
            #[cfg(test)]
            test_hooks: ScanRunTestHooks::default(),
        }
    }

    #[cfg(test)]
    /// Attaches request-scoped deterministic hooks without exposing them publicly.
    fn with_test_hooks(mut self, test_hooks: ScanRunTestHooks) -> Self {
        self.test_hooks = test_hooks;
        self
    }

    /// Runs analysis for the selected Crash Logs and owns all run-level side effects.
    ///
    /// # Errors
    ///
    /// Returns an error for setup failures that prevent the run from starting, such as
    /// orchestrator initialization or FormID database setup failure. Per-log analysis,
    /// Autoscan Report write, and Unsolved Logs relocation failures are returned as log
    /// outcomes instead.
    pub async fn run<F>(
        &self,
        request: CrashLogScanRunRequest,
        mut on_event: F,
    ) -> Result<CrashLogScanRunResult>
    where
        F: FnMut(CrashLogScanRunEvent),
    {
        self.run_inner(request, &mut on_event).await
    }

    async fn run_inner<F>(
        &self,
        request: CrashLogScanRunRequest,
        mut on_event: F,
    ) -> Result<CrashLogScanRunResult>
    where
        F: FnMut(CrashLogScanRunEvent),
    {
        self.validate_run_scoped_setup()?;

        let total = request.logs.len();
        if total == 0 {
            return Ok(CrashLogScanRunResult::empty());
        }

        let CrashLogScanRunRequest {
            logs,
            intent,
            max_concurrent,
            cancellation,
            preserve_order,
        } = request;

        // Scan-run sentinel: `Some(0)` means "adaptive default" here, identical to
        // `None`. This fold lives at the scan-run seam only; `resolve_batch_concurrency`
        // keeps `Some(0) -> 1` (serial) for the other batch callers and their tests.
        let max_concurrent = normalize_scan_run_concurrency(max_concurrent);

        let unsolved_logs_destination = resolve_unsolved_logs_destination(&self.ready, &intent)?;

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
            let outcome = finalize_log_outcome(
                indexed.input_index,
                indexed.result,
                unsolved_logs_destination.as_deref(),
                &orchestrator,
                #[cfg(test)]
                &self.test_hooks,
            )
            .await;
            on_event(outcome.terminal_event(completed, total));
            outcomes.push(outcome);
        }

        orchestrator.async_exit().await?;

        Ok(CrashLogScanRunResult::from_outcomes(outcomes))
    }

    /// Runs the final contract's scan-run-owned scheduler over the single-log engine.
    ///
    /// Effective concurrency is selected by the caller exactly once. Cancellation is
    /// checked only before admission; once `Started` is published, the engine runs
    /// through report persistence and applicable Unsolved Logs finalization.
    async fn run_scheduled<F>(
        &self,
        logs: Vec<PathBuf>,
        intent: CrashLogScanRunIntent,
        effective_concurrency: usize,
        cancellation: Option<Arc<AtomicBool>>,
        preserve_order: bool,
        mut on_event: F,
    ) -> Result<CrashLogScanRunResult>
    where
        F: FnMut(CrashLogScanRunEvent),
    {
        self.validate_run_scoped_setup()?;

        let total = logs.len();
        if total == 0 {
            return Ok(CrashLogScanRunResult::empty());
        }

        let unsolved_logs_destination = resolve_unsolved_logs_destination(&self.ready, &intent)?;
        let mut orchestrator = self.build_orchestrator().await?;
        let mut outcomes = schedule_logs(
            &orchestrator,
            logs,
            unsolved_logs_destination.as_deref(),
            effective_concurrency,
            cancellation.as_ref(),
            &mut on_event,
            #[cfg(test)]
            &self.test_hooks,
        )
        .await;
        orchestrator.async_exit().await?;

        if preserve_order {
            outcomes.sort_by_key(|outcome| outcome.input_index);
        }
        Ok(CrashLogScanRunResult::from_outcomes(outcomes))
    }

    /// Rejects FCX execution when no immutable run-owned setup snapshot is attached.
    fn validate_run_scoped_setup(&self) -> Result<()> {
        if self.ready.analysis_config().fcx_mode && self.setup.is_none() {
            return Err(ScanLogError::ValidationError(
                "FCX-enabled Crash Log Scan Runs require run-scoped setup facts; use the final scan_run contract"
                    .to_string(),
            ));
        }
        Ok(())
    }

    async fn build_orchestrator(&self) -> Result<OrchestratorCore> {
        let mut orchestrator = OrchestratorCore::new(self.ready.analysis_config().clone())?;
        orchestrator.set_scan_run_setup(self.setup.clone());

        if self.ready.should_initialize_formid_database() {
            let cache_profile = self.ready.cache_profile();
            let pool = Arc::new(DatabasePool::new(
                None,
                Duration::from_secs(cache_profile.cache_ttl_secs),
                self.ready.analysis_config().game.clone(),
            ));
            cache_profile.apply_to_pool(&pool);
            pool.initialize(self.ready.formid_readiness().database_paths.clone())
                .await
                .map_err(|error| ScanLogError::DatabaseError(error.to_string()))?;
            orchestrator.attach_database_pool(pool)?;
        }

        orchestrator.async_enter(None).await?;
        Ok(orchestrator)
    }
}

/// Schedules discovered logs and serializes every observer call from one execution pump.
async fn schedule_logs<F>(
    orchestrator: &OrchestratorCore,
    logs: Vec<PathBuf>,
    unsolved_logs_destination: Option<&Path>,
    effective_concurrency: usize,
    cancellation: Option<&Arc<AtomicBool>>,
    on_event: &mut F,
    #[cfg(test)] test_hooks: &ScanRunTestHooks,
) -> Vec<CrashLogScanRunLogOutcome>
where
    F: FnMut(CrashLogScanRunEvent),
{
    let total = logs.len();
    let engine = SingleLogAnalysisEngine {
        orchestrator,
        unsolved_logs_destination,
        #[cfg(test)]
        test_hooks,
    };

    for (input_index, crash_log) in logs.iter().enumerate() {
        on_event(CrashLogScanRunEvent {
            input_index,
            crash_log: crash_log.clone(),
            kind: CrashLogScanRunEventKind::Queued,
            phase: ScanProgressPhase::Setup,
            completed: 0,
            total,
            success: false,
            disposition: None,
        });
    }

    type AdmittedLogFuture<'a> =
        Pin<Box<dyn Future<Output = CrashLogScanRunLogOutcome> + Send + 'a>>;
    let (phase_tx, mut phase_rx) = mpsc::unbounded_channel::<ScheduledLogPhase>();
    let mut pending = logs.into_iter().enumerate().collect::<VecDeque<_>>();
    let mut admitted = FuturesUnordered::<AdmittedLogFuture<'_>>::new();
    let mut outcomes = Vec::with_capacity(total);
    let mut completed = 0usize;

    loop {
        while admitted.len() < effective_concurrency {
            if cancellation_requested(cancellation) {
                break;
            }
            let Some((input_index, crash_log)) = pending.pop_front() else {
                break;
            };

            // The successful cancellation check above is the admission boundary.
            // Started publishes that decision; cancellation requested by this callback
            // applies to later queued logs, while this log remains admitted.
            on_event(CrashLogScanRunEvent {
                input_index,
                crash_log: crash_log.clone(),
                kind: CrashLogScanRunEventKind::Started,
                phase: ScanProgressPhase::Setup,
                completed,
                total,
                success: false,
                disposition: None,
            });
            admitted.push(Box::pin(engine.analyze_and_finalize(
                input_index,
                crash_log,
                phase_tx.clone(),
            )));
        }

        if admitted.is_empty() {
            break;
        }

        tokio::select! {
            biased;
            maybe_phase = phase_rx.recv() => {
                if let Some(phase) = maybe_phase {
                    emit_scheduled_phase(on_event, phase, completed, total);
                }
            }
            maybe_outcome = admitted.next() => {
                let Some(outcome) = maybe_outcome else {
                    break;
                };
                while let Ok(phase) = phase_rx.try_recv() {
                    emit_scheduled_phase(on_event, phase, completed, total);
                }
                completed += 1;
                on_event(outcome.terminal_event(completed, total));
                outcomes.push(outcome);
            }
        }
    }

    while let Ok(phase) = phase_rx.try_recv() {
        emit_scheduled_phase(on_event, phase, completed, total);
    }
    for (input_index, crash_log) in pending {
        let outcome = cancelled_log_outcome(input_index, crash_log);
        completed += 1;
        on_event(outcome.terminal_event(completed, total));
        outcomes.push(outcome);
    }

    outcomes
}

/// Request to execute a Crash Log Scan Run for selected Crash Logs.
pub struct CrashLogScanRunRequest {
    /// Selected Crash Logs. Adapters own selection; this module owns execution.
    pub logs: Vec<PathBuf>,
    /// Caller intent for Standard or Targeted Crash Log Scan Run behavior.
    pub intent: CrashLogScanRunIntent,
    /// Optional maximum number of concurrently processed Crash Logs.
    pub max_concurrent: Option<usize>,
    /// Optional cooperative cancellation flag checked before each Crash Log starts.
    pub cancellation: Option<Arc<AtomicBool>>,
    /// Return log outcomes in input order instead of completion order.
    pub preserve_order: bool,
}

/// Crash Log Scan Run intent.
pub enum CrashLogScanRunIntent {
    /// A Standard Crash Log Scan Run may move failed logs to Unsolved Logs.
    Standard(StandardCrashLogScanRunIntent),
    /// A Targeted Crash Log Scan Run never moves failed logs to Unsolved Logs.
    Targeted,
}

impl CrashLogScanRunIntent {
    /// Builds a Crash Log Scan Run intent from already-parsed caller flags.
    ///
    /// This is the request-normalization seam adapters build against: they pass
    /// the user's intent facts (Targeted mode, whether to move Unsolved Logs, and
    /// an optional already-parsed destination path) and the core derives the
    /// Standard/Targeted intent. Behavioral rules stay in the run itself:
    ///
    /// - Targeted mode always wins over any movement flags.
    /// - `move_unsolved_logs == false` means [`StandardUnsolvedLogsIntent::LeaveInPlace`]
    ///   and the destination is ignored.
    /// - Move with an explicit destination means [`StandardUnsolvedLogsIntent::MoveToCustom`].
    /// - Move without a destination means [`StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault`].
    ///
    /// Absolute-path validation of a custom destination stays in
    /// [`CrashLogScanRun::run`]; this constructor is infallible. TUI-style callers
    /// that already hold an `Option<PathBuf>` should use this to avoid a lossy
    /// path -> string -> path round trip; string-based adapters should use
    /// [`CrashLogScanRunIntent::from_adapter_flags`].
    #[must_use]
    pub fn from_configured_flags(
        targeted_mode: bool,
        move_unsolved_logs: bool,
        unsolved_logs_destination: Option<PathBuf>,
    ) -> Self {
        if targeted_mode {
            return CrashLogScanRunIntent::Targeted;
        }

        let unsolved_logs = if !move_unsolved_logs {
            StandardUnsolvedLogsIntent::LeaveInPlace
        } else if let Some(destination) = unsolved_logs_destination {
            StandardUnsolvedLogsIntent::MoveToCustom(destination)
        } else {
            StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault
        };

        CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent { unsolved_logs })
    }

    /// Builds a Crash Log Scan Run intent from raw adapter flags.
    ///
    /// The string-based binding surfaces (CXX, Node, Python) share the destination
    /// sentinel convention where an absent, empty, or whitespace-only destination
    /// means "not supplied". This constructor owns that normalization — trimming
    /// the destination and treating an empty result as absent — then delegates to
    /// [`CrashLogScanRunIntent::from_configured_flags`] so both variants share a
    /// single derivation path.
    #[must_use]
    pub fn from_adapter_flags(
        targeted_mode: bool,
        move_unsolved_logs: bool,
        unsolved_logs_destination: Option<&str>,
    ) -> Self {
        let destination = unsolved_logs_destination
            .map(str::trim)
            .filter(|destination| !destination.is_empty())
            .map(PathBuf::from);
        Self::from_configured_flags(targeted_mode, move_unsolved_logs, destination)
    }
}

/// Intent for a Standard Crash Log Scan Run.
pub struct StandardCrashLogScanRunIntent {
    /// Unsolved Logs intent for failed Crash Logs and related Autoscan Reports.
    pub unsolved_logs: StandardUnsolvedLogsIntent,
}

/// Standard Crash Log Scan Run Unsolved Logs intent.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum StandardUnsolvedLogsIntent {
    /// Leave failed Crash Logs and Autoscan Reports in place.
    LeaveInPlace,
    /// Move failed Crash Logs and Autoscan Reports to the configured destination, or canonical default.
    MoveToConfiguredOrDefault,
    /// Move failed Crash Logs and Autoscan Reports to the provided absolute directory.
    MoveToCustom(PathBuf),
}

/// Result of a completed Crash Log Scan Run.
pub struct CrashLogScanRunResult {
    /// Lifecycle status for the run as a whole.
    pub status: CrashLogScanRunStatus,
    /// Discovery details when the high-level facade owns discovery.
    pub discovery: Option<CrashLogScanDiscoveryResult>,
    /// Setup details when FCX setup validation was requested.
    pub setup: Option<CrashLogScanSetupResult>,
    /// Optional concise run-level message.
    pub message: Option<String>,
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
            status: CrashLogScanRunStatus::NoCrashLogsFound,
            discovery: None,
            setup: None,
            message: Some("No crash logs found".to_string()),
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
            status: if cancelled > 0 {
                CrashLogScanRunStatus::Cancelled
            } else {
                CrashLogScanRunStatus::Completed
            },
            discovery: None,
            setup: None,
            message: None,
            total,
            succeeded,
            failed,
            cancelled,
            logs,
        }
    }

    fn cancelled_before_discovery() -> Self {
        Self {
            status: CrashLogScanRunStatus::CancelledBeforeDiscovery,
            discovery: None,
            setup: None,
            message: Some("Cancelled before crash log discovery".to_string()),
            total: 0,
            succeeded: 0,
            failed: 0,
            cancelled: 0,
            logs: Vec::new(),
        }
    }

    /// Builds a terminal cancellation result after discovery committed but
    /// before any accepted Crash Log entered execution.
    fn cancelled_after_discovery(discovery: CrashLogScanDiscoveryResult) -> Self {
        let logs = discovery
            .accepted_logs
            .iter()
            .enumerate()
            .map(|(input_index, crash_log)| CrashLogScanRunLogOutcome {
                input_index,
                crash_log: crash_log.clone(),
                autoscan_report: None,
                outcome: CrashLogScanOutcome::CancelledBeforeStart,
                report_write_failed: false,
                moved_to_unsolved_logs: false,
                unsolved_logs_finalization_failed: false,
                analysis_error: None,
                report_write_error: None,
                unsolved_logs_finalization_error: None,
                error: Some(CANCELLED_BY_USER_MESSAGE.to_string()),
                processing_time_us: 0,
                processing_time_ms: 0,
                formid_count: 0,
                plugin_count: 0,
                suspect_count: 0,
            })
            .collect::<Vec<_>>();
        let total = logs.len();

        Self {
            status: CrashLogScanRunStatus::Cancelled,
            discovery: Some(discovery),
            setup: None,
            message: Some("Cancelled after crash log discovery".to_string()),
            total,
            succeeded: 0,
            failed: 0,
            cancelled: total,
            logs,
        }
    }

    fn no_logs_found(discovery: CrashLogScanDiscoveryResult) -> Self {
        Self {
            status: CrashLogScanRunStatus::NoCrashLogsFound,
            discovery: Some(discovery),
            setup: None,
            message: Some("No crash logs found".to_string()),
            total: 0,
            succeeded: 0,
            failed: 0,
            cancelled: 0,
            logs: Vec::new(),
        }
    }

    fn setup_failed(
        discovery: CrashLogScanDiscoveryResult,
        setup: Option<CrashLogScanSetupResult>,
        message: String,
    ) -> Self {
        let total = discovery.accepted_logs.len();
        Self {
            status: CrashLogScanRunStatus::SetupFailed,
            discovery: Some(discovery),
            setup,
            message: Some(message),
            total,
            succeeded: 0,
            failed: 0,
            cancelled: 0,
            logs: Vec::new(),
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
    /// Whether analysis succeeded but Autoscan Report writing failed.
    pub report_write_failed: bool,
    /// Whether the Crash Log or Autoscan Report was moved to Unsolved Logs.
    pub moved_to_unsolved_logs: bool,
    /// Whether the requested Unsolved Logs finalization failed.
    pub unsolved_logs_finalization_failed: bool,
    /// Structured analysis failure message, excluding cancellation.
    pub analysis_error: Option<String>,
    /// Structured Autoscan Report persistence failure message.
    pub report_write_error: Option<String>,
    /// Structured Unsolved Logs finalization failure message.
    pub unsolved_logs_finalization_error: Option<String>,
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
            disposition: Some(match self.outcome {
                CrashLogScanOutcome::Succeeded => contract::LogDisposition::Succeeded,
                CrashLogScanOutcome::Failed => contract::LogDisposition::Failed,
                CrashLogScanOutcome::CancelledBeforeStart => {
                    contract::LogDisposition::CancelledBeforeStart
                }
            }),
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
    /// Final contract disposition for terminal events.
    pub disposition: Option<contract::LogDisposition>,
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
            disposition: None,
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

/// Completes report persistence and applicable Unsolved Logs movement for one admitted log.
///
/// This function never consults cancellation. It returns only after durable finalization
/// resolves. Unsolved Logs destinations are claimed atomically, so overlapping runs cannot
/// overwrite one another before their terminal events are published.
async fn finalize_log_outcome(
    input_index: usize,
    result: AnalysisResult,
    unsolved_logs_destination: Option<&Path>,
    orchestrator: &OrchestratorCore,
    #[cfg(test)] test_hooks: &ScanRunTestHooks,
) -> CrashLogScanRunLogOutcome {
    let crash_log = PathBuf::from(result.log_path.clone());
    let mut outcome = outcome_from_analysis(&result);
    let mut error = result.error.clone();
    let analysis_error = if outcome == CrashLogScanOutcome::Failed {
        result.error.clone()
    } else {
        None
    };
    let mut autoscan_report = None;
    let mut report_write_failed = false;
    let mut report_write_error = None;

    if result.success && !result.report_lines.is_empty() {
        match orchestrator
            .write_autoscan_report(&crash_log, &result.report_lines)
            .await
        {
            Ok(path) => autoscan_report = Some(path),
            Err(write_error) => {
                outcome = CrashLogScanOutcome::Failed;
                report_write_failed = true;
                let message = write_error.to_string();
                report_write_error = Some(message.clone());
                error = Some(message);
            }
        }
    }

    let mut moved_to_unsolved_logs = false;
    let mut unsolved_logs_finalization_failed = false;
    let mut unsolved_logs_finalization_error = None;
    if outcome == CrashLogScanOutcome::Failed
        && let Some(directory) = unsolved_logs_destination
    {
        let finalization = move_unsolved_artifacts(
            &crash_log,
            directory,
            #[cfg(test)]
            test_hooks,
        )
        .await;
        moved_to_unsolved_logs = finalization.moved_any;
        if let Some(move_error) = finalization.error {
            unsolved_logs_finalization_failed = true;
            unsolved_logs_finalization_error = Some(move_error.clone());
            error = Some(match error {
                Some(existing) => format!("{existing}; {move_error}"),
                None => move_error,
            });
        }
    }

    CrashLogScanRunLogOutcome {
        input_index,
        crash_log,
        autoscan_report,
        outcome,
        report_write_failed,
        moved_to_unsolved_logs,
        unsolved_logs_finalization_failed,
        analysis_error,
        report_write_error,
        unsolved_logs_finalization_error,
        error,
        processing_time_us: result.processing_time_us,
        processing_time_ms: result.processing_time_ms,
        formid_count: result.formid_count,
        plugin_count: result.plugin_count,
        suspect_count: result.suspect_count,
    }
}

/// Emits one admitted log's phase through the scheduler's single observer pump.
fn emit_scheduled_phase<F>(
    on_event: &mut F,
    phase: ScheduledLogPhase,
    completed: usize,
    total: usize,
) where
    F: FnMut(CrashLogScanRunEvent),
{
    on_event(CrashLogScanRunEvent {
        input_index: phase.input_index,
        crash_log: phase.crash_log,
        kind: CrashLogScanRunEventKind::Phase,
        phase: phase.phase,
        completed,
        total,
        success: false,
        disposition: None,
    });
}

/// Builds the terminal non-start outcome for a discovered log left in the queue.
fn cancelled_log_outcome(input_index: usize, crash_log: PathBuf) -> CrashLogScanRunLogOutcome {
    CrashLogScanRunLogOutcome {
        input_index,
        crash_log,
        autoscan_report: None,
        outcome: CrashLogScanOutcome::CancelledBeforeStart,
        report_write_failed: false,
        moved_to_unsolved_logs: false,
        unsolved_logs_finalization_failed: false,
        analysis_error: None,
        report_write_error: None,
        unsolved_logs_finalization_error: None,
        error: Some(CANCELLED_BY_USER_MESSAGE.to_string()),
        processing_time_us: 0,
        processing_time_ms: 0,
        formid_count: 0,
        plugin_count: 0,
        suspect_count: 0,
    }
}

/// Folds the scan-run `max_concurrent` sentinel: `Some(0)` becomes `None`
/// (adaptive default), matching `None`. Any other value is preserved.
fn normalize_scan_run_concurrency(max_concurrent: Option<usize>) -> Option<usize> {
    max_concurrent.filter(|value| *value != 0)
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

/// Discovers the complete accepted Crash Log set, returning `None` when
/// cancellation wins before the discovery result is committed.
///
/// # Errors
///
/// Returns an error when Standard directory setup, file organization, or
/// enumeration fails. Targeted path rejections remain structured result data.
async fn discover_scan_source(
    request: &CrashLogScanRunServiceRequest,
) -> Result<Option<CrashLogScanDiscoveryResult>> {
    match &request.source {
        CrashLogScanSource::Standard(source) => {
            let collector = LogCollector::new_for_scan(
                source.base_directory.clone(),
                &request.yaml_dir_data,
                &request.game,
                &request.game_version,
                source.configured_documents_root.as_deref(),
                source.custom_scan_directory.clone(),
            );
            let logs = collector.collect_all().await?;
            if cancellation_requested(request.cancellation.as_ref()) {
                return Ok(None);
            }

            let mut searched_locations = vec![
                source.base_directory.clone(),
                source.base_directory.join("Crash Logs"),
            ];
            if let Some(custom) = &source.custom_scan_directory {
                searched_locations.push(custom.clone());
            }
            if let Some(docs) = &source.configured_documents_root {
                searched_locations.push(docs.clone());
            }

            Ok(Some(CrashLogScanDiscoveryResult {
                source: CrashLogScanDiscoverySource::Standard,
                accepted_logs: logs,
                rejected_inputs: Vec::new(),
                searched_locations,
            }))
        }
        CrashLogScanSource::Targeted(source) => {
            let resolution = resolve_targeted_inputs(source.inputs.clone()).await;
            if cancellation_requested(request.cancellation.as_ref()) {
                return Ok(None);
            }

            Ok(Some(CrashLogScanDiscoveryResult {
                source: CrashLogScanDiscoverySource::Targeted,
                accepted_logs: resolution.logs,
                rejected_inputs: resolution
                    .rejected
                    .into_iter()
                    .map(CrashLogScanRejectedInput::from)
                    .collect(),
                searched_locations: source.inputs.clone(),
            }))
        }
    }
}

fn evaluate_setup_for_scan(
    request: &CrashLogScanRunServiceRequest,
) -> Result<(Option<CrashLogScanSetupResult>, bool)> {
    if !request.options.fcx_mode {
        return Ok((None, false));
    }

    let Some(context) = request.setup_context.as_ref() else {
        let setup = CrashLogScanSetupResult::missing_context(
            "FCX Mode requires Crash Log Scan Setup Context",
        );
        return Ok((Some(setup), true));
    };

    let game_id = match request.game.parse::<GameId>() {
        Ok(game_id) => game_id,
        Err(error) => {
            let setup = CrashLogScanSetupResult::fatal(error);
            return Ok((Some(setup), true));
        }
    };

    let mut intake = GameSetupIntake::new(game_id, &request.game_version);
    if let Some(path) = &context.game_root {
        intake = intake.with_game_root(path);
    }
    if let Some(path) = &context.docs_root {
        intake = intake.with_docs_root(path);
    }
    if let Some(path) = &context.game_exe_path {
        intake = intake.with_game_exe_path(path);
    }
    if let Some(path) = &context.xse_log_path {
        intake = intake.with_xse_log_path(path);
    }

    let game_setup = intake.run();
    let configuration_issues = context
        .game_root
        .as_deref()
        .or(game_setup.paths.game_root.as_deref())
        .map(|game_root| detect_config_issues_for_scan(game_root, game_id.as_str()))
        .transpose()?
        .unwrap_or_default();
    let setup = CrashLogScanSetupResult::from_game_setup(game_setup, configuration_issues);
    let setup_failed = setup
        .checks
        .iter()
        .any(|check| check.state == GameSetupCheckState::ActionRequired.as_str())
        || !setup.actions.is_empty()
        || !setup.fatal_errors.is_empty();

    Ok((Some(setup), setup_failed))
}

/// Detects FCX configuration issues without collapsing scanner failures into an empty result.
fn detect_config_issues_for_scan(game_root: &Path, game_name: &str) -> Result<Vec<ConfigIssue>> {
    let mut cache = ConfigFileCache::new(game_root, &[]).map_err(|error| {
        ScanLogError::ConfigError(format!(
            "Failed to prepare FCX configuration issues scan for {}: {error}",
            game_root.display()
        ))
    })?;
    let result = ModIniScanner::scan_with_cache(&mut cache, game_name).map_err(|error| {
        ScanLogError::ConfigError(format!(
            "Failed to detect FCX configuration issues under {}: {error}",
            game_root.display()
        ))
    })?;
    Ok(result
        .issues
        .into_iter()
        .map(scangame_issue_to_scanlog_issue)
        .collect())
}

impl CrashLogScanSetupResult {
    fn missing_context(message: impl Into<String>) -> Self {
        let message = message.into();
        Self {
            status: "action_required".to_string(),
            checks: Vec::new(),
            path_updates: Vec::new(),
            configuration_issues: Vec::new(),
            actions: vec!["provide_setup_context".to_string()],
            fatal_errors: Vec::new(),
            message: Some(message.clone()),
            rendered_report: message,
        }
    }

    fn fatal(message: impl Into<String>) -> Self {
        let message = message.into();
        Self {
            status: "fatal_error".to_string(),
            checks: Vec::new(),
            path_updates: Vec::new(),
            configuration_issues: Vec::new(),
            actions: Vec::new(),
            fatal_errors: vec![message.clone()],
            message: Some(message.clone()),
            rendered_report: message,
        }
    }

    fn from_game_setup(
        value: GameSetupIntakeResult,
        configuration_issues: Vec<ConfigIssue>,
    ) -> Self {
        let message = if value.actions.is_empty() && value.fatal_errors.is_empty() {
            None
        } else if !value.fatal_errors.is_empty() {
            Some("Game setup validation failed".to_string())
        } else {
            Some("Game setup requires additional input".to_string())
        };

        Self {
            status: value.status.as_str().to_string(),
            checks: value
                .checks
                .into_iter()
                .map(|check| CrashLogScanSetupCheck {
                    kind: check.kind.as_str().to_string(),
                    state: check.state.as_str().to_string(),
                    message: check.message,
                    details: check.details,
                })
                .collect(),
            path_updates: value
                .path_updates
                .into_iter()
                .map(|update| CrashLogScanSetupPathUpdate {
                    kind: update.kind,
                    path: update.path,
                })
                .collect(),
            configuration_issues,
            actions: value
                .actions
                .into_iter()
                .map(|action| action.as_str().to_string())
                .collect(),
            fatal_errors: value.fatal_errors,
            message,
            rendered_report: value.rendered_report,
        }
    }
}

fn scangame_issue_to_scanlog_issue(issue: classic_scangame_core::ConfigIssue) -> ConfigIssue {
    ConfigIssue::new(
        issue.file_path.display().to_string(),
        Some(issue.section),
        issue.setting,
        issue.current_value,
        issue.recommended_value,
        issue.description,
        match issue.severity {
            classic_scangame_core::IssueSeverity::Error => "error",
            classic_scangame_core::IssueSeverity::Warning => "warning",
            classic_scangame_core::IssueSeverity::Info => "info",
        }
        .to_string(),
    )
}

fn cancellation_requested(cancellation: Option<&Arc<AtomicBool>>) -> bool {
    cancellation.is_some_and(|flag| flag.load(Ordering::Acquire))
}

fn resolve_unsolved_logs_destination(
    ready: &ScanReadyAnalysis,
    intent: &CrashLogScanRunIntent,
) -> Result<Option<PathBuf>> {
    match intent {
        CrashLogScanRunIntent::Targeted => Ok(None),
        CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
            unsolved_logs: StandardUnsolvedLogsIntent::LeaveInPlace,
        }) => Ok(None),
        CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
            unsolved_logs: StandardUnsolvedLogsIntent::MoveToCustom(destination),
        }) => {
            if destination.is_absolute() {
                Ok(Some(destination.clone()))
            } else {
                Err(ScanLogError::InvalidInput(format!(
                    "Unsolved Logs Destination must be an absolute path: {}",
                    destination.display()
                )))
            }
        }
        CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
            unsolved_logs: StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
        }) => ready
            .unsolved_logs_destination()
            .map(|destination| Ok(Some(destination.to_path_buf())))
            .unwrap_or_else(|| {
                ready
                    .paths()
                    .map(|paths| Ok(Some(paths.canonical_unsolved_logs_destination())))
                    .unwrap_or_else(|| {
                        Err(ScanLogError::InvalidInput(
                            "Unsolved Logs Destination requires path-backed intake or a custom absolute destination"
                                .to_string(),
                        ))
                    })
            }),
    }
}

/// Complete best-effort movement state for both a Crash Log and its Autoscan Report.
struct UnsolvedLogsFinalization {
    moved_any: bool,
    error: Option<String>,
}

/// Attempts both artifacts and retains partial success if either move fails.
async fn move_unsolved_artifacts(
    log_path: &Path,
    destination_dir: &Path,
    #[cfg(test)] test_hooks: &ScanRunTestHooks,
) -> UnsolvedLogsFinalization {
    let autoscan_path = autoscan_report_path(log_path);
    let mut moved_any = false;
    let mut errors = Vec::new();

    for source in [log_path, autoscan_path.as_path()] {
        #[cfg(test)]
        if let Some(message) = test_hooks.movement_failure() {
            errors.push(message);
            continue;
        }

        match move_file_if_exists(source, destination_dir).await {
            Ok(moved) => {
                moved_any |= moved;
                #[cfg(test)]
                if moved {
                    test_hooks.record_movement_success();
                }
            }
            Err(error) => errors.push(error.to_string()),
        }
    }

    UnsolvedLogsFinalization {
        moved_any,
        error: (!errors.is_empty()).then(|| errors.join("; ")),
    }
}

/// Copies one existing artifact into an atomically claimed destination, syncs it, then deletes
/// the source. Failures remove the incomplete claim on a best-effort basis and retain the source.
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

    let mut source_file = tokio::fs::File::open(source).await?;
    let (destination, mut destination_file) = claim_available_destination(destination).await?;
    if let Err(error) = tokio::io::copy(&mut source_file, &mut destination_file).await {
        drop(destination_file);
        cleanup_incomplete_destination(&destination).await;
        return Err(ScanLogError::IoError(error));
    }
    if let Err(error) = destination_file.sync_all().await {
        drop(destination_file);
        cleanup_incomplete_destination(&destination).await;
        return Err(ScanLogError::IoError(error));
    }
    drop(destination_file);
    drop(source_file);

    if let Err(error) = tokio::fs::remove_file(source).await {
        cleanup_incomplete_destination(&destination).await;
        return Err(ScanLogError::IoError(error));
    }
    Ok(true)
}

/// Atomically reserves the first collision-safe destination without replacing existing data.
async fn claim_available_destination(destination: PathBuf) -> Result<(PathBuf, tokio::fs::File)> {
    let parent = destination.parent().unwrap_or_else(|| Path::new(""));
    let stem = destination
        .file_stem()
        .map(|stem| stem.to_string_lossy())
        .unwrap_or_else(|| "artifact".into());
    let extension = destination
        .extension()
        .map(|extension| extension.to_string_lossy());

    for suffix in 0usize.. {
        let candidate = if suffix == 0 {
            destination.clone()
        } else {
            let candidate_name = match extension.as_ref() {
                Some(extension) if !extension.is_empty() => {
                    format!("{stem}-{suffix}.{extension}")
                }
                _ => format!("{stem}-{suffix}"),
            };
            parent.join(candidate_name)
        };
        match tokio::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&candidate)
            .await
        {
            Ok(file) => return Ok((candidate, file)),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(error) => return Err(ScanLogError::IoError(error)),
        }
    }

    Err(ScanLogError::Internal(format!(
        "Could not find available Unsolved Logs destination for {}",
        destination.display()
    )))
}

/// Removes a destination claim when copying cannot complete, preserving the source artifact.
async fn cleanup_incomplete_destination(destination: &Path) {
    // The originating I/O failure is more useful than a secondary best-effort cleanup error.
    let _ = tokio::fs::remove_file(destination).await;
}

#[cfg(test)]
#[path = "scan_run_test_support.rs"]
mod test_support;

#[cfg(test)]
#[path = "scan_run_tests.rs"]
mod tests;
