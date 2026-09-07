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
            case["action"] != family + ".observe"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("scenario must declare its sole input fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("fixture escapes fixture root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
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
        ),
    )
