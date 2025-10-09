//! Python bindings for GPU detection - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::{GpuDetector, GpuInfo, GpuVendor};
use pyo3::prelude::*;
use std::collections::HashMap;

/// Python wrapper for GpuVendor enum
#[pyclass(name = "GpuVendor")]
#[derive(Clone)]
pub struct PyGpuVendor {
    inner: GpuVendor,
}

#[pymethods]
impl PyGpuVendor {
    #[new]
    pub fn new(vendor_name: String) -> Self {
        let inner = match vendor_name.to_uppercase().as_str() {
            "AMD" => GpuVendor::AMD,
            "NVIDIA" => GpuVendor::Nvidia,
            "INTEL" => GpuVendor::Intel,
            _ => GpuVendor::Unknown,
        };
        Self { inner }
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    fn __repr__(&self) -> String {
        format!("GpuVendor({})", self.inner.as_str())
    }
}

/// Python wrapper for GpuInfo
#[pyclass(name = "GpuInfo")]
#[derive(Clone)]
pub struct PyGpuInfo {
    inner: GpuInfo,
}

#[pymethods]
impl PyGpuInfo {
    #[new]
    pub fn new() -> Self {
        Self {
            inner: GpuInfo::new(),
        }
    }

    #[getter]
    pub fn primary(&self) -> String {
        self.inner.primary.clone()
    }

    #[getter]
    pub fn secondary(&self) -> Option<String> {
        self.inner.secondary.clone()
    }

    #[getter]
    pub fn manufacturer(&self) -> String {
        self.inner.manufacturer.clone()
    }

    #[getter]
    pub fn rival(&self) -> Option<String> {
        self.inner.rival.clone()
    }

    pub fn to_dict(&self) -> HashMap<String, Option<String>> {
        self.inner.to_dict()
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    fn __repr__(&self) -> String {
        format!("{:?}", self.inner)
    }
}

/// Python wrapper for GpuDetector
#[pyclass(name = "GpuDetector")]
pub struct PyGpuDetector {
    inner: GpuDetector,
}

#[pymethods]
impl PyGpuDetector {
    #[new]
    pub fn new() -> Self {
        Self {
            inner: GpuDetector::new(),
        }
    }

    /// Extract GPU information from system specification
    pub fn extract_gpu_info(&self, segment_system: Vec<String>) -> PyGpuInfo {
        // Use static method from core
        let gpu_info = GpuDetector::get_gpu_info(&segment_system);
        PyGpuInfo { inner: gpu_info }
    }

    /// Batch extract GPU info from multiple logs
    pub fn extract_gpu_info_batch(&self, system_segments: Vec<Vec<String>>) -> Vec<PyGpuInfo> {
        // Use static method from core
        GpuDetector::get_gpu_info_batch(system_segments)
            .into_iter()
            .map(|info| PyGpuInfo { inner: info })
            .collect()
    }
}
