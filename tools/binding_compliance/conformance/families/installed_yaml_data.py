"""Public Installed YAML Data observations and narrowly scoped coverage facts.

Exact values are compared by the central receipt validator. These predicates
recognize independently meaningful selection, snapshot, failure, and filesystem
relationships; they never read fixture inputs, expected results, or runner labels.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_FIELDS = {
    "outcome",
    "game",
    "gameDataRole",
    "main",
    "gameFile",
    "localIgnore",
    "recovery",
    "snapshot",
    "diagnostics",
    "error",
    "files",
}
_IGNORE = "installation/CLASSIC Data/CLASSIC Ignore.yaml"
_INSPECT_SYMBOLS = (
    "inspect_installed_yaml_data",
    "InstalledYamlDataInspection",
    "InstalledYamlDataInspectionError",
    "InstalledYamlDataInspectionRequest",
)
_LOAD_SYMBOLS = (
    "load_installed_yaml_data",
    "InstalledYamlDataSnapshot",
    "InstalledYamlDataLoadError",
    "InstalledYamlDataLoadRequest",
    "InstalledYamlDataLoadOutcome",
)
_INSPECT_OPERATIONS = (
    None,
    "inspect_installed_yaml_data",
    "inspectInstalledYamlData",
    "installed_yaml_data_inspect",
    "installed_yaml_data_inspection_status",
    "installed_yaml_data_inspection_take",
    "installed_yaml_data_inspection_diagnostics",
    "installed_yaml_data_inspection_game",
    "installed_yaml_data_inspection_game_role",
    "installed_yaml_data_inspection_main",
    "installed_yaml_data_inspection_game_file",
)
_LOAD_OPERATIONS = (
    None,
    "load_installed_yaml_data",
    "loadInstalledYamlData",
    "installed_yaml_data_load",
    "installed_yaml_data_load_status",
    "installed_yaml_data_load_take_snapshot",
    "installed_yaml_data_load_take_recovery_plan",
    "installed_yaml_data_snapshot_diagnostics",
    "installed_yaml_data_snapshot_game",
    "installed_yaml_data_snapshot_game_role",
    "installed_yaml_data_snapshot_main",
    "installed_yaml_data_snapshot_game_file",
    "installed_yaml_data_snapshot_local_ignore_identity",
    "installed_yaml_data_snapshot_local_ignore_state",
    "installed_yaml_data_snapshot_simplify_remove_list",
    "installed_yaml_data_snapshot_yaml_data",
)


def _identity(value: object) -> bool:
    """Require exact-byte identity with a canonical workspace-relative path."""
    return (
        isinstance(value, Mapping)
        and set(value) == {"path", "sha256", "byteLength"}
        and isinstance(value["path"], str)
        and value["path"].startswith(("installation/", "cache/"))
        and "\\" not in value["path"]
        and ".." not in value["path"].split("/")
        and isinstance(value["sha256"], str)
        and re.fullmatch("[0-9a-f]{64}", value["sha256"]) is not None
        and type(value["byteLength"]) is int
        and value["byteLength"] >= 0
    )


def _file(value: object, role: str) -> bool:
    """Recognize one selected source and its role-specific schema metadata."""
    return (
        isinstance(value, Mapping)
        and set(value) == {"role", "provenance", "schemaVersion", "identity"}
        and value["role"] == role
        and value["provenance"] in {"updated", "previous", "bundled"}
        and value["schemaVersion"] == ("2.0" if role == "main" else "1.0")
        and _identity(value["identity"])
    )


def _base(observation: Mapping[str, Any]) -> bool:
    """Reject omitted optional fields and malformed durable/diagnostic inventories."""
    if set(observation) != _FIELDS:
        return False
    files = observation["files"]
    diagnostics = observation["diagnostics"]
    return (
        isinstance(files, list)
        and all(_identity(item) for item in files)
        and [item["path"] for item in files] == sorted({item["path"] for item in files})
        and isinstance(diagnostics, list)
        and all(
            isinstance(item, Mapping)
            and set(item) == {"role", "candidate", "path", "kind"}
            and item["role"] in {None, "main", "game"}
            and item["candidate"] in {None, "updated", "previous", "bundled"}
            and (item["path"] is None or isinstance(item["path"], str))
            and item["kind"]
            in {
                "missing",
                "parse",
                "invalid_schema",
                "incompatible_schema",
                "invalid_role_data",
                "local_ignore_generated",
            }
            for item in diagnostics
        )
    )


def _selection(observation: Mapping[str, Any]) -> bool:
    """Require successful typed game selection and both retained source identities."""
    return (
        _base(observation)
        and observation["error"] is None
        and observation["game"] in {"Fallout4", "Fallout4VR"}
        and observation["gameDataRole"] == "Fallout4"
        and _file(observation["main"], "main")
        and _file(observation["gameFile"], "game")
    )


def _inspect(
    provenance: str, kinds: tuple[str, ...], observation: Mapping[str, Any]
) -> bool:
    """Recognize immutable inspection, including attributed rejected candidates."""
    return (
        _selection(observation)
        and observation["outcome"] == "inspected"
        and all(
            observation[field] is None
            for field in ("localIgnore", "recovery", "snapshot")
        )
        and observation["main"]["provenance"] == provenance
        and observation["gameFile"]["provenance"] == "bundled"
        and tuple(item["kind"] for item in observation["diagnostics"]) == kinds
        and observation["main"]["identity"] in observation["files"]
        and observation["gameFile"]["identity"] in observation["files"]
        and (
            provenance != "previous"
            or not any(
                item["path"]
                == observation["main"]["identity"]["path"].removesuffix(".prev")
                for item in observation["files"]
            )
        )
    )


def _error(code: str, observation: Mapping[str, Any]) -> bool:
    """Recognize the typed failure arm without fabricated selected data."""
    return (
        _base(observation)
        and observation["outcome"] == "error"
        and all(
            observation[field] is None
            for field in (
                "game",
                "gameDataRole",
                "main",
                "gameFile",
                "localIgnore",
                "recovery",
                "snapshot",
            )
        )
        and observation["error"]
        == {"code": code, "role": "main" if code == "no_usable_source" else None}
        and (
            code != "local_ignore_default_invalid"
            or not any(item["path"] == _IGNORE for item in observation["files"])
        )
    )


def _ready(observation: Mapping[str, Any]) -> bool:
    """Require a ready snapshot projected from retained bytes and parsed values."""
    if not _selection(observation) or observation["outcome"] != "ready":
        return False
    local = observation["localIgnore"]
    return (
        observation["recovery"] is None
        and isinstance(local, Mapping)
        and set(local) == {"state", "identity"}
        and local["state"] == "existing"
        and _identity(local["identity"])
        and local["identity"]["path"] == _IGNORE
        and observation["snapshot"]
        == {
            "classicVersion": "9.1.0",
            "gameRootName": "Fallout 4",
            "ignoreList": ["ExistingUserEntry.dll"],
            "simplifyRemoveList": [],
        }
    )


def _retained(observation: Mapping[str, Any]) -> bool:
    """Prove Main, game, and Local Ignore still describe pre-mutation content."""
    return _ready(observation) and all(
        identity not in observation["files"]
        and any(item["path"] == identity["path"] for item in observation["files"])
        for identity in (
            observation["main"]["identity"],
            observation["gameFile"]["identity"],
            observation["localIgnore"]["identity"],
        )
    )


def _legacy(observation: Mapping[str, Any]) -> bool:
    """Prove legacy bytes survived and became the canonical Local Ignore copy."""
    if not _ready(observation):
        return False
    identity = observation["localIgnore"]["identity"]
    legacy = {**identity, "path": "installation/CLASSIC Ignore.yaml"}
    return (
        identity in observation["files"]
        and legacy in observation["files"]
        and observation["diagnostics"]
        == [
            {
                "role": None,
                "candidate": None,
                "path": _IGNORE,
                "kind": "local_ignore_generated",
            }
        ]
    )


def _canonical(observation: Mapping[str, Any]) -> bool:
    """Prove an existing canonical file remains authoritative over legacy bytes."""
    return (
        _ready(observation)
        and observation["diagnostics"] == []
        and observation["localIgnore"]["identity"] in observation["files"]
        and any(
            item["path"] == "installation/CLASSIC Ignore.yaml"
            and item["sha256"] != observation["localIgnore"]["identity"]["sha256"]
            for item in observation["files"]
        )
    )


def _recovery(observation: Mapping[str, Any]) -> bool:
    """Recognize a retained malformed identity and explicitly unavailable defaults."""
    if not _selection(observation) or observation["outcome"] != "recovery_required":
        return False
    plan = observation["recovery"]
    return (
        observation["localIgnore"] is None
        and observation["snapshot"] is None
        and isinstance(plan, Mapping)
        and set(plan)
        == {
            "localIgnorePath",
            "malformedIdentity",
            "defaultIdentity",
            "selectedGameVersion",
        }
        and plan["localIgnorePath"] == _IGNORE
        and _identity(plan["malformedIdentity"])
        and plan["malformedIdentity"] in observation["files"]
        and plan["defaultIdentity"] is None
        and plan["selectedGameVersion"] == "OG"
        and observation["diagnostics"]
        == [{"role": None, "candidate": None, "path": _IGNORE, "kind": "parse"}]
    )


def _symbols_for_fact(action: str, name: str) -> tuple[str, ...]:
    """Credit only the returned result arm, never another arm's opaque carrier."""
    if action == "inspect":
        error = name in {"no-usable-source", "unsupported-game"}
        return tuple(
            symbol
            for symbol in _INSPECT_SYMBOLS
            if symbol
            != (
                "InstalledYamlDataInspection"
                if error
                else "InstalledYamlDataInspectionError"
            )
        )
    if name == "invalid-defaults-before-write":
        return (
            "load_installed_yaml_data",
            "InstalledYamlDataLoadRequest",
            "InstalledYamlDataLoadError",
        )
    return tuple(
        symbol
        for symbol in _LOAD_SYMBOLS
        if symbol != "InstalledYamlDataLoadError"
        and (
            name != "recovery-unavailable-defaults"
            or symbol != "InstalledYamlDataSnapshot"
        )
    )


