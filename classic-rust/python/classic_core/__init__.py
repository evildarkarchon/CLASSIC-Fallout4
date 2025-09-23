"""
CLASSIC Core - High-performance Rust extensions for CLASSIC Fallout 4

This module provides drop-in replacements for performance-critical Python components
using Rust implementations via PyO3.
"""

__version__ = "8.0.0"

# Try multiple loading strategies for maximum compatibility
RUST_AVAILABLE = False
_rust = None

# Strategy 1: Try loading from the custom loader (handles all scenarios)
try:
    import sys
    from pathlib import Path
    # Add project root to path if needed
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from ClassicLib.rust_loader import get_rust_module, is_rust_available
    _rust = get_rust_module()
    RUST_AVAILABLE = _rust is not None
except ImportError:
    pass

# Strategy 2: Try direct import (for when it's properly installed)
if not RUST_AVAILABLE:
    try:
        from . import _rust
        RUST_AVAILABLE = True
    except ImportError:
        pass

# Strategy 3: Try importing from known locations
if not RUST_AVAILABLE:
    import importlib.util
    possible_paths = [
        Path(__file__).parent / "_rust.pyd",  # Same directory
        Path(__file__).parent.parent.parent.parent / "rust_extensions" / "classic_core._rust.pyd",
        Path(__file__).parent.parent.parent.parent / "ClassicLib" / "rust_ext" / "_rust.pyd",
    ]

    for path in possible_paths:
        if path.exists():
            try:
                spec = importlib.util.spec_from_file_location("_rust", path)
                if spec and spec.loader:
                    _rust = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(_rust)
                    RUST_AVAILABLE = True
                    break
            except:
                continue

# Final warning if nothing worked
if not RUST_AVAILABLE:
    import warnings
    warnings.warn(
        "Rust extensions not available. Falling back to pure Python implementations.",
        ImportWarning
    )

# Re-export main classes
if RUST_AVAILABLE:
    from .adapters import (
        DatabasePool,
        FileIOCore,
        FormIDAnalyzer,
        LogParser,
        PatternMatcher,
        StringProcessor,
    )

__all__ = [
    "RUST_AVAILABLE",
    "DatabasePool",
    "FileIOCore",
    "FormIDAnalyzer",
    "LogParser",
    "PatternMatcher",
    "StringProcessor",
    "__version__",
]
