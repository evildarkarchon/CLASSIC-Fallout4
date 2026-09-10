"""Version value contracts with exact public-operation evidence."""

import json
from collections.abc import Mapping
from functools import partial

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

OPERATIONS = {
    "game-version-parse": (
        ("parse", "GameVersion"),
        (None, "parse_game_version", "parseGameVersion", "__init__"),
    ),
    "game-version-distance": (
        ("semantic_distance",),
        ("semantic_distance", "GameVersion.semantic_distance", "gameVersionDistance"),
    ),
    "game-version-order": (
        ("same_major", "GameVersion"),
        (
            "__eq__",
            "__lt__",
            "__le__",
            "__gt__",
            "__ge__",
            "__hash__",
            "same_major",
            "GameVersion.same_major",
        ),
    ),
    "fallout4-identity": (
        ("Fallout4Version", "is_vr", "exe_name", "steam_app_id"),
        (
            None,
            "all",
            "getAllFallout4Versions",
            "getFallout4VersionInfo",
            "is_vr",
            "exe_name",
            "steam_app_id",
            "fallout4_version_is_vr",
            "fallout4_version_exe_name",
            "fallout4_version_steam_app_id",
        ),
    ),
    "fallout4-paths": (
        ("as_str", "docs_folder_name", "is_standard", "registry_id", "Fallout4Version"),
        (
            "Fallout4Version.as_str",
            "as_str",
            "docs_folder_name",
            "is_standard",
            "registry_id",
            "fallout4_version_as_str",
            "fallout4_version_docs_folder_name",
            "fallout4_version_is_standard",
            "fallout4_version_registry_id",
        ),
    ),
    "fallout4-metadata": (
        ("game_version", "Fallout4Version"),
        (
            "Fallout4Version.version",
            "version",
            "short_name",
            "xse_acronym",
            "display_name",
            "__repr__",
            "__str__",
            "__eq__",
            "__hash__",
            "from_str",
        ),
    ),
}


def _observed(family, value):
    """Require complete exact result shapes, including read-only file effects."""
    if not isinstance(value, Mapping):
        return False
    if family == "game-version-parse":
        return set(value) == {"parsed"} and (
            value["parsed"] is None or isinstance(value["parsed"], str)
        )
    if family == "game-version-distance":
        return (
            set(value) == {"distance"}
            and type(value["distance"]) is int
            and value["distance"] >= 0
        )
    if family == "game-version-order":
        return set(value) == {
            "equal",
            "less",
            "lessEqual",
            "greater",
            "greaterEqual",
            "sameMajor",
            "hashEqualCopy",
        } and all(type(v) is bool for v in value.values())
    keys = {
        "fallout4-identity": {"isVr", "exeName", "steamAppId"},
        "fallout4-paths": {"token", "docsName", "standard", "registryId"},
        "fallout4-metadata": {
            "version",
            "shortName",
            "xse",
            "displayName",
            "repr",
            "text",
            "equalCopy",
            "hashEqualCopy",
        },
    }[family]
    return (
        set(value)
        == (
            {"variants", "files", "aliases"}
            if family == "fallout4-metadata"
            else {"variants", "files"}
        )
        and isinstance(value["variants"], list)
        and len(value["variants"]) == 4
        and all(
            isinstance(v, Mapping)
            and set(v) == keys
            and all(isinstance(x, (str, int, bool)) for x in v.values())
            for v in value["variants"]
        )
        and isinstance(value["files"], list)
        and len(value["files"]) == 1
        and value["files"][0].get("path") == "CLASSIC Main.yaml"
        and set(value["files"][0]) == {"path", "content"}
        and isinstance(value["files"][0]["content"], str)
        and (
            family != "fallout4-metadata"
            or isinstance(value["aliases"], list)
            and all(v is None or isinstance(v, str) for v in value["aliases"])
        )
    )


def validate_version_values_pack(document, root):
    """Reject input oracles and malformed requests before initializing public state."""
    family = document["familyId"]
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != family + ".observe"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("invalid version value fixture reference")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("version value fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        request = fixture.get("request")
        fields = {
            "game-version-parse": {"version"},
            "game-version-distance": {"a", "b"},
            "game-version-order": {"a", "b"},
            "fallout4-metadata": {"aliases"},
        }.get(family, set())
        if (
            not isinstance(request, Mapping)
            or set(request) != fields
            or set(fixture)
            != (
                {"request", "registryYaml"}
                if family.startswith("fallout4-")
                else {"request"}
            )
        ):
            raise ValueError("malformed version value input")
        if family.startswith("game-version-") and not all(
            isinstance(v, str) for v in request.values()
        ):
            raise ValueError("version inputs must be strings")
        if family.startswith("fallout4-") and not isinstance(
            fixture["registryYaml"], str
        ):
            raise ValueError("registry input must be YAML bytes")
        if family == "fallout4-metadata" and (
            not isinstance(request["aliases"], list)
            or not all(isinstance(v, str) for v in request["aliases"])
        ):
            raise ValueError("aliases must be input strings")
        if not _observed(family, case["expected"]):
            raise ValueError("malformed version value observation")
        paths.append(path)
    return tuple(paths)


def version_values_coverage_policy(family):
    """Restrict each fact to the public methods actually called by its adapter."""
    symbols, operations = OPERATIONS[family]
    return FamilyCoveragePolicy(
        family,
        (
            CoveragePredicate(
                id=family + "-values",
                capability_id=family + ".observe",
                action=family + ".observe",
                observation_family="value-results",
                rust_symbols=symbols,
                runtime_operations=operations,
                matches=partial(_observed, family),
            ),
        )
        + (
            (
                CoveragePredicate(
                    id="game-version-null-sentinel",
                    capability_id="game-version-parse.observe",
                    action="game-version-parse.observe",
                    observation_family="value-results",
                    rust_symbols=("NULL_VERSION",),
                    runtime_operations=("is_null_version",),
                    matches=lambda value: (
                        _observed("game-version-parse", value)
                        and isinstance(value["parsed"], str)
                    ),
                ),
            )
            if family == "game-version-parse"
            else ()
        )
        + (
            (
                CoveragePredicate(
                    id="fallout4-config-executable",
                    capability_id="fallout4-paths.config-exe",
                    action="fallout4-paths.observe",
                    observation_family="value-results",
                    rust_symbols=("resolve_registry_version_info",),
                    runtime_operations=("resolve_fallout4_exe_name",),
                    matches=partial(_observed, "fallout4-paths"),
                ),
            )
            if family == "fallout4-paths"
            else ()
        ),
    )
