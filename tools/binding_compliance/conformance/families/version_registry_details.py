"""Additional registry queries exported by Node and Python, with narrow operation credit."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .version_registry import _complete

SYMBOLS = (
    "VersionRegistry",
    "get_by_version",
    "get_by_short_name",
    "get_correct_versions",
    "get_wrong_versions",
    "get_address_library_filename",
    "get_crashgen_version_strings",
    "unknown_version_handling",
    "UnknownVersionHandling",
)
OPERATIONS = (
    None,
    "__init__",
    "get_by_version",
    "getVersionByVersionString",
    "get_by_short_name",
    "getVersionByShortName",
    "get_correct_versions",
    "getCorrectVersions",
    "get_wrong_versions",
    "getWrongVersions",
    "get_address_library_filename",
    "getAddressLibraryFilename",
    "get_crashgen_versions",
    "getCrashgenVersionStrings",
    "get_crashgen_version_strings",
    "VersionInfo.get_crashgen_version_strings",
    "get_all_exe_hashes",
    "getAllExeHashes",
    "get_all_script_hashes",
    "getAllScriptHashes",
    "get_script_hashes_for_version",
    "getScriptHashesForVersion",
    "getUnknownVersionHandling",
    "getUnknownVersionDefault",
    "get_default",
    "getVersionRegistry",
    "isVersionCompatible",
    "is_compatible_with",
)


def _details(value: Mapping[str, Any]) -> bool:
    """Require every result and file effect; a partial query cannot prove the group."""
    if not _complete(value) or value["error"] is not None:
        return False
    result = value["result"]
    if not isinstance(result, Mapping) or set(result) != {
        "byVersion",
        "byShortName",
        "correctIds",
        "wrongIds",
        "addressLibrary",
        "crashgenVersions",
        "exeHashes",
        "scriptHashes",
        "versionScriptHashes",
        "strategy",
        "logLevel",
        "defaultId",
        "compatible",
        "snapshotIds",
    }:
        return False
    return (
        all(
            result[key] is None or isinstance(result[key], str)
            for key in ("byVersion", "byShortName", "addressLibrary", "defaultId")
        )
        and all(
            isinstance(result[key], list)
            and all(isinstance(item, str) for item in result[key])
            for key in (
                "correctIds",
                "wrongIds",
                "crashgenVersions",
                "exeHashes",
                "snapshotIds",
            )
        )
        and type(result["compatible"]) is bool
        and result["strategy"] in {"nearest_match", "strict", "default_only"}
        and result["logLevel"] in {"debug", "warning", "error"}
        and isinstance(result["scriptHashes"], dict)
        and all(
            isinstance(key, str)
            and isinstance(items, list)
            and all(isinstance(item, str) for item in items)
            for key, items in result["scriptHashes"].items()
        )
        and isinstance(result["versionScriptHashes"], dict)
        and all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in result["versionScriptHashes"].items()
        )
    )


def _invalid(value: Mapping[str, Any]) -> bool:
    """Preserve a native parse failure independently of successful empty queries."""
    return (
        _complete(value)
        and value["result"] is None
        and value["error"] == {"code": "invalid_version"}
    )


VERSION_REGISTRY_DETAILS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "version-registry-details",
    (
        CoveragePredicate(
            id="version-registry-details.observed",
            capability_id="version-registry-details.execute",
            action="version-registry-details.execute",
            observation_family="values",
            rust_symbols=SYMBOLS,
            matches=_details,
            runtime_operations=OPERATIONS,
        ),
        CoveragePredicate(
            id="version-registry-details.invalid",
            capability_id="version-registry-details.execute",
            action="version-registry-details.execute",
            observation_family="errors",
            rust_symbols=SYMBOLS,
            matches=_invalid,
            runtime_operations=("get_by_version", "getVersionByVersionString"),
        ),
    ),
)
