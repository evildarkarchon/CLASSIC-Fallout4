//! Final Crash Log Scan Run contract adapter for Node.js and Bun.
//!
//! This module projects invariant-preserving request construction, opaque
//! cancellation, serialized event observation, and exhaustive terminal mapping
//! without recreating any Rust-owned lifecycle behavior.

#[cfg(test)]
#[path = "scan_run_tests.rs"]
mod tests;

use crate::explicit_yaml_data::{JsYamlDataContentIdentity, content_identity_to_js};
use crate::installed_yaml_data::{
    JsInspectedYamlDataFile, JsInstalledYamlDataProvenance, JsInstalledYamlDataRole,
    inspected_file_to_js,
};
use crate::scanlog::JsFcxConfigIssue;
use crate::shared::{JsGameId, js_to_core_game_id};
use classic_scan_presentation::{
    DisplayLine, DisplaySegment, DisplaySeverity, RecoveryPrompt, render_event,
    render_infrastructure_error, render_local_ignore_recovery, render_resume_error,
    render_run_result,
};
use classic_scanlog_core::scan_run::contract;
use classic_scanlog_core::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanFacts,
    CrashLogScanSetupContext, CrashLogScanSetupResult, ScanProgressPhase,
    StandardCrashLogScanSource, StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
use classic_vocabulary::{Vocabulary, display_label, from_token};
use napi::bindgen_prelude::{AsyncTask, Either, FnArgs, Function, JsObjectValue, ToNapiValue};
use napi::threadsafe_function::{
    ThreadsafeFunction, ThreadsafeFunctionCallMode, UnknownReturnValue,
};
use napi::{Env, JsError, JsValue, Status, Task};
use std::path::PathBuf;
use std::sync::{Arc, Mutex, mpsc};

/// JavaScript configuration shared by Standard and Targeted requests.
#[napi(object)]
pub struct JsScanRunConfiguration {
    /// CLASSIC installation root whose Installed YAML Data is selected once for the run.
    pub installation_root: String,
    /// Typed supported game identity.
    pub game: JsGameId,
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

/// Local Ignore states possible for the complete scan-run recovery contract.
// `PartialEq` exists so the Display Label projection can resolve a variant by
// running the forward `local_ignore_run_state_to_js` map over the core
// `VARIANTS` list. A reverse `match` would be a second variant mapping that
// could disagree with the forward one; derived from it, the two cannot.
#[derive(PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsScanRunLocalIgnoreState {
    /// A valid user-owned Local Ignore file already existed in the installation.
    Existing,
    /// Missing Local Ignore YAML Data was generated from selected Main defaults.
    Generated,
    /// Malformed Local Ignore YAML Data requires an explicit caller decision.
    RecoveryRequired,
    /// The retained run resumed with operation-scoped empty ignores.
    ProceedWithoutIgnore,
    /// Malformed Local Ignore was durably reset from retained selected-Main defaults.
    ResetToDefault,
}

/// Explicit Local Ignore recovery decisions owned by Rust scan coordination.
// `Clone`, `Copy`, `Debug`, and `PartialEq` exist for the recovery-prompt tests, which
// compare a projected decision against the twin it should have produced and round-trip
// it back. Same reason `JsScanRunDisplaySeverity` carries them.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsScanRunLocalIgnoreRecoveryDecision {
    /// Resume with an empty ignore list scoped only to the retained run.
    ProceedWithoutIgnore,
    /// Durably reset malformed Local Ignore, then resume the retained run.
    ResetToDefault,
}

/// Opaque process-local carrier for one paused Crash Log Scan Run.
#[napi]
pub struct ScanRunContinuation {
    inner: Arc<contract::CrashLogScanRunContinuation>,
}

/// Stable diagnostic categories emitted by valid-or-generated scan-run intake.
// See `JsScanRunLocalIgnoreState` for why `PartialEq` is derived.
#[derive(PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsScanRunInstalledYamlDataDiagnosticKind {
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
#[napi(object)]
pub struct JsScanRunInstalledYamlDataDiagnostic {
    /// Affected update-eligible role, absent for installation-wide or Local Ignore events.
    pub role: Option<JsInstalledYamlDataRole>,
    /// Rejected candidate provenance, absent when no update-eligible candidate applies.
    pub candidate: Option<JsInstalledYamlDataProvenance>,
    /// Affected path when the diagnostic is path-attributable.
    pub path: Option<String>,
    /// Stable machine-readable scan-run diagnostic category.
    pub kind: JsScanRunInstalledYamlDataDiagnosticKind,
    /// Actionable human-readable explanation.
    pub message: String,
}

/// Installed YAML Data metadata retained from the immutable run snapshot.
#[napi(object, object_from_js = false)]
pub struct JsInstalledYamlDataRunData {
    /// Selected Main YAML Data schema, identity, and provenance.
    pub main: JsInspectedYamlDataFile,
    /// Selected game YAML Data schema, identity, and provenance.
    pub game_file: JsInspectedYamlDataFile,
    /// How Local Ignore YAML Data entered the immutable run snapshot.
    pub local_ignore_state: JsScanRunLocalIgnoreState,
    /// Identity of the exact Local Ignore bytes retained by the run.
    pub local_ignore_identity: JsYamlDataContentIdentity,
    /// Structured fallback, validation, and generation diagnostics.
    pub diagnostics: Vec<JsScanRunInstalledYamlDataDiagnostic>,
    /// Whether Reset To Default can succeed while recovery is required.
    ///
    /// Only meaningful when `localIgnoreState` is `RecoveryRequired`. A recovery plan whose
    /// selected Main YAML has no usable `default_ignorefile` can only satisfy Proceed Without
    /// Ignore; offering Reset anyway spends the one-shot continuation on a certain failure.
    pub local_ignore_reset_available: bool,
    /// Durable reset metadata populated only after successful Reset To Default resume.
    pub local_ignore_reset: Option<JsScanRunLocalIgnoreResetRunData>,
}

/// Durable backup and replacement metadata from successful Reset To Default resume.
#[napi(object, object_from_js = false)]
pub struct JsScanRunLocalIgnoreResetRunData {
    pub local_ignore_path: String,
    pub backup_path: String,
    pub malformed_identity: JsYamlDataContentIdentity,
    pub backup_identity: JsYamlDataContentIdentity,
    pub replacement_identity: JsYamlDataContentIdentity,
}

/// How gravely one Crash Log Scan Run display line should read.
///
/// A consumer maps this onto its own styling. Rust never names a colour, a text
/// attribute, or a widget — a plain, pipeable frontend may map every severity
/// onto nothing at all and still be correct.
///
/// Mirrors `classic_scan_presentation::DisplaySeverity` exhaustively.
// `Debug` and `PartialEq` exist for the flattening tests, which compare a
// projected severity against the twin it should have produced. Same reason
// `JsScanRunLocalIgnoreState` carries `PartialEq`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsScanRunDisplaySeverity {
    /// Neutral fact about the run.
    Info,
    /// Worth noticing, but nothing failed.
    Notice,
    /// Something is wrong or incomplete and may need attention.
    Warning,
    /// Something failed.
    Failure,
    /// Something completed as intended.
    Success,
}

