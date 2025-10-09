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
pub mod parser;
pub mod formid;
pub mod formid_analyzer;
pub mod patterns;
pub mod plugin_analyzer;
pub mod record_scanner;
pub mod mod_detector;
pub mod suspect_scanner;
pub mod settings_validator;
pub mod gpu_detector;
pub mod fcx_handler;
pub mod orchestrator;
pub mod report;

// Re-export key types for convenience
pub use error::ScanLogError;
pub use parser::LogParser;
pub use formid::{FormIDAnalyzer, RustFormIDAnalyzer};
pub use formid_analyzer::{FormIDAnalyzerCore, extract_formids_batch, is_valid_formid, validate_formids_batch};
pub use patterns::PatternMatcher;
pub use plugin_analyzer::{PluginAnalyzer, detect_plugins_batch, contains_plugin};
pub use record_scanner::{RecordScanner, scan_records_batch, contains_record};
pub use mod_detector::{detect_mods_single, detect_mods_double, detect_mods_important, detect_mods_batch};
pub use suspect_scanner::SuspectScanner;
pub use settings_validator::SettingsValidator;
pub use gpu_detector::{GpuDetector, GpuInfo, GpuVendor};
pub use fcx_handler::FcxModeHandler;
pub use orchestrator::{OrchestratorCore, AnalysisConfig, AnalysisResult};
pub use report::{ReportFragment, ReportComposer, ReportGenerator, StringPool};
