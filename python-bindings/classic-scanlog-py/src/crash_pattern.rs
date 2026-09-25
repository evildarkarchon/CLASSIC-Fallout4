//! Thin Python transport for the shared crash-header pattern classifier.

use pyo3::prelude::*;

/// Classifies the first thirty header lines and returns a stable token or `None`.
/// Matching is case-insensitive and includes symbolic names and hexadecimal codes.
#[pyfunction]
pub fn detect_crash_pattern(content: &str) -> Option<String> {
    classic_scanlog_core::detect_crash_pattern(content).map(str::to_owned)
}
