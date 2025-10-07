//! CLASSIC Core - High-performance Rust extensions for CLASSIC Fallout 4
//!
//! This is a thin facade module that re-exports all functionality from the modular
//! CLASSIC Rust crates, maintaining backward compatibility with the original monolithic API.
//!
//! ## Architecture (Post-Modularization)
//! - **classic-shared**: Foundation (runtime, errors, utilities)
//! - **classic-yaml**: YAML operations
//! - **classic-database**: SQLite operations
//! - **classic-file-io**: File I/O operations
//! - **classic-scanlog**: Log parsing & analysis
//! - **classic-core** (this crate): Facade that re-exports everything
//!
//! ## ONE RUNTIME RULE
//! All async operations use the shared runtime from classic-shared.

use pyo3::prelude::*;

// Re-export the shared runtime for backward compatibility
pub use classic_shared::get_runtime;

// Re-export all types from modular crates
pub use classic_shared::{
    ClassicError, ClassicResult, IntoClassicError,
    PathHandler, StringProcessor, RustPerformanceMonitor,
};

pub use classic_yaml::RustYamlOperations;

pub use classic_database::RustDatabasePool;

pub use classic_file_io::{RustFileIOCore, EncodingDetector, DDSHeader};

pub use classic_scanlog::{
    FormIDAnalyzer, FormIDAnalyzerCore, LogParser, PatternMatcher,
    PluginAnalyzer, RecordScanner, TestClass,
    ReportFragment, ReportComposer, ReportGenerator, StringPool, ParallelReportProcessor,
    extract_formids_batch, is_valid_formid, validate_formids_batch,
    scan_records_batch, contains_record,
    detect_plugins_batch, contains_plugin,
    detect_mods_single, detect_mods_double, detect_mods_important, detect_mods_batch,
};

// Legacy classes for backward compatibility
// These are kept here to maintain the exact same API

/// High-performance file reader using async I/O internally
#[pyclass]
struct FileReader;

#[pymethods]
impl FileReader {
    #[new]
    fn new() -> Self {
        Self
    }

    /// Read a file synchronously (but uses async I/O internally)
    fn read_file(&self, path: String) -> PyResult<String> {
        // Use global runtime for async operation
        get_runtime().block_on(async move {
            tokio::fs::read_to_string(path).await
        })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }

    /// Read multiple files in parallel (exposed as sync to Python)
    fn read_files_batch(&self, paths: Vec<String>) -> PyResult<Vec<Option<String>>> {
        // Use global runtime for parallel I/O
        let results = get_runtime().block_on(async move {
            let tasks: Vec<_> = paths
                .into_iter()
                .map(|path| {
                    tokio::spawn(async move {
                        tokio::fs::read_to_string(path).await.ok()
                    })
                })
                .collect();

            // Wait for all tasks to complete
            let mut results = Vec::new();
            for task in tasks {
                results.push(task.await.unwrap_or(None));
            }
            results
        });
        Ok(results)
    }
}

/// Fast FormID processor using parallel computation
#[pyclass]
struct FormIDProcessor;

#[pymethods]
impl FormIDProcessor {
    #[new]
    fn new() -> Self {
        Self
    }

    /// Process FormIDs in parallel (sync API, async implementation)
    fn process_batch(&self, formids: Vec<String>) -> Vec<Option<u32>> {
        use rayon::prelude::*;

        // Use rayon for CPU-bound parallel processing
        formids
            .par_iter()
            .map(|formid| {
                let cleaned = formid
                    .trim()
                    .trim_start_matches("0x")
                    .trim_start_matches("0X");
                u32::from_str_radix(cleaned, 16).ok()
            })
            .collect()
    }

    /// Async database lookup exposed as sync
    fn lookup_formids(&self, db_path: String, formids: Vec<String>) -> PyResult<Vec<Option<String>>> {
        // Use the global runtime for async operations
        get_runtime().block_on(async move {
            // Simulate async database operations
            let _contents = tokio::fs::read_to_string(&db_path).await?;

            // Parallel async lookups
            let tasks: Vec<_> = formids
                .into_iter()
                .map(|formid| {
                    let _db = db_path.clone();
                    tokio::spawn(async move {
                        // Simulate database lookup
                        tokio::time::sleep(tokio::time::Duration::from_micros(10)).await;
                        Some(format!("Plugin_{}", formid))
                    })
                })
                .collect();

            let mut results = Vec::new();
            for task in tasks {
                results.push(task.await.unwrap_or(None));
            }
            Ok::<Vec<Option<String>>, tokio::io::Error>(results)
        })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }
}

/// Pattern matcher with async file operations
#[pyfunction]
fn count_patterns_in_file(path: String, pattern: String) -> PyResult<usize> {
    // Use global runtime for one-off async operations
    get_runtime().block_on(async move {
        let content = tokio::fs::read_to_string(path).await?;
        Ok::<usize, tokio::io::Error>(content.matches(&pattern).count())
    })
    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
}

/// Python module initialization
#[pymodule]
fn classic_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Legacy classes (for backward compatibility)
    m.add_class::<FileReader>()?;
    m.add_class::<FormIDProcessor>()?;
    m.add_function(wrap_pyfunction!(count_patterns_in_file, m)?)?;

    // Register utils submodule (from classic-shared)
    let utils_module = PyModule::new(m.py(), "utils")?;
    utils_module.add_class::<StringProcessor>()?;
    utils_module.add_class::<PathHandler>()?;
    utils_module.add_class::<RustPerformanceMonitor>()?;
    m.add_submodule(&utils_module)?;

    // Register scanlog submodule (from classic-scanlog)
    let scanlog_module = PyModule::new(m.py(), "scanlog")?;
    scanlog_module.add_class::<FormIDAnalyzer>()?;
    scanlog_module.add_class::<FormIDAnalyzerCore>()?;
    scanlog_module.add_class::<LogParser>()?;
    scanlog_module.add_class::<PatternMatcher>()?;
    scanlog_module.add_class::<PluginAnalyzer>()?;
    scanlog_module.add_class::<RecordScanner>()?;
    scanlog_module.add_class::<StringPool>()?;
    scanlog_module.add_class::<ReportFragment>()?;
    scanlog_module.add_class::<ReportComposer>()?;
    scanlog_module.add_class::<ReportGenerator>()?;
    scanlog_module.add_class::<ParallelReportProcessor>()?;
    scanlog_module.add_function(wrap_pyfunction!(extract_formids_batch, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(is_valid_formid, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(validate_formids_batch, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(scan_records_batch, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(contains_record, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(detect_plugins_batch, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(contains_plugin, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(detect_mods_single, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(detect_mods_double, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(detect_mods_important, &scanlog_module)?)?;
    scanlog_module.add_function(wrap_pyfunction!(detect_mods_batch, &scanlog_module)?)?;
    m.add_submodule(&scanlog_module)?;

    // Register database submodule (from classic-database)
    let database_module = PyModule::new(m.py(), "database")?;
    database_module.add_class::<RustDatabasePool>()?;
    m.add_submodule(&database_module)?;

    // Register file_io submodule (from classic-file-io)
    let file_io_module = PyModule::new(m.py(), "file_io")?;
    file_io_module.add_class::<RustFileIOCore>()?;
    file_io_module.add_class::<EncodingDetector>()?;
    m.add_submodule(&file_io_module)?;

    // Register YAML submodule (from classic-yaml)
    let yaml_module = PyModule::new(m.py(), "yaml")?;
    yaml_module.add_class::<RustYamlOperations>()?;
    m.add_submodule(&yaml_module)?;

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
