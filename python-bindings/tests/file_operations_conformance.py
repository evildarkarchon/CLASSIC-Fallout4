"""Observe public text I/O in a disposable workspace with exact durable bytes."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _owned_path(root: Path, path: str) -> Path:
    """Reject nonportable fixture paths before performing any native operation."""
    if (
        not path
        or ":" in path
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
    ):
        raise ValueError("file operation needs a contained relative path")
    return root / path


def _files(root: Path) -> list[dict[str, str]]:
    """Re-read every durable file as exact UTF-8 without newline translation."""
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "content": path.read_bytes().decode("utf-8"),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


async def _execute(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Await native binding work while the owning temporary directory remains alive."""
    import classic_file_io

    operation = fixture["operation"]
    if operation not in {"read-text", "write-text"}:
        raise ValueError("unsupported file operation")
    with tempfile.TemporaryDirectory(prefix="classic-file-conformance-") as directory:
        root = Path(directory)
        target = _owned_path(root, fixture["path"])
        for path, content in fixture["files"].items():
            destination = _owned_path(root, path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content.encode("utf-8"))
        result = {
            "operation": operation,
            "path": fixture["path"],
            "content": None,
            "error": None,
            "beforeFiles": _files(root),
            "files": [],
        }
        io = classic_file_io.FileIOCore()
        try:
            if operation == "read-text":
                result["content"] = await io.read_file(str(target))
            else:
                await io.write_file(str(target), fixture["content"])
        except classic_file_io.RustFileIOIOError:
            # The public exception type preserves the Rust I/O category without OS prose.
            result["error"] = "io_error"
        if operation == "read-text":
            alias_content = None
            alias_error = None
            try:
                alias_content = await io.read_file_with_encoding(str(target), "utf-8")
            except classic_file_io.RustFileIOIOError:
                # The explicit-encoding alias must agree with automatic text reads.
                alias_error = "io_error"
            if (alias_content, alias_error) != (result["content"], result["error"]):
                raise ValueError(
                    "public read_file_with_encoding disagrees with read_file"
                )
        result["files"] = _files(root)
        return result


def observe_file_operations(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Run one input-only fixture against the public Python file I/O binding."""
    return asyncio.run(_execute(fixture))
