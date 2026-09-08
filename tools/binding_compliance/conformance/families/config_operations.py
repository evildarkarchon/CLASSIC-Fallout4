"""Narrow config-operation facts over explicit loader values and attributed failures."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .config_yaml_values import YAML_VALUES_PREDICATE


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
            and item["path"]
            in {
                "main.yaml",
                "game.yaml",
                "ignore.yaml",
                "CLASSIC Main.yaml",
                "local.yaml",
                "CLASSIC Settings.yaml",
            }
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
        == {
            "classicVersion",
            "xseAcronym",
            "crashgenName",
            "gameVersion",
            "ignoreList",
            "game",
            "gameRole",
            "identities",
            "yamlValues",
        }
        and result["game"] == "Fallout4"
        and all(
            isinstance(result[key], str) and result[key]
            for key in result
            if key not in {"ignoreList", "identities", "yamlValues"}
        )
        and isinstance(result["ignoreList"], list)
        and bool(result["ignoreList"])
        and all(isinstance(value, str) and value for value in result["ignoreList"])
        and {item["path"] for item in observation["files"]}
        == {"main.yaml", "game.yaml", "ignore.yaml"}
    )


def _identities(observation: Mapping[str, Any]) -> bool:
    """Authenticate native retained identities against independently observed file bytes."""
    if not _values(observation) or observation["result"]["gameRole"] != "Fallout4":
        return False
    return observation["result"]["identities"] == {
        item["path"]: {
            "sha256": hashlib.sha256(item["content"].encode("utf-8")).hexdigest(),
            "byteLen": len(item["content"].encode("utf-8")),
        }
        for item in observation["files"]
    }


def _main_version(observation: Mapping[str, Any]) -> bool:
    """Require a typed successful bundled version and the unchanged source inventory."""
    result = observation.get("result")
    return (
        _base(observation)
        and observation["error"] is None
        and isinstance(result, Mapping)
        and set(result) == {"version"}
        and isinstance(result["version"], str)
        and bool(result["version"].strip())
        and {item["path"] for item in observation["files"]} == {"CLASSIC Main.yaml"}
    )


def _persisted(observation: Mapping[str, Any]) -> bool:
    """Require successful void persistence and the complete owned byte inventory."""
    return (
        _base(observation)
        and observation["result"] is None
        and observation["error"] is None
        and {file["path"] for file in observation["files"]}
        <= {"local.yaml", "CLASSIC Settings.yaml"}
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


def _clear_callable(observation: Mapping[str, Any]) -> bool:
    """Prove only repeated void calls and unchanged disk bytes, not cache eviction."""
    return observation == {
        "result": [None, None],
        "error": None,
        "files": [{"path": "main.yaml", "content": "sentinel: untouched\n"}],
    }


CONFIG_OPERATIONS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "config-operations",
    (
        CoveragePredicate(
            "config-operations.clear-cache",
            "config-operations.clear-cache",
            "config-operations.clear-cache",
            "values",
            ("clear_global_yaml_cache",),
            _clear_callable,
            runtime_operations=("clear_yaml_cache",),
        ),
        YAML_VALUES_PREDICATE,
        CoveragePredicate(
            "config-operations.persist-local",
            "config-operations.persist-local",
            "config-operations.persist-local",
            "durable-effects",
            ("persist_game_local_paths",),
            _persisted,
            runtime_operations=(
                None,
                "persist_game_local_paths",
                "persistGameLocalPaths",
                "save_local_yaml_paths",
            ),
        ),
        CoveragePredicate(
            id="config-operations.main-version",
            capability_id="config-operations.main-version",
            action="config-operations.main-version",
            observation_family="values",
            rust_symbols=("load_main_yaml_version_with_bundled_dir",),
            matches=_main_version,
            runtime_operations=(None, "load_main_yaml_version", "loadMainYamlVersion"),
        ),
        CoveragePredicate(
            id="config-operations.snapshot-identities",
            capability_id="config-operations.load-explicit",
            action="config-operations.load-explicit",
            observation_family="values",
            rust_symbols=(
                "ExplicitYamlDataSnapshot",
                "YamlDataContentIdentity",
                "GameDataRole",
            ),
            matches=_identities,
            runtime_operations=(
                None,
                "explicit_yaml_data_snapshot_game_identity",
                "explicit_yaml_data_snapshot_game_role",
                "explicit_yaml_data_snapshot_ignore_identity",
                "explicit_yaml_data_snapshot_main_identity",
            ),
        ),
        CoveragePredicate(
            id="config-operations.snapshot-game",
            capability_id="config-operations.load-explicit",
            action="config-operations.load-explicit",
            observation_family="values",
            rust_symbols=("ExplicitYamlDataSnapshot",),
            matches=_values,
            runtime_operations=("explicit_yaml_data_snapshot_game",),
        ),
        CoveragePredicate(
            id="config-operations.tier1-fields",
            capability_id="config-operations.load-explicit",
            action="config-operations.load-explicit",
            observation_family="values",
            rust_symbols=("load_explicit_yaml_data", "ExplicitYamlDataSnapshot"),
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