/// Which payload field of a [`JsScanRunDisplaySegment`] carries its value.
///
/// Mirrors the variant set of `classic_scan_presentation::DisplaySegment`. The
/// taxonomy is fixed at six kinds for its first version: each addition touches
/// three binding parity baselines, so growth must be a deliberate decision.
// See `JsScanRunDisplaySeverity` for why the comparison derives are here.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[napi(string_enum)]
pub enum JsScanRunDisplaySegmentKind {
    /// Fixed Rust-owned prose, carried in `text`.
    Text,
    /// A Display Label, carried in `text`.
    Label,
    /// A quantity in `count` beside the noun Rust resolved for it in `text`.
    Count,
    /// A filesystem path, carried in `path`.
    Path,
    /// The name of a domain entity that is not a path, carried in `text`.
    Name,
    /// A value set apart from the prose around it, carried in `text`.
    Emphasis,
}

/// One typed piece of a Crash Log Scan Run display line.
///
/// The six-variant Rust segment crosses flattened: a kind tag plus one field per
/// payload shape, with the fields the kind does not use left empty. Read only the
/// field `kind` selects.
///
/// The flattening is the C++ bridge's, field for field, rather than a
/// Node-idiomatic shape with optional payloads. One flattening across every
/// binding is what lets a wording fix reach all of them without three separate
/// readings of the same segment, and it is what the parity baselines pin.
//
// Bidirectional rather than output-only, because napi requires a nested type to be
// readable from JavaScript when its parent is, and `JsScanRunEvent` and
// `JsScanRunFailure` both are. The alternative — narrowing those two to
// output-only — is the larger change to an existing surface.
//
// Note the consequence, since it is a contract change rather than a pure addition:
// `displayLines` is required, so a JavaScript object literal that used to satisfy
// `JsScanRunEvent` or `JsScanRunFailure` no longer does. Harmless in practice —
// no entry point on this surface accepts either type as an argument; both are only
// ever resolved out of a scan run — but it is why neither was narrowed instead.
#[napi(object)]
pub struct JsScanRunDisplaySegment {
    /// Selects which of the fields below carries this segment's payload.
    pub kind: JsScanRunDisplaySegmentKind,
    /// Payload for `Text`, `Label`, `Name`, and `Emphasis`. For `Count` this is
    /// the noun Rust already resolved to agree with `count`, so no consumer
    /// re-decides pluralization and no user reads "1 logs". Empty for `Path`.
    pub text: String,
    /// Payload for `Path`, whole and untruncated. Truncation is the consumer's
    /// choice. Empty otherwise.
    pub path: String,
    /// Payload for `Count`. Zero otherwise.
    ///
    /// Widened to `i64` for the same reason a log result's processing time is:
    /// JavaScript has no `u64`, and this surface saturates rather than wrapping.
    pub count: i64,
}

/// One line of Crash Log Scan Run Display Content.
///
/// A consumer concatenates `segments` in order and never reorders within a line.
/// It may reorder, group, or omit whole lines. It must not re-derive a Display
/// Label already carried in a `Label` segment, and must not re-decide a
/// `Count`'s noun.
//
// Bidirectional for the same reason as `JsScanRunDisplaySegment` above.
#[napi(object)]
pub struct JsScanRunDisplayLine {
    /// How gravely this line should read.
    pub severity: JsScanRunDisplaySeverity,
    /// The line's content, in reading order.
    pub segments: Vec<JsScanRunDisplaySegment>,
}

/// One Local Ignore recovery decision, named and explained, with its availability
/// attached.
///
/// `available` travels here rather than as a separate flag beside the prompt, which
/// is what makes honouring it take no separate lookup. A consumer must not offer a
/// decision for which it is false: Rust still fails safely and touches nothing on
/// disk, but the attempt spends the one-shot continuation, so the user is left with
/// no scan and no second attempt. Two native frontends made exactly that mistake
/// while the fact lived beside the prompt instead of on the decision.
//
// Output-only, unlike the display types above: its only parent is
// `JsScanRunSuccess`, which is already `object_from_js = false`, so napi needs no
// readable-from-JavaScript form and no consumer-constructible shape is widened.
#[napi(object, object_from_js = false)]
pub struct JsScanRunRecoveryDecisionDescription {
    /// The decision to hand back to `scanRunResume`.
    pub decision: JsScanRunLocalIgnoreRecoveryDecision,
    /// The decision's Display Label.
    pub label: String,
    /// What choosing it will actually do, concatenated in order like any other line.
    pub description: Vec<JsScanRunDisplaySegment>,
    /// Whether this run can honor the decision.
    pub available: bool,
}

/// The Rust-owned content of a Local Ignore recovery prompt.
///
/// `lines` state why the run paused and what is being decided about; `decisions`
/// lists every decision the continuation contract accepts. The affordance beside a
/// description is the consumer's own, as is the order it presents them in and what
/// kind of surface asks the question. The descriptions themselves are not.
///
/// Backing out appears nowhere here. `JsScanRunLocalIgnoreRecoveryDecision` has
/// exactly two variants by design, and abandonment is spelled as the absence of a
/// decision through `scanRunAbandon`.
#[napi(object, object_from_js = false)]
pub struct JsScanRunRecoveryPrompt {
    /// Why the run paused and what is being decided about, in reading order.
    pub lines: Vec<JsScanRunDisplayLine>,
    /// One description per recovery decision, in the contract's variant order.
    pub decisions: Vec<JsScanRunRecoveryDecisionDescription>,
}

/// Complete terminal Crash Log Scan Run result.
#[napi(object, object_from_js = false)]
pub struct JsScanRunResult {
    #[napi(
        ts_type = "'completed' | 'no_crash_logs_found' | 'setup_failed' | 'local_ignore_recovery_required' | 'cancelled_before_discovery' | 'cancelled'"
    )]
    pub status: String,
    pub discovery: Option<JsScanRunDiscoveryResult>,
    pub setup: Option<JsScanRunSetupResult>,
    /// Installed YAML Data selected after discovery, absent when intake was not reached.
    pub installed_yaml_data: Option<JsInstalledYamlDataRunData>,
    /// Opaque one-shot continuation populated only for Local Ignore Recovery Required.
    pub continuation: Option<ScanRunContinuation>,
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
    /// What this event says, in Rust's words.
    ///
    /// Rendered inline in the observer adapter before the event reaches
    /// JavaScript, so a consumer that shows progress states it in the same words
    /// every other frontend does. One event can produce more than one line — a
    /// discovery that rejected some of its targeted inputs states the rejection
    /// separately.
    ///
    /// Unlike the optional fields above, this is never defaulted by `kind`: every
    /// event kind renders. A consumer that shows only some kinds omits whole
    /// lines, which the adapter contract allows.
    pub display_lines: Vec<JsScanRunDisplayLine>,
}

