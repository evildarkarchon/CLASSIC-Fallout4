//! Final language-neutral Crash Log Scan Run contract.
//!
//! [`execute`] is the only public execution operation for a complete Crash Log
//! Scan Run. Discovery, setup, scheduling, durable finalization, cancellation,
//! events, results, and typed infrastructure failures cross this boundary.

#[cfg(test)]
#[path = "contract_tests.rs"]
mod tests;

use super::{
    CrashLogScanDiscoveryResult, CrashLogScanOutcome, CrashLogScanRunEvent as EngineEvent,
    CrashLogScanRunEventKind as EngineEventKind, CrashLogScanRunLogOutcome as EngineLogOutcome,
    CrashLogScanRunResult as EngineRunResult, CrashLogScanRunServiceError,
    CrashLogScanRunServiceEvent, CrashLogScanRunServiceRequest, CrashLogScanSetupContext,
    CrashLogScanSetupResult, CrashLogScanSource, StandardCrashLogScanSource,
    StandardUnsolvedLogsIntent, TargetedCrashLogScanSource, execute_service,
};
use crate::{CrashLogScanFacts, CrashLogScanOptions, ScanProgressPhase};
use classic_shared_core::GameId;
use std::fmt;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

#[cfg(test)]
use super::test_support::{InfrastructureFault, ScanRunTestHooks};

/// Analysis flags that are valid with or without FCX Mode.
///
/// FCX Mode is deliberately absent. Callers select it only through the
/// `*_with_fcx` request constructors, which require setup context.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct Options {
    /// Whether FormID values should be looked up through configured databases.
    pub show_formid_values: bool,
    /// Whether simplify-log removal is enabled during preprocessing.
    pub simplify_logs: bool,
}

impl Options {
    /// Creates analysis options that cannot independently enable FCX Mode.
    #[must_use]
    pub const fn new(show_formid_values: bool, simplify_logs: bool) -> Self {
        Self {
            show_formid_values,
            simplify_logs,
        }
    }
}

/// Configuration shared by Standard and Targeted Crash Log Scan Runs.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Configuration {
    /// Root directory containing settings and ignore YAML.
    pub yaml_dir_root: PathBuf,
    /// `CLASSIC Data` directory containing shippable YAML databases.
    pub yaml_dir_data: PathBuf,
    /// Supported game identifier.
    pub game: GameId,
    /// Selected game-version mode.
    pub game_version: String,
    /// Analysis flags that do not encode FCX state.
    pub options: Options,
    /// Typed User Settings facts projected by the caller.
    pub scan_facts: CrashLogScanFacts,
    /// Optional explicit concurrency limit. `None` selects adaptively.
    pub max_concurrent: Option<usize>,
}

#[derive(Clone, Debug)]
enum SetupMode {
    Disabled,
    Fcx(CrashLogScanSetupContext),
}

impl SetupMode {
    const fn enabled(&self) -> bool {
        matches!(self, Self::Fcx(_))
    }

    const fn context(&self) -> Option<&CrashLogScanSetupContext> {
        match self {
            Self::Disabled => None,
            Self::Fcx(context) => Some(context),
        }
    }
}

/// Standard Crash Log Scan Run request data.
#[derive(Clone, Debug)]
pub struct StandardRequest {
    configuration: Configuration,
    source: StandardCrashLogScanSource,
    setup: SetupMode,
    unsolved_logs: StandardUnsolvedLogsIntent,
}

impl StandardRequest {
    /// Returns the shared run configuration.
    #[must_use]
    pub const fn configuration(&self) -> &Configuration {
        &self.configuration
    }

    /// Returns the Standard discovery source.
    #[must_use]
    pub const fn source(&self) -> &StandardCrashLogScanSource {
        &self.source
    }

    /// Returns whether this request enables FCX Mode.
    #[must_use]
    pub const fn fcx_enabled(&self) -> bool {
        self.setup.enabled()
    }

    /// Returns the setup context required by an FCX request.
    #[must_use]
    pub const fn setup_context(&self) -> Option<&CrashLogScanSetupContext> {
        self.setup.context()
    }

