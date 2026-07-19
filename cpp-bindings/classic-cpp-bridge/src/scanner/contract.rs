use crate::runtime_support::block_on;
use classic_config_core::{
    InspectedYamlDataFile, InstalledYamlDataProvenance, InstalledYamlDataRole,
    YamlDataContentIdentity,
};
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::{
    ConfigIssue as CoreFcxConfigIssue, CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource,
    CrashLogScanFacts, CrashLogScanRunStatus, CrashLogScanSetupContext, CrashLogScanSetupResult,
    ScanProgressPhase, StandardCrashLogScanSource, StandardUnsolvedLogsIntent,
    TargetedCrashLogScanSource,
};
use classic_shared_core::GameId;
use std::path::PathBuf;

use super::ffi;

/// Opaque invariant-preserving request for the final Crash Log Scan Run contract.
pub(crate) struct ScanRunRequest {
    inner: contract::Request,
}

/// Opaque Standard-only Unsolved Logs intent.
pub(crate) struct ScanRunUnsolvedLogs {
    inner: classic_scanlog_core::StandardUnsolvedLogsIntent,
}

/// Opaque cooperative cancellation control for the final contract.
pub(crate) struct ScanRunCancellation {
    inner: contract::Cancellation,
}

/// Opaque execution operation that owns a DTO envelope and optional recovery continuation.
pub(crate) struct ScanRunContractExecution {
    result: ffi::ScanRunContractExecutionResult,
    continuation: Option<ScanRunContinuation>,
}

/// Process-local, non-cloneable carrier for one retained Local Ignore recovery.
pub(crate) struct ScanRunContinuation {
    inner: contract::CrashLogScanRunContinuation,
}

/// Creates Standard intent that leaves failed Crash Logs and reports in place.
pub(crate) fn scan_run_unsolved_logs_leave_in_place() -> Box<ScanRunUnsolvedLogs> {
    Box::new(ScanRunUnsolvedLogs {
        inner: StandardUnsolvedLogsIntent::LeaveInPlace,
    })
}

/// Creates Standard intent that moves eligible artifacts to the configured or default destination.
pub(crate) fn scan_run_unsolved_logs_move_to_configured_or_default() -> Box<ScanRunUnsolvedLogs> {
    Box::new(ScanRunUnsolvedLogs {
        inner: StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault,
    })
}

/// Creates Standard intent that moves eligible artifacts to a caller-selected destination.
///
/// The core contract validates destination semantics during execution so typed
/// request-validation failures retain the same behavior across adapters.
pub(crate) fn scan_run_unsolved_logs_move_to_custom(
    destination: &str,
) -> Result<Box<ScanRunUnsolvedLogs>, String> {
    Ok(Box::new(ScanRunUnsolvedLogs {
        inner: StandardUnsolvedLogsIntent::MoveToCustom(required_path(destination, "destination")?),
    }))
}

/// Constructs a non-FCX Standard request while preserving its tagged invariants.
///
/// Returns an error when a required path or game identifier cannot be represented.
/// An explicit zero concurrency remains a typed request-validation failure at execution.
pub(crate) fn scan_run_request_standard(
    configuration: &ffi::ScanRunConfigurationDto,
    source: &ffi::ScanRunStandardSourceDto,
    unsolved_logs: &ScanRunUnsolvedLogs,
) -> Result<Box<ScanRunRequest>, String> {
    let configuration = configuration_to_core(configuration)?;
    let source = standard_source_to_core(source)?;
    Ok(Box::new(ScanRunRequest {
        inner: contract::Request::standard(configuration, source, unsolved_logs.inner.clone()),
    }))
}

/// Constructs an FCX-enabled Standard request with explicit run-scoped setup facts.
///
/// Returns an error when the shared configuration or source cannot be represented.
pub(crate) fn scan_run_request_standard_with_fcx(
    configuration: &ffi::ScanRunConfigurationDto,
    source: &ffi::ScanRunStandardSourceDto,
    unsolved_logs: &ScanRunUnsolvedLogs,
    setup_context: &ffi::ScanRunSetupContextDto,
) -> Result<Box<ScanRunRequest>, String> {
    Ok(Box::new(ScanRunRequest {
        inner: contract::Request::standard_with_fcx(
            configuration_to_core(configuration)?,
            standard_source_to_core(source)?,
            unsolved_logs.inner.clone(),
            setup_context_to_core(setup_context)?,
        ),
    }))
}

/// Constructs a non-FCX Targeted request, which has no Unsolved Logs capability.
///
/// Returns an error when the shared configuration contains invalid required values.
pub(crate) fn scan_run_request_targeted(
    configuration: &ffi::ScanRunConfigurationDto,
    source: &ffi::ScanRunTargetedSourceDto,
) -> Result<Box<ScanRunRequest>, String> {
    Ok(Box::new(ScanRunRequest {
        inner: contract::Request::targeted(
            configuration_to_core(configuration)?,
            targeted_source_to_core(source),
        ),
    }))
}

/// Constructs an FCX-enabled Targeted request with explicit run-scoped setup facts.
///
/// Targeted construction deliberately accepts no Unsolved Logs intent.
///
/// Returns an error when the shared configuration, source, or setup context
/// contains a required value that cannot be represented.
pub(crate) fn scan_run_request_targeted_with_fcx(
    configuration: &ffi::ScanRunConfigurationDto,
    source: &ffi::ScanRunTargetedSourceDto,
    setup_context: &ffi::ScanRunSetupContextDto,
) -> Result<Box<ScanRunRequest>, String> {
    Ok(Box::new(ScanRunRequest {
        inner: contract::Request::targeted_with_fcx(
            configuration_to_core(configuration)?,
            targeted_source_to_core(source),
            setup_context_to_core(setup_context)?,
        ),
    }))
}

