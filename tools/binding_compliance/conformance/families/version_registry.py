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
    "get_by_id",
    "get_version_by_id",
    "getVersionById",
    "version_registry_get_by_id",
)
_MATCH_OPERATIONS = (
    None,
    "match_version",
    "matchVersion",
    "version_registry_match_version",
)
VERSION_REGISTRY_COVERAGE_POLICY = FamilyCoveragePolicy(
    "version-registry",
    (
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