    /// Returns the Standard-only Unsolved Logs intent.
    #[must_use]
    pub const fn unsolved_logs(&self) -> &StandardUnsolvedLogsIntent {
        &self.unsolved_logs
    }
}

/// Targeted Crash Log Scan Run request data.
///
/// This type has no Unsolved Logs field, so relocation cannot be expressed for
/// a Targeted run.
#[derive(Clone, Debug)]
pub struct TargetedRequest {
    configuration: Configuration,
    source: TargetedCrashLogScanSource,
    setup: SetupMode,
}

impl TargetedRequest {
    /// Returns the shared run configuration.
    #[must_use]
    pub const fn configuration(&self) -> &Configuration {
        &self.configuration
    }

    /// Returns the Targeted discovery source.
    #[must_use]
    pub const fn source(&self) -> &TargetedCrashLogScanSource {
        &self.source
    }

    /// Returns whether this request enables FCX Mode.
    #[must_use]
    pub const fn fcx_enabled(&self) -> bool {
        self.setup.enabled()
    }

    /// Returns the setup context required by an FCX request.
    #[must_use]
    pub const fn setup_context(&self) -> Option<&CrashLogScanSetupContext> {
        self.setup.context()
    }
}

/// Tagged request accepted by the final Crash Log Scan Run operation.
///
/// The constructor signatures are the construction policy. A Targeted request
/// has no movement argument, and every FCX constructor requires
/// [`CrashLogScanSetupContext`].
///
/// ```compile_fail
/// # use classic_scanlog_core::scan_run::contract::{Configuration, Request};
/// # use classic_scanlog_core::{StandardUnsolvedLogsIntent, TargetedCrashLogScanSource};
/// # let configuration: Configuration = unimplemented!();
/// # let source: TargetedCrashLogScanSource = unimplemented!();
/// Request::targeted(
///     configuration,
///     source,
///     StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
/// );
/// ```
///
/// ```compile_fail
/// # use classic_scanlog_core::scan_run::contract::{Configuration, Request};
/// # use classic_scanlog_core::{StandardCrashLogScanSource, StandardUnsolvedLogsIntent};
/// # let configuration: Configuration = unimplemented!();
/// # let source: StandardCrashLogScanSource = unimplemented!();
/// Request::standard_with_fcx(
///     configuration,
///     source,
///     StandardUnsolvedLogsIntent::LeaveInPlace,
/// );
/// ```
///
/// ```compile_fail
/// # use classic_scanlog_core::scan_run::contract::{Configuration, Request};
/// # use classic_scanlog_core::TargetedCrashLogScanSource;
/// # let configuration: Configuration = unimplemented!();
/// # let source: TargetedCrashLogScanSource = unimplemented!();
/// Request::targeted_with_fcx(configuration, source);
/// ```
///
/// ```compile_fail
/// # use classic_scanlog_core::scan_run::contract::{Configuration, Request};
/// # use classic_scanlog_core::{CrashLogScanSetupContext, StandardUnsolvedLogsIntent, TargetedCrashLogScanSource};
/// # let configuration: Configuration = unimplemented!();
/// # let source: TargetedCrashLogScanSource = unimplemented!();
/// # let setup_context: CrashLogScanSetupContext = unimplemented!();
/// Request::targeted_with_fcx(
///     configuration,
///     source,
///     setup_context,
///     StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
/// );
/// ```
#[derive(Clone, Debug)]
pub enum Request {
    /// Standard discovery with Standard-only Unsolved Logs policy.
    Standard(StandardRequest),
    /// Explicit Targeted discovery without any relocation capability.
    Targeted(TargetedRequest),
}

impl Request {
    /// Creates a Standard request with FCX Mode disabled.
    #[must_use]
    pub fn standard(
        configuration: Configuration,
        source: StandardCrashLogScanSource,
        unsolved_logs: StandardUnsolvedLogsIntent,
    ) -> Self {
        Self::Standard(StandardRequest {
            configuration,
            source,
            setup: SetupMode::Disabled,
            unsolved_logs,
        })
    }

