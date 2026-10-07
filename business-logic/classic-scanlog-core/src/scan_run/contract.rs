//! Final language-neutral Crash Log Scan Run contract.
//!
//! [`execute`] starts the only public execution flow for a complete Crash Log
//! Scan Run. A run paused on Local Ignore recovery offers a [`PendingRecovery`]
//! through [`RunResult::take_pending_recovery`], and [`PendingRecovery::settle`]
//! completes the retained work once, returning a [`SettledRunResult`] that has
//! no continuation. Settling is the only way to answer a paused run: there is
//! no separate resume or abandon entry point and no public continuation
//! (ADR-0009). Discovery, setup, scheduling, durable finalization, cancellation, events,
//! results, and typed infrastructure failures cross this boundary.

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
use classic_file_io_core::FileHashScope;
use classic_shared_core::GameId;
use classic_shared_core::yaml::YamlFileCacheScope;
use classic_version_registry_core::VersionRegistryScope;
use classic_vocabulary::Vocabulary;
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
    fn into_engine_request(
        self,
        cancellation: &Cancellation,
        version_registry: VersionRegistryScope,
        file_hash: FileHashScope,
        yaml_file_cache: YamlFileCacheScope,
    ) -> CrashLogScanRunServiceRequest {
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
            version_registry,
            file_hash,
            yaml_file_cache,
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

    /// Rewraps the engine's view of a run's control so a paused run can keep answering it.
    ///
    /// The engine only ever sees the shared flag, so this is how a continuation built there
    /// retains the *same* control the caller passed to [`execute`] rather than a fresh one: a
    /// cancellation requested on the caller's handle is then visible through
    /// [`PendingRecovery::cancellation_requested`]. A run started without a control gets a new,
    /// uncancelled one, which nothing else can cancel.
    pub(super) fn from_engine_flag(flag: Option<Arc<AtomicBool>>) -> Self {
        flag.map_or_else(Self::new, |requested| Self { requested })
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

impl Vocabulary for LocalIgnoreRecoveryDecision {
    const VARIANTS: &'static [Self] = &[Self::ProceedWithoutIgnore, Self::ResetToDefault];

    /// These tokens are frozen and are the exact strings the inherent `as_str`
    /// this trait method replaced already published.
    ///
    /// This is deliberately *not* a delegating twin of `LocalIgnoreYamlDataState`,
    /// which spells two of its own tokens identically. The two enums answer
    /// different questions — one is a caller's choice, the other is a stored
    /// file's condition — and a shared spelling is not a shared concept.
    fn as_str(self) -> &'static str {
        match self {
            Self::ProceedWithoutIgnore => "proceed_without_ignore",
            Self::ResetToDefault => "reset_to_default",
        }
    }

    /// Title Case here rather than the sentence case most labels in this contract
    /// use, because these two name the decisions themselves, as the glossary does
    /// where it defines a Local Ignore Reset Result in terms of *accepting Reset
    /// To Default*.
    ///
    /// All three interactive frontends already say roughly this and none of them
    /// agree: the TUI writes `Proceed Without Ignore` and `Reset To Default`, the
    /// native CLI writes `Proceed without Ignore` and `Reset to default`, and the
    /// Qt GUI writes `Continue Without Ignore` and `Back Up && Reset to Default`
    /// — which does not use the word *Proceed* at all. Following the glossary
    /// rather than any one frontend is what makes this a decision instead of a
    /// vote.
    fn label(self) -> &'static str {
        match self {
            Self::ProceedWithoutIgnore => "Proceed Without Ignore",
            Self::ResetToDefault => "Reset To Default",
        }
    }
}

/// Stable categories returned when continuation resume cannot complete normally.
///
/// Deliberately outside the Vocabulary naming contract, and the only enum in this
/// contract that is. Every neighbour here carries both a Vocabulary Token and a
/// Display Label; this one carries a token alone because a resume error kind is a
/// stable error *code* rather than a name for something a person reads. Giving it
/// a label would invite a frontend to render `scan_run_continuation_consumed`
/// where a sentence belongs. What a person should read when a resume fails is
/// Display Content composed from the whole error - its kind, its stage, and its
/// path - not a name for the kind on its own.
///
/// Keeping the inherent `as_str` rather than adopting the trait method is part of
/// the same decision: there is no `label` to pair it with.
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
    /// Replacement is visible and recoverable, but namespace durability is unconfirmed.
    LocalIgnoreResetDurabilityUnknown,
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
            Self::LocalIgnoreResetDurabilityUnknown => "local_ignore_reset_durability_unknown",
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

/// Returns the reset failure stage one durable publication stage maps onto.
///
/// The source-to-twin half of the identity mapping. Named rather than inlined
/// into [`project_local_ignore_reset_error`] for the same reason as
/// [`local_ignore_run_state_from_source`]: so the round trip against
/// [`local_ignore_reset_failure_stage_to_source`] can be asserted, and so a
/// stage added to the shared vocabulary later stops this `match` from
/// compiling.
const fn local_ignore_reset_failure_stage_from_source(
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

/// Returns the durable publication stage a reset failure stage mirrors.
///
/// Total, like [`installed_yaml_data_run_diagnostic_kind_to_source`]: this twin
/// is a true identity mapping, so every variant delegates and there is no local
/// vocabulary at all. It stays private because the run contract deliberately
/// does not leak the types it mirrors, and because `LocalIgnoreResetPublicationStage`
/// is a re-export of the shared durable publication stage — handing it to
/// callers would undo the separation this twin exists to keep.
const fn local_ignore_reset_failure_stage_to_source(
    stage: LocalIgnoreResetFailureStage,
) -> LocalIgnoreResetPublicationStage {
    match stage {
        LocalIgnoreResetFailureStage::Create => LocalIgnoreResetPublicationStage::Create,
        LocalIgnoreResetFailureStage::Write => LocalIgnoreResetPublicationStage::Write,
        LocalIgnoreResetFailureStage::Flush => LocalIgnoreResetPublicationStage::Flush,
        LocalIgnoreResetFailureStage::Sync => LocalIgnoreResetPublicationStage::Sync,
        LocalIgnoreResetFailureStage::Publish => LocalIgnoreResetPublicationStage::Publish,
    }
}

impl Vocabulary for LocalIgnoreResetFailureStage {
    const VARIANTS: &'static [Self] = &[
        Self::Create,
        Self::Write,
        Self::Flush,
        Self::Sync,
        Self::Publish,
    ];

    /// Fully delegated. These five strings were byte-identical to the shared
    /// durable publication stage vocabulary — which documents itself as *the*
    /// stage vocabulary for the whole workspace — so restating them here was a
    /// twin contradicting the claim its own source makes. The strings are
    /// unchanged, so nothing a consumer parses moves.
    fn as_str(self) -> &'static str {
        local_ignore_reset_failure_stage_to_source(self).as_str()
    }

    /// Fully delegated on the same split as [`Self::as_str`]. The shared
    /// vocabulary deliberately keeps each label equal to its token, and this
    /// twin inherits that decision rather than making a second one.
    fn label(self) -> &'static str {
        local_ignore_reset_failure_stage_to_source(self).label()
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

