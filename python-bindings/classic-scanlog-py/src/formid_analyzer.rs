//! Python projection of independently useful FormID batch utilities.

use pyo3::prelude::*;

/// Extracts FormIDs from multiple callstack segments in parallel.
#[pyfunction]
pub fn extract_formids_batch(callstack_segments: Vec<Vec<String>>) -> Vec<Vec<String>> {
    classic_scanlog_core::extract_formids_batch(callstack_segments)
}

/// Returns whether a string contains a syntactically valid non-null FormID.
#[pyfunction]
pub fn is_valid_formid(formid: &str) -> bool {
    classic_scanlog_core::is_valid_formid(formid)
}

/// Validates multiple owned FormID strings in input order.
#[pyfunction]
pub fn validate_formids_batch(formids: Vec<String>) -> Vec<bool> {
    classic_scanlog_core::validate_formids_batch(formids)
}
