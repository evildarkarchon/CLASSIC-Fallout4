//! Python bindings for GPU detection - Thin wrapper over classic-scanlog-core

use classic_scanlog_core::{GpuDetector, GpuInfo, GpuVendor};
use pyo3::prelude::*;
use std::collections::HashMap;

/// Python wrapper for GpuVendor enum
///
/// Represents GPU vendor/manufacturer (AMD, Nvidia, Intel, or Unknown)
#[pyclass(name = "GpuVendor", from_py_object)]
#[derive(Clone)]
pub struct PyGpuVendor {
    /// Inner Rust GpuVendor instance
    inner: GpuVendor,
}

#[pymethods]
impl PyGpuVendor {
    /// Create a new GpuVendor from vendor name string
    ///
    /// # Arguments
    /// * `vendor_name` - Vendor name (case-insensitive: "AMD", "NVIDIA", "INTEL")
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

    /// String representation of the vendor
    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    /// Python repr() representation
    fn __repr__(&self) -> String {
        format!("GpuVendor({})", self.inner.as_str())
    }
}

/// Python wrapper for GpuInfo
///
/// Contains detected GPU information including primary/secondary GPUs,
/// manufacturer, and potential rival GPU vendor.
#[pyclass(name = "GpuInfo", from_py_object)]
#[derive(Clone)]
pub struct PyGpuInfo {
    /// Inner Rust GpuInfo instance
    inner: GpuInfo,
}

impl Default for PyGpuInfo {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PyGpuInfo {
    /// Create a new empty GpuInfo instance
    #[new]
    pub fn new() -> Self {
        Self {
            inner: GpuInfo::new(),
        }
    }

    /// Get the primary GPU name
    #[getter]
    pub fn primary(&self) -> String {
        self.inner.primary.clone()
    }

    /// Get the secondary GPU name if present (for multi-GPU systems)
    #[getter]
    pub fn secondary(&self) -> Option<String> {
        self.inner.secondary.clone()
    }

    /// Get the GPU manufacturer/vendor name
    #[getter]
    pub fn manufacturer(&self) -> String {
        self.inner.manufacturer.clone()
    }

    /// Get the rival GPU vendor if detected (for multi-vendor systems)
    #[getter]
    pub fn rival(&self) -> Option<String> {
        self.inner.rival.clone()
    }

    /// Convert GPU info to a dictionary representation
    pub fn to_dict(&self) -> HashMap<String, Option<String>> {
        self.inner.to_dict()
    }

    /// String representation of GPU info
    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    /// Python repr() representation
    fn __repr__(&self) -> String {
        format!("{:?}", self.inner)
    }
}

/// Python wrapper for GpuDetector
///
/// Detects GPU information from crash log system specifications.
#[pyclass(name = "GpuDetector")]
pub struct PyGpuDetector;

impl Default for PyGpuDetector {
    fn default() -> Self {
        Self
    }
}

#[pymethods]
impl PyGpuDetector {
    /// Create a new GPU detector instance
    #[new]
    pub fn new() -> Self {
        Self
    }

    /// Extract GPU information from system specification
    ///
    /// # Arguments
    /// * `segment_system` - System specification lines from crash log
    ///
    /// # Returns
    /// Detected GPU information
    pub fn extract_gpu_info(&self, segment_system: Vec<String>) -> PyGpuInfo {
        // Use static method from core
        let gpu_info = GpuDetector::get_gpu_info(&segment_system);
        PyGpuInfo { inner: gpu_info }
    }

    /// Batch extract GPU info from multiple logs
    ///
    /// # Arguments
    /// * `system_segments` - Vector of system specification segments from multiple crash logs
    ///
    /// # Returns
    /// Vector of GPU information for each log
    pub fn extract_gpu_info_batch(&self, system_segments: Vec<Vec<String>>) -> Vec<PyGpuInfo> {
        // Use static method from core
        GpuDetector::get_gpu_info_batch(system_segments)
            .into_iter()
            .map(|info| PyGpuInfo { inner: info })
            .collect()
    }
}
