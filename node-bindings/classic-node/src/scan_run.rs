//! Final Crash Log Scan Run contract adapter for Node.js and Bun.
//!
//! This module projects invariant-preserving request construction, opaque
//! cancellation, serialized event observation, and exhaustive terminal mapping
//! without recreating any Rust-owned lifecycle behavior.

#[cfg(test)]
#[path = "scan_run_tests.rs"]
mod tests;

use crate::scanlog::JsFcxConfigIssue;
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanFacts,
    CrashLogScanRunStatus, CrashLogScanSetupContext, CrashLogScanSetupResult, ScanProgressPhase,
    StandardCrashLogScanSource, StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
use classic_shared_core::GameId;
use napi::bindgen_prelude::{AsyncTask, Either, FnArgs, Function};
use napi::threadsafe_function::{
    ThreadsafeFunction, ThreadsafeFunctionCallMode, UnknownReturnValue,
};
use napi::{Env, Status, Task};
use std::path::PathBuf;
use std::sync::{Arc, Mutex, mpsc};

/// JavaScript configuration shared by Standard and Targeted requests.
#[napi(object)]
#[derive(Clone)]
pub struct JsScanRunConfiguration {
    /// Root directory containing settings and the ignore YAML document.
    pub yaml_dir_root: String,
    /// `CLASSIC Data` directory containing shippable YAML databases.
    pub yaml_dir_data: String,
    /// Supported game identifier.
    pub game: String,
    /// Selected game-version mode.
    pub game_version: String,
    /// Whether FormID values should be resolved through configured databases.
    pub show_formid_values: bool,
    /// Whether simplify-log preprocessing is enabled.
    pub simplify_logs: bool,
    /// Explicit FormID database paths projected from User Settings.
    pub formid_database_paths: Vec<String>,
    /// Configured Standard-run Unsolved Logs destination, when present.
    pub unsolved_logs_destination: Option<String>,
    /// Explicit concurrency limit. Absence selects adaptively; zero is invalid.
    pub max_concurrent: Option<u32>,
}

/// Standard discovery inputs for one request.
#[napi(object)]
#[derive(Clone)]
pub struct JsScanRunStandardSource {
    /// Primary discovery base directory.
    pub base_directory: String,
    /// Optional custom scan directory.
    pub custom_scan_directory: Option<String>,
    /// Optional configured documents root.
    pub configured_documents_root: Option<String>,
}

/// Targeted discovery inputs for one request.
#[napi(object)]
#[derive(Clone)]
pub struct JsScanRunTargetedSource {
    /// Explicit user-selected candidate paths in caller order.
    pub inputs: Vec<String>,
}

/// Explicit run-scoped FCX setup facts.
#[napi(object)]
#[derive(Clone)]
pub struct JsScanRunSetupContext {
    pub game_root: Option<String>,
    pub docs_root: Option<String>,
    pub game_exe_path: Option<String>,
    pub xse_log_path: Option<String>,
}

/// Opaque Standard-only Unsolved Logs policy.
#[napi]
pub struct ScanRunUnsolvedLogs {
    inner: StandardUnsolvedLogsIntent,
}

#[napi]
impl ScanRunUnsolvedLogs {
    /// Creates a policy that leaves failed artifacts in place.
    #[napi(factory)]
    pub fn leave_in_place() -> Self {
        Self {
            inner: StandardUnsolvedLogsIntent::LeaveInPlace,
        }
    }

    /// Creates a policy that uses the configured or Rust-default destination.
    #[napi(factory)]
    pub fn move_to_configured_or_default() -> Self {
        Self {
            inner: StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
        }
    }

    /// Creates a policy that uses one caller-selected destination.
    #[napi(factory)]
    pub fn move_to_custom(destination: String) -> napi::Result<Self> {
        Ok(Self {
            inner: StandardUnsolvedLogsIntent::MoveToCustom(required_path(
                destination,
                "destination",
            )?),
        })
    }
}

