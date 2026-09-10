"""Execute owned DatabasePool fixtures through the real Python extension."""

from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


async def _execute(fixture: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """Run pool operations and close native handles before observing durable bytes."""
    import classic_database

    pool = classic_database.DatabasePool(
        max_connections=1, cache_ttl_seconds=300, game_table="Fallout4"
    )
    for getter, constant in (
        (classic_database.get_default_cache_ttl, classic_database.DEFAULT_CACHE_TTL),
        (classic_database.get_batch_cache_ttl, classic_database.BATCH_CACHE_TTL),
        (classic_database.get_max_cache_ttl, classic_database.MAX_CACHE_TTL),
        (
            classic_database.get_default_query_cache_capacity,
            classic_database.DEFAULT_QUERY_CACHE_CAPACITY,
        ),
        (
            classic_database.get_default_cache_cleanup_threshold,
            classic_database.DEFAULT_CACHE_CLEANUP_THRESHOLD,
        ),
        (
            classic_database.get_default_cache_cleanup_interval,
            classic_database.DEFAULT_CACHE_CLEANUP_INTERVAL,
        ),
    ):
        if getter() != constant:
            raise ValueError("cache helper disagrees with its exported constant")
    pool.set_game_table("ConformanceTemporaryTable")
    if pool.get_game_table() != "ConformanceTemporaryTable":
        raise ValueError("game-table setter failed to update the native owner")
    pool.set_game_table("Fallout4")
    for setter, getter, value in (
        (pool.set_cache_capacity, pool.get_cache_capacity, 64),
        (pool.set_cache_cleanup_threshold, pool.get_cache_cleanup_threshold, 20),
        (pool.set_cache_cleanup_interval, pool.get_cache_cleanup_interval, 60),
        (pool.set_max_connections, pool.get_max_connections, 2),
    ):
        setter(value)
        if getter() != value:
            raise ValueError("pool configuration setter/getter mismatch")
    pool.recalculate_max_connections()
    if not pool.get_max_connections() or pool.get_max_connections() < 1:
        raise ValueError("automatic connection budget is not positive")
    # Restore the controlled budget before opening handles; resource-dependent
    # auto sizing must not change the fixture's deterministic query lifecycle.
    pool.set_max_connections(1)
    await pool.rebalance_connections()
    # Zero TTL proves mutation through repeated lookups producing no cache hits,
    # without sleeps or reliance on wall-clock precision.
    pool.set_cache_ttl(0)
    result: dict[str, Any] = {
        "table": pool.get_game_table(),
        "initialAvailable": pool.is_available(),
        "error": None,
        "single": [],
        "batch": [],
    }
    try:
        try:
            await pool.initialize([str(root / "formids.db")])
        except classic_database.RustDatabaseIOError as failure:
            # Attribute only the native open carrier; unrelated failures must fail the runner.
            if not str(failure).startswith("Failed to open database:") or json.dumps(
                str(root / "formids.db")
            )[1:-1] not in str(failure):
                raise
            result["error"] = {"code": "open", "path": "formids.db"}
        result["available"] = pool.is_available()
        if result["error"] is None:
            pairs = [tuple(pair) for pair in fixture["queries"]]
            result["single"] = [
                await pool.get_entry(formid, plugin) for formid, plugin in pairs
            ]
            batch = await pool.get_entries_batch(pairs)
            result["batch"] = [
                batch.get(f"{formid}:{plugin}") for formid, plugin in pairs
            ]
        stats = pool.get_stats()
        if stats["configured_connection_budget"] != 1 or stats[
            "active_pool_count"
        ] != int(pool.is_available()):
            raise ValueError("pool statistics disagree with native lifecycle")
        if not all(type(value) is int and value >= 0 for value in stats.values()):
            raise ValueError("pool statistics contain invalid counters")
        if stats["cache_hits"] != 0:
            raise ValueError("zero TTL reused an expired cache entry")
        await pool.optimize()
        result["cleared"] = pool.clear_cache(False)
        result["afterClear"] = pool.clear_cache(False)
    finally:
        # Close before directory cleanup so Windows never removes a live SQLite file.
        await pool.close()
    result["closedAvailable"] = pool.is_available()
    result["closedCache"] = pool.clear_cache(False)
    result["files"] = [
        {"path": path.relative_to(root).as_posix(), "hex": path.read_bytes().hex()}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    return result


def observe_database_operations(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize input-only SQLite bytes and return public pool observations."""
    if fixture == {"operation": "cache-defaults"}:
        import classic_database as database

        result = {
            "defaultTtl": database.get_default_cache_ttl(),
            "batchTtl": database.get_batch_cache_ttl(),
            "maximumTtl": database.get_max_cache_ttl(),
            "capacity": database.get_default_query_cache_capacity(),
            "cleanupThreshold": database.get_default_cache_cleanup_threshold(),
            "cleanupInterval": database.get_default_cache_cleanup_interval(),
        }
        constants = {
            "defaultTtl": database.DEFAULT_CACHE_TTL,
            "batchTtl": database.BATCH_CACHE_TTL,
            "maximumTtl": database.MAX_CACHE_TTL,
            "capacity": database.DEFAULT_QUERY_CACHE_CAPACITY,
            "cleanupThreshold": database.DEFAULT_CACHE_CLEANUP_THRESHOLD,
            "cleanupInterval": database.DEFAULT_CACHE_CLEANUP_INTERVAL,
        }
        if result != constants:
            raise ValueError("cache getter values disagree with exported constants")
        return result
    if (
        set(fixture) != {"operation", "databaseHex", "queries"}
        or fixture["operation"] != "pool"
    ):
        raise ValueError("unsupported database operation fixture")
    if not isinstance(fixture["queries"], list) or any(
        not isinstance(pair, list)
        or len(pair) != 2
        or not all(isinstance(value, str) for value in pair)
        for pair in fixture["queries"]
    ):
        raise ValueError("database queries require string pairs")
    with tempfile.TemporaryDirectory(
        prefix="classic-database-conformance-"
    ) as directory:
        root = Path(directory)
        content = fixture["databaseHex"]
        if content is not None:
            if (
                not isinstance(content, str)
                or len(content) % 2
                or any(c not in "0123456789abcdef" for c in content)
            ):
                raise ValueError("database bytes require lowercase hex")
            (root / "formids.db").write_bytes(bytes.fromhex(content))
        return asyncio.run(_execute(fixture, root))
