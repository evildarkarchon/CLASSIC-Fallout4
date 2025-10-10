//! CLASSIC Scanlog Python Bindings
//!
//! This crate provides PyO3 bindings for classic-scanlog-core.
//! It wraps the pure Rust business logic for Python consumption.
//!
//! ## Architecture
//! This is a THIN ADAPTER layer that:
//! - Delegates all business logic to classic-scanlog-core
//! - Only handles Python ↔ Rust type conversions
//! - Maintains API compatibility with existing Python code

use pyo3::prelude::*;

// Import all wrapper modules
pub mod fcx_handler;
pub mod formid;
pub mod formid_analyzer;
pub mod gpu_detector;
pub mod mod_detector;
pub mod orchestrator;
pub mod parser;
pub mod patterns;
pub mod plugin_analyzer;
pub mod record_scanner;
pub mod report;
pub mod settings_validator;
pub mod suspect_scanner;

// Re-export all public types
pub use fcx_handler::PyFcxModeHandler;
pub use formid::{PyFormIDAnalyzer, PyRustFormIDAnalyzer};
pub use formid_analyzer::{
    extract_formids_batch, is_valid_formid, validate_formids_batch, PyFormIDAnalyzerCore,
};
pub use gpu_detector::{PyGpuDetector, PyGpuInfo, PyGpuVendor};
pub use mod_detector::{
    detect_mods_batch, detect_mods_double, detect_mods_important, detect_mods_single,
};
pub use orchestrator::{PyAnalysisConfig, PyAnalysisResult, PyRustOrchestrator};
pub use parser::PyLogParser;
pub use patterns::PyPatternMatcher;
pub use plugin_analyzer::{contains_plugin, detect_plugins_batch, PyPluginAnalyzer};
pub use record_scanner::{contains_record, scan_records_batch, PyRecordScanner};
pub use report::{
    PyParallelReportProcessor, PyReportComposer, PyReportFragment, PyReportGenerator, PyStringPool,
};
pub use settings_validator::PySettingsValidator;
pub use suspect_scanner::PySuspectScanner;

/// Convert ScanLogError to PyErr
pub fn to_pyerr(err: impl std::fmt::Display) -> PyErr {
    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(err.to_string())
}

/// Python module initialization
#[pymodule]
fn classic_scanlog(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Parser
    m.add_class::<PyLogParser>()?;

    // FormID analysis
    m.add_class::<PyFormIDAnalyzer>()?;
    m.add_class::<PyRustFormIDAnalyzer>()?;
    m.add_class::<PyFormIDAnalyzerCore>()?;
    m.add_function(wrap_pyfunction!(extract_formids_batch, m)?)?;
    m.add_function(wrap_pyfunction!(is_valid_formid, m)?)?;
    m.add_function(wrap_pyfunction!(validate_formids_batch, m)?)?;

    // Scanners and analyzers
    m.add_class::<PyRecordScanner>()?;
    m.add_function(wrap_pyfunction!(scan_records_batch, m)?)?;
    m.add_function(wrap_pyfunction!(contains_record, m)?)?;

    m.add_class::<PyPluginAnalyzer>()?;
    m.add_function(wrap_pyfunction!(detect_plugins_batch, m)?)?;
    m.add_function(wrap_pyfunction!(contains_plugin, m)?)?;

    m.add_class::<PyPatternMatcher>()?;
    m.add_class::<PySuspectScanner>()?;

    // Detectors
    m.add_class::<PyGpuDetector>()?;
    m.add_class::<PyGpuInfo>()?;
    m.add_class::<PyGpuVendor>()?;

    // Mod detection
    m.add_function(wrap_pyfunction!(detect_mods_single, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_double, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_important, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_batch, m)?)?;

    // Validators and handlers
    m.add_class::<PySettingsValidator>()?;
    m.add_class::<PyFcxModeHandler>()?;

    // Orchestrator
    m.add_class::<PyRustOrchestrator>()?;
    m.add_class::<PyAnalysisConfig>()?;
    m.add_class::<PyAnalysisResult>()?;

    // Report generation
    m.add_class::<PyStringPool>()?;
    m.add_class::<PyReportFragment>()?;
    m.add_class::<PyReportComposer>()?;
    m.add_class::<PyReportGenerator>()?;
    m.add_class::<PyParallelReportProcessor>()?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}

/// Public registration function for use by facade modules
/// This allows classic-core to include all scanlog components in its submodule
pub fn register_scanlog_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Parser
    m.add_class::<PyLogParser>()?;

    // FormID analysis
    m.add_class::<PyFormIDAnalyzer>()?;
    m.add_class::<PyRustFormIDAnalyzer>()?;
    m.add_class::<PyFormIDAnalyzerCore>()?;
    m.add_function(wrap_pyfunction!(extract_formids_batch, m)?)?;
    m.add_function(wrap_pyfunction!(is_valid_formid, m)?)?;
    m.add_function(wrap_pyfunction!(validate_formids_batch, m)?)?;

    // Scanners and analyzers
    m.add_class::<PyRecordScanner>()?;
    m.add_function(wrap_pyfunction!(scan_records_batch, m)?)?;
    m.add_function(wrap_pyfunction!(contains_record, m)?)?;

    m.add_class::<PyPluginAnalyzer>()?;
    m.add_function(wrap_pyfunction!(detect_plugins_batch, m)?)?;
    m.add_function(wrap_pyfunction!(contains_plugin, m)?)?;

    m.add_class::<PyPatternMatcher>()?;
    m.add_class::<PySuspectScanner>()?;

    // Detectors
    m.add_class::<PyGpuDetector>()?;
    m.add_class::<PyGpuInfo>()?;
    m.add_class::<PyGpuVendor>()?;

    // Mod detection
    m.add_function(wrap_pyfunction!(detect_mods_single, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_double, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_important, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_batch, m)?)?;

    // Validators and handlers
    m.add_class::<PySettingsValidator>()?;
    m.add_class::<PyFcxModeHandler>()?;

    // Orchestrator
    m.add_class::<PyRustOrchestrator>()?;
    m.add_class::<PyAnalysisConfig>()?;
    m.add_class::<PyAnalysisResult>()?;

    // Report generation
    m.add_class::<PyStringPool>()?;
    m.add_class::<PyReportFragment>()?;
    m.add_class::<PyReportComposer>()?;
    m.add_class::<PyReportGenerator>()?;
    m.add_class::<PyParallelReportProcessor>()?;

    Ok(())
}