/// Opaque invariant-preserving request for the final scan-run operation.
#[napi]
pub struct ScanRunRequest {
    inner: contract::Request,
}

#[napi]
impl ScanRunRequest {
    /// Constructs a non-FCX Standard request.
    #[napi(factory)]
    pub fn standard(
        configuration: JsScanRunConfiguration,
        source: JsScanRunStandardSource,
        unsolved_logs: &ScanRunUnsolvedLogs,
    ) -> napi::Result<Self> {
        Ok(Self {
            inner: contract::Request::standard(
                configuration_to_core(configuration)?,
                standard_source_to_core(source)?,
                unsolved_logs.inner.clone(),
            ),
        })
    }

    /// Constructs an FCX-enabled Standard request with required setup facts.
    #[napi(factory)]
    pub fn standard_with_fcx(
        configuration: JsScanRunConfiguration,
        source: JsScanRunStandardSource,
        unsolved_logs: &ScanRunUnsolvedLogs,
        setup_context: JsScanRunSetupContext,
    ) -> napi::Result<Self> {
        Ok(Self {
            inner: contract::Request::standard_with_fcx(
                configuration_to_core(configuration)?,
                standard_source_to_core(source)?,
                unsolved_logs.inner.clone(),
                setup_context_to_core(setup_context),
            ),
        })
    }

    /// Constructs a non-FCX Targeted request with no movement capability.
    #[napi(factory)]
    pub fn targeted(
        configuration: JsScanRunConfiguration,
        source: JsScanRunTargetedSource,
    ) -> napi::Result<Self> {
        Ok(Self {
            inner: contract::Request::targeted(
                configuration_to_core(configuration)?,
                targeted_source_to_core(source),
            ),
        })
    }

    /// Constructs an FCX-enabled Targeted request with no movement capability.
    #[napi(factory)]
    pub fn targeted_with_fcx(
        configuration: JsScanRunConfiguration,
        source: JsScanRunTargetedSource,
        setup_context: JsScanRunSetupContext,
    ) -> napi::Result<Self> {
        Ok(Self {
            inner: contract::Request::targeted_with_fcx(
                configuration_to_core(configuration)?,
                targeted_source_to_core(source),
                setup_context_to_core(setup_context),
            ),
        })
    }
}

/// Opaque monotonic cancellation control for one scan run.
#[napi]
pub struct ScanRunCancellation {
    inner: contract::Cancellation,
}

#[napi]
impl ScanRunCancellation {
    /// Creates an uncancelled control.
    #[napi(constructor)]
    pub fn new() -> Self {
        Self {
            inner: contract::Cancellation::new(),
        }
    }

    /// Requests cancellation at the next Rust-owned safe seam.
    #[napi]
    pub fn cancel(&self) {
        self.inner.cancel();
    }

    /// Returns whether cancellation has been requested.
    #[napi(getter)]
    pub fn is_cancelled(&self) -> bool {
        self.inner.is_cancelled()
    }
}

impl Default for ScanRunCancellation {
    fn default() -> Self {
        Self::new()
    }
}

/// JavaScript-compatible Targeted input rejection.
#[napi(object)]
pub struct JsScanRunRejectedInput {
    pub path: String,
    pub reason: String,
}

/// JavaScript-compatible discovery result.
#[napi(object)]
pub struct JsScanRunDiscoveryResult {
    #[napi(ts_type = "'standard' | 'targeted'")]
    pub source: String,
    pub accepted_logs: Vec<String>,
    pub rejected_inputs: Vec<JsScanRunRejectedInput>,
    pub searched_locations: Vec<String>,
}

/// JavaScript-compatible setup check.
#[napi(object)]
pub struct JsScanRunSetupCheck {
    pub kind: String,
    pub state: String,
    pub message: String,
    pub details: Vec<String>,
}