/// Creates an uncancelled, monotonic control for one final-contract run.
pub(crate) fn scan_run_cancellation_new() -> Box<ScanRunCancellation> {
    Box::new(ScanRunCancellation {
        inner: contract::Cancellation::new(),
    })
}

/// Requests cooperative cancellation at the next Rust-owned safe seam.
pub(crate) fn scan_run_cancellation_cancel(cancellation: &ScanRunCancellation) {
    cancellation.inner.cancel();
}

/// Returns whether cancellation has been requested for this control.
pub(crate) fn scan_run_cancellation_is_cancelled(cancellation: &ScanRunCancellation) -> bool {
    cancellation.inner.is_cancelled()
}

/// Executes one final-contract request with an optional serialized C++ observer.
///
/// Passing a null observer disables observation. Infrastructure failures are
/// returned in the typed execution envelope rather than flattened into a CXX exception.
///
/// # Safety
///
/// A non-null `observer` must point to a live `ScanRunObserver` for the entire
/// synchronous call and must not throw from `on_scan_run_event`.
pub(crate) unsafe fn scan_run_contract_execute(
    request: &ScanRunRequest,
    cancellation: &ScanRunCancellation,
    observer: *const ffi::ScanRunObserver,
) -> Box<ScanRunContractExecution> {
    // SAFETY: the caller contract requires a non-null pointer to stay live for
    // this synchronous invocation; null explicitly means observation is disabled.
    let observer = unsafe { observer.as_ref() };
    let result = match observer {
        Some(observer) => {
            let mut adapter = CxxObserverAdapter { observer };
            block_on(contract::execute(
                request.inner.clone(),
                &cancellation.inner,
                Some(&mut adapter),
            ))
        }
        None => block_on(contract::execute(
            request.inner.clone(),
            &cancellation.inner,
            None,
        )),
    };

    Box::new(execution_from_initial_result(result))
}

/// Moves the DTO envelope out while leaving an ignored default behind.
pub(crate) fn scan_run_contract_execution_take_result(
    execution: &mut ScanRunContractExecution,
) -> ffi::ScanRunContractExecutionResult {
    std::mem::replace(&mut execution.result, empty_execution_result_dto())
}

/// Returns whether the operation still owns a recovery continuation.
pub(crate) fn scan_run_contract_execution_has_continuation(
    execution: &ScanRunContractExecution,
) -> bool {
    execution.continuation.is_some()
}

/// Moves the non-cloneable continuation out of its initial execution operation.
pub(crate) fn scan_run_contract_execution_take_continuation(
    execution: &mut ScanRunContractExecution,
) -> Result<Box<ScanRunContinuation>, String> {
    execution
        .continuation
        .take()
        .map(Box::new)
        .ok_or_else(|| "scan run execution has no recovery continuation".to_string())
}

/// Resumes retained work without repeating discovery or YAML Data selection.
///
/// Replay is projected into the stable typed resume-error envelope.
///
/// # Safety
///
/// A non-null `observer` must point to a live `ScanRunObserver` for this synchronous call.
pub(crate) unsafe fn scan_run_continuation_resume(
    continuation: &ScanRunContinuation,
    decision: ffi::ScanRunLocalIgnoreRecoveryDecision,
    cancellation: &ScanRunCancellation,
    observer: *const ffi::ScanRunObserver,
) -> Result<Box<ScanRunContractExecution>, String> {
    // SAFETY: the caller contract requires a non-null pointer to stay live for
    // this synchronous invocation; null explicitly means observation is disabled.
    let observer = unsafe { observer.as_ref() };
    // Reject CXX's non-exhaustive sentinel before claiming the one-shot continuation.
    let decision = map_local_ignore_recovery_decision(decision)?;
    let result = match observer {
        Some(observer) => {
            let mut adapter = CxxObserverAdapter { observer };
            block_on(
                continuation
                    .inner
                    .resume(decision, &cancellation.inner, Some(&mut adapter)),
            )
        }
        None => block_on(
            continuation
                .inner
                .resume(decision, &cancellation.inner, None),
        ),
    };

    Ok(Box::new(execution_from_resume_result(result)))
}

fn execution_from_initial_result(
    result: Result<contract::RunResult, contract::InfrastructureError>,
) -> ScanRunContractExecution {
    match result {
        Ok(mut result) => ScanRunContractExecution {
            continuation: result
                .continuation
                .take()
                .map(|inner| ScanRunContinuation { inner }),
            result: success_execution_result_dto(result),
        },
        Err(error) => ScanRunContractExecution {
            result: infrastructure_execution_result_dto(error),
            continuation: None,
        },
    }
}

fn execution_from_resume_result(
    result: Result<contract::RunResult, contract::ResumeError>,
) -> ScanRunContractExecution {
    let result = match result {
        Ok(result) => success_execution_result_dto(result),
        Err(contract::ResumeError::Infrastructure(error)) => {
            infrastructure_execution_result_dto(error)
        }
        Err(error) => ffi::ScanRunContractExecutionResult {
            has_result: false,
            result: empty_run_result_dto(),
            has_error: false,
            error: empty_infrastructure_error_dto(),
            has_resume_error: true,
            resume_error: resume_error_to_dto(error),
        },
    };
    ScanRunContractExecution {
        result,
        continuation: None,
    }
}