/// Recoverable receipt for a visible replacement whose durability barrier failed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LocalIgnoreResetDurabilityUnknownError {
    /// Canonical Local Ignore path containing the complete retained defaults.
    pub path: PathBuf,
    /// Durable byte-exact backup published before replacement.
    pub backup_path: PathBuf,
    /// Identity of the malformed bytes retained by the recovery plan.
    pub malformed_identity: YamlDataContentIdentity,
    /// Identity independently verified from the durable backup bytes.
    pub backup_identity: YamlDataContentIdentity,
    /// Identity of the complete defaults now visible at the canonical path.
    pub replacement_identity: YamlDataContentIdentity,
    /// Human-readable durability diagnostic.
    pub message: String,
}

/// Typed failure returned by [`PendingRecovery::settle`].
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
    /// Reset replacement is visible with a verified backup, but durability is unconfirmed.
    LocalIgnoreResetDurabilityUnknown(Box<LocalIgnoreResetDurabilityUnknownError>),
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
            Self::LocalIgnoreResetDurabilityUnknown(_) => {
                ResumeErrorKind::LocalIgnoreResetDurabilityUnknown
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
            | Self::LocalIgnoreResetReplacementFailure(_)
            | Self::LocalIgnoreResetDurabilityUnknown(_) => None,
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
            Self::LocalIgnoreResetDurabilityUnknown(failure) => {
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
            | Self::LocalIgnoreResetReplacementFailure(_)
            | Self::LocalIgnoreResetDurabilityUnknown(_) => None,
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
    let error = match error {
        LocalIgnoreResetError::ReplacementDurabilityUnknown { receipt, .. } => {
            let receipt = *receipt;
            return ResumeError::LocalIgnoreResetDurabilityUnknown(Box::new(
                LocalIgnoreResetDurabilityUnknownError {
                    path: receipt.path,
                    backup_path: receipt.backup_path,
                    malformed_identity: receipt.malformed_identity,
                    backup_identity: receipt.backup_identity,
                    replacement_identity: receipt.replacement_identity,
                    message,
                },
            ));
        }
        other => other,
    };
    let (replacement_failure, path, stage) = match error {
        LocalIgnoreResetError::DefaultsUnavailable { path, .. }
        | LocalIgnoreResetError::Lock { path, .. }
        | LocalIgnoreResetError::Read { path, .. }
        | LocalIgnoreResetError::BackupDirectory { path, .. }
        | LocalIgnoreResetError::BackupVerification { path, .. } => (false, path, None),
        LocalIgnoreResetError::BackupPublication { path, stage, .. } => (
            false,
            path,
            Some(local_ignore_reset_failure_stage_from_source(stage)),
        ),
        LocalIgnoreResetError::ReplacementPublication { path, stage, .. } => (
            true,
            path,
            Some(local_ignore_reset_failure_stage_from_source(stage)),
        ),
        LocalIgnoreResetError::ReplacementDurabilityUnknown { .. } => {
            unreachable!("durability uncertainty returns before failure projection")
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

/// Opaque, process-local, non-cloneable continuation for one paused scan run.
///
/// Crate-private: the only way to answer a paused run is [`PendingRecovery::settle`], which owns
/// one of these. The separate resume and abandon entry points and the optional continuation field
/// that once exposed it were removed on every surface (ADR-0009).
pub(crate) struct CrashLogScanRunContinuation {
    state: Mutex<Option<PreparedCrashLogScanRunContinuation>>,
    /// The control of the run this continuation paused, which every claim runs under.
    run_cancellation: Cancellation,
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
    ///
    /// `run_cancellation` is the paused run's own control, retained so a [`PendingRecovery`]
    /// can report and settle on it without the caller handing it over a second time.
    pub(super) fn new(
        state: PreparedCrashLogScanRunContinuation,
        run_cancellation: Cancellation,
    ) -> Self {
        Self {
            state: Mutex::new(Some(state)),
            run_cancellation,
        }
    }

    /// Atomically claims this continuation and resumes the retained run once.
    ///
    /// Runs under the paused run's own control. Cancellation is checked after the one-shot claim
    /// but before the recovery plan is consumed, so a cancelled resume returns the normal
    /// cancelled-after-discovery result without analysis. Reset To Default then runs as one
    /// synchronous non-interruptible transaction; cancellation observed after that transaction
    /// returns the same normal cancelled result after preserving its durable backup and
    /// replacement.
    ///
    /// `observer_failure_policy` decides whether a failed observer delivery cancels the resumed
    /// run; the result reports the first failed delivery either way.
    ///
    /// # Errors
    ///
    /// Returns [`ResumeError::ContinuationConsumed`] for sequential or concurrent replay, a typed
    /// Local Ignore reset conflict/backup/replacement failure, or [`ResumeError::Infrastructure`]
    /// when the resumed run cannot produce a terminal result.
    async fn resume(
        &self,
        decision: LocalIgnoreRecoveryDecision,
        observer: Option<&mut dyn Observer>,
        observer_failure_policy: ObserverFailurePolicy,
    ) -> Result<RunResult, ResumeError> {
        let cancellation = &self.run_cancellation;
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
                            observer_delivery_failure: None,
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
                                observer_delivery_failure: None,
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
            // Cancellation won the race, but the reset transaction had already completed: the
            // malformed `CLASSIC Ignore.yaml` is replaced on disk and its byte-exact backup exists.
            // Carry the reset receipt into the cancelled result so frontends can still tell the
            // user what changed and where the backup went. Reporting a bare cancellation here read
            // as "nothing happened", which is the opposite of the truth and leaves the backup path
            // — the only pointer back to the user's original bytes — unreported.
            let mut cancelled = EngineRunResult::cancelled_after_discovery(prepared.discovery);
            cancelled.installed_yaml_data = Some(installed_yaml_data);
            return Ok(project_engine_result(cancelled, None));
        }

        let mut effective_concurrency = None;
        let mut dispatch = ObserverDispatch::new(observer, observer_failure_policy, cancellation);
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
                    dispatch.emit(Event::EffectiveConcurrencySelected {
                        effective_concurrency: value,
                    });
                }
                CrashLogScanRunServiceEvent::Log(event) => {
                    if let Some(event) = translate_engine_event(event) {
                        dispatch.emit(event);
                    }
                }
            },
        )
        .await;
        let observer_delivery_failure = dispatch.into_failure();
        let engine_result = engine_result.map_err(|error| {
            ResumeError::Infrastructure(InfrastructureError {
                observer_delivery_failure: observer_delivery_failure.clone(),
                ..InfrastructureError::from_service(error)
            })
        })?;

        let mut result = project_engine_result(engine_result, effective_concurrency);
        result.observer_delivery_failure = observer_delivery_failure;
        Ok(result)
    }

    /// Abandons this paused Crash Log Scan Run without performing any recovery.
    ///
    /// Requests cancellation on the run's own control, then claims the continuation with a
    /// decision the run never acts on. [`Self::resume`] inspects cancellation immediately after
    /// the one-shot claim and before the retained recovery plan is consumed, so neither Proceed
    /// Without Ignore nor Reset To Default is ever applied: no backup is taken, nothing is
    /// published, and the malformed Local Ignore file is left exactly as it was. The caller
    /// receives the ordinary post-discovery [`RunStatus::Cancelled`] result, and the continuation
    /// is spent, so any later claim reports [`ResumeError::ContinuationConsumed`].
    ///
    /// [`LocalIgnoreRecoveryDecision`] deliberately carries no abandonment variant — adding one
    /// reshapes a type crossing five binding surfaces — so this operation encapsulates the
    /// cancel-then-resume-with-a-placeholder sequence. The placeholder is `ProceedWithoutIgnore`
    /// rather than `ResetToDefault` purely defensively: the decision is unreachable, and if that
    /// ever stopped being true, the non-durable variant is the one that cannot touch the user's
    /// files.
    ///
    /// The run's control stays cancelled afterwards. That is intended: abandoning the run *is*
    /// cancelling it. The request is made *before* the claim is attempted, so a call that goes on
    /// to report a consumed continuation has still cancelled the control. That is inert for the
    /// intended use — the control belongs to the run this continuation came from, and that run
    /// has already finished — but a caller that reuses one control across runs would be
    /// cancelling the wrong one, which it would be doing at [`Self::resume`] too.
    ///
    /// # Errors
    ///
    /// Returns [`ResumeError::ContinuationConsumed`] when this continuation was already claimed,
    /// sequentially or concurrently. The recovery-plan and infrastructure failures
    /// [`Self::resume`] can report are unreachable here, because cancellation short-circuits ahead
    /// of every stage that produces them.
    async fn abandon(&self, observer: Option<&mut dyn Observer>) -> Result<RunResult, ResumeError> {
        self.run_cancellation.cancel();
        // The policy is moot: cancellation short-circuits resume before any event is delivered.
        self.resume(
            LocalIgnoreRecoveryDecision::ProceedWithoutIgnore,
            observer,
            ObserverFailurePolicy::ContinueRun,
        )
        .await
    }
}