def _operations_for_fact(action: str, name: str) -> tuple[str | None, ...]:
    """Limit CXX operation credit to the native status and handles actually read."""
    if action == "inspect":
        if name in {"no-usable-source", "unsupported-game"}:
            return (
                None,
                "inspect_installed_yaml_data",
                "inspectInstalledYamlData",
                "installed_yaml_data_inspect",
                "installed_yaml_data_inspection_status",
            )
        return _INSPECT_OPERATIONS
    common = (
        None,
        "load_installed_yaml_data",
        "loadInstalledYamlData",
        "installed_yaml_data_load",
        "installed_yaml_data_load_status",
    )
    if name == "invalid-defaults-before-write":
        return common
    if name == "recovery-unavailable-defaults":
        return (*common, "installed_yaml_data_load_take_recovery_plan")
    return tuple(
        operation
        for operation in _LOAD_OPERATIONS
        if operation != "installed_yaml_data_load_take_recovery_plan"
    )


INSTALLED_YAML_DATA_COVERAGE_POLICY = FamilyCoveragePolicy(
    "installed-yaml-data",
    tuple(
        CoveragePredicate(
            id="installed-yaml-data." + name,
            capability_id="installed-yaml-data." + action,
            action="installed-yaml-data." + action,
            observation_family=family,
            rust_symbols=_symbols_for_fact(action, name),
            matches=matches,
            runtime_operations=_operations_for_fact(action, name),
        )
        for name, action, family, matches in (
            (
                "updated-selection",
                "inspect",
                "selection",
                partial(_inspect, "updated", ()),
            ),
            (
                "previous-read-only",
                "inspect",
                "selection",
                partial(_inspect, "previous", ()),
            ),
            (
                "bundled-selection",
                "inspect",
                "selection",
                partial(_inspect, "bundled", ()),
            ),
            (
                "parse-fallback",
                "inspect",
                "diagnostics",
                partial(_inspect, "bundled", ("parse",)),
            ),
            (
                "independent-fallback",
                "inspect",
                "diagnostics",
                partial(
                    _inspect, "bundled", ("incompatible_schema", "invalid_role_data")
                ),
            ),
            (
                "invalid-schema-fallback",
                "inspect",
                "diagnostics",
                partial(_inspect, "bundled", ("invalid_schema",)),
            ),
            (
                "no-usable-source",
                "inspect",
                "diagnostics",
                partial(_error, "no_usable_source"),
            ),
            (
                "unsupported-game",
                "inspect",
                "diagnostics",
                partial(_error, "unsupported_game"),
            ),
            ("retained-snapshot", "load", "snapshot", _retained),
            ("legacy-adoption", "load", "durable-effects", _legacy),
            ("canonical-precedence", "load", "durable-effects", _canonical),
            ("recovery-unavailable-defaults", "load", "recovery", _recovery),
            (
                "invalid-defaults-before-write",
                "load",
                "durable-effects",
                partial(_error, "local_ignore_default_invalid"),
            ),
        )
    ),
)
