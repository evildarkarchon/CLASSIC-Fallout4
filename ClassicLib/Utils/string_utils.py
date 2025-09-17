"""String manipulation and text processing utilities."""


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
    Appends or extends a destination list with the string representation of a given value.

    This function modifies the given destination list by either appending the string
    representation of a single value or extending the list with the string
    representation of all elements in a given iterable value.

    Args:
        value: A value to be added to the destination list. It can be a single
            string, integer, float, or an iterable (list, tuple, set) containing
            such elements. If None is passed, the function does nothing.
        destination: The list to which the string representation of the value is
            appended or extended. Each value is converted into a string before
            being added to the list.
    """
    if value is None:
        return

    if isinstance(value, (list, tuple, set)):
        # Convert all items to strings and extend
        destination.extend(str(item) for item in value)
    else:
        # Convert single value to string and append
        destination.append(str(value))
