"""Type stubs for classic_resource.

Python bindings for classic-resource-core, providing comprehensive resource handling
for Bethesda game files, including file type detection, resource enumeration, and validation.

Architecture:
    - classic-resource-core: Business logic (resource detection, enumeration)
    - classic-resource-py: Python bindings (this module - PyO3 adapters)

Features:
    - File type detection for game resources
    - Recursive resource enumeration
    - Resource validation and existence checking
    - Type-safe resource categories

Usage:
    import classic_resource
    from pathlib import Path

    # Detect resource type
    rt = classic_resource.detect_resource_type("textures/armor.dds")
    print(rt.as_str())  # "texture"

    # Enumerate resources
    resources = classic_resource.enumerate_resources("Data")
    for res in resources:
        print(f"{res.path()}: {res.resource_type().as_str()}")

    # Filter by type
    textures = classic_resource.enumerate_resources(
        "Data",
        classic_resource.ResourceType.texture()
    )
"""

from __future__ import annotations

__version__: str

class ResourceType:
    """Resource type enumeration for game files.

    Each variant corresponds to a specific type of game resource
    (textures, meshes, scripts, etc.).
    """

    @staticmethod
    def texture() -> ResourceType:
        """Create a Texture resource type."""

    @staticmethod
    def mesh() -> ResourceType:
        """Create a Mesh resource type."""

    @staticmethod
    def script() -> ResourceType:
        """Create a Script resource type."""

    @staticmethod
    def plugin() -> ResourceType:
        """Create a Plugin resource type."""

    @staticmethod
    def sound() -> ResourceType:
        """Create a Sound resource type."""

    @staticmethod
    def animation() -> ResourceType:
        """Create an Animation resource type."""

    @staticmethod
    def interface() -> ResourceType:
        """Create an Interface resource type."""

    @staticmethod
    def strings() -> ResourceType:
        """Create a Strings resource type."""

    @staticmethod
    def archive() -> ResourceType:
        """Create an Archive resource type."""

    @staticmethod
    def config() -> ResourceType:
        """Create a Config resource type."""

    @staticmethod
    def other() -> ResourceType:
        """Create an Other resource type."""

    def as_str(self) -> str:
        """Get the resource type name as a string."""

    def extensions(self) -> list[str]:
        """Get all file extensions for this resource type."""

    def __eq__(self, other: object) -> bool:
        """Compare resource types for equality."""

    def __repr__(self) -> str:
        """Return the debug representation of this ResourceType.

        Returns:
            A string representation suitable for debugging.

        """

    def __str__(self) -> str:
        """Return the string representation of this ResourceType.

        Returns:
            The resource type name as a string.

        """

class ResourceInfo:
    """Resource file information.

    Contains metadata about a game resource file including its path,
    detected type, and size.
    """

    def __init__(self, path: str) -> None:
        """Create a new ResourceInfo from a path."""

    def path(self) -> str:
        """Get the resource path."""

    def resource_type(self) -> ResourceType:
        """Get the detected resource type."""

    def size(self) -> int:
        """Get the file size in bytes."""

    def __repr__(self) -> str:
        """Return the debug representation of this ResourceInfo.

        Returns:
            A string representation suitable for debugging.

        """

    def __str__(self) -> str:
        """Return the string representation of this ResourceInfo.

        Returns:
            A formatted string with path, type, and size.

        """

def detect_resource_type(path: str) -> ResourceType:
    """Detect the resource type from a file path.

    Args:
        path: The file path to examine.

    Returns:
        The detected ResourceType.

    Example:
        >>> rt = detect_resource_type("textures/armor.dds")
        >>> assert rt.as_str() == "texture"

    """

def is_supported_resource(path: str) -> bool:
    """Check if a file is a supported resource type.

    Args:
        path: The file path to check.

    Returns:
        True if the file is a recognized resource type.

    Example:
        >>> assert is_supported_resource("texture.dds")
        >>> assert not is_supported_resource("readme.txt")

    """

def parse_resource_type(type_name: str) -> ResourceType:
    """Parse a resource type from a string.

    Args:
        type_name: The resource type name (case-insensitive).

    Returns:
        The corresponding ResourceType.

    Example:
        >>> rt = parse_resource_type("texture")
        >>> assert rt.as_str() == "texture"

    """

def enumerate_resources(root: str, filter_type: ResourceType | None = None) -> list[ResourceInfo]:
    """Enumerate resources in a directory.

    Recursively walks the directory tree and collects information about
    all supported resource files.

    Args:
        root: The root directory to scan.
        filter_type: Optional resource type filter (use None for all types).

    Returns:
        A list of ResourceInfo objects for all found resources.

    Raises:
        IOError: If directory traversal fails.

    Example:
        >>> resources = enumerate_resources("Data")
        >>> print(f"Found {len(resources)} resources")

    """

def count_resources_by_type(root: str) -> list[tuple[ResourceType, int]]:
    """Count resources in a directory by type.

    Args:
        root: The root directory to scan.

    Returns:
        A list of tuples containing (ResourceType, count).

    Raises:
        IOError: If directory traversal fails.

    Example:
        >>> counts = count_resources_by_type("Data")
        >>> for resource_type, count in counts:
        ...     print(f"{resource_type.as_str()}: {count} files")

    """

def validate_resource(path: str) -> None:
    """Check if a resource file exists and is readable.

    Args:
        path: The resource path to validate.

    Raises:
        IOError: If the file doesn't exist or cannot be accessed.
        ValueError: If the path is not a file.

    Example:
        >>> try:
        ...     validate_resource("texture.dds")
        ...     print("Resource is valid")
        ... except IOError as e:
        ...     print(f"Validation failed: {e}")

    """
