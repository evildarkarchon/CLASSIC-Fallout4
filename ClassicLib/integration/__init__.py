"""
CLASSIC Rust Integration Layer

This package provides a clean separation between Rust component detection,
factory functions, and status monitoring for the CLASSIC application.

The integration layer handles:
- Runtime detection of available Rust components
- Factory functions that return the best available implementation
- Status monitoring and performance reporting
- Configuration management
"""

from __future__ import annotations

# Note: We don't import submodules here to avoid circular dependencies.
# Users should import directly from the submodules:
#   from ClassicLib.integration.factory import get_parser
#   from ClassicLib.integration.status import is_rust_accelerated
#   from ClassicLib.integration.config import ALL_COMPONENTS
