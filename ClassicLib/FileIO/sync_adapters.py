"""Synchronous adapter functions for backwards compatibility."""

from pathlib import Path

from ClassicLib.AsyncBridge import AsyncBridge

from .core import FileIOCore


def read_file_sync(path: Path | str) -> str:
    """Sync adapter for reading file contents."""
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(FileIOCore().read_file(path))


def read_lines_sync(path: Path | str) -> list[str]:
    """Sync adapter for reading file lines."""
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(FileIOCore().read_lines(path))


def read_bytes_sync(path: Path | str) -> bytes:
    """Sync adapter for reading file bytes."""
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(FileIOCore().read_bytes(path))


def write_file_sync(path: Path | str, content: str) -> None:
    """Sync adapter for writing file contents."""
    bridge = AsyncBridge.get_instance()
    bridge.run_async(FileIOCore().write_file(path, content))


def write_lines_sync(path: Path | str, lines: list[str]) -> None:
    """Sync adapter for writing file lines."""
    bridge = AsyncBridge.get_instance()
    bridge.run_async(FileIOCore().write_lines(path, lines))


def write_bytes_sync(path: Path | str, content: bytes) -> None:
    """Sync adapter for writing file bytes."""
    bridge = AsyncBridge.get_instance()
    bridge.run_async(FileIOCore().write_bytes(path, content))


def read_crash_log_sync(path: Path | str) -> list[str]:
    """Sync adapter for reading crash logs."""
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(FileIOCore().read_crash_log(path))


def write_crash_report_sync(path: Path | str, report_lines: list[str]) -> None:
    """Sync adapter for writing crash reports."""
    bridge = AsyncBridge.get_instance()
    bridge.run_async(FileIOCore().write_crash_report(path, report_lines))


def append_file_sync(path: Path | str, content: str) -> None:
    """Sync adapter for appending to files."""
    bridge = AsyncBridge.get_instance()
    bridge.run_async(FileIOCore().append_file(path, content))
