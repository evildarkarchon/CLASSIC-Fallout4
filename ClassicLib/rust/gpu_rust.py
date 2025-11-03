"""
Rust-accelerated GPUDetector wrapper.

This module provides a transparent wrapper around the Rust GpuDetector implementation,
maintaining full API compatibility with the Python reference while delivering performance
improvements.

Key API Translations:
- Python: get_gpu_info() standalone function returning dict
- Rust: GpuDetector.extract_gpu_info() instance method returning GpuInfo object
- Return type: Convert Rust GpuInfo object to Python dict
"""

from __future__ import annotations

try:
    import classic_scanlog

    RustGpuDetector = classic_scanlog.GpuDetector
    RustGpuInfo = classic_scanlog.GpuInfo
    RUST_AVAILABLE = True
except (ImportError, AttributeError):
    RustGpuDetector = None
    RustGpuInfo = None
    RUST_AVAILABLE = False


def get_gpu_info(segment_system: list[str]) -> dict[str, str | None]:
    """
    Extracts and processes GPU information from a given system specification.

    This function takes a list of system specification data typically in string
    format and identifies GPU-related details such as the primary GPU name,
    secondary GPU name, GPU manufacturer, and the rival manufacturer.

    Args:
        segment_system: A list of strings containing system specification information.
            Each string represents a line of system description that may or may not
            include GPU-related details.

    Returns:
        A dictionary containing GPU information with the following keys:
            - primary: str - The name of the primary GPU. If not found, defaults to "Unknown".
            - secondary: str | None - The name of the secondary GPU. If not found, defaults to None.
            - manufacturer: str - The name of the GPU manufacturer (e.g., "AMD", "Nvidia").
              If not found, defaults to "Unknown".
            - rival: str | None - The name of the rival GPU manufacturer. If not found,
              defaults to None.
    """
    if RUST_AVAILABLE:
        # Use Rust implementation
        detector = RustGpuDetector()
        gpu_info = detector.extract_gpu_info(segment_system)

        # Convert Rust GpuInfo object to dict for Python API compatibility
        # Rust returns GpuInfo with primary, manufacturer, secondary (Option<String>), rival (Option<String>)
        return {
            "primary": gpu_info.primary,
            "secondary": gpu_info.secondary,  # Rust returns None if not present
            "manufacturer": gpu_info.manufacturer,
            "rival": gpu_info.rival,  # Rust returns None if not present
        }
    # Fallback to Python implementation
    from ClassicLib.ScanLog.GPUDetector import get_gpu_info as py_get_gpu_info

    return py_get_gpu_info(segment_system)


# Export for compatibility
__all__ = ["get_gpu_info", "RUST_AVAILABLE"]
