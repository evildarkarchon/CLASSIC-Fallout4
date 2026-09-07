"""Observe fixture-seeded Version Registry metadata through actual Python bindings."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def observe_version_registry(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Invoke lookup/matching in a dedicated serial process and restore its cwd.

    Every fixture carries identical YAML because the public registry initializes
    once per process. Unrelated adapter exceptions propagate as execution failures.
    """
    import classic_version_registry

    if set(fixture) != {"operation", "registryYaml", "request"} or fixture[
        "operation"
    ] not in {"lookup", "match"}:
        raise ValueError("unsupported version registry fixture")
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(
        prefix="classic-version-registry-conformance-"
    ) as directory:
        root = Path(directory)
        (root / "CLASSIC Main.yaml").write_bytes(
            fixture["registryYaml"].encode("utf-8")
        )
        try:
            # Isolate first-use YAML discovery from repository/user configuration.
            os.chdir(root)
            observation = _observe(fixture, classic_version_registry.VersionRegistry())
            files = []
            for path in sorted(root.iterdir()):
                if path.is_symlink() or not path.is_file():
                    raise ValueError(
                        "unexpected non-file in version registry workspace"
                    )
                files.append(
                    {"path": path.name, "content": path.read_bytes().decode("utf-8")}
                )
            return {**observation, "files": files}
        finally:
            os.chdir(previous)


def _observe(fixture: Mapping[str, Any], registry: Any) -> dict[str, Any]:
    """Convert native success/error carriers without inferring results from inputs."""
    request = fixture["request"]
    if fixture["operation"] == "lookup":
        info = registry.get_by_id(request["id"])
        result = (
            None
            if info is None
            else {
                "id": info.id,
                "version": info.version,
                "shortName": info.short_name,
                "game": info.game,
                "docsName": info.docs_name,
                "steamId": info.steam_id,
                "isVr": info.is_vr,
            }
        )
        return {"result": result, "error": None}
    try:
        matched = registry.match_version(
            request["version"], request["game"], request["isVr"]
        )
    except ValueError as failure:
        if not str(failure).startswith("Invalid version: Invalid version string:"):
            raise
        return {"result": None, "error": {"code": "invalid_version"}}
    return {
        "result": {
            "matchedId": None
            if matched.version_info is None
            else matched.version_info.id,
            "confidence": str(matched.confidence),
            "message": matched.message,
        },
        "error": None,
    }
