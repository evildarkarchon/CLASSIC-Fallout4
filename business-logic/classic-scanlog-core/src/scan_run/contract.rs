//! Final language-neutral Crash Log Scan Run contract.
//!
//! [`execute`] starts the only public execution flow for a complete Crash Log
//! Scan Run, while [`CrashLogScanRunContinuation::resume`] completes retained
//! Local Ignore recovery work. Discovery, setup, scheduling, durable finalization,
//! cancellation, events, results, and typed infrastructure failures cross this boundary.

#[cfg(test)]
#[path = "contract_tests.rs"]
mod tests;

use super::{
    CrashLogScanDiscoveryResult, CrashLogScanOutcome, CrashLogScanRunEvent as EngineEvent,
    CrashLogScanRunEventKind as EngineEventKind, CrashLogScanRunLogOutcome as EngineLogOutcome,
    CrashLogScanRunResult as EngineRunResult, CrashLogScanRunServiceError,
    CrashLogScanRunServiceEvent, CrashLogScanRunServiceRequest, CrashLogScanSetupContext,
    CrashLogScanSetupResult, CrashLogScanSource, PreparedCrashLogScanRunContinuation,
    StandardCrashLogScanSource, StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
    execute_service, resume_prepared_scan_run,
};
use crate::{CrashLogScanFacts, CrashLogScanOptions, ScanProgressPhase};
use classic_config_core::{
    InspectedYamlDataFile, InstalledYamlDataDiagnostic, InstalledYamlDataDiagnosticKind,
    InstalledYamlDataProvenance, InstalledYamlDataRole, InstalledYamlDataSnapshot,
    LocalIgnoreRecoveryPlan, LocalIgnoreResetConflict, LocalIgnoreResetError,
    LocalIgnoreResetOutcome, LocalIgnoreResetPublicationStage, LocalIgnoreResetResult,
    LocalIgnoreYamlDataState, YamlDataContentIdentity,
};
use classic_shared_core::GameId;
use std::fmt;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::Mutex;
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
    /// Root of the CLASSIC installation whose Installed YAML Data should be selected.
    pub installation_root: PathBuf,
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
            installation_root: configuration.installation_root,
            game: configuration.game,
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

/// Explicit recovery choices supported by this continuation contract.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LocalIgnoreRecoveryDecision {
    /// Resume the retained run with an empty ignore list scoped to this operation.
    ProceedWithoutIgnore,
    /// Durably reset malformed Local Ignore from retained selected-Main defaults, then resume.
    ResetToDefault,
}

impl LocalIgnoreRecoveryDecision {
    /// Returns the stable adapter-facing decision identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ProceedWithoutIgnore => "proceed_without_ignore",
            Self::ResetToDefault => "reset_to_default",
        }
    }
}

/// Stable categories returned when continuation resume cannot complete normally.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ResumeErrorKind {
    /// The opaque continuation was already claimed by an earlier resume attempt.
    ContinuationConsumed,
    /// The canonical Local Ignore identity changed while the caller was deciding.
    LocalIgnoreResetConflict,
    /// Reset failed before a verified backup was ready for replacement.
    LocalIgnoreResetBackupFailure,
    /// Reset failed while publishing the retained defaults as authoritative.
    LocalIgnoreResetReplacementFailure,
    /// The retained run encountered a run-wide infrastructure failure after resume.
    Infrastructure,
}

impl ResumeErrorKind {
    /// Returns the stable adapter-facing error identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ContinuationConsumed => "scan_run_continuation_consumed",
            Self::LocalIgnoreResetConflict => "local_ignore_reset_conflict",
            Self::LocalIgnoreResetBackupFailure => "local_ignore_reset_backup_failure",
            Self::LocalIgnoreResetReplacementFailure => "local_ignore_reset_replacement_failure",
            Self::Infrastructure => "infrastructure",
        }
    }
}

/// Conflict details retained when Reset To Default refuses to overwrite newer Local Ignore state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LocalIgnoreResetConflictError {
    /// Malformed-file identity against which the caller approved reset.
    pub expected_identity: YamlDataContentIdentity,
    /// Current canonical identity, absent when another actor removed the file.
    pub actual_identity: Option<YamlDataContentIdentity>,
    /// Verified backup retained before a late conflict, when publication had already completed.
    pub backup_path: Option<PathBuf>,
}

