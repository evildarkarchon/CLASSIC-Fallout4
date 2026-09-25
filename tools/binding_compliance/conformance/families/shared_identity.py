"""Narrow shared-core game token and runtime access contracts."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

GAME_ROWS = (
    "parity:cxx:d04a85fb7225176b",
    "parity:cxx:e5c87d8b488cc983",
    "parity:node:aux-phase4c-js-game-id",
    "parity:node:aux-phase4c-get-all-game-ids",
    "parity:python:shared.lib.GameId",
    "parity:python:shared.lib.GameId.as_str",
)


def _games(value: Mapping[str, Any]) -> bool:
    """Require complete ordered domain tokens, not just a successful call flag."""
    return (
        set(value) == {"tokens"}
        and isinstance(value["tokens"], list)
        and len(value["tokens"]) == 4
        and all(isinstance(token, str) for token in value["tokens"])
    )


def _game_metadata(value: Mapping[str, Any]) -> bool:
    """Require the independent user-facing label contract, distinct from identity tokens."""
    return value == {"labels": ["Fallout 4", "Fallout 4 VR", "Skyrim", "Starfield"]}


def _game_details(value: Mapping[str, Any]) -> bool:
    """Require native executable/VR metadata plus identity, representation, and hashing results."""
    expected = {
        "games": [
            {
                "exeName": exe,
                "vr": vr,
                "text": token,
                "repr": f"GameId.{token}",
                "equalCopy": True,
                "equalOther": False,
                "hashCopy": True,
            }
            for token, exe, vr in (
                ("Fallout4", "Fallout4.exe", False),
                ("Fallout4VR", "Fallout4VR.exe", True),
                ("Skyrim", "SkyrimSE.exe", False),
                ("Starfield", "Starfield.exe", False),
            )
        ]
    }
    return json.dumps(value, sort_keys=True) == json.dumps(expected, sort_keys=True)


def _runtime(value: Mapping[str, Any]) -> bool:
    """Retain both initial and repeated public availability results."""
    return set(value) == {"available", "diagnosticsAvailable"} and all(
        isinstance(value[key], list)
        and len(value[key]) == 2
        and all(type(item) is bool for item in value[key])
        for key in value
    )


def validate_pack(document: Mapping[str, Any], root: Path) -> tuple[Path, ...]:
    """Validate input-only requests without synthesizing either domain oracle."""
    family = document["familyId"]
    if family not in {"game-identity", "runtime-access"}:
        raise ValueError("unsupported shared identity family")
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"]
            not in (
                {
                    "game-identity.observe",
                    "game-identity.metadata",
                    "game-identity.details",
                }
                if family == "game-identity"
                else {family + ".observe"}
            )
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("scenario must declare its sole input fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("fixture escapes fixture root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if family == "game-identity" and case["action"] != "game-identity.observe":
            operation = case["action"].removeprefix("game-identity.")
            if fixture != {"request": {"operation": operation}} or not (
                _game_metadata if operation == "metadata" else _game_details
            )(case["expected"]):
                raise ValueError("game metadata fixture or observation malformed")
            paths.append(path)
            continue
        if fixture != {"request": {}} or not (
            _games if family == "game-identity" else _runtime
        )(case["expected"]):
            raise ValueError("shared identity fixture or observation malformed")
        paths.append(path)
    return tuple(paths)


def coverage_policy(family: str) -> FamilyCoveragePolicy:
    """Limit token credit to exact invoked carriers and runtime credit to access calls."""
    if family == "game-identity":
        symbols, matches, rows, operations = (
            ("GameId", "as_str"),
            _games,
            GAME_ROWS,
            (None, "as_str", "game_id_as_str", "getAllGameIds"),
        )
    elif family == "runtime-access":
        symbols, matches, rows, operations = (
            ("get_runtime",),
            _runtime,
            (),
            (
                None,
                "init_runtime",
                "is_runtime_active",
                "isRuntimeAvailable",
                "getRuntimeInfo",
                "get_runtime_stats",
                "is_runtime_healthy",
            ),
        )
    else:
        raise ValueError("unsupported shared identity family")
    return FamilyCoveragePolicy(
        family,
        (
            CoveragePredicate(
                id=family + "-observed",
                capability_id=family + ".observe",
                action=family + ".observe",
                observation_family=family,
                rust_symbols=symbols,
                matches=matches,
                binding_obligation_ids=rows,
                runtime_operations=operations,
            ),
        )
        + (
            (
                CoveragePredicate(
                    id="runtime-access.shutdown-intent",
                    capability_id="runtime-access.observe",
                    action="runtime-access.observe",
                    observation_family="runtime-access",
                    rust_symbols=("get_runtime",),
                    matches=_runtime,
                    binding_obligation_ids=("parity:cxx:b0a1036b892934c2",),
                    runtime_operations=("shutdown_runtime",),
                ),
            )
            if family == "runtime-access"
            else ()
        )
        + (
            (
                CoveragePredicate(
                    id="game-identity.metadata",
                    capability_id="game-identity.metadata",
                    action="game-identity.metadata",
                    observation_family="game-identity",
                    rust_symbols=("GameId", "display_name"),
                    runtime_operations=(
                        "getGameName",
                        "display_name",
                        "game_id_display_name",
                    ),
                    matches=_game_metadata,
                ),
                CoveragePredicate(
                    id="game-identity.details",
                    capability_id="game-identity.details",
                    action="game-identity.details",
                    observation_family="game-identity",
                    rust_symbols=("GameId", "exe_name", "is_vr"),
                    runtime_operations=(
                        "exe_name",
                        "is_vr",
                        "__repr__",
                        "__str__",
                        "__eq__",
                        "__hash__",
                    ),
                    matches=_game_details,
                ),
            )
            if family == "game-identity"
            else ()
        ),
    )
