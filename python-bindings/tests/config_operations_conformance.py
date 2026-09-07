"""Observe explicit config loading through real Python bindings and owned files."""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def observe_config_operations(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Load only caller-selected files and re-read all durable bytes after execution.

    Domain errors retain their structured role and path. Unexpected adapter errors
    propagate, and temporary storage is removed even when native execution fails.
    """
    import classic_config

    if fixture.get("operation") != "load-explicit" or set(fixture) != {
        "operation",
        "files",
    }:
        raise ValueError("unsupported config operation fixture")
    with tempfile.TemporaryDirectory(prefix="classic-config-conformance-") as directory:
        root = Path(directory)
        for name, content in fixture["files"].items():
            if name not in {"main.yaml", "game.yaml", "ignore.yaml"} or not isinstance(
                content, str
            ):
                raise ValueError(
                    "config fixture requires owned YAML filenames and UTF-8 text"
                )
            (root / name).write_bytes(content.encode("utf-8"))
        result = error = None
        try:
            snapshot = classic_config.load_explicit_yaml_data(
                classic_config.ExplicitYamlDataPaths(
                    root / "main.yaml", root / "game.yaml", root / "ignore.yaml"
                ),
                classic_config.ExplicitYamlDataGame.FALLOUT4,
                "auto",
            )
        except classic_config.ExplicitYamlDataLoadError as failure:
            error = {
                "code": failure.code,
                "role": failure.yaml_role,
                "path": None
                if failure.path is None
                else Path(failure.path).relative_to(root).as_posix(),
            }
        else:
            data = snapshot.yaml_data
            result = {
                "classicVersion": data.classic_version,
                "xseAcronym": data.xse_acronym,
                "crashgenName": data.crashgen_name,
                "gameVersion": data.game_version,
                "ignoreList": list(data.ignore_list),
            }
        files = [
            {
                "path": path.relative_to(root).as_posix(),
                "content": path.read_bytes().decode("utf-8"),
            }
            for path in sorted(root.rglob("*"))
            if path.is_file()
        ]
        return {"result": result, "error": error, "files": files}
