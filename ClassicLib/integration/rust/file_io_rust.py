"""Rust-accelerated FileIOCore wrapper.

Thin delegation layer: converts Python types to Rust-compatible types,
calls Rust, converts return values. Falls back to Python when Rust unavailable.

Translates Rust-specific exceptions (RustFileIOIOError, etc.) into standard
Python exceptions (FileNotFoundError, OSError) so callers don't need to
know about the Rust backend.
"""

from __future__ import annotations

import errno
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

from ClassicLib.integration.exceptions import RustError, RustIOError, RustParseError
from ClassicLib.integration.factory import detect_component

logger = logging.getLogger(__name__)


def _translate_rust_io_error(e: Exception, path: str | Path) -> Exception:
    """Translate Rust file I/O exceptions to standard Python exceptions.

    Inspects the error message to determine the appropriate Python exception
    type, preserving the original message for debugging.

    Args:
        e: The Rust exception to translate.
        path: The file path involved, for constructing Python exceptions.

    Returns:
        A standard Python exception (FileNotFoundError, PermissionError, or OSError).

    """
    msg = str(e)
    if "not found" in msg.lower() or "os error 2" in msg.lower():
        return FileNotFoundError(errno.ENOENT, msg, str(path))
    if "permission denied" in msg.lower() or "os error 5" in msg.lower():
        return PermissionError(errno.EACCES, msg, str(path))
    return OSError(msg)


RUST_AVAILABLE, _rust_io = detect_component("classic_file_io", "FileIOCore")
_RustFileIOIOError: type[Exception] | None = None
if RUST_AVAILABLE:
    logger.info("Rust FileIOCore available")
    try:
        import classic_file_io as _cfi

        _RustFileIOIOError = _cfi.RustFileIOIOError
    except (ImportError, AttributeError):
        pass


