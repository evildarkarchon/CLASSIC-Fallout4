//! Crash log scanning bridge for CXX FFI.
//!
//! Exposes the final Rust-owned Crash Log Scan Run contract, the Crash Log Scan
//! Launch that builds its requests, and Papyrus log monitoring.
//!
//! The CXX bridge declarations stay in this façade module while implementation
//! concerns live in private scanner submodules.

mod contract;
mod launch;
mod papyrus;

pub(crate) use contract::{
    ScanRunCancellation, ScanRunContractExecution, ScanRunPendingRecovery, ScanRunRequest,
    scan_run_cancellation_cancel, scan_run_cancellation_is_cancelled, scan_run_cancellation_new,
    scan_run_contract_execute, scan_run_contract_execution_has_pending_recovery,
    scan_run_contract_execution_take_pending_recovery, scan_run_contract_execution_take_result,
    scan_run_installed_yaml_data_provenance_label, scan_run_local_ignore_yaml_data_state_label,
    scan_run_pending_recovery_cancellation_requested, scan_run_pending_recovery_prompt,
    scan_run_pending_recovery_settle,
};
pub(crate) use launch::{
    ScanRunLaunch, scan_run_launch_error, scan_run_launch_request, scan_run_launch_standard,
    scan_run_launch_targeted, scan_run_launch_view,
};
pub(crate) use papyrus::{
    CxxPapyrusAnalyzer, papyrus_analyzer_new, papyrus_check_updates, papyrus_log_exists,
    papyrus_start_monitoring,
};

#[cxx::bridge(namespace = "classic::scanner")]
mod ffi {
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractProgressPhase {
        Setup = 0,
        Parse = 1,
        Analyze = 2,
        Finalize = 3,
    }