/// Successful final operation envelope with adapter-only observation failure data.
#[napi(object, object_from_js = false)]
pub struct JsScanRunSuccess {
    pub result: JsScanRunResult,
    pub observer_error: Option<String>,
    /// What this run says, in Rust's words.
    ///
    /// Rendered while the Rust run result was still live, because JavaScript
    /// receives a projected copy and cannot render from the Rust value later. A
    /// consumer states the run from these lines rather than composing sentences
    /// of its own; `result` stays the machine-facing surface it matches on.
    ///
    /// `scanRunExecute` and `scanRunResume` resolve the same envelope, so this
    /// one field covers the initial run and the continuation resume alike.
    pub display_lines: Vec<JsScanRunDisplayLine>,
    /// What to ask the user, and which answers this run can honor.
    ///
    /// Present only when `result.status` is `local_ignore_recovery_required`, which
    /// is also exactly when the run retains a continuation to answer with. Absent
    /// rather than empty, because a run with nothing to ask has no prompt rather
    /// than an empty one — and `undefined` is what a JavaScript consumer already
    /// reads as "not present" everywhere else on this surface.
    ///
    /// Rendered here for the reason `displayLines` is: JavaScript receives a
    /// projected copy of the run and cannot render from the Rust value later.
    pub recovery_prompt: Option<JsScanRunRecoveryPrompt>,
}

/// Failed final operation envelope with adapter-only observation failure data.
#[napi(object)]
pub struct JsScanRunFailure {
    pub error: JsScanRunInfrastructureError,
    pub observer_error: Option<String>,
    /// What this failure says, in Rust's words.
    ///
    /// The stage reads as its Display Label here, never as the Vocabulary Token
    /// `error.stage` still publishes. That split is the point: a user should not
    /// have to know that `formid_database_access` means "FormID database access",
    /// and a consumer should never match on the sentence.
    pub display_lines: Vec<JsScanRunDisplayLine>,
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
            Ok(result) => {
                ScanRunTaskOutput::Success(Box::new(success_envelope(result, observer_error)))
            }
            Err(error) => ScanRunTaskOutput::Failure(failure_envelope(error, observer_error)),
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
    // Narrows `JsScanRunEvent` to the payloads each `kind` actually carries, which
    // the flat all-optional struct cannot express. Every member repeats
    // `displayLines` because it is the one field no `kind` defaults away — an
    // event that renders nothing does not exist.
    #[napi(
        ts_arg_type = "(event: { kind: 'discovery_completed'; discovery: JsScanRunDiscoveryResult; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'effective_concurrency_selected'; effectiveConcurrency: number; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'log_queued' | 'log_started'; log: JsScanRunLogEvent; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'log_phase'; log: JsScanRunLogEvent; phase: 'setup' | 'parse' | 'analyze' | 'finalize'; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'log_finished'; log: JsScanRunLogEvent; disposition: 'succeeded' | 'failed' | 'cancelled_before_start'; displayLines: Array<JsScanRunDisplayLine> }) => void"
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

/// Internal continuation-claim output retained until JavaScript-thread resolution.
pub enum ScanRunClaimTaskOutput {
    /// The retained run produced normal terminal result data.
    Success(Box<JsScanRunSuccess>),
    /// The retained run encountered an infrastructure failure.
    Failure(JsScanRunFailure),
    /// Another sequential or concurrent caller already claimed the continuation.
    ContinuationConsumed,
    /// Reset conflict or operational failure rejected with stable structured metadata.
    LocalIgnoreResetError(contract::ResumeError),
}

/// Background task that claims one Rust-owned continuation on the shared runtime.
///
/// Named for the claim rather than for `resume`, because both `scanRunResume` and `scanRunAbandon`
/// run through it and the one-shot claim is what they share. It reaches no TypeScript declaration —
/// both entry points override their return type — so the name costs no baseline row.
pub struct ScanRunClaimTask {
    continuation: Arc<contract::CrashLogScanRunContinuation>,
    /// The recovery decision to claim the continuation with, or `None` to abandon the run.
    ///
    /// Abandonment is modelled as the absence of a decision rather than as a third variant,
    /// because that is what it is: `LocalIgnoreRecoveryDecision` deliberately carries no
    /// abandonment variant, and adding one would reshape a type crossing five binding surfaces.
    /// Sharing one task keeps `scanRunAbandon` and `scanRunResume` on the same observer adapter,
    /// the same envelope builders, and the same rejection routing.
    decision: Option<contract::LocalIgnoreRecoveryDecision>,
    cancellation: contract::Cancellation,
    observer: Option<JsObserverFunction>,
    cancel_on_observer_error: bool,
}

impl Task for ScanRunClaimTask {
    type Output = ScanRunClaimTaskOutput;
    type JsValue = Either<JsScanRunSuccess, JsScanRunFailure>;

    /// Claims the core continuation without constructing another runtime.
    ///
    /// A `None` decision abandons the run through the shared core operation rather than
    /// cancelling here and resuming with a placeholder; that sequence is Rust's to own.
    fn compute(&mut self) -> napi::Result<Self::Output> {
        let observer_error = Arc::new(Mutex::new(None));
        let mut adapter = self.observer.take().map(|callback| JsObserverAdapter {
            callback,
            cancellation: self.cancellation.clone(),
            cancel_on_error: self.cancel_on_observer_error,
            delivery_error: Arc::clone(&observer_error),
            delivery_failed: false,
        });
        let runtime = classic_shared_core::get_runtime();
        let result = match self.decision {
            Some(decision) => runtime.block_on(
                self.continuation.resume(
                    decision,
                    &self.cancellation,
                    adapter
                        .as_mut()
                        .map(|observer| observer as &mut dyn contract::Observer),
                ),
            ),
            None => runtime.block_on(
                self.continuation.abandon(
                    &self.cancellation,
                    adapter
                        .as_mut()
                        .map(|observer| observer as &mut dyn contract::Observer),
                ),
            ),
        };
        let observer_error = observer_error
            .lock()
            .map_err(|_| napi::Error::from_reason("scan-run observer error state was poisoned"))?
            .clone();

        Ok(match result {
            Ok(result) => {
                ScanRunClaimTaskOutput::Success(Box::new(success_envelope(result, observer_error)))
            }
            Err(contract::ResumeError::Infrastructure(error)) => {
                ScanRunClaimTaskOutput::Failure(failure_envelope(error, observer_error))
            }
            Err(contract::ResumeError::ContinuationConsumed) => {
                ScanRunClaimTaskOutput::ContinuationConsumed
            }
            Err(error) => ScanRunClaimTaskOutput::LocalIgnoreResetError(error),
        })
    }