/// Stable publication stages exposed by reset operational failures.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LocalIgnoreResetFailureStage {
    /// A same-directory staging file could not be created.
    Create,
    /// Complete bytes could not be written to the staging file.
    Write,
    /// Buffered staging bytes could not be flushed.
    Flush,
    /// Staging bytes could not be synchronized to durable storage.
    Sync,
    /// The synchronized staging file could not be published.
    Publish,
}

impl LocalIgnoreResetFailureStage {
    /// Returns the stable adapter-facing publication stage identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Create => "create",
            Self::Write => "write",
            Self::Flush => "flush",
            Self::Sync => "sync",
            Self::Publish => "publish",
        }
    }
}

/// Presentation-safe details for a Local Ignore reset operational failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LocalIgnoreResetFailure {
    /// Relevant backup, staging, or canonical path.
    pub path: PathBuf,
    /// Publication stage when the failure came from staged durable publication.
    pub stage: Option<LocalIgnoreResetFailureStage>,
    /// Human-readable diagnostic preserving the config-core failure context.
    pub message: String,
}

/// Typed failure returned by [`CrashLogScanRunContinuation::resume`].
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ResumeError {
    /// The continuation was already consumed by a sequential or concurrent caller.
    ContinuationConsumed,
    /// Reset detected newer or removed canonical Local Ignore state.
    LocalIgnoreResetConflict(LocalIgnoreResetConflictError),
    /// Reset failed before replacement could safely begin.
    LocalIgnoreResetBackupFailure(LocalIgnoreResetFailure),
    /// Reset failed while publishing the retained defaults.
    LocalIgnoreResetReplacementFailure(LocalIgnoreResetFailure),
    /// Resume reached a run-wide infrastructure failure.
    Infrastructure(InfrastructureError),
}

impl ResumeError {
    /// Returns the stable category for exhaustive binding projection.
    #[must_use]
    pub const fn kind(&self) -> ResumeErrorKind {
        match self {
            Self::ContinuationConsumed => ResumeErrorKind::ContinuationConsumed,
            Self::LocalIgnoreResetConflict(_) => ResumeErrorKind::LocalIgnoreResetConflict,
            Self::LocalIgnoreResetBackupFailure(_) => {
                ResumeErrorKind::LocalIgnoreResetBackupFailure
            }
            Self::LocalIgnoreResetReplacementFailure(_) => {
                ResumeErrorKind::LocalIgnoreResetReplacementFailure
            }
            Self::Infrastructure(_) => ResumeErrorKind::Infrastructure,
        }
    }

    /// Returns retained infrastructure failure details when that category applies.
    #[must_use]
    pub const fn infrastructure(&self) -> Option<&InfrastructureError> {
        match self {
            Self::ContinuationConsumed
            | Self::LocalIgnoreResetConflict(_)
            | Self::LocalIgnoreResetBackupFailure(_)
            | Self::LocalIgnoreResetReplacementFailure(_) => None,
            Self::Infrastructure(error) => Some(error),
        }
    }
}

impl fmt::Display for ResumeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ContinuationConsumed => {
                formatter.write_str("Crash Log Scan Run continuation was already consumed")
            }
            Self::LocalIgnoreResetConflict(_) => {
                formatter.write_str("Local Ignore reset conflicted with current canonical state")
            }
            Self::LocalIgnoreResetBackupFailure(failure)
            | Self::LocalIgnoreResetReplacementFailure(failure) => {
                formatter.write_str(&failure.message)
            }
            Self::Infrastructure(error) => error.fmt(formatter),
        }
    }
}

impl std::error::Error for ResumeError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::ContinuationConsumed
            | Self::LocalIgnoreResetConflict(_)
            | Self::LocalIgnoreResetBackupFailure(_)
            | Self::LocalIgnoreResetReplacementFailure(_) => None,
            Self::Infrastructure(error) => Some(error),
        }
    }
}

/// Projects config-core conflict data without exposing the consumed recovery plan.
fn project_local_ignore_reset_conflict(
    conflict: LocalIgnoreResetConflict,
) -> LocalIgnoreResetConflictError {
    LocalIgnoreResetConflictError {
        expected_identity: conflict.expected_identity().clone(),
        actual_identity: conflict.actual_identity().cloned(),
        backup_path: conflict.backup_path().map(std::path::Path::to_path_buf),
    }
}

