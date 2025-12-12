"""Type definitions for YamlSettings module.

This module provides type aliases used throughout the YAML settings system,
including types for YAML data structures and generic type variables for
type-safe settings access.

Type Aliases:
    YAMLLiteral: Basic YAML scalar types (str, int, bool).
    YAMLSequence: YAML list of strings.
    YAMLMapping: YAML dictionary with string keys.
    YAMLValue: Union of all YAML value types.
    YAMLValueOptional: YAMLValue that can be None.

Type Variables:
    T: Generic type variable for settings retrieval.

Example:
    >>> from ClassicLib.YamlSettings.types import YAMLMapping, T
    >>> def get_setting(data: YAMLMapping, key: str) -> T | None:
    ...     return data.get(key)

"""

from typing import TypeVar

# YAML type definitions
type YAMLLiteral = str | int | bool
"""Basic YAML scalar types: strings, integers, and booleans."""

type YAMLSequence = list[str]
"""YAML sequence (list) containing string elements."""

type YAMLMapping = dict[str, YAMLValue]
"""YAML mapping (dictionary) with string keys and any YAML value."""

type YAMLValue = YAMLMapping | YAMLSequence | YAMLLiteral
"""Union of all possible YAML value types."""

type YAMLValueOptional = YAMLValue | None
"""Optional YAML value that can be None."""

# Generic type for settings retrieval
T = TypeVar("T")
"""Generic type variable for type-safe settings access."""

__all__ = [
    "T",
    "YAMLLiteral",
    "YAMLMapping",
    "YAMLSequence",
    "YAMLValue",
    "YAMLValueOptional",
]
