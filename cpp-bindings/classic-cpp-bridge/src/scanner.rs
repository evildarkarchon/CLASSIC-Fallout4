//! Crash log scanning bridge for CXX FFI.
//!
//! Bridges `classic_scanlog_core::OrchestratorCore` for crash log analysis.
//! This is the PRIMARY FEATURE of the CLASSIC application.
//!
//! The CXX bridge declarations stay in this façade module while implementation
//! concerns live in private scanner submodules.

mod dto;
mod orchestrator;
mod papyrus;
mod progress;
mod util;

pub(crate) use orchestrator::{
    FullScanConfig, Orchestrator, build_full_scan_config, fcx_reset_global_state,
    get_fcx_config_issues, orchestrator_new, orchestrator_new_minimal, orchestrator_process_log,
    orchestrator_process_logs_batch, orchestrator_process_logs_batch_with_progress,
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
        type ScanBatchProgressCallback;
        fn on_batch_progress(self: &ScanBatchProgressCallback, event: &BatchProgressEvent);
    }

    extern "Rust" {
        type FullScanConfig;
        type Orchestrator;

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