/// Converts config-core reset failures into stable continuation outcomes for every adapter.
fn project_local_ignore_reset_error(error: LocalIgnoreResetError) -> ResumeError {
    let message = error.to_string();
    let (replacement_failure, path, stage) = match error {
        LocalIgnoreResetError::DefaultsUnavailable { path, .. }
        | LocalIgnoreResetError::Lock { path, .. }
        | LocalIgnoreResetError::Read { path, .. }
        | LocalIgnoreResetError::BackupDirectory { path, .. }
        | LocalIgnoreResetError::BackupVerification { path, .. } => (false, path, None),
        LocalIgnoreResetError::BackupPublication { path, stage, .. } => {
            (false, path, Some(project_reset_publication_stage(stage)))
        }
        LocalIgnoreResetError::ReplacementPublication { path, stage, .. } => {
            (true, path, Some(project_reset_publication_stage(stage)))
        }
    };
    let failure = LocalIgnoreResetFailure {
        path,
        stage,
        message,
    };
    if replacement_failure {
        ResumeError::LocalIgnoreResetReplacementFailure(failure)
    } else {
        ResumeError::LocalIgnoreResetBackupFailure(failure)
    }
}

/// Maps config-core durable-publication stages into the scan-run contract vocabulary.
const fn project_reset_publication_stage(
    stage: LocalIgnoreResetPublicationStage,
) -> LocalIgnoreResetFailureStage {
    match stage {
        LocalIgnoreResetPublicationStage::Create => LocalIgnoreResetFailureStage::Create,
        LocalIgnoreResetPublicationStage::Write => LocalIgnoreResetFailureStage::Write,
        LocalIgnoreResetPublicationStage::Flush => LocalIgnoreResetFailureStage::Flush,
        LocalIgnoreResetPublicationStage::Sync => LocalIgnoreResetFailureStage::Sync,
        LocalIgnoreResetPublicationStage::Publish => LocalIgnoreResetFailureStage::Publish,
    }
}

/// Opaque, process-local, non-cloneable continuation for one paused scan run.
pub struct CrashLogScanRunContinuation {
    state: Mutex<Option<PreparedCrashLogScanRunContinuation>>,
}

impl fmt::Debug for CrashLogScanRunContinuation {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        let consumed = self
            .state
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .is_none();
        formatter
            .debug_struct("CrashLogScanRunContinuation")
            .field("consumed", &consumed)
            .finish_non_exhaustive()
    }
}

impl CrashLogScanRunContinuation {
    /// Wraps prepared Rust-owned state without exposing reconstructable fields.
    pub(super) fn new(state: PreparedCrashLogScanRunContinuation) -> Self {
        Self {
            state: Mutex::new(Some(state)),
        }
    }

