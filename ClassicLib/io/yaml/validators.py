"""Validation and coercion utilities for YAML settings.

This module provides functions to validate and coerce settings values,
ensuring they have the correct structure and types for the YAML settings
system.

Functions:
    validate_settings_structure: Validates the overall structure of settings data.
    validate_setting_value: Checks if a value matches an expected type.
    coerce_setting_value: Attempts to convert a value to the expected type.

Example:
    >>> from ClassicLib.YamlSettings.validators import validate_setting_value
    >>> validate_setting_value(42, int)
    True
    >>> validate_setting_value("42", int)
    True  # Can be coerced
    >>> validate_setting_value("hello", int)
    False

"""

from typing import Any, get_origin

from ClassicLib.core.constants import SETTINGS_IGNORE_NONE
from ClassicLib.core.logger import logger


def validate_settings_structure(data: dict[str, Any], store_type: str) -> None:
    """Validate the structure of a settings data object.

    Ensures the settings data conforms to specific requirements based on
    the store type. Raises an exception if the structure is invalid.
    Logs a warning if the data is empty.

    Args:
        data: The settings data object to validate. Must be a dictionary.
        store_type: A string indicating the type of store being validated
            (e.g., "Settings", "Main", "Game").

    Raises:
        TypeError: If the data is not a dictionary.
        ValueError: If specific structural requirements are not met based
            on the store type (e.g., Settings file missing 'CLASSIC_Settings'
            root key).

    Example:
        >>> data = {"CLASSIC_Settings": {"VR Mode": False}}
        >>> validate_settings_structure(data, "Settings")  # OK
        >>> validate_settings_structure({}, "Settings")
        ValueError: Settings file missing 'CLASSIC_Settings' root key

    """
    if not isinstance(data, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"Invalid {store_type} structure: expected dict, got {type(data)}")

    # Store-specific validation
    if store_type == "Settings" and "CLASSIC_Settings" not in data:
        # Settings file must have CLASSIC_Settings root
        raise ValueError("Settings file missing 'CLASSIC_Settings' root key")

    # Check for completely empty files
    if not data:
        logger.warning(f"{store_type} file is empty")


# noinspection PyTypeChecker
def validate_setting_value(value: Any, expected_type: type) -> bool:
    """Validate if a value matches the expected type.

    Checks for direct type matches, compatibility with generic types
    (e.g., list[str]), special cases like Path, and performs type
    conversion if applicable. A global setting may allow None as a
    valid value.

    Args:
        value: The value to validate.
        expected_type: The expected type or type hint to validate against.
            Can be a simple type (int, str, bool) or a parameterized
            generic (list[str], dict[str, Any]).

    Returns:
        True if the value matches the expected type or can be successfully
        converted; False otherwise.

    Example:
        >>> validate_setting_value(42, int)
        True
        >>> validate_setting_value("hello", str)
        True
        >>> validate_setting_value([1, 2, 3], list)
        True
        >>> validate_setting_value("hello", int)
        True  # Can be converted
        >>> validate_setting_value([1, 2], int)
        False

    """
    # None is valid if allowed by settings
    if value is None:
        return not SETTINGS_IGNORE_NONE

    # Handle parameterized generics (e.g., list[str], dict[str, Any])
    origin_type = get_origin(expected_type)
    if origin_type is not None:
        if not isinstance(value, origin_type):
            pass  # Type mismatch, continue to other checks below
        else:
            # For generic types, check against the origin (e.g., list for list[str])
            return True
    # Direct type match for non-generic types
    elif isinstance(value, expected_type):
        return True

    # Special case for Path
    if expected_type.__name__ == "Path":
        return isinstance(value, str)

    # Type conversion possible
    try:
        if expected_type in {int, float, str, bool}:
            expected_type(value)
            return True
    except (ValueError, TypeError):
        pass  # Coercion failed

    return False


# noinspection PyTypeChecker
def coerce_setting_value(value: Any, expected_type: type) -> Any:
    """Attempt to coerce a value to the expected type.

    Handles basic type coercions, handling for parameterized generics,
    and special cases like paths and collections.

    Args:
        value: The value to coerce to the expected type.
        expected_type: The type to which the value should be coerced.
            Can be a simple type (int, str, bool, Path) or a collection
            type (list, dict).

    Returns:
        The coerced value if conversion is possible, or the original
        value if coercion is not possible.

    Example:
        >>> coerce_setting_value("42", int)
        42
        >>> coerce_setting_value(42, str)
        "42"
        >>> coerce_setting_value("path/to/file", Path)
        Path("path/to/file")
        >>> coerce_setting_value("item", list)
        ["item"]

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
        if expected_type in {int, float, str, bool}:
            return expected_type(value)

        # List/dict handling
        if expected_type is list and not isinstance(value, list):
            return [value]

        if expected_type is dict and not isinstance(value, dict):
            return {}

    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to coerce {value} to {expected_type}: {e}")

    return value  # pyright: ignore[reportUnknownVariableType]


__all__ = [
    "coerce_setting_value",
    "validate_setting_value",
    "validate_settings_structure",
]