    /// Resolves normal envelopes and rejects replay or reset failures with stable metadata.
    fn resolve(&mut self, env: Env, output: Self::Output) -> napi::Result<Self::JsValue> {
        match output {
            ScanRunClaimTaskOutput::Success(result) => Ok(Either::A(*result)),
            ScanRunClaimTaskOutput::Failure(error) => Ok(Either::B(error)),
            // Routed through the shared rejection builder rather than rebuilding
            // the code and message by hand. The pair written here was already
            // byte-identical to `ResumeErrorKind::as_str` and `ResumeError`'s
            // `Display`, so it recorded the agreement instead of checking it —
            // and it is what kept this one rejection from carrying the rendered
            // lines every other one now does.
            ScanRunClaimTaskOutput::ContinuationConsumed => Err(scan_run_resume_error_to_napi(
                env,
                contract::ResumeError::ContinuationConsumed,
            )),
            ScanRunClaimTaskOutput::LocalIgnoreResetError(error) => {
                Err(scan_run_resume_error_to_napi(env, error))
            }
        }
    }
}

/// Resumes one retained Crash Log Scan Run through an explicit Rust-owned recovery decision.
///
/// Replay and concurrent double consumption reject with JavaScript error code
/// `scan_run_continuation_consumed`. Reset conflict, backup failure, and replacement failure
/// reject with their stable codes plus applicable identity, path, and publication-stage metadata.
/// Infrastructure failures retain the same resolved envelope used by [`scan_run_execute`].
#[napi(ts_return_type = "Promise<JsScanRunSuccess | JsScanRunFailure>")]
pub fn scan_run_resume(
    continuation: &ScanRunContinuation,
    decision: JsScanRunLocalIgnoreRecoveryDecision,
    cancellation: &ScanRunCancellation,
    // Same narrowing as `scan_run_execute`, minus `discovery_completed`: a resumed
    // run replays the discovery it already made rather than observing it again.
    #[napi(
        ts_arg_type = "(event: { kind: 'effective_concurrency_selected'; effectiveConcurrency: number; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'log_queued' | 'log_started'; log: JsScanRunLogEvent; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'log_phase'; log: JsScanRunLogEvent; phase: 'setup' | 'parse' | 'analyze' | 'finalize'; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'log_finished'; log: JsScanRunLogEvent; disposition: 'succeeded' | 'failed' | 'cancelled_before_start'; displayLines: Array<JsScanRunDisplayLine> }) => void"
    )]
    observer: Option<Function<'_, FnArgs<(JsScanRunEvent,)>, UnknownReturnValue>>,
    cancel_on_observer_error: Option<bool>,
) -> napi::Result<AsyncTask<ScanRunClaimTask>> {
    claim_continuation_task(
        continuation,
        Some(local_ignore_recovery_decision_to_core(decision)),
        cancellation,
        observer,
        cancel_on_observer_error,
    )
}

/// Abandons one retained Crash Log Scan Run without applying either recovery decision.
///
/// Requests cancellation on `cancellation` and then claims the continuation, resolving with the
/// ordinary post-discovery cancelled envelope. No backup is taken, nothing is published, and the
/// malformed Local Ignore file is left exactly as it was. Prefer this over cancelling and then
/// calling [`scan_run_resume`] with a placeholder decision: that sequence is what this replaces,
/// and getting its ordering wrong spends the one-shot continuation on a real recovery attempt.
///
/// `cancellation` is left cancelled afterwards, which is what abandoning the run means. Replay and
/// concurrent double consumption reject with JavaScript error code
/// `scan_run_continuation_consumed`, exactly as [`scan_run_resume`] does. The recovery-plan and
/// infrastructure failures resume can reject with are unreachable here, because cancellation
/// short-circuits ahead of every stage that produces them.
#[napi(ts_return_type = "Promise<JsScanRunSuccess | JsScanRunFailure>")]
pub fn scan_run_abandon(
    continuation: &ScanRunContinuation,
    cancellation: &ScanRunCancellation,
    // Byte-identical to `scan_run_resume`'s narrowing, and deliberately so: under
    // `strictFunctionTypes` a callback typed for that union is not assignable to a wider parameter,
    // so a consumer wiring one observer across both entry points needs the two to agree exactly.
    // `napi`'s attribute takes a literal, so this cannot be hoisted into a shared constant;
    // `bun run test:types` and `bun run build:cli` are what catch a divergence.
    //
    // An abandoned run observes nothing in practice — cancellation short-circuits ahead of every
    // stage that emits — but the parameter stays for that assignability, and for symmetry with the
    // CXX and Python surfaces, which both accept an observer here too.
    #[napi(
        ts_arg_type = "(event: { kind: 'effective_concurrency_selected'; effectiveConcurrency: number; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'log_queued' | 'log_started'; log: JsScanRunLogEvent; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'log_phase'; log: JsScanRunLogEvent; phase: 'setup' | 'parse' | 'analyze' | 'finalize'; displayLines: Array<JsScanRunDisplayLine> } | { kind: 'log_finished'; log: JsScanRunLogEvent; disposition: 'succeeded' | 'failed' | 'cancelled_before_start'; displayLines: Array<JsScanRunDisplayLine> }) => void"
    )]
    observer: Option<Function<'_, FnArgs<(JsScanRunEvent,)>, UnknownReturnValue>>,
    cancel_on_observer_error: Option<bool>,
) -> napi::Result<AsyncTask<ScanRunClaimTask>> {
    claim_continuation_task(
        continuation,
        None,
        cancellation,
        observer,
        cancel_on_observer_error,
    )
}

/// Builds the background task that claims a continuation exactly once.
///
/// `decision` is `None` to abandon the run. Sharing one builder keeps [`scan_run_resume`] and
/// [`scan_run_abandon`] on the same threadsafe-observer construction and the same task fields, so
/// the two cannot drift in how they reach the core — which is the whole point of the shared
/// abandonment operation they both call into.
fn claim_continuation_task(
    continuation: &ScanRunContinuation,
    decision: Option<contract::LocalIgnoreRecoveryDecision>,
    cancellation: &ScanRunCancellation,
    observer: Option<Function<'_, FnArgs<(JsScanRunEvent,)>, UnknownReturnValue>>,
    cancel_on_observer_error: Option<bool>,
) -> napi::Result<AsyncTask<ScanRunClaimTask>> {
    let observer = observer
        .map(|observer| {
            observer
                .build_threadsafe_function::<JsScanRunEvent>()
                .max_queue_size::<1>()
                .build_callback(|context| Ok((context.value,).into()))
        })
        .transpose()?;
    Ok(AsyncTask::new(ScanRunClaimTask {
        continuation: Arc::clone(&continuation.inner),
        decision,
        cancellation: cancellation.inner.clone(),
        observer,
        cancel_on_observer_error: cancel_on_observer_error.unwrap_or(false),
    }))
}

/// Maps every adapter recovery decision to the Rust-owned state transition.
const fn local_ignore_recovery_decision_to_core(
    decision: JsScanRunLocalIgnoreRecoveryDecision,
) -> contract::LocalIgnoreRecoveryDecision {
    match decision {
        JsScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore => {
            contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore
        }
        JsScanRunLocalIgnoreRecoveryDecision::ResetToDefault => {
            contract::LocalIgnoreRecoveryDecision::ResetToDefault
        }
    }
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
    Ok(contract::Configuration {
        installation_root: required_path(value.installation_root, "installationRoot")?,
        game: js_to_core_game_id(&value.game),
        game_version: value.game_version,
        options: contract::Options::new(value.show_formid_values, value.simplify_logs),
        scan_facts: CrashLogScanFacts {
            formid_database_paths: value
                .formid_database_paths
                .into_iter()
                .map(PathBuf::from)
                .collect(),
            unsolved_logs_destination: optional_path(value.unsolved_logs_destination),
        },
        max_concurrent: value.max_concurrent.map(|value| value as usize),
    })
}

