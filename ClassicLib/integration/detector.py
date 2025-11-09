"""
A module to detect and analyze availability of Rust components.

This module provides functionality to verify the presence and availability of
various Rust components utilized in the system. It includes options to fetch
detailed component information while honoring runtime conditions such as the
environmental disablement of Rust-related acceleration.

Functions:
    detect_rust_components: Checks the availability of Rust components.
    get_available_components: Gathers comprehensive details about Rust components,
                              including their version and environmental status.
    detect_component: Centralized component detection with caching.
    is_component_available: Check if a component is available.
    get_component: Get a component or raise ImportError.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Cache for component detection results (avoids repeated imports)
_detection_cache: dict[str, tuple[bool, Any | None]] = {}

# Configuration for module component detection
MODULE_CONFIGS = {
    "classic_scanlog": {
        "components": {
            "LogParser": "parser",
            "FormIDAnalyzer": "formid_analyzer",
            "PluginAnalyzer": "plugin_analyzer",
            "RecordScanner": "record_scanner",
            "ReportGenerator": "report_generation",
            "SuspectScanner": "suspect_scanner",
            "SettingsValidator": "settings_validator",
            "GpuDetector": "gpu_detector",
            "FcxModeHandler": "fcx_handler",
            "Orchestrator": "orchestrator",
        },
        "special_checks": [
            (("detect_mods_batch", "detect_mods_single"), "mod_detector"),
        ],
    },
    "classic_database": {
        "base_component": "database",
        "components": {
            "DatabasePool": "database_pool",
        },
    },
    "classic_file_io": {
        "base_component": "file_io",
        "components": {
            "FileIOCore": "file_io_core",
        },
    },
    "classic_yaml": {
        "base_component": "yaml",
        "components": {
            "YamlOperations": "yaml_operations",
        },
    },
    "classic_path": {
        "base_component": "path",
        "components": {
            "RustPathOperations": "path_operations",
        },
    },
    "classic_config": {
        "components": {
            "YamlData": "yamldata",
        },
    },
    "classic_constants": {
        "base_component": "constants",
    },
    "classic_version": {
        "base_component": "version_utils",
    },
    "classic_resource": {
        "base_component": "resource_mgmt",
    },
    "classic_xse": {
        "base_component": "xse_utils",
    },
    "classic_web": {
        "base_component": "web_utils",
    },
}


def _check_module_components(module: Any, config: dict[str, Any], components: dict[str, bool]) -> None:
    """Check and update component availability from a module based on config.

    Args:
        module: The imported module to check.
        config: Configuration dict with 'components', 'base_component', and 'special_checks'.
        components: Dictionary to update with component availability.
    """
    # Check base component (the module itself)
    if "base_component" in config:
        components[config["base_component"]] = True
        logger.debug(f"{config['base_component']} module available")

    # Check regular components (attributes)
    for attr_name, component_key in config.get("components", {}).items():
        if hasattr(module, attr_name):
            components[component_key] = True
            logger.debug(f"{attr_name} component available")

    # Check special conditions (multiple attributes for one component)
    for attr_names, component_key in config.get("special_checks", []):
        if any(hasattr(module, attr) for attr in attr_names):
            components[component_key] = True
            logger.debug(f"{component_key} functions available")


def _try_import_module(module_name: str, config: dict[str, Any], components: dict[str, bool]) -> None:
    """Try to import a module and check its components.

    Args:
        module_name: Name of the module to import.
        config: Configuration dict for component checking.
        components: Dictionary to update with component availability.

    Note:
        Catches ImportError for unavailable modules and broad Exception for
        unexpected errors during component detection. Broad exception catching
        is necessary to prevent any single module's issues from breaking the
        entire detection process.
    """
    try:
        module = __import__(module_name)
        version = getattr(module, "__version__", "unknown")
        logger.info(f"{module_name} module loaded (version: {version})")
        _check_module_components(module, config, components)
    except ImportError as e:
        logger.warning(f"{module_name} module not available: {e}")
    except Exception as e:  # noqa: BLE001 - Intentional broad catch for robustness
        logger.error(f"Error detecting {module_name} components: {e}")


def detect_rust_components() -> dict[str, bool]:
    """
    Detects and validates the availability of Rust-based components and modules.

    This function determines which Rust-based components are enabled and available
    for use. It uses a configuration-driven approach to check various modules and
    their attributes or functions. The output is a dictionary where component names
    are the keys, and boolean values indicate whether the component is available
    (`True`) or unavailable (`False`).

    The function also respects the environment variable `CLASSIC_DISABLE_RUST` to
    disable Rust acceleration globally when specified.

    Returns:
        dict[str, bool]: A dictionary indicating the availability of Rust components.
    """
    # Check if Rust is disabled via environment variable
    if os.environ.get("CLASSIC_DISABLE_RUST", "").lower() in {"1", "true", "yes"}:
        logger.info("Rust acceleration disabled via CLASSIC_DISABLE_RUST environment variable")
        return _get_empty_component_dict()

    components = _get_empty_component_dict()

    # Iterate through all configured modules and check their components
    for module_name, config in MODULE_CONFIGS.items():
        _try_import_module(module_name, config, components)

    return components


def get_available_components() -> dict[str, Any]:
    """
    Retrieves the available components and their respective state for the system.

    This function gathers information about the available components by detecting
    Rust components and checking if they are disabled through an environment variable.
    It also determines versions of available Rust modules.

    Returns:
        dict[str, Any]: A dictionary containing:
            - "components": The result from `detect_rust_components()` function.
            - "versions": Dict of module versions for available modules.
            - "disabled": Whether Rust components are disabled, determined by the
              environment variable `CLASSIC_DISABLE_RUST`.
    """
    disabled = os.environ.get("CLASSIC_DISABLE_RUST", "").lower() in {"1", "true", "yes"}
    versions = {}

    if not disabled:
        # Check versions of individual modules
        for module_name in [
            "classic_scanlog",
            "classic_database",
            "classic_file_io",
            "classic_yaml",
            "classic_path",
            "classic_config",
            # Phase 4 - Constants and Utilities
            "classic_constants",
            "classic_version",
            "classic_resource",
            "classic_xse",
            "classic_web",
        ]:
            try:
                module = __import__(module_name)
                versions[module_name] = getattr(module, "__version__", "unknown")
            except ImportError:
                pass

    return {"components": detect_rust_components(), "versions": versions, "disabled": disabled}


def _get_empty_component_dict() -> dict[str, bool]:
    """
    Generates a dictionary representing the status of various components with initial
    states set to `False`.

    This function provides a structured way to initialize component status, suitable for
    describing the state of different modules or features in a system.

    Returns:
        dict[str, bool]: A dictionary where keys are component names as strings and values
        are booleans representing the initialization status of the components (default is
        `False`).
    """
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
        "path": False,
        "path_operations": False,
        "yamldata": False,
        # Phase 2 components (classic_scanlog module)
        "suspect_scanner": False,
        "settings_validator": False,
        "gpu_detector": False,
        "fcx_handler": False,
        "orchestrator": False,
        # Phase 4 - Constants and Utilities
        "constants": False,
        "version_utils": False,
        "resource_mgmt": False,
        "xse_utils": False,
        "web_utils": False,
    }


# ==========================================
# Centralized Component Detection (Phase 3)
# ==========================================


def detect_component(module_name: str, class_name: str | None = None) -> tuple[bool, Any | None]:
    """Detect if a Rust component is available.

    This function provides centralized detection with caching to avoid repeated
    import attempts. Use this instead of module-level try/except blocks in wrappers.

    Args:
        module_name: Python module name (e.g., "classic_yaml")
        class_name: Optional class name within module (e.g., "YamlOperations")

    Returns:
        Tuple of (available: bool, component: Any | None)

    Example:
        >>> available, YamlOps = detect_component("classic_yaml", "YamlOperations")
        >>> if available:
        ...     ops = YamlOps()
    """
    cache_key = f"{module_name}:{class_name}" if class_name else module_name

    # Check cache first (avoids repeated imports)
    if cache_key in _detection_cache:
        return _detection_cache[cache_key]

    try:
        # Import the module
        module = __import__(module_name)

        # Get the class if specified
        if class_name:
            if not hasattr(module, class_name):
                result = (False, None)
            else:
                component = getattr(module, class_name)
                result = (True, component)
        else:
            result = (True, module)

    except ImportError:
        result = (False, None)

    # Cache the result
    _detection_cache[cache_key] = result
    return result


def is_component_available(module_name: str, class_name: str | None = None) -> bool:
    """Check if a Rust component is available (convenience method).

    Args:
        module_name: Python module name
        class_name: Optional class name within module

    Returns:
        True if component is available, False otherwise

    Example:
        >>> if is_component_available("classic_yaml", "YamlOperations"):
        ...     print("Rust YAML acceleration available")
    """
    available, _ = detect_component(module_name, class_name)
    return available


def get_component(module_name: str, class_name: str) -> Any:
    """Get a Rust component or raise ImportError.

    Args:
        module_name: Python module name
        class_name: Class name within module

    Returns:
        The component class

    Raises:
        ImportError: If component is not available

    Example:
        >>> YamlOps = get_component("classic_yaml", "YamlOperations")
        >>> ops = YamlOps()
    """
    available, component = detect_component(module_name, class_name)
    if not available:
        msg = f"Rust component {module_name}.{class_name} not available"
        raise ImportError(msg)
    return component