/// JavaScript-compatible setup path update.
#[napi(object)]
pub struct JsScanRunSetupPathUpdate {
    pub kind: String,
    pub path: String,
}

/// JavaScript-compatible run-scoped setup result.
#[napi(object)]
pub struct JsScanRunSetupResult {
    pub status: String,
    pub message: Option<String>,
    pub rendered_report: String,
    pub checks: Vec<JsScanRunSetupCheck>,
    pub path_updates: Vec<JsScanRunSetupPathUpdate>,
    pub configuration_issues: Vec<JsFcxConfigIssue>,
    pub actions: Vec<String>,
    pub fatal_errors: Vec<String>,
}

/// One structured per-log processing or finalization failure.
#[napi(object)]
pub struct JsScanRunLogFailure {
    #[napi(ts_type = "'analysis' | 'report_write' | 'unsolved_logs_finalization'")]
    pub stage: String,
    pub message: String,
}

/// Complete terminal result for one discovered Crash Log.
#[napi(object)]
pub struct JsScanRunLogResult {
    pub discovery_index: u32,
    pub crash_log: String,
    pub autoscan_report: Option<String>,
    #[napi(ts_type = "'succeeded' | 'failed' | 'cancelled_before_start'")]
    pub disposition: String,
    pub failures: Vec<JsScanRunLogFailure>,
    pub message: Option<String>,
    pub moved_to_unsolved_logs: bool,
    pub processing_time_us: i64,
    pub processing_time_ms: i64,
    pub formid_count: u32,
    pub plugin_count: u32,
    pub suspect_count: u32,
}

/// Complete terminal Crash Log Scan Run result.
#[napi(object)]
pub struct JsScanRunResult {
    #[napi(
        ts_type = "'completed' | 'no_crash_logs_found' | 'setup_failed' | 'cancelled_before_discovery' | 'cancelled'"
    )]
    pub status: String,
    pub discovery: Option<JsScanRunDiscoveryResult>,
    pub setup: Option<JsScanRunSetupResult>,
    pub effective_concurrency: Option<u32>,
    pub message: Option<String>,
    pub total: u32,
    pub succeeded: u32,
    pub failed: u32,
    pub cancelled: u32,
    pub logs: Vec<JsScanRunLogResult>,
}

/// Typed run-wide infrastructure failure.
#[napi(object)]
pub struct JsScanRunInfrastructureError {
    #[napi(
        ts_type = "'request_validation' | 'discovery' | 'intake' | 'formid_database_access' | 'initialization' | 'internal_invariant'"
    )]
    pub stage: String,
    pub message: String,
    pub path: Option<String>,
}

/// Common log-scoped event payload.
#[napi(object)]
pub struct JsScanRunLogEvent {
    pub discovery_index: u32,
    pub crash_log: String,
    pub completed: u32,
    pub total: u32,
}

/// One tagged serialized observer event.
#[napi(object)]
pub struct JsScanRunEvent {
    #[napi(
        ts_type = "'discovery_completed' | 'effective_concurrency_selected' | 'log_queued' | 'log_started' | 'log_phase' | 'log_finished'"
    )]
    pub kind: String,
    pub discovery: Option<JsScanRunDiscoveryResult>,
    pub effective_concurrency: Option<u32>,
    pub log: Option<JsScanRunLogEvent>,
    #[napi(ts_type = "'setup' | 'parse' | 'analyze' | 'finalize'")]
    pub phase: Option<String>,
    #[napi(ts_type = "'succeeded' | 'failed' | 'cancelled_before_start'")]
    pub disposition: Option<String>,
}

/// Successful final operation envelope with adapter-only observation failure data.
#[napi(object)]
pub struct JsScanRunSuccess {
    pub result: JsScanRunResult,
    pub observer_error: Option<String>,
}

/// Failed final operation envelope with adapter-only observation failure data.
#[napi(object)]
pub struct JsScanRunFailure {
    pub error: JsScanRunInfrastructureError,
    pub observer_error: Option<String>,
}