fn success_execution_result_dto(
    result: contract::RunResult,
) -> ffi::ScanRunContractExecutionResult {
    ffi::ScanRunContractExecutionResult {
        has_result: true,
        result: run_result_to_dto(result),
        has_error: false,
        error: empty_infrastructure_error_dto(),
        has_resume_error: false,
        resume_error: empty_resume_error_dto(),
    }
}

fn infrastructure_execution_result_dto(
    error: contract::InfrastructureError,
) -> ffi::ScanRunContractExecutionResult {
    ffi::ScanRunContractExecutionResult {
        has_result: false,
        result: empty_run_result_dto(),
        has_error: true,
        error: infrastructure_error_to_dto(error),
        has_resume_error: false,
        resume_error: empty_resume_error_dto(),
    }
}

struct CxxObserverAdapter<'a> {
    observer: &'a ffi::ScanRunObserver,
}

// The final core serializes observer calls. The C++ object is borrowed for the
// blocking execution and its noexcept method may be called from that execution context.
unsafe impl Send for CxxObserverAdapter<'_> {}

impl contract::Observer for CxxObserverAdapter<'_> {
    fn on_event(&mut self, event: contract::Event) {
        self.observer.on_scan_run_event(&event_to_dto(event));
    }
}

fn map_run_status(value: CrashLogScanRunStatus) -> ffi::ScanRunContractStatus {
    match value {
        CrashLogScanRunStatus::Completed => ffi::ScanRunContractStatus::Completed,
        CrashLogScanRunStatus::NoCrashLogsFound => ffi::ScanRunContractStatus::NoCrashLogsFound,
        CrashLogScanRunStatus::SetupFailed => ffi::ScanRunContractStatus::SetupFailed,
        CrashLogScanRunStatus::CancelledBeforeDiscovery => {
            ffi::ScanRunContractStatus::CancelledBeforeDiscovery
        }
        CrashLogScanRunStatus::Cancelled => ffi::ScanRunContractStatus::Cancelled,
        CrashLogScanRunStatus::LocalIgnoreRecoveryRequired => {
            ffi::ScanRunContractStatus::LocalIgnoreRecoveryRequired
        }
    }
}

fn map_discovery_source(value: CrashLogScanDiscoverySource) -> ffi::ScanRunContractDiscoverySource {
    match value {
        CrashLogScanDiscoverySource::Standard => ffi::ScanRunContractDiscoverySource::Standard,
        CrashLogScanDiscoverySource::Targeted => ffi::ScanRunContractDiscoverySource::Targeted,
    }
}

fn map_log_disposition(value: contract::LogDisposition) -> ffi::ScanRunContractLogDisposition {
    match value {
        contract::LogDisposition::Succeeded => ffi::ScanRunContractLogDisposition::Succeeded,
        contract::LogDisposition::Failed => ffi::ScanRunContractLogDisposition::Failed,
        contract::LogDisposition::CancelledBeforeStart => {
            ffi::ScanRunContractLogDisposition::CancelledBeforeStart
        }
    }
}

fn map_log_failure_stage(value: contract::LogFailureStage) -> ffi::ScanRunContractLogFailureStage {
    match value {
        contract::LogFailureStage::Analysis => ffi::ScanRunContractLogFailureStage::Analysis,
        contract::LogFailureStage::ReportWrite => ffi::ScanRunContractLogFailureStage::ReportWrite,
        contract::LogFailureStage::UnsolvedLogsFinalization => {
            ffi::ScanRunContractLogFailureStage::UnsolvedLogsFinalization
        }
    }
}

fn map_infrastructure_error_stage(
    value: contract::InfrastructureErrorStage,
) -> ffi::ScanRunContractInfrastructureErrorStage {
    match value {
        contract::InfrastructureErrorStage::RequestValidation => {
            ffi::ScanRunContractInfrastructureErrorStage::RequestValidation
        }
        contract::InfrastructureErrorStage::Discovery => {
            ffi::ScanRunContractInfrastructureErrorStage::Discovery
        }
        contract::InfrastructureErrorStage::Intake => {
            ffi::ScanRunContractInfrastructureErrorStage::Intake
        }
        contract::InfrastructureErrorStage::FormIdDatabaseAccess => {
            ffi::ScanRunContractInfrastructureErrorStage::FormIdDatabaseAccess
        }
        contract::InfrastructureErrorStage::Initialization => {
            ffi::ScanRunContractInfrastructureErrorStage::Initialization
        }
        contract::InfrastructureErrorStage::InternalInvariant => {
            ffi::ScanRunContractInfrastructureErrorStage::InternalInvariant
        }
    }
}

fn map_phase(value: ScanProgressPhase) -> ffi::ScanRunContractProgressPhase {
    match value {
        ScanProgressPhase::Setup => ffi::ScanRunContractProgressPhase::Setup,
        ScanProgressPhase::Parse => ffi::ScanRunContractProgressPhase::Parse,
        ScanProgressPhase::Analyze => ffi::ScanRunContractProgressPhase::Analyze,
        ScanProgressPhase::Finalize => ffi::ScanRunContractProgressPhase::Finalize,
    }
}

