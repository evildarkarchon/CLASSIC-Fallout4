"""Inspect temporary bytes through public hashing and encoding bindings."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any


def observe_file_fingerprint(fixture: dict[str, Any]) -> dict[str, Any]:
    """Return real cache effects and file bytes, cleaning global state on exit."""
    import classic_file_io as api

    hasher = api.FileHasher

    def stats() -> dict[str, int]:
        """Keep deterministic counters and verify the public size accessor."""
        value = hasher.cache_stats()
        size = hasher.cache_size()
        if size != value["size"]:
            raise ValueError("cache size accessor disagrees with statistics")
        return {key: value[key] for key in ("hits", "misses", "size")}

    with tempfile.TemporaryDirectory(prefix="classic-fingerprint-") as directory:
        root = Path(directory)
        target = root / "payload.bin"
        if fixture["bytes"] is not None:
            target.write_bytes(bytes(fixture["bytes"]))
        hasher.clear_cache()
        hasher.reset_cache_stats()
        try:
            digest, error = None, None
            for _ in range(2):
                try:
                    digest = hasher.hash_file(str(target))
                except RuntimeError as failure:
                    # FileHasher uses the legacy RuntimeError envelope, preserving the core prefix.
                    if not str(failure).startswith(
                            "Hash calculation failed: File not found: "
                    ):
                        raise
                    error = "not_found"
            cache = stats()
            paths = [str(target), str(root / "absent.bin")]
            batch = {
                Path(path).name: value
                for path, value in hasher.hash_files_parallel(paths).items()
                if value is not None
            }
            mapped = {
                Path(path).name: value
                for path, value in hasher.hash_files_to_map(paths).items()
            }
            hasher.reset_cache_stats()
            reset = stats()
            hasher.clear_cache()
            return {
                "hash": digest,
                "error": error,
                "encoding": api.EncodingDetector().detect_encoding(target.read_bytes())
                if target.exists()
                else None,
                "batch": batch,
                "map": mapped,
                "cache": cache,
                "reset": reset,
                "cleared": stats(),
                "files": [
                    {"path": path.name, "bytes": list(path.read_bytes())}
                    for path in sorted(root.iterdir())
                ],
            }
        finally:
            # Each scenario owns the global hash cache for its isolated process.
            hasher.clear_cache()
            hasher.reset_cache_stats()
