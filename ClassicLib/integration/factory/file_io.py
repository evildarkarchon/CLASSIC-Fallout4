"""File I/O factory functions.

Provides factory functions for file I/O and YAML operations,
selecting between Rust and Python implementations.

Functions:
    get_file_io: Retrieve the best available file I/O implementation.
    get_yaml_operations: Retrieve the Rust YAML operations if available.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from ClassicLib.integration.factory.core import get_components, is_rust_disabled

logger = logging.getLogger(__name__)

# Cache for FileIO singleton
_file_io_instance: Any = None
_file_io_lock = threading.Lock()


def get_file_io(encoding: str = "utf-8", errors: str = "ignore") -> Any:
    """Retrieve or initialize a global file I/O instance.

    Uses the specified encoding and error handling mode. Follows a thread-safe
    singleton pattern to ensure only one instance is created and efficiently
    reused. Attempts to use Rust-based implementation for improved performance,
    falling back to Python-based implementation if unavailable.

    Args:
        encoding: The text encoding format to be used for file operations.
            Defaults to "utf-8".
        errors: Specifies the error handling mode for encoding/decoding
            operations. Defaults to "ignore".

    Returns:
        Any: A singleton instance of the file I/O implementation that best fits
        the system's configuration.

    Raises:
        ImportError: If the Rust-based file I/O implementation fails to load,
        though the Python implementation is used as a fallback.

    """
    global _file_io_instance  # noqa: PLW0603

    # Fast path - instance already exists
    if _file_io_instance is not None:
        return _file_io_instance

    # Slow path - need to create instance
    with _file_io_lock:
        # Double-check pattern
        if _file_io_instance is not None:
            return _file_io_instance

        components = get_components()

        if not is_rust_disabled() and components.get("file_io_core", False):
            try:
                from ClassicLib.integration.rust.file_io_rust import FileIOCore

                logger.debug("Using Rust FileIOCore (10-20x file ops, 30-40x DDS processing)")
                _file_io_instance = FileIOCore(encoding, errors)
            except ImportError as e:
                logger.warning(f"Failed to import Rust FileIOCore: {e}")
            else:
                return _file_io_instance

        # Fall back to Python implementation
        from ClassicLib.integration.python.file_io_py import FileIOCore

        logger.debug("Using Python FileIOCore implementation")
        _file_io_instance = FileIOCore(encoding, errors)
        return _file_io_instance


def get_yaml_operations() -> Any:
    """Retrieve the appropriate YAML operations implementation.

    This function determines whether to use a Rust-based YAML operations
    implementation for enhanced performance or to fall back to a Python-based
    implementation. If Rust-based operations are available and not disabled,
    they are utilized; otherwise, the Python implementation serves as the
    default.

    Returns:
        Any: An instance of the Rust-based YAML operations class if available
        and enabled, or None if Python implementation is used or if no
        acceleration is available.

    """
    components = get_components()

    if not is_rust_disabled() and components.get("yaml_operations", False):
        try:
            import classic_yaml

            if hasattr(classic_yaml, "YamlOperations"):
                logger.debug("Using Rust YAML Operations (15-30x parsing, 10-20x writing speedup)")
                return classic_yaml.YamlOperations()
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to get Rust YAML Operations: {e}")

    # Fall back to Python implementation - return None to indicate no acceleration available
    logger.debug("Using Python YAML implementation (ruamel.yaml)")
    return None