    /// Typed game identity used to select one Installed YAML Data Snapshot.
    ///
    /// CXX bridge modules cannot share enum definitions, so this scanner-local
    /// type exhaustively mirrors `classic_shared_core::GameId`.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunGameId {
        Fallout4 = 0,
        Fallout4VR = 1,
        Skyrim = 2,
        Starfield = 3,
    }

    /// Update-eligible role for one file retained by a scan-run snapshot.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunInstalledYamlDataRole {
        Main = 0,
        Game = 1,
    }

    /// Candidate provenance for one selected scan-run YAML Data file.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunInstalledYamlDataProvenance {
        Updated = 0,
        Previous = 1,
        Bundled = 2,
    }

    /// Stable category for one scan-run Installed YAML Data diagnostic.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunInstalledYamlDataDiagnosticKind {
        CacheUnavailable = 0,
        Missing = 1,
        Read = 2,
        InvalidUtf8 = 3,
        Parse = 4,
        InvalidSchema = 5,
        IncompatibleSchema = 6,
        InvalidRoleData = 7,
        LocalIgnoreGenerated = 8,
        LocalIgnoreReset = 9,
    }

    /// How Local Ignore YAML Data entered the immutable scan-run snapshot.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunLocalIgnoreYamlDataState {
        Existing = 0,
        Generated = 1,
        RecoveryRequired = 2,
        ProceedWithoutIgnore = 3,
        ResetToDefault = 4,
    }

    /// Explicit choice accepted by a Local Ignore recovery continuation.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunLocalIgnoreRecoveryDecision {
        ProceedWithoutIgnore = 0,
        ResetToDefault = 1,
    }

    /// An optional Local Ignore Recovery Decision for `scan_run_pending_recovery_settle`.
    ///
    /// The bridge has no `Option`, so the absence of a decision is spelled like every other
    /// optional field here: `decision` is read only when `has_decision` is true. No decision
    /// abandons the run; it is not a third decision.
    struct ScanRunLocalIgnoreRecoverySettlement {
        has_decision: bool,
        decision: ScanRunLocalIgnoreRecoveryDecision,
    }

    /// Whether a failed observer delivery cancels the run.
    ///
    /// Passed to `scan_run_contract_execute` and `scan_run_pending_recovery_settle`. Either way
    /// the envelope reports the first failed delivery and no further events reach the observer.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunObserverFailurePolicy {
        /// Keep running to a normal terminal result.
        ContinueRun = 0,
        /// Request cancellation on the run's own control at the first failed delivery.
        CancelRun = 1,
    }

    /// What `ScanRunObserver::on_scan_run_event` returns instead of throwing.
    ///
    /// A value-initialized `{}` means delivered. Set `failed` (and optionally `message`) when the
    /// event could not be delivered; the bridge applies the caller's
    /// `ScanRunObserverFailurePolicy` and reports the failure in the execution envelope.
    struct ScanRunObserverDelivery {
        failed: bool,
        message: String,
    }

    /// One setup check in a Crash Log Scan Setup Result.
    struct ScanRunSetupCheckDto {
        kind: String,
        state: String,
        message: String,
        details: Vec<String>,
    }

    /// Proposed setup path update.
    struct ScanRunSetupPathUpdateDto {
        kind: String,
        path: String,
    }

    /// Shared configuration for the final Crash Log Scan Run contract.
    struct ScanRunConfigurationDto {
        installation_root: String,
        game: ScanRunGameId,
        game_version: String,
        show_formid_values: bool,
        simplify_logs: bool,
        formid_database_paths: Vec<String>,
        has_configured_unsolved_logs_destination: bool,
        configured_unsolved_logs_destination: String,
        has_max_concurrent: bool,
        max_concurrent: usize,
    }

    /// Standard discovery source for the final Crash Log Scan Run contract.
    struct ScanRunStandardSourceDto {
        base_directory: String,
        has_custom_scan_directory: bool,
        custom_scan_directory: String,
        has_configured_documents_root: bool,
        configured_documents_root: String,
    }

    /// Targeted discovery source for the final Crash Log Scan Run contract.
    struct ScanRunTargetedSourceDto {
        inputs: Vec<String>,
    }

    /// Run-scoped FCX setup facts a launch resolved for an FCX-enabled Crash Log Scan Run.
    struct ScanRunSetupContextDto {
        has_game_root: bool,
        game_root: String,
        has_docs_root: bool,
        docs_root: String,
        has_game_exe_path: bool,
        game_exe_path: String,
        has_xse_log_path: bool,
        xse_log_path: String,
    }

    /// Optional per-run values that win over saved User Settings for one Crash Log Scan Launch.
    ///
    /// Each `has_*` flag says whether its value was supplied. `game_version` takes a User
    /// Settings game-version token (`auto`, `Original`, `NextGen`, `AnniversaryEdition`, `VR`).
    /// `max_concurrent` zero explicitly requests adaptive concurrency, which overrides a saved
    /// limit. `show_formid_values`, `simplify_logs` and `fcx_mode` are supplied-as-on: `true`
    /// turns the option on for this run, `false` keeps the saved value. `no_scan_path` supplies
    /// "no custom scan folder", which withholds a saved custom scan folder for this run (a
    /// cleared custom scan folder input); it cannot be combined with `has_scan_path`.
    struct ScanRunLaunchOverridesDto {
        has_game: bool,
        game: ScanRunGameId,
        has_game_version: bool,
        game_version: String,
        has_scan_path: bool,
        scan_path: String,
        no_scan_path: bool,
        has_max_concurrent: bool,
        max_concurrent: usize,
        show_formid_values: bool,
        simplify_logs: bool,
        fcx_mode: bool,
    }

    /// Which Crash Logs a launched request scans.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunLaunchIntent {
        Standard = 0,
        Targeted = 1,
    }

    /// Standard-only Unsolved Logs intent carried by a launched request.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunLaunchUnsolvedLogs {
        LeaveInPlace = 0,
        MoveToConfiguredOrDefault = 1,
        MoveToCustom = 2,
    }

    /// Which launch rule produced a launch diagnostic.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunLaunchDiagnosticKind {
        UserSettings = 0,
        /// The game-differs rule withheld the managed game's saved game version.
        GameVersionNotApplied = 1,
        /// The game-differs rule withheld the managed game's saved FCX Mode.
        FcxModeNotApplied = 2,
        /// The game-differs rule withheld the managed game's saved custom scan folder.
        CustomScanFolderNotApplied = 3,
        /// The game-differs rule withheld the managed game's saved setup folders.
        SetupFoldersNotApplied = 4,
    }

    /// One non-fatal launch diagnostic; the launch still produced a scannable request.
    struct ScanRunLaunchDiagnosticDto {
        kind: ScanRunLaunchDiagnosticKind,
        /// Stable machine-readable code (the User Settings code for `UserSettings`, the
        /// kind's snake_case token otherwise).
        code: String,
        /// Human-readable context. Prose; branch on `kind` and `code` instead.
        message: String,
    }

    /// Stable category of a typed launch error.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunLaunchErrorKind {
        TargetedWithoutInputs = 0,
        /// FCX Mode is on and the XSE log location could not be inspected (not mere absence).
        XseLogInspect = 1,
    }

    /// Typed launch error. `has_error` is authoritative; the other fields are placeholders
    /// when it is false.
    struct ScanRunLaunchErrorDto {
        has_error: bool,
        kind: ScanRunLaunchErrorKind,
        message: String,
    }

    /// Read-only view of a launched Crash Log Scan Run request and its diagnostics.
    ///
    /// The view is built from the configuration, source and setup-context DTOs, filled with
    /// exactly what the launch decided. `standard_source` and `unsolved_logs*` are meaningful only for a Standard
    /// intent, `targeted_source` only for a Targeted intent, and `setup_context` only when
    /// `fcx_enabled`; CXX shared structs cannot omit fields, so the others are empty.
    struct ScanRunLaunchRequestDto {
        intent: ScanRunLaunchIntent,
        configuration: ScanRunConfigurationDto,
        standard_source: ScanRunStandardSourceDto,
        unsolved_logs: ScanRunLaunchUnsolvedLogs,
        unsolved_logs_custom_destination: String,
        targeted_source: ScanRunTargetedSourceDto,
        fcx_enabled: bool,
        setup_context: ScanRunSetupContextDto,
        diagnostics: Vec<ScanRunLaunchDiagnosticDto>,
        /// The diagnostics rendered as Display Content, one line per diagnostic in the
        /// same order. Show these rather than phrasing `diagnostics` in C++.
        display_lines: Vec<ScanRunDisplayLine>,
    }

    /// Stable lifecycle status from the final Crash Log Scan Run contract.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractStatus {
        Completed = 0,
        NoCrashLogsFound = 1,
        SetupFailed = 2,
        CancelledBeforeDiscovery = 3,
        Cancelled = 4,
        LocalIgnoreRecoveryRequired = 5,
    }

    /// Discovery source retained by the final contract.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractDiscoverySource {
        Standard = 0,
        Targeted = 1,
    }

    /// Typed terminal disposition for one discovered Crash Log.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractLogDisposition {
        Succeeded = 0,
        Failed = 1,
        CancelledBeforeStart = 2,
    }

    /// Stable stage for one per-log processing or finalization failure.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractLogFailureStage {
        Analysis = 0,
        ReportWrite = 1,
        UnsolvedLogsFinalization = 2,
    }

    /// Stable stage for a run-wide infrastructure failure.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractInfrastructureErrorStage {
        RequestValidation = 0,
        Discovery = 1,
        Intake = 2,
        FormIdDatabaseAccess = 3,
        Initialization = 4,
        InternalInvariant = 5,
    }

    /// Stable continuation replay or Local Ignore reset failure category.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractResumeErrorKind {
        ContinuationConsumed = 0,
        LocalIgnoreResetConflict = 1,
        LocalIgnoreResetBackupFailure = 2,
        LocalIgnoreResetReplacementFailure = 3,
        LocalIgnoreResetDurabilityUnknown = 4,
    }

    /// Durable publication stage retained by a Local Ignore reset failure.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunLocalIgnoreResetFailureStage {
        Create = 0,
        Write = 1,
        Flush = 2,
        Sync = 3,
        Publish = 4,
    }

    /// Stable event variants emitted by the final contract.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractEventKind {
        DiscoveryCompleted = 0,
        EffectiveConcurrencySelected = 1,
        LogQueued = 2,
        LogStarted = 3,
        LogPhase = 4,
        LogFinished = 5,
    }

    /// One rejected Targeted discovery input and its reason.
    struct ScanRunContractRejectedInput {
        path: String,
        reason: String,
    }

    /// Complete retained discovery data from the final contract.
    struct ScanRunContractDiscoveryResult {
        source: ScanRunContractDiscoverySource,
        accepted_logs: Vec<String>,
        rejected_inputs: Vec<ScanRunContractRejectedInput>,
        searched_locations: Vec<String>,
    }

    /// One typed failure for a discovered Crash Log.
    struct ScanRunContractLogFailure {
        stage: ScanRunContractLogFailureStage,
        message: String,
    }

    /// Complete terminal result for one Crash Log in discovery order.
    struct ScanRunContractLogResult {
        discovery_index: usize,
        crash_log: String,
        has_autoscan_report: bool,
        autoscan_report: String,
        disposition: ScanRunContractLogDisposition,
        failures: Vec<ScanRunContractLogFailure>,
        has_message: bool,
        message: String,
        moved_to_unsolved_logs: bool,
        processing_time_us: u64,
        processing_time_ms: u64,
        formid_count: usize,
        plugin_count: usize,
        suspect_count: usize,
    }

    /// FCX setup details with explicit optional-message presence.
    struct ScanRunContractSetupResult {
        status: String,
        has_message: bool,
        message: String,
        rendered_report: String,
        checks: Vec<ScanRunSetupCheckDto>,
        path_updates: Vec<ScanRunSetupPathUpdateDto>,
        configuration_issues: Vec<FcxIssueDto>,
        actions: Vec<String>,
        fatal_errors: Vec<String>,
    }

    /// Content identity derived from exact bytes retained by the scan run.
    struct ScanRunYamlDataContentIdentityDto {
        sha256: String,
        byte_len: u64,
    }

    /// Selected-file metadata derived from exact retained YAML Data bytes.
    struct ScanRunInspectedYamlDataFileDto {
        role: ScanRunInstalledYamlDataRole,
        provenance: ScanRunInstalledYamlDataProvenance,
        schema_version: String,
        sha256: String,
        byte_len: u64,
    }

    /// Structured attribution for one fallback, validation, or generation event.
    struct ScanRunInstalledYamlDataDiagnosticDto {
        has_role: bool,
        role: ScanRunInstalledYamlDataRole,
        has_candidate: bool,
        candidate: ScanRunInstalledYamlDataProvenance,
        has_path: bool,
        path: String,
        kind: ScanRunInstalledYamlDataDiagnosticKind,
        message: String,
    }

    /// Installed YAML Data metadata selected once for the complete scan run.
    struct ScanRunInstalledYamlDataRunDataDto {
        main: ScanRunInspectedYamlDataFileDto,
        game_file: ScanRunInspectedYamlDataFileDto,
        local_ignore_state: ScanRunLocalIgnoreYamlDataState,
        local_ignore_identity: ScanRunYamlDataContentIdentityDto,
        diagnostics: Vec<ScanRunInstalledYamlDataDiagnosticDto>,
        /// Whether Reset To Default can succeed while recovery is required.
        ///
        /// Only meaningful when `local_ignore_state` is `RecoveryRequired`. A recovery plan
        /// built from a Main YAML with no usable `default_ignorefile` can only satisfy Proceed
        /// Without Ignore, and a frontend that offers Reset anyway burns the one-shot
        /// continuation on a guaranteed failure.
        local_ignore_reset_available: bool,
        has_local_ignore_reset: bool,
        local_ignore_reset: ScanRunLocalIgnoreResetRunDataDto,
    }

    /// Durable backup and replacement metadata from successful Reset To Default resume.
    struct ScanRunLocalIgnoreResetRunDataDto {
        local_ignore_path: String,
        backup_path: String,
        malformed_identity: ScanRunYamlDataContentIdentityDto,
        backup_identity: ScanRunYamlDataContentIdentityDto,
        replacement_identity: ScanRunYamlDataContentIdentityDto,
    }

    /// How gravely one Crash Log Scan Run display line should read.
    ///
    /// Adapters map this onto their own styling. Rust never names a colour, a text
    /// attribute, or a widget. A plain, pipeable frontend may map it onto nothing more
    /// than a choice of output stream.
    ///
    /// CXX bridge modules cannot share enum definitions, so this scanner-local type
    /// exhaustively mirrors `classic_scan_presentation::DisplaySeverity`.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunDisplaySeverity {
        Info = 0,
        Notice = 1,
        Warning = 2,
        Failure = 3,
        Success = 4,
    }

    /// Which payload field of a `ScanRunDisplaySegment` carries its value.
    ///
    /// Mirrors the variant set of `classic_scan_presentation::DisplaySegment`. The
    /// taxonomy is fixed at six kinds for its first version: each addition touches this
    /// DTO and the CLI and GUI segment renderers, so growth must be a deliberate decision.
    #[repr(u8)]
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunDisplaySegmentKind {
        Text = 0,
        Label = 1,
        Count = 2,
        Path = 3,
        Name = 4,
        Emphasis = 5,
    }

    /// One typed piece of a Crash Log Scan Run display line.
    ///
    /// CXX cannot express a Rust enum carrying payloads, so the six-variant segment crosses
    /// flattened: a kind tag plus one field per payload shape, with the fields the kind does
    /// not use left empty. Read only the field `kind` selects.
    struct ScanRunDisplaySegment {
        kind: ScanRunDisplaySegmentKind,
        /// Payload for `Text`, `Label`, `Name`, and `Emphasis`. For `Count` this is the
        /// noun Rust already resolved to agree with `count`, so no adapter re-decides
        /// pluralization and no user reads "1 logs". Empty for `Path`.
        text: String,
        /// Payload for `Path`, whole and untruncated. Truncation is the adapter's
        /// choice. Empty otherwise.
        path: String,
        /// Payload for `Count`. Zero otherwise.
        count: u64,
    }

    /// One line of Crash Log Scan Run Display Content.
    ///
    /// An adapter concatenates `segments` in order and never reorders within a line. It
    /// may reorder, group, or omit whole lines. It must not re-derive a Display Label
    /// already carried in a `Label` segment, and must not re-decide a `Count`'s noun.
    struct ScanRunDisplayLine {
        severity: ScanRunDisplaySeverity,
        segments: Vec<ScanRunDisplaySegment>,
    }

    /// One Local Ignore recovery decision, named and explained, with its availability
    /// attached.
    ///
    /// `available` travels here rather than as a separate flag beside the prompt, which is
    /// what makes honouring it take no separate lookup. An adapter must not offer a decision
    /// for which it is false: Rust still fails safely and touches nothing on disk, but the
    /// attempt spends the one-shot continuation, so the user is left with no scan and no
    /// second attempt.
    struct ScanRunRecoveryDecisionDescription {
        /// The decision to hand back to `scan_run_pending_recovery_settle`.
        decision: ScanRunLocalIgnoreRecoveryDecision,
        /// The decision's Display Label.
        label: String,
        /// What choosing it will actually do, concatenated in order like any other line.
        description: Vec<ScanRunDisplaySegment>,
        /// Whether this run can honor the decision.
        available: bool,
    }

    /// The Rust-owned content of a Local Ignore recovery prompt.
    ///
    /// `lines` state why the run paused and what is being decided about; `decisions` lists
    /// every decision the continuation contract accepts. The affordance beside a description
    /// — a bracketed letter, a key hint, a button — is the adapter's own, as is the order it
    /// presents them in and whether the prompt is a dialog, an overlay, or a line of stdin.
    /// The descriptions themselves are not.
    ///
    /// Backing out appears nowhere here. `ScanRunLocalIgnoreRecoveryDecision` has exactly two
    /// variants by design, and abandonment is spelled as the absence of a decision when
    /// settling through `scan_run_pending_recovery_settle`.
    struct ScanRunRecoveryPrompt {
        lines: Vec<ScanRunDisplayLine>,
        decisions: Vec<ScanRunRecoveryDecisionDescription>,
    }

    /// Complete terminal result from the final Crash Log Scan Run contract.
    struct ScanRunContractRunResult {
        status: ScanRunContractStatus,
        has_discovery: bool,
        discovery: ScanRunContractDiscoveryResult,
        has_setup: bool,
        setup: ScanRunContractSetupResult,
        has_installed_yaml_data: bool,
        installed_yaml_data: ScanRunInstalledYamlDataRunDataDto,
        has_effective_concurrency: bool,
        effective_concurrency: usize,
        has_message: bool,
        message: String,
        total: usize,
        succeeded: usize,
        failed: usize,
        cancelled: usize,
        logs: Vec<ScanRunContractLogResult>,
    }

    /// Typed run-wide failure that prevented a meaningful terminal result.
    struct ScanRunContractInfrastructureError {
        stage: ScanRunContractInfrastructureErrorStage,
        message: String,
        has_path: bool,
        path: String,
    }

    /// Typed recovery-resume failure that is distinct from infrastructure failure.
    struct ScanRunContractResumeError {
        kind: ScanRunContractResumeErrorKind,
        code: String,
        message: String,
        has_path: bool,
        path: String,
        has_stage: bool,
        stage: ScanRunLocalIgnoreResetFailureStage,
        has_expected_identity: bool,
        expected_identity: ScanRunYamlDataContentIdentityDto,
        has_actual_identity: bool,
        actual_identity: ScanRunYamlDataContentIdentityDto,
        has_backup_path: bool,
        backup_path: String,
        has_durability_receipt: bool,
        malformed_identity: ScanRunYamlDataContentIdentityDto,
        backup_identity: ScanRunYamlDataContentIdentityDto,
        replacement_identity: ScanRunYamlDataContentIdentityDto,
    }

    /// Exactly one of `result`, `error`, or `resume_error`, identified by presence flags.
    ///
    /// Both `scan_run_contract_execute` and `scan_run_pending_recovery_settle` return this
    /// one envelope, so a single `display_lines` field covers the initial run and the
    /// settled run alike.
    struct ScanRunContractExecutionResult {
        has_result: bool,
        result: ScanRunContractRunResult,
        has_error: bool,
        error: ScanRunContractInfrastructureError,
        has_resume_error: bool,
        resume_error: ScanRunContractResumeError,
        /// What this run says, in Rust's words, for whichever payload the presence flags
        /// select above.
        ///
        /// Rendered while the Rust run result was still live, because C++ receives a
        /// projected copy and cannot render from the Rust value later. An adapter states
        /// the run from these lines rather than composing sentences of its own; the
        /// fields above stay the machine-facing surface a consumer matches on.
        ///
        /// Empty when no payload is present, which is what a moved-from envelope leaves
        /// behind.
        display_lines: Vec<ScanRunDisplayLine>,
        /// Whether `recovery_prompt` below describes a decision this run is waiting on.
        ///
        /// True only when `result.status` is `LocalIgnoreRecoveryRequired`, which is also
        /// exactly when the execution offers a pending recovery.
        has_recovery_prompt: bool,
        /// What to ask the user, and which answers this run can honor.
        ///
        /// Rendered here for the reason `display_lines` is: C++ receives a projected copy of
        /// the run and cannot render from the Rust value later. Empty in both vectors when
        /// `has_recovery_prompt` is false.
        recovery_prompt: ScanRunRecoveryPrompt,
        /// Whether an observer delivery failed during this run, whatever the payload above.
        ///
        /// Reported under every `ScanRunObserverFailurePolicy`, so an adapter reads "delivery
        /// failed" here instead of tracking it in its own observer.
        has_observer_delivery_failure: bool,
        /// The first failed delivery's message; empty when `has_observer_delivery_failure` is
        /// false.
        observer_delivery_failure_message: String,
    }

    /// One serialized lifecycle event from the final contract.
    ///
    /// Fields unrelated to `kind` contain defaults and must be ignored.
    struct ScanRunContractEvent {
        kind: ScanRunContractEventKind,
        discovery: ScanRunContractDiscoveryResult,
        effective_concurrency: usize,
        discovery_index: usize,
        crash_log: String,
        completed: usize,
        total: usize,
        phase: ScanRunContractProgressPhase,
        disposition: ScanRunContractLogDisposition,
        /// What this event says, in Rust's words.
        ///
        /// Populated inline in the observer adapter before the event reaches C++, so an
        /// adapter that shows progress states it in the same words every other frontend
        /// does. One event can produce more than one line — a discovery that rejected
        /// some of its targeted inputs states the rejection separately.
        ///
        /// Unlike the fields above, this is never defaulted by `kind`: every event kind
        /// renders. An adapter that shows only some kinds omits whole lines, which the
        /// adapter contract allows.
        display_lines: Vec<ScanRunDisplayLine>,
    }

    /// Papyrus log statistics transferred across the FFI boundary.
    struct PapyrusStatsDto {
        dumps: u32,
        stacks: u32,
        warnings: u32,
        errors: u32,
        lines_processed: u32,
        dumps_stacks_ratio: f64,
    }

    /// Run-scoped FCX configuration issue returned by the final scan-run contract.
    ///
    /// The single `Option<String>` field (`section`) is flattened following the
    /// Bridge String/Path Contract from plan 02-01:
    ///   - `section_or_empty`: the section name, or `""` when `section` was `None`
    ///   - `has_section`: `true` when `section` was `Some(…)`, `false` when `None`
    ///
    /// All other fields are plain `String` copies — no `Option` wrappers (Pitfall 6 CLEAR).
    struct FcxIssueDto {
        /// Path to the configuration file (e.g., "Fallout4.ini")
        file_path: String,
        /// INI section name, or `""` when the source `section` field was `None`
        section_or_empty: String,
        /// `true` when `section` was `Some(…)`, `false` when it was `None`
        has_section: bool,
        /// Setting/key name (e.g., "iNumThreads")
        setting: String,
        /// Current value found in the file
        current_value: String,
        /// Recommended replacement value
        recommended_value: String,
        /// Human-readable description of the issue
        description: String,
        /// Severity level: "error", "warning", or "info"
        severity: String,
    }

    unsafe extern "C++" {
        include!("classic_cxx_bridge/scan_run_observer.h");
        type ScanRunObserver;
        fn on_scan_run_event(
            self: &ScanRunObserver,
            event: &ScanRunContractEvent,
        ) -> ScanRunObserverDelivery;
    }

    extern "Rust" {
        type ScanRunRequest;
        type ScanRunCancellation;
        type ScanRunContractExecution;
        type ScanRunLaunch;
        type ScanRunPendingRecovery;

        /// Creates a new uncancelled monotonic control; final-contract cancellation cannot be reset.
        fn scan_run_cancellation_new() -> Box<ScanRunCancellation>;
        /// Requests cooperative cancellation at the next Rust-owned safe seam.
        fn scan_run_cancellation_cancel(cancellation: &ScanRunCancellation);
        /// Returns whether cancellation was requested for this control.
        fn scan_run_cancellation_is_cancelled(cancellation: &ScanRunCancellation) -> bool;
        /// Executes one tagged request and retains any opaque recovery continuation beside its result.
        ///
        /// `observer` may be null. A non-null observer must remain live for the synchronous call and its
        /// `on_scan_run_event` implementation must not throw across the CXX boundary; it reports a
        /// failed delivery by returning `ScanRunObserverDelivery{true, message}` instead.
        /// `observer_failure_policy` decides whether such a failure cancels the run. A failure
        /// before the run pauses for Local Ignore recovery abandons that recovery, so the run
        /// finishes cancelled with no pending recovery and no filesystem work. Throws only for an
        /// out-of-range policy, rejected before the run starts.
        unsafe fn scan_run_contract_execute(
            request: &ScanRunRequest,
            cancellation: &ScanRunCancellation,
            observer: *const ScanRunObserver,
            observer_failure_policy: ScanRunObserverFailurePolicy,
        ) -> Result<Box<ScanRunContractExecution>>;
        /// Moves the execution envelope out of an opaque execution operation.
        fn scan_run_contract_execution_take_result(
            execution: &mut ScanRunContractExecution,
        ) -> ScanRunContractExecutionResult;
        /// Returns whether a paused run still offers its pending recovery.
        fn scan_run_contract_execution_has_pending_recovery(
            execution: &ScanRunContractExecution,
        ) -> bool;
        /// Moves the pending recovery out of its execution operation.
        ///
        /// Throws when the run did not pause or the pending recovery was already taken. Settling
        /// it is the only way to answer a paused run (ADR-0009).
        fn scan_run_contract_execution_take_pending_recovery(
            execution: &mut ScanRunContractExecution,
        ) -> Result<Box<ScanRunPendingRecovery>>;
        /// Returns the recovery prompt Rust rendered for this pending recovery.
        fn scan_run_pending_recovery_prompt(
            pending: &ScanRunPendingRecovery,
        ) -> ScanRunRecoveryPrompt;
        /// Returns whether cancellation of the paused run was already requested.
        ///
        /// Read live from the control passed to `scan_run_contract_execute`. When true, do not
        /// prompt: settle with no decision.
        fn scan_run_pending_recovery_cancellation_requested(
            pending: &ScanRunPendingRecovery,
        ) -> bool;
        /// Settles the paused run once, synchronously, with an optional decision.
        ///
        /// No decision abandons the run: the run's own control is cancelled and the run finishes
        /// cancelled after discovery with no filesystem work. Returns the ordinary envelope,
        /// which cannot carry a continuation; a replay is the typed consumed-continuation
        /// resume error. Throws only for an out-of-range decision or policy. `observer` may be
        /// null and receives only post-discovery lifecycle events; no callback crosses for the
        /// decision. `observer_failure_policy` decides whether a failed delivery cancels the
        /// settled run; the envelope reports the failure either way.
        unsafe fn scan_run_pending_recovery_settle(
            pending: &ScanRunPendingRecovery,
            settlement: ScanRunLocalIgnoreRecoverySettlement,
            observer: *const ScanRunObserver,
            observer_failure_policy: ScanRunObserverFailurePolicy,
        ) -> Result<ScanRunContractExecutionResult>;

        /// Human-facing Display Label for one selected-file candidate provenance.
        ///
        /// It exists beside the configuration crate's own wording because cxx
        /// namespaces its shared enums per bridge module and a scan-run result
        /// carries the scanner-local mirror. Presentation only: the label is
        /// reworkable between releases, so branch on the enum and never on this
        /// string. An out-of-range enum value yields an empty string.
        fn scan_run_installed_yaml_data_provenance_label(
            provenance: ScanRunInstalledYamlDataProvenance,
        ) -> String;
        /// Human-facing Display Label for one scan-run Local Ignore state.
        /// Same stability caveat as above.
        fn scan_run_local_ignore_yaml_data_state_label(
            state: ScanRunLocalIgnoreYamlDataState,
        ) -> String;

        /// Launches a Standard Crash Log Scan from saved User Settings and `overrides`.
        ///
        /// Opens User Settings under `installation_root` read-only and never writes them; the
        /// Standard base folder is always `installation_root`. Degraded User Settings still
        /// produce a request, with their diagnostics. Throws a CXX exception only when an input
        /// cannot be represented (an empty root or path, an unknown game-version token, or an
        /// out-of-range game discriminant); typed launch errors are read through
        /// `scan_run_launch_error`. With FCX Mode on (saved or `fcx_mode`), the view's
        /// `setup_context` carries the game folder, documents folder, game executable and
        /// XSE log; an XSE log location that cannot be inspected is the typed
        /// `XseLogInspect` launch error.
        fn scan_run_launch_standard(
            installation_root: &str,
            overrides: &ScanRunLaunchOverridesDto,
        ) -> Result<Box<ScanRunLaunch>>;
        /// Launches a Targeted Crash Log Scan of exactly `inputs`, in order.
        ///
        /// An empty `inputs` list is the typed `TargetedWithoutInputs` launch error, not an
        /// exception. Otherwise behaves like `scan_run_launch_standard`.
        fn scan_run_launch_targeted(
            installation_root: &str,
            inputs: &Vec<String>,
            overrides: &ScanRunLaunchOverridesDto,
        ) -> Result<Box<ScanRunLaunch>>;
        /// Returns the typed launch error; `has_error` is false for a successful launch.
        fn scan_run_launch_error(launch: &ScanRunLaunch) -> ScanRunLaunchErrorDto;
        /// Returns the read-only view of the launched request and its diagnostics.
        ///
        /// Throws a CXX exception when the launch failed; check `scan_run_launch_error` first.
        fn scan_run_launch_view(launch: &ScanRunLaunch) -> Result<ScanRunLaunchRequestDto>;
        /// Returns an executable copy of the launched request for `scan_run_contract_execute`.
        ///
        /// Throws a CXX exception when the launch failed; check `scan_run_launch_error` first.
        fn scan_run_launch_request(launch: &ScanRunLaunch) -> Result<Box<ScanRunRequest>>;

        // Papyrus monitoring
        type CxxPapyrusAnalyzer;
        fn papyrus_analyzer_new(log_path: &str) -> Box<CxxPapyrusAnalyzer>;
        fn papyrus_start_monitoring(analyzer: &mut CxxPapyrusAnalyzer) -> Result<()>;
        fn papyrus_check_updates(analyzer: &mut CxxPapyrusAnalyzer) -> PapyrusStatsDto;
        fn papyrus_log_exists(analyzer: &CxxPapyrusAnalyzer) -> bool;
    }
}