/// A Crash Log Scan Run paused on a malformed Local Ignore, waiting to be settled exactly once.
///
/// Taken from a [`RunResult`] with [`RunResult::take_pending_recovery`]. It bundles the run's
/// single-use, crate-private continuation, the run's own [`Cancellation`] control, and the
/// typed recovery facts a prompt is rendered from. It exists only for a run that paused, so a
/// recovery status without a continuation to answer it cannot be represented here.
///
/// The recovery prompt itself is not here. It is Display Content, which the
/// `classic-scan-presentation` crate owns, and this crate must never depend on that one; that
/// crate bundles this value with its rendered prompt for every adapter.
///
/// [`Self::settle`] borrows rather than consumes, so an adapter can share one pending recovery
/// across threads and a replay still reports the typed [`ResumeError::ContinuationConsumed`]
/// rather than becoming impossible to express on a binding surface.
pub struct PendingRecovery {
    continuation: CrashLogScanRunContinuation,
    installed_yaml_data: InstalledYamlDataRunData,
}

impl fmt::Debug for PendingRecovery {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("PendingRecovery")
            .field("continuation", &self.continuation)
            .field("cancellation_requested", &self.cancellation_requested())
            .finish_non_exhaustive()
    }
}

impl PendingRecovery {
    /// Returns whether cancellation of the paused run was already requested.
    ///
    /// Read live from the run's own control, so a cancellation requested on the handle the
    /// caller gave [`execute`] — before or after the run paused — is visible here. When this is
    /// `true` a frontend must not prompt: every settlement now finishes cancelled after discovery
    /// with no filesystem work, so the honest move is to settle with no decision.
    #[must_use]
    pub fn cancellation_requested(&self) -> bool {
        self.continuation.run_cancellation.is_cancelled()
    }

    /// Returns the paused run's own cancellation control.
    ///
    /// The same control the caller passed to [`execute`]. An adapter whose observer can fail
    /// needs it to request safe cancellation of the settled run.
    #[must_use]
    pub const fn cancellation(&self) -> &Cancellation {
        &self.continuation.run_cancellation
    }

    /// Returns the Installed YAML Data facts the recovery prompt is rendered from.
    ///
    /// Its `local_ignore_reset_available` decides whether Reset To Default can be offered.
    #[must_use]
    pub const fn installed_yaml_data(&self) -> &InstalledYamlDataRunData {
        &self.installed_yaml_data
    }

    /// Settles the paused run once, with a Local Ignore Recovery Decision or with none.
    ///
    /// `Some(decision)` resumes the same discovered Crash Logs without rediscovery, with Reset To
    /// Default still one non-interruptible transaction. `None` abandons the run: it cancels the run's own control,
    /// then finishes as cancelled after discovery with no filesystem work. That is the one
    /// abandonment operation, not a third decision. If cancellation was already requested,
    /// either form finishes cancelled after discovery.
    ///
    /// The result is a [`SettledRunResult`], which has no continuation, so a settled run can
    /// never ask for a second recovery.
    ///
    /// `observer_failure_policy` decides whether a failed observer delivery cancels the settled
    /// run, exactly as it does for [`execute`]; the result reports the first failed delivery
    /// either way.
    ///
    /// # Errors
    ///
    /// Returns [`ResumeError::ContinuationConsumed`] when this pending recovery was already
    /// settled, sequentially or concurrently; a typed Local Ignore reset conflict or failure for
    /// Reset To Default; or [`ResumeError::Infrastructure`] when the resumed run cannot produce a
    /// terminal result.
    pub async fn settle(
        &self,
        decision: Option<LocalIgnoreRecoveryDecision>,
        observer: Option<&mut dyn Observer>,
        observer_failure_policy: ObserverFailurePolicy,
    ) -> Result<SettledRunResult, ResumeError> {
        let result = match decision {
            Some(decision) => {
                self.continuation
                    .resume(decision, observer, observer_failure_policy)
                    .await?
            }
            None => self.continuation.abandon(observer).await?,
        };
        SettledRunResult::from_resumed(result)
    }
}

