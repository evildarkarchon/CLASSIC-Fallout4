//! PyO3 bindings for ScanReportBuilder and ScanValidators (G-09/G-10)
//!
//! Wraps the game report building functionality for Python consumption.
//!
//! Note: `ScanValidators` uses `RefCell` internally (not `Sync`), so we
//! create instances on-the-fly rather than storing them in `#[pyclass]`.

use classic_scangame_core::game_report::{ScanReportBuilder, ScanValidators};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::{BTreeMap, BTreeSet};

/// Get issue messages for a given XSE acronym and scan mode.
///
/// Args:
///     xse_acronym: Script extender name (e.g., "F4SE", "SKSE")
///     mode: Scan mode -- "unpacked" or "archived"
///
/// Returns:
///     Dict mapping issue category to list of header/description lines
///
/// Example:
///     >>> messages = get_scan_issue_messages("F4SE", "unpacked")
///     >>> print(messages["tex_dims"])
#[pyfunction]
fn get_scan_issue_messages<'py>(
    py: Python<'py>,
    xse_acronym: &str,
    mode: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let validators = ScanValidators::new();
    let messages = validators.get_issue_messages(xse_acronym, mode);
    let dict = PyDict::new(py);
    for (key, lines) in &messages {
        let py_list = PyList::new(py, lines)?;
        dict.set_item(key, py_list)?;
    }
    Ok(dict)
}

/// Build report for unpacked (loose) mod file scan.
///
/// Args:
///     issue_lists: Dict of issue category -> list/set of issue strings
///     xse_acronym: Script extender name (e.g., "F4SE")
///
/// Returns:
///     Formatted report string
///
/// Example:
///     >>> report = build_unpacked_report({"tex_frmt": ["  - TGA : bad.tga\n"]}, "F4SE")
///     >>> print(report)
#[pyfunction]
fn build_unpacked_report(issue_lists: &Bound<'_, PyDict>, xse_acronym: &str) -> PyResult<String> {
    let issues = dict_to_btreemap(issue_lists)?;
    let validators = ScanValidators::new();
    let builder = ScanReportBuilder::new(&validators);
    Ok(builder.build_unpacked_report(&issues, xse_acronym))
}

/// Build report for archived (BA2) mod file scan.
///
/// Args:
///     issue_lists: Dict of issue category -> list/set of issue strings
///     xse_acronym: Script extender name (e.g., "F4SE")
///
/// Returns:
///     Formatted report string
#[pyfunction]
fn build_archived_report(issue_lists: &Bound<'_, PyDict>, xse_acronym: &str) -> PyResult<String> {
    let issues = dict_to_btreemap(issue_lists)?;
    let validators = ScanValidators::new();
    let builder = ScanReportBuilder::new(&validators);
    Ok(builder.build_archived_report(&issues, xse_acronym))
}

/// Build combined report for both unpacked and archived scans.
///
/// Args:
///     unpacked_issues: Dict of issue category -> list/set of issue strings
///     archived_issues: Dict of issue category -> list/set of issue strings
///     xse_acronym: Script extender name (e.g., "F4SE")
///
/// Returns:
///     Combined formatted report string
///
/// Example:
///     >>> report = build_combined_scan_report(
///     ...     {"tex_frmt": ["  - TGA : bad.tga\n"]},
///     ...     {"ba2_frmt": ["  - invalid.ba2\n"]},
///     ...     "F4SE"
///     ... )
#[pyfunction]
fn build_combined_scan_report(
    unpacked_issues: &Bound<'_, PyDict>,
    archived_issues: &Bound<'_, PyDict>,
    xse_acronym: &str,
) -> PyResult<String> {
    let unpacked = dict_to_btreemap(unpacked_issues)?;
    let archived = dict_to_btreemap(archived_issues)?;
    let validators = ScanValidators::new();
    let builder = ScanReportBuilder::new(&validators);
    Ok(builder.build_combined_report(&unpacked, &archived, xse_acronym))
}

/// Convert a Python dict[str, iterable[str]] to BTreeMap<String, BTreeSet<String>>
fn dict_to_btreemap(dict: &Bound<'_, PyDict>) -> PyResult<BTreeMap<String, BTreeSet<String>>> {
    let mut map = BTreeMap::new();
    for (key, value) in dict.iter() {
        let key_str: String = key.extract()?;
        let mut set = BTreeSet::new();

        // Accept any iterable (list, set, tuple, etc.) from Python
        let iter = value.try_iter()?;
        for item in iter {
            set.insert(item?.extract::<String>()?);
        }

        map.insert(key_str, set);
    }
    Ok(map)
}

/// Register game report functions with the Python module
pub fn register_game_report(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_scan_issue_messages, m)?)?;
    m.add_function(wrap_pyfunction!(build_unpacked_report, m)?)?;
    m.add_function(wrap_pyfunction!(build_archived_report, m)?)?;
    m.add_function(wrap_pyfunction!(build_combined_scan_report, m)?)?;
    Ok(())
}
