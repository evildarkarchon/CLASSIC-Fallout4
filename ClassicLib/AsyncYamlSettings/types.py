"""Type definitions for AsyncYamlSettings module."""

from typing import TypeVar

# YAML type definitions
type YAMLLiteral = str | int | bool
type YAMLSequence = list[str]
type YAMLMapping = dict[str, "YAMLValue"]
type YAMLValue = YAMLMapping | YAMLSequence | YAMLLiteral
type YAMLValueOptional = YAMLValue | None

# Generic type for settings
T = TypeVar("T")

__all__ = [
    "YAMLLiteral",
    "YAMLSequence",
    "YAMLMapping",
    "YAMLValue",
    "YAMLValueOptional",
    "T",
]
