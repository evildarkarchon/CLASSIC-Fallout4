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
    from classic_yaml import YamlOperations

    # Create YAML operations handler
    yaml_ops = YamlOperations()

    # Load YAML file
    data = yaml_ops.load_yaml_file("config.yaml")

    # Parse YAML string
    parsed = yaml_ops.parse_yaml("key: value")

    # Save YAML file
    yaml_ops.save_yaml_file("output.yaml", {"key": "value"})
"""

from pathlib import Path
from typing import Any, TypedDict

__version__: str

class YamlCacheStats(TypedDict):
    """Canonical YAML cache statistics contract."""

    hits: int
    misses: int
    hit_rate: float
    size: int
    capacity: int

class YamlOperations:
    """Main YAML operations handler using yaml-rust2.

    High-performance YAML parser and manipulator with comprehensive support for
    YAML 1.2 specification. Provides caching for improved performance on
    repeated operations.

    The YamlOperations class handles:
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
            >>> yaml_ops = YamlOperations()
            >>> config = yaml_ops.load_yaml_file("config.yaml")
            >>> print(config["setting"])
            'value'

        """

    def parse_yaml(self, content: str) -> Any:
        r"""Parse YAML content from a string.

        Parses YAML text and returns the parsed data as a Python object.
        Supports all YAML 1.2 features including anchors, aliases, and
        complex data structures.

        Args:
            content: YAML content as string

        Returns:
            Parsed YAML as Python object. Can be:
            - None (for YAML null)
            - bool (for YAML true/false)
            - int (for YAML integers)
            - float (for YAML floats)
            - str (for YAML strings)
            - list (for YAML sequences)
            - dict[str, Any] (for YAML mappings, with insertion order preserved)

        Raises:
            ValueError: If YAML is malformed or invalid

        Example:
            >>> yaml_ops = YamlOperations()
            >>> data = yaml_ops.parse_yaml("key: value\\nlist:\\n  - item1\\n  - item2")
            >>> print(data["list"])
            ['item1', 'item2']

        """

    def dump_yaml(self, data: Any) -> str:
        """Convert Python object to YAML string.

        Serializes a Python object to YAML format with proper indentation
        and formatting. Preserves order and handles nested structures.

        Args:
            data: Python object to serialize. Supported types:
                - None (becomes YAML null)
                - bool (becomes YAML true/false)
                - int (becomes YAML integer)
                - float (becomes YAML float)
                - str (becomes YAML string)
                - list (becomes YAML sequence)
                - dict (becomes YAML mapping)

        Returns:
            YAML formatted string

        Example:
            >>> yaml_ops = YamlOperations()
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
            >>> yaml_ops = YamlOperations()
            >>> yaml_ops.save_yaml_file("output.yaml", {"key": "value"})

        """

    def get_setting(self, data: dict[str, Any], key_path: str) -> Any | None:
        r"""Get a setting value from YAML data using dot notation.

        Retrieves a value from YAML data using a dot-separated key path.
        Returns None if the key path is not found.

        Args:
            data: YAML data to extract from
            key_path: Dot-separated path (e.g., "parent.child.field")

        Returns:
            Setting value or None if not found

        Example:
            >>> yaml_ops = YamlOperations()
            >>> data = yaml_ops.parse_yaml("database:\\n  host: localhost\\n  port: 5432")
            >>> host = yaml_ops.get_setting(data, "database.host")
            >>> print(host)
            'localhost'

        """

    def set_setting(
        self, data: dict[str, Any], key_path: str, value: Any
    ) -> dict[str, Any]:
        """Set a setting value in YAML data using dot notation.

        Updates a value in YAML data using a dot-separated key path.
        Creates intermediate keys if they don't exist. Returns the modified data.

        Args:
            data: YAML data to modify
            key_path: Dot-separated path (e.g., "parent.child.field")
            value: Value to assign

        Returns:
            Modified YAML data with the new value

        Raises:
            ValueError: If the key path is invalid

        Example:
            >>> yaml_ops = YamlOperations()
            >>> data = yaml_ops.parse_yaml("database: {}")
            >>> data = yaml_ops.set_setting(data, "database.host", "localhost")
            >>> data = yaml_ops.set_setting(data, "database.port", 5432)

        """

    def get_string_value(
        self, data: dict[str, Any], key_path: str, default: str
    ) -> str:
        """Extract a string value from YAML using dot notation.

        Convenience method for getting string values from nested YAML structures.
        Navigates through the YAML document using dot notation and returns the
        string value or a default if the key doesn't exist or isn't a string.

        Args:
            data: YAML data to extract from
            key_path: Dot-separated path (e.g., "parent.child.field")
            default: Default value if key not found or not a string

        Returns:
            String value or default

        Example:
            >>> yaml_ops = YamlOperations()
            >>> yaml_str = '''
            ... game:
            ...   name: Fallout4
            ...   version: "1.10.163"
            ... '''
            >>> data = yaml_ops.parse_yaml(yaml_str)
            >>> name = yaml_ops.get_string_value(data, "game.name", "Unknown")
            >>> print(name)
            'Fallout4'

        """

    def get_vec_value(self, data: dict[str, Any], key_path: str) -> list[str]:
        """Extract a vector of strings from YAML using dot notation.

        Convenience method for getting string arrays from nested YAML structures.
        Navigates through the YAML document using dot notation and returns a list
        of strings, or an empty list if the key doesn't exist or isn't an array.

        Args:
            data: YAML data to extract from
            key_path: Dot-separated path (e.g., "parent.child.array")

        Returns:
            List of strings, or empty list if key not found or not an array

        Example:
            >>> yaml_ops = YamlOperations()
            >>> yaml_str = '''
            ... game:
            ...   plugins:
            ...     - plugin1.esp
            ...     - plugin2.esp
            ...     - plugin3.esp
            ... '''
            >>> data = yaml_ops.parse_yaml(yaml_str)
            >>> plugins = yaml_ops.get_vec_value(data, "game.plugins")
            >>> print(plugins)
            ['plugin1.esp', 'plugin2.esp', 'plugin3.esp']

        """

    def get_hashmap_value(self, data: dict[str, Any], key_path: str) -> dict[str, str]:
        """Extract a hashmap from YAML using dot notation.

        Convenience method for getting string key-value maps from nested YAML structures.
        Navigates through the YAML document using dot notation and returns a dict,
        or an empty dict if the key doesn't exist or isn't a hash.

        Args:
            data: YAML data to extract from
            key_path: Dot-separated path (e.g., "parent.child.map")

        Returns:
            Dictionary of string key-value pairs, or empty dict if key not found or not a hash

        Example:
            >>> yaml_ops = YamlOperations()
            >>> yaml_str = '''
            ... game:
            ...   mods:
            ...     mod1: "Description 1"
            ...     mod2: "Description 2"
            ... '''
            >>> data = yaml_ops.parse_yaml(yaml_str)
            >>> mods = yaml_ops.get_hashmap_value(data, "game.mods")
            >>> print(mods)
            {'mod1': 'Description 1', 'mod2': 'Description 2'}

        """

    def clear_cache(self) -> None:
        """Clear the YAML cache to free memory.

        Removes all cached YAML data from memory. Useful for releasing memory
        after processing large YAML files or when cache data is no longer needed.

        Example:
            >>> yaml_ops = YamlOperations()
            >>> yaml_ops.load_yaml_file("large_config.yaml")
            >>> # ... use data ...
            >>> yaml_ops.clear_cache()  # Free memory

        """

    def get_cache_stats(self) -> YamlCacheStats:
        """Get cache statistics.

        Returns the canonical Phase 4 cache statistics contract.

        Returns:
            Dictionary with cache statistics:
                - 'hits': Number of cache hits
                - 'misses': Number of cache misses
                - 'hit_rate': Hit ratio as a float from 0.0 to 1.0
                - 'size': Current number of cached entries
                - 'capacity': Maximum retained cache entries

        Example:
            >>> yaml_ops = YamlOperations()
            >>> yaml_ops.load_yaml_file("config.yaml")
            >>> stats = yaml_ops.get_cache_stats()
            >>> print(f"Cache hits: {stats['hits']}")
            >>> print(f"Capacity: {stats['capacity']}")

        """
