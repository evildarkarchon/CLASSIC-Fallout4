"""
Rust Component Detection Module

Handles runtime detection of available Rust components for CLASSIC.
This module checks for the availability of the classic_core Rust extension
and identifies which components are available for acceleration.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def detect_rust_components() -> dict[str, bool]:
    """
    Detect available Rust components.

    Returns:
        Dictionary mapping component names to their availability status.
    """
    # Check if Rust is disabled via environment variable
    if os.environ.get("CLASSIC_DISABLE_RUST", "").lower() in ("1", "true", "yes"):
        logger.info("Rust acceleration disabled via CLASSIC_DISABLE_RUST environment variable")
        return _get_empty_component_dict()

    components = _get_empty_component_dict()

    try:
        import classic_core
        logger.info(f"classic_core module loaded (version: {getattr(classic_core, '__version__', 'unknown')})")

        # Check scanlog module components
        if hasattr(classic_core, "scanlog"):
            scanlog = classic_core.scanlog
            logger.debug("scanlog module detected")

            # LogParser
            if hasattr(scanlog, "LogParser"):
                components["parser"] = True
                logger.debug("LogParser component available")

            # FormIDAnalyzer
            if hasattr(scanlog, "FormIDAnalyzer"):
                components["formid_analyzer"] = True
                logger.debug("FormIDAnalyzer component available")

            # PluginAnalyzer
            if hasattr(scanlog, "PluginAnalyzer"):
                components["plugin_analyzer"] = True
                logger.debug("PluginAnalyzer component available")

            # RecordScanner
            if hasattr(scanlog, "RecordScanner"):
                components["record_scanner"] = True
                logger.debug("RecordScanner component available")

            # Report Generation
            if hasattr(scanlog, "ReportGenerator") or hasattr(scanlog, "report"):
                components["report_generation"] = True
                logger.debug("ReportGenerator component available")

            # Mod Detector functions
            if hasattr(scanlog, "detect_mods_batch") or hasattr(scanlog, "detect_mods_single"):
                components["mod_detector"] = True
                logger.debug("ModDetector functions available")

        # Check classic_scanlog standalone module for Phase 2 components
        try:
            import classic_scanlog

            # SuspectScanner
            if hasattr(classic_scanlog, "SuspectScanner"):
                components["suspect_scanner"] = True
                logger.debug("SuspectScanner component available (classic_scanlog)")

            # SettingsValidator
            if hasattr(classic_scanlog, "SettingsValidator"):
                components["settings_validator"] = True
                logger.debug("SettingsValidator component available (classic_scanlog)")

            # GpuDetector
            if hasattr(classic_scanlog, "GpuDetector"):
                components["gpu_detector"] = True
                logger.debug("GpuDetector component available (classic_scanlog)")

            # FcxModeHandler
            if hasattr(classic_scanlog, "FcxModeHandler"):
                components["fcx_handler"] = True
                logger.debug("FcxModeHandler component available (classic_scanlog)")

        except ImportError:
            logger.debug("classic_scanlog module not available for Phase 2 components")

        # Check database module components
        if hasattr(classic_core, "database"):
            components["database"] = True
            logger.debug("database module detected")

            # Database Pool
            if hasattr(classic_core.database, "RustDatabasePool") or hasattr(classic_core.database, "DatabasePool"):
                components["database_pool"] = True
                logger.debug("DatabasePool component available")

        # Check file I/O module components
        if hasattr(classic_core, "file_io"):
            components["file_io"] = True
            logger.debug("file_io module detected")

            # FileIOCore
            if hasattr(classic_core.file_io, "RustFileIOCore"):
                components["file_io_core"] = True
                logger.debug("FileIOCore component available")

        # Check YAML module components
        if hasattr(classic_core, "yaml"):
            components["yaml"] = True
            logger.debug("yaml module detected")

            # RustYamlOperations
            if hasattr(classic_core.yaml, "RustYamlOperations"):
                components["yaml_operations"] = True
                logger.debug("RustYamlOperations component available")

    except ImportError as e:
        logger.warning(f"classic_core module not available: {e}")
    except Exception as e:
        logger.error(f"Error detecting Rust components: {e}")

    # Check config-core (standalone module)
    try:
        import classic_config
        logger.info(f"classic_config module loaded (version: {getattr(classic_config, '__version__', 'unknown')})")

        # YamlData
        if hasattr(classic_config, "YamlData"):
            components["yamldata"] = True
            logger.debug("YamlData component available")

    except ImportError as e:
        logger.warning(f"classic_config module not available: {e}")
    except Exception as e:
        logger.error(f"Error detecting config module: {e}")

    return components


def get_available_components() -> dict[str, Any]:
    """
    Get detailed information about available Rust components.

    Returns:
        Dictionary containing:
        - components: Dict of component availability
        - version: Version of classic_core if available
        - disabled: Whether Rust is disabled by environment variable
    """
    disabled = os.environ.get("CLASSIC_DISABLE_RUST", "").lower() in ("1", "true", "yes")
    version = "unknown"

    try:
        if not disabled:
            import classic_core
            version = getattr(classic_core, '__version__', 'unknown')
    except ImportError:
        pass

    return {
        "components": detect_rust_components(),
        "version": version,
        "disabled": disabled
    }


def _get_empty_component_dict() -> dict[str, bool]:
    """Get an empty component dictionary with all components set to False."""
    return {
        "parser": False,
        "formid_analyzer": False,
        "plugin_analyzer": False,
        "record_scanner": False,
        "report_generation": False,
        "database": False,
        "database_pool": False,
        "file_io": False,
        "file_io_core": False,
        "mod_detector": False,
        "yaml": False,
        "yaml_operations": False,
        "yamldata": False,
        # Phase 2 components (classic_scanlog module)
        "suspect_scanner": False,
        "settings_validator": False,
        "gpu_detector": False,
        "fcx_handler": False,
    }
