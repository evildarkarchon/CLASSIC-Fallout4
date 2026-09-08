"""Separate shared-string and registry owners with operation-scoped evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

SYMBOLS = {
    "string-operations": (
        "StringProcessor",
        "intern",
        "normalize_string",
        "process_batch",
    ),
    "registry-operations": (
        "register",
        "get",
        "unregister",
        "clear_all",
        "is_registered",
    ),
}


def _strings(value: Any) -> bool:
    """Accept ordered string observations without silently coercing values."""
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _string_observed(value: Mapping[str, Any]) -> bool:
    """Require every stable result of interning and normalization."""
    return set(value) == {"interned", "normalized", "batch"} and all(
        _strings(value[key]) for key in value
    )


def _registry_observed(value: Mapping[str, Any]) -> bool:
    """Require stored typed values and absence after both removal operations."""
    if set(value) != {
        "initiallyPresent",
        "stored",
        "replacement",
        "afterRemovePresent",
        "afterClearPresent",
        "gameVersion",
    }:
        return False
    stored = value["stored"]
    return (
        all(
            value[key] is False
            for key in ("initiallyPresent", "afterRemovePresent", "afterClearPresent")
        )
        and isinstance(value["replacement"], str)
        and isinstance(value["gameVersion"], str)
        and isinstance(stored, dict)
        and set(stored) == {"stringValue", "boolValue", "intValue"}
        and isinstance(stored["stringValue"], str)
        and type(stored["boolValue"]) is bool
        and type(stored["intValue"]) is int
    )


def validate_pack(document: Mapping[str, Any], root: Path) -> tuple[Path, ...]:
    """Validate input-only fixtures and authored result shape without computing an oracle."""
    family = document["familyId"]
    if family not in SYMBOLS:
        raise ValueError("unsupported shared/registry family")
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != family + ".execute"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("scenario must declare its sole input fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("fixture escapes fixture root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(fixture, dict)
            or set(fixture) != {"request"}
            or not isinstance(fixture["request"], dict)
        ):
            raise ValueError("fixture must contain only request")
        request = fixture["request"]
        if family == "string-operations":
            valid = (
                set(request) == {"values"}
                and _strings(request["values"])
                and _string_observed(case["expected"])
            )
        else:
            valid = (
                set(request)
                == {
                    "stringValue",
                    "boolValue",
                    "intValue",
                    "replacement",
                    "gameVersion",
                }
                and isinstance(request["gameVersion"], str)
                and isinstance(request["stringValue"], str)
                and isinstance(request["replacement"], str)
                and type(request["boolValue"]) is bool
                and type(request["intValue"]) is int
                and -(2**31) <= request["intValue"] < 2**31
                and _registry_observed(case["expected"])
            )
        if not valid:
            raise ValueError("shared/registry request or observation malformed")
        paths.append(path)
    return tuple(paths)


def coverage_policy(family: str) -> FamilyCoveragePolicy:
    """Credit only calls performed by this family, never other class operations."""
    if family == "string-operations":
        operations = (
            None,
            "intern",
            "normalize",
            "normalize_string",
            "process_batch",
            "internString",
            "normalizeString",
            "processStringBatch",
        )
        matches = _string_observed
    elif family == "registry-operations":
        operations = (
            None,
            "register",
            "get",
            "unregister",
            "clear_all",
            "is_registered",
            "registrySet",
            "registryGet",
            "registryGetGameVersion",
            "registryRemove",
            "registryClear",
            "registry_set_string",
            "registry_set_bool",
            "registry_set_i32",
            "registry_get_string",
            "registry_get_bool",
            "registry_get_i32",
            "registry_is_registered",
            "registry_unregister",
            "registry_clear_all",
        )
        matches = _registry_observed
    else:
        raise ValueError("unsupported shared/registry family")
    return FamilyCoveragePolicy(
        family,
        (
            CoveragePredicate(
                id=family + "-observed",
                capability_id=family + ".execute",
                action=family + ".execute",
                observation_family=family,
                rust_symbols=SYMBOLS[family],
                matches=matches,
                runtime_operations=operations,
            ),
        ),
    )
