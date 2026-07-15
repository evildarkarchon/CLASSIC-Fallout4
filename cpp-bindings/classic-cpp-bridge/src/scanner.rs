//! Crash log scanning bridge for CXX FFI.
//!
//! Bridges `classic_scanlog_core::OrchestratorCore` for crash log analysis.
//! This is the PRIMARY FEATURE of the CLASSIC application.
//!
//! The CXX bridge declarations stay in this façade module while implementation
//! concerns live in private scanner submodules.

mod contract;
mod dto;
mod orchestrator;
mod papyrus;
mod progress;
mod util;

pub(crate) use contract::{
    ScanRunCancellation, ScanRunRequest, ScanRunUnsolvedLogs, scan_run_cancellation_cancel,
    scan_run_cancellation_is_cancelled, scan_run_cancellation_new, scan_run_contract_execute,
    scan_run_request_standard, scan_run_request_standard_with_fcx, scan_run_request_targeted,
    scan_run_request_targeted_with_fcx, scan_run_unsolved_logs_leave_in_place,
    scan_run_unsolved_logs_move_to_configured_or_default, scan_run_unsolved_logs_move_to_custom,
};
pub(crate) use orchestrator::{
    FullScanConfig, Orchestrator, ScanCancellationToken, build_full_scan_config,
    fcx_reset_global_state, get_fcx_config_issues, orchestrator_new, orchestrator_new_minimal,
    orchestrator_process_log, orchestrator_process_logs_batch,
    orchestrator_process_logs_batch_with_progress, scan_cancellation_token_cancel,
    scan_cancellation_token_new, scan_cancellation_token_reset, scan_run_execute,
};
pub(crate) use papyrus::{
    CxxPapyrusAnalyzer, papyrus_analyze_full, papyrus_analyzer_new, papyrus_check_updates,
    papyrus_log_exists, papyrus_reset, papyrus_start_monitoring,
};
pub(crate) use util::{detect_crash_pattern, detect_vr_log};

#[cxx::bridge(namespace = "classic::scanner")]
mod ffi {
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum BatchProgressEventKind {
        Queued = 0,
        Started = 1,
        Phase = 2,
        Completed = 3,
        Failed = 4,
    }

    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum BatchProgressPhase {
        Setup = 0,
        Parse = 1,
        Analyze = 2,
        Finalize = 3,
    }

    struct BatchProgressEvent {
        completed: u32,
        total: u32,
        input_index: u32,
        log_path: String,
        event_kind: BatchProgressEventKind,
        phase: BatchProgressPhase,
        success: bool,
    }

    /// Result of scanning a single crash log.
    struct ScanResult {
        log_path: String,
        success: bool,
        report_lines: Vec<String>,
        error_message: String,
        processing_time_ms: u64,
        formid_count: u32,
        plugin_count: u32,
        suspect_count: u32,
    }

    /// Batch scan result plus progress metadata for each completed log.
    struct BatchScanResult {
        input_index: u32,
        completed: u32,
        total: u32,
        log_path: String,
        success: bool,
        report_lines: Vec<String>,
        error_message: String,
        processing_time_ms: u64,
        formid_count: u32,
        plugin_count: u32,
        suspect_count: u32,
    }

    /// Per-log result from a full Crash Log Scan Run.
    struct ScanRunLogResult {
        input_index: u32,
        log_path: String,
        autoscan_report_path: String,
        success: bool,
        report_write_failed: bool,
        cancelled: bool,
        moved_to_unsolved_logs: bool,
        error_message: String,
        processing_time_ms: u64,
        formid_count: u32,
        plugin_count: u32,
        suspect_count: u32,
    }

    /// Discovery details from a full Crash Log Scan Run.
    struct ScanRunDiscoveryResult {
        source: String,
        accepted_logs: Vec<String>,
        rejected_paths: Vec<String>,
        rejected_reasons: Vec<String>,
        searched_locations: Vec<String>,
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

