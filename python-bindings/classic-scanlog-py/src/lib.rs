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
//!
//! ## Complete Usage Example
//!
//! ```python
//! from classic_core import scanlog
//! import asyncio
//!
//! async def main():
//!     # Parse crash log with SIMD-optimized segmentation
//!     parser = scanlog.PyLogParser()
//!
//!     with open("crash-2024-01-01.log", "r") as f:
//!         lines = f.readlines()
//!
//!     # Parse named sections (20-40x faster than Python)
//!     segments = parser.parse_all_sections(lines)
//!     print(f"Found {len(segments)} segments")
//!
//!     # Extract FormIDs (25x faster than Python regex)
//!     callstack = segments.get("callstack", [])
//!     formids = parser.extract_formids(callstack)
//!     print(f"Found {len(formids)} FormIDs")
//!
//!     # Detect plugins in parallel
//!     plugins_segment = segments.get("plugins", [])
//!     plugins = parser.extract_plugins(plugins_segment)
//!     print(f"Found {len(plugins)} plugins")
//!
//!     # Detect mods with pattern matching (15-25x faster)
//!     yaml_dict = {"problemmod": "Known Issue\nDetails..."}
//!     mods_found = scanlog.detect_mods_single(yaml_dict, plugins)
//!     for line in mods_found:
//!         print(line, end="")
//!
//!     # GPU detection
//!     gpu_detector = scanlog.PyGpuDetector()
//!     gpu_info = gpu_detector.detect_gpu(lines)
//!     if gpu_info:
//!         print(f"GPU: {gpu_info.name()} ({gpu_info.vendor()})")
//!
//!     # Complete scan execution uses ScanRunRequest plus scan_run_execute;
//!     # lower-level utilities remain available only for independent analysis.
//!
//! asyncio.run(main())
//! ```
//!
//! ## Performance Characteristics
//!
//! - **Log parsing**: 20-40x faster than Python with SIMD optimizations
//! - **FormID extraction**: 25x faster than Python regex
//! - **Pattern matching**: 5-10x faster with Rayon parallelism
//! - **Mod detection**: 15-25x faster with compiled regex
//! - **DDS processing**: 40x faster with parallel batch operations
//! - **Papyrus log analysis**: 15-30x faster than Python
//! - **Complete analysis**: 50-200ms per log (Python: 2-3 seconds)
//!
//! ## Thread Safety
//!
//! All scanlog components are thread-safe and can be used from multiple Python threads
//! or async tasks. Complete runs execute through the shared Rust runtime.

use classic_shared::{define_exceptions, register_exceptions};
use pyo3::prelude::*;

// Define the standard 3-tier exception hierarchy using the shared macro
// Note: scanlog uses different naming convention (RustParseError, RustConfigError)
// The macro parameter names (io, parse) don't dictate the exception names
define_exceptions!(
    module: classic_scanlog,
    base: RustScanLogError,
    io: RustParseError,       // Actually used for parse/analysis errors
    parse: RustConfigError    // Actually used for configuration errors
);

// Import all wrapper modules
/// Conversion helpers for `CoreModExclude` ↔ Python dict round-tripping.
pub mod core_mod_convert;
pub mod crash_suspect_analyzer;
/// Crashgen settings rule parsing helpers for Python inputs.
pub mod crashgen_rules;
pub mod crashgen_settings_analyzer;
pub mod fcx_handler;
pub mod formid;
pub mod formid_analyzer;
pub mod gpu_detector;
pub mod mod_detector;
pub mod papyrus;
pub mod parser;
pub mod patterns;
pub mod plugin_analyzer;
mod py_adapters;
pub mod record_scanner;
pub mod report;
pub mod scan_run;
pub mod settings_validator;
pub mod version;