/// Terminal result of settling a [`PendingRecovery`].
///
/// The fields mirror [`RunResult`] minus its continuation. Leaving that field out is the whole
/// point: a settled run cannot carry a continuation, so a second recovery request is
/// unrepresentable rather than an invariant each adapter has to check.
///
/// ```compile_fail
/// # use classic_scanlog_core::scan_run::contract::SettledRunResult;
/// # let settled: SettledRunResult = unimplemented!();
/// let _ = settled.continuation;
/// ```
///
/// ```compile_fail
/// # use classic_scanlog_core::scan_run::contract::SettledRunResult;
/// # let mut settled: SettledRunResult = unimplemented!();
/// let _ = settled.take_pending_recovery();
/// ```
#[derive(Debug)]
pub struct SettledRunResult {
    /// Expected lifecycle status for the settled run as a whole.
    pub status: RunStatus,
    /// The discovery completed before the run paused, never rediscovered.
    pub discovery: Option<CrashLogScanDiscoveryResult>,
    /// FCX setup data when FCX Mode was enabled.
    pub setup: Option<CrashLogScanSetupResult>,
    /// Installed YAML Data the settled run used, absent when settling cancelled before intake.
    pub installed_yaml_data: Option<InstalledYamlDataRunData>,
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
    /// First observer delivery failure while settling, if any; reported under every policy.
    pub observer_delivery_failure: Option<ObserverDeliveryFailure>,
}

impl SettledRunResult {
    /// Drops the continuation slot of a resumed run, which resume never fills.
    ///
    /// A resumed run reaches only terminal engine constructors, none of which retain a
    /// continuation. Should that ever stop being true, this reports an internal invariant
    /// failure instead of silently discarding a second recovery request.
    fn from_resumed(result: RunResult) -> Result<Self, ResumeError> {
        let RunResult {
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
            observer_delivery_failure,
        } = result;
        if continuation.is_some() {
            return Err(ResumeError::Infrastructure(InfrastructureError {
                stage: InfrastructureErrorStage::InternalInvariant,
                message: "a settled Crash Log Scan Run requested a second recovery".to_string(),
                path: None,
                observer_delivery_failure,
            }));
        }
        Ok(Self {
            status,
            discovery,
            setup,
            installed_yaml_data,
            effective_concurrency,
            message,
            total,
            succeeded,
            failed,
            cancelled,
            logs,
            observer_delivery_failure,
        })
    }
}

/// Widens a settled result back into the run result shape, with no continuation.
///
/// For adapters whose result projection, Display Content rendering, and DTOs are written once
/// against [`RunResult`]: the settled value converts losslessly, and the continuation slot is
/// always `None`.
impl From<SettledRunResult> for RunResult {
    fn from(value: SettledRunResult) -> Self {
        let SettledRunResult {
            status,
            discovery,
            setup,
            installed_yaml_data,
            effective_concurrency,
            message,
            total,
            succeeded,
            failed,
            cancelled,
            logs,
            observer_delivery_failure,
        } = value;
        Self {
            status,
            discovery,
            setup,
            installed_yaml_data,
            continuation: None,
            effective_concurrency,
            message,
            total,
            succeeded,
            failed,
            cancelled,
            logs,
            observer_delivery_failure,
        }
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

/// Observer for serialized Crash Log Scan Run events whose delivery can fail.
///
/// An observer reports that it could not take an event (its progress view went away, its
/// channel closed, its callback threw) by returning [`ObserverDeliveryFailure`]. What that
/// failure does to the run is not the observer's call: it is the [`ObserverFailurePolicy`] the
/// caller chose at execution or settling time. Once one delivery has failed, Rust delivers no
/// further events to that observer, and the run's result reports the first failure.
///
/// An observer that wants to stop the run for any other reason still requests that through
/// [`Cancellation`] rather than by failing a delivery.
pub trait Observer: Send {
    /// Observes one event.
    ///
    /// # Errors
    ///
    /// Returns [`ObserverDeliveryFailure`] when the event could not be delivered.
    fn on_event(&mut self, event: Event) -> Result<(), ObserverDeliveryFailure>;
}

/// What an observer closure may return: nothing (it always delivers) or a delivery outcome.
///
/// This lets a plain `|event| { ... }` closure stay an observer that never fails, while a closure
/// returning `Result<(), ObserverDeliveryFailure>` can report a failed delivery.
pub trait ObserverDelivery {
    /// Converts the closure's return value into a delivery outcome.
    ///
    /// # Errors
    ///
    /// Returns the [`ObserverDeliveryFailure`] the closure reported.
    fn into_delivery(self) -> Result<(), ObserverDeliveryFailure>;
}

impl ObserverDelivery for () {
    fn into_delivery(self) -> Result<(), ObserverDeliveryFailure> {
        Ok(())
    }
}

impl ObserverDelivery for Result<(), ObserverDeliveryFailure> {
    fn into_delivery(self) -> Result<(), ObserverDeliveryFailure> {
        self
    }
}

impl<F, R> Observer for F
where
    F: FnMut(Event) -> R + Send,
    R: ObserverDelivery,
{
    fn on_event(&mut self, event: Event) -> Result<(), ObserverDeliveryFailure> {
        self(event).into_delivery()
    }
}

/// An observer's report that it could not deliver one event.
///
/// Run results, settled results, and infrastructure errors carry the first one a run saw, so
/// adapters read "delivery failed" from the result instead of tracking it themselves.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ObserverDeliveryFailure {
    /// Adapter-supplied diagnostic, such as the message of the exception a callback threw.
    pub message: String,
}

impl ObserverDeliveryFailure {
    /// Creates a delivery failure carrying `message`.
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl fmt::Display for ObserverDeliveryFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl std::error::Error for ObserverDeliveryFailure {}

/// Whether a failed observer delivery cancels the run, chosen by the caller of [`execute`] and
/// [`PendingRecovery::settle`].
///
/// Either way the result reports the failure and no further events reach that observer.
/// Independently of this policy, a delivery failure before a run pauses for Local Ignore
/// recovery makes Rust abandon that recovery, because the frontend that would answer it has
/// already lost its view of the run.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ObserverFailurePolicy {
    /// Keep running to a normal terminal result.
    ContinueRun,
    /// Request cancellation on the run's own control at the first failed delivery.
    CancelRun,
}

/// Delivers events to an optional observer under one [`ObserverFailurePolicy`].
///
/// Owns the "first failure wins, then stop delivering" rule so execution and settling cannot
/// drift apart on it.
struct ObserverDispatch<'observer, 'control> {
    observer: Option<&'observer mut dyn Observer>,
    policy: ObserverFailurePolicy,
    cancellation: &'control Cancellation,
    failure: Option<ObserverDeliveryFailure>,
}

impl<'observer, 'control> ObserverDispatch<'observer, 'control> {
    fn new(
        observer: Option<&'observer mut dyn Observer>,
        policy: ObserverFailurePolicy,
        cancellation: &'control Cancellation,
    ) -> Self {
        Self {
            observer,
            policy,
            cancellation,
            failure: None,
        }
    }

