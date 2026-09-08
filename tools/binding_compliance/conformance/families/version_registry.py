"""Narrow Version Registry metadata and matching facts over public observations."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _complete(observation: Mapping[str, Any]) -> bool:
    """Require both success and failure carriers, including explicit absence."""
    return (
        set(observation) == {"result", "error", "files"}
        and isinstance(observation["files"], list)
        and len(observation["files"]) == 1
        and isinstance(observation["files"][0], Mapping)
        and set(observation["files"][0]) == {"path", "content"}
        and observation["files"][0]["path"] == "CLASSIC Main.yaml"
        and isinstance(observation["files"][0]["content"], str)
        and bool(observation["files"][0]["content"])
    )


def _lookup(found: bool, observation: Mapping[str, Any]) -> bool:
    """Recognize all shared metadata fields or an explicit missing lookup."""
    if not _complete(observation) or observation["error"] is not None:
        return False
    result = observation["result"]
    if not found:
        return result is None
    return (
        isinstance(result, Mapping)
        and set(result)
        == {"id", "version", "shortName", "game", "docsName", "steamId", "isVr"}
        and all(
            isinstance(result[key], str) and result[key]
            for key in ("id", "version", "shortName", "game", "docsName")
        )
        and type(result["steamId"]) is int
        and result["steamId"] > 0
        and type(result["isVr"]) is bool
    )


def _match(confidence: str, observation: Mapping[str, Any]) -> bool:
    """Require the match identity, confidence, and Rust-authored explanation together."""
    if not _complete(observation) or observation["error"] is not None:
        return False
    result = observation["result"]
    return (
        isinstance(result, Mapping)
        and set(result) == {"matchedId", "confidence", "message"}
        and result["confidence"] == confidence
        and isinstance(result["message"], str)
        and bool(result["message"])
        and (
            result["matchedId"] is None
            if confidence == "unknown"
            else isinstance(result["matchedId"], str) and bool(result["matchedId"])
        )
    )


def _invalid(observation: Mapping[str, Any]) -> bool:
    """Invalid native parse results are distinct from a successful unknown match."""
    return (
        _complete(observation)
        and observation["result"] is None
        and observation["error"] == {"code": "invalid_version"}
    )


_LOOKUP_OPERATIONS = (
    None,
    "__init__",
    "get_by_id",
    "get_version_by_id",
    "getVersionById",
    "version_registry_get_by_id",
)
_MATCH_OPERATIONS = (
    None,
    "match_version",
    "match_version_string",
    "matchVersion",
    "version_registry_match_version",
)


def _configuration(value: object, keys: set[str]) -> bool:
    """Require every transported configuration field without guessing absent values."""
    return (
        isinstance(value, Mapping)
        and set(value) == keys
        and all(isinstance(item, str) for item in value.values())
    )


def _remaining(operation: str, observation: Mapping[str, Any]) -> bool:
    """Keep enumeration and configuration facts separate from metadata lookup."""
    if not _complete(observation) or observation["error"] is not None:
        return False
    result = observation["result"]
    if operation == "xse":
        return result is None or (
            isinstance(result, Mapping)
            and set(result)
            == {"acronym", "fullName", "compatibleVersion", "loader", "fileCount"}
            and type(result["fileCount"]) is int
            and result["fileCount"] >= 0
            and all(
                isinstance(value, str)
                for key, value in result.items()
                if key != "fileCount"
            )
        )
    if not isinstance(result, Mapping):
        return False
    if operation == "enumerate":
        return set(result) == {"ids", "count", "filteredIds"} and (
            type(result["count"]) is int
            and isinstance(result["ids"], list)
            and isinstance(result["filteredIds"], list)
            and result["count"] == len(result["ids"])
            and all(
                isinstance(item, str) for item in result["ids"] + result["filteredIds"]
            )
        )
    keys = {"version", "name", "acronym", "dllFile", "description", "downloadUrl"}
    return set(result) == {"configs", "selected"} and (
        isinstance(result["configs"], list)
        and all(_configuration(item, keys) for item in result["configs"])
        and (result["selected"] is None or _configuration(result["selected"], keys))
    )


def _confidence_carrier(observation: Mapping[str, Any]) -> bool:
    """Require a successful public match before crediting its confidence object."""
    return any(_match(kind, observation) for kind in ("exact", "nearest", "unknown"))


def _crashgen_carrier(observation: Mapping[str, Any]) -> bool:
    """Empty/missing configurations cannot prove a returned configuration carrier."""
    return _remaining("crashgen", observation) and bool(
        observation["result"]["configs"]
    )


VERSION_REGISTRY_COVERAGE_POLICY = FamilyCoveragePolicy(
    "version-registry",
    (
        *(
            CoveragePredicate(
                id="version-registry." + operation,
                capability_id="version-registry." + operation,
                action="version-registry." + operation,
                observation_family="values",
                rust_symbols=symbols,
                matches=partial(_remaining, operation),
                runtime_operations=operations,
            )
            for operation, symbols, operations in (
                (
                    "enumerate",
                    ("get_all", "get_all_for_game", "VersionRegistry"),
                    (
                        "get_all",
                        "get_all_for_game",
                        "getAllVersions",
                        "getAllVersionsForGame",
                        "version_registry_get_all_ids",
                        "version_registry_get_all_count",
                        "version_registry_get_all_for_game",
                    ),
                ),
                (
                    "crashgen",
                    (
                        "get_crashgen_versions",
                        "get_crashgen_for_version",
                        "VersionRegistry",
                    ),
                    (
                        "get_crashgen_configs",
                        "get_crashgen_for_version",
                        "VersionInfo.get_crashgen_for_version",
                        "getCrashgenVersions",
                        "getCrashgenForVersion",
                        "version_registry_get_crashgen_configs",
                        "version_registry_get_crashgen_config",
                    ),
                ),
                ("xse", ("XseConfig",), (None, "version_registry_get_xse_config")),
            )
        ),
        *(
            CoveragePredicate(
                id="version-registry." + name,
                capability_id="version-registry.query",
                action="version-registry.query",
                observation_family="values",
                rust_symbols=("get_by_id", "VersionInfo", "VersionRegistry"),
                matches=partial(_lookup, found),
                runtime_operations=_LOOKUP_OPERATIONS,
            )
            for name, found in (("metadata", True), ("missing-id", False))
        ),
        *(
            CoveragePredicate(
                id="version-registry." + confidence,
                capability_id="version-registry.query",
                action="version-registry.query",
                observation_family="values",
                rust_symbols=("match_version", "MatchResult", "VersionRegistry"),
                matches=partial(_match, confidence),
                runtime_operations=_MATCH_OPERATIONS,
            )
            for confidence in ("exact", "nearest", "unknown")
        ),
        CoveragePredicate(
            id="version-registry.singleton",
            capability_id="version-registry.query",
            action="version-registry.query",
            observation_family="values",
            rust_symbols=("get_version_registry",),
            matches=partial(_lookup, True),
            runtime_operations=("get_version_registry",),
        ),
        CoveragePredicate(
            id="version-registry.confidence-carrier",
            capability_id="version-registry.query",
            action="version-registry.query",
            observation_family="values",
            rust_symbols=("MatchConfidence",),
            matches=_confidence_carrier,
            runtime_operations=(None, "__eq__", "__hash__", "is_high_confidence"),
        ),
        CoveragePredicate(
            id="version-registry.crashgen-carrier",
            capability_id="version-registry.crashgen",
            action="version-registry.crashgen",
            observation_family="values",
            rust_symbols=("CrashgenConfig",),
            matches=_crashgen_carrier,
            runtime_operations=(None,),
        ),
        CoveragePredicate(
            id="version-registry.invalid-version",
            capability_id="version-registry.query",
            action="version-registry.query",
            observation_family="errors",
            rust_symbols=("match_version", "MatchResult", "VersionRegistry"),
            matches=_invalid,
            runtime_operations=_MATCH_OPERATIONS,
        ),
    ),
)