/// Maps stable Installed YAML Data metadata from the immutable run snapshot.
fn installed_yaml_data_run_to_js(
    value: contract::InstalledYamlDataRunData,
) -> JsInstalledYamlDataRunData {
    JsInstalledYamlDataRunData {
        main: inspected_file_to_js(&value.main),
        game_file: inspected_file_to_js(&value.game_file),
        local_ignore_state: local_ignore_run_state_to_js(value.local_ignore_state),
        local_ignore_identity: content_identity_to_js(&value.local_ignore_identity),
        diagnostics: value
            .diagnostics
            .iter()
            .map(installed_yaml_data_run_diagnostic_to_js)
            .collect(),
        local_ignore_reset_available: value.local_ignore_reset_available,
        local_ignore_reset: value
            .local_ignore_reset
            .map(local_ignore_reset_run_data_to_js),
    }
}

fn local_ignore_reset_run_data_to_js(
    value: contract::LocalIgnoreResetRunData,
) -> JsScanRunLocalIgnoreResetRunData {
    JsScanRunLocalIgnoreResetRunData {
        local_ignore_path: value.local_ignore_path.to_string_lossy().into_owned(),
        backup_path: value.backup_path.to_string_lossy().into_owned(),
        malformed_identity: content_identity_to_js(&value.malformed_identity),
        backup_identity: content_identity_to_js(&value.backup_identity),
        replacement_identity: content_identity_to_js(&value.replacement_identity),
    }
}

/// Projects every scanner-local Local Ignore state exhaustively.
const fn local_ignore_run_state_to_js(
    value: contract::LocalIgnoreRunState,
) -> JsScanRunLocalIgnoreState {
    match value {
        contract::LocalIgnoreRunState::Existing => JsScanRunLocalIgnoreState::Existing,
        contract::LocalIgnoreRunState::Generated => JsScanRunLocalIgnoreState::Generated,
        contract::LocalIgnoreRunState::RecoveryRequired => {
            JsScanRunLocalIgnoreState::RecoveryRequired
        }
        contract::LocalIgnoreRunState::ProceedWithoutIgnore => {
            JsScanRunLocalIgnoreState::ProceedWithoutIgnore
        }
        contract::LocalIgnoreRunState::ResetToDefault => JsScanRunLocalIgnoreState::ResetToDefault,
    }
}

/// Projects one scanner-local diagnostic without widening it to recovery-only categories.
fn installed_yaml_data_run_diagnostic_to_js(
    value: &contract::InstalledYamlDataRunDiagnostic,
) -> JsScanRunInstalledYamlDataDiagnostic {
    JsScanRunInstalledYamlDataDiagnostic {
        role: value.role().map(|role| match role {
            classic_config_core::InstalledYamlDataRole::Main => JsInstalledYamlDataRole::Main,
            classic_config_core::InstalledYamlDataRole::Game => JsInstalledYamlDataRole::Game,
        }),
        candidate: value.candidate().map(|candidate| match candidate {
            classic_config_core::InstalledYamlDataProvenance::Updated => {
                JsInstalledYamlDataProvenance::Updated
            }
            classic_config_core::InstalledYamlDataProvenance::Previous => {
                JsInstalledYamlDataProvenance::Previous
            }
            classic_config_core::InstalledYamlDataProvenance::Bundled => {
                JsInstalledYamlDataProvenance::Bundled
            }
        }),
        path: value.path().map(|path| path.to_string_lossy().into_owned()),
        kind: installed_yaml_data_run_diagnostic_kind_to_js(value.kind()),
        message: value.message().to_string(),
    }
}

/// Maps every valid-or-generated scan-run diagnostic category exhaustively.
const fn installed_yaml_data_run_diagnostic_kind_to_js(
    value: contract::InstalledYamlDataRunDiagnosticKind,
) -> JsScanRunInstalledYamlDataDiagnosticKind {
    use contract::InstalledYamlDataRunDiagnosticKind as Kind;
    match value {
        Kind::CacheUnavailable => JsScanRunInstalledYamlDataDiagnosticKind::CacheUnavailable,
        Kind::Missing => JsScanRunInstalledYamlDataDiagnosticKind::Missing,
        Kind::Read => JsScanRunInstalledYamlDataDiagnosticKind::Read,
        Kind::InvalidUtf8 => JsScanRunInstalledYamlDataDiagnosticKind::InvalidUtf8,
        Kind::Parse => JsScanRunInstalledYamlDataDiagnosticKind::Parse,
        Kind::InvalidSchema => JsScanRunInstalledYamlDataDiagnosticKind::InvalidSchema,
        Kind::IncompatibleSchema => JsScanRunInstalledYamlDataDiagnosticKind::IncompatibleSchema,
        Kind::InvalidRoleData => JsScanRunInstalledYamlDataDiagnosticKind::InvalidRoleData,
        Kind::LocalIgnoreGenerated => {
            JsScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated
        }
        Kind::LocalIgnoreReset => JsScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreReset,
    }
}

/// Returns the human-facing Display Label for one scan-run diagnostic kind.
///
/// A frontend prints this label as a bare prefix before the diagnostic message,
/// so four of the ten read as failures rather than statuses: `Parse` resolves to
/// `parse failure`, not `parse`.
///
/// The wording is the configuration crate's, because the core enum behind this
/// projection is a contract-stability twin that delegates both naming forms
/// there. This surface therefore returns exactly what
/// `installedYamlDataDiagnosticKindLabel` does, without either being told twice.
///
/// Presentation only. Labels are reworded freely between releases, so branch on
/// the enum and never on this string — the enum value is the stable form.
#[napi]
pub fn scan_run_installed_yaml_data_diagnostic_kind_label(
    kind: JsScanRunInstalledYamlDataDiagnosticKind,
) -> String {
    display_label(kind, installed_yaml_data_run_diagnostic_kind_to_js).to_string()
}

/// Returns the human-facing Display Label for one scan-run Local Ignore state.
///
/// `RecoveryRequired` is the one variant whose prose the run contract owns
/// itself, since a paused run has no configuration counterpart. Same stability
/// caveat as [`scan_run_installed_yaml_data_diagnostic_kind_label`].
#[napi]
pub fn scan_run_local_ignore_yaml_data_state_label(state: JsScanRunLocalIgnoreState) -> String {
    display_label(state, local_ignore_run_state_to_js).to_string()
}