/// Internal task output retained until conversion on the JavaScript thread.
pub enum ScanRunTaskOutput {
    Success(Box<JsScanRunSuccess>),
    Failure(JsScanRunFailure),
}

type JsObserverFunction = ThreadsafeFunction<
    JsScanRunEvent,
    UnknownReturnValue,
    FnArgs<(JsScanRunEvent,)>,
    Status,
    false,
    false,
    1,
>;

/// Background task that enters CLASSIC's shared Tokio runtime for execution.
pub struct ScanRunTask {
    request: contract::Request,
    cancellation: contract::Cancellation,
    observer: Option<JsObserverFunction>,
    cancel_on_observer_error: bool,
}

impl Task for ScanRunTask {
    type Output = ScanRunTaskOutput;
    type JsValue = Either<JsScanRunSuccess, JsScanRunFailure>;

    /// Executes the core future without constructing an independent runtime.
    fn compute(&mut self) -> napi::Result<Self::Output> {
        let observer_error = Arc::new(Mutex::new(None));
        let mut adapter = self.observer.take().map(|callback| JsObserverAdapter {
            callback,
            cancellation: self.cancellation.clone(),
            cancel_on_error: self.cancel_on_observer_error,
            delivery_error: Arc::clone(&observer_error),
            delivery_failed: false,
        });
        let result = classic_shared_core::get_runtime().block_on(contract::execute(
            self.request.clone(),
            &self.cancellation,
            adapter
                .as_mut()
                .map(|observer| observer as &mut dyn contract::Observer),
        ));
        let observer_error = observer_error
            .lock()
            .map_err(|_| napi::Error::from_reason("scan-run observer error state was poisoned"))?
            .clone();

        Ok(match result {
            Ok(result) => ScanRunTaskOutput::Success(Box::new(JsScanRunSuccess {
                result: run_result_to_js(result),
                observer_error,
            })),
            Err(error) => ScanRunTaskOutput::Failure(JsScanRunFailure {
                error: infrastructure_error_to_js(error),
                observer_error,
            }),
        })
    }

    /// Resolves the already-converted operation envelope on the JavaScript thread.
    fn resolve(&mut self, _env: Env, output: Self::Output) -> napi::Result<Self::JsValue> {
        Ok(match output {
            ScanRunTaskOutput::Success(result) => Either::A(*result),
            ScanRunTaskOutput::Failure(error) => Either::B(error),
        })
    }
}

/// Executes one final-contract request with optional serialized observation.
///
/// The observer is non-controlling. If it throws or cannot be delivered, the
/// failure is returned only through `observerError`; `cancelOnObserverError`
/// controls whether that adapter failure also uses the separate cancellation
/// control to request safe stopping.
#[napi(ts_return_type = "Promise<JsScanRunSuccess | JsScanRunFailure>")]
pub fn scan_run_execute(
    request: &ScanRunRequest,
    cancellation: &ScanRunCancellation,
    #[napi(
        ts_arg_type = "(event: { kind: 'discovery_completed'; discovery: JsScanRunDiscoveryResult } | { kind: 'effective_concurrency_selected'; effectiveConcurrency: number } | { kind: 'log_queued' | 'log_started'; log: JsScanRunLogEvent } | { kind: 'log_phase'; log: JsScanRunLogEvent; phase: 'setup' | 'parse' | 'analyze' | 'finalize' } | { kind: 'log_finished'; log: JsScanRunLogEvent; disposition: 'succeeded' | 'failed' | 'cancelled_before_start' }) => void"
    )]
    observer: Option<Function<'_, FnArgs<(JsScanRunEvent,)>, UnknownReturnValue>>,
    cancel_on_observer_error: Option<bool>,
) -> napi::Result<AsyncTask<ScanRunTask>> {
    let request = request.inner.clone();
    let cancellation = cancellation.inner.clone();
    let observer = observer
        .map(|observer| {
            observer
                .build_threadsafe_function::<JsScanRunEvent>()
                .max_queue_size::<1>()
                .build_callback(|context| Ok((context.value,).into()))
        })
        .transpose()?;

    Ok(AsyncTask::new(ScanRunTask {
        request,
        cancellation,
        observer,
        cancel_on_observer_error: cancel_on_observer_error.unwrap_or(false),
    }))
}

