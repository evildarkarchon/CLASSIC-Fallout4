//! Crash log scanning bridge for CXX FFI.
//!
//! Exposes the final Rust-owned Crash Log Scan Run contract plus independent
//! crash-log parsing and Papyrus utilities.
//!
//! The CXX bridge declarations stay in this façade module while implementation
//! concerns live in private scanner submodules.

mod analyzer;
mod contract;
mod papyrus;
mod util;

pub(crate) use analyzer::{
    CxxCrashSuspectAnalyzer, CxxCrashgenSettingsAnalyzer, crash_suspect_analyze,
    crash_suspect_analyzer_construction_result, crash_suspect_analyzer_new,
    crashgen_settings_analyze, crashgen_settings_analyzer_construction_result,
    crashgen_settings_analyzer_new,
};
pub(crate) use contract::{
    ScanRunCancellation, ScanRunRequest, ScanRunUnsolvedLogs, scan_run_cancellation_cancel,
    scan_run_cancellation_is_cancelled, scan_run_cancellation_new, scan_run_contract_execute,
    scan_run_request_standard, scan_run_request_standard_with_fcx, scan_run_request_targeted,
    scan_run_request_targeted_with_fcx, scan_run_unsolved_logs_leave_in_place,
    scan_run_unsolved_logs_move_to_configured_or_default, scan_run_unsolved_logs_move_to_custom,
};
pub(crate) use papyrus::{
    CxxPapyrusAnalyzer, papyrus_analyze_full, papyrus_analyzer_new, papyrus_check_updates,
    papyrus_log_exists, papyrus_reset, papyrus_start_monitoring,
};
pub(crate) use util::{detect_crash_pattern, detect_vr_log};