// Re-export all public types
pub use crash_suspect_analyzer::{
    PyCrashSuspectAnalysisInput, PyCrashSuspectAnalysisResult, PyCrashSuspectAnalyzer,
    PyCrashSuspectFinding, PyCrashSuspectFindingKind, PyCrashSuspectMainErrorRule,
    PyCrashSuspectStackCountRule, PyCrashSuspectStackRule,
};
pub use crashgen_settings_analyzer::{
    PyAnalyzerKind, PyAnalyzerSeverity, PyAutoscanReportPlacement, PyCrashgenExpectationKind,
    PyCrashgenExpectationOutcome, PyCrashgenSettingsAnalysisResult, PyCrashgenSettingsAnalyzer,
    PyDisabledSettingNotice,
};
pub use fcx_handler::PyConfigIssue;
pub use formid::PyRustFormIDAnalyzer;
pub use formid_analyzer::{
    PyFormIDAnalyzerCore, extract_formids_batch, is_valid_formid, validate_formids_batch,
};
pub use gpu_detector::{PyGpuDetector, PyGpuInfo, PyGpuVendor};
pub use mod_detector::{
    detect_mods_batch, detect_mods_double, detect_mods_important, detect_mods_single,
};
pub use papyrus::{PyPapyrusAnalyzer, PyPapyrusStats, papyrus_logging};
pub use parser::PyLogParser;
pub use patterns::PyPatternMatcher;
pub use plugin_analyzer::{PyPluginAnalyzer, contains_plugin, detect_plugins_batch};
pub use record_scanner::{PyRecordScanner, contains_record, scan_records_batch};
pub use report::{
    PyParallelReportProcessor, PyReportComposer, PyReportFragment, PyReportGenerator, PyStringPool,
};
pub use scan_run::{
    PyScanRunCancellation, PyScanRunConfiguration, PyScanRunDiscoveryResult, PyScanRunEvent,
    PyScanRunExecution, PyScanRunInfrastructureError, PyScanRunLogEvent, PyScanRunLogFailure,
    PyScanRunLogResult, PyScanRunRejectedInput, PyScanRunRequest, PyScanRunResult,
    PyScanRunSetupCheck, PyScanRunSetupContext, PyScanRunSetupPathUpdate, PyScanRunSetupResult,
    PyScanRunStandardSource, PyScanRunTargetedSource, PyScanRunUnsolvedLogs, scan_run_execute,
};
pub use settings_validator::PySettingsValidator;
pub use version::{
    PyCrashgenVersion, PyCrashgenVersionStatus, check_crashgen_version_status,
    parse_crashgen_version,
};

/// Convert errors to PyErr using custom exception types
///
/// Maps errors to Python exception types from ClassicLib.integration.exceptions
/// for better error handling. Uses error message patterns to determine type.
pub fn to_pyerr(err: impl std::fmt::Display) -> PyErr {
    let err_str = err.to_string().to_lowercase();

    // Check error message patterns to determine exception type
    if err_str.contains("config") || err_str.contains("setting") || err_str.contains("invalid") {
        RustConfigError::new_err(err.to_string())
    } else if err_str.contains("parse")
        || err_str.contains("segment")
        || err_str.contains("formid")
        || err_str.contains("analysis")
        || err_str.contains("detect")
    {
        RustParseError::new_err(err.to_string())
    } else {
        // Generic ScanLog error
        RustScanLogError::new_err(err.to_string())
    }
}

fn auto_init_application_dir(py: Python<'_>) {
    if classic_registry_core::get_application_dir().is_none()
        && let Some(app_dir) = classic_shared::resolve_python_entry_dir(py)
    {
        classic_registry_core::set_application_dir(app_dir);
    }
}

