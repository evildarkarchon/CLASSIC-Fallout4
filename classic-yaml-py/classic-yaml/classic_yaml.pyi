"""Type stubs for classic_yaml Rust extension module.

This module provides high-performance YAML operations using yaml-rust2:
- 15-30x speedup for YAML parsing
- 10-20x speedup for YAML writing
- YAML 1.2 compliant (via yaml-rust2)
- Pure Rust implementation (no unsafe FFI)
- Multi-document support
- Anchor/alias resolution
"""

from __future__ import annotations

from typing import Any, Optional

__version__: str

class RustYamlOperations:
    """High-performance YAML operations (15-30x parsing, 10-20x writing).

    Uses yaml-rust2 v0.10.4 for YAML 1.2 compliant parsing with:
    - Owned types (no lifetime parameters)
    - Insertion order preservation
    - Anchor and alias resolution
    - Multi-document support
    """

    def __init__(self) -> None:
        """Create YAML operations instance."""
        ...

    def parse_yaml(self, yaml_str: str) -> Any:
        """Parse YAML string to Python objects.

        Converts YAML to Python using standard mappings:
        - YAML mapping → Python dict
        - YAML sequence → Python list
        - YAML scalar → Python str/int/float/bool/None

        Args:
            yaml_str: YAML content as string

        Returns:
            Parsed YAML data as Python objects

        Raises:
            ValueError: If YAML is invalid or malformed
        """
        ...

    def parse_yaml_file(self, path: str) -> Any:
        """Parse YAML file to Python objects.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML data

        Raises:
            IOError: If file cannot be read
            ValueError: If YAML is invalid
        """
        ...

    def parse_yaml_multi(self, yaml_str: str) -> list[Any]:
        """Parse multi-document YAML string.

        Args:
            yaml_str: YAML content with multiple documents (separated by ---)

        Returns:
            List of parsed YAML documents

        Raises:
            ValueError: If YAML is invalid
        """
        ...

    def dump_yaml(self, data: Any) -> str:
        """Convert Python objects to YAML string.

        Args:
            data: Python data to serialize (dict, list, primitives)

        Returns:
            YAML string representation

        Raises:
            ValueError: If data cannot be serialized to YAML
        """
        ...

    def dump_yaml_file(self, path: str, data: Any) -> None:
        """Write Python objects to YAML file.

        Args:
            path: Output file path
            data: Python data to serialize

        Raises:
            IOError: If file cannot be written
            ValueError: If data cannot be serialized
        """
        ...

    def dump_yaml_multi(self, documents: list[Any]) -> str:
        """Convert multiple Python objects to multi-document YAML.

        Args:
            documents: List of Python objects to serialize

        Returns:
            Multi-document YAML string (documents separated by ---)
        """
        ...

    def get_value(self, data: Any, key: str) -> Optional[Any]:
        """Get value by dot-separated key path.

        Supports nested access using dot notation:
        - "key" → data["key"]
        - "outer.inner" → data["outer"]["inner"]
        - "list.0" → data["list"][0]

        Args:
            data: Parsed YAML data (dict or nested structure)
            key: Dot-separated key path (e.g., "section.subsection.key")

        Returns:
            Value at key path, or None if not found
        """
        ...

    def set_value(self, data: Any, key: str, value: Any) -> Any:
        """Set value by dot-separated key path.

        Creates intermediate dictionaries as needed.

        Args:
            data: Parsed YAML data to modify
            key: Dot-separated key path
            value: Value to set

        Returns:
            Modified data structure
        """
        ...

    def merge_yaml(self, base: Any, overlay: Any) -> Any:
        """Merge two YAML structures.

        Performs deep merge where overlay values override base values.

        Args:
            base: Base YAML data
            overlay: Overlay YAML data

        Returns:
            Merged YAML data
        """
        ...

    def validate_yaml(self, yaml_str: str) -> tuple[bool, Optional[str]]:
        """Validate YAML syntax without parsing.

        Args:
            yaml_str: YAML string to validate

        Returns:
            Tuple of (is_valid, error_message)
            where error_message is None if valid
        """
        ...