struct JsObserverAdapter {
    callback: JsObserverFunction,
    cancellation: contract::Cancellation,
    cancel_on_error: bool,
    delivery_error: Arc<Mutex<Option<String>>>,
    delivery_failed: bool,
}

impl JsObserverAdapter {
    /// Records the first adapter delivery failure and optionally requests cancellation.
    fn record_failure(&mut self, message: String) {
        self.delivery_failed = true;
        if let Ok(mut error) = self.delivery_error.lock()
            && error.is_none()
        {
            *error = Some(message);
        }
        if self.cancel_on_error {
            self.cancellation.cancel();
        }
    }
}

impl contract::Observer for JsObserverAdapter {
    /// Delivers one event and waits for the callback result to preserve serialization.
    fn on_event(&mut self, event: contract::Event) {
        if self.delivery_failed {
            return;
        }

        let (sender, receiver) = mpsc::sync_channel(1);
        let status = self.callback.call_with_return_value(
            event_to_js(event),
            ThreadsafeFunctionCallMode::NonBlocking,
            move |result, _env| {
                // The receiver can disappear only when execution is already unwinding.
                let _ = sender.send(result.map(|_| ()).map_err(|error| error.reason.clone()));
                Ok(())
            },
        );
        if status != Status::Ok {
            self.record_failure(format!("observer delivery failed: {status}"));
            return;
        }

        match receiver.recv() {
            Ok(Ok(())) => {}
            Ok(Err(error)) => self.record_failure(error),
            Err(error) => self.record_failure(format!("observer delivery failed: {error}")),
        }
    }
}

/// Converts shared JavaScript configuration into the final core configuration.
fn configuration_to_core(value: JsScanRunConfiguration) -> napi::Result<contract::Configuration> {
    let game = value
        .game
        .parse::<GameId>()
        .map_err(|error| napi::Error::new(Status::InvalidArg, error.to_string()))?;

    Ok(contract::Configuration {
        yaml_dir_root: required_path(value.yaml_dir_root, "yamlDirRoot")?,
        yaml_dir_data: required_path(value.yaml_dir_data, "yamlDirData")?,
        game,
        game_version: value.game_version,
        options: contract::Options::new(value.show_formid_values, value.simplify_logs),
        scan_facts: CrashLogScanFacts {
            formid_database_paths: value
                .formid_database_paths
                .into_iter()
                .map(PathBuf::from)
                .collect(),
            unsolved_logs_destination: value.unsolved_logs_destination.map(PathBuf::from),
        },
        max_concurrent: value.max_concurrent.map(|value| value as usize),
    })
}

/// Converts Standard discovery inputs without adding policy.
fn standard_source_to_core(
    value: JsScanRunStandardSource,
) -> napi::Result<StandardCrashLogScanSource> {
    Ok(StandardCrashLogScanSource {
        base_directory: required_path(value.base_directory, "baseDirectory")?,
        custom_scan_directory: value.custom_scan_directory.map(PathBuf::from),
        configured_documents_root: value.configured_documents_root.map(PathBuf::from),
    })
}

/// Converts Targeted discovery inputs in caller order.
fn targeted_source_to_core(value: JsScanRunTargetedSource) -> TargetedCrashLogScanSource {
    TargetedCrashLogScanSource {
        inputs: value.inputs.into_iter().map(PathBuf::from).collect(),
    }
}