/// Maps discovery without separating rejected paths from their reasons.
fn discovery_to_dto(value: CrashLogScanDiscoveryResult) -> ffi::ScanRunContractDiscoveryResult {
    ffi::ScanRunContractDiscoveryResult {
        source: map_discovery_source(value.source),
        accepted_logs: value
            .accepted_logs
            .into_iter()
            .map(path_to_string)
            .collect(),
        rejected_inputs: value
            .rejected_inputs
            .into_iter()
            .map(|rejected| ffi::ScanRunContractRejectedInput {
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

/// Maps one terminal log result while preserving every failure and optional-field presence.
fn log_result_to_dto(value: contract::LogResult) -> ffi::ScanRunContractLogResult {
    let (has_autoscan_report, autoscan_report) = optional_path_to_dto(value.autoscan_report);
    let (has_message, message) = optional_string_to_dto(value.message);
    ffi::ScanRunContractLogResult {
        discovery_index: value.discovery_index,
        crash_log: path_to_string(value.crash_log),
        has_autoscan_report,
        autoscan_report,
        disposition: map_log_disposition(value.disposition),
        failures: value
            .failures
            .into_iter()
            .map(|failure| ffi::ScanRunContractLogFailure {
                stage: map_log_failure_stage(failure.stage),
                message: failure.message,
            })
            .collect(),
        has_message,
        message,
        moved_to_unsolved_logs: value.moved_to_unsolved_logs,
        processing_time_us: value.processing_time_us,
        processing_time_ms: value.processing_time_ms,
        formid_count: value.formid_count,
        plugin_count: value.plugin_count,
        suspect_count: value.suspect_count,
    }
}

/// Maps the complete terminal result and supplies ignored defaults beside explicit presence flags.
fn run_result_to_dto(value: contract::RunResult) -> ffi::ScanRunContractRunResult {
    let (has_discovery, discovery) = value
        .discovery
        .map(|discovery| (true, discovery_to_dto(discovery)))
        .unwrap_or_else(|| (false, empty_discovery_dto()));
    let (has_setup, setup) = value
        .setup
        .map(|setup| (true, setup_to_dto(setup)))
        .unwrap_or_else(|| (false, empty_setup_dto()));
    let (has_installed_yaml_data, installed_yaml_data) = value
        .installed_yaml_data
        .map(|installed| (true, installed_yaml_data_to_dto(installed)))
        .unwrap_or_else(|| (false, empty_installed_yaml_data_dto()));
    let (has_effective_concurrency, effective_concurrency) = value
        .effective_concurrency
        .map(|value| (true, value))
        .unwrap_or((false, 0));
    let (has_message, message) = optional_string_to_dto(value.message);

    ffi::ScanRunContractRunResult {
        status: map_run_status(value.status),
        has_discovery,
        discovery,
        has_setup,
        setup,
        has_installed_yaml_data,
        installed_yaml_data,
        has_effective_concurrency,
        effective_concurrency,
        has_message,
        message,
        total: value.total,
        succeeded: value.succeeded,
        failed: value.failed,
        cancelled: value.cancelled,
        logs: value.logs.into_iter().map(log_result_to_dto).collect(),
    }
}

/// Preserves the typed run-wide stage, message, and optional relevant path.
fn infrastructure_error_to_dto(
    value: contract::InfrastructureError,
) -> ffi::ScanRunContractInfrastructureError {
    let (has_path, path) = optional_path_to_dto(value.path);
    ffi::ScanRunContractInfrastructureError {
        stage: map_infrastructure_error_stage(value.stage),
        message: value.message,
        has_path,
        path,
    }
}

fn empty_discovery_dto() -> ffi::ScanRunContractDiscoveryResult {
    ffi::ScanRunContractDiscoveryResult {
        source: ffi::ScanRunContractDiscoverySource::Standard,
        accepted_logs: Vec::new(),
        rejected_inputs: Vec::new(),
        searched_locations: Vec::new(),
    }
}

/// Maps run-scoped setup data without collapsing an absent message into an empty present value.
fn setup_to_dto(value: CrashLogScanSetupResult) -> ffi::ScanRunContractSetupResult {
    let (has_message, message) = optional_string_to_dto(value.message);
    ffi::ScanRunContractSetupResult {
        status: value.status,
        has_message,
        message,
        rendered_report: value.rendered_report,
        checks: value
            .checks
            .into_iter()
            .map(|check| ffi::ScanRunSetupCheckDto {
                kind: check.kind,
                state: check.state,
                message: check.message,
                details: check.details,
            })
            .collect(),
        path_updates: value
            .path_updates
            .into_iter()
            .map(|update| ffi::ScanRunSetupPathUpdateDto {
                kind: update.kind,
                path: path_to_string(update.path),
            })
            .collect(),
        configuration_issues: value
            .configuration_issues
            .iter()
            .map(fcx_issue_to_dto)
            .collect(),
        actions: value.actions,
        fatal_errors: value.fatal_errors,
    }
}

fn empty_setup_dto() -> ffi::ScanRunContractSetupResult {
    ffi::ScanRunContractSetupResult {
        status: String::new(),
        has_message: false,
        message: String::new(),
        rendered_report: String::new(),
        checks: Vec::new(),
        path_updates: Vec::new(),
        configuration_issues: Vec::new(),
        actions: Vec::new(),
        fatal_errors: Vec::new(),
    }
}

fn empty_run_result_dto() -> ffi::ScanRunContractRunResult {
    ffi::ScanRunContractRunResult {
        status: ffi::ScanRunContractStatus::Completed,
        has_discovery: false,
        discovery: empty_discovery_dto(),
        has_setup: false,
        setup: empty_setup_dto(),
        has_installed_yaml_data: false,
        installed_yaml_data: empty_installed_yaml_data_dto(),
        has_effective_concurrency: false,
        effective_concurrency: 0,
        has_message: false,
        message: String::new(),
        total: 0,
        succeeded: 0,
        failed: 0,
        cancelled: 0,
        logs: Vec::new(),
    }
}

fn empty_infrastructure_error_dto() -> ffi::ScanRunContractInfrastructureError {
    ffi::ScanRunContractInfrastructureError {
        stage: ffi::ScanRunContractInfrastructureErrorStage::RequestValidation,
        message: String::new(),
        has_path: false,
        path: String::new(),
    }
}

fn resume_error_to_dto(error: contract::ResumeError) -> ffi::ScanRunContractResumeError {
    let kind = error.kind();
    let message = error.to_string();
    let mut dto = empty_resume_error_dto();
    dto.kind = map_resume_error_kind(kind);
    dto.code = kind.as_str().to_string();
    dto.message = message;
    match error {
        contract::ResumeError::ContinuationConsumed | contract::ResumeError::Infrastructure(_) => {}
        contract::ResumeError::LocalIgnoreResetConflict(conflict) => {
            dto.has_expected_identity = true;
            dto.expected_identity = yaml_data_content_identity_to_dto(conflict.expected_identity);
            if let Some(actual) = conflict.actual_identity {
                dto.has_actual_identity = true;
                dto.actual_identity = yaml_data_content_identity_to_dto(actual);
            }
            if let Some(backup_path) = conflict.backup_path {
                dto.has_backup_path = true;
                dto.backup_path = path_to_string(backup_path);
            }
        }
        contract::ResumeError::LocalIgnoreResetBackupFailure(failure)
        | contract::ResumeError::LocalIgnoreResetReplacementFailure(failure) => {
            dto.has_path = true;
            dto.path = path_to_string(failure.path);
            if let Some(stage) = failure.stage {
                dto.has_stage = true;
                dto.stage = map_reset_failure_stage(stage);
            }
        }
    }
    dto
}

fn empty_resume_error_dto() -> ffi::ScanRunContractResumeError {
    ffi::ScanRunContractResumeError {
        kind: ffi::ScanRunContractResumeErrorKind::ContinuationConsumed,
        code: String::new(),
        message: String::new(),
        has_path: false,
        path: String::new(),
        has_stage: false,
        stage: ffi::ScanRunLocalIgnoreResetFailureStage::Create,
        has_expected_identity: false,
        expected_identity: empty_yaml_data_content_identity_dto(),
        has_actual_identity: false,
        actual_identity: empty_yaml_data_content_identity_dto(),
        has_backup_path: false,
        backup_path: String::new(),
    }
}

fn empty_execution_result_dto() -> ffi::ScanRunContractExecutionResult {
    ffi::ScanRunContractExecutionResult {
        has_result: false,
        result: empty_run_result_dto(),
        has_error: false,
        error: empty_infrastructure_error_dto(),
        has_resume_error: false,
        resume_error: empty_resume_error_dto(),
    }
}

fn optional_string_to_dto(value: Option<String>) -> (bool, String) {
    value.map(|value| (true, value)).unwrap_or_default()
}

fn optional_path_to_dto(value: Option<PathBuf>) -> (bool, String) {
    value
        .map(|path| (true, path_to_string(path)))
        .unwrap_or_default()
}

fn path_to_string(path: PathBuf) -> String {
    path.to_string_lossy().into_owned()
}

/// Maps every tagged lifecycle event; consumers ignore defaulted fields unrelated to the tag.
fn event_to_dto(value: contract::Event) -> ffi::ScanRunContractEvent {
    match value {
        contract::Event::DiscoveryCompleted(discovery) => {
            let mut event = empty_event_dto(ffi::ScanRunContractEventKind::DiscoveryCompleted);
            event.discovery = discovery_to_dto(discovery);
            event
        }
        contract::Event::EffectiveConcurrencySelected {
            effective_concurrency,
        } => {
            let mut event =
                empty_event_dto(ffi::ScanRunContractEventKind::EffectiveConcurrencySelected);
            event.effective_concurrency = effective_concurrency;
            event
        }
        contract::Event::LogQueued(log) => {
            log_event_to_dto(ffi::ScanRunContractEventKind::LogQueued, log)
        }
        contract::Event::LogStarted(log) => {
            log_event_to_dto(ffi::ScanRunContractEventKind::LogStarted, log)
        }
        contract::Event::LogPhase { log, phase } => {
            let mut event = log_event_to_dto(ffi::ScanRunContractEventKind::LogPhase, log);
            event.phase = map_phase(phase);
            event
        }
        contract::Event::LogFinished { log, disposition } => {
            let mut event = log_event_to_dto(ffi::ScanRunContractEventKind::LogFinished, log);
            event.disposition = map_log_disposition(disposition);
            event
        }
    }
}

fn empty_event_dto(kind: ffi::ScanRunContractEventKind) -> ffi::ScanRunContractEvent {
    ffi::ScanRunContractEvent {
        kind,
        discovery: empty_discovery_dto(),
        effective_concurrency: 0,
        discovery_index: 0,
        crash_log: String::new(),
        completed: 0,
        total: 0,
        phase: ffi::ScanRunContractProgressPhase::Setup,
        disposition: ffi::ScanRunContractLogDisposition::Succeeded,
    }
}

/// Maps one run-scoped FCX setup issue into the final CXX contract shape.
fn fcx_issue_to_dto(issue: &CoreFcxConfigIssue) -> ffi::FcxIssueDto {
    ffi::FcxIssueDto {
        file_path: issue.file_path.clone(),
        section_or_empty: issue.section.clone().unwrap_or_default(),
        has_section: issue.section.is_some(),
        setting: issue.setting.clone(),
        current_value: issue.current_value.clone(),
        recommended_value: issue.recommended_value.clone(),
        description: issue.description.clone(),
        severity: issue.severity.clone(),
    }
}

/// Supplies ignored nested defaults when Installed YAML Data is absent.
fn empty_installed_yaml_data_dto() -> ffi::ScanRunInstalledYamlDataRunDataDto {
    ffi::ScanRunInstalledYamlDataRunDataDto {
        main: empty_inspected_yaml_data_file_dto(ffi::ScanRunInstalledYamlDataRole::Main),
        game_file: empty_inspected_yaml_data_file_dto(ffi::ScanRunInstalledYamlDataRole::Game),
        local_ignore_state: ffi::ScanRunLocalIgnoreYamlDataState::Existing,
        local_ignore_identity: ffi::ScanRunYamlDataContentIdentityDto {
            sha256: String::new(),
            byte_len: 0,
        },
        diagnostics: Vec::new(),
        has_local_ignore_reset: false,
        local_ignore_reset: empty_local_ignore_reset_run_data_dto(),
    }
}

fn empty_yaml_data_content_identity_dto() -> ffi::ScanRunYamlDataContentIdentityDto {
    ffi::ScanRunYamlDataContentIdentityDto {
        sha256: String::new(),
        byte_len: 0,
    }
}

fn empty_local_ignore_reset_run_data_dto() -> ffi::ScanRunLocalIgnoreResetRunDataDto {
    ffi::ScanRunLocalIgnoreResetRunDataDto {
        local_ignore_path: String::new(),
        backup_path: String::new(),
        malformed_identity: empty_yaml_data_content_identity_dto(),
        backup_identity: empty_yaml_data_content_identity_dto(),
        replacement_identity: empty_yaml_data_content_identity_dto(),
    }
}

/// Supplies ignored selected-file defaults beside an absent run-level projection.
fn empty_inspected_yaml_data_file_dto(
    role: ffi::ScanRunInstalledYamlDataRole,
) -> ffi::ScanRunInspectedYamlDataFileDto {
    ffi::ScanRunInspectedYamlDataFileDto {
        role,
        provenance: ffi::ScanRunInstalledYamlDataProvenance::Bundled,
        schema_version: String::new(),
        sha256: String::new(),
        byte_len: 0,
    }
}

/// Maps exact retained content identity into its scanner-local CXX DTO.
fn yaml_data_content_identity_to_dto(
    value: YamlDataContentIdentity,
) -> ffi::ScanRunYamlDataContentIdentityDto {
    ffi::ScanRunYamlDataContentIdentityDto {
        sha256: value.sha256_hex(),
        byte_len: value.byte_len(),
    }
}

/// Maps selected file metadata into its scanner-local CXX DTO.
fn inspected_yaml_data_file_to_dto(
    value: InspectedYamlDataFile,
) -> ffi::ScanRunInspectedYamlDataFileDto {
    ffi::ScanRunInspectedYamlDataFileDto {
        role: map_installed_yaml_data_role(value.role()),
        provenance: map_installed_yaml_data_provenance(value.provenance()),
        schema_version: value.schema_version().to_string(),
        sha256: value.identity().sha256_hex(),
        byte_len: value.identity().byte_len(),
    }
}

/// Maps one structured selection or generation diagnostic without dropping optional context.
fn installed_yaml_data_diagnostic_to_dto(
    value: contract::InstalledYamlDataRunDiagnostic,
) -> ffi::ScanRunInstalledYamlDataDiagnosticDto {
    let role = value.role();
    let candidate = value.candidate();
    let path = value.path();
    ffi::ScanRunInstalledYamlDataDiagnosticDto {
        has_role: role.is_some(),
        role: role
            .map(map_installed_yaml_data_role)
            .unwrap_or(ffi::ScanRunInstalledYamlDataRole::Main),
        has_candidate: candidate.is_some(),
        candidate: candidate
            .map(map_installed_yaml_data_provenance)
            .unwrap_or(ffi::ScanRunInstalledYamlDataProvenance::Bundled),
        has_path: path.is_some(),
        path: path
            .map(|path| path_to_string(path.to_path_buf()))
            .unwrap_or_default(),
        kind: map_installed_yaml_data_diagnostic_kind(value.kind()),
        message: value.message().to_string(),
    }
}

/// Maps the complete Installed YAML Data run projection into scanner-local DTOs.
fn installed_yaml_data_to_dto(
    value: contract::InstalledYamlDataRunData,
) -> ffi::ScanRunInstalledYamlDataRunDataDto {
    let (has_local_ignore_reset, local_ignore_reset) = value
        .local_ignore_reset
        .map(|reset| (true, local_ignore_reset_run_data_to_dto(reset)))
        .unwrap_or_else(|| (false, empty_local_ignore_reset_run_data_dto()));
    ffi::ScanRunInstalledYamlDataRunDataDto {
        main: inspected_yaml_data_file_to_dto(value.main),
        game_file: inspected_yaml_data_file_to_dto(value.game_file),
        local_ignore_state: map_local_ignore_yaml_data_state(value.local_ignore_state),
        local_ignore_identity: yaml_data_content_identity_to_dto(value.local_ignore_identity),
        diagnostics: value
            .diagnostics
            .into_iter()
            .map(installed_yaml_data_diagnostic_to_dto)
            .collect(),
        has_local_ignore_reset,
        local_ignore_reset,
    }
}

fn local_ignore_reset_run_data_to_dto(
    value: contract::LocalIgnoreResetRunData,
) -> ffi::ScanRunLocalIgnoreResetRunDataDto {
    ffi::ScanRunLocalIgnoreResetRunDataDto {
        local_ignore_path: path_to_string(value.local_ignore_path),
        backup_path: path_to_string(value.backup_path),
        malformed_identity: yaml_data_content_identity_to_dto(value.malformed_identity),
        backup_identity: yaml_data_content_identity_to_dto(value.backup_identity),
        replacement_identity: yaml_data_content_identity_to_dto(value.replacement_identity),
    }
}

/// Maps every Installed YAML Data file role into the scanner-local CXX inventory.
fn map_installed_yaml_data_role(value: InstalledYamlDataRole) -> ffi::ScanRunInstalledYamlDataRole {
    match value {
        InstalledYamlDataRole::Main => ffi::ScanRunInstalledYamlDataRole::Main,
        InstalledYamlDataRole::Game => ffi::ScanRunInstalledYamlDataRole::Game,
    }
}

/// Maps every selected-file provenance into the scanner-local CXX inventory.
fn map_installed_yaml_data_provenance(
    value: InstalledYamlDataProvenance,
) -> ffi::ScanRunInstalledYamlDataProvenance {
    match value {
        InstalledYamlDataProvenance::Updated => ffi::ScanRunInstalledYamlDataProvenance::Updated,
        InstalledYamlDataProvenance::Previous => ffi::ScanRunInstalledYamlDataProvenance::Previous,
        InstalledYamlDataProvenance::Bundled => ffi::ScanRunInstalledYamlDataProvenance::Bundled,
    }
}

/// Maps every Local Ignore snapshot state into the scanner-local CXX inventory.
fn map_local_ignore_yaml_data_state(
    value: contract::LocalIgnoreRunState,
) -> ffi::ScanRunLocalIgnoreYamlDataState {
    match value {
        contract::LocalIgnoreRunState::Existing => ffi::ScanRunLocalIgnoreYamlDataState::Existing,
        contract::LocalIgnoreRunState::Generated => ffi::ScanRunLocalIgnoreYamlDataState::Generated,
        contract::LocalIgnoreRunState::RecoveryRequired => {
            ffi::ScanRunLocalIgnoreYamlDataState::RecoveryRequired
        }
        contract::LocalIgnoreRunState::ProceedWithoutIgnore => {
            ffi::ScanRunLocalIgnoreYamlDataState::ProceedWithoutIgnore
        }
        contract::LocalIgnoreRunState::ResetToDefault => {
            ffi::ScanRunLocalIgnoreYamlDataState::ResetToDefault
        }
    }
}

/// Maps the explicit CXX recovery choice into the Rust-owned continuation contract.
fn map_local_ignore_recovery_decision(
    value: ffi::ScanRunLocalIgnoreRecoveryDecision,
) -> Result<contract::LocalIgnoreRecoveryDecision, String> {
    match value {
        ffi::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore => {
            Ok(contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore)
        }
        ffi::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault => {
            Ok(contract::LocalIgnoreRecoveryDecision::ResetToDefault)
        }
        _ => Err(format!(
            "unsupported ScanRunLocalIgnoreRecoveryDecision discriminant: {}",
            value.repr
        )),
    }
}

/// Maps every Installed YAML Data diagnostic kind into the scanner-local CXX inventory.
fn map_installed_yaml_data_diagnostic_kind(
    value: contract::InstalledYamlDataRunDiagnosticKind,
) -> ffi::ScanRunInstalledYamlDataDiagnosticKind {
    use contract::InstalledYamlDataRunDiagnosticKind as Kind;
    match value {
        Kind::CacheUnavailable => ffi::ScanRunInstalledYamlDataDiagnosticKind::CacheUnavailable,
        Kind::Missing => ffi::ScanRunInstalledYamlDataDiagnosticKind::Missing,
        Kind::Read => ffi::ScanRunInstalledYamlDataDiagnosticKind::Read,
        Kind::InvalidUtf8 => ffi::ScanRunInstalledYamlDataDiagnosticKind::InvalidUtf8,
        Kind::Parse => ffi::ScanRunInstalledYamlDataDiagnosticKind::Parse,
        Kind::InvalidSchema => ffi::ScanRunInstalledYamlDataDiagnosticKind::InvalidSchema,
        Kind::IncompatibleSchema => ffi::ScanRunInstalledYamlDataDiagnosticKind::IncompatibleSchema,
        Kind::InvalidRoleData => ffi::ScanRunInstalledYamlDataDiagnosticKind::InvalidRoleData,
        Kind::LocalIgnoreGenerated => {
            ffi::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated
        }
        Kind::LocalIgnoreReset => ffi::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreReset,
    }
}

fn map_resume_error_kind(value: contract::ResumeErrorKind) -> ffi::ScanRunContractResumeErrorKind {
    match value {
        contract::ResumeErrorKind::ContinuationConsumed => {
            ffi::ScanRunContractResumeErrorKind::ContinuationConsumed
        }
        contract::ResumeErrorKind::LocalIgnoreResetConflict => {
            ffi::ScanRunContractResumeErrorKind::LocalIgnoreResetConflict
        }
        contract::ResumeErrorKind::LocalIgnoreResetBackupFailure => {
            ffi::ScanRunContractResumeErrorKind::LocalIgnoreResetBackupFailure
        }
        contract::ResumeErrorKind::LocalIgnoreResetReplacementFailure => {
            ffi::ScanRunContractResumeErrorKind::LocalIgnoreResetReplacementFailure
        }
        contract::ResumeErrorKind::Infrastructure => {
            unreachable!("infrastructure resume errors use the infrastructure envelope")
        }
    }
}

fn map_reset_failure_stage(
    value: contract::LocalIgnoreResetFailureStage,
) -> ffi::ScanRunLocalIgnoreResetFailureStage {
    match value {
        contract::LocalIgnoreResetFailureStage::Create => {
            ffi::ScanRunLocalIgnoreResetFailureStage::Create
        }
        contract::LocalIgnoreResetFailureStage::Write => {
            ffi::ScanRunLocalIgnoreResetFailureStage::Write
        }
        contract::LocalIgnoreResetFailureStage::Flush => {
            ffi::ScanRunLocalIgnoreResetFailureStage::Flush
        }
        contract::LocalIgnoreResetFailureStage::Sync => {
            ffi::ScanRunLocalIgnoreResetFailureStage::Sync
        }
        contract::LocalIgnoreResetFailureStage::Publish => {
            ffi::ScanRunLocalIgnoreResetFailureStage::Publish
        }
    }
}

fn log_event_to_dto(
    kind: ffi::ScanRunContractEventKind,
    log: contract::LogEvent,
) -> ffi::ScanRunContractEvent {
    let mut event = empty_event_dto(kind);
    event.discovery_index = log.discovery_index;
    event.crash_log = path_to_string(log.crash_log);
    event.completed = log.completed;
    event.total = log.total;
    event
}

/// Validates bridge primitives and projects them into the core typed configuration.
///
/// Optional values honor their presence flags. Explicit zero concurrency is
/// retained so the final operation can return its typed request-validation error.
fn configuration_to_core(
    value: &ffi::ScanRunConfigurationDto,
) -> Result<contract::Configuration, String> {
    let installation_root = required_path(&value.installation_root, "installation_root")?;
    let game = scan_run_game_id_to_core(value.game)?;
    let max_concurrent = if value.has_max_concurrent {
        Some(value.max_concurrent)
    } else {
        None
    };
    let unsolved_logs_destination = optional_flagged_path(
        value.has_configured_unsolved_logs_destination,
        &value.configured_unsolved_logs_destination,
        "configured_unsolved_logs_destination",
    )?;

    Ok(contract::Configuration {
        installation_root,
        game,
        game_version: value.game_version.clone(),
        options: contract::Options::new(value.show_formid_values, value.simplify_logs),
        scan_facts: CrashLogScanFacts {
            formid_database_paths: value
                .formid_database_paths
                .iter()
                .map(PathBuf::from)
                .collect(),
            unsolved_logs_destination,
        },
        max_concurrent,
    })
}

/// Converts the scanner-local CXX game enum to the shared core identity.
fn scan_run_game_id_to_core(value: ffi::ScanRunGameId) -> Result<GameId, String> {
    match value {
        ffi::ScanRunGameId::Fallout4 => Ok(GameId::Fallout4),
        ffi::ScanRunGameId::Fallout4VR => Ok(GameId::Fallout4VR),
        ffi::ScanRunGameId::Skyrim => Ok(GameId::Skyrim),
        ffi::ScanRunGameId::Starfield => Ok(GameId::Starfield),
        // CXX shared enums can carry an unknown discriminant. Reject it instead
        // of conflating it with a real game whose support can change over time.
        _ => Err(format!(
            "unsupported ScanRunGameId discriminant: {}",
            value.repr
        )),
    }
}

fn standard_source_to_core(
    value: &ffi::ScanRunStandardSourceDto,
) -> Result<StandardCrashLogScanSource, String> {
    Ok(StandardCrashLogScanSource {
        base_directory: required_path(&value.base_directory, "base_directory")?,
        custom_scan_directory: optional_flagged_path(
            value.has_custom_scan_directory,
            &value.custom_scan_directory,
            "custom_scan_directory",
        )?,
        configured_documents_root: optional_flagged_path(
            value.has_configured_documents_root,
            &value.configured_documents_root,
            "configured_documents_root",
        )?,
    })
}

fn targeted_source_to_core(value: &ffi::ScanRunTargetedSourceDto) -> TargetedCrashLogScanSource {
    TargetedCrashLogScanSource {
        inputs: value.inputs.iter().map(PathBuf::from).collect(),
    }
}

fn setup_context_to_core(
    value: &ffi::ScanRunSetupContextDto,
) -> Result<CrashLogScanSetupContext, String> {
    Ok(CrashLogScanSetupContext {
        game_root: optional_flagged_path(value.has_game_root, &value.game_root, "game_root")?,
        docs_root: optional_flagged_path(value.has_docs_root, &value.docs_root, "docs_root")?,
        game_exe_path: optional_flagged_path(
            value.has_game_exe_path,
            &value.game_exe_path,
            "game_exe_path",
        )?,
        xse_log_path: optional_flagged_path(
            value.has_xse_log_path,
            &value.xse_log_path,
            "xse_log_path",
        )?,
    })
}

fn required_path(raw: &str, field: &str) -> Result<PathBuf, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        Err(format!("{field} must not be empty"))
    } else {
        Ok(PathBuf::from(trimmed))
    }
}

fn optional_flagged_path(
    has_value: bool,
    raw: &str,
    field: &str,
) -> Result<Option<PathBuf>, String> {
    if has_value {
        required_path(raw, field).map(Some)
    } else {
        Ok(None)
    }
}

// Keep the repository's required sibling-test declaration intact under rustfmt.
#[rustfmt::skip]
#[cfg(test)] #[path = "contract_tests.rs"] mod tests;
