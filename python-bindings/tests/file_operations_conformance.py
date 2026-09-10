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


async def _check_read_variants(
    io: Any, target: Path, result: Mapping[str, Any]
) -> None:
    """Require each public read variant to agree before a text receipt can pass.

    Fixture expectations never enter this helper. Comparisons use the primary
    native result and independently re-read durable bytes; any alias drift
    aborts receipt production rather than donating the primary call's credit.
    """
    import classic_file_io

    content = result["content"]
    error = result["error"]
    for operation in (
        "read_bytes",
        "read_lines",
        "read_file_mmap",
        "stream_lines",
        "stream_lines_sync",
    ):
        actual = None
        actual_error = None
        try:
            if operation == "stream_lines_sync":
                actual = list(io.stream_lines_sync(str(target)))
            else:
                actual = await getattr(io, operation)(str(target))
                if operation == "stream_lines":
                    actual = [line async for line in actual]
                elif operation == "read_bytes":
                    actual = bytes(actual)
        except classic_file_io.RustFileIOIOError:
            # Missing files must preserve the same native I/O error category.
            actual_error = "io_error"
        expected = (
            None
            if content is None
            else (
                content.encode("utf-8")
                if operation == "read_bytes"
                else content
                if operation == "read_file_mmap"
                else content.splitlines()
            )
        )
        if (actual, actual_error) != (expected, error):
            raise ValueError(f"public {operation} disagrees with native text read")
    exists = io.file_exists(str(target))
    size = io.get_file_size(str(target))
    info = io.get_file_info(str(target))
    if exists != target.is_file() or size != (target.stat().st_size if exists else -1):
        raise ValueError("public metadata disagrees with durable file")
    if exists:
        if info.get("size") != size or "error" in info:
            raise ValueError("public file information disagrees with durable file")
    elif not isinstance(info.get("error"), str) or not info["error"]:
        raise ValueError("missing file information lacks an error")
    batch = await io.py_read_multiple_files([str(target)])
    if batch != {str(target): content or ""}:
        raise ValueError("public batch read disagrees with native text read")
    walked = {
        Path(path) for path in io.py_walk_directory(str(target.parent), None, None)
    }
    if walked != {path for path in target.parent.rglob("*") if path.is_file()}:
        raise ValueError("public directory walk disagrees with durable files")
    if content is not None:
        # A changed file after cache invalidation must not return cached bytes.
        target.write_bytes(b"fresh after invalidation\n")
        io.clear_cache()
        if await io.read_file(str(target)) != "fresh after invalidation\n":
            raise ValueError("clear_cache preserved stale file content")
        target.write_bytes(content.encode("utf-8"))
        io.clear_cache()


async def _check_write_variants(io: Any, target: Path, content: str) -> None:
    """Execute successful public writers and verify their actual durable bytes."""
    await io.write_bytes(str(target), content.encode("utf-8"))
    if target.read_bytes() != content.encode("utf-8"):
        raise ValueError("public byte writer changed durable content")
    if content.endswith("\n"):
        await io.write_lines(str(target), content.splitlines())
        if target.read_bytes() != content.encode("utf-8"):
            raise ValueError("public line writer changed durable content")
    # Append starts from empty bytes so the complete payload must be appended.
    target.write_bytes(b"")
    await io.append_file(str(target), content)
    if target.read_bytes() != content.encode("utf-8"):
        raise ValueError("public append writer changed durable content")
    await io.py_write_multiple_files({str(target): content})
    if target.read_bytes() != content.encode("utf-8"):
        raise ValueError("public batch writer changed durable content")


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
            await _check_read_variants(io, target, result)
            result["similarity"] = _similarity_observation()
        elif result["error"] is None:
            await _check_write_variants(io, target, fixture["content"])
        result["files"] = _files(root)
        return result


def _similarity_observation() -> list[str]:
    """Compare equal, disjoint and partially matching lines through both public APIs."""
    import classic_file_io

    with tempfile.TemporaryDirectory(prefix="classic-similarity-") as directory:
        root = Path(directory)
        left, right = root / "left.txt", root / "right.txt"
        first = "alpha\nbeta\n"
        left.write_bytes(first.encode())
        results = []
        for second in (first, "gamma\ndelta\n", "alpha\ngamma\n"):
            right.write_bytes(second.encode())
            result = classic_file_io.calculate_similarity(str(left), str(right))
            if classic_file_io.similarity_ratio(first, second) != result:
                raise ValueError(
                    "text similarity disagrees with native file similarity"
                )
            if (
                left.read_bytes() != first.encode()
                or right.read_bytes() != second.encode()
            ):
                raise ValueError("similarity changed source bytes")
            results.append(f"{result:.6f}")
        return results


def observe_file_operations(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Run one input-only fixture against the public Python file I/O binding."""
    return asyncio.run(_execute(fixture))
