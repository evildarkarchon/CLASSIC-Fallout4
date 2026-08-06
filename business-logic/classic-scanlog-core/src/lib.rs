//! CLASSIC Scanlog Core - Pure Rust business logic for log parsing and analysis
//!
//! This crate provides high-performance crash log analysis with:
//! - Fast log parsing with pattern matching
//! - FormID extraction and validation
//! - Plugin and record detection
//! - Mod detection algorithms
//! - Rust-owned Crash Log Scan Run execution
//! - Report generation
//!
//! **NO PyO3 DEPENDENCIES** - Pure Rust business logic only.
//! For Python bindings, see `classic-scanlog-py`.
//!
//! # Optional Features
//!
//! - `mimalloc`: Use mimalloc as the global allocator for improved performance
//!   (Phase 16 optimization). Enable with `--features mimalloc`.

// Phase 16 optimization: Use mimalloc as global allocator when feature is enabled
// mimalloc provides better performance for allocation-heavy workloads
#[cfg(feature = "mimalloc")]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

// Public utility modules and the final Crash Log Scan Run contract.
pub mod analyzer;
pub(crate) mod autoscan_report_contribution_collector;
pub mod crash_suspect_analyzer;
pub mod crashgen_registry;
pub mod crashgen_settings_analyzer;
pub mod error;
pub(crate) mod fcx_handler;
pub mod formid;
pub mod formid_analyzer;
pub mod formid_finding_analyzer;
pub mod gpu_detector;
pub mod mod_guidance_analyzer;
pub mod named_record_finding_analyzer;
// These implementation modules retain focused characterization helpers that are
// exercised only in their sibling unit tests.
#[allow(dead_code)]
pub(crate) mod orchestrator;
pub mod papyrus;
pub mod parser;
pub mod patterns;
pub mod plugin_analyzer;
pub mod plugin_evidence_analyzer;
pub mod record_scanner;
pub(crate) mod report;
#[allow(dead_code)]
pub(crate) mod scan_intake;
pub mod scan_run;
mod scan_sidecar_settings;
pub mod segment_key;
pub mod version;

// Re-export key types for convenience
pub use analyzer::{AnalyzerError, AnalyzerErrorCode, AnalyzerKind, AnalyzerResult};
pub use crash_suspect_analyzer::{
    CrashSuspectAnalysisInput, CrashSuspectAnalysisResult, CrashSuspectAnalyzer,
    CrashSuspectFinding, CrashSuspectFindingKind,
};
pub use crashgen_registry::{CrashgenEntry, CrashgenRegistry};
pub use crashgen_settings_analyzer::{
    CrashgenExpectationOutcome, CrashgenSettingsAnalysisInput, CrashgenSettingsAnalysisResult,
    CrashgenSettingsAnalyzer, DisabledSettingNotice,
};
pub use error::ScanLogError;
pub use fcx_handler::ConfigIssue;
pub use formid::{FormIDAnalyzer, RustFormIDAnalyzer};
pub use formid_analyzer::{extract_formids_batch, is_valid_formid, validate_formids_batch};
pub use formid_finding_analyzer::{
    FormIDFinding, FormIDFindingAnalysisInput, FormIDFindingAnalysisResult, FormIDFindingAnalyzer,
    FormIDPlugin, FormIDValueLookupStatus,
};
pub use gpu_detector::{GpuDetector, GpuInfo, GpuVendor};
pub use mod_guidance_analyzer::{
    ImportantModGuidance, ModConflictGuidance, ModGuidanceAnalysisInput, ModGuidanceAnalysisResult,
    ModGuidanceAnalyzer, ModGuidanceMatchState, ModSolutionGuidance,
};
pub use named_record_finding_analyzer::{
    NamedRecordFinding, NamedRecordFindingAnalysisInput, NamedRecordFindingAnalysisResult,
    NamedRecordFindingAnalyzer,
};
pub use orchestrator::ScanProgressPhase;
pub(crate) use orchestrator::{AnalysisConfig, AnalysisResult, OrchestratorCore};
pub use papyrus::{PapyrusAnalyzer, PapyrusError, PapyrusStats};
pub use parser::{LogParser, StreamingIteratorParser, StreamingLogParser};
pub use patterns::PatternMatcher;
pub use plugin_analyzer::{PluginAnalyzer, contains_plugin, detect_plugins_batch};
pub use plugin_evidence_analyzer::{
    PluginEvidence, PluginEvidenceAnalysisInput, PluginEvidenceAnalysisResult,
    PluginEvidenceAnalyzer,
};
pub use record_scanner::{
    RecordScanner, contains_record, scan_records_batch, try_scan_records_batch,
};
pub use scan_intake::{CrashLogScanFacts, CrashLogScanOptions};
pub(crate) use scan_intake::{CrashLogScanIntake, ScanReadyAnalysis};
pub use scan_run::{
    CrashLogScanDiscoveryResult, CrashLogScanDiscoverySource, CrashLogScanRejectedInput,
    CrashLogScanRunStatus, CrashLogScanSetupCheck, CrashLogScanSetupContext,
    CrashLogScanSetupPathUpdate, CrashLogScanSetupResult, StandardCrashLogScanSource,
    StandardUnsolvedLogsIntent, TargetedCrashLogScanSource,
};
pub use version::{
    CrashgenVersion, CrashgenVersionStatus, check_crashgen_version_status,
    check_crashgen_version_status_with_exceptions, crashgen_version_gen,
};

/// Detect if a crash log is from Fallout 4 VR.
///
/// Checks for the presence of Fallout4VR.exe or Fallout4VR.esm
/// in the log content, case-insensitively.
pub fn detect_vr_log(content: &str) -> bool {
    let lower = content.to_lowercase();
    lower.contains("fallout4vr.exe") || lower.contains("fallout4vr.esm")
}
