"""Type stubs for classic_yaml.

Python bindings for classic-yaml-core, providing high-performance YAML operations
using the yaml-rust2 library. This module offers 15-30x speedup over ruamel.yaml
for parsing and manipulation of YAML configuration files.

Architecture:
    - classic-yaml-core: Business logic (YAML parsing, serialization)
    - classic-yaml-py: Python bindings (this module - PyO3 adapters)

Features:
    - YAML 1.2 compliant parsing
    - Multi-document support
    - Anchor/alias resolution
    - Insertion order preservation (LinkedHashMap)
    - Pure Rust safety (no unsafe code)
    - Intelligent caching for repeated operations

Usage:
    from classic_yaml import RustYamlOperations

    # Create YAML operations handler
    yaml_ops = RustYamlOperations()

    # Load YAML file
    data = yaml_ops.load_yaml_file("config.yaml")

    # Parse YAML string
    parsed = yaml_ops.parse_yaml("key: value")

    # Save YAML file
    yaml_ops.save_yaml_file("output.yaml", {"key": "value"})
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__version__: str

class RustYamlOperations:
    """Main YAML operations handler using yaml-rust2.

    High-performance YAML parser and manipulator with comprehensive support for
    YAML 1.2 specification. Provides caching for improved performance on
    repeated operations.

    The RustYamlOperations class handles:
    - Loading and parsing YAML files
    - Converting between Python objects and YAML
    - Managing cached YAML data for settings
    - Serializing Python objects to YAML format

    All YAML operations preserve insertion order and support complex YAML features
    like anchors, aliases, and multi-document files.
    """

    def __init__(self) -> None:
        """Create a new YAML operations handler with empty cache.

        Initializes internal caching structures for improved performance on
        repeated YAML operations.
        """

    def load_yaml_file(self, path: str | Path) -> dict[str, Any]:
        """Load and parse a YAML file.

        Reads the file from disk, parses the YAML content, and returns the
        parsed data as a Python dictionary. Supports multi-document YAML files
        (returns the first document).

        Args:
            path: Path to the YAML file (string or pathlib.Path)

        Returns:
            Parsed YAML content as a dictionary with insertion order preserved

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If YAML content is malformed or invalid
            IOError: If file cannot be read

        Example:
            >>> yaml_ops = RustYamlOperations()
            >>> config = yaml_ops.load_yaml_file("config.yaml")
            >>> print(config["setting"])
            'value'
        """

    def parse_yaml(self, content: str) -> dict[str, Any]:
        """Parse YAML content from a string.

        Parses YAML text and returns the parsed data as a Python dictionary.
        Supports all YAML 1.2 features including anchors, aliases, and
        complex data structures.

        Args:
            content: YAML content as string

        Returns:
            Parsed YAML as dictionary with insertion order preserved

        Raises:
            ValueError: If YAML is malformed or invalid

        Example:
            >>> yaml_ops = RustYamlOperations()
            >>> data = yaml_ops.parse_yaml("key: value\\nlist:\\n  - item1\\n  - item2")
            >>> print(data["list"])
            ['item1', 'item2']
        """

    def dump_yaml(self, data: dict[str, Any]) -> str:
        """Convert Python dictionary to YAML string.

        Serializes a Python dictionary to YAML format with proper indentation
        and formatting. Preserves order and handles nested structures.

        Args:
            data: Python dictionary to serialize

        Returns:
            YAML formatted string

        Example:
            >>> yaml_ops = RustYamlOperations()
            >>> yaml_str = yaml_ops.dump_yaml({"key": "value", "list": [1, 2, 3]})
            >>> print(yaml_str)
            key: value
            list:
              - 1
              - 2
              - 3
        """

    def save_yaml_file(self, path: str | Path, data: dict[str, Any]) -> None:
        """Save dictionary as YAML file.

        Serializes a Python dictionary to YAML format and writes it to a file.
        Creates parent directories if they don't exist.

        Args:
            path: Destination file path (string or pathlib.Path)
            data: Dictionary to save

        Raises:
            IOError: If file cannot be written
            PermissionError: If lacking write permissions

        Example:
            >>> yaml_ops = RustYamlOperations()
            >>> yaml_ops.save_yaml_file("output.yaml", {"key": "value"})
        """

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value from cached YAML data.

        Retrieves a value from the internal YAML cache using a dot-separated
        key path. Returns the default value if the key is not found.

        Args:
            key: Setting key to retrieve (supports dot notation for nested keys)
            default: Default value if key not found (default: None)

        Returns:
            Setting value or default if not found

        Example:
            >>> yaml_ops = RustYamlOperations()
            >>> yaml_ops.parse_yaml("database:\\n  host: localhost\\n  port: 5432")
            >>> host = yaml_ops.get_setting("database.host")
            >>> print(host)
            'localhost'
        """

    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value in cached YAML data.

        Updates a value in the internal YAML cache using a dot-separated key path.
        Creates intermediate keys if they don't exist.

        Args:
            key: Setting key to set (supports dot notation for nested keys)
            value: Value to assign

        Example:
            >>> yaml_ops = RustYamlOperations()
            >>> yaml_ops.set_setting("database.host", "localhost")
            >>> yaml_ops.set_setting("database.port", 5432)
        """

    def clear_cache(self) -> None:
        """Clear the YAML cache to free memory.

        Removes all cached YAML data from memory. Useful for releasing memory
        after processing large YAML files or when cache data is no longer needed.

        Example:
            >>> yaml_ops = RustYamlOperations()
            >>> yaml_ops.load_yaml_file("large_config.yaml")
            >>> # ... use data ...
            >>> yaml_ops.clear_cache()  # Free memory
        """

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns information about the current cache state including the number
        of cached entries and estimated memory usage.

        Returns:
            Dictionary with cache statistics:
                - 'entries': Number of cached items
                - 'memory_bytes': Estimated memory usage in bytes

        Example:
            >>> yaml_ops = RustYamlOperations()
            >>> yaml_ops.load_yaml_file("config.yaml")
            >>> stats = yaml_ops.get_cache_stats()
            >>> print(f"Cached items: {stats['entries']}")
            >>> print(f"Memory used: {stats['memory_bytes']} bytes")
        """