    /// Atomically claims this continuation and resumes the retained run once.
    ///
    /// Cancellation is checked after the one-shot claim but before the recovery plan is consumed,
    /// so a cancelled resume returns the normal cancelled-after-discovery result without analysis.
    /// Reset To Default then runs as one synchronous non-interruptible transaction; cancellation
    /// observed after that transaction returns the same normal cancelled result after preserving
    /// its durable backup and replacement.
    ///
    /// # Errors
    ///
    /// Returns [`ResumeError::ContinuationConsumed`] for sequential or concurrent replay, a typed
    /// Local Ignore reset conflict/backup/replacement failure, or [`ResumeError::Infrastructure`]
    /// when the resumed run cannot produce a terminal result.
    pub async fn resume(
        &self,
        decision: LocalIgnoreRecoveryDecision,
        cancellation: &Cancellation,
        mut observer: Option<&mut dyn Observer>,
    ) -> Result<RunResult, ResumeError> {
        let state = self
            .state
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .take()
            .ok_or(ResumeError::ContinuationConsumed)?;

        if cancellation.is_cancelled() {
            return Ok(project_engine_result(
                EngineRunResult::cancelled_after_discovery(state.prepared.discovery),
                None,
            ));
        }

        let PreparedCrashLogScanRunContinuation {
            recovery_plan,
            prepared,
        } = state;
        let (snapshot, installed_yaml_data, reset_completed) = match decision {
            LocalIgnoreRecoveryDecision::ProceedWithoutIgnore => {
                let snapshot = recovery_plan.proceed_without_ignore();
                let installed_yaml_data = InstalledYamlDataRunData::from_snapshot(&snapshot)
                    .ok_or_else(|| {
                        ResumeError::Infrastructure(InfrastructureError {
                            stage: InfrastructureErrorStage::InternalInvariant,
                            message: "Proceed Without Ignore produced unsupported scan metadata"
                                .to_string(),
                            path: None,
                        })
                    })?;
                (snapshot, installed_yaml_data, false)
            }
            LocalIgnoreRecoveryDecision::ResetToDefault => {
                #[cfg(test)]
                prepared
                    .test_hooks
                    .enter_local_ignore_reset_critical_section();
                match recovery_plan.reset_to_default() {
                    Ok(LocalIgnoreResetOutcome::Reset(reset)) => {
                        let installed_yaml_data = InstalledYamlDataRunData::from_reset_result(
                            &reset,
                        )
                        .ok_or_else(|| {
                            ResumeError::Infrastructure(InfrastructureError {
                                stage: InfrastructureErrorStage::InternalInvariant,
                                message: "Reset To Default produced unsupported scan metadata"
                                    .to_string(),
                                path: None,
                            })
                        })?;
                        (reset.into_snapshot(), installed_yaml_data, true)
                    }
                    Ok(LocalIgnoreResetOutcome::Conflict(conflict)) => {
                        return Err(ResumeError::LocalIgnoreResetConflict(
                            project_local_ignore_reset_conflict(conflict),
                        ));
                    }
                    Err(error) => {
                        return Err(project_local_ignore_reset_error(error));
                    }
                }
            }
        };

        if reset_completed && cancellation.is_cancelled() {
            return Ok(project_engine_result(
                EngineRunResult::cancelled_after_discovery(prepared.discovery),
                None,
            ));
        }

        let mut effective_concurrency = None;
        let engine_result = resume_prepared_scan_run(
            prepared,
            snapshot,
            installed_yaml_data,
            cancellation.engine_flag(),
            |event| match event {
                CrashLogScanRunServiceEvent::DiscoveryCompleted(_) => {
                    // Resume owns completed discovery already and never emits rediscovery events.
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
            },
        )
        .await
        .map_err(|error| ResumeError::Infrastructure(InfrastructureError::from_service(error)))?;

        Ok(project_engine_result(engine_result, effective_concurrency))
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

/// Local Ignore state retained by a Crash Log Scan Run.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LocalIgnoreRunState {
    /// A valid user-owned Local Ignore file already existed in the installation.
    Existing,
    /// Missing Local Ignore YAML Data was generated from selected Main defaults.
    Generated,
    /// Malformed Local Ignore YAML Data requires an explicit caller decision.
    RecoveryRequired,
    /// This operation resumed with an empty, operation-scoped ignore list.
    ProceedWithoutIgnore,
    /// Malformed Local Ignore was durably reset from retained selected-Main defaults.
    ResetToDefault,
}

impl LocalIgnoreRunState {
    /// Returns the stable adapter-facing Local Ignore state identifier.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Existing => "existing",
            Self::Generated => "generated",
            Self::RecoveryRequired => "recovery_required",
            Self::ProceedWithoutIgnore => "proceed_without_ignore",
            Self::ResetToDefault => "reset_to_default",
        }
    }
}

/// Stable diagnostic categories emitted by valid-or-generated scan-run intake.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InstalledYamlDataRunDiagnosticKind {
    /// The per-user update cache could not be resolved.
    CacheUnavailable,
    /// A required final fallback candidate was absent.
    Missing,
    /// A present candidate could not be read.
    Read,
    /// Candidate bytes were not valid UTF-8.
    InvalidUtf8,
    /// Candidate text was not valid YAML Data.
    Parse,
    /// A candidate omitted or malformed its schema version.
    InvalidSchema,
    /// A candidate schema was outside the client-owned compatibility range.
    IncompatibleSchema,
    /// A candidate failed role-specific semantic validation.
    InvalidRoleData,
    /// Missing Local Ignore YAML Data was generated from selected Main defaults.
    LocalIgnoreGenerated,
    /// Malformed Local Ignore YAML Data was reset from retained selected-Main defaults.
    LocalIgnoreReset,
}

/// Structured attribution for one scan-run selection, fallback, or generation event.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InstalledYamlDataRunDiagnostic {
    role: Option<InstalledYamlDataRole>,
    candidate: Option<InstalledYamlDataProvenance>,
    path: Option<PathBuf>,
    kind: InstalledYamlDataRunDiagnosticKind,
    message: String,
}

