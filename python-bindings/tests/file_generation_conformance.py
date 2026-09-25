"""Observe relative-path generation inside a process-owned temporary directory."""

import asyncio
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from file_operations_conformance import _files, _owned_path


async def _observe(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Await every native generator before restoring its process-relative working root."""
    import classic_file_io as native

    if fixture["game"] not in {"Fallout4", "Fallout4VR"}:
        raise ValueError("generator fixture game must have a contained filename")
    with tempfile.TemporaryDirectory(prefix="classic-generation-") as directory:
        root = Path(directory)
        for path, content in fixture["files"].items():
            target = _owned_path(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))
        previous = Path.cwd()
        # This dedicated receipt process runs scenarios serially; all futures
        # finish inside this scope because native generation uses relative paths.
        os.chdir(root)
        try:
            config = native.FileGeneratorConfig(
                fixture["ignore"], fixture["local"], fixture["game"]
            )
            generator = native.FileGenerator(config)
            copied = generator.config()
            if (
                    copied.ignore_file_content,
                    copied.local_yaml_content,
                    copied.game_name,
            ) != (
                    config.ignore_file_content,
                    config.local_yaml_content,
                    config.game_name,
            ):
                raise ValueError("generator config accessor changed constructor state")
            result = {
                "paths": [
                    generator.ignore_file_path().as_posix(),
                    generator.local_yaml_path().as_posix(),
                ],
                "before": _files(root),
                "generated": list(await generator.generate_all_files_async()),
            }
            result["existing"] = [
                await generator.generate_ignore_file_async(),
                await generator.generate_local_yaml_async(),
            ]
            result["standalone"] = [
                await native.generate_ignore_file_async("must not replace"),
                await native.generate_local_yaml_async(
                    "must not replace", fixture["game"]
                ),
            ]
            result["files"] = _files(root)
            return result
        finally:
            os.chdir(previous)


def observe_file_generation(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Run one input-only generation scenario through the public native module."""
    return asyncio.run(_observe(fixture))
