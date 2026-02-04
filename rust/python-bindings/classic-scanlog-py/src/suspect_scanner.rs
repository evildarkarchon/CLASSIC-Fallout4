//! Python bindings for SuspectScanner - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::SuspectScanner;
use classic_shared::{pydict_to_indexmap_str, pydict_to_indexmap_vecstr};
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Python wrapper for SuspectScanner
#[pyclass(name = "SuspectScanner")]
pub struct PySuspectScanner {
    inner: SuspectScanner,
}

#[pymethods]
impl PySuspectScanner {
    /// Create a new instance
    ///
    /// Args:
    ///     suspects_error_list: Dict of error patterns (order preserved)
    ///     suspects_stack_list: Dict of stack patterns (order preserved)
    #[new]
    pub fn new(
        suspects_error_list: &Bound<'_, PyDict>,
        suspects_stack_list: &Bound<'_, PyDict>,
    ) -> PyResult<Self> {
        let error_map = pydict_to_indexmap_str(suspects_error_list)?;
        let stack_map = pydict_to_indexmap_vecstr(suspects_stack_list)?;
        Ok(Self {
            inner: SuspectScanner::new(error_map, stack_map),
        })
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
