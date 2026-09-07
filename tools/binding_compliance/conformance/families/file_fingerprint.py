"""Fingerprint and encoding observations from public file inspection operations."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def validate_file_fingerprint_pack(
    document: Mapping[str, Any], root: Path
) -> tuple[Path, ...]:
    """Accept only byte inputs and a fixed contained target before execution."""
    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
            or case["action"] != "file-fingerprint.inspect"
        ):
            raise ValueError("fingerprint scenario requires its sole byte fixture")
        path = (
            root / document["fixtureRoot"] / document["fixtures"][reference]
        ).resolve()
        if not path.is_relative_to((root / document["fixtureRoot"]).resolve()):
            raise ValueError("fingerprint fixture escapes root")
        value = json.loads(path.read_text(encoding="utf-8"))
        if set(value) != {"bytes"} or (
            value["bytes"] is not None
            and (
                not isinstance(value["bytes"], list)
                or not all(
                    type(byte) is int and 0 <= byte <= 255 for byte in value["bytes"]
                )
            )
        ):
            raise ValueError("fingerprint input must be bytes or a missing file")
        if not _observation(case["expected"]):
            raise ValueError("invalid fingerprint observation")
        paths.append(path)
    return tuple(paths)


def _observation(value: Mapping[str, Any]) -> bool:
    """Require hash, batch, encoding and observable cache transitions together."""
    if set(value) != {
        "hash",
        "error",
        "encoding",
        "batch",
        "map",
        "cache",
        "reset",
        "cleared",
        "files",
    }:
        return False
    digest = value["hash"]
    if digest is not None and (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        return False
    return (
        value["error"] == ("not_found" if digest is None else None)
        and (
            value["encoding"] is None
            if digest is None
            else value["encoding"] in {"UTF-8", "windows-1252"}
        )
        and all(isinstance(value[key], Mapping) for key in ("batch", "map"))
        and all(
            isinstance(value[key], Mapping)
            and set(value[key]) == {"hits", "misses", "size"}
            and all(
                type(number) is int and number >= 0 for number in value[key].values()
            )
            for key in ("cache", "reset", "cleared")
        )
        and isinstance(value["files"], list)
    )


FILE_FINGERPRINT_COVERAGE_POLICY = FamilyCoveragePolicy(
    "file-fingerprint",
    (
        CoveragePredicate(
            id="hash-and-cache-transitions",
            capability_id="file-fingerprint.inspect",
            action="file-fingerprint.inspect",
            observation_family="file-fingerprint",
            rust_symbols=("FileHasher",),
            matches=_observation,
            runtime_operations=(
                None,
                "hash_file",
                "hash_files_parallel",
                "hash_files_to_map",
                "cache_stats",
                "cache_size",
                "clear_cache",
                "reset_cache_stats",
                "hashFile",
                "hashFilesParallel",
                "getHashCacheStats",
                "clearHashCache",
                "resetHashCacheStats",
            ),
        ),
        CoveragePredicate(
            id="detected-encoding",
            capability_id="file-fingerprint.inspect",
            action="file-fingerprint.inspect",
            observation_family="file-fingerprint",
            rust_symbols=("EncodingDetector",),
            matches=lambda value: _observation(value) and value["encoding"] is not None,
            runtime_operations=(None, "__init__", "detect_encoding", "detectEncoding"),
        ),
    ),
)