class FileIOCore:
    """Rust-accelerated file I/O with Python fallback.

    Each method: convert args -> call Rust -> convert return.
    Falls back to Python implementation when Rust is unavailable.
    """

    def __init__(self, encoding: str = "utf-8", errors: str = "ignore") -> None:
        """Initialize with encoding preferences and Rust/Python backend."""
        self.default_encoding = encoding
        self.default_errors = errors
        self._rust_core = None
        self._python_core = None
        if RUST_AVAILABLE and _rust_io:
            try:
                self._rust_core = _rust_io(encoding=encoding, errors=errors, cache_size=100, max_concurrent_io=50)
            except (RustError, OSError, ImportError) as e:
                logger.warning(f"Failed to initialize Rust FileIOCore: {e}")
        if not self._rust_core:
            from ClassicLib.io.files.core import FileIOCore as PythonFileIOCore

            self._python_core = PythonFileIOCore(encoding, errors)

    @property
    def is_rust_accelerated(self) -> bool:
        """Check if Rust acceleration is active."""
        return self._rust_core is not None

    async def read_file(self, path: Path | str) -> str:
        """Read file contents as string."""
        if self._rust_core:
            try:
                return await self._rust_core.read_file(str(path))
            except Exception as e:
                if _RustFileIOIOError and isinstance(e, _RustFileIOIOError):
                    raise _translate_rust_io_error(e, path) from e
                raise
        return await self._python_core.read_file(Path(path))

    async def read_lines(self, path: Path | str) -> list[str]:
        """Read file as list of lines."""
        if self._rust_core:
            try:
                return await self._rust_core.read_lines(str(path))
            except Exception as e:
                if _RustFileIOIOError and isinstance(e, _RustFileIOIOError):
                    raise _translate_rust_io_error(e, path) from e
                raise
        return await self._python_core.read_lines(Path(path))

    async def stream_lines(self, path: Path | str) -> AsyncIterator[str]:
        """Stream lines from file asynchronously."""
        if self._rust_core:
            streamer = await self._rust_core.stream_lines(str(path))
            async for line in streamer:
                yield line
            return
        async for line in self._python_core.stream_lines(Path(path)):
            yield line

    def stream_lines_sync(self, path: Path | str) -> Iterator[str]:
        """Stream lines from file synchronously."""
        if self._rust_core:
            yield from self._rust_core.stream_lines_sync(str(path))
            return
        from ClassicLib.Utils.file_utils import open_file_with_encoding

        with open_file_with_encoding(Path(path)) as f:
            for line in f:
                yield line.rstrip("\n")

    async def read_bytes(self, path: Path | str) -> bytes:
        """Read file as raw bytes."""
        if self._rust_core:
            try:
                return await self._rust_core.read_bytes(str(path))
            except Exception as e:
                if _RustFileIOIOError and isinstance(e, _RustFileIOIOError):
                    raise _translate_rust_io_error(e, path) from e
                raise
        return await self._python_core.read_bytes(Path(path))

    async def read_file_mmap(self, path: Path | str) -> str:
        """Read file using memory mapping (optimized for large files)."""
        if self._rust_core:
            return await self._rust_core.read_file_mmap(str(path))
        return await self.read_file(path)

    async def read_file_with_encoding(self, path: Path | str, encoding: str) -> str:
        """Read file with specific encoding."""
        if self._rust_core:
            return await self._rust_core.read_file_with_encoding(str(path), encoding)
        return Path(path).read_text(encoding=encoding, errors=self.default_errors)  # noqa: ASYNC240

    async def write_file(self, path: Path | str, content: str) -> None:
        """Write string content to file."""
        if self._rust_core:
            await self._rust_core.write_file(str(path), content)
            return
        await self._python_core.write_file(Path(path), content)

    async def write_lines(self, path: Path | str, lines: list[str]) -> None:
        """Write list of lines to file."""
        if self._rust_core:
            await self._rust_core.write_lines(str(path), lines)
            return
        await self._python_core.write_lines(Path(path), lines)

    async def write_bytes(self, path: Path | str, content: bytes) -> None:
        """Write raw bytes to file."""
        if self._rust_core:
            await self._rust_core.write_bytes(str(path), content)
            return
        await self._python_core.write_bytes(Path(path), content)

    async def append_file(self, path: Path | str, content: str) -> None:
        """Append content to file."""
        if self._rust_core:
            await self._rust_core.append_file(str(path), content)
            return
        await self._python_core.append_file(Path(path), content)

    def read_dds_header(self, path: Path | str) -> tuple[int, int] | None:
        """Read DDS header, returning (width, height) or None."""
        if self._rust_core:
            try:
                return self._rust_core.read_dds_header(str(path))
            except (RustError, RustIOError, RustParseError):
                return None
        try:
            import asyncio

            from ClassicLib.scanning.game.checks.dds_processor import DDSProcessor

            return DDSProcessor(asyncio.Semaphore(1)).read_dds_header_mmap(Path(path))
        except (ImportError, OSError, RuntimeError):
            return None

    def read_dds_headers_batch(self, paths: list[Path | str]) -> dict[str, tuple[int, int] | None]:
        """Read DDS headers from multiple files."""
        if self._rust_core:
            return self._rust_core.read_dds_headers_batch([str(p) for p in paths])
        return {str(p): self.read_dds_header(p) for p in paths}

    def walk_directory(self, path: Path | str, pattern: str | None = None, max_depth: int | None = None) -> list[str]:
        """Recursively walk directory, optionally filtering by regex pattern."""
        if self._rust_core:
            return self._rust_core.py_walk_directory(str(path), pattern, max_depth)
        import re

        path_obj, pattern_re = Path(path), re.compile(pattern) if pattern else None
        results: list[str] = []

        def _walk(p: Path, depth: int = 0) -> None:
            if max_depth is not None and depth > max_depth:
                return
            try:
                for item in p.iterdir():
                    if item.is_file() and (pattern_re is None or pattern_re.search(item.name)):
                        results.append(str(item))
                    elif item.is_dir():
                        _walk(item, depth + 1)
            except PermissionError:
                pass

        _walk(path_obj)
        return results

    async def read_multiple_files(self, paths: list[Path | str]) -> dict[str, str]:
        """Read multiple files, returning {filename: content}."""
        if self._rust_core:
            result = await self._rust_core.py_read_multiple_files([str(p) for p in paths])
            return {Path(k).name: v for k, v in result.items()}
        return await self._python_core.read_multiple_files(paths)

    async def write_multiple_files(self, files: dict[Path | str, str]) -> None:
        """Write multiple files."""
        if self._rust_core:
            await self._rust_core.py_write_multiple_files({str(k): v for k, v in files.items()})
            return
        await self._python_core.write_multiple_files(files)

    def file_exists(self, path: Path | str) -> bool:
        """Check if file exists."""
        if self._rust_core:
            return self._rust_core.file_exists(str(path))
        return Path(path).exists()

    def get_file_size(self, path: Path | str) -> int:
        """Get file size in bytes, -1 if not found."""
        if self._rust_core:
            return self._rust_core.get_file_size(str(path))
        try:
            return Path(path).stat().st_size
        except (OSError, FileNotFoundError):
            return -1

    def get_file_info(self, path: Path | str) -> dict[str, Any]:
        """Get file info dict with size, created, modified (or error)."""
        if self._rust_core:
            return self._rust_core.get_file_info(str(path))
        try:
            stat = Path(path).stat()
        except OSError as e:
            return {"error": str(e)}
        else:
            return {"size": stat.st_size, "created": stat.st_ctime, "modified": stat.st_mtime}

    async def read_crash_log(self, path: Path | str) -> list[str]:
        """Read crash log, stripping trailing empty lines."""
        lines = await self.read_lines(path)
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    async def write_crash_report(self, path: Path | str, report_lines: list[str]) -> None:
        """Write crash report as .md file."""
        report_path = Path(path).with_suffix(".md")
        await self.write_file(report_path, "".join(report_lines))
        logger.info(f"Report written to: {report_path}")

    def clear_cache(self) -> None:
        """Clear all internal caches."""
        if self._rust_core:
            self._rust_core.clear_cache()