    /// Creates a Standard request with FCX Mode and its required setup context.
    #[must_use]
    pub fn standard_with_fcx(
        configuration: Configuration,
        source: StandardCrashLogScanSource,
        unsolved_logs: StandardUnsolvedLogsIntent,
        setup_context: CrashLogScanSetupContext,
    ) -> Self {
        Self::Standard(StandardRequest {
            configuration,
            source,
            setup: SetupMode::Fcx(setup_context),
            unsolved_logs,
        })
    }

    /// Creates a Targeted request with FCX Mode disabled.
    #[must_use]
    pub fn targeted(configuration: Configuration, source: TargetedCrashLogScanSource) -> Self {
        Self::Targeted(TargetedRequest {
            configuration,
            source,
            setup: SetupMode::Disabled,
        })
    }

    /// Creates a Targeted request with FCX Mode and its required setup context.
    #[must_use]
    pub fn targeted_with_fcx(
        configuration: Configuration,
        source: TargetedCrashLogScanSource,
        setup_context: CrashLogScanSetupContext,
    ) -> Self {
        Self::Targeted(TargetedRequest {
            configuration,
            source,
            setup: SetupMode::Fcx(setup_context),
        })
    }

    /// Returns the shared configuration regardless of the request tag.
    #[must_use]
    pub const fn configuration(&self) -> &Configuration {
        match self {
            Self::Standard(request) => request.configuration(),
            Self::Targeted(request) => request.configuration(),
        }
    }

    /// Projects the invariant-preserving request into the crate-private engine shape.
    fn into_engine_request(self, cancellation: &Cancellation) -> CrashLogScanRunServiceRequest {
        let (configuration, source, setup, move_unsolved_logs, custom_destination) = match self {
            Self::Standard(request) => {
                let (move_unsolved_logs, custom_destination) = match request.unsolved_logs {
                    StandardUnsolvedLogsIntent::LeaveInPlace => (false, None),
                    StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault => (true, None),
                    StandardUnsolvedLogsIntent::MoveToCustom(path) => (true, Some(path)),
                };
                (
                    request.configuration,
                    CrashLogScanSource::Standard(request.source),
                    request.setup,
                    move_unsolved_logs,
                    custom_destination,
                )
            }
            Self::Targeted(request) => (
                request.configuration,
                CrashLogScanSource::Targeted(request.source),
                request.setup,
                false,
                None,
            ),
        };

        let fcx_mode = setup.enabled();
        let setup_context = match setup {
            SetupMode::Disabled => None,
            SetupMode::Fcx(context) => Some(context),
        };
        let mut scan_facts = configuration.scan_facts;
        if let Some(destination) = custom_destination {
            scan_facts.unsolved_logs_destination = Some(destination);
        }

        CrashLogScanRunServiceRequest {
            yaml_dir_root: configuration.yaml_dir_root,
            yaml_dir_data: configuration.yaml_dir_data,
            game: configuration.game.as_str().to_string(),
            game_version: configuration.game_version,
            options: CrashLogScanOptions::new(
                configuration.options.show_formid_values,
                fcx_mode,
                configuration.options.simplify_logs,
            ),
            source,
            setup_context,
            move_unsolved_logs,
            scan_facts,
            max_concurrent: configuration.max_concurrent,
            cancellation: Some(cancellation.engine_flag()),
            // Discovery order is mandatory in the final result contract.
            preserve_order: true,
            #[cfg(test)]
            test_hooks: ScanRunTestHooks::default(),
        }
    }
}

/// Opaque cooperative cancellation control for one Crash Log Scan Run.
#[derive(Clone, Default)]
pub struct Cancellation {
    requested: Arc<AtomicBool>,
}

impl fmt::Debug for Cancellation {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("Cancellation")
            .field("is_cancelled", &self.is_cancelled())
            .finish_non_exhaustive()
    }
}

impl Cancellation {
    /// Creates an uncancelled control.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Requests cancellation at the next safe execution seam.
    pub fn cancel(&self) {
        self.requested.store(true, Ordering::Release);
    }

    /// Returns whether cancellation has been requested.
    #[must_use]
    pub fn is_cancelled(&self) -> bool {
        self.requested.load(Ordering::Acquire)
    }

    fn engine_flag(&self) -> Arc<AtomicBool> {
        Arc::clone(&self.requested)
    }
}

