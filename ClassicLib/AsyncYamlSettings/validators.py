"""Validation utilities for AsyncYamlSettings."""

from typing import Any, get_origin

from ClassicLib.Constants import SETTINGS_IGNORE_NONE
from ClassicLib.Logger import logger


def validate_settings_structure(data: dict[str, Any], store_type: str) -> None:
    """
    Validate the structure of loaded settings.

    Ensures required keys exist and have valid values.

    Args:
        data: The loaded YAML data
        store_type: Type of store (e.g., "Settings", "Game")
    """
    if not isinstance(data, dict):
        raise ValueError(f"Invalid {store_type} structure: expected dict, got {type(data)}")

    # Store-specific validation
    if store_type == "Settings" and "CLASSIC_Settings" not in data:
        # Settings file must have CLASSIC_Settings root
        raise ValueError("Settings file missing 'CLASSIC_Settings' root key")

    # Check for completely empty files
    if not data:
        logger.warning(f"{store_type} file is empty")


def validate_setting_value(value: Any, expected_type: type) -> bool:
    """
    Validate that a setting value matches the expected type.

    Args:
        value: The value to validate
        expected_type: The expected type

    Returns:
        True if valid, False otherwise
    """
    # None is valid if allowed by settings
    if value is None:
        return not SETTINGS_IGNORE_NONE

    # Handle parameterized generics (e.g., list[str], dict[str, Any])
    origin_type = get_origin(expected_type)
    if origin_type is not None:
        # For generic types, check against the origin (e.g., list for list[str])
        if isinstance(value, origin_type):
            return True
    # Direct type match for non-generic types
    elif isinstance(value, expected_type):
        return True

    # Special case for Path
    if expected_type.__name__ == "Path":
        return isinstance(value, str)

    # Type conversion possible
    try:
        if expected_type in (int, float, str, bool):
            expected_type(value)
            return True
    except (ValueError, TypeError):
        pass

    return False


def coerce_setting_value(value: Any, expected_type: type) -> Any:
    """
    Attempt to coerce a value to the expected type.

    Args:
        value: The value to coerce
        expected_type: The target type

    Returns:
        Coerced value or original if coercion fails
    """
    # Handle parameterized generics
    origin_type = get_origin(expected_type)
    check_type = origin_type if origin_type is not None else expected_type

    if value is None or isinstance(value, check_type):
        return value

    try:
        # Special handling for Path
        if expected_type.__name__ == "Path":
            from pathlib import Path
            return Path(value) if value else None

        # Basic type coercion
        if expected_type in (int, float, str, bool):
            return expected_type(value)

        # List/dict handling
        if expected_type == list and not isinstance(value, list):
            return [value]

        if expected_type == dict and not isinstance(value, dict):
            return {}

    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to coerce {value} to {expected_type}: {e}")

    return value