    /// Setup details from a full Crash Log Scan Run.
    struct ScanRunSetupResultDto {
        status: String,
        message: String,
        rendered_report: String,
        checks: Vec<ScanRunSetupCheckDto>,
        path_updates: Vec<ScanRunSetupPathUpdateDto>,
        configuration_issues: Vec<FcxIssueDto>,
        actions: Vec<String>,
        fatal_errors: Vec<String>,
    }

    /// Top-level result from a full Crash Log Scan Run.
    struct ScanRunResult {
        status: String,
        message: String,
        total: u32,
        succeeded: u32,
        failed: u32,
        cancelled: u32,
        discovery: ScanRunDiscoveryResult,
        has_setup: bool,
        setup: ScanRunSetupResultDto,
        logs: Vec<ScanRunLogResult>,
    }

    /// Structured input to `scan_run_execute`.
    struct ScanRunRequestDto {
        yaml_dir_root: String,
        yaml_dir_data: String,
        game: String,
        game_version: String,
        base_directory: String,
        custom_scan_directory: String,
        configured_documents_root: String,
        show_formid_values: bool,
        formid_database_paths: Vec<String>,
        fcx_mode: bool,
        simplify_logs: bool,
        move_unsolved_logs: bool,
        unsolved_logs_destination: String,
        targeted_mode: bool,
        setup_game_root: String,
        setup_docs_root: String,
        setup_game_exe_path: String,
        setup_xse_log_path: String,
        max_concurrent: u32,
        targeted_inputs: Vec<String>,
        log_paths: Vec<String>,
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
        phase: BatchProgressPhase,
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

    /// Mirrors `classic_scanlog_core::fcx_handler::ConfigIssue` field-for-field (CXXS-03).
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
        include!("classic_cxx_bridge/scan_progress_callback.h");
        include!("classic_cxx_bridge/scan_run_observer.h");
        type ScanBatchProgressCallback;
        type ScanRunObserver;
        fn on_batch_progress(self: &ScanBatchProgressCallback, event: &BatchProgressEvent);
        fn on_scan_run_event(self: &ScanRunObserver, event: &ScanRunContractEvent);
    }

    extern "Rust" {
        type FullScanConfig;
        type Orchestrator;
        type ScanCancellationToken;
        type ScanRunRequest;
        type ScanRunUnsolvedLogs;
        type ScanRunCancellation;

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

        // Config construction
        fn build_full_scan_config(
            yaml_dir_root: &str,
            yaml_dir_data: &str,
            game: &str,
            game_version: &str,
            show_formid_values: bool,
            fcx_mode: bool,
            simplify_logs: bool,
        ) -> Result<Box<FullScanConfig>>;

        // Orchestrator
        fn orchestrator_new(config: &FullScanConfig) -> Result<Box<Orchestrator>>;
        fn orchestrator_new_minimal(
            game: &str,
            game_version: &str,
            crashgen_name: &str,
            xse_acronym: &str,
        ) -> Result<Box<Orchestrator>>;
        fn fcx_reset_global_state() -> Result<()>;
        /// Return a snapshot of all FCX configuration issues from the global handler (CXXS-03).
        /// Empty Vec when no scan has run, after a reset, or when no issues were detected.
        fn get_fcx_config_issues() -> Vec<FcxIssueDto>;
        fn scan_cancellation_token_new() -> Box<ScanCancellationToken>;
        fn scan_cancellation_token_cancel(token: &ScanCancellationToken);
        fn scan_cancellation_token_reset(token: &ScanCancellationToken);
        fn orchestrator_process_log(orch: &Orchestrator, log_path: &str) -> Result<ScanResult>;
        fn orchestrator_process_logs_batch(
            orch: &Orchestrator,
            log_paths: &[String],
            max_concurrent: u32,
        ) -> Vec<ScanResult>;
        fn orchestrator_process_logs_batch_with_progress(
            orch: &Orchestrator,
            log_paths: &[String],
            max_concurrent: u32,
            callback: &ScanBatchProgressCallback,
        ) -> Vec<BatchScanResult>;
        fn scan_run_execute(
            request: &ScanRunRequestDto,
            callback: &ScanBatchProgressCallback,
            cancellation_token: &ScanCancellationToken,
        ) -> Result<ScanRunResult>;

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
