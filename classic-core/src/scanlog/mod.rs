//! Scan log module - High-performance log parsing and pattern matching

use pyo3::prelude::*;

pub mod formid;
pub mod formid_analyzer;
pub mod mod_detector;
pub mod parser;
pub mod patterns;
pub mod plugin_analyzer;
pub mod record_scanner;
pub mod report;
pub mod test_class;

pub use formid::FormIDAnalyzer;
pub use formid_analyzer::{
    extract_formids_batch, is_valid_formid, validate_formids_batch, FormIDAnalyzerCore,
};
pub use mod_detector::{
    detect_mods_batch, detect_mods_double, detect_mods_important, detect_mods_single,
};
pub use parser::LogParser;
pub use patterns::PatternMatcher;
pub use plugin_analyzer::{contains_plugin, detect_plugins_batch, PluginAnalyzer};
pub use record_scanner::{contains_record, scan_records_batch, RecordScanner};
pub use report::{
    ParallelReportProcessor, ReportComposer, ReportFragment, ReportGenerator, StringPool,
};
pub use test_class::TestClass;

/// Register the scanlog module with Python
pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FormIDAnalyzer>()?;
    m.add_class::<FormIDAnalyzerCore>()?;
    m.add_class::<LogParser>()?;
    m.add_class::<PatternMatcher>()?;
    m.add_class::<PluginAnalyzer>()?;
    m.add_class::<RecordScanner>()?;

    // Add report generation classes
    m.add_class::<StringPool>()?;
    m.add_class::<ReportFragment>()?;
    m.add_class::<ReportComposer>()?;
    m.add_class::<ReportGenerator>()?;
    m.add_class::<ParallelReportProcessor>()?;

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

    Ok(())
}
