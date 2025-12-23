//! CLASSIC Scanlog Core - Pure Rust business logic for log parsing and analysis
//!
//! This crate provides high-performance crash log analysis with:
//! - Fast log parsing with pattern matching
//! - FormID extraction and validation
//! - Plugin and record detection
//! - Mod detection algorithms
//! - Parallel batch processing
//! - Report generation
//!
//! **NO PyO3 DEPENDENCIES** - Pure Rust business logic only.
//! For Python bindings, see `classic-scanlog-py`.

// Re-export all public modules
pub mod error;
pub mod fcx_handler;
pub mod formid;
pub mod formid_analyzer;
pub mod gpu_detector;
pub mod mod_detector;
pub mod orchestrator;
pub mod papyrus;
pub mod parser;
pub mod patterns;
pub mod plugin_analyzer;
pub mod record_scanner;
pub mod report;
pub mod settings_validator;
pub mod suspect_scanner;
pub mod version;

// Re-export key types for convenience
pub use error::ScanLogError;
pub use fcx_handler::{ConfigIssue, FcxModeHandler, GLOBAL_FCX_HANDLER};
pub use formid::{FormIDAnalyzer, RustFormIDAnalyzer};
pub use formid_analyzer::{
    FormIDAnalyzerCore, extract_formids_batch, is_valid_formid, validate_formids_batch,
};
pub use gpu_detector::{GpuDetector, GpuInfo, GpuVendor};
pub use mod_detector::{
    detect_mods_batch, detect_mods_double, detect_mods_important, detect_mods_single,
};
pub use orchestrator::{AnalysisConfig, AnalysisResult, OrchestratorCore};
pub use papyrus::{PapyrusAnalyzer, PapyrusError, PapyrusStats};
pub use parser::{LogParser, StreamingIteratorParser, StreamingLogParser};
pub use patterns::PatternMatcher;
pub use plugin_analyzer::{PluginAnalyzer, contains_plugin, detect_plugins_batch};
pub use record_scanner::{RecordScanner, contains_record, scan_records_batch};
pub use report::{ReportComposer, ReportFragment, ReportGenerator, StringPool};
pub use settings_validator::SettingsValidator;
pub use suspect_scanner::SuspectScanner;
pub use version::{CrashgenVersion, crashgen_version_gen};

/// Detect if a crash log is from Fallout 4 VR.
///
/// Checks for the presence of Fallout4VR.exe or Fallout4VR.esm
/// in the log content, case-insensitively.
pub fn detect_vr_log(content: &str) -> bool {
    let lower = content.to_lowercase();
    lower.contains("fallout4vr.exe") || lower.contains("fallout4vr.esm")
}