    /// Delivers `event` unless the observer is absent or has already failed.
    fn emit(&mut self, event: Event) {
        if self.failure.is_some() {
            return;
        }
        let Some(observer) = self.observer.as_deref_mut() else {
            return;
        };
        if let Err(failure) = observer.on_event(event) {
            self.failure = Some(failure);
            if self.policy == ObserverFailurePolicy::CancelRun {
                self.cancellation.cancel();
            }
        }
    }

    /// Returns the first delivery failure, if any.
    fn into_failure(self) -> Option<ObserverDeliveryFailure> {
        self.failure
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

impl Vocabulary for LogDisposition {
    const VARIANTS: &'static [Self] = &[Self::Succeeded, Self::Failed, Self::CancelledBeforeStart];

    /// These tokens are frozen. They are the exact strings this contract has
    /// always returned from its inherent `as_str`, and which the Python scan-run
    /// binding separately wrote out a second time — so respelling one here
    /// breaks every binding consumer at once.
    fn as_str(self) -> &'static str {
        match self {
            Self::Succeeded => "succeeded",
            Self::Failed => "failed",
            Self::CancelledBeforeStart => "cancelled_before_start",
        }
    }

    /// Settles nothing, which is the point: the CLI, the GUI, and the TUI
    /// already render exactly these three phrases for a terminal disposition, so
    /// adopting them moves agreed wording to one home without changing shipped
    /// output. Only `CancelledBeforeStart` differs from its token, and only by
    /// the word separator.
    fn label(self) -> &'static str {
        match self {
            Self::Succeeded => "succeeded",
            Self::Failed => "failed",
            Self::CancelledBeforeStart => "cancelled before start",
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

impl Vocabulary for LogFailureStage {
    const VARIANTS: &'static [Self] = &[
        Self::Analysis,
        Self::ReportWrite,
        Self::UnsolvedLogsFinalization,
    ];

    /// These tokens are frozen. They are the exact strings this contract has
    /// always returned, and which the Python scan-run binding separately wrote
    /// out a second time.
    fn as_str(self) -> &'static str {
        match self {
            Self::Analysis => "analysis",
            Self::ReportWrite => "report_write",
            Self::UnsolvedLogsFinalization => "unsolved_logs_finalization",
        }
    }

    /// All three frontends already render exactly these phrases, so no wording
    /// is settled here. `UnsolvedLogsFinalization` is the one that could not
    /// have been derived from its token: `Unsolved Logs` is a domain term and
    /// keeps its glossary capitalization, which no mechanical transform of
    /// `unsolved_logs_finalization` could know to apply.
    fn label(self) -> &'static str {
        match self {
            Self::Analysis => "analysis",
            Self::ReportWrite => "report write",
            Self::UnsolvedLogsFinalization => "Unsolved Logs finalization",
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

/// The Vocabulary Token for the one run state with no configuration counterpart.
const RECOVERY_REQUIRED_TOKEN: &str = "recovery_required";

/// The Display Label for that same state.
///
/// Both C++ frontends and the TUI already render exactly this wording, so unlike
/// the delegated variants it settles no divergence — it only moves an agreed
/// string to the place the other four now come from.
const RECOVERY_REQUIRED_LABEL: &str = "recovery required";

/// Returns the run state one configuration state maps onto.
///
/// The source-to-twin half of the near-identity mapping, named rather than
/// inlined into [`InstalledYamlDataRunData::from_snapshot`] so that the round
/// trip against [`local_ignore_run_state_to_source`] can be asserted. Adding a
/// configuration variant stops this `match` from compiling, which is where a
/// contributor is told the twin needs extending.
const fn local_ignore_run_state_from_source(
    state: LocalIgnoreYamlDataState,
) -> LocalIgnoreRunState {
    match state {
        LocalIgnoreYamlDataState::Existing => LocalIgnoreRunState::Existing,
        LocalIgnoreYamlDataState::Generated => LocalIgnoreRunState::Generated,
        LocalIgnoreYamlDataState::ProceedWithoutIgnore => LocalIgnoreRunState::ProceedWithoutIgnore,
        LocalIgnoreYamlDataState::ResetToDefault => LocalIgnoreRunState::ResetToDefault,
    }
}

/// Returns the configuration state a run state mirrors, if there is one.
///
/// This is the twin-to-source half of the near-identity mapping whose
/// source-to-twin half is inlined in [`InstalledYamlDataRunData::from_snapshot`].
/// The two halves are written separately because Rust cannot invert a `match`,
/// and they are pinned against each other by a round-trip test rather than by
/// review.
///
/// It stays private: the run contract deliberately does not leak configuration
/// types, and exposing this would hand callers the very type the twin exists to
/// keep out of the contract.
const fn local_ignore_run_state_to_source(
    state: LocalIgnoreRunState,
) -> Option<LocalIgnoreYamlDataState> {
    match state {
        LocalIgnoreRunState::Existing => Some(LocalIgnoreYamlDataState::Existing),
        LocalIgnoreRunState::Generated => Some(LocalIgnoreYamlDataState::Generated),
        // A run can pause for a caller decision; a stored snapshot cannot, so
        // the configuration enum has nothing to delegate to here.
        LocalIgnoreRunState::RecoveryRequired => None,
        LocalIgnoreRunState::ProceedWithoutIgnore => {
            Some(LocalIgnoreYamlDataState::ProceedWithoutIgnore)
        }
        LocalIgnoreRunState::ResetToDefault => Some(LocalIgnoreYamlDataState::ResetToDefault),
    }
}

impl Vocabulary for LocalIgnoreRunState {
    const VARIANTS: &'static [Self] = &[
        Self::Existing,
        Self::Generated,
        Self::RecoveryRequired,
        Self::ProceedWithoutIgnore,
        Self::ResetToDefault,
    ];

    /// Delegated for the four variants the configuration enum also has, so the
    /// frozen tokens keep exactly one definition site. The strings are the ones
    /// this contract already published, so nothing a consumer parses moves.
    ///
    /// Adding a variant to this enum stops `local_ignore_run_state_to_source` from
    /// compiling, which is where a contributor must decide between delegating
    /// and owning. Answering `None` without also declaring the variant as
    /// locally owned collapses it onto `recovery_required`, which the
    /// conformance assertion rejects twice over — as a duplicate token, and as
    /// an undeclared locally owned variant.
    fn as_str(self) -> &'static str {
        match local_ignore_run_state_to_source(self) {
            Some(source) => source.as_str(),
            None => RECOVERY_REQUIRED_TOKEN,
        }
    }

    /// Delegated on the same split as [`Self::as_str`]. This is where
    /// delegation earns its keep: `Generated` reads as `generated from selected
    /// Main defaults` here because the configuration crate settled that wording,
    /// and a twin that restated its labels would have had to be told.
    fn label(self) -> &'static str {
        match local_ignore_run_state_to_source(self) {
            Some(source) => source.label(),
            None => RECOVERY_REQUIRED_LABEL,
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

/// Returns the run diagnostic kind one configuration diagnostic kind maps onto.
///
/// The source-to-twin half of the mapping, named rather than inlined into
/// [`InstalledYamlDataRunData::map_diagnostics`] for the same reason as
/// [`local_ignore_run_state_from_source`]: so the round trip against its
/// inverse can be asserted, and so a configuration variant added later stops
/// this `match` from compiling.
const fn installed_yaml_data_run_diagnostic_kind_from_source(
    kind: InstalledYamlDataDiagnosticKind,
) -> InstalledYamlDataRunDiagnosticKind {
    match kind {
        InstalledYamlDataDiagnosticKind::CacheUnavailable => {
            InstalledYamlDataRunDiagnosticKind::CacheUnavailable
        }
        InstalledYamlDataDiagnosticKind::Missing => InstalledYamlDataRunDiagnosticKind::Missing,
        InstalledYamlDataDiagnosticKind::Read => InstalledYamlDataRunDiagnosticKind::Read,
        InstalledYamlDataDiagnosticKind::InvalidUtf8 => {
            InstalledYamlDataRunDiagnosticKind::InvalidUtf8
        }
        InstalledYamlDataDiagnosticKind::Parse => InstalledYamlDataRunDiagnosticKind::Parse,
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
    }
}

/// Returns the configuration diagnostic kind a run diagnostic kind mirrors.
///
/// Total, unlike [`local_ignore_run_state_to_source`]: this twin is a true identity
/// mapping, so every variant delegates and there is no local vocabulary at all.
/// It is the twin-to-source half of the mapping whose source-to-twin half is
/// inlined in [`InstalledYamlDataRunData::map_diagnostics`], and is private for
/// the same reason — the run contract does not leak configuration types.
const fn installed_yaml_data_run_diagnostic_kind_to_source(
    kind: InstalledYamlDataRunDiagnosticKind,
) -> InstalledYamlDataDiagnosticKind {
    match kind {
        InstalledYamlDataRunDiagnosticKind::CacheUnavailable => {
            InstalledYamlDataDiagnosticKind::CacheUnavailable
        }
        InstalledYamlDataRunDiagnosticKind::Missing => InstalledYamlDataDiagnosticKind::Missing,
        InstalledYamlDataRunDiagnosticKind::Read => InstalledYamlDataDiagnosticKind::Read,
        InstalledYamlDataRunDiagnosticKind::InvalidUtf8 => {
            InstalledYamlDataDiagnosticKind::InvalidUtf8
        }
        InstalledYamlDataRunDiagnosticKind::Parse => InstalledYamlDataDiagnosticKind::Parse,
        InstalledYamlDataRunDiagnosticKind::InvalidSchema => {
            InstalledYamlDataDiagnosticKind::InvalidSchema
        }
        InstalledYamlDataRunDiagnosticKind::IncompatibleSchema => {
            InstalledYamlDataDiagnosticKind::IncompatibleSchema
        }
        InstalledYamlDataRunDiagnosticKind::InvalidRoleData => {
            InstalledYamlDataDiagnosticKind::InvalidRoleData
        }
        InstalledYamlDataRunDiagnosticKind::LocalIgnoreGenerated => {
            InstalledYamlDataDiagnosticKind::LocalIgnoreGenerated
        }
        InstalledYamlDataRunDiagnosticKind::LocalIgnoreReset => {
            InstalledYamlDataDiagnosticKind::LocalIgnoreReset
        }
    }
}

impl Vocabulary for InstalledYamlDataRunDiagnosticKind {
    const VARIANTS: &'static [Self] = &[
        Self::CacheUnavailable,
        Self::Missing,
        Self::Read,
        Self::InvalidUtf8,
        Self::Parse,
        Self::InvalidSchema,
        Self::IncompatibleSchema,
        Self::InvalidRoleData,
        Self::LocalIgnoreGenerated,
        Self::LocalIgnoreReset,
    ];

    /// Fully delegated. Before this, three binding surfaces each wrote these ten
    /// tokens out; the strings are unchanged, so nothing a consumer parses moves.
    fn as_str(self) -> &'static str {
        installed_yaml_data_run_diagnostic_kind_to_source(self).as_str()
    }

    /// Fully delegated, which is what carries the settled wording into the run
    /// contract for free: `Parse` reads as `parse failure` and `Read` as `read
    /// failure` here because the configuration crate decided so.
    fn label(self) -> &'static str {
        installed_yaml_data_run_diagnostic_kind_to_source(self).label()
    }
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
    /// Whether Reset To Default can succeed for this run's recovery decision.
    ///
    /// Meaningful only while `local_ignore_state` is
    /// [`LocalIgnoreRunState::RecoveryRequired`]; `false` in every other state, where no
    /// recovery decision is pending.
    ///
    /// Config Core deliberately builds a recovery plan even when the selected Main YAML has a
    /// missing, malformed, or unusable `CLASSIC_Info.default_ignorefile`, because Proceed Without
    /// Ignore still works without defaults. Reset To Default does not. Without this fact projected
    /// here, every frontend offered both choices unconditionally, and picking Reset consumed the
    /// one-shot continuation only to fail — leaving the user with no scan, no repair, and no
    /// second attempt.
    pub local_ignore_reset_available: bool,
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
        let local_ignore_state = local_ignore_run_state_from_source(snapshot.local_ignore_state());
        let diagnostics = Self::map_diagnostics(snapshot.diagnostics())?;