impl InstalledYamlDataRunDiagnostic {
    /// Returns the affected update-eligible role, when the event is role-specific.
    #[must_use]
    pub const fn role(&self) -> Option<InstalledYamlDataRole> {
        self.role
    }

    /// Returns the rejected candidate provenance, when the event is candidate-specific.
    #[must_use]
    pub const fn candidate(&self) -> Option<InstalledYamlDataProvenance> {
        self.candidate
    }

    /// Returns the affected path when the diagnostic is path-attributable.
    #[must_use]
    pub fn path(&self) -> Option<&std::path::Path> {
        self.path.as_deref()
    }

    /// Returns the stable scan-run diagnostic category.
    #[must_use]
    pub const fn kind(&self) -> InstalledYamlDataRunDiagnosticKind {
        self.kind
    }

    /// Returns the actionable human-readable explanation.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// Installed YAML Data facts selected once and retained for a complete Crash Log Scan Run.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InstalledYamlDataRunData {
    /// Selected Main file schema, identity, and provenance.
    pub main: InspectedYamlDataFile,
    /// Selected game file schema, identity, and provenance.
    pub game_file: InspectedYamlDataFile,
    /// How Local Ignore YAML Data entered the immutable run snapshot.
    pub local_ignore_state: LocalIgnoreRunState,
    /// Identity derived from the exact Local Ignore bytes retained by the run.
    pub local_ignore_identity: YamlDataContentIdentity,
    /// Structured fallback, validation, and generation diagnostics.
    pub diagnostics: Vec<InstalledYamlDataRunDiagnostic>,
    /// Durable reset metadata, present only after successful Reset To Default resume.
    pub local_ignore_reset: Option<LocalIgnoreResetRunData>,
}

/// Durable Local Ignore reset metadata retained in a successful Crash Log Scan Run Result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LocalIgnoreResetRunData {
    /// Canonical Local Ignore path repaired by the retained recovery plan.
    pub local_ignore_path: PathBuf,
    /// Durable byte-exact backup verified before replacement became authoritative.
    pub backup_path: PathBuf,
    /// Identity of the malformed bytes retained while the caller decided.
    pub malformed_identity: YamlDataContentIdentity,
    /// Identity independently verified from the durable backup bytes.
    pub backup_identity: YamlDataContentIdentity,
    /// Identity of the retained selected-Main defaults published as replacement.
    pub replacement_identity: YamlDataContentIdentity,
}

impl InstalledYamlDataRunData {
    /// Copies scan-run metadata from a selected Installed YAML Data snapshot.
    #[must_use]
    pub(super) fn from_snapshot(snapshot: &InstalledYamlDataSnapshot) -> Option<Self> {
        let local_ignore_state = match snapshot.local_ignore_state() {
            LocalIgnoreYamlDataState::Existing => LocalIgnoreRunState::Existing,
            LocalIgnoreYamlDataState::Generated => LocalIgnoreRunState::Generated,
            LocalIgnoreYamlDataState::ProceedWithoutIgnore => {
                LocalIgnoreRunState::ProceedWithoutIgnore
            }
            LocalIgnoreYamlDataState::ResetToDefault => LocalIgnoreRunState::ResetToDefault,
        };
        let diagnostics = Self::map_diagnostics(snapshot.diagnostics())?;

        Some(Self {
            main: snapshot.main().clone(),
            game_file: snapshot.game_file().clone(),
            local_ignore_state,
            local_ignore_identity: snapshot.local_ignore_identity().clone(),
            diagnostics,
            local_ignore_reset: None,
        })
    }

    /// Copies presentation-safe metadata from a malformed Local Ignore recovery plan.
    #[must_use]
    pub(super) fn from_recovery_plan(plan: &LocalIgnoreRecoveryPlan) -> Option<Self> {
        Some(Self {
            main: plan.main().clone(),
            game_file: plan.game_file().clone(),
            local_ignore_state: LocalIgnoreRunState::RecoveryRequired,
            local_ignore_identity: plan.malformed_local_ignore_identity().clone(),
            diagnostics: Self::map_diagnostics(plan.diagnostics())?,
            local_ignore_reset: None,
        })
    }

