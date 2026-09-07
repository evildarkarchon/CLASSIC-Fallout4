"""Narrow config-operation facts over explicit loader values and attributed failures."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _base(observation: Mapping[str, Any]) -> bool:
    """Require a complete result/error envelope and a sorted exact-byte inventory."""
    if set(observation) != {"result", "error", "files"}:
        return False
    files = observation["files"]
    return (
        isinstance(files, list)
        and all(
            isinstance(item, Mapping)
            and set(item) == {"path", "content"}
            and item["path"] in {"main.yaml", "game.yaml", "ignore.yaml"}
            and isinstance(item["content"], str)
            for item in files
        )
        and [item["path"] for item in files] == sorted({item["path"] for item in files})
    )


def _values(observation: Mapping[str, Any]) -> bool:
    """Recognize stable parsed Tier-1 fields with both nonempty and ordered values."""
    if not _base(observation) or observation["error"] is not None:
        return False
    result = observation["result"]
    return (
        isinstance(result, Mapping)
        and set(result)
        == {"classicVersion", "xseAcronym", "crashgenName", "gameVersion", "ignoreList"}
        and all(
            isinstance(result[key], str) and result[key]
            for key in result
            if key != "ignoreList"
        )
        and isinstance(result["ignoreList"], list)
        and bool(result["ignoreList"])
        and all(isinstance(value, str) and value for value in result["ignoreList"])
        and {item["path"] for item in observation["files"]}
        == {"main.yaml", "game.yaml", "ignore.yaml"}
    )


def _failure(code: str, role: str, path: str, observation: Mapping[str, Any]) -> bool:
    """Attribute errors from native carriers and forbid repair on missing input."""
    return (
        _base(observation)
        and observation["result"] is None
        and observation["error"] == {"code": code, "role": role, "path": path}
        and {item["path"] for item in observation["files"]}
        == (
            {"main.yaml", "game.yaml"}
            if code == "read"
            else {"main.yaml", "game.yaml", "ignore.yaml"}
        )
    )


_LOAD_OPERATIONS = (
    None,
    "load_explicit_yaml_data",
    "loadExplicitYamlData",
    "explicit_yaml_data_load",
    "explicit_yaml_data_load_status",
)
CONFIG_OPERATIONS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "config-operations",
    (
        CoveragePredicate(
            id="config-operations.tier1-fields",
            capability_id="config-operations.load-explicit",
            action="config-operations.load-explicit",
            observation_family="values",
            rust_symbols=("load_explicit_yaml_data",),
            matches=_values,
            runtime_operations=(
                *_LOAD_OPERATIONS,
                "explicit_yaml_data_load_take_snapshot",
                "explicit_yaml_data_snapshot_yaml_data",
                "yaml_data_classic_version",
                "yaml_data_xse_acronym",
                "yaml_data_crashgen_name_field",
                "yaml_data_game_version",
                "yaml_data_ignore_list",
            ),
        ),
        *(
            CoveragePredicate(
                id="config-operations." + name,
                capability_id="config-operations.load-explicit",
                action="config-operations.load-explicit",
                observation_family=family,
                rust_symbols=("load_explicit_yaml_data",),
                matches=partial(_failure, code, role, path),
                runtime_operations=_LOAD_OPERATIONS,
            )
            for name, code, role, path, family in (
                ("malformed-main", "parse", "main", "main.yaml", "errors"),
                (
                    "missing-ignore-unmodified",
                    "read",
                    "local_ignore",
                    "ignore.yaml",
                    "durable-effects",
                ),
            )
        ),
    ),
)
