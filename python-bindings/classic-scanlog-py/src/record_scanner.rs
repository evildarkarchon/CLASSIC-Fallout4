//! Python bindings for RecordScanner - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::RecordScanner;
use pyo3::prelude::*;

/// Python wrapper for RecordScanner
#[pyclass(name = "RecordScanner")]
pub struct PyRecordScanner {
    inner: RecordScanner,
}

#[pymethods]
impl PyRecordScanner {
    /// Create a new instance

    #[new]
    pub fn new(
        target_records: Vec<String>,
        ignore_records: Vec<String>,
        crashgen_name: String,
    ) -> PyResult<Self> {
        let inner = RecordScanner::new(target_records, ignore_records, crashgen_name);
        Ok(Self { inner })
    }

    /// Scan named records from callstack segment
    pub fn scan_named_records(
        &self,
        segment_callstack: Vec<String>,
    ) -> PyResult<(Vec<String>, Vec<String>)> {
        self.inner
            .try_scan_named_records(&segment_callstack)
            .map_err(crate::to_pyerr)
    }

    /// Extract records from callstack segment
    pub fn extract_records(&self, segment_callstack: Vec<String>) -> PyResult<Vec<String>> {
        self.inner
            .try_extract_records(&segment_callstack)
            .map_err(crate::to_pyerr)
    }

    /// Clear scanner cache
    pub fn clear_cache(&self) {
        self.inner.clear_cache();
    }
}

/// Scan multiple logs for records (standalone function)
#[pyfunction]
pub fn scan_records_batch(
    segments: Vec<Vec<String>>,
    target_records: Vec<String>,
    ignore_records: Vec<String>,
) -> PyResult<Vec<Vec<String>>> {
    classic_scanlog_core::try_scan_records_batch(segments, target_records, ignore_records)
        .map_err(crate::to_pyerr)
}

/// Check if a line contains a record (standalone function)
#[pyfunction]
pub fn contains_record(
    line: String,
    target_records: Vec<String>,
    ignore_records: Vec<String>,
) -> bool {
    classic_scanlog_core::contains_record(&line, &target_records, &ignore_records)
}
