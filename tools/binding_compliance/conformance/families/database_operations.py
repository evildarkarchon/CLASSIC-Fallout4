"""Narrow DatabasePool receipts over public lookups, lifecycle, and immutable files."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _matches(kind: str, observation: Mapping[str, Any]) -> bool:
    """Require the complete lifecycle and distinguish empty hits from genuine misses."""
    if set(observation) != {
        "table",
        "initialAvailable",
        "available",
        "error",
        "single",
        "batch",
        "cleared",
        "afterClear",
        "closedAvailable",
        "closedCache",
        "files",
    }:
        return False
    if (
        observation["table"] != "Fallout4"
        or observation["initialAvailable"] is not False
        or observation["closedAvailable"] is not False
    ):
        return False
    if observation["afterClear"] != 0 or observation["closedCache"] != 0:
        return False
    files = observation["files"]
    if not isinstance(files, list) or any(
        not isinstance(item, Mapping)
        or set(item) != {"path", "hex"}
        or item["path"] != "formids.db"
        or not isinstance(item["hex"], str)
        or not item["hex"]
        for item in files
    ):
        return False
    if kind == "populated":
        expected = ["Alpha café", "", None, "Alpha café"]
        return (
            observation["error"] is None
            and observation["available"] is True
            and observation["single"] == expected
            and observation["batch"] == expected
            and observation["cleared"] == 2
            and len(files) == 1
            and files[0]["hex"].startswith("53514c69746520666f726d6174203300")
        )
    return (
        observation["available"] is False
        and observation["single"] == []
        and observation["batch"] == []
        and observation["cleared"] == 0
        and (
            (kind == "missing" and observation["error"] is None and files == [])
            or (
                kind == "invalid"
                and observation["error"] == {"code": "open", "path": "formids.db"}
                and len(files) == 1
                and files[0]["hex"] == b"not a SQLite database\n".hex()
            )
        )
    )


_OPERATIONS = (
    None,
    "new",
    "__init__",
    "initialize",
    "py_initialize",
    "is_available",
    "isAvailable",
    "get_game_table",
    "getGameTable",
    "clear_cache",
    "clearCache",
    "close",
    "py_close",
    "db_pool_new",
    "db_pool_initialize",
    "db_pool_is_available",
    "db_pool_game_table",
    "db_pool_clear_cache",
    "db_pool_close",
)
DATABASE_OPERATIONS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "database-operations",
    tuple(
        CoveragePredicate(
            id=f"database-operations.{kind}",
            capability_id="database-operations.pool",
            action="database-operations.pool",
            observation_family=family,
            rust_symbols=(
                "DatabasePool",
                "initialize",
                "get_entry",
                "get_entries_batch",
                "is_available",
                "get_game_table",
                "clear_cache",
                "close",
            ),
            matches=partial(_matches, kind),
            runtime_operations=_OPERATIONS
            + (
                (
                    "get_entry",
                    "py_get_entry",
                    "getEntry",
                    "get_entries_batch",
                    "py_get_entries_batch",
                    "getEntriesBatch",
                    "db_pool_get_entry",
                    "db_pool_get_entry_typed",
                    "db_pool_get_entries_batch",
                    "db_pool_get_entries_batch_typed",
                )
                if kind == "populated"
                else ()
            ),
        )
        for kind, family in (
            ("populated", "values"),
            ("missing", "durable-effects"),
            ("invalid", "errors"),
        )
    ),
)
