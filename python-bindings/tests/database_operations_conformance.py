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