    /// Copies reset-ready snapshot facts plus durable backup and replacement metadata.
    #[must_use]
    pub(super) fn from_reset_result(result: &LocalIgnoreResetResult) -> Option<Self> {
        let mut data = Self::from_snapshot(result.snapshot())?;
        data.local_ignore_reset = Some(LocalIgnoreResetRunData {
            local_ignore_path: result.local_ignore_path().to_path_buf(),
            backup_path: result.backup_path().to_path_buf(),
            malformed_identity: result.malformed_local_ignore_identity().clone(),
            backup_identity: result.backup_identity().clone(),
            replacement_identity: result.replacement_identity().clone(),
        });
        Some(data)
    }

    /// Maps Config Core diagnostics exhaustively into the language-neutral run contract.
    fn map_diagnostics(
        diagnostics: &[InstalledYamlDataDiagnostic],
    ) -> Option<Vec<InstalledYamlDataRunDiagnostic>> {
        diagnostics
            .iter()
            .map(|diagnostic| {
                let kind = match diagnostic.kind() {
                    InstalledYamlDataDiagnosticKind::CacheUnavailable => {
                        InstalledYamlDataRunDiagnosticKind::CacheUnavailable
                    }
                    InstalledYamlDataDiagnosticKind::Missing => {
                        InstalledYamlDataRunDiagnosticKind::Missing
                    }
                    InstalledYamlDataDiagnosticKind::Read => {
                        InstalledYamlDataRunDiagnosticKind::Read
                    }
                    InstalledYamlDataDiagnosticKind::InvalidUtf8 => {
                        InstalledYamlDataRunDiagnosticKind::InvalidUtf8
                    }
                    InstalledYamlDataDiagnosticKind::Parse => {
                        InstalledYamlDataRunDiagnosticKind::Parse
                    }
                    InstalledYamlDataDiagnosticKind::InvalidSchema => {
                        InstalledYamlDataRunDiagnosticKind::InvalidSchema
                    }
                    InstalledYamlDataDiagnosticKind::IncompatibleSchema => {
                        InstalledYamlDataRunDiagnosticKind::IncompatibleSchema
                    }
                    InstalledYamlDataDiagnosticKind::InvalidRoleData => {
                        InstalledYamlDataRunDiagnosticKind::InvalidRoleData
                    }
                    InstalledYamlDataDiagnosticKind::LocalIgnoreGenerated => {
                        InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated
                    }
                    InstalledYamlDataDiagnosticKind::LocalIgnoreReset => {
                        InstalledYamlDataRunDiagnosticKind::LocalIgnoreReset
                    }
                };
                Some(InstalledYamlDataRunDiagnostic {
                    role: diagnostic.role(),
                    candidate: diagnostic.candidate(),
                    path: diagnostic.path().map(std::path::Path::to_path_buf),
                    kind,
                    message: diagnostic.message().to_string(),
                })
            })
            .collect()
    }
}

/// Terminal result of the final Crash Log Scan Run operation.
#[derive(Debug)]
pub struct RunResult {
    /// Expected lifecycle status for the run as a whole.
    pub status: RunStatus,
    /// Completed discovery data, absent only when discovery did not complete.
    pub discovery: Option<CrashLogScanDiscoveryResult>,
    /// FCX setup data when FCX Mode was enabled.
    pub setup: Option<CrashLogScanSetupResult>,
    /// Installed YAML Data selected after discovery, absent when intake was not reached.
    pub installed_yaml_data: Option<InstalledYamlDataRunData>,
    /// Opaque one-shot continuation present only for Local Ignore Recovery Required.
    pub continuation: Option<CrashLogScanRunContinuation>,
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

    Ok(project_engine_result(engine_result, effective_concurrency))
}

/// Projects the internal terminal state without cloning an opaque continuation.
fn project_engine_result(
    engine_result: EngineRunResult,
    effective_concurrency: Option<usize>,
) -> RunResult {
    let EngineRunResult {
        status,
        discovery,
        setup,
        installed_yaml_data,
        continuation,
        message,
        total,
        succeeded,
        failed,
        cancelled,
        logs,
    } = engine_result;
    let logs: Vec<LogResult> = logs.into_iter().map(LogResult::from).collect();

    RunResult {
        status,
        discovery,
        setup,
        installed_yaml_data,
        continuation,
        effective_concurrency,
        message,
        total,
        succeeded,
        failed,
        cancelled,
        logs,
    }
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
