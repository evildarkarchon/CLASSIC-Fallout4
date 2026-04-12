//! Python bindings for SuspectScanner - Thin wrapper over classic-scanlog-core

use classic_config_core::{SuspectErrorRule, SuspectStackCountRule, SuspectStackRule};
use classic_scanlog_core::SuspectScanner;
use classic_shared::without_gil;
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};

macro_rules! required_field {
    ($dict:expr, $key:literal, $context:expr, $ty:ty) => {{
        $dict
            .get_item($key)?
            .ok_or_else(|| PyValueError::new_err(format!("missing {}.{}", $context, $key)))?
            .extract::<$ty>()
            .map_err(|err| {
                PyTypeError::new_err(format!("invalid {}.{}: {}", $context, $key, err))
            })?
    }};
}

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
            .enumerate()
            .map(|(index, item)| -> PyResult<_> {
                let context = format!("suspect_error_rules[{index}]");
                let dict = item
                    .cast::<PyDict>()
                    .map_err(|_| PyTypeError::new_err(format!("{context} must be a dict")))?;

                Ok(SuspectErrorRule {
                    id: required_field!(dict, "id", context.as_str(), String),
                    name: required_field!(dict, "name", context.as_str(), String),
                    severity: required_field!(dict, "severity", context.as_str(), i32),
                    main_error_contains_any: required_field!(
                        dict,
                        "main_error_contains_any",
                        context.as_str(),
                        Vec<String>
                    ),
                })
            })
            .collect::<PyResult<Vec<_>>>()?;
        let stack_rules = suspect_stack_rules
            .extract::<Vec<Bound<'_, PyAny>>>()?
            .iter()
            .enumerate()
            .map(|(index, item)| -> PyResult<_> {
                let context = format!("suspect_stack_rules[{index}]");
                let dict = item
                    .cast::<PyDict>()
                    .map_err(|_| PyTypeError::new_err(format!("{context} must be a dict")))?;
                let count_rules = required_field!(
                    dict,
                    "stack_contains_at_least",
                    context.as_str(),
                    Vec<Bound<'_, PyAny>>
                )
                .iter()
                .enumerate()
                .map(|(count_index, count_item)| -> PyResult<_> {
                    let count_context = format!(
                        "{}.stack_contains_at_least[{count_index}]",
                        context.as_str()
                    );
                    let count_dict = count_item.cast::<PyDict>().map_err(|_| {
                        PyTypeError::new_err(format!("{count_context} must be a dict"))
                    })?;

                    Ok(SuspectStackCountRule {
                        substring: required_field!(
                            count_dict,
                            "substring",
                            count_context.as_str(),
                            String
                        ),
                        count: required_field!(count_dict, "count", count_context.as_str(), usize),
                    })
                })
                .collect::<PyResult<Vec<_>>>()?;

                Ok(SuspectStackRule {
                    id: required_field!(dict, "id", context.as_str(), String),
                    name: required_field!(dict, "name", context.as_str(), String),
                    severity: required_field!(dict, "severity", context.as_str(), i32),
                    main_error_required_any: required_field!(
                        dict,
                        "main_error_required_any",
                        context.as_str(),
                        Vec<String>
                    ),
                    main_error_optional_any: required_field!(
                        dict,
                        "main_error_optional_any",
                        context.as_str(),
                        Vec<String>
                    ),
                    stack_contains_any: required_field!(
                        dict,
                        "stack_contains_any",
                        context.as_str(),
                        Vec<String>
                    ),
                    exclude_if_stack_contains_any: required_field!(
                        dict,
                        "exclude_if_stack_contains_any",
                        context.as_str(),
                        Vec<String>
                    ),
                    stack_contains_at_least: count_rules,
                })
            })
            .collect::<PyResult<Vec<_>>>()?;
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

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::types::{PyDict, PyList};

    #[test]
    fn new_rejects_malformed_error_rule_payloads() {
        Python::attach(|py| -> PyResult<()> {
            let error_rule = PyDict::new(py);
            error_rule.set_item("id", "rule-id")?;
            error_rule.set_item("name", "Missing matcher")?;
            error_rule.set_item("severity", 1)?;

            let error_rules = PyList::empty(py);
            error_rules.append(&error_rule)?;
            let stack_rules = PyList::empty(py);

            let err = match PySuspectScanner::new(error_rules.as_any(), stack_rules.as_any()) {
                Ok(_) => panic!("missing main_error_contains_any should fail"),
                Err(err) => err,
            };

            assert!(err.to_string().contains("main_error_contains_any"));
            Ok(())
        })
        .expect("malformed error rules should produce a Python error");
    }

    #[test]
    fn new_rejects_malformed_stack_rule_payloads() {
        Python::attach(|py| -> PyResult<()> {
            let count_rule = PyDict::new(py);
            count_rule.set_item("substring", "foo")?;

            let count_rules = PyList::empty(py);
            count_rules.append(&count_rule)?;

            let stack_rule = PyDict::new(py);
            stack_rule.set_item("id", "stack-rule")?;
            stack_rule.set_item("name", "Missing count")?;
            stack_rule.set_item("severity", 2)?;
            stack_rule.set_item("main_error_required_any", vec!["foo"])?;
            stack_rule.set_item("main_error_optional_any", Vec::<String>::new())?;
            stack_rule.set_item("stack_contains_any", vec!["foo"])?;
            stack_rule.set_item("exclude_if_stack_contains_any", Vec::<String>::new())?;
            stack_rule.set_item("stack_contains_at_least", count_rules)?;

            let error_rules = PyList::empty(py);
            let stack_rules = PyList::empty(py);
            stack_rules.append(&stack_rule)?;

            let err = match PySuspectScanner::new(error_rules.as_any(), stack_rules.as_any()) {
                Ok(_) => panic!("missing nested count field should fail"),
                Err(err) => err,
            };

            assert!(err.to_string().contains("count"));
            Ok(())
        })
        .expect("malformed stack rules should produce a Python error");
    }
}
