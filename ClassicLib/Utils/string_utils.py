"""String manipulation and text processing utilities."""

from pathlib import Path


def normalize_list(items: list[str]) -> list[str]:
    """
    Convert all string items in a list to lowercase.

    This function takes a list of strings and returns a new list with all strings
    converted to lowercase, useful for case-insensitive comparisons.

    Args:
        items: List of strings to normalize

    Returns:
        New list with all strings in lowercase
    """
    return [item.lower() for item in items]


def append_or_extend(value: str | int | float | list | tuple | set, destination: list[str]) -> None:
    """
    Intelligently add value(s) to a destination list as strings.

    Args:
        value: Single value or collection to add
        destination: List to append/extend with string values

    Returns:
        None (modifies destination in place)
    """
    if value is None:
        return

    if isinstance(value, (list, tuple, set)):
        # Convert all items to strings and extend
        destination.extend(str(item) for item in value)
    else:
        # Convert single value to string and append
        destination.append(str(value))
