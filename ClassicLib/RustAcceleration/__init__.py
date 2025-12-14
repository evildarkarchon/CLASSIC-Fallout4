"""RustAcceleration Coordination Package for CLASSIC.

This package provides centralized coordination and management of all Rust-accelerated
components in CLASSIC. It handles component orchestration, performance monitoring,
automatic optimization, and provides a unified interface for the entire Rust subsystem.

Features:
- Centralized component management and configuration
- Performance monitoring and metrics collection
- Automatic optimization based on workload characteristics
- Component health checks and diagnostics
- Unified error handling and recovery
- Real-time performance statistics

This is the primary interface for Phase 6: Integration & Optimization.

All classes and functions are re-exported from their individual modules
for backward compatibility.
"""

from __future__ import annotations

# Re-export all public API for backward compatibility
from ClassicLib.RustAcceleration.coordinator import (
    RustAcceleration,
    configure_for_batch_processing,
    configure_for_single_file,
    get_rust_acceleration,
    perform_health_check,
    print_acceleration_status,
)
from ClassicLib.RustAcceleration.metrics import ComponentMetrics
from ClassicLib.RustAcceleration.types import ComponentType
from ClassicLib.RustAcceleration.workload import OptimizationLevel, WorkloadCharacteristics

# Initialize on package import for pre-release
_accelerator = get_rust_acceleration()

__all__ = [
    # Types and enums
    "ComponentMetrics",
    "ComponentType",
    "OptimizationLevel",
    "WorkloadCharacteristics",
    # Main class
    "RustAcceleration",
    # Convenience functions
    "configure_for_batch_processing",
    "configure_for_single_file",
    "get_rust_acceleration",
    "perform_health_check",
    "print_acceleration_status",
]
