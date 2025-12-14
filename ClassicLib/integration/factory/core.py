"""Core utilities for the factory module.

Provides shared functions for Rust component detection and caching
that are used across all factory submodules.

Functions:
    get_components: Retrieve cached Rust component availability status.
    is_rust_disabled: Check if Rust features are disabled via environment.
    reset_cache: Reset the component detection cache.
"""

from __future__ import annotations

import logging
import os

from ClassicLib.integration.config import DISABLE_RUST_ENV_VAR
from ClassicLib.integration.detector import detect_rust_components

logger = logging.getLogger(__name__)

# Cache for component availability to avoid repeated detection
_components_cache: dict[str, bool] | None = None


def get_components() -> dict[str, bool]:
    """Retrieve the status of Rust components and caches the result.

    This function checks if the Rust components have already been detected and
    cached. If not, it calls the `detect_rust_components` function to get the
    status of the available Rust components, stores the result in a global cache,
    and returns it.

    Returns:
        dict[str, bool]: A dictionary where keys represent Rust components as
        strings and values are booleans indicating the presence of those components.

    """
    global _components_cache  # noqa: PLW0603
    if _components_cache is None:
        _components_cache = detect_rust_components()
    return _components_cache


def is_rust_disabled() -> bool:
    """Determine if Rust features are disabled based on an environment variable.

    This function checks the presence and value of a specific environment
    variable to determine whether Rust features should be disabled. It is
    commonly used to conditionally enable or disable functionality.

    Returns:
        bool: True if Rust features are disabled, False otherwise.

    """
    return os.environ.get(DISABLE_RUST_ENV_VAR, "").lower() in {"1", "true", "yes"}


def reset_cache() -> None:
    """Reset the global components cache.

    This function sets the global `_components_cache` variable to `None` and logs
    a debug message indicating that the component cache has been reset.

    """
    global _components_cache  # noqa: PLW0603
    _components_cache = None
    logger.debug("Component cache reset")
