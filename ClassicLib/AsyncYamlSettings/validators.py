"""
A utility for validating and coercing settings data structures.

Provides functions to ensure settings have the correct structure and types,
validate values against expected types, and coerce values to the required
types where possible. Includes logging and handling of specific cases such
as generic types and special types like Path.
"""

from typing import Any, get_origin

from ClassicLib.Constants import SETTINGS_IGNORE_NONE
from ClassicLib.Logger import logger


def validate_settings_structure(data: dict[str, Any], store_type: str) -> None:
    """
    Validates the structure of a given settings data object, ensuring it conforms to specific
    requirements based on the store type. Raises an exception if the structure is invalid.
    Logs a warning if the data is empty.

    Args:
        data (dict[str, Any]): The settings data object to validate.
        store_type (str): A string indicating the type of store (e.g., "Settings") being validated.

    Raises:
        TypeError: If the data is not a dictionary.
        ValueError: If specific structural requirements are not met based on the store type.
    """
    if not isinstance(data, dict):
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
    """
    Validates if a given value matches the expected type, with support for handling
    parameterized generic types and type conversions. This function checks for direct
    type matches, compatibility with generic types (e.g., list[str]), special cases
    like Path, and performs type conversion if applicable. A global setting may allow
    `None` as a valid value.

    Args:
        value: The value to validate.
        expected_type: The expected type or type hint to validate against.

    Returns:
        bool: True if the value matches the expected type or can be successfully
              converted; False otherwise.
    """
    # None is valid if allowed by settings
    if value is None:
        return not SETTINGS_IGNORE_NONE

    # Handle parameterized generics (e.g., list[str], dict[str, Any])
    origin_type = get_origin(expected_type)
    if origin_type is not None:
        if not isinstance(value, origin_type):
            pass
        # For generic types, check against the origin (e.g., list for list[str])
        else:
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
        pass

    return False


# noinspection PyTypeChecker
def coerce_setting_value(value: Any, expected_type: type) -> Any:
    """
    Attempts to coerce a given value to the expected type. Handles basic type
    coercions, handling for parameterized generics, and special cases like
    paths and collections.

    Args:
        value: The value to coerce to the expected type.
        expected_type: The type to which the value should be coerced.

    Returns:
        The coerced value, or the original value if coercion is not possible.
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

    return value