/// One log-scoped lifecycle event payload.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LogEvent {
    /// Stable index in Crash Log discovery order.
    pub discovery_index: usize,
    /// Crash Log associated with this event.
    pub crash_log: PathBuf,
    /// Number of logs finished when this event was observed.
    pub completed: usize,
    /// Total accepted Crash Logs.
    pub total: usize,
}

/// Stable lifecycle events emitted by the final operation.
#[derive(Clone, Debug)]
pub enum Event {
    /// Discovery completed with a complete, retainable result.
    DiscoveryCompleted(CrashLogScanDiscoveryResult),
    /// Rust selected the concurrency used by this run.
    EffectiveConcurrencySelected {
        /// Number of Crash Logs Rust will admit concurrently.
        effective_concurrency: usize,
    },
    /// A discovered Crash Log entered the execution queue.
    LogQueued(LogEvent),
    /// A queued Crash Log was admitted for processing.
    LogStarted(LogEvent),
    /// An admitted Crash Log entered a coarse analysis phase.
    LogPhase {
        /// Common log event facts.
        log: LogEvent,
        /// Current coarse phase.
        phase: ScanProgressPhase,
    },
    /// A Crash Log reached its terminal durable disposition.
    LogFinished {
        /// Common log event facts.
        log: LogEvent,
        /// Terminal disposition after finalization.
        disposition: LogDisposition,
    },
}

/// Non-controlling observer for serialized Crash Log Scan Run events.
pub trait Observer: Send {
    /// Observes one event. Implementations request stopping through
    /// [`Cancellation`] rather than by returning control data here.
    fn on_event(&mut self, event: Event);
}

impl<F> Observer for F
where
    F: FnMut(Event) + Send,
{
    fn on_event(&mut self, event: Event) {
        self(event);
    }
}

/// Terminal per-log disposition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LogDisposition {
    /// Analysis and required durable finalization succeeded.
    Succeeded,
    /// One or more structured processing or finalization failures occurred.
    Failed,
    /// Cancellation prevented this discovered Crash Log from starting.
    CancelledBeforeStart,
}

impl LogDisposition {
    /// Returns the stable adapter-facing disposition identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Succeeded => "succeeded",
            Self::Failed => "failed",
            Self::CancelledBeforeStart => "cancelled_before_start",
        }
    }
}

/// Stable stage for one structured per-log failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LogFailureStage {
    /// Crash Log analysis failed.
    Analysis,
    /// Autoscan Report persistence failed.
    ReportWrite,
    /// Requested Unsolved Logs finalization failed.
    UnsolvedLogsFinalization,
}

impl LogFailureStage {
    /// Returns the stable adapter-facing per-log failure stage identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Analysis => "analysis",
            Self::ReportWrite => "report_write",
            Self::UnsolvedLogsFinalization => "unsolved_logs_finalization",
        }
    }
}

/// One structured processing or durable-finalization failure for a Crash Log.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LogFailure {
    /// Stable failure stage.
    pub stage: LogFailureStage,
    /// Human-readable diagnostic for this stage.
    pub message: String,
}

