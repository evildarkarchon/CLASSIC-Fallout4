"""Independent URL, resource and version operations with narrow executable facts."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

OPERATIONS = {
    "web-operations": (
        ("is_valid_url", ("is_valid_url",)),
        ("validate_url", ("validate_url", "validate_url_string")),
        ("extract_domain", ("extract_domain", "extract_domain_string")),
        ("join_url", ("join_url", "web_join_url")),
        ("build_url_with_query", ("build_url_with_query", "web_build_url_with_query")),
    ),
    "resource-operations": (
        ("detect_resource_type", ("detect_resource_type",)),
        ("is_supported_resource", ("is_supported_resource",)),
        (
            "ResourceType",
            (
                "parse_resource_type",
                "as_str",
                "extensions",
                "enumerate_resources",
                "texture",
                "mesh",
                "script",
                "plugin",
                "sound",
                "animation",
                "interface",
                "strings",
                "archive",
                "config",
                "other",
            ),
        ),
        ("extensions", ("get_resource_extensions", "extensions")),
        (
            "ResourceInfo",
            (
                "create_resource_info",
                "create_resource_info_with_size",
                "__init__",
                "path",
                "resource_type",
                "size",
            ),
        ),
        ("enumerate_resources", ("enumerate_resources",)),
        ("count_resources_by_type", ("count_resources_by_type",)),
        ("validate_resource", ("validate_resource",)),
    ),
    "version-operations": (
        ("parse_version", ("parse_version",)),
        ("try_parse_version", ("try_parse_version",)),
        ("compare_versions", ("compare_versions",)),
        ("format_version", ("format_version",)),
    ),
}
OPERATIONS.update(
    {
        family: ()
        for family in [
            "version-extraction",
            "version-f4se",
            "version-pe",
            "version-pe-path",
        ]
    }
)
OBSERVATIONS = {
    "web-operations": "url-resolution",
    "resource-operations": "resource-classification",
    "version-operations": "version-comparison",
}


def _result(value: object) -> bool:
    """Require a real success value or explicit domain error, never both."""
    return (
        isinstance(value, Mapping)
        and set(value) == {"value", "error"}
        and (
            isinstance(value["value"], str)
            and value["error"] is None
            or value["value"] is None
            and isinstance(value["error"], str)
            and bool(value["error"])
        )
    )


def _observation(family: str, value: Mapping[str, Any]) -> bool:
    """Validate complete domain facts independently of receipt metadata."""
    if family == "web-operations":
        return (
            set(value) == {"valid", "validated", "domain", "joined", "query"}
            and type(value["valid"]) is bool
            and all(
                _result(value[key])
                for key in ("validated", "domain", "joined", "query")
            )
        )
    if family == "resource-operations":
        return (
            set(value)
            == {
                "detected",
                "supported",
                "parsed",
                "extensions",
                "info",
                "resources",
                "counts",
                "validation",
                "typeCatalog",
                "sizedInfo",
                "files",
            }
            and type(value["supported"]) is bool
            and isinstance(value["typeCatalog"], list)
            and value["typeCatalog"]
            == [
                "texture",
                "mesh",
                "script",
                "plugin",
                "sound",
                "animation",
                "interface",
                "strings",
                "archive",
                "config",
                "other",
            ]
            and all(isinstance(value[key], str) for key in ("detected", "parsed"))
            and isinstance(value["extensions"], list)
            and all(isinstance(item, str) for item in value["extensions"])
            and _resource_info(value["info"])
            and _resource_info(value["sizedInfo"])
            and isinstance(value["files"], list)
            and all(
                isinstance(item, Mapping)
                and set(item) == {"path", "hex"}
                and _relative(item["path"])
                and isinstance(item["hex"], str)
                and re.fullmatch(r"(?:[0-9a-f]{2})*", item["hex"]) is not None
                for item in value["files"]
            )
            and [item["path"] for item in value["files"]]
            == sorted({item["path"] for item in value["files"]})
            and isinstance(value["resources"], list)
            and all(_resource_info(item) for item in value["resources"])
            and isinstance(value["counts"], list)
            and all(
                isinstance(item, Mapping)
                and set(item) == {"type", "count"}
                and isinstance(item["type"], str)
                and type(item["count"]) is int
                and item["count"] >= 0
                for item in value["counts"]
            )
            and isinstance(value["validation"], list)
            and bool(value["validation"])
            and all(
                isinstance(item, Mapping)
                and set(item) == {"path", "error"}
                and _relative(item["path"])
                and item["error"] in (None, "not_found", "invalid_type")
                for item in value["validation"]
            )
        )
    return (
        set(value) == {"parsed", "optional", "comparison", "formatted"}
        and _result(value["parsed"])
        and (value["optional"] is None or isinstance(value["optional"], str))
        and (value["formatted"] is None or isinstance(value["formatted"], str))
        and (
            value["comparison"] is None
            or type(value["comparison"]) is int
            and value["comparison"] in (-1, 0, 1)
        )
    )


def _relative(value: object) -> bool:
    """Only fixture-owned portable relative paths may reach filesystem operations."""
    return (
        isinstance(value, str)
        and bool(value)
        and not any(char in value for char in "\\:")
        and all(part not in {"", ".", ".."} for part in value.split("/"))
    )


def _resource_info(value: object) -> bool:
    """Require real resource path, classification and nonnegative byte size."""
    return (
        isinstance(value, Mapping)
        and set(value) == {"path", "type", "size"}
        and _relative(value["path"])
        and isinstance(value["type"], str)
        and type(value["size"]) is int
        and value["size"] >= 0
    )


def validate_aux_operations_pack(
    document: Mapping[str, Any], root: Path
) -> tuple[Path, ...]:
    """Reject non-input fixtures and malformed requests before adapter execution."""
    family = document["familyId"]
    if family not in OPERATIONS:
        raise ValueError("unknown auxiliary owner domain")
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for scenario in document["scenarios"]:
        reference = scenario["input"].get("fixtureRef")
        if (
            scenario["action"] != family + ".observe"
            or scenario["input"] != {"fixtureRef": reference}
            or scenario["fixtureRefs"] != [reference]
        ):
            raise ValueError("auxiliary scenario must declare only its input fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("auxiliary fixture escapes its root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if family.startswith("version-") and "operation" in fixture.get("request", {}):
            from .version_extended import validate_fixture

            validate_fixture(fixture, scenario["expected"])
            paths.append(path)
            continue
        if set(fixture) != (
            {"request", "files"} if family == "resource-operations" else {"request"}
        ) or not isinstance(fixture["request"], Mapping):
            raise ValueError("auxiliary fixture must contain only a request")
        request = fixture["request"]
        fields = {
            "web-operations": {"url", "path", "params"},
            "resource-operations": {"path", "type", "validate", "types"},
            "version-operations": {"version", "other"},
        }[family]
        if set(request) != fields or not all(
            isinstance(value, str)
            for key, value in request.items()
            if key not in {"params", "validate", "types"}
        ):
            raise ValueError("malformed auxiliary request")
        if family == "web-operations" and (
            not isinstance(request["params"], list)
            or not all(
                isinstance(pair, list)
                and len(pair) == 2
                and all(isinstance(item, str) for item in pair)
                for pair in request["params"]
            )
        ):
            raise ValueError("URL query parameters must be ordered string pairs")
        if family == "resource-operations" and (
            not isinstance(fixture["files"], Mapping)
            or not all(
                _relative(key) and isinstance(value, str)
                for key, value in fixture["files"].items()
            )
            or not _relative(request["path"])
            or not isinstance(request["validate"], list)
            or not all(_relative(item) for item in request["validate"])
            or request["types"]
            != [
                "texture",
                "mesh",
                "script",
                "plugin",
                "sound",
                "animation",
                "interface",
                "strings",
                "archive",
                "config",
                "other",
            ]
        ):
            raise ValueError("resource paths must remain inside the fixture workspace")
        if not _observation(family, scenario["expected"]):
            raise ValueError("malformed auxiliary domain observation")
        paths.append(path)
    return tuple(paths)


def _operation_observation(
    family: str, operation: str, value: Mapping[str, Any]
) -> bool:
    """Only executed operations earn facts; failed parse skips compare and format."""
    return _observation(family, value) and not (
        family == "version-operations"
        and operation in {"compare_versions", "format_version"}
        and value["parsed"]["error"] is not None
    )


def aux_operations_coverage_policy(family: str) -> FamilyCoveragePolicy:
    """Attribute actual operation observations to canonical public Rust symbols."""
    from .version_extended import predicates

    return FamilyCoveragePolicy(
        family,
        tuple(
            CoveragePredicate(
                id=symbol.replace("_", "-").lower(),
                capability_id=family + ".observe",
                action=family + ".observe",
                observation_family=OBSERVATIONS[family],
                rust_symbols=(symbol,),
                matches=partial(_operation_observation, family, symbol),
                runtime_operations=(None, *aliases),
            )
            for symbol, aliases in OPERATIONS[family]
        )
        + tuple(predicates(family)),
    )