        Some(Self {
            main: snapshot.main().clone(),
            game_file: snapshot.game_file().clone(),
            local_ignore_state,
            local_ignore_identity: snapshot.local_ignore_identity().clone(),
            diagnostics,
            // No recovery decision is pending on a selected snapshot, so there is nothing to offer.
            local_ignore_reset_available: false,
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
            // `None` here is Config Core's way of saying the plan has no retained defaults to
            // publish, which is exactly when Reset To Default cannot succeed.
            local_ignore_reset_available: plan.default_local_ignore_identity().is_some(),
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
                Some(InstalledYamlDataRunDiagnostic {
                    role: diagnostic.role(),
                    candidate: diagnostic.candidate(),
                    path: diagnostic.path().map(std::path::Path::to_path_buf),
                    kind: installed_yaml_data_run_diagnostic_kind_from_source(diagnostic.kind()),
                    message: diagnostic.message().to_string(),
                })
            })
            .collect()
    }
}

/// Terminal result of the final Crash Log Scan Run operation.
///
/// A run paused on Local Ignore recovery retains its continuation privately; the only way to
/// reach it is [`Self::take_pending_recovery`]. There is no public continuation field, so no
/// adapter can claim the continuation outside [`PendingRecovery::settle`] (ADR-0009).
///
/// ```compile_fail
/// # use classic_scanlog_core::scan_run::contract::RunResult;
/// # let result: RunResult = unimplemented!();
/// let _ = result.continuation;
/// ```
///
/// Values outside this crate are built from a [`SettledRunResult`], which converts losslessly
/// and never carries a continuation.
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
    /// First observer delivery failure of this run, if any; reported under every policy.
    pub observer_delivery_failure: Option<ObserverDeliveryFailure>,
    /// Opaque one-shot continuation present only for Local Ignore Recovery Required.
    ///
    /// Private on purpose; [`Self::take_pending_recovery`] is the one way out.
    continuation: Option<CrashLogScanRunContinuation>,
}