/// Final result for one discovered Crash Log.
#[derive(Clone, Debug)]
pub struct LogResult {
    /// Stable index in Crash Log discovery order.
    pub discovery_index: usize,
    /// Crash Log path.
    pub crash_log: PathBuf,
    /// Autoscan Report path when persistence succeeded.
    pub autoscan_report: Option<PathBuf>,
    /// Typed terminal disposition.
    pub disposition: LogDisposition,
    /// Structured failures preserved independently by stage.
    pub failures: Vec<LogFailure>,
    /// Human-readable failure detail when applicable.
    pub message: Option<String>,
    /// Whether any artifact moved to Unsolved Logs.
    pub moved_to_unsolved_logs: bool,
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

impl From<EngineLogOutcome> for LogResult {
    fn from(value: EngineLogOutcome) -> Self {
        let EngineLogOutcome {
            input_index,
            crash_log,
            autoscan_report,
            outcome,
            moved_to_unsolved_logs,
            analysis_error,
            report_write_error,
            unsolved_logs_finalization_error,
            error,
            processing_time_us,
            processing_time_ms,
            formid_count,
            plugin_count,
            suspect_count,
        } = value;
        let disposition = match outcome {
            CrashLogScanOutcome::Succeeded => LogDisposition::Succeeded,
            CrashLogScanOutcome::Failed => LogDisposition::Failed,
            CrashLogScanOutcome::CancelledBeforeStart => LogDisposition::CancelledBeforeStart,
        };
        let failures = [
            analysis_error.map(|message| LogFailure {
                stage: LogFailureStage::Analysis,
                message,
            }),
            report_write_error.map(|message| LogFailure {
                stage: LogFailureStage::ReportWrite,
                message,
            }),
            unsolved_logs_finalization_error.map(|message| LogFailure {
                stage: LogFailureStage::UnsolvedLogsFinalization,
                message,
            }),
        ]
        .into_iter()
        .flatten()
        .collect();

        Self {
            discovery_index: input_index,
            crash_log,
            autoscan_report,
            disposition,
            failures,
            message: error,
            moved_to_unsolved_logs,
            processing_time_us,
            processing_time_ms,
            formid_count,
            plugin_count,
            suspect_count,
        }
    }
}

/// Stable lifecycle status used by [`RunResult`].
pub use super::CrashLogScanRunStatus as RunStatus;

/// Terminal result of the final Crash Log Scan Run operation.
#[derive(Clone, Debug)]
pub struct RunResult {
    /// Expected lifecycle status for the run as a whole.
    pub status: RunStatus,
    /// Completed discovery data, absent only when discovery did not complete.
    pub discovery: Option<CrashLogScanDiscoveryResult>,
    /// FCX setup data when FCX Mode was enabled.
    pub setup: Option<CrashLogScanSetupResult>,
    /// Rust-selected concurrency, once scheduling was reached.
    pub effective_concurrency: Option<usize>,
    /// Optional concise run-level message.
    pub message: Option<String>,
    /// Total discovered Crash Logs.
    pub total: usize,
    /// Number of successful Crash Logs.
    pub succeeded: usize,
    /// Number of failed Crash Logs.
    pub failed: usize,
    /// Number of discovered Crash Logs cancelled before start.
    pub cancelled: usize,
    /// Per-log results in discovery order.
    pub logs: Vec<LogResult>,
}

/// Stable stage for a run-wide infrastructure failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InfrastructureErrorStage {
    /// The request could not be validated.
    RequestValidation,
    /// Crash Log discovery could not complete.
    Discovery,
    /// Crash Log Scan Intake could not complete.
    Intake,
    /// A required FormID database could not be accessed.
    FormIdDatabaseAccess,
    /// Analysis infrastructure could not initialize or shut down.
    Initialization,
    /// A core invariant was violated.
    InternalInvariant,
}

impl InfrastructureErrorStage {
    /// Returns the stable adapter-facing stage identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::RequestValidation => "request_validation",
            Self::Discovery => "discovery",
            Self::Intake => "intake",
            Self::FormIdDatabaseAccess => "formid_database_access",
            Self::Initialization => "initialization",
            Self::InternalInvariant => "internal_invariant",
        }
    }
}

impl fmt::Display for InfrastructureErrorStage {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

/// Run-wide failure that prevents a meaningful terminal [`RunResult`].
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InfrastructureError {
    /// Stable failure stage.
    pub stage: InfrastructureErrorStage,
    /// Human-readable diagnostic.
    pub message: String,
    /// Relevant path when one can be identified safely.
    pub path: Option<PathBuf>,
}

impl InfrastructureError {
    fn request_validation(message: impl Into<String>, path: Option<PathBuf>) -> Self {
        Self {
            stage: InfrastructureErrorStage::RequestValidation,
            message: message.into(),
            path,
        }
    }

    /// Preserves the exact stage and path captured at the failing lifecycle boundary.
    fn from_service(error: CrashLogScanRunServiceError) -> Self {
        Self {
            stage: error.stage,
            message: error.message,
            path: error.path,
        }
    }
}

impl fmt::Display for InfrastructureError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.stage, self.message)
    }
}

impl std::error::Error for InfrastructureError {}

