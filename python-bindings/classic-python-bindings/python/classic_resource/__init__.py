"""Resource management for game files
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_resource import (
    ResourceInfo,
    ResourceType,
    __version__,
    count_resources_by_type,
    detect_resource_type,
    enumerate_resources,
    is_supported_resource,
    parse_resource_type,
    validate_resource,
)

__all__ = [
    "ResourceInfo",
    "ResourceType",
    "__version__",
    "count_resources_by_type",
    "detect_resource_type",
    "enumerate_resources",
    "is_supported_resource",
    "parse_resource_type",
    "validate_resource",
]
