//! Python bindings for encoding detection (thin PyO3 adapter)

use classic_file_io_core::EncodingDetector;
use pyo3::prelude::*;

/// Python wrapper for EncodingDetector
#[pyclass(name = "EncodingDetector")]
pub struct PyEncodingDetector {
    inner: EncodingDetector,
}

impl Default for PyEncodingDetector {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyEncodingDetector {
    /// Create a new instance
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
