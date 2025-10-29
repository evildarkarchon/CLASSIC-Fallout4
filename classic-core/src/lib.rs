//! CLASSIC Core - High-performance Rust extensions for CLASSIC Fallout 4
//!
//! This is a thin facade module that re-exports all functionality from the modular
//! CLASSIC Rust crates, maintaining backward compatibility with the original monolithic API.
//!
//! ## Architecture (Post-Business Logic Separation)
//!
//! ### Foundation Layer
//! - **classic-shared-core**: Runtime, errors, pure Rust utilities
//! - **classic-shared-py**: PyO3 bindings for utilities
//!
//! ### Business Logic Layer (Pure Rust, no PyO3)
//! - **classic-yaml-core**: YAML operations (yaml-rust2)
//! - **classic-database-core**: SQLite operations with connection pooling
//! - **classic-file-io-core**: File I/O, encoding detection, DDS parsing
//! - **classic-scanlog-core**: Log parsing, FormID analysis, pattern matching
//!
//! ### Python Bindings Layer (PyO3 adapters)
//! - **classic-yaml-py**: Python bindings for yaml-core
//! - **classic-database-py**: Python bindings for database-core
//! - **classic-file-io-py**: Python bindings for file-io-core
//! - **classic-scanlog-py**: Python bindings for scanlog-core
//! - **classic-config-py**: Python bindings for classic-config-core
//!
//! ### Facade Layer
//! - **classic-core** (this crate): Re-exports all Python bindings for backward compatibility
//!
//! ## ONE RUNTIME RULE
//! All async operations use the shared runtime from classic-shared.
//!
//! ## Usage
//!
//! ### From Python (via PyO3 bindings):
//! ```python
//! import classic_core
//! parser = classic_core.scanlog.LogParser()
//! ```
//!
//! ### From Rust (direct business logic access):
//! ```rust
//! use classic_core::core::scanlog::LogParser;
//! let parser = LogParser::new(Default::default());
//! ```

use pyo3::prelude::*;

// Re-export the shared runtime for backward compatibility
pub use classic_shared_core::get_runtime;

// Re-export all types from shared foundation
pub use classic_shared_core::{ClassicError, ClassicResult, IntoClassicError};
pub use classic_shared::{
    PyPathHandler as PathHandler, PyRustPerformanceMonitor as RustPerformanceMonitor,
    PyStringProcessor as StringProcessor,
};

// Re-export Python bindings (for Python usage via PyO3)
// Note: These use the library names from [lib] name in each crate's Cargo.toml
pub use classic_yaml::PyYamlOperations as RustYamlOperations;

pub use classic_database::PyDatabasePool as RustDatabasePool;

pub use classic_file_io::{
    PyEncodingDetector as EncodingDetector, PyFileIOCore as RustFileIOCore,
    PyLogCollector as LogCollector, PyLogCollector, // Import both aliased and original
};

pub use classic_scanlog::{
    contains_plugin, contains_record, detect_mods_batch, detect_mods_double, detect_mods_important,
    detect_mods_single, detect_plugins_batch, extract_formids_batch, is_valid_formid,
    scan_records_batch, validate_formids_batch, PyAnalysisConfig as AnalysisConfig,
    PyAnalysisResult as AnalysisResult, PyFcxModeHandler as FcxModeHandler,
    PyFormIDAnalyzer as FormIDAnalyzer, PyFormIDAnalyzerCore as FormIDAnalyzerCore,
    PyGpuDetector as GpuDetector, PyGpuInfo as GpuInfo, PyGpuVendor as GpuVendor,
    PyLogParser as LogParser, PyParallelReportProcessor as ParallelReportProcessor,
    PyPatternMatcher as PatternMatcher, PyPluginAnalyzer as PluginAnalyzer,
    PyRecordScanner as RecordScanner, PyReportComposer as ReportComposer,
    PyReportFragment as ReportFragment, PyReportGenerator as ReportGenerator,
    PyRustFormIDAnalyzer as RustFormIDAnalyzer, PyRustOrchestrator as RustOrchestrator,
    PySettingsValidator as SettingsValidator, PyStringPool as StringPool,
    PySuspectScanner as SuspectScanner,
};

// Re-export config bindings
pub use classic_config::create_yamldata;
pub use classic_config::PyYamlData as YamlData;