#[cxx::bridge(namespace = "classic::scanner")]
mod ffi {
    /// Focused semantic analyzer identity shared across language bindings.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum AnalyzerKind {
        CrashgenSettings = 0,
        CrashSuspect = 1,
        ModGuidance = 2,
        PluginEvidence = 3,
        FormIdFinding = 4,
        NamedRecordFinding = 5,
    }

    /// Stable machine-readable category for a focused analyzer failure.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum AnalyzerErrorCode {
        InvalidConfiguration = 0,
        UnsupportedConfigurationVersion = 1,
    }

    /// Semantic category of one Crashgen Expectation Outcome.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum CrashgenExpectationOutcomeKind {
        Notice = 0,
        Issue = 1,
        Success = 2,
    }

    /// Authored severity retained from a Crashgen Expectation.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum CrashgenExpectationSeverity {
        Info = 0,
        Warning = 1,
        Error = 2,
    }

    /// YAML-owned Autoscan Report destination for one expectation outcome.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum AutoscanReportPlacement {
        Settings = 0,
        ErrorInformation = 1,
    }

    /// Detected layout of the analyzed Crashgen configuration.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum CrashgenConfigLayout {
        Og = 0,
        Vr = 1,
        Unknown = 2,
    }

    /// Evidence source that produced one Crash Suspect Finding.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum CrashSuspectFindingKind {
        MainErrorRule = 0,
        StackRule = 1,
        DllInvolvement = 2,
    }

    /// Shared typed focused-analyzer error envelope payload.
    struct AnalyzerErrorDto {
        analyzer_kind: AnalyzerKind,
        code: AnalyzerErrorCode,
        message: String,
    }

    /// Owned configuration used to construct an immutable Crashgen Settings Analyzer.
    struct CrashgenSettingsAnalyzerConfigurationDto {
        crashgen_name: String,
        display_section: String,
        ignore_keys: Vec<String>,
        has_settings_rules: bool,
        has_settings_rules_version: bool,
        settings_rules_version: u32,
        settings_rules_json: String,
    }

    /// Explicit constructor status for an opaque Crashgen Settings Analyzer handle.
    ///
    /// Exactly one presence flag is true. When `has_error` is false, the
    /// placeholder `error` fields must be ignored.
    struct CrashgenSettingsAnalyzerConstructionResultDto {
        has_analyzer: bool,
        has_error: bool,
        error: AnalyzerErrorDto,
    }

    /// One owned final Crashgen setting supplied for semantic analysis.
    struct CrashgenSettingDto {
        has_section: bool,
        section: String,
        key: String,
        value: String,
    }

    /// Owned input for one aggregate Crashgen Settings Analysis call.
    struct CrashgenSettingsAnalysisInputDto {
        settings: Vec<CrashgenSettingDto>,
        installed_plugins: Vec<String>,
        has_crashgen_version: bool,
        crashgen_version_major: u32,
        crashgen_version_minor: u32,
        crashgen_version_patch: u32,
        config_layout: CrashgenConfigLayout,
    }

    /// One typed, unrendered result from a YAML-authored Crashgen Expectation.
    struct CrashgenExpectationOutcomeDto {
        rule_id: String,
        kind: CrashgenExpectationOutcomeKind,
        severity: CrashgenExpectationSeverity,
        message: String,
        has_fix: bool,
        fix: String,
        placement: AutoscanReportPlacement,
        has_section: bool,
        section: String,
        has_setting: bool,
        setting: String,
        has_expected: bool,
        expected: String,
        has_actual: bool,
        actual: String,
    }

    /// One universal notice for a non-ignored disabled Crashgen setting.
    struct DisabledSettingNoticeDto {
        setting_name: String,
    }

    /// Completed aggregate Crashgen Settings Analysis, including explicit empty success.
    struct CrashgenSettingsAnalysisResultDto {
        expectation_outcomes: Vec<CrashgenExpectationOutcomeDto>,
        disabled_setting_notices: Vec<DisabledSettingNoticeDto>,
    }

    /// Exactly one typed analysis result or typed analyzer error.
    ///
    /// Presence flags are authoritative; fields in the absent branch contain
    /// placeholders required by CXX shared DTOs.
    struct CrashgenSettingsAnalysisExecutionResultDto {
        has_result: bool,
        result: CrashgenSettingsAnalysisResultDto,
        has_error: bool,
        error: AnalyzerErrorDto,
    }

    /// One minimum-occurrence condition in a Crash Suspect stack rule.
    struct CrashSuspectStackCountRuleDto {
        substring: String,
        count: usize,
    }

    /// One owned main-error rule used to construct a Crash Suspect Analyzer.
    struct CrashSuspectMainErrorRuleDto {
        id: String,
        name: String,
        severity: i32,
        main_error_contains_any: Vec<String>,
    }

    /// One owned stack rule used to construct a Crash Suspect Analyzer.
    struct CrashSuspectStackRuleDto {
        id: String,
        name: String,
        severity: i32,
        main_error_required_any: Vec<String>,
        main_error_optional_any: Vec<String>,
        stack_contains_any: Vec<String>,
        exclude_if_stack_contains_any: Vec<String>,
        stack_contains_at_least: Vec<CrashSuspectStackCountRuleDto>,
    }

    /// Owned configuration for one immutable Crash Suspect Analyzer.
    struct CrashSuspectAnalyzerConfigurationDto {
        main_error_rules: Vec<CrashSuspectMainErrorRuleDto>,
        stack_rules: Vec<CrashSuspectStackRuleDto>,
    }

    /// Explicit constructor status for an opaque Crash Suspect Analyzer handle.
    struct CrashSuspectAnalyzerConstructionResultDto {
        has_analyzer: bool,
        has_error: bool,
        error: AnalyzerErrorDto,
    }

    /// Owned input for one aggregate Crash Suspect analysis call.
    struct CrashSuspectAnalysisInputDto {
        main_error: String,
        call_stack: String,
    }

    /// One semantic Crash Suspect Finding without report presentation fields.
    struct CrashSuspectFindingDto {
        kind: CrashSuspectFindingKind,
        has_rule_id: bool,
        rule_id: String,
        has_name: bool,
        name: String,
        has_severity: bool,
        severity: i32,
    }

    /// Completed Crash Suspect analysis, including explicit empty success.
    struct CrashSuspectAnalysisResultDto {
        findings: Vec<CrashSuspectFindingDto>,
    }

    /// Exactly one typed Crash Suspect result or shared analyzer error.
    struct CrashSuspectAnalysisExecutionResultDto {
        has_result: bool,
        result: CrashSuspectAnalysisResultDto,
        has_error: bool,
        error: AnalyzerErrorDto,
    }

    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractProgressPhase {
        Setup = 0,
        Parse = 1,
        Analyze = 2,
        Finalize = 3,
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
        yaml_dir_root: String,
        yaml_dir_data: String,
        game: String,
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

    /// Run-scoped FCX setup facts required by FCX request constructors.
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

    /// Stable lifecycle status from the final Crash Log Scan Run contract.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ScanRunContractStatus {
        Completed = 0,
        NoCrashLogsFound = 1,
        SetupFailed = 2,
        CancelledBeforeDiscovery = 3,
        Cancelled = 4,
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

    /// Complete terminal result from the final Crash Log Scan Run contract.
    struct ScanRunContractRunResult {
        status: ScanRunContractStatus,
        has_discovery: bool,
        discovery: ScanRunContractDiscoveryResult,
        has_setup: bool,
        setup: ScanRunContractSetupResult,
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

    /// Exactly one of `result` or `error`, identified by the presence flags.
    struct ScanRunContractExecutionResult {
        has_result: bool,
        result: ScanRunContractRunResult,
        has_error: bool,
        error: ScanRunContractInfrastructureError,
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
        fn on_scan_run_event(self: &ScanRunObserver, event: &ScanRunContractEvent);
    }

    extern "Rust" {
        type CxxCrashSuspectAnalyzer;
        type CxxCrashgenSettingsAnalyzer;
        type ScanRunRequest;
        type ScanRunUnsolvedLogs;
        type ScanRunCancellation;

        /// Constructs and validates an immutable analyzer handle from owned configuration.
        ///
        /// The handle retains a typed construction error when parsing, validation, or
        /// matcher compilation fails. Call `crashgen_settings_analyzer_construction_result`
        /// before analysis to inspect that status without relying on CXX exceptions.
        fn crashgen_settings_analyzer_new(
            configuration: CrashgenSettingsAnalyzerConfigurationDto,
        ) -> Box<CxxCrashgenSettingsAnalyzer>;
        /// Returns the typed success/error status captured during analyzer construction.
        fn crashgen_settings_analyzer_construction_result(
            analyzer: &CxxCrashgenSettingsAnalyzer,
        ) -> CrashgenSettingsAnalyzerConstructionResultDto;
        /// Runs one aggregate semantic analysis over owned input.
        ///
        /// The immutable handle may be reused concurrently. Invalid construction and
        /// analysis failures are returned through the explicit typed error envelope.
        fn crashgen_settings_analyze(
            analyzer: &CxxCrashgenSettingsAnalyzer,
            input: CrashgenSettingsAnalysisInputDto,
        ) -> CrashgenSettingsAnalysisExecutionResultDto;

        /// Constructs and validates an immutable Crash Suspect Analyzer handle.
        fn crash_suspect_analyzer_new(
            configuration: CrashSuspectAnalyzerConfigurationDto,
        ) -> Box<CxxCrashSuspectAnalyzer>;
        /// Returns the typed status captured during Crash Suspect construction.
        fn crash_suspect_analyzer_construction_result(
            analyzer: &CxxCrashSuspectAnalyzer,
        ) -> CrashSuspectAnalyzerConstructionResultDto;
        /// Runs one aggregate Crash Suspect analysis over owned input.
        fn crash_suspect_analyze(
            analyzer: &CxxCrashSuspectAnalyzer,
            input: CrashSuspectAnalysisInputDto,
        ) -> CrashSuspectAnalysisExecutionResultDto;

        /// Creates Standard intent that leaves failed Crash Logs and reports in place.
        fn scan_run_unsolved_logs_leave_in_place() -> Box<ScanRunUnsolvedLogs>;
        /// Creates Standard intent that moves eligible artifacts to the configured or default destination.
        fn scan_run_unsolved_logs_move_to_configured_or_default() -> Box<ScanRunUnsolvedLogs>;
        /// Creates caller-selected Standard movement intent; rejects an empty destination.
        fn scan_run_unsolved_logs_move_to_custom(
            destination: &str,
        ) -> Result<Box<ScanRunUnsolvedLogs>>;
        /// Constructs a non-FCX Standard request from shared configuration and source facts.
        ///
        /// Throws a CXX exception when a required path or game identifier cannot be represented;
        /// zero concurrency is deferred to the typed execution envelope.
        fn scan_run_request_standard(
            configuration: &ScanRunConfigurationDto,
            source: &ScanRunStandardSourceDto,
            unsolved_logs: &ScanRunUnsolvedLogs,
        ) -> Result<Box<ScanRunRequest>>;
        /// Constructs an FCX Standard request whose setup context remains run-scoped.
        ///
        /// Throws a CXX exception when required configuration, source, or setup values cannot be represented.
        fn scan_run_request_standard_with_fcx(
            configuration: &ScanRunConfigurationDto,
            source: &ScanRunStandardSourceDto,
            unsolved_logs: &ScanRunUnsolvedLogs,
            setup_context: &ScanRunSetupContextDto,
        ) -> Result<Box<ScanRunRequest>>;
        /// Constructs a non-FCX Targeted request, which cannot express Unsolved Logs movement.
        ///
        /// Throws a CXX exception when required configuration values cannot be represented.
        fn scan_run_request_targeted(
            configuration: &ScanRunConfigurationDto,
            source: &ScanRunTargetedSourceDto,
        ) -> Result<Box<ScanRunRequest>>;
        /// Constructs an FCX Targeted request with required run-scoped setup facts and no movement capability.
        ///
        /// Throws a CXX exception when required configuration or setup values cannot be represented.
        fn scan_run_request_targeted_with_fcx(
            configuration: &ScanRunConfigurationDto,
            source: &ScanRunTargetedSourceDto,
            setup_context: &ScanRunSetupContextDto,
        ) -> Result<Box<ScanRunRequest>>;
        /// Creates a new uncancelled monotonic control; final-contract cancellation cannot be reset.
        fn scan_run_cancellation_new() -> Box<ScanRunCancellation>;
        /// Requests cooperative cancellation at the next Rust-owned safe seam.
        fn scan_run_cancellation_cancel(cancellation: &ScanRunCancellation);
        /// Returns whether cancellation was requested for this control.
        fn scan_run_cancellation_is_cancelled(cancellation: &ScanRunCancellation) -> bool;
        /// Executes one tagged request and returns either a terminal result or typed infrastructure error.
        ///
        /// `observer` may be null. A non-null observer must remain live for the synchronous call and its
        /// `on_scan_run_event` implementation must not throw across the CXX boundary.
        unsafe fn scan_run_contract_execute(
            request: &ScanRunRequest,
            cancellation: &ScanRunCancellation,
            observer: *const ScanRunObserver,
        ) -> ScanRunContractExecutionResult;

        // Utilities
        fn detect_vr_log(content: &str) -> bool;
        fn detect_crash_pattern(content: &str) -> String;

        // Papyrus monitoring
        type CxxPapyrusAnalyzer;
        fn papyrus_analyzer_new(log_path: &str) -> Box<CxxPapyrusAnalyzer>;
        fn papyrus_start_monitoring(analyzer: &mut CxxPapyrusAnalyzer) -> Result<()>;
        fn papyrus_check_updates(analyzer: &mut CxxPapyrusAnalyzer) -> PapyrusStatsDto;
        fn papyrus_analyze_full(analyzer: &mut CxxPapyrusAnalyzer) -> Result<PapyrusStatsDto>;
        fn papyrus_log_exists(analyzer: &CxxPapyrusAnalyzer) -> bool;
        fn papyrus_reset(analyzer: &mut CxxPapyrusAnalyzer);
    }
}
