"""Observe explicit config loading through real Python bindings and owned files."""

from __future__ import annotations

import os
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
    from config_yaml_values_conformance import yaml_values

    if fixture.get("operation") not in {
        "load-explicit",
        "main-version",
        "persist-local",
        "clear-cache",
    } or set(fixture) != {
        "operation",
        "files",
    } | (
            {"gameRoot", "docsRoot"}
            if fixture.get("operation") == "persist-local"
            else set()
    ):
        raise ValueError("unsupported config operation fixture")
    with tempfile.TemporaryDirectory(prefix="classic-config-conformance-") as directory:
        root = Path(directory)
        for name, content in fixture["files"].items():
            if name not in {
                "main.yaml",
                "game.yaml",
                "ignore.yaml",
                "CLASSIC Main.yaml",
                "local.yaml",
                "CLASSIC Settings.yaml",
            } or not isinstance(content, str):
                raise ValueError(
                    "config fixture requires owned YAML filenames and UTF-8 text"
                )
            (root / name).write_bytes(content.encode("utf-8"))
        if fixture["operation"] == "clear-cache":
            # The extension owns its own Rust statics. This boundary proves the
            # public void return and read-only disk contract, not hidden eviction.
            first = classic_config.clear_yaml_cache()
            second = classic_config.clear_yaml_cache()
            return {
                "result": [first, second],
                "error": None,
                "files": [
                    {"path": path.name, "content": path.read_bytes().decode("utf-8")}
                    for path in sorted(root.iterdir())
                    if path.is_file()
                ],
            }
        if fixture["operation"] == "persist-local":
            classic_config.persist_game_local_paths(
                root / "local.yaml", fixture["gameRoot"], fixture["docsRoot"]
            )
            return {
                "result": None,
                "error": None,
                "files": [
                    {"path": path.name, "content": path.read_bytes().decode("utf-8")}
                    for path in sorted(root.iterdir())
                    if path.is_file()
                ],
            }
        if fixture["operation"] == "main-version":
            # The public loader resolves process cache roots; cases run sequentially.
            previous = {
                name: os.environ.get(name)
                for name in ("LOCALAPPDATA", "XDG_CACHE_HOME")
            }
            try:
                for name in previous:
                    os.environ[name] = str(root / "isolated-cache")
                version = classic_config.load_main_yaml_version(str(root))
            finally:
                for name, value in previous.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value
            return {
                "result": {"version": version},
                "error": None,
                "files": [
                    {"path": path.name, "content": path.read_bytes().decode("utf-8")}
                    for path in sorted(root.iterdir())
                    if path.is_file()
                ],
            }
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
            if snapshot.game != classic_config.ExplicitYamlDataGame.FALLOUT4:
                raise ValueError("explicit snapshot returned an unexpected game")
            data = snapshot.yaml_data
            values = yaml_values(data)
            from_content = classic_config.YamlData.from_yaml_content(
                fixture["files"]["main.yaml"],
                fixture["files"]["game.yaml"],
                fixture["files"]["ignore.yaml"],
                "Fallout4",
                "auto",
            )
            if yaml_values(from_content) != values:
                raise ValueError(
                    "content constructor differs from retained explicit data"
                )
            if (
                    repr(data)
                    != f"YamlData(game={data.crashgen_name.split('_')[0]}, version={data.classic_version})"
            ):
                raise ValueError(
                    "public YAML representation lost its identifying fields"
                )
            result = {
                "yamlValues": values,
                "game": "Fallout4",
                "gameRole": snapshot.game_data_role,
                "identities": {
                    name: {"sha256": value.sha256, "byteLen": value.byte_len}
                    for name, value in (
                        ("main.yaml", snapshot.main_identity),
                        ("game.yaml", snapshot.game_identity),
                        ("ignore.yaml", snapshot.ignore_identity),
                    )
                },
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