/// Converts explicit FCX setup facts without process-global state.
fn setup_context_to_core(value: JsScanRunSetupContext) -> CrashLogScanSetupContext {
    CrashLogScanSetupContext {
        game_root: value.game_root.map(PathBuf::from),
        docs_root: value.docs_root.map(PathBuf::from),
        game_exe_path: value.game_exe_path.map(PathBuf::from),
        xse_log_path: value.xse_log_path.map(PathBuf::from),
    }
}

fn required_path(value: String, label: &str) -> napi::Result<PathBuf> {
    if value.trim().is_empty() {
        return Err(napi::Error::new(
            Status::InvalidArg,
            format!("{label} must not be blank"),
        ));
    }
    Ok(PathBuf::from(value))
}

fn path_to_string(path: PathBuf) -> String {
    path.to_string_lossy().into_owned()
}

fn usize_to_u32(value: usize) -> u32 {
    u32::try_from(value).unwrap_or(u32::MAX)
}

fn u64_to_i64(value: u64) -> i64 {
    i64::try_from(value).unwrap_or(i64::MAX)
}

/// Maps discovery while preserving all accepted, rejected, and searched paths.
fn discovery_to_js(value: CrashLogScanDiscoveryResult) -> JsScanRunDiscoveryResult {
    let source = match value.source {
        CrashLogScanDiscoverySource::Standard => "standard",
        CrashLogScanDiscoverySource::Targeted => "targeted",
    };
    JsScanRunDiscoveryResult {
        source: source.to_string(),
        accepted_logs: value
            .accepted_logs
            .into_iter()
            .map(path_to_string)
            .collect(),
        rejected_inputs: value
            .rejected_inputs
            .into_iter()
            .map(|rejected| JsScanRunRejectedInput {
                path: path_to_string(rejected.path),
                reason: rejected.reason,
            })
            .collect(),
        searched_locations: value
            .searched_locations
            .into_iter()
            .map(path_to_string)
            .collect(),
    }
}

/// Maps run-scoped setup data with optional fields intact.
fn setup_to_js(value: CrashLogScanSetupResult) -> JsScanRunSetupResult {
    JsScanRunSetupResult {
        status: value.status,
        message: value.message,
        rendered_report: value.rendered_report,
        checks: value
            .checks
            .into_iter()
            .map(|check| JsScanRunSetupCheck {
                kind: check.kind,
                state: check.state,
                message: check.message,
                details: check.details,
            })
            .collect(),
        path_updates: value
            .path_updates
            .into_iter()
            .map(|update| JsScanRunSetupPathUpdate {
                kind: update.kind,
                path: path_to_string(update.path),
            })
            .collect(),
        configuration_issues: value
            .configuration_issues
            .iter()
            .map(JsFcxConfigIssue::from)
            .collect(),
        actions: value.actions,
        fatal_errors: value.fatal_errors,
    }
}

/// Maps one complete terminal log result without collapsing structured failures.
fn log_result_to_js(value: contract::LogResult) -> JsScanRunLogResult {
    JsScanRunLogResult {
        discovery_index: usize_to_u32(value.discovery_index),
        crash_log: path_to_string(value.crash_log),
        autoscan_report: value.autoscan_report.map(path_to_string),
        disposition: value.disposition.as_str().to_string(),
        failures: value
            .failures
            .into_iter()
            .map(|failure| JsScanRunLogFailure {
                stage: failure.stage.as_str().to_string(),
                message: failure.message,
            })
            .collect(),
        message: value.message,
        moved_to_unsolved_logs: value.moved_to_unsolved_logs,
        processing_time_us: u64_to_i64(value.processing_time_us),
        processing_time_ms: u64_to_i64(value.processing_time_ms),
        formid_count: usize_to_u32(value.formid_count),
        plugin_count: usize_to_u32(value.plugin_count),
        suspect_count: usize_to_u32(value.suspect_count),
    }
}