/// Register the final Crash Log Scan Run adapter types and execution function.
fn register_scan_run_exports(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyScanRunConfiguration>()?;
    m.add_class::<PyScanRunCancellation>()?;
    m.add_class::<PyScanRunStandardSource>()?;
    m.add_class::<PyScanRunTargetedSource>()?;
    m.add_class::<PyScanRunUnsolvedLogs>()?;
    m.add_class::<PyScanRunRequest>()?;
    m.add_class::<PyScanRunRejectedInput>()?;
    m.add_class::<PyScanRunDiscoveryResult>()?;
    m.add_class::<PyScanRunSetupContext>()?;
    m.add_class::<PyScanRunSetupCheck>()?;
    m.add_class::<PyScanRunSetupPathUpdate>()?;
    m.add_class::<PyScanRunSetupResult>()?;
    m.add_class::<PyScanRunLogFailure>()?;
    m.add_class::<PyScanRunLogResult>()?;
    m.add_class::<PyScanRunResult>()?;
    m.add_class::<PyScanRunInfrastructureError>()?;
    m.add_class::<PyScanRunLogEvent>()?;
    m.add_class::<PyScanRunEvent>()?;
    m.add_class::<PyScanRunExecution>()?;
    m.add_function(wrap_pyfunction!(scan_run_execute, m)?)?;
    Ok(())
}

/// Python module initialization
#[pymodule]
fn classic_scanlog(m: &Bound<'_, PyModule>) -> PyResult<()> {
    classic_shared::configure_python_stdio(m.py());
    auto_init_application_dir(m.py());

    // Parser
    m.add_class::<PyLogParser>()?;
    m.add_class::<parser::ScanOutput>()?;

    // FormID analysis
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

    // Detectors
    m.add_class::<PyGpuDetector>()?;
    m.add_class::<PyGpuInfo>()?;
    m.add_class::<PyGpuVendor>()?;
    version::register(m)?;

    // Mod detection
    m.add_function(wrap_pyfunction!(detect_mods_single, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_double, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_important, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_batch, m)?)?;

    // Validators and run-result data
    crashgen_settings_analyzer::register(m)?;
    crash_suspect_analyzer::register(m)?;
    m.add_class::<PySettingsValidator>()?;
    m.add_class::<PyConfigIssue>()?;
    register_scan_run_exports(m)?;

    // Report generation
    m.add_class::<PyStringPool>()?;
    m.add_class::<PyReportFragment>()?;
    m.add_class::<PyReportComposer>()?;
    m.add_class::<PyReportGenerator>()?;
    m.add_class::<PyParallelReportProcessor>()?;

    // Papyrus log analysis
    papyrus::register(m)?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Register custom exception types using the shared macro
    register_exceptions!(m, RustScanLogError, RustParseError, RustConfigError);

    Ok(())
}

/// Public registration function for use by facade modules
/// This allows classic-core to include all scanlog components in its submodule
pub fn register_scanlog_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    auto_init_application_dir(m.py());

    // Parser
    m.add_class::<PyLogParser>()?;
    m.add_class::<parser::ScanOutput>()?;

    // FormID analysis
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

    // Detectors
    m.add_class::<PyGpuDetector>()?;
    m.add_class::<PyGpuInfo>()?;
    m.add_class::<PyGpuVendor>()?;
    version::register(m)?;

    // Mod detection
    m.add_function(wrap_pyfunction!(detect_mods_single, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_double, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_important, m)?)?;
    m.add_function(wrap_pyfunction!(detect_mods_batch, m)?)?;

    // Validators and run-result data
    crashgen_settings_analyzer::register(m)?;
    crash_suspect_analyzer::register(m)?;
    m.add_class::<PySettingsValidator>()?;
    m.add_class::<PyConfigIssue>()?;
    register_scan_run_exports(m)?;

    // Report generation
    m.add_class::<PyStringPool>()?;
    m.add_class::<PyReportFragment>()?;
    m.add_class::<PyReportComposer>()?;
    m.add_class::<PyReportGenerator>()?;
    m.add_class::<PyParallelReportProcessor>()?;

    // Papyrus log analysis
    papyrus::register(m)?;

    Ok(())
}

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
