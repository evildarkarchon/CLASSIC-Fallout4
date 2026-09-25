"""Python registry value methods use direct core methods rather than shared carriers."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .version_registry import _complete

METHODS = ("get_compatible_crashgens", "is_compatible_with")


def _values(value: Mapping[str, Any]) -> bool:
    """Require inclusive bounds, native compatibility decisions and object identity behavior."""
    if not _complete(value) or value["error"] is not None:
        return False
    result = value["result"]
    return (
        isinstance(result, Mapping)
        and set(result)
        == {
            "range",
            "contains",
            "versionCompatible",
            "crashgenCompatible",
            "compatibleCrashgens",
            "defaultCrashgens",
            "versions",
            "selected",
            "missing",
            "equalClone",
            "differentId",
            "hashClone",
        }
        and (
            isinstance(result["range"], list)
            and len(result["range"]) == 2
            and all(isinstance(item, str) for item in result["range"])
            and all(
                isinstance(result[key], list)
                and all(type(item) is bool for item in result[key])
                for key in ("contains", "versionCompatible", "crashgenCompatible")
            )
            and len(result["contains"])
            == len(result["versionCompatible"])
            == len(result["crashgenCompatible"])
            and isinstance(result["compatibleCrashgens"], list)
            and all(
                isinstance(items, list) and all(isinstance(item, str) for item in items)
                for items in result["compatibleCrashgens"]
            )
            and all(
                isinstance(result[key], list)
                and all(isinstance(item, str) for item in result[key])
                for key in ("defaultCrashgens", "versions")
            )
            and isinstance(result["selected"], str)
            and result["missing"] is None
            and all(
                type(result[key]) is bool
                for key in ("equalClone", "differentId", "hashClone")
            )
        )
    )


VERSION_REGISTRY_VALUES_COVERAGE_POLICY = FamilyCoveragePolicy(
    "version-registry-values",
    (
        CoveragePredicate(
            id="version-registry-values.observed",
            capability_id="version-registry-values.execute",
            action="version-registry-values.execute",
            observation_family="values",
            rust_symbols=("CompatibleRange", *METHODS),
            matches=_values,
            runtime_operations=(
                None,
                "contains",
                "VersionInfo.get_compatible_crashgens",
                "VersionInfo.is_compatible_with",
                "CrashgenConfig.is_compatible_with",
            ),
        ),
        CoveragePredicate(
            id="version-registry-values.identity",
            capability_id="version-registry-values.execute",
            action="version-registry-values.execute",
            observation_family="values",
            rust_symbols=("VersionInfo",),
            matches=_values,
            runtime_operations=("__eq__", "__hash__"),
        ),
    ),
)
