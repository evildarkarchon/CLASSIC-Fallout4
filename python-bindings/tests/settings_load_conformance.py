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
                settings.clear_cache()
                observed[operation] = {
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
    return asyncio.run(_observe(fixture))
