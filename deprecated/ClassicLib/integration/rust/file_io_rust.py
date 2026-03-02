"""Rust-accelerated FileIOCore wrapper.

Thin delegation layer that requires the Rust backend. Python fallback paths
have been removed.
"""

from __future__ import annotations

import errno
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

from ClassicLib.integration.exceptions import RustBindingInitError, RustError, RustIOError, RustParseError
from ClassicLib.integration.factory import get_component

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


_rust_io = get_component("classic_file_io", "FileIOCore")
_RustFileIOIOError: type[Exception] | None = None
logger.info("Rust FileIOCore available")
try:
    import classic_file_io as _cfi

    _RustFileIOIOError = _cfi.RustFileIOIOError
except (ImportError, AttributeError):
    _RustFileIOIOError = None


class FileIOCore:
    """Rust-accelerated file I/O wrapper."""

    def __init__(self, encoding: str = "utf-8", errors: str = "ignore") -> None:
        """Initialize with encoding preferences and Rust/Python backend."""
        self.default_encoding = encoding
        self.default_errors = errors
        try:
            self._rust_core = _rust_io(encoding=encoding, errors=errors, cache_size=100, max_concurrent_io=50)
        except Exception as exc:
            raise RustBindingInitError("classic_file_io.FileIOCore", str(exc)) from exc

    @property
    def is_rust_accelerated(self) -> bool:
        """Check if Rust acceleration is active."""
        return True

    async def read_file(self, path: Path | str) -> str:
        """Read file contents as string."""
        try:
            return await self._rust_core.read_file(str(path))
        except Exception as e:
            if _RustFileIOIOError and isinstance(e, _RustFileIOIOError):
                raise _translate_rust_io_error(e, path) from e
            raise

    async def read_lines(self, path: Path | str) -> list[str]:
        """Read file as list of lines."""
        try:
            return await self._rust_core.read_lines(str(path))
        except Exception as e:
            if _RustFileIOIOError and isinstance(e, _RustFileIOIOError):
                raise _translate_rust_io_error(e, path) from e
            raise

    async def stream_lines(self, path: Path | str) -> AsyncIterator[str]:
        """Stream lines from file asynchronously."""
        streamer = await self._rust_core.stream_lines(str(path))
        async for line in streamer:
            yield line

    def stream_lines_sync(self, path: Path | str) -> Iterator[str]:
        """Stream lines from file synchronously."""
        yield from self._rust_core.stream_lines_sync(str(path))

    async def read_bytes(self, path: Path | str) -> bytes:
        """Read file as raw bytes."""
        try:
            return await self._rust_core.read_bytes(str(path))
        except Exception as e:
            if _RustFileIOIOError and isinstance(e, _RustFileIOIOError):
                raise _translate_rust_io_error(e, path) from e
            raise

    async def read_file_mmap(self, path: Path | str) -> str:
        """Read file using memory mapping (optimized for large files)."""
        return await self._rust_core.read_file_mmap(str(path))

    async def read_file_with_encoding(self, path: Path | str, encoding: str) -> str:
        """Read file with specific encoding."""
        return await self._rust_core.read_file_with_encoding(str(path), encoding)

    async def write_file(self, path: Path | str, content: str) -> None:
        """Write string content to file."""
        await self._rust_core.write_file(str(path), content)

    async def write_lines(self, path: Path | str, lines: list[str]) -> None:
        """Write list of lines to file."""
        await self._rust_core.write_lines(str(path), lines)

    async def write_bytes(self, path: Path | str, content: bytes) -> None:
        """Write raw bytes to file."""
        await self._rust_core.write_bytes(str(path), content)

    async def append_file(self, path: Path | str, content: str) -> None:
        """Append content to file."""
        await self._rust_core.append_file(str(path), content)

    def read_dds_header(self, path: Path | str) -> tuple[int, int] | None:
        """Read DDS header, returning (width, height) or None."""
        try:
            return self._rust_core.read_dds_header(str(path))
        except (RustError, RustIOError, RustParseError):
            return None

    def read_dds_headers_batch(self, paths: list[Path | str]) -> dict[str, tuple[int, int] | None]:
        """Read DDS headers from multiple files."""
        return self._rust_core.read_dds_headers_batch([str(p) for p in paths])

    def walk_directory(self, path: Path | str, pattern: str | None = None, max_depth: int | None = None) -> list[str]:
        """Recursively walk directory, optionally filtering by regex pattern."""
        return self._rust_core.py_walk_directory(str(path), pattern, max_depth)

    async def read_multiple_files(self, paths: list[Path | str]) -> dict[str, str]:
        """Read multiple files, returning {filename: content}."""
        result = await self._rust_core.py_read_multiple_files([str(p) for p in paths])
        return {Path(k).name: v for k, v in result.items()}

    async def write_multiple_files(self, files: dict[Path | str, str]) -> None:
        """Write multiple files."""
        await self._rust_core.py_write_multiple_files({str(k): v for k, v in files.items()})

    def file_exists(self, path: Path | str) -> bool:
        """Check if file exists."""
        return self._rust_core.file_exists(str(path))

    def get_file_size(self, path: Path | str) -> int:
        """Get file size in bytes, -1 if not found."""
        return self._rust_core.get_file_size(str(path))

    def get_file_info(self, path: Path | str) -> dict[str, Any]:
        """Get file info dict with size, created, modified (or error)."""
        return self._rust_core.get_file_info(str(path))

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
        self._rust_core.clear_cache()
