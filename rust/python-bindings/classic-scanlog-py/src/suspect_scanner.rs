//! Python bindings for SuspectScanner - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::SuspectScanner;
use pyo3::prelude::*;
use std::collections::HashMap;

/// Python wrapper for SuspectScanner
#[pyclass(name = "SuspectScanner")]
pub struct PySuspectScanner {
    inner: SuspectScanner,
}

#[pymethods]
impl PySuspectScanner {
    /// Create a new instance

    #[new]
    pub fn new(
        suspects_error_list: HashMap<String, String>,
        suspects_stack_list: HashMap<String, Vec<String>>,
    ) -> Self {
        Self {
            inner: SuspectScanner::new(suspects_error_list, suspects_stack_list),
        }
    }

    /// Scan main error for suspect patterns
    pub fn suspect_scan_mainerror(
        &self,
        crashlog_mainerror: String,
        max_warn_length: usize,
    ) -> PyResult<(Vec<String>, bool)> {
        let (fragment, found) = self
            .inner
            .suspect_scan_mainerror(&crashlog_mainerror, max_warn_length)
            .map_err(crate::to_pyerr)?;
        Ok((fragment.to_list(), found))
    }

    /// Scan callstack for suspect patterns
    pub fn suspect_scan_stack(
        &self,
        crashlog_mainerror: String,
        segment_callstack_intact: String,
        max_warn_length: usize,
    ) -> PyResult<(Vec<String>, bool)> {
        let (fragment, found) = self
            .inner
            .suspect_scan_stack(
                &crashlog_mainerror,
                &segment_callstack_intact,
                max_warn_length,
            )
            .map_err(crate::to_pyerr)?;
        Ok((fragment.to_list(), found))
    }

    /// Batch scan multiple crash logs
    pub fn scan_suspects_batch(
        &self,
        crash_logs: Vec<(String, String)>,
        max_warn_length: usize,
    ) -> PyResult<Vec<(Vec<String>, bool)>> {
        let results = self
            .inner
            .scan_suspects_batch(crash_logs, max_warn_length)
            .map_err(crate::to_pyerr)?;
        Ok(results
            .into_iter()
            .map(|(fragment, found)| (fragment.to_list(), found))
            .collect())
    }

    /// Check if main error is a DLL crash
    #[staticmethod]
    pub fn check_dll_crash(crashlog_mainerror: String) -> PyResult<Vec<String>> {
        let fragment = classic_scanlog_core::SuspectScanner::check_dll_crash(&crashlog_mainerror)
            .map_err(crate::to_pyerr)?;
        Ok(fragment.to_list())
    }
}
