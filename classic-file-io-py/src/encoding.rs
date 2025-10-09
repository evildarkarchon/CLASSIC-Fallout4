//! Python bindings for encoding detection (thin PyO3 adapter)

use pyo3::prelude::*;
use classic_file_io_core::EncodingDetector;

/// Python wrapper for EncodingDetector
#[pyclass(name = "EncodingDetector")]
pub struct PyEncodingDetector {
    inner: EncodingDetector,
}

#[pymethods]
impl PyEncodingDetector {
    #[new]
    pub fn new() -> Self {
        Self {
            inner: EncodingDetector::new(),
        }
    }

    /// Detect encoding from bytes
    pub fn detect_encoding(&self, bytes: &[u8]) -> String {
        self.inner.detect_name(bytes)
    }
}
