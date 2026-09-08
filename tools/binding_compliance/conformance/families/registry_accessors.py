"""Operation-scoped registry accessors over disposable process-owned state."""

import json
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

OPERATIONS = {
    "registry-game": {
        "set_game": ("set_game", "registrySetGame", "registry_set_game"),
        "get_game": ("get_game", "registryGetGame", "registry_get_game"),
        "GAME": ("registry_key_game",),
    },
    "registry-gui": {
        "is_gui_mode": ("is_gui_mode", "registry_is_gui_mode"),
        "IS_GUI_MODE": ("registry_key_is_gui_mode",),
    },
    "registry-paths": {
        "set_application_dir": ("set_application_dir", "setApplicationDir"),
        "get_application_dir": ("get_application_dir", "getApplicationDir"),
    },
    "registry-context": {
        name: (name,)
        for name in (
            "get_yaml_cache",
            "get_manual_docs_gui",
            "get_game_path_gui",
            "get_local_dir",
            "is_version_auto_detected",
            "is_xse_valid",
            "is_enb_present",
            "get_game_version_string",
        )
    },
}


def _observed(family: str, value: Mapping[str, Any]) -> bool:
    """Require each public result and reset effect without accepting extra fields."""
    if family == "registry-game":
        return (
            set(value) == {"key", "game", "replacement", "afterClearPresent"}
            and value["key"] == "gamevars_game"
            and all(isinstance(value[k], str) for k in ("game", "replacement"))
            and value["afterClearPresent"] is False
        )
    if family == "registry-gui":
        return (
            set(value) == {"key", "default", "enabled", "disabled", "afterClear"}
            and value["key"] == "is_gui_mode"
            and (
                value["default"] is False
                and value["enabled"] is True
                and value["disabled"] is False
                and value["afterClear"] is False
            )
        )
    if family == "registry-paths":
        return set(value) == {
            "initial",
            "path",
            "replacement",
            "afterClear",
            "files",
        } and (
            value["initial"] is None
            and value["afterClear"] is None
            and value["files"] == []
            and all(isinstance(value[k], str) for k in ("path", "replacement"))
        )
    return set(value) == {"initial", "stored", "afterClear", "localDir", "files"} and (
        value["files"] == []
        and isinstance(value["localDir"], str)
        and all(_context(value[k]) for k in ("initial", "stored", "afterClear"))
    )


def _context(value: Any) -> bool:
    """Preserve nullable object values and typed flags separately from absence."""
    return (
        isinstance(value, dict)
        and set(value)
        == {
            "yamlCache",
            "manualDocs",
            "gamePath",
            "autoDetected",
            "xseValid",
            "enbPresent",
            "version",
        }
        and all(
            value[k] is None or isinstance(value[k], str)
            for k in (
                "yamlCache",
                "manualDocs",
                "gamePath",
            )
        )
        and all(
            type(value[k]) is bool
            for k in (
                "autoDetected",
                "xseValid",
                "enbPresent",
            )
        )
        and isinstance(value["version"], str)
    )


def validate_pack(document: Mapping[str, Any], root: Path) -> tuple[Path, ...]:
    """Reject undeclared input and paths before any adapter touches registry state."""
    family = document["familyId"]
    if family not in OPERATIONS:
        raise ValueError("unknown registry accessor family")
    fixture_root = (root / document["fixtureRoot"]).resolve()
    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != family + ".observe"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("registry accessor needs its sole declared input fixture")
        path = (fixture_root / document["fixtures"][reference]).resolve()
        if not path.is_relative_to(fixture_root):
            raise ValueError("registry fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(fixture, dict) or set(fixture) != {"request"}:
            raise ValueError("registry fixture must be input-only")
        request = fixture["request"]
        keys = (
            {"game", "replacement"}
            if family == "registry-game"
            else {"value", "version"}
            if family == "registry-context"
            else set()
        )
        if (
            not isinstance(request, dict)
            or set(request) != keys
            or not all(isinstance(v, str) for v in request.values())
            or not _observed(family, case["expected"])
        ):
            raise ValueError("malformed registry accessor request or observation")
        paths.append(path)
    return tuple(paths)


def coverage_policy(family: str) -> FamilyCoveragePolicy:
    """Credit exact executed convenience methods, never their entire owner module."""
    return FamilyCoveragePolicy(
        family,
        tuple(
            CoveragePredicate(
                id=family
                + "."
                + ("key-" if symbol.isupper() else "")
                + symbol.replace("_", "-").lower(),
                capability_id=family + ".observe",
                action=family + ".observe",
                observation_family="registry-state",
                rust_symbols=(symbol,),
                runtime_operations=(None, *aliases),
                matches=partial(_observed, family),
            )
            for symbol, aliases in OPERATIONS[family].items()
        ),
    )