/// Resolves the Display Label for one published Vocabulary Token, or rejects it.
///
/// The two label functions above take a `string_enum`, so N-API rejects an
/// unknown value at the boundary and the "not a variant" case is unreachable.
/// The four enums below are not modelled that way on this surface — they are
/// published as bare token strings on `JsScanRunLogFailure.stage`,
/// `JsScanRunInfrastructureError.stage`, the observer's `disposition`, and a
/// Local Ignore reset rejection's `stage` — so their label functions take a
/// `string`, and a typo *is* reachable.
///
/// Throwing rather than returning `""` is the point. An empty string would
/// surface as a blank cell in a frontend with nothing to diagnose it by, and
/// this is the same answer the Python surface gives for the same reason: both
/// take a free-form token, so both owe the caller an error rather than a
/// silence.
///
/// The token spelling is snake_case here, not the camelCase this surface uses
/// for enum *identifiers*, because these four are published as snake_case token
/// strings today and those strings are frozen.
fn scan_run_label_for_token<T: Vocabulary>(token: &str, vocabulary: &str) -> napi::Result<String> {
    from_token::<T>(token)
        .map(|variant| variant.label().to_string())
        .ok_or_else(|| {
            napi::Error::from_reason(format!(
                "unknown Crash Log Scan Run {vocabulary} token `{token}`"
            ))
        })
}

/// Returns the human-facing Display Label for one terminal log disposition token.
///
/// The token is what this surface publishes on a log result's `disposition` and
/// on the `logFinished` observer event. Unlike the two twins above, the wording
/// is the run crate's own — this enum has no counterpart to delegate to.
///
/// Presentation only. Labels are reworded freely between releases, so compare
/// the token and never the label.
///
/// # Errors
///
/// Rejects with an `Error` when `token` is not a published disposition token.
#[napi]
pub fn scan_run_log_disposition_label(token: String) -> napi::Result<String> {
    scan_run_label_for_token::<contract::LogDisposition>(&token, "disposition")
}

/// Returns the human-facing Display Label for one per-log failure stage token.
///
/// The token is what this surface publishes on `JsScanRunLogFailure.stage`.
/// `unsolved_logs_finalization` resolves to `Unsolved Logs finalization`,
/// keeping the glossary capitalization of the domain term — which is exactly
/// what no mechanical transform of the token could have produced, and why the
/// label is worth crossing the seam at all.
///
/// # Errors
///
/// Rejects with an `Error` when `token` is not a published failure stage token.
#[napi]
pub fn scan_run_log_failure_stage_label(token: String) -> napi::Result<String> {
    scan_run_label_for_token::<contract::LogFailureStage>(&token, "log failure stage")
}

/// Returns the human-facing Display Label for one infrastructure stage token.
///
/// The token is what this surface publishes on
/// `JsScanRunInfrastructureError.stage`. `formid_database_access` resolves to
/// `FormID database access` and `internal_invariant` to `internal invariant
/// validation`.
///
/// # Errors
///
/// Rejects with an `Error` when `token` is not a published infrastructure stage
/// token.
#[napi]
pub fn scan_run_infrastructure_error_stage_label(token: String) -> napi::Result<String> {
    scan_run_label_for_token::<contract::InfrastructureErrorStage>(&token, "infrastructure stage")
}

/// Returns the human-facing Display Label for one reset failure stage token.
///
/// The token is what this surface publishes on a Local Ignore reset rejection's
/// `stage`. These five labels deliberately equal their tokens: the core enum is
/// a twin of the workspace's shared durable publication stage vocabulary, which
/// names ordinary steps rather than domain terms. The entry point exists anyway
/// so a caller can resolve every scan-run token the same way, rather than
/// knowing which vocabularies happen to need it.
///
/// # Errors
///
/// Rejects with an `Error` when `token` is not a published reset failure stage
/// token.
#[napi]
pub fn scan_run_local_ignore_reset_failure_stage_label(token: String) -> napi::Result<String> {
    scan_run_label_for_token::<contract::LocalIgnoreResetFailureStage>(
        &token,
        "reset failure stage",
    )
}

/// Pure metadata projected before allocating a JavaScript reset error.
enum ScanRunResumeErrorMetadata {
    None,
    Conflict {
        expected_identity: JsYamlDataContentIdentity,
        actual_identity: Option<JsYamlDataContentIdentity>,
        backup_path: Option<String>,
    },
    OperationalFailure {
        path: String,
        stage: Option<&'static str>,
    },
    DurabilityUnknown {
        path: String,
        backup_path: String,
        malformed_identity: JsYamlDataContentIdentity,
        backup_identity: JsYamlDataContentIdentity,
        replacement_identity: JsYamlDataContentIdentity,
    },
}

/// Stable code, message, rendered lines, and optional metadata for one rejected
/// continuation resume.
struct ScanRunResumeErrorProjection {
    code: &'static str,
    message: String,
    display_lines: Vec<JsScanRunDisplayLine>,
    metadata: ScanRunResumeErrorMetadata,
}

/// Projects every resume failure without depending on a live N-API environment.
fn project_scan_run_resume_error(error: contract::ResumeError) -> ScanRunResumeErrorProjection {
    let code = error.kind().as_str();
    let message = error.to_string();
    // Rendered from the borrowed error before the match below consumes it. The
    // rendered lines deliberately omit the stable resume error code that `code`
    // still carries: the code is machine-facing identity for a consumer to match
    // on, and a sentence is not where it belongs.
    let display_lines = display_lines_to_js(&render_resume_error(&error));
    let metadata = match error {
        contract::ResumeError::LocalIgnoreResetConflict(conflict) => {
            ScanRunResumeErrorMetadata::Conflict {
                expected_identity: content_identity_to_js(&conflict.expected_identity),
                actual_identity: conflict
                    .actual_identity
                    .as_ref()
                    .map(content_identity_to_js),
                backup_path: conflict
                    .backup_path
                    .map(|path| path.to_string_lossy().into_owned()),
            }
        }
        contract::ResumeError::LocalIgnoreResetBackupFailure(failure)
        | contract::ResumeError::LocalIgnoreResetReplacementFailure(failure) => {
            ScanRunResumeErrorMetadata::OperationalFailure {
                path: failure.path.to_string_lossy().into_owned(),
                stage: failure
                    .stage
                    .map(contract::LocalIgnoreResetFailureStage::as_str),
            }
        }
        contract::ResumeError::LocalIgnoreResetDurabilityUnknown(receipt) => {
            ScanRunResumeErrorMetadata::DurabilityUnknown {
                path: receipt.path.to_string_lossy().into_owned(),
                backup_path: receipt.backup_path.to_string_lossy().into_owned(),
                malformed_identity: content_identity_to_js(&receipt.malformed_identity),
                backup_identity: content_identity_to_js(&receipt.backup_identity),
                replacement_identity: content_identity_to_js(&receipt.replacement_identity),
            }
        }
        contract::ResumeError::ContinuationConsumed | contract::ResumeError::Infrastructure(_) => {
            ScanRunResumeErrorMetadata::None
        }
    };
    ScanRunResumeErrorProjection {
        code,
        message,
        display_lines,
        metadata,
    }
}

