"""Phase 4 utility factory functions.

Provides factory functions for constants and utility modules,
selecting between Rust and Python implementations.

Functions:
    get_constants: Retrieve the Rust constants module.
    get_version_utils: Retrieve the Rust version utilities module.
    get_resource_mgmt: Retrieve the Rust resource management module.
    get_xse_utils: Retrieve the Rust XSE utilities module.
    get_web_utils: Retrieve the Rust web utilities module.
    get_path_operations: Retrieve the Rust path operations module.
"""

from __future__ import annotations

import logging
from typing import Any

from ClassicLib.integration.factory.core import get_components, is_rust_disabled

logger = logging.getLogger(__name__)


def get_constants() -> Any | None:
    """Retrieve the Rust-based constants module if available.

    This function attempts to import and return the Rust `classic_constants`
    module, which provides game constants, enumerations, and common values
    with high performance. If the module is unavailable or Rust is disabled,
    returns None.

    Returns:
        Any | None: The classic_constants module if available, None otherwise.

    Examples:
        >>> constants = get_constants()
        >>> if constants:
        ...     game = constants.GameId.fallout4()
        ...     print(f"Game: {game.as_str()}")

    """
    components = get_components()

    if not is_rust_disabled() and components.get("constants", False):
        try:
            import classic_constants
        except ImportError as e:
            logger.warning(f"Failed to import classic_constants: {e}")
        else:
            logger.debug("Using Rust constants module")
            return classic_constants

    logger.debug("Constants module not available")
    return None


def get_version_utils() -> Any | None:
    """Retrieve the Rust-based version utilities module if available.

    This function attempts to import and return the Rust `classic_version`
    module, which provides fast version parsing, comparison, and extraction
    utilities. If the module is unavailable or Rust is disabled, returns None.

    Returns:
        Any | None: The classic_version module if available, None otherwise.

    Examples:
        >>> version = get_version_utils()
        >>> if version:
        ...     v = version.parse_version("1.10.163")
        ...     print(f"Parsed: {v}")

    """
    components = get_components()

    if not is_rust_disabled() and components.get("version_utils", False):
        try:
            import classic_version
        except ImportError as e:
            logger.warning(f"Failed to import classic_version: {e}")
        else:
            logger.debug("Using Rust version utilities module")
            return classic_version

    logger.debug("Version utilities module not available")
    return None


def get_resource_mgmt() -> Any | None:
    """Retrieve the Rust-based resource management module if available.

    This function attempts to import and return the Rust `classic_resource`
    module, which provides fast resource file detection, enumeration, and
    validation. If the module is unavailable or Rust is disabled, returns None.

    Returns:
        Any | None: The classic_resource module if available, None otherwise.

    Examples:
        >>> resource = get_resource_mgmt()
        >>> if resource:
        ...     rt = resource.detect_resource_type("texture.dds")
        ...     print(f"Type: {rt.as_str()}")

    """
    components = get_components()

    if not is_rust_disabled() and components.get("resource_mgmt", False):
        try:
            import classic_resource
        except ImportError as e:
            logger.warning(f"Failed to import classic_resource: {e}")
        else:
            logger.debug("Using Rust resource management module")
            return classic_resource

    logger.debug("Resource management module not available")
    return None


def get_xse_utils() -> Any | None:
    """Retrieve the Rust-based XSE utilities module if available.

    This function attempts to import and return the Rust `classic_xse`
    module, which provides Script Extender (XSE) detection, version checking,
    and status information for F4SE, SKSE, SFSE, and their VR variants. If the
    module is unavailable or Rust is disabled, returns None.

    Returns:
        Any | None: The classic_xse module if available, None otherwise.

    Examples:
        >>> xse = get_xse_utils()
        >>> if xse:
        ...     info = xse.get_xse_info("C:/Games/Fallout4", xse.XseType.f4se())
        ...     print(f"F4SE installed: {info.installed()}")

    """
    components = get_components()

    if not is_rust_disabled() and components.get("xse_utils", False):
        try:
            import classic_xse
        except ImportError as e:
            logger.warning(f"Failed to import classic_xse: {e}")
        else:
            logger.debug("Using Rust XSE utilities module")
            return classic_xse

    logger.debug("XSE utilities module not available")
    return None


def get_web_utils() -> Any | None:
    """Retrieve the Rust-based web utilities module if available.

    This function attempts to import and return the Rust `classic_web`
    module, which provides URL validation, user agent generation, and
    mod site constants. If the module is unavailable or Rust is disabled,
    returns None.

    Returns:
        Any | None: The classic_web module if available, None otherwise.

    Examples:
        >>> web = get_web_utils()
        >>> if web:
        ...     ua = web.get_user_agent()
        ...     print(f"User agent: {ua}")
        ...     valid = web.is_valid_url("https://www.nexusmods.com")
        ...     print(f"Valid URL: {valid}")

    """
    components = get_components()

    if not is_rust_disabled() and components.get("web_utils", False):
        try:
            import classic_web
        except ImportError as e:
            logger.warning(f"Failed to import classic_web: {e}")
        else:
            logger.debug("Using Rust web utilities module")
            return classic_web

    logger.debug("Web utilities module not available")
    return None


def get_path_operations() -> Any | None:
    """Retrieve the Rust-based path operations module if available.

    This function attempts to import and return the Rust `classic_path`
    module, which provides high-performance path validation, game path
    detection, registry queries, and XSE log parsing. If the module is
    unavailable or Rust is disabled, returns None for fallback to Python
    implementations in GamePath, DocsPath, and PathValidator modules.

    **Performance**: Rust acceleration provides 10-50x speedup for:
    - Windows registry queries for game paths
    - Path validation and existence checks
    - XSE log parsing for game detection
    - File system operations

    Returns:
        Any | None: The classic_path module if available, None otherwise.
            Calling code should check for None and use Python fallback.

    Examples:
        >>> path_ops = get_path_operations()
        >>> if path_ops:
        ...     # Use Rust acceleration
        ...     finder = path_ops.GamePathFinder(exe_name, xse_loader, game, is_vr)
        ...     path = finder.find_game_path(cached_path, xse_log_path)
        ... else:
        ...     # Use Python fallback
        ...     path = _python_find_game_path()

    """
    components = get_components()

    if not is_rust_disabled() and components.get("path_operations", False):
        try:
            import classic_path

        except ImportError as e:
            logger.warning(f"Failed to import classic_path: {e}")
        else:
            logger.debug("Using Rust path operations module (10-50x speedup)")
            return classic_path

    logger.debug("Path operations module not available, using Python fallback")
    return None
