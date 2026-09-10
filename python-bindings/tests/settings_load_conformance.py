"""Input-only generic settings loader observations through public Python APIs."""

import asyncio
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


def _owned(root: Path, relative: str) -> Path:
    """Contain every authored filename before materialization."""
    if (
        not relative
        or any(char in relative for char in "\\:")
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise ValueError("settings fixture requires a contained relative path")
    return root / relative


def _error(failure: OSError, root: Path, paths: list[str]) -> dict[str, str]:
    """Project only attributed core I/O/parse errors; unexpected failures propagate."""
    message = str(failure)
    for prefix, kind in (
        ("Failed to read file ", "io"),
        ("Failed to parse YAML from ", "yaml-parse"),
    ):
        for relative in paths:
            if message.startswith(prefix + str(_owned(root, relative)) + ": "):
                return {"kind": kind, "path": relative}
    raise failure


async def _observe(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Await public async loaders on their shared runtime and retain cache effects."""
    import classic_settings as settings

    with TemporaryDirectory(prefix="classic-settings-conformance-") as directory:
        root = Path(directory)
        for relative, content in fixture["files"].items():
            path = _owned(root, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
        settings.reset_cache_stats()
        observed = {}
        try:
            for operation in ("sync", "async", "batchSync", "batchAsync"):
                settings.clear_cache()
                batch = operation.startswith("batch")
                relatives = (
                    fixture["request"]["batch"]
                    if batch
                    else [fixture["request"]["single"]]
                )
                paths = [str(_owned(root, item)) for item in relatives]
                keys = paths if batch else ["conformance.single"]
                count, error = None, None
                try:
                    if operation == "sync":
                        count = len(settings.load_settings_sync(keys[0], paths[0]))
                    elif operation == "async":
                        count = len(
                            await settings.load_settings_async(keys[0], paths[0])
                        )
                    elif operation == "batchSync":
                        count = settings.load_batch_sync(paths)
                    else:
                        count = await settings.load_batch_async(paths)
                except OSError as failure:
                    error = _error(failure, root, relatives)
                cached = [settings.is_cached(key) for key in keys]
                cache_state = {
                    "keys": sorted(
                        Path(key).relative_to(root).as_posix() if batch else key
                        for key in settings.cache_keys()
                    ),
                    "size": settings.cache_size(),
                    "stats": _stats(settings.cache_stats()),
                    "invalidated": [settings.invalidate(key) for key in keys],
                    "invalidatedAgain": [settings.invalidate(key) for key in keys],
                    "afterInvalidate": settings.cache_size(),
                }
                settings.reset_cache_stats()
                cache_state["resetStats"] = _stats(settings.cache_stats())
                # Refill entries so clear is checked independently of invalidation.
                for key, path, present in zip(keys, paths, cached, strict=True):
                    if present:
                        settings.load_settings_sync(key, path)
                settings.clear_cache()
                observed[operation] = {
                    "cacheState": cache_state,
                    "count": count,
                    "error": error,
                    "cached": cached,
                    "afterClear": [settings.is_cached(key) for key in keys],
                }
            observed["files"] = {
                path.relative_to(root).as_posix(): path.read_bytes().decode("utf-8")
                for path in root.rglob("*")
                if path.is_file()
            }
            return observed
        finally:
            # Dedicated receipt processes own global cache state; failed calls
            # must not leave entries that contaminate a following scenario.
            settings.clear_cache()


def observe_settings_load(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Bridge the synchronous receipt dispatcher to real asynchronous binding calls."""
    if fixture.get("kind") == "yaml":
        return observe_settings_yaml(fixture)
    return asyncio.run(_observe(fixture))


def _stats(stats: Mapping[str, Any]) -> dict[str, Any]:
    """Retain counters and bounded storage without platform-specific capacity."""
    return {
        "hits": stats["hits"],
        "misses": stats["misses"],
        "hitRateZero": stats["hit_rate"] == 0,
        "size": stats["size"],
        "bounded": stats["capacity"] > 0,
    }


def observe_settings_yaml(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Exercise the public YAML handle, mutation and file-cache lifecycle."""
    import classic_settings as settings

    ops = settings.YamlOperations()
    ops.clear_cache()
    try:
        document = ops.parse_yaml(fixture["content"])
        before = {
            "name": ops.get_string_value(document, "name", "fallback"),
            "missing": ops.get_string_value(document, "absent", "fallback"),
            "items": ops.get_vec_value(document, "items"),
            "mapping": ops.get_hashmap_value(document, "mapping"),
        }
        for key in fixture["updateOrder"]:
            document = ops.set_setting(document, key, fixture["updates"][key])
        dumped = ops.dump_yaml(document)
        round_trip = ops.parse_yaml(dumped)
        after = {key: ops.get_setting(round_trip, key) for key in fixture["updates"]}
        with TemporaryDirectory(prefix="classic-yaml-conformance-") as directory:
            path = Path(directory) / "saved.yaml"
            ops.save_yaml_file(path, document)
            initial = ops.get_cache_stats()
            loaded = ops.load_yaml_file(path)
            ops.load_yaml_file(path)
            stats = ops.get_cache_stats()
            persisted = {
                key: ops.get_setting(loaded, key) for key in fixture["updates"]
            }
            files = {
                item.name: item.read_bytes().decode("utf-8")
                for item in Path(directory).iterdir()
                if item.is_file()
            }
            ops.clear_cache()
            return {
                "before": before,
                "after": after,
                "persisted": persisted,
                "files": files,
                "cache": {
                    "hits": stats["hits"] - initial["hits"],
                    "misses": stats["misses"] - initial["misses"],
                    "size": stats["size"],
                    "afterClear": ops.get_cache_stats()["size"],
                },
            }
    finally:
        # The dedicated adapter owns process cache state even after native failures.
        ops.clear_cache()