/// Builds a JavaScript error that preserves stable reset outcome metadata.
fn scan_run_resume_error_to_napi(env: Env, error: contract::ResumeError) -> napi::Error {
    let projection = project_scan_run_resume_error(error);
    let raw_error = JsError::from(napi::Error::new(
        projection.code,
        projection.message.clone(),
    ))
    .into_unknown(env);
    let Ok(mut object) = raw_error.coerce_to_object() else {
        return napi::Error::from(
            JsError::from(napi::Error::new(projection.code, projection.message)).into_unknown(env),
        );
    };
    if object.set_named_property("kind", projection.code).is_err() {
        return napi::Error::from(
            JsError::from(napi::Error::new(projection.code, projection.message)).into_unknown(env),
        );
    }
    // Purely additive. `code`, `kind`, `stage`, and the identities below stay the
    // machine-facing surface a consumer matches on; these lines are the
    // human-facing half, in the same words every other frontend says them in. A
    // consumer that only reports the failure now has a sentence it did not write.
    if object
        .set_named_property("displayLines", projection.display_lines)
        .is_err()
    {
        return napi::Error::from(
            JsError::from(napi::Error::new(projection.code, projection.message)).into_unknown(env),
        );
    }
    let metadata_result = match projection.metadata {
        ScanRunResumeErrorMetadata::Conflict {
            expected_identity,
            actual_identity,
            backup_path,
        } => object
            .set_named_property("expectedIdentity", expected_identity)
            .and_then(|()| {
                if let Some(actual) = actual_identity {
                    object.set_named_property("actualIdentity", actual)
                } else {
                    Ok(())
                }
            })
            .and_then(|()| {
                if let Some(backup_path) = backup_path {
                    object.set_named_property("backupPath", backup_path)
                } else {
                    Ok(())
                }
            }),
        ScanRunResumeErrorMetadata::OperationalFailure { path, stage } => object
            .set_named_property("path", path)
            .and_then(|()| match stage {
                Some(stage) => object.set_named_property("stage", stage),
                None => Ok(()),
            }),
        ScanRunResumeErrorMetadata::DurabilityUnknown {
            path,
            backup_path,
            malformed_identity,
            backup_identity,
            replacement_identity,
        } => object
            .set_named_property("path", path)
            .and_then(|()| object.set_named_property("backupPath", backup_path))
            .and_then(|()| object.set_named_property("malformedIdentity", malformed_identity))
            .and_then(|()| object.set_named_property("backupIdentity", backup_identity))
            .and_then(|()| object.set_named_property("replacementIdentity", replacement_identity)),
        ScanRunResumeErrorMetadata::None => Ok(()),
    };
    if metadata_result.is_err() {
        return napi::Error::from(
            JsError::from(napi::Error::new(projection.code, projection.message)).into_unknown(env),
        );
    }
    object
        .into_unknown(&env)
        .map(napi::Error::from)
        .unwrap_or_else(|_| {
            napi::Error::from(
                JsError::from(napi::Error::new(projection.code, projection.message))
                    .into_unknown(env),
            )
        })
}

