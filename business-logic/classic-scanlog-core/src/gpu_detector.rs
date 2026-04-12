//! GPU Detector - GPU information extraction and vendor detection
//!
//! This module detects GPU information from system specs:
//! - Parsing system specs for GPU information
//! - Determining GPU manufacturer (AMD, Nvidia, Intel)
//! - Identifying rival GPU vendor for compatibility checks

use std::collections::HashMap;

/// GPU vendor enumeration
#[derive(Clone, Debug, PartialEq)]
pub enum GpuVendor {
    /// AMD (Advanced Micro Devices) graphics cards
    AMD,
    /// Nvidia graphics cards
    Nvidia,
    /// Intel integrated graphics
    Intel,
    /// Unknown or unrecognized vendor
    Unknown,
}

impl GpuVendor {
    /// Convert GPU vendor to string representation
    pub fn as_str(&self) -> &'static str {
        match self {
            GpuVendor::AMD => "AMD",
            GpuVendor::Nvidia => "Nvidia",
            GpuVendor::Intel => "Intel",
            GpuVendor::Unknown => "Unknown",
        }
    }
}

impl std::fmt::Display for GpuVendor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

/// GPU information structure
#[derive(Clone, Debug)]
pub struct GpuInfo {
    /// Primary GPU name
    pub primary: String,

    /// Secondary GPU name (if present)
    pub secondary: Option<String>,

    /// GPU manufacturer
    pub manufacturer: String,

    /// Rival GPU manufacturer (for compatibility checks)
    pub rival: Option<String>,
}

impl Default for GpuInfo {
    fn default() -> Self {
        Self::new()
    }
}

impl GpuInfo {
    /// Create a new GpuInfo instance with default "Unknown" values
    pub fn new() -> Self {
        Self {
            primary: "Unknown".to_string(),
            secondary: None,
            manufacturer: "Unknown".to_string(),
            rival: None,
        }
    }

    /// Convert to HashMap for compatibility
    pub fn to_dict(&self) -> HashMap<String, Option<String>> {
        let mut result = HashMap::new();
        result.insert("primary".to_string(), Some(self.primary.clone()));
        result.insert("secondary".to_string(), self.secondary.clone());
        result.insert("manufacturer".to_string(), Some(self.manufacturer.clone()));
        result.insert("rival".to_string(), self.rival.clone());
        result
    }
}

impl std::fmt::Display for GpuInfo {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "GpuInfo(primary={}, manufacturer={}, secondary={:?}, rival={:?})",
            self.primary, self.manufacturer, self.secondary, self.rival
        )
    }
}

/// High-performance GPU detector
#[derive(Clone)]
pub struct GpuDetector;

impl GpuDetector {
    /// Create a new GPU detector instance
    pub fn new() -> Self {
        Self
    }

    /// Extract GPU information from system specification
    ///
    /// Args:
    ///     segment_system: List of system specification lines
    ///
    /// Returns:
    ///     GpuInfo containing detected GPU information
    pub fn get_gpu_info(segment_system: &[String]) -> GpuInfo {
        let mut gpu_info = GpuInfo::new();

        for line in segment_system {
            if line.contains("GPU #1") {
                // Detect vendor
                if line.contains("AMD") {
                    gpu_info.manufacturer = "AMD".to_string();
                    gpu_info.rival = Some("nvidia".to_string());
                    gpu_info.primary = "AMD".to_string();
                } else if line.contains("Nvidia") {
                    gpu_info.manufacturer = "Nvidia".to_string();
                    gpu_info.rival = Some("amd".to_string());
                    gpu_info.primary = "Nvidia".to_string();
                } else if line.contains("Intel") {
                    gpu_info.manufacturer = "Intel".to_string();
                    gpu_info.rival = None; // Intel integrated graphics
                    gpu_info.primary = "Intel".to_string();
                }

                // Extract full GPU name if available (after colon)
                if let Some(colon_pos) = line.find(':') {
                    let gpu_name = line[(colon_pos + 1)..].trim();
                    if !gpu_name.is_empty() {
                        gpu_info.primary = gpu_name.to_string();
                    }
                }
            } else if line.contains("GPU #2") {
                // Extract secondary GPU name (after colon)
                if let Some(colon_pos) = line.find(':') {
                    let gpu_name = line[(colon_pos + 1)..].trim();
                    if !gpu_name.is_empty() {
                        gpu_info.secondary = Some(gpu_name.to_string());
                    }
                }
            }
        }

        gpu_info
    }