impl RunResult {
    /// Takes the pending recovery a paused run offers, leaving none behind.
    ///
    /// Returns `Some` exactly when this result retains a continuation, which only a run paused
    /// on Local Ignore recovery does. The rest of the result stays readable, so an adapter can
    /// still render the paused run after taking its pending recovery. Taking it twice returns
    /// `None` the second time.
    pub fn take_pending_recovery(&mut self) -> Option<PendingRecovery> {
        // Facts first, so a result that somehow lacks them keeps its continuation rather than
        // losing it to a half-built pending recovery.
        let installed_yaml_data = self
            .continuation
            .as_ref()
            .and(self.installed_yaml_data.clone())?;
        let continuation = self.continuation.take()?;
        Some(PendingRecovery {
            continuation,
            installed_yaml_data,
        })
    }
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

impl Vocabulary for InfrastructureErrorStage {
    const VARIANTS: &'static [Self] = &[
        Self::RequestValidation,
        Self::Discovery,
        Self::Intake,
        Self::FormIdDatabaseAccess,
        Self::Initialization,
        Self::InternalInvariant,
    ];

    /// These tokens are frozen. `formid_database_access` in particular is the
    /// published spelling rather than the `form_id_database_access` a mechanical
    /// snake_case of the variant name would produce, which is why this contract
    /// writes the strings out instead of deriving them.
    ///
    /// [`fmt::Display`] renders this form, so it is also the stage that appears
    /// inside a rendered [`InfrastructureError`] message.
    fn as_str(self) -> &'static str {
        match self {
            Self::RequestValidation => "request_validation",
            Self::Discovery => "discovery",
            Self::Intake => "intake",
            Self::FormIdDatabaseAccess => "formid_database_access",
            Self::Initialization => "initialization",
            Self::InternalInvariant => "internal_invariant",
        }
    }

    /// The wording the CLI and the GUI already render. Two labels are more than
    /// a respelling of their token and could not have been derived from one:
    /// `FormIdDatabaseAccess` capitalizes `FormID` as the domain term it is, and
    /// `InternalInvariant` reads as `internal invariant validation` because the
    /// bare noun phrase names the thing rather than the failure.
    ///
    /// The TUI renders the *token* here rather than prose, so this is the one
    /// enum in this change where a frontend has something to adopt.
    fn label(self) -> &'static str {
        match self {
            Self::RequestValidation => "request validation",
            Self::Discovery => "discovery",
            Self::Intake => "intake",
            Self::FormIdDatabaseAccess => "FormID database access",
            Self::Initialization => "initialization",
            Self::InternalInvariant => "internal invariant validation",
        }
    }
}

impl fmt::Display for InfrastructureErrorStage {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(Vocabulary::as_str(*self))
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
    /// First observer delivery failure the run saw before failing, if any.
    pub observer_delivery_failure: Option<ObserverDeliveryFailure>,
}

impl InfrastructureError {
    fn request_validation(message: impl Into<String>, path: Option<PathBuf>) -> Self {
        Self {
            stage: InfrastructureErrorStage::RequestValidation,
            message: message.into(),
            path,
            observer_delivery_failure: None,
        }
    }

