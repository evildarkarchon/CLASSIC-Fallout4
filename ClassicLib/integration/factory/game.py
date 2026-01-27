"""Game-related factory functions.

Provides factory functions for game configuration and mode handling,
selecting between Rust and Python implementations.

Functions:
    get_yamldata: Load YAML data with Rust acceleration if available.
    get_fcx_handler: Retrieve the FCX mode handler implementation.
"""

from __future__ import annotations

import logging
from typing import Any

from ClassicLib.integration.factory.core import get_components, is_rust_disabled

logger = logging.getLogger(__name__)


def get_yamldata() -> Any:
    """Load YAML data depending on available components and configurations.

    This function attempts to load YAML data using a Rust-based library for faster
    performance if the component is available and Rust is enabled. If Rust is not
    available, it falls back to a Python-based implementation.

    Returns:
        Any: An instance of the YAML data handler, either Rust or Python-based,
        depending on availability.

    """
    components = get_components()

    if not is_rust_disabled() and components.get("yamldata", False):
        try:
            from classic_config import YamlData

            from ClassicLib.core.registry import get_game, get_vr
            from ClassicLib.support.resources import ResourceLoader

            logger.debug("Using Rust YamlData (15-30x faster YAML loading)")

            # Get YAML directories from ResourceLoader
            data_dir = ResourceLoader.get_data_directory()
            # Rust YamlData now accepts [root, data] as a cleaner API
            # root: contains CLASSIC Ignore.yaml
            # data: contains databases/CLASSIC Main.yaml and databases/CLASSIC Fallout4.yaml
            yaml_dirs = [
                str(data_dir.parent),  # Root directory
                str(data_dir),  # CLASSIC Data directory
            ]

            # Get game and VR mode from registry
            game = get_game()
            vr_mode = get_vr() == "VR"

            return YamlData(yaml_dirs=yaml_dirs, game=game, vr_mode=vr_mode)
        except (ImportError, AttributeError, TypeError, ValueError, OSError) as e:
            logger.warning(f"Failed to initialize Rust YamlData: {e}")

    # Fall back to Python implementation
    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo

    logger.debug("Using Python ClassicScanLogsInfo implementation")
    return ClassicScanLogsInfo()


def get_fcx_handler(fcx_mode: bool | None) -> Any:
    """Determine and return the appropriate FCXModeHandler.

    The function utilizes a Rust-accelerated implementation if available
    (`RUST_AVAILABLE`), otherwise falls back to the Python implementation.
    This provides flexibility and optimized performance where possible.

    Args:
        fcx_mode: Determines the specific mode for the FCXModeHandler.
            Can be `True`, `False`, or `None` to represent different behavior.

    Returns:
        Any: An instance of the appropriate FCXModeHandler (either Python or
        Rust-based).

    """
    # Use wrapper that handles Rust/Python automatically
    from ClassicLib.integration.rust.fcx_rust import RUST_AVAILABLE, FCXModeHandler

    if RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated FcxModeHandler")
    else:
        logger.debug("Using Python FCXModeHandler implementation")

    return FCXModeHandler(fcx_mode)
