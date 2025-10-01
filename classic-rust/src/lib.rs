//! CLASSIC Core - High-performance Rust extensions for CLASSIC Fallout 4
//!
//! This module provides optimized utilities and processing capabilities for the CLASSIC
//! crash log analyzer, implementing Phase 1.2 and Phase 2 of the Rust migration plan.

use pyo3::prelude::*;
use tokio::runtime::Runtime;
use once_cell::sync::Lazy;

// Module declarations
pub mod database;
pub mod file_io;
pub mod scanlog;
pub mod utils;
pub mod yaml;

// Re-export key types for convenience
pub use utils::{
    ClassicError, ClassicResult,
    PathHandler, StringProcessor, LogProcessor, RustPerformanceMonitor
};

/// Shared tokio runtime for all async operations (ONE RUNTIME RULE)
///
/// This is the ONLY runtime that should exist in the entire application.
/// All submodules MUST use this runtime via crate::get_runtime() to avoid deadlocks.
pub(crate) static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    let worker_threads = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);

    tokio::runtime::Builder::new_multi_thread()
        .worker_threads(worker_threads)
        .enable_all()
        .build()
        .expect("Failed to create Tokio runtime")
});

/// Get a reference to the global runtime
///
/// Use this function in submodules instead of creating new runtimes.
pub(crate) fn get_runtime() -> &'static Runtime {
    &RUNTIME
}

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
        RUNTIME.block_on(async move {
            tokio::fs::read_to_string(path).await
        })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }

    /// Read multiple files in parallel (exposed as sync to Python)
    fn read_files_batch(&self, paths: Vec<String>) -> PyResult<Vec<Option<String>>> {
        // Use global runtime for parallel I/O
        let results = RUNTIME.block_on(async move {
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
        RUNTIME.block_on(async move {
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
    RUNTIME.block_on(async move {
        let content = tokio::fs::read_to_string(path).await?;
        Ok::<usize, tokio::io::Error>(content.matches(&pattern).count())
    })
    .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
}

/// Python module initialization
#[pymodule]
fn classic_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add classes
    m.add_class::<FileReader>()?;
    m.add_class::<FormIDProcessor>()?;

    // Add functions
    m.add_function(wrap_pyfunction!(count_patterns_in_file, m)?)?;

    // Register submodules
    let utils_module = PyModule::new(m.py(), "utils")?;
    utils::register_module(&utils_module)?;
    m.add_submodule(&utils_module)?;

    let scanlog_module = PyModule::new(m.py(), "scanlog")?;
    scanlog::register_module(&scanlog_module)?;
    m.add_submodule(&scanlog_module)?;

    let database_module = PyModule::new(m.py(), "database")?;
    database::register_module(&database_module)?;
    m.add_submodule(&database_module)?;

    let file_io_module = PyModule::new(m.py(), "file_io")?;
    file_io::register_module(&file_io_module)?;
    m.add_submodule(&file_io_module)?;

    // Temporarily disabled to debug import freeze
    // let yaml_module = PyModule::new_bound(m.py(), "yaml")?;
    // yaml::init_module(&yaml_module)?;
    // m.add_submodule(&yaml_module)?;

    // Add version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
