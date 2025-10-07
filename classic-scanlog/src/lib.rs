//! CLASSIC Scanlog - High-performance log parsing and analysis
//!
//! This crate provides optimized crash log analysis with:
//! - Fast log parsing with pattern matching
//! - FormID extraction and validation
//! - Plugin and record detection
//! - Mod detection algorithms
//! - Parallel batch processing
//! - Report generation

use pyo3::prelude::*;

pub mod formid;
pub mod formid_analyzer;
pub mod mod_detector;
pub mod orchestrator;
pub mod parser;
pub mod patterns;
pub mod plugin_analyzer;
pub mod record_scanner;
pub mod report;
pub mod test_class;

pub use formid::{FormIDAnalyzer, RustFormIDAnalyzer};
pub use formid_analyzer::{FormIDAnalyzerCore, extract_formids_batch, is_valid_formid, validate_formids_batch};
pub use mod_detector::{detect_mods_single, detect_mods_double, detect_mods_important, detect_mods_batch};
pub use orchestrator::{RustOrchestrator, AnalysisConfig, AnalysisResult};
pub use parser::LogParser;
pub use patterns::PatternMatcher;
pub use plugin_analyzer::{PluginAnalyzer, detect_plugins_batch, contains_plugin};
pub use record_scanner::{RecordScanner, scan_records_batch, contains_record};
pub use report::{ReportFragment, ReportComposer, ReportGenerator, StringPool, ParallelReportProcessor};
pub use test_class::TestClass;

/// Python module initialization
#[pymodule]
fn classic_scanlog(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FormIDAnalyzer>()?;
    m.add_class::<RustFormIDAnalyzer>()?;
    m.add_class::<FormIDAnalyzerCore>()?;
    m.add_class::<LogParser>()?;
    m.add_class::<PatternMatcher>()?;
    m.add_class::<PluginAnalyzer>()?;
    m.add_class::<RecordScanner>()?;

    // Add orchestrator classes
    m.add_class::<RustOrchestrator>()?;
    m.add_class::<AnalysisConfig>()?;
    m.add_class::<AnalysisResult>()?;

    // Add report generation classes
    m.add_class::<StringPool>()?;
    m.add_class::<ReportFragment>()?;
    m.add_class::<ReportComposer>()?;
    m.add_class::<ReportGenerator>()?;
    m.add_class::<ParallelReportProcessor>()?;

    // Add test classes
    m.add_class::<TestClass>()?;

    // Add standalone functions
    m.add_function(wrap_pyfunction!(extract_formids_batch, m)?)?;
    m.add_function(wrap_pyfunction!(is_valid_formid, m)?)?;
    m.add_function(wrap_pyfunction!(validate_formids_batch, m)?)?;
    m.add_function(wrap_pyfunction!(scan_records_batch, m)?)?;
    m.add_function(wrap_pyfunction!(contains_record, m)?)?;
    m.add_function(wrap_pyfunction!(detect_plugins_batch, m)?)?;
    m.add_function(wrap_pyfunction!(contains_plugin, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_single, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_double, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_important, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_batch, m)?)?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