/// Converts Standard discovery inputs without adding policy.
fn standard_source_to_core(
    value: JsScanRunStandardSource,
) -> napi::Result<StandardCrashLogScanSource> {
    Ok(StandardCrashLogScanSource {
        base_directory: required_path(value.base_directory, "baseDirectory")?,
        custom_scan_directory: optional_path(value.custom_scan_directory),
        configured_documents_root: optional_path(value.configured_documents_root),
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

/// Converts optional path text while treating blank binding sentinels as absent.
fn optional_path(value: Option<String>) -> Option<PathBuf> {
    value
        .filter(|path| !path.trim().is_empty())
        .map(PathBuf::from)
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
        // Delegated rather than restated, like the per-log disposition and failure
        // stage below. The core token is published unchanged rather than through
        // `js_token`, because this surface's scan-run tokens are snake_case: the
        // `ts_type` on `JsScanRunResult::status` and `index.d.ts` both spell them
        // out, and camelizing one here would rename a value consumers match on.
        status: value.status.as_str().to_string(),
        discovery: value.discovery.map(discovery_to_js),
        setup: value.setup.map(setup_to_js),
        installed_yaml_data: value.installed_yaml_data.map(installed_yaml_data_run_to_js),
        continuation: value.continuation.map(|continuation| ScanRunContinuation {
            inner: Arc::new(continuation),
        }),
        effective_concurrency: value.effective_concurrency.map(usize_to_u32),
        message: value.message,
        total: usize_to_u32(value.total),
        succeeded: usize_to_u32(value.succeeded),
        failed: usize_to_u32(value.failed),
        cancelled: usize_to_u32(value.cancelled),
        logs: value.logs.into_iter().map(log_result_to_js).collect(),
    }
}

/// Builds the resolved success envelope, rendering the run before projecting it.
///
/// The order is load-bearing. `run_result_to_js` consumes the result — including
/// moving its one-shot continuation into the opaque carrier — so the render has
/// to happen while the Rust value is still borrowable. Rendering afterwards would
/// have nothing left to render, and writing it that way does not compile.
///
/// `scanRunExecute` and `scanRunResume` both resolve this envelope, which is why
/// one builder serves the initial run and the continuation resume alike.
fn success_envelope(
    result: contract::RunResult,
    observer_error: Option<String>,
) -> JsScanRunSuccess {
    let display_lines = display_lines_to_js(&render_run_result(&result));
    // Rendered only for the one status that pauses for an answer. Every other status
    // has nothing to ask, and a prompt attached to a finished run would invite a
    // consumer to show one.
    let recovery_prompt =
        (result.status == contract::RunStatus::LocalIgnoreRecoveryRequired).then(|| {
            recovery_prompt_to_js(&render_local_ignore_recovery(
                result.installed_yaml_data.as_ref(),
            ))
        });
    JsScanRunSuccess {
        result: run_result_to_js(result),
        observer_error,
        display_lines,
        recovery_prompt,
    }
}

/// Builds the resolved failure envelope, rendering the failure before projecting it.
fn failure_envelope(
    error: contract::InfrastructureError,
    observer_error: Option<String>,
) -> JsScanRunFailure {
    let display_lines = display_lines_to_js(&render_infrastructure_error(&error));
    JsScanRunFailure {
        error: infrastructure_error_to_js(error),
        observer_error,
        display_lines,
    }
}

/// Flattens rendered Display Content into the JavaScript mirror types.
///
/// The flattening is the C++ bridge's, unchanged: each segment crosses as a kind
/// tag plus one field per payload shape, and the fields the kind does not use
/// stay empty rather than absent. Making them optional here would be more
/// idiomatic JavaScript and worse parity — a consumer reading two bindings would
/// read the same segment two ways, and the taxonomy is frozen precisely so that
/// cannot happen.
fn display_lines_to_js(lines: &[DisplayLine]) -> Vec<JsScanRunDisplayLine> {
    lines
        .iter()
        .map(|line| JsScanRunDisplayLine {
            severity: map_display_severity(line.severity),
            segments: line.segments.iter().map(display_segment_to_js).collect(),
        })
        .collect()
}

/// Flattens one typed segment, filling exactly the fields its kind selects.
fn display_segment_to_js(segment: &DisplaySegment) -> JsScanRunDisplaySegment {
    let mut projected = JsScanRunDisplaySegment {
        kind: JsScanRunDisplaySegmentKind::Text,
        text: String::new(),
        path: String::new(),
        count: 0,
    };
    match segment {
        DisplaySegment::Text(text) => {
            // Assigned rather than left to the initializer's default, so reordering
            // the fields above cannot silently relabel a `Text` segment as some
            // other kind.
            projected.kind = JsScanRunDisplaySegmentKind::Text;
            projected.text = (*text).to_string();
        }
        DisplaySegment::Label(label) => {
            projected.kind = JsScanRunDisplaySegmentKind::Label;
            projected.text = (*label).to_string();
        }
        DisplaySegment::Count { value, noun } => {
            projected.kind = JsScanRunDisplaySegmentKind::Count;
            // The noun rides in `text` already agreeing with `count`. A consumer
            // prints the two side by side; it never re-decides the form.
            projected.text = (*noun).to_string();
            projected.count = u64_to_i64(*value);
        }
        DisplaySegment::Path(path) => {
            projected.kind = JsScanRunDisplaySegmentKind::Path;
            projected.path = path.to_string_lossy().into_owned();
        }
        DisplaySegment::Name(name) => {
            projected.kind = JsScanRunDisplaySegmentKind::Name;
            projected.text = name.clone();
        }
        DisplaySegment::Emphasis(value) => {
            projected.kind = JsScanRunDisplaySegmentKind::Emphasis;
            projected.text = value.clone();
        }
    }
    projected
}

/// Maps how gravely a line should read onto its JavaScript twin.
///
/// Exhaustive rather than numeric: the two enumerations agree today, but a
/// `match` is what makes them keep agreeing when either one gains a variant.
const fn map_display_severity(value: DisplaySeverity) -> JsScanRunDisplaySeverity {
    match value {
        DisplaySeverity::Info => JsScanRunDisplaySeverity::Info,
        DisplaySeverity::Notice => JsScanRunDisplaySeverity::Notice,
        DisplaySeverity::Warning => JsScanRunDisplaySeverity::Warning,
        DisplaySeverity::Failure => JsScanRunDisplaySeverity::Failure,
        DisplaySeverity::Success => JsScanRunDisplaySeverity::Success,
    }
}

/// Flattens a rendered Local Ignore recovery prompt into the JavaScript mirror types.
///
/// The decision descriptions cross as ordinary segment lists, the same flattening the
/// lines beside them use, so a consumer reads a description with the renderer it
/// already has.
fn recovery_prompt_to_js(prompt: &RecoveryPrompt) -> JsScanRunRecoveryPrompt {
    JsScanRunRecoveryPrompt {
        lines: display_lines_to_js(&prompt.lines),
        decisions: prompt
            .decisions
            .iter()
            .map(|description| JsScanRunRecoveryDecisionDescription {
                decision: map_local_ignore_recovery_decision(description.decision),
                label: description.label.to_string(),
                description: description
                    .description
                    .iter()
                    .map(display_segment_to_js)
                    .collect(),
                available: description.available,
            })
            .collect(),
    }
}

/// Maps a Rust-owned recovery decision onto its JavaScript twin.
///
/// The outbound half of the mapping whose inbound half is
/// [`local_ignore_recovery_decision_to_core`]. Written separately because Rust cannot
/// invert a `match`, and exhaustive so that a third variant added to the contract stops
/// this from compiling rather than silently describing itself as one of the two that
/// exist.
const fn map_local_ignore_recovery_decision(
    value: contract::LocalIgnoreRecoveryDecision,
) -> JsScanRunLocalIgnoreRecoveryDecision {
    match value {
        contract::LocalIgnoreRecoveryDecision::ProceedWithoutIgnore => {
            JsScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore
        }
        contract::LocalIgnoreRecoveryDecision::ResetToDefault => {
            JsScanRunLocalIgnoreRecoveryDecision::ResetToDefault
        }
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

/// Returns the published token for one coarse-grained scan progress phase.
///
/// Delegates rather than restating: the phase adopted the Vocabulary naming
/// contract with the four strings this table already published, and the copy that
/// stood here was byte-identical to the Python surface's own copy and to the
/// core's — three exhaustive matches, none of which would have failed to compile
/// if one had drifted.
fn phase_to_string(value: ScanProgressPhase) -> String {
    value.as_str().to_string()
}

fn log_event_to_js(value: contract::LogEvent) -> JsScanRunLogEvent {
    JsScanRunLogEvent {
        discovery_index: usize_to_u32(value.discovery_index),
        crash_log: path_to_string(value.crash_log),
        completed: usize_to_u32(value.completed),
        total: usize_to_u32(value.total),
    }
}

/// Maps one lifecycle event, rendering its Display Content on the way through.
///
/// Rendering happens here, inline on the observer path, before the event reaches
/// JavaScript. There is no later opportunity: the JavaScript observer receives a
/// projected copy and never holds the Rust event.
fn event_to_js(value: contract::Event) -> JsScanRunEvent {
    let display_lines = display_lines_to_js(&render_event(&value));
    let mut event = tagged_event_to_js(value);
    event.display_lines = display_lines;
    event
}

/// Maps every event variant into one stable tagged JavaScript shape.
///
/// Leaves `display_lines` empty; [`event_to_js`] fills it once the borrowed event
/// has been rendered.
fn tagged_event_to_js(value: contract::Event) -> JsScanRunEvent {
    match value {
        contract::Event::DiscoveryCompleted(discovery) => JsScanRunEvent {
            kind: "discovery_completed".to_string(),
            discovery: Some(discovery_to_js(discovery)),
            effective_concurrency: None,
            log: None,
            phase: None,
            disposition: None,
            display_lines: Vec::new(),
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
            display_lines: Vec::new(),
        },
        contract::Event::LogQueued(log) => JsScanRunEvent {
            kind: "log_queued".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_js(log)),
            phase: None,
            disposition: None,
            display_lines: Vec::new(),
        },
        contract::Event::LogStarted(log) => JsScanRunEvent {
            kind: "log_started".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_js(log)),
            phase: None,
            disposition: None,
            display_lines: Vec::new(),
        },
        contract::Event::LogPhase { log, phase } => JsScanRunEvent {
            kind: "log_phase".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_js(log)),
            phase: Some(phase_to_string(phase)),
            disposition: None,
            display_lines: Vec::new(),
        },
        contract::Event::LogFinished { log, disposition } => JsScanRunEvent {
            kind: "log_finished".to_string(),
            discovery: None,
            effective_concurrency: None,
            log: Some(log_event_to_js(log)),
            phase: None,
            disposition: Some(disposition.as_str().to_string()),
            display_lines: Vec::new(),
        },
    }
}
