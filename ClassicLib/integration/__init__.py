"""CLASSIC Rust Integration Layer.

This package provides a clean separation between Rust component detection,
factory functions, and status monitoring for the CLASSIC application.

The integration layer handles:
- Runtime detection of available Rust components
- Factory functions that return the best available implementation
- Status monitoring and performance reporting
- Configuration management
"""

from __future__ import annotations

# Runtime diagnostics (Phase 3)
from ClassicLib.integration.diagnostics import (
    get_runtime_stats,
    is_runtime_healthy,
    print_runtime_status,
)

# Exception types for Rust integration errors
from ClassicLib.integration.exceptions import (
    RustConcurrencyError,
    RustConfigError,
    RustDatabaseError,
    RustError,
    RustIOError,
    RustMemoryError,
    RustParseError,
)

# Centralized component detection
from ClassicLib.integration.factory import (
    detect_component,
    get_component,
    is_component_available,
)

# Note: We don't import other submodules here to avoid circular dependencies.
# Users should import directly from the submodules:
#   from ClassicLib.integration.factory import get_parser

__all__ = [
    # Exception types
    "RustError",
    "RustIOError",
    "RustParseError",
    "RustConfigError",
    "RustDatabaseError",
    "RustMemoryError",
    "RustConcurrencyError",
    # Centralized detection (Phase 3)
    "detect_component",
    "is_component_available",
    "get_component",
    # Runtime diagnostics (Phase 3)
    "get_runtime_stats",
    "is_runtime_healthy",
    "print_runtime_status",
]