    /// Get GPU info as dictionary (compatibility helper)
    pub fn get_gpu_info_dict(segment_system: &[String]) -> HashMap<String, Option<String>> {
        Self::get_gpu_info(segment_system).to_dict()
    }

    /// Batch process GPU info from multiple system segments (parallel)
    pub fn get_gpu_info_batch(system_segments: Vec<Vec<String>>) -> Vec<GpuInfo> {
        use rayon::prelude::*;

        system_segments
            .par_iter()
            .map(|segment| Self::get_gpu_info(segment))
            .collect()
    }
}

impl Default for GpuDetector {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_amd_gpu_detection() {
        let system_lines = vec!["GPU #1: AMD Radeon RX 6800 XT".to_string()];

        let gpu_info = GpuDetector::get_gpu_info(&system_lines);

        assert_eq!(gpu_info.manufacturer, "AMD");
        assert_eq!(gpu_info.primary, "AMD Radeon RX 6800 XT");
        assert_eq!(gpu_info.rival, Some("nvidia".to_string()));
    }

    #[test]
    fn test_nvidia_gpu_detection() {
        let system_lines = vec!["GPU #1: Nvidia GeForce RTX 3080".to_string()];

        let gpu_info = GpuDetector::get_gpu_info(&system_lines);

        assert_eq!(gpu_info.manufacturer, "Nvidia");
        assert_eq!(gpu_info.primary, "Nvidia GeForce RTX 3080");
        assert_eq!(gpu_info.rival, Some("amd".to_string()));
    }

    #[test]
    fn test_intel_gpu_detection() {
        let system_lines = vec!["GPU #1: Intel UHD Graphics 630".to_string()];

        let gpu_info = GpuDetector::get_gpu_info(&system_lines);

        assert_eq!(gpu_info.manufacturer, "Intel");
        assert_eq!(gpu_info.primary, "Intel UHD Graphics 630");
        assert_eq!(gpu_info.rival, None);
    }

    #[test]
    fn test_dual_gpu_detection() {
        let system_lines = vec![
            "GPU #1: Nvidia GeForce RTX 3080".to_string(),
            "GPU #2: Intel UHD Graphics 630".to_string(),
        ];

        let gpu_info = GpuDetector::get_gpu_info(&system_lines);

        assert_eq!(gpu_info.manufacturer, "Nvidia");
        assert_eq!(gpu_info.primary, "Nvidia GeForce RTX 3080");
        assert_eq!(
            gpu_info.secondary,
            Some("Intel UHD Graphics 630".to_string())
        );
    }

    #[test]
    fn test_unknown_gpu() {
        let system_lines = vec!["Some other line".to_string()];

        let gpu_info = GpuDetector::get_gpu_info(&system_lines);

        assert_eq!(gpu_info.manufacturer, "Unknown");
        assert_eq!(gpu_info.primary, "Unknown");
        assert_eq!(gpu_info.rival, None);
    }

    #[test]
    fn test_batch_processing() {
        let batch = vec![
            vec!["GPU #1: AMD Radeon RX 6800 XT".to_string()],
            vec!["GPU #1: Nvidia GeForce RTX 3080".to_string()],
        ];

        let results = GpuDetector::get_gpu_info_batch(batch);

        assert_eq!(results.len(), 2);
        assert_eq!(results[0].manufacturer, "AMD");
        assert_eq!(results[1].manufacturer, "Nvidia");
    }
}