// Re-export pure business logic (for internal Rust usage)
/// Pure Rust business logic modules - use these for CLI/TUI or internal Rust code
pub mod core {
    /// Configuration data structures
    pub use classic_config_core as config;
    /// Database operations (SQLite with connection pooling)
    pub use classic_database_core as database;
    /// File I/O (encoding detection, DDS parsing)
    pub use classic_file_io_core as file_io;
    /// Log parsing and analysis
    pub use classic_scanlog_core as scanlog;
    /// YAML operations (yaml-rust2)
    pub use classic_yaml_core as yaml;
}

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
        get_runtime()
            .block_on(async move { tokio::fs::read_to_string(path).await })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }

    /// Read multiple files in parallel (exposed as sync to Python)
    fn read_files_batch(&self, paths: Vec<String>) -> PyResult<Vec<Option<String>>> {
        // Use global runtime for parallel I/O
        let results = get_runtime().block_on(async move {
            let tasks: Vec<_> = paths
                .into_iter()
                .map(|path| tokio::spawn(async move { tokio::fs::read_to_string(path).await.ok() }))
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
///
/// FormID Rules for Fallout 4:
/// - Valid FormIDs are exactly 8 hex digits (0x00000000 - 0xFFFFFFFF)
/// - FormIDs with FF prefix (0xFF000000 - 0xFFFFFFFF) are save file items
/// - Anything longer than 8 hex digits is invalid
#[pyclass]
struct FormIDProcessor;

#[pymethods]
impl FormIDProcessor {
    #[new]
    fn new() -> Self {
        Self
    }

    /// Process FormIDs in parallel with validation
    ///
    /// Rules:
    /// - Max 8 hex digits (after removing 0x prefix)
    /// - Returns None for invalid FormIDs (too long, non-hex chars, empty)
    /// - Returns Some(u32) for valid FormIDs (including FF-prefixed save file items)
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

                // Validate: max 8 hex digits
                if cleaned.is_empty() || cleaned.len() > 8 {
                    return None;
                }

                // Parse as hex and validate range
                u32::from_str_radix(cleaned, 16).ok()
            })
            .collect()
    }

    /// Check if a FormID is a save file FormID (FF prefix)
    ///
    /// Save file FormIDs have the FF prefix (0xFF000000 - 0xFFFFFFFF)
    /// and represent items dynamically created in the save file.
    fn is_save_file_formid(&self, formid: u32) -> bool {
        // Check if the highest byte is 0xFF
        (formid & 0xFF000000) == 0xFF000000
    }

    /// Process FormIDs with metadata about save file status
    ///
    /// Returns Vec of tuples: (Option<u32>, bool) where:
    /// - First element: parsed FormID (None if invalid)
    /// - Second element: true if save file FormID (FF prefix), false otherwise
    fn process_batch_with_metadata(&self, formids: Vec<String>) -> Vec<(Option<u32>, bool)> {
        use rayon::prelude::*;

        formids
            .par_iter()
            .map(|formid| {
                let cleaned = formid
                    .trim()
                    .trim_start_matches("0x")
                    .trim_start_matches("0X");

                // Validate: max 8 hex digits
                if cleaned.is_empty() || cleaned.len() > 8 {
                    return (None, false);
                }

                // Parse as hex
                match u32::from_str_radix(cleaned, 16) {
                    Ok(value) => {
                        let is_save_file = (value & 0xFF000000) == 0xFF000000;
                        (Some(value), is_save_file)
                    }
                    Err(_) => (None, false)
                }
            })
            .collect()
    }

    /// Async database lookup exposed as sync
    fn lookup_formids(
        &self,
        db_path: String,
        formids: Vec<String>,
    ) -> PyResult<Vec<Option<String>>> {
        // Use the global runtime for async operations
        get_runtime()
            .block_on(async move {
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
    get_runtime()
        .block_on(async move {
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

    // Register scanlog submodule (from classic-scanlog-py)
    // Use the registration function to include all components
    let scanlog_module = PyModule::new(m.py(), "scanlog")?;
    classic_scanlog::register_scanlog_module(&scanlog_module)?;
    m.add_submodule(&scanlog_module)?;

    // Register database submodule (from classic-database)
    let database_module = PyModule::new(m.py(), "database")?;
    database_module.add_class::<RustDatabasePool>()?;
    m.add_submodule(&database_module)?;

    // Register file_io submodule (from classic-file-io-py)
    // Use the registration function to include all components (matching scanlog pattern)
    let file_io_module = PyModule::new(m.py(), "file_io")?;
    classic_file_io::register_file_io_module(&file_io_module)?;
    m.add_submodule(&file_io_module)?;

    // Register YAML submodule (from classic-yaml)
    let yaml_module = PyModule::new(m.py(), "yaml")?;
    yaml_module.add_class::<RustYamlOperations>()?;
    m.add_submodule(&yaml_module)?;

    // Register config submodule (from classic-config-py)
    // Use the registration function to include all components
    let config_module = PyModule::new(m.py(), "config")?;
    classic_config::register_config_module(&config_module)?;
    m.add_submodule(&config_module)?;

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