    /// Preserves the exact stage and path captured at the failing lifecycle boundary.
    fn from_service(error: CrashLogScanRunServiceError) -> Self {
        Self {
            stage: error.stage,
            message: error.message,
            path: error.path,
            observer_delivery_failure: None,
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
/// `observer_failure_policy` decides whether a failed observer delivery
/// cancels the run; the result (or error) reports the first failed delivery
/// either way. A delivery failure before the run pauses for Local Ignore
/// recovery abandons that recovery, so such a run finishes cancelled after
/// discovery with no pending recovery and no filesystem work.
///
/// # Errors
///
/// Returns a typed [`InfrastructureError`] when the run cannot produce a
/// meaningful terminal result. Expected lifecycle states remain in [`RunResult`].
pub async fn execute(
    request: Request,
    cancellation: &Cancellation,
    observer: Option<&mut dyn Observer>,
    observer_failure_policy: ObserverFailurePolicy,
) -> Result<RunResult, InfrastructureError> {
    execute_in_version_registry_scope(
        request,
        VersionRegistryScope::default_scope(),
        cancellation,
        observer,
        observer_failure_policy,
    )
    .await
}

/// Executes one Crash Log Scan Run like [`execute`], reading Version Registry
/// metadata only from `version_registry`.
///
/// Every registry-backed stage of the run reads that scope: Standard XSE
/// Folder discovery, FCX setup, Installed YAML Data metadata, analysis
/// configuration, and per-log analysis. A pending recovery returned for Local
/// Ignore recovery keeps the scope, so [`PendingRecovery::settle`] reads it
/// too. No other snapshot, including the process default, is read.
/// This lets a binding facade keep its own snapshot. FCX setup still hashes
/// through the process default [`FileHashScope`], and Standard discovery reads
/// the Game Local document through the process default [`YamlFileCacheScope`];
/// use [`execute_in_scopes`] to choose those scopes as well.
///
/// # Errors
///
/// Same as [`execute`].
pub async fn execute_in_version_registry_scope(
    request: Request,
    version_registry: VersionRegistryScope,
    cancellation: &Cancellation,
    observer: Option<&mut dyn Observer>,
    observer_failure_policy: ObserverFailurePolicy,
) -> Result<RunResult, InfrastructureError> {
    execute_in_scopes(
        request,
        version_registry,
        FileHashScope::default_scope(),
        YamlFileCacheScope::default_scope(),
        cancellation,
        observer,
        observer_failure_policy,
    )
    .await
}

/// Executes one Crash Log Scan Run like [`execute_in_version_registry_scope`],
/// and also hashes only through `file_hash` and reads the Game Local document
/// only through `yaml_file_cache`.
///
/// The FCX Game Setup Intake step hashes the game executable and XSE scripts
/// with [`GameSetupIntake::run_in_scopes`](classic_scangame_core::GameSetupIntake::run_in_scopes),
/// so its cache entries and hit/miss counters land only in `file_hash`. A
/// continuation returned for Local Ignore recovery keeps every scope.
/// Standard discovery reads `CLASSIC <game> Local.yaml` (to derive the XSE
/// Folder) through `yaml_file_cache`, so its path/mtime cache entries and
/// hit/miss counters land only there and no other facade's YAML cache clear
/// can evict them. All handles are opaque and chosen by the caller (a
/// binding facade selects its own at facade entry); unscoped callers use
/// [`execute`], which passes the process defaults.
///
/// # Errors
///
/// Same as [`execute`].
pub async fn execute_in_scopes(
    request: Request,
    version_registry: VersionRegistryScope,
    file_hash: FileHashScope,
    yaml_file_cache: YamlFileCacheScope,
    cancellation: &Cancellation,
    observer: Option<&mut dyn Observer>,
    observer_failure_policy: ObserverFailurePolicy,
) -> Result<RunResult, InfrastructureError> {
    execute_inner(
        request,
        version_registry,
        file_hash,
        yaml_file_cache,
        cancellation,
        observer,
        observer_failure_policy,
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
    observer_failure_policy: ObserverFailurePolicy,
) -> Result<RunResult, InfrastructureError> {
    execute_inner(
        request,
        VersionRegistryScope::default_scope(),
        FileHashScope::default_scope(),
        YamlFileCacheScope::default_scope(),
        cancellation,
        observer,
        observer_failure_policy,
        test_hooks,
    )
    .await
}

/// Shared implementation for the public operation and its request-scoped test harness.
#[allow(clippy::too_many_arguments)]
async fn execute_inner(
    request: Request,
    version_registry: VersionRegistryScope,
    file_hash: FileHashScope,
    yaml_file_cache: YamlFileCacheScope,
    cancellation: &Cancellation,
    observer: Option<&mut dyn Observer>,
    observer_failure_policy: ObserverFailurePolicy,
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

    let engine_request =
        request.into_engine_request(cancellation, version_registry, file_hash, yaml_file_cache);
    #[cfg(test)]
    let engine_request = {
        let mut engine_request = engine_request;
        engine_request.test_hooks = test_hooks;
        engine_request
    };
    let mut effective_concurrency = None;
    let mut dispatch = ObserverDispatch::new(observer, observer_failure_policy, cancellation);
    let engine_result = execute_service(engine_request, |event| match event {
        CrashLogScanRunServiceEvent::DiscoveryCompleted(discovery) => {
            dispatch.emit(Event::DiscoveryCompleted(discovery));
        }
        CrashLogScanRunServiceEvent::EffectiveConcurrencySelected(value) => {
            effective_concurrency = Some(value);
            dispatch.emit(Event::EffectiveConcurrencySelected {
                effective_concurrency: value,
            });
        }
        CrashLogScanRunServiceEvent::Log(event) => {
            if let Some(event) = translate_engine_event(event) {
                dispatch.emit(event);
            }
        }
    })
    .await;
    let observer_delivery_failure = dispatch.into_failure();
    let engine_result = engine_result.map_err(|error| InfrastructureError {
        observer_delivery_failure: observer_delivery_failure.clone(),
        ..InfrastructureError::from_service(error)
    })?;

    let mut result = project_engine_result(engine_result, effective_concurrency);
    result.observer_delivery_failure = observer_delivery_failure;
    if result.observer_delivery_failure.is_some()
        && let Some(continuation) = result.continuation.take()
    {
        return abandon_after_delivery_failure(continuation, result).await;
    }
    Ok(result)
}

/// Abandons a pending recovery whose run already failed to deliver an observer event.
///
/// The frontend that would answer the recovery prompt has lost its view of the run, so leaving
/// the continuation for it risks the continuation being dropped un-abandoned (the GUI did exactly
/// that). Rust settles it without a decision instead: the run's own control is cancelled and the
/// run finishes cancelled after discovery with no filesystem work, under either
/// [`ObserverFailurePolicy`]. `paused` supplies the failure to carry into the cancelled result.
async fn abandon_after_delivery_failure(
    continuation: CrashLogScanRunContinuation,
    paused: RunResult,
) -> Result<RunResult, InfrastructureError> {
    let mut abandoned = continuation
        .abandon(None)
        .await
        .map_err(|error| InfrastructureError {
            // A freshly paused continuation cannot already be claimed, and abandonment
            // short-circuits ahead of every recovery stage, so this is an invariant breach.
            stage: InfrastructureErrorStage::InternalInvariant,
            message: format!(
                "abandoning a pending recovery after observer delivery failed: {error}"
            ),
            path: None,
            observer_delivery_failure: paused.observer_delivery_failure.clone(),
        })?;
    abandoned.observer_delivery_failure = paused.observer_delivery_failure;
    Ok(abandoned)
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
        observer_delivery_failure: None,
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
