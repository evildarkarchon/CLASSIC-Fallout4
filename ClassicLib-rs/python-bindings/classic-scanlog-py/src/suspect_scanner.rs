//! Python bindings for SuspectScanner - Thin wrapper over classic-scanlog-core

use classic_config_core::{SuspectErrorRule, SuspectStackCountRule, SuspectStackRule};
use classic_scanlog_core::SuspectScanner;
use classic_shared::without_gil;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};

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
    ///     suspect_error_rules: List of structured main-error rules
    ///     suspect_stack_rules: List of structured stack rules
    #[new]
    pub fn new(
        suspect_error_rules: &Bound<'_, PyAny>,
        suspect_stack_rules: &Bound<'_, PyAny>,
    ) -> PyResult<Self> {
        let error_rules = suspect_error_rules
            .extract::<Vec<Bound<'_, PyAny>>>()?
            .iter()
            .filter_map(|item| {
                let dict = item.cast::<PyDict>().ok()?;
                Some(SuspectErrorRule {
                    id: dict.get_item("id").ok()??.extract::<String>().ok()?,
                    name: dict.get_item("name").ok()??.extract::<String>().ok()?,
                    severity: dict.get_item("severity").ok()??.extract::<i32>().ok()?,
                    main_error_contains_any: dict
                        .get_item("main_error_contains_any")
                        .ok()??
                        .extract::<Vec<String>>()
                        .ok()?,
                })
            })
            .collect();
        let stack_rules = suspect_stack_rules
            .extract::<Vec<Bound<'_, PyAny>>>()?
            .iter()
            .filter_map(|item| {
                let dict = item.cast::<PyDict>().ok()?;
                let count_rules = dict
                    .get_item("stack_contains_at_least")
                    .ok()??
                    .extract::<Vec<Bound<'_, PyAny>>>()
                    .ok()?
                    .iter()
                    .filter_map(|count_item| {
                        let count_dict = count_item.cast::<PyDict>().ok()?;
                        Some(SuspectStackCountRule {
                            substring: count_dict
                                .get_item("substring")
                                .ok()??
                                .extract::<String>()
                                .ok()?,
                            count: count_dict
                                .get_item("count")
                                .ok()??
                                .extract::<usize>()
                                .ok()?,
                        })
                    })
                    .collect();

                Some(SuspectStackRule {
                    id: dict.get_item("id").ok()??.extract::<String>().ok()?,
                    name: dict.get_item("name").ok()??.extract::<String>().ok()?,
                    severity: dict.get_item("severity").ok()??.extract::<i32>().ok()?,
                    main_error_required_any: dict
                        .get_item("main_error_required_any")
                        .ok()??
                        .extract::<Vec<String>>()
                        .ok()?,
                    main_error_optional_any: dict
                        .get_item("main_error_optional_any")
                        .ok()??
                        .extract::<Vec<String>>()
                        .ok()?,
                    stack_contains_any: dict
                        .get_item("stack_contains_any")
                        .ok()??
                        .extract::<Vec<String>>()
                        .ok()?,
                    exclude_if_stack_contains_any: dict
                        .get_item("exclude_if_stack_contains_any")
                        .ok()??
                        .extract::<Vec<String>>()
                        .ok()?,
                    stack_contains_at_least: count_rules,
                })
            })
            .collect();
        Ok(Self {
            inner: SuspectScanner::new(error_rules, stack_rules),
        })
    }

    /// Scan main error for suspect patterns
    ///
    /// Releases GIL during pattern scanning to allow concurrent Python threads.
    pub fn suspect_scan_mainerror(
        &self,
        py: Python<'_>,
        crashlog_mainerror: String,
        max_warn_length: usize,
    ) -> PyResult<(Vec<String>, bool)> {
        // Release GIL during pattern scanning
        let (fragment, found) = without_gil(py, || {
            self.inner
                .suspect_scan_mainerror(&crashlog_mainerror, max_warn_length)
        })
        .map_err(crate::to_pyerr)?;
        Ok((fragment.to_list(), found))
    }

    /// Scan callstack for suspect patterns
    ///
    /// Releases GIL during pattern scanning to allow concurrent Python threads.
    pub fn suspect_scan_stack(
        &self,
        py: Python<'_>,
        crashlog_mainerror: String,
        segment_callstack_intact: String,
        max_warn_length: usize,
    ) -> PyResult<(Vec<String>, bool)> {
        // Release GIL during pattern scanning
        let (fragment, found) = without_gil(py, || {
            self.inner.suspect_scan_stack(
                &crashlog_mainerror,
                &segment_callstack_intact,
                max_warn_length,
            )
        })
        .map_err(crate::to_pyerr)?;
        Ok((fragment.to_list(), found))
    }

    /// Batch scan multiple crash logs
    ///
    /// Releases GIL during batch scanning to allow concurrent Python threads.
    pub fn scan_suspects_batch(
        &self,
        py: Python<'_>,
        crash_logs: Vec<(String, String)>,
        max_warn_length: usize,
    ) -> PyResult<Vec<(Vec<String>, bool)>> {
        // Release GIL during batch scanning
        let results = without_gil(py, || {
            self.inner.scan_suspects_batch(crash_logs, max_warn_length)
        })
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
