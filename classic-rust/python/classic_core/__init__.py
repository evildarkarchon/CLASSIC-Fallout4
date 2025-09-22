"""
CLASSIC Core - High-performance Rust extensions for CLASSIC Fallout 4

This module provides drop-in replacements for performance-critical Python components
using Rust implementations via PyO3.
"""

__version__ = "8.0.0"

# Import the Rust extension module
try:
    from . import _rust
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    import warnings
    warnings.warn(
        "Rust extensions not available. Falling back to pure Python implementations.",
        ImportWarning
    )

# Re-export main classes
if RUST_AVAILABLE:
    from .adapters import (
        FileIOCore,
        FormIDAnalyzer,
        LogParser,
        PatternMatcher,
        DatabasePool,
        StringProcessor,
    )

__all__ = [
    "FileIOCore",
    "FormIDAnalyzer",
    "LogParser",
    "PatternMatcher",
    "DatabasePool",
    "StringProcessor",
    "RUST_AVAILABLE",
    "__version__",
]
