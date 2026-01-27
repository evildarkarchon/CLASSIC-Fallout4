"""Rust-accelerated FileIOCore wrapper.

This module provides a drop-in replacement for FileIOCore that uses
the high-performance Rust implementation when available.

Performance improvements with Rust:
- 10-20x faster file operations with async I/O
- 30-40x faster batch DDS header processing
- Memory-mapped file support for large files
- Parallel directory traversal
- Zero-copy operations where possible

Async/Sync Behavior:
    Methods fall into two categories:

    1. **True Async Methods** (marked `async def`):
       - These methods await Rust coroutines and do NOT block
       - Examples: read_file(), write_file(), read_lines(), read_bytes()
       - Use directly in async contexts: `content = await io_core.read_file(path)`

    2. **Blocking Methods** (marked `def`):
       - These methods call synchronous Rust functions that block on Tokio runtime
       - Examples: read_dds_header(), walk_directory(), file_exists()
       - Use directly in CLI/sync contexts: `header = io_core.read_dds_header(path)`

AsyncBridge Usage (GUI Applications Only):
    For blocking methods in Qt GUI applications, wrap with AsyncBridge:

    ```python
    from ClassicLib.core.async_bridge import AsyncBridge
    from ClassicLib.integration.rust.file_io_rust import FileIOCore

    io_core = FileIOCore()
    bridge = AsyncBridge.get_instance()

    # For blocking methods (read_dds_header, walk_directory, etc.)
    result = bridge.run_async(lambda: io_core.read_dds_header(path))
    files = bridge.run_async(lambda: io_core.walk_directory(path, "*.dds"))

    # For true async methods, use directly in async contexts
    async def process_files():
        content = await io_core.read_file(path)  # No AsyncBridge needed
        await io_core.write_file(path, content)
    ```

CLI Usage:
    For CLI applications, use async methods directly with asyncio.run():

    ```python
    import asyncio
    from ClassicLib.integration.rust.file_io_rust import FileIOCore

    async def main():
        io_core = FileIOCore()
        # Use async methods directly
        content = await io_core.read_file(path)
        # Use blocking methods directly (already in sync context)
        header = io_core.read_dds_header(path)

    asyncio.run(main())
    ```
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.integration.detector import detect_component
from ClassicLib.integration.exceptions import RustError, RustIOError, RustParseError

logger = logging.getLogger(__name__)

# Centralized detection of Rust FileIOCore
RUST_AVAILABLE, _rust_io = detect_component("classic_file_io", "FileIOCore")
if RUST_AVAILABLE:
    logger.info("✓ Rust FileIOCore available (10-20x speedup)")

# Detect Rust-specific exception types
_, _rust_io_error = detect_component("classic_file_io", "RustFileIOIOError")
_, _rust_parse_error = detect_component("classic_file_io", "RustFileIOParseError")


def _get_rust_exception_types() -> tuple[tuple[type, ...], tuple[type, ...], tuple[type, ...]]:
    """Get tuple of Rust exception types to catch.

    Returns:
        A tuple containing three tuples of exception types:
            - First tuple: IOError types (RustIOError and module-specific variants)
            - Second tuple: ParseError types (RustParseError and module-specific variants)
            - Third tuple: Generic RustError types

    """
    io_errors = (RustIOError,)
    parse_errors = (RustParseError,)
    rust_errors = (RustError,)

    # Add module-specific exceptions if available
    if _rust_io_error:
        io_errors = (RustIOError, _rust_io_error)
    if _rust_parse_error:
        parse_errors = (RustParseError, _rust_parse_error)

    return io_errors, parse_errors, rust_errors


# Get exception type tuples at module level for use in exception handlers
io_errors, parse_errors, rust_errors = _get_rust_exception_types()

# Combined exception tuples for convenient use in exception handlers
# These include both base exceptions and module-specific variants
io_and_rust_errors = io_errors + rust_errors
all_rust_errors = io_errors + parse_errors + rust_errors


class FileIOCore:
    """Rust-accelerated FileIOCore with Python API compatibility.

    This class provides the same API as the Python FileIOCore but uses
    high-performance Rust implementations when available.
    """

    def __init__(self, encoding: str = "utf-8", errors: str = "ignore") -> None:
        """Initialize a File I/O core system to handle encoding and error preferences. This
        class supports fallback between Rust and Python implementations, ensuring robust
        file I/O operations regardless of the underlying availability of native support.
        If Rust core is available and successfully initialized, it will be used;
        otherwise, a Python-based fallback system is initialized.

        Args:
            encoding (str): The default text encoding to use for file operations. Defaults to "utf-8".
            errors (str): The default error handling strategy for file encoding and decoding operations.
                Possible values include "ignore", "strict", and "replace". Defaults to "ignore".

        """
        self.default_encoding = encoding
        self.default_errors = errors
        self._rust_core = None
        self._python_core = None

        if RUST_AVAILABLE and _rust_io:
            try:
                # Initialize Rust core with reasonable defaults
                self._rust_core = _rust_io(encoding=encoding, errors=errors, cache_size=100, max_concurrent_io=50)
                logger.debug("Using Rust FileIOCore")
            except RustError as e:
                logger.warning(f"Rust initialization error: {e}")
            except (OSError, ImportError) as e:
                logger.warning(f"Failed to initialize Rust FileIOCore: {e}")

        # Always create Python fallback
        if not self._rust_core:
            from ClassicLib.io.files.core import FileIOCore as PythonFileIOCore

            self._python_core = PythonFileIOCore(encoding, errors)

    @property
    def is_rust_accelerated(self) -> bool:
        """Property to check if Rust acceleration is enabled.

        The property evaluates whether the `_rust_core` attribute is
        set or not. If `_rust_core` is not `None`, it indicates that
        Rust acceleration is active.

        Returns:
            bool: True if Rust acceleration is enabled, False otherwise.

        """
        return self._rust_core is not None

    @staticmethod
    def _ensure_path(path: Path | str) -> Path:
        """Ensure that the given path is converted to a Path object.

        This method checks if the provided input is of type `str`. If so, it converts
        it to a `Path` object. If the input is already a `Path` object, it returns it
        unchanged.

        Args:
            path (Path | str): The input path that needs to be ensured as a `Path` object.

        Returns:
            Path: The ensured `Path` object.

        """
        if isinstance(path, str):
            return Path(path)
        return path

    # ==========================================
    # Core Read Operations
    # ==========================================

    async def read_file(self, path: Path | str) -> str:
        """Read the content of a file asynchronously and returns it as a string.

        This function attempts to read a file using a Rust-based core if available for
        optimal performance. If the Rust-based core fails or is unavailable, it falls
        back to a Python-based core. If neither core is present, it employs manual
        fallback logic to read the file synchronously using built-in Python capabilities.

        Args:
            path (Path | str): The path to the file to be read. Can be a Path object
                or a string representing the file path.

        Returns:
            str: The content of the file as a string.

        """
        if self._rust_core:
            try:
                # Await Rust coroutine - true async, no blocking!
                return await self._rust_core.read_file(str(path))
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in read_file, falling back: {e}")

        # Python fallback
        if self._python_core:
            return await self._python_core.read_file(path)

        # Manual fallback
        path = self._ensure_path(path)
        return path.read_text(encoding=self.default_encoding, errors=self.default_errors)

    async def read_lines(self, path: Path | str) -> list[str]:
        """Read lines from a file specified by the given path.

        This method attempts to read the file using the Rust-based core reader if available.
        If the Rust-based reader fails, it falls back to the Python-based core reader.
        As a last resort, it reads the file content and splits it into lines manually.

        Args:
            path (Path | str): The path to the file to be read.

        Returns:
            list[str]: A list of strings, each representing a line from the file.

        Raises:
            Exception: Raises exceptions from the Rust core or Python core readers during failure.

        """
        if self._rust_core:
            try:
                return await self._rust_core.read_lines(str(path))
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in read_lines, falling back: {e}")

        if self._python_core:
            return await self._python_core.read_lines(path)

        content = await self.read_file(path)
        return content.splitlines()

    async def stream_lines(self, path: Path | str) -> AsyncIterator[str]:
        """Stream lines from a file asynchronously.

        Args:
            path (Path | str): The path to the file.

        Yields:
            str: Lines from the file.

        """
        if self._rust_core:
            try:
                # This returns an async iterator (PyLineStreamer)
                streamer = await self._rust_core.stream_lines(str(path))
                async for line in streamer:
                    yield line
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in stream_lines, falling back: {e}")
            else:
                return

        # Python fallback
        if self._python_core:
            async for line in self._python_core.stream_lines(path):
                yield line
            return

        # Manual fallback
        lines = await self.read_lines(path)
        for line in lines:
            yield line

    def stream_lines_sync(self, path: Path | str) -> Iterator[str]:
        """Stream lines from a file synchronously.

        Args:
            path (Path | str): The path to the file.

        Yields:
            str: Lines from the file.

        """
        if self._rust_core:
            try:
                # This returns a standard iterator (PySyncLineStreamer)
                # The Rust method call is synchronous (blocks I/O)
                yield from self._rust_core.stream_lines_sync(str(path))
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in stream_lines_sync, falling back: {e}")
            else:
                return

        # Manual fallback using open_file_with_encoding
        from ClassicLib.Utils.file_utils import open_file_with_encoding

        path = self._ensure_path(path)
        with open_file_with_encoding(path) as f:
            for line in f:
                yield line.rstrip("\n")

    async def read_bytes(self, path: Path | str) -> bytes:
        """Read bytes from the specified file path using available core handlers.

        The method attempts to read bytes from the file using the Rust core handler.
        If it fails, it switches to the Python core handler. As a final fallback, it
        directly reads the bytes from the given path.

        Args:
            path (Path | str): The file path from which bytes are to be read. Can be
                provided as either a Path object or a string.

        Returns:
            bytes: The content of the file as bytes.

        """
        if self._rust_core:
            try:
                # Rust returns bytes directly - no wrapper needed
                return await self._rust_core.read_bytes(str(path))
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in read_bytes, falling back: {e}")

        if self._python_core:
            return await self._python_core.read_bytes(path)

        path = self._ensure_path(path)
        return path.read_bytes()

    async def read_file_mmap(self, path: Path | str) -> str:
        """Read a file using memory mapping for large files (optimized).

        Args:
            path (Path | str): Path to the file to read.

        Returns:
            str: File content.

        """
        if self._rust_core:
            try:
                return await self._rust_core.read_file_mmap(str(path))
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in read_file_mmap, falling back: {e}")

        # Fallback to regular read
        return await self.read_file(path)

    async def read_file_with_encoding(self, path: Path | str, encoding: str) -> str:
        """Read a file with a specific encoding.

        Args:
            path (Path | str): Path to the file.
            encoding (str): Encoding to use.

        Returns:
            str: File content.

        """
        if self._rust_core:
            try:
                return await self._rust_core.read_file_with_encoding(str(path), encoding)
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in read_file_with_encoding, falling back: {e}")

        # Fallback
        path = self._ensure_path(path)
        return path.read_text(encoding=encoding, errors=self.default_errors)

    # ==========================================
    # Core Write Operations
    # ==========================================

    async def write_file(self, path: Path | str, content: str) -> None:
        """Write content to a file, either using the rust or python core, or directly
        using Python file operations as a fallback. Ensures the parent directory
        exists if using the Python fallback.

        Args:
            path (Path | str): The path to the file to be written.
            content (str): The content to be written to the file.

        """
        if self._rust_core:
            try:
                await self._rust_core.write_file(str(path), content)
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in write_file, falling back: {e}")
            else:
                return

        if self._python_core:
            await self._python_core.write_file(path, content)
        else:
            path = self._ensure_path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding=self.default_encoding, errors=self.default_errors)

    async def write_lines(self, path: Path | str, lines: list[str]) -> None:
        """Write multiple lines to a specified file asynchronously. The method determines
        whether to use a Rust-based or Python-based core for writing the lines. If both
        cores fail, it falls back to default content formatting for writing.

        Args:
            path (Path | str): The file path where the lines will be written.
            lines (list[str]): A list of strings, each representing a line to be written
                into the file.

        """
        if self._rust_core:
            try:
                await self._rust_core.write_lines(str(path), lines)
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in write_lines, falling back: {e}")
            else:
                return

        if self._python_core:
            await self._python_core.write_lines(path, lines)
        else:
            content = "\n".join(lines)
            if not content.endswith("\n"):
                content += "\n"
            await self.write_file(path, content)

    async def write_bytes(self, path: Path | str, content: bytes) -> None:
        """Write byte content to a specified file path.

        This method attempts to utilize a Rust-based core implementation for performance.
        If the Rust implementation fails, it will fall back to a Python-based or
        default implementation.

        Args:
            path (Path | str): The file path where the byte content is to be written.
            content (bytes): The byte content to be written to the specified file path.

        """
        if self._rust_core:
            try:
                # PyO3 converts bytes to Vec<u8> automatically
                await self._rust_core.write_bytes(str(path), content)
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in write_bytes, falling back: {e}")
            else:
                return

        if self._python_core:
            await self._python_core.write_bytes(path, content)
        else:
            path = self._ensure_path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    async def append_file(self, path: Path | str, content: str) -> None:
        """Append the provided content to a file at the given path. The method attempts to
        use the Rust implementation if available, otherwise falls back to the Python
        implementation. If neither core is available, it directly handles the file
        operation, ensuring the file's parent directory exists if necessary.

        Args:
            path (Path | str): The path to the file where the content should be appended.
            content (str): The string content to append to the specified file.

        Raises:
            Exception: Raised if the Rust core fails during the append operation.

        """
        if self._rust_core:
            try:
                await self._rust_core.append_file(str(path), content)
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in append_file, falling back: {e}")
            else:
                return

        if self._python_core:
            await self._python_core.append_file(path, content)
        else:
            path = self._ensure_path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding=self.default_encoding, errors=self.default_errors) as f:
                f.write(content)

    # ==========================================
    # Advanced Operations (Rust-specific)
    # ==========================================

    def read_dds_header(self, path: Path | str) -> tuple[int, int] | None:
        """Read the DDS header from the specified file path and returns the extracted header
        information. This method ensures compatibility by attempting to use a high-performance
        Rust implementation if available, or a Python fallback otherwise.

        Note:
            This method blocks on Rust's Tokio runtime. For GUI applications, wrap with AsyncBridge:
            ```python
            from ClassicLib.core.async_bridge import AsyncBridge
            bridge = AsyncBridge.get_instance()
            result = bridge.run_async(lambda: io_core.read_dds_header(path))
            ```

        Args:
            path (Path | str): The file path to the DDS file which header needs to be read.

        Returns:
            tuple[int, int] | None: A tuple containing the width and height of the DDS file if
            successful, or None if the operation fails.

        """
        if self._rust_core:
            try:
                # Rust method is synchronous (blocks on Tokio runtime internally)
                return self._rust_core.read_dds_header(str(path))
            except all_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in read_dds_header: {e}")
                return None

        # Python fallback using existing DDSProcessor
        try:
            from ClassicLib.scanning.game.checks.dds_processor import DDSProcessor

            processor = DDSProcessor(asyncio.Semaphore(1))
            path = self._ensure_path(path)
            return processor.read_dds_header_mmap(path)
        except (ImportError, OSError, RuntimeError):
            return None

    def read_dds_headers_batch(self, paths: list[Path | str]) -> dict[str, tuple[int, int] | None]:
        """Read headers from multiple DDS (DirectDraw Surface) files either using a Rust
        core implementation for batch processing or a Python fallback that processes
        files sequentially.

        This function attempts to use a Rust-based implementation for performance
        optimization. If the Rust implementation is unavailable or fails, the method
        resorts to a Python-based sequential processing approach to extract the
        required data from the files.

        Note:
            This method blocks on Rust's Tokio runtime with parallel processing. For GUI applications,
            wrap with AsyncBridge:
            ```python
            from ClassicLib.core.async_bridge import AsyncBridge
            bridge = AsyncBridge.get_instance()
            result = bridge.run_async(lambda: io_core.read_dds_headers_batch(paths))
            ```

        Args:
            paths (list[Path | str]): A list of file paths to DDS files where each path
                is represented as a string or Path object.

        Returns:
            dict[str, tuple[int, int] | None]: A dictionary where the keys are file
                paths (as strings) and the values are either tuples containing header
                information (two integers) or None if the header could not be processed.

        """
        if self._rust_core:
            try:
                str_paths = [str(p) for p in paths]
                # Rust method is synchronous (blocks with parallel processing internally)
                return self._rust_core.read_dds_headers_batch(str_paths)
            except all_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in read_dds_headers_batch: {e}")

        # Python fallback - process sequentially
        results = {}
        for path in paths:
            results[str(path)] = self.read_dds_header(path)
        return results  # pyright: ignore[reportUnknownVariableType]

    def walk_directory(self, path: Path | str, pattern: str | None = None, max_depth: int | None = None) -> list[str]:
        """Recursively walks through a directory to collect the file paths, optionally filtering by
        a pattern and limiting the depth of the search.

        This method attempts to use a Rust-based implementation for improved
        performance when available. If the Rust-based implementation fails or is unavailable,
        it falls back to a Python implementation for traversing the directory structure.

        Note:
            This method blocks on Rust's Tokio runtime with parallel traversal. For GUI applications,
            wrap with AsyncBridge:
            ```python
            from ClassicLib.core.async_bridge import AsyncBridge
            bridge = AsyncBridge.get_instance()
            result = bridge.run_async(lambda: io_core.walk_directory(path, pattern, max_depth))
            ```

        Args:
            path (Path | str): The directory path to start the walk from. Can be provided
                as a Path object or a string.
            pattern (str | None): The regex pattern to filter file names. Only files whose
                names match the pattern will be included in the results. Defaults to None,
                meaning no filtering is applied.
            max_depth (int | None): The maximum depth to recurse into subdirectories. A
                value of None indicates no depth restrictions. Defaults to None.

        Returns:
            list[str]: A list of file paths (as strings) collected during the directory walk.
            Only paths meeting the specified filter criteria and depth constraints are included.

        Raises:
            None

        """
        if self._rust_core:
            try:
                # Rust method is synchronous (blocks with parallel processing internally)
                return self._rust_core.py_walk_directory(str(path), pattern, max_depth)
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in walk_directory: {e}")

        # Python fallback
        import re

        path = self._ensure_path(path)
        pattern_re = re.compile(pattern) if pattern else None
        results = []

        def walk(p: Path, depth: int = 0) -> None:
            if max_depth is not None and depth > max_depth:
                return
            try:
                for item in p.iterdir():
                    if item.is_file():
                        if pattern_re is None or pattern_re.search(item.name):
                            results.append(str(item))
                    elif item.is_dir():
                        walk(item, depth + 1)
            except PermissionError:
                pass  # Skip inaccessible directories

        walk(path)
        return results  # pyright: ignore[reportUnknownVariableType]

    # ==========================================
    # Batch Operations
    # ==========================================

    async def read_multiple_files(self, paths: list[Path | str]) -> dict[str, str]:
        """Read multiple files asynchronously and returns their contents in a dictionary.

        The method attempts to use an optimized reading mechanism if it is available
        through `_rust_core` or `_python_core`, falling back to a manual reading
        approach if neither optimization is available. File contents are read and
        mapped to their corresponding filenames (not full paths).

        Args:
            paths (list[Path | str]): A list of file paths or strings representing file
                paths to be read.

        Returns:
            dict[str, str]: A dictionary where the keys are filenames and the values
                are the file contents.

        Raises:
            Exception: Logs an error message and adds empty content to the result in
                case of individual file read failures.

        """
        if self._rust_core:
            try:
                str_paths = [str(p) for p in paths]
                # Rust method returns coroutine - must await
                result = await self._rust_core.py_read_multiple_files(str_paths)
                # Convert paths to filenames for compatibility
                return {Path(k).name: v for k, v in result.items()}
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in read_multiple_files: {e}")

        if self._python_core:
            return await self._python_core.read_multiple_files(paths)

        # Manual fallback
        results = {}
        for path in paths:
            try:
                content = await self.read_file(path)
                results[Path(path).name] = content
            except OSError as e:
                logger.error(f"Error reading {path}: {e}")
                results[Path(path).name] = ""
        return results  # pyright: ignore[reportUnknownVariableType]

    async def write_multiple_files(self, files: dict[Path | str, str]) -> None:
        """Write content to multiple files asynchronously.

        This method writes the specified content to the provided file paths. It utilizes
        different mechanisms for file writing based on the available core implementation
        (rust or python). If none of the core implementations are accessible, it falls
        back to writing each file individually.

        Args:
            files (dict[Path | str, str]): A dictionary where the keys are file paths
                (either `Path` objects or strings) and the values are the file contents
                as strings.

        """
        if self._rust_core:
            try:
                str_files = {str(k): v for k, v in files.items()}
                # Rust method returns coroutine - must await
                await self._rust_core.py_write_multiple_files(str_files)
            except io_and_rust_errors as e:  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]
                logger.debug(f"Rust error in write_multiple_files: {e}")
            else:
                return

        if self._python_core:
            await self._python_core.write_multiple_files(files)
        else:
            for path, content in files.items():
                await self.write_file(path, content)

    # ==========================================
    # Utility Operations
    # ==========================================

    def file_exists(self, path: Path | str) -> bool:
        """Check whether a specified file or directory exists.

        This method verifies the existence of a file or directory at the provided
        path. If an internal `_rust_core` attribute is present, it delegates the check
        to the Rust core implementation for performance. Otherwise, it converts the
        path and verifies its existence using Python's built-in functionality.

        Args:
            path (Path | str): The path to the file or directory to check. This can
                be provided as a `Path` object or a string.

        Returns:
            bool: True if the file or directory exists, otherwise False.

        """
        if self._rust_core:
            return self._rust_core.file_exists(str(path))

        path = self._ensure_path(path)
        return path.exists()

    def get_file_size(self, path: Path | str) -> int:
        """Return the size of a file located at the given path.

        This method attempts to determine the physical size of a file in bytes.
        If the underlying Rust core is available, it will delegate the size
        calculation to it. Otherwise, it uses the `stat` method from the
        os module to retrieve the file size. If the file does not exist or
        an error occurs during the retrieval process, it will return -1.

        Args:
            path (Path | str): The file path for which the size is to be determined.

        Returns:
            int: The size of the file in bytes. Returns -1 if the file does not
            exist or if the size retrieval fails.

        """
        if self._rust_core:
            return self._rust_core.get_file_size(str(path))

        path = self._ensure_path(path)
        try:
            return path.stat().st_size
        except (OSError, FileNotFoundError):
            return -1

    def get_file_info(self, path: Path | str) -> dict[str, Any]:
        """Get detailed file information (size, timestamps).

        Args:
            path (Path | str): Path to the file.

        Returns:
            dict[str, Any]: Dictionary with keys 'size', 'created', 'modified', or 'error'.

        """
        if self._rust_core:
            return self._rust_core.get_file_info(str(path))

        path = self._ensure_path(path)
        try:
            stat = path.stat()
        except OSError as e:
            return {"error": str(e)}
        else:
            return {"size": stat.st_size, "created": stat.st_ctime, "modified": stat.st_mtime}

    async def read_crash_log(self, path: Path | str) -> list[str]:
        """Read the crash log from the specified file and returns a list of non-empty lines. This method strips any
        trailing empty lines from the log for consistency.

        Args:
            path (Path | str): The path to the crash log file.

        Returns:
            list[str]: A list of strings, each representing a non-empty line from the crash log.

        """
        lines = await self.read_lines(path)
        # Strip any trailing empty lines for consistency
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    async def write_crash_report(self, path: Path | str, report_lines: list[str]) -> None:
        """Write a crash report to the specified path in Markdown format.

        This method ensures the given path is valid, converts it to a `.md` file,
        and writes the given report lines as the content. It logs the operation
        upon successful completion.

        Args:
            path (Path | str): The file path where the crash report should
                be saved. It can be a string or a Path object.
            report_lines (list[str]): A list of strings containing the lines
                to be written into the report. Each line is expected to already
                end with a newline character.

        """
        path = self._ensure_path(path)
        report_path = path.with_suffix(".md")
        content = "".join(report_lines)  # Assume lines already have newlines
        await self.write_file(report_path, content)
        logger.info(f"Report written to: {report_path}")

    def clear_cache(self) -> None:
        """Clear all internal caches."""
        if self._rust_core:
            self._rust_core.clear_cache()


# Sync adapter functions for backward compatibility
def get_rust_file_io() -> FileIOCore | None:
    """Get an instance of FileIOCore if Rust is available.

    This function checks whether Rust functionality is available in the current
    environment. If available, it returns an instance of FileIOCore. If not,
    it returns None. This is particularly useful for systems that require file I/O
    handling through Rust for performance optimization or specific functionalities.

    Returns:
        FileIOCore | None: An instance of FileIOCore if Rust is available,
        otherwise None.

    """
    if RUST_AVAILABLE:
        return FileIOCore()
    return None


def create_file_io_sync(encoding: str = "utf-8", errors: str = "ignore") -> Any:
    """Create a synchronous file I/O utility. GUI workers only.

    WARNING: This function uses AsyncBridge internally and creates additional event loop overhead.
    Not for CLI use. For CLI usage, use FileIOCore async methods directly with await.

    Args:
        encoding: Encoding to use for reading and writing text files. Default
            is "utf-8".
        errors: Error handling strategy for encoding and decoding operations.
            Default is "ignore".

    Returns:
        An instance of a synchronous wrapper for file I/O operations.

    """
    io_core = FileIOCore(encoding, errors)

    # Create sync wrappers
    bridge = AsyncBridge.get_instance()

    # Wrap async methods for sync usage
    class SyncWrapper:
        """Synchronous wrapper for FileIOCore async methods. GUI workers only."""

        def __init__(self, core: FileIOCore) -> None:
            self._core = core

        def read_file(self, path: Path | str) -> str:
            return bridge.run_async(self._core.read_file(path))

        def read_lines(self, path: Path | str) -> list[str]:
            return bridge.run_async(self._core.read_lines(path))

        def read_bytes(self, path: Path | str) -> bytes:
            return bridge.run_async(self._core.read_bytes(path))

        def write_file(self, path: Path | str, content: str) -> None:
            return bridge.run_async(self._core.write_file(path, content))

        def write_lines(self, path: Path | str, lines: list[str]) -> None:
            return bridge.run_async(self._core.write_lines(path, lines))

        def write_bytes(self, path: Path | str, content: bytes) -> None:
            return bridge.run_async(self._core.write_bytes(path, content))

        def append_file(self, path: Path | str, content: str) -> None:
            return bridge.run_async(self._core.append_file(path, content))

        def read_crash_log(self, path: Path | str) -> list[str]:
            return bridge.run_async(self._core.read_crash_log(path))

        def write_crash_report(self, path: Path | str, report_lines: list[str]) -> None:
            return bridge.run_async(self._core.write_crash_report(path, report_lines))

        def read_multiple_files(self, paths: list[Path | str]) -> dict[str, str]:
            return bridge.run_async(self._core.read_multiple_files(paths))

        def write_multiple_files(self, files: dict[Path | str, str]) -> None:
            return bridge.run_async(self._core.write_multiple_files(files))

        def file_exists(self, path: Path | str) -> bool:
            return self._core.file_exists(path)

        def get_file_size(self, path: Path | str) -> int:
            return self._core.get_file_size(path)

        def clear_cache(self) -> None:
            return self._core.clear_cache()

    return SyncWrapper(io_core)
