"""Factory module for dynamic implementation selection.

This package provides factory functions for selecting between Rust and Python
implementations of various components, with automatic fallback mechanisms.

Submodules:
    core: Shared utilities for component detection and caching.
    file_io: File I/O and YAML operations factories.
    parsers: Log parser factories.
    analyzers: Analysis component factories.
    database: Database pool factories.
    scanlog: Crash log scanning and reporting factories.
    game: Game configuration and mode handling factories.
    utilities: Phase 4 utility module factories.

All factory functions are re-exported from this module for backward compatibility.
Import directly from ClassicLib.integration.factory:

    from ClassicLib.integration.factory import get_file_io, get_parser

Or import from submodules for explicit organization:

    from ClassicLib.integration.factory.analyzers import get_formid_analyzer
"""

from __future__ import annotations

# Analyzers
from ClassicLib.integration.factory.analyzers import (
    get_formid_analyzer,
    get_gpu_detector,
    get_plugin_analyzer,
    get_record_scanner,
    get_settings_validator,
    get_suspect_scanner,
)

# Core utilities
from ClassicLib.integration.factory.core import (
    get_components,
    is_rust_disabled,
    reset_cache,
)

# Database
from ClassicLib.integration.factory.database import get_database_pool

# File I/O
from ClassicLib.integration.factory.file_io import (
    get_file_io,
    get_yaml_operations,
)

# Game
from ClassicLib.integration.factory.game import (
    get_fcx_handler,
    get_yamldata,
)

# Parsers
from ClassicLib.integration.factory.parsers import (
    PythonParserWrapper,
    get_parser,
)

# Scanlog
from ClassicLib.integration.factory.scanlog import (
    get_mod_detector,
    get_orchestrator,
    get_report_generator,
)

# Utilities (Phase 4)
from ClassicLib.integration.factory.utilities import (
    get_constants,
    get_path_operations,
    get_resource_mgmt,
    get_version_utils,
    get_web_utils,
    get_xse_utils,
)

# Backward compatibility aliases
_get_components = get_components
_is_rust_disabled = is_rust_disabled

__all__ = [
    # Core
    "get_components",
    "is_rust_disabled",
    "reset_cache",
    # Backward compatibility
    "_get_components",
    "_is_rust_disabled",
    # File I/O
    "get_file_io",
    "get_yaml_operations",
    # Parsers
    "get_parser",
    "PythonParserWrapper",
    # Analyzers
    "get_formid_analyzer",
    "get_plugin_analyzer",
    "get_record_scanner",
    "get_suspect_scanner",
    "get_settings_validator",
    "get_gpu_detector",
    # Database
    "get_database_pool",
    # Scanlog
    "get_report_generator",
    "get_mod_detector",
    "get_orchestrator",
    # Game
    "get_yamldata",
    "get_fcx_handler",
    # Utilities
    "get_constants",
    "get_version_utils",
    "get_resource_mgmt",
    "get_xse_utils",
    "get_web_utils",
    "get_path_operations",
]