/// Executes one Standard or Targeted Crash Log Scan Run.
///
/// Cancellation and observation are deliberately separate from [`Request`].
/// Passing `None` for `observer` cannot change scheduling or result semantics.
/// The operation is async and relies on its caller to enter CLASSIC's shared
/// Tokio runtime; it never creates or owns a runtime.
///
/// # Errors
///
/// Returns a typed [`InfrastructureError`] when the run cannot produce a
/// meaningful terminal result. Expected lifecycle states remain in [`RunResult`].
pub async fn execute(
    request: Request,
    cancellation: &Cancellation,
    observer: Option<&mut dyn Observer>,
) -> Result<RunResult, InfrastructureError> {
    execute_inner(
        request,
        cancellation,
        observer,
        #[cfg(test)]
        ScanRunTestHooks::default(),
    )
    .await
}

#[cfg(test)]
/// Executes through the public contract with request-scoped deterministic test controls.
pub(crate) async fn execute_with_test_hooks(
    request: Request,
    cancellation: &Cancellation,
    observer: Option<&mut dyn Observer>,
    test_hooks: ScanRunTestHooks,
) -> Result<RunResult, InfrastructureError> {
    execute_inner(request, cancellation, observer, test_hooks).await
}

/// Shared implementation for the public operation and its request-scoped test harness.
async fn execute_inner(
    request: Request,
    cancellation: &Cancellation,
    mut observer: Option<&mut dyn Observer>,
    #[cfg(test)] test_hooks: ScanRunTestHooks,
) -> Result<RunResult, InfrastructureError> {
    #[cfg(test)]
    if let Some(error) = test_hooks.infrastructure_failure(InfrastructureFault::RequestValidation) {
        return Err(InfrastructureError::request_validation(
            error.to_string(),
            None,
        ));
    }

    let max_concurrent = request.configuration().max_concurrent;
    if max_concurrent == Some(0) {
        return Err(InfrastructureError::request_validation(
            "max_concurrent must be greater than zero when supplied",
            None,
        ));
    }

    let engine_request = request.into_engine_request(cancellation);
    #[cfg(test)]
    let engine_request = {
        let mut engine_request = engine_request;
        engine_request.test_hooks = test_hooks;
        engine_request
    };
    let mut effective_concurrency = None;
    let engine_result = execute_service(engine_request, |event| match event {
        CrashLogScanRunServiceEvent::DiscoveryCompleted(discovery) => {
            emit(&mut observer, Event::DiscoveryCompleted(discovery));
        }
        CrashLogScanRunServiceEvent::EffectiveConcurrencySelected(value) => {
            effective_concurrency = Some(value);
            emit(
                &mut observer,
                Event::EffectiveConcurrencySelected {
                    effective_concurrency: value,
                },
            );
        }
        CrashLogScanRunServiceEvent::Log(event) => {
            if let Some(event) = translate_engine_event(event) {
                emit(&mut observer, event);
            }
        }
    })
    .await
    .map_err(InfrastructureError::from_service)?;

    let EngineRunResult {
        status,
        discovery,
        setup,
        message,
        total,
        succeeded,
        failed,
        cancelled,
        logs,
    } = engine_result;
    let logs: Vec<LogResult> = logs.into_iter().map(LogResult::from).collect();

    Ok(RunResult {
        status,
        discovery,
        setup,
        effective_concurrency,
        message,
        total,
        succeeded,
        failed,
        cancelled,
        logs,
    })
}

fn emit(observer: &mut Option<&mut dyn Observer>, event: Event) {
    if let Some(observer) = observer.as_deref_mut() {
        observer.on_event(event);
    }
}

fn translate_engine_event(event: EngineEvent) -> Option<Event> {
    let disposition = event.disposition;
    let log = LogEvent {
        discovery_index: event.input_index,
        crash_log: event.crash_log,
        completed: event.completed,
        total: event.total,
    };
    match event.kind {
        EngineEventKind::Queued => Some(Event::LogQueued(log)),
        EngineEventKind::Started => Some(Event::LogStarted(log)),
        EngineEventKind::Phase => Some(Event::LogPhase {
            log,
            phase: event.phase,
        }),
        EngineEventKind::Completed | EngineEventKind::Failed => {
            disposition.map(|disposition| Event::LogFinished { log, disposition })
        }
    }
}