/// Maps the complete terminal result including Rust-selected concurrency.
fn run_result_to_js(value: contract::RunResult) -> JsScanRunResult {
    JsScanRunResult {
        status: match value.status {
            CrashLogScanRunStatus::Completed => "completed",
            CrashLogScanRunStatus::NoCrashLogsFound => "no_crash_logs_found",
            CrashLogScanRunStatus::SetupFailed => "setup_failed",
            CrashLogScanRunStatus::CancelledBeforeDiscovery => "cancelled_before_discovery",
            CrashLogScanRunStatus::Cancelled => "cancelled",
        }
        .to_string(),
        discovery: value.discovery.map(discovery_to_js),
        setup: value.setup.map(setup_to_js),
        effective_concurrency: value.effective_concurrency.map(usize_to_u32),
        message: value.message,
        total: usize_to_u32(value.total),
        succeeded: usize_to_u32(value.succeeded),
        failed: usize_to_u32(value.failed),
        cancelled: usize_to_u32(value.cancelled),
        logs: value.logs.into_iter().map(log_result_to_js).collect(),
    }
}

/// Maps every typed run-wide error field, including its optional path.
fn infrastructure_error_to_js(
    value: contract::InfrastructureError,
) -> JsScanRunInfrastructureError {
    let stage = match value.stage {
        contract::InfrastructureErrorStage::RequestValidation => "request_validation",
        contract::InfrastructureErrorStage::Discovery => "discovery",
        contract::InfrastructureErrorStage::Intake => "intake",
        contract::InfrastructureErrorStage::FormIdDatabaseAccess => "formid_database_access",
        contract::InfrastructureErrorStage::Initialization => "initialization",
        contract::InfrastructureErrorStage::InternalInvariant => "internal_invariant",
    };
    JsScanRunInfrastructureError {
        stage: stage.to_string(),
        message: value.message,
        path: value.path.map(path_to_string),
    }
}

fn phase_to_string(value: ScanProgressPhase) -> String {
    match value {
        ScanProgressPhase::Setup => "setup",
        ScanProgressPhase::Parse => "parse",
        ScanProgressPhase::Analyze => "analyze",
        ScanProgressPhase::Finalize => "finalize",
    }
    .to_string()
}

fn log_event_to_js(value: contract::LogEvent) -> JsScanRunLogEvent {
    JsScanRunLogEvent {
        discovery_index: usize_to_u32(value.discovery_index),
        crash_log: path_to_string(value.crash_log),
        completed: usize_to_u32(value.completed),
        total: usize_to_u32(value.total),
    }
}

/// Maps every event variant into one stable tagged JavaScript shape.
fn event_to_js(value: contract::Event) -> JsScanRunEvent {
    match value {
        contract::Event::DiscoveryCompleted(discovery) => JsScanRunEvent {
            kind: "discovery_completed".to_string(),
            discovery: Some(discovery_to_js(discovery)),
            effective_concurrency: None,
            log: None,
            phase: None,
            disposition: None,
        },
        contract::Event::EffectiveConcurrencySelected {
            effective_concurrency,
        } => JsScanRunEvent {
            kind: "effective_concurrency_selected".to_string(),
            discovery: None,
            effective_concurrency: Some(usize_to_u32(effective_concurrency)),
            log: None,
            phase: None,
            disposition: None,
        },
        contract::Event::LogQueued(log) => JsScanRunEvent {
            kind: "log_queued".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_js(log)),
            phase: None,
            disposition: None,
        },
        contract::Event::LogStarted(log) => JsScanRunEvent {
            kind: "log_started".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_js(log)),
            phase: None,
            disposition: None,
        },
        contract::Event::LogPhase { log, phase } => JsScanRunEvent {
            kind: "log_phase".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_js(log)),
            phase: Some(phase_to_string(phase)),
            disposition: None,
        },
        contract::Event::LogFinished { log, disposition } => JsScanRunEvent {
            kind: "log_finished".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_js(log)),
            phase: None,
            disposition: Some(disposition.as_str().to_string()),
        },
    }
}
