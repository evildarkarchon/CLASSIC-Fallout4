"""Type stubs for classic_file_io.

Python bindings for classic-file-io-core, providing high-performance file I/O
operations with automatic encoding detection and DDS texture header parsing.
This module offers 10-40x speedup over Python's built-in file operations.

Architecture:
    - classic-file-io-core: Business logic (file I/O, encoding detection, DDS parsing)
    - classic-file-io-py: Python bindings (this module - PyO3 adapters)

Features:
    - Automatic encoding detection (chardet)
    - Parallel file operations
    - DDS texture header parsing (40x speedup)
    - Memory-mapped file reading
    - Intelligent caching
    - Directory walking
    - 10x speedup for file I/O

Usage:
    from classic_file_io import RustFileIOCore, EncodingDetector

    # Create file I/O core
    io_core = RustFileIOCore()

    # Read file with auto-detection
    content = io_core.read_file("config.txt")

    # Read multiple files in parallel
    contents = io_core.py_read_multiple_files(["file1.txt", "file2.txt"])

    # Parse DDS header
    header = io_core.read_dds_header("texture.dds")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__version__: str

class RustFileIOCore:
    """High-performance file I/O core with caching and encoding detection.

    Optimized file operations with 10x speedup over Python I/O through parallel
    reading, SIMD-accelerated encoding detection, and intelligent caching.

    The RustFileIOCore provides:
    - Automatic text encoding detection
    - Parallel file operations for batch processing
    - DDS texture header parsing (40x faster)
    - Memory-mapped file reading for large files
    - Directory traversal utilities
    - Intelligent file content caching
    """

    def __init__(self) -> None:
        """Create a new file I/O core with empty cache.

        Initializes internal caching structures for improved performance on
        repeated file operations.

        Example:
            >>> io_core = RustFileIOCore()
        """

    def read_file(self, path: str | Path, encoding: str | None = None) -> str:
        """Read entire file as string with automatic encoding detection.

        Reads a text file and returns its contents as a string. If no encoding
        is specified, automatically detects the file encoding using chardet.

        Args:
            path: File path to read (string or pathlib.Path)
            encoding: Explicit encoding (auto-detected if None)
                     Common values: 'utf-8', 'windows-1252', 'iso-8859-1'

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails
            UnicodeDecodeError: If encoding is incorrect

        Example:
            >>> io_core = RustFileIOCore()
            >>> content = io_core.read_file("config.txt")
            >>> # Or with explicit encoding
            >>> content = io_core.read_file("config.txt", encoding="utf-8")
        """

    def read_lines(self, path: str | Path, encoding: str | None = None) -> list[str]:
        """Read file as list of lines.

        Reads a text file and returns its contents as a list of lines.
        Newline terminators are removed from each line.

        Args:
            path: File path to read (string or pathlib.Path)
            encoding: Explicit encoding (auto-detected if None)

        Returns:
            List of lines (without newline terminators)

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails

        Example:
            >>> io_core = RustFileIOCore()
            >>> lines = io_core.read_lines("log.txt")
            >>> for line in lines:
            ...     print(line)
        """

    def read_bytes(self, path: str | Path) -> bytes:
        """Read entire file as raw bytes.

        Reads a file in binary mode and returns its raw byte content.
        Useful for binary files or when encoding is unknown.

        Args:
            path: File path to read (string or pathlib.Path)

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails

        Example:
            >>> io_core = RustFileIOCore()
            >>> data = io_core.read_bytes("image.png")
            >>> print(f"File size: {len(data)} bytes")
        """

    def write_file(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """Write string content to file.

        Writes text content to a file. Creates parent directories if they
        don't exist. Overwrites existing files.

        Args:
            path: Destination file path (string or pathlib.Path)
            content: String content to write
            encoding: Text encoding (default: "utf-8")

        Raises:
            IOError: If write fails
            PermissionError: If lacking write permissions

        Example:
            >>> io_core = RustFileIOCore()
            >>> io_core.write_file("output.txt", "Hello, World!")
        """

    def write_lines(self, path: str | Path, lines: list[str], encoding: str = "utf-8") -> None:
        """Write list of lines to file.

        Writes a list of lines to a file. Newline terminators are added
        automatically to each line.

        Args:
            path: Destination file path (string or pathlib.Path)
            lines: Lines to write (newlines added automatically)
            encoding: Text encoding (default: "utf-8")

        Raises:
            IOError: If write fails
            PermissionError: If lacking write permissions

        Example:
            >>> io_core = RustFileIOCore()
            >>> lines = ["Line 1", "Line 2", "Line 3"]
            >>> io_core.write_lines("output.txt", lines)
        """

    def write_bytes(self, path: str | Path, data: bytes) -> None:
        """Write raw bytes to file.

        Writes binary data to a file. Creates parent directories if they
        don't exist. Overwrites existing files.

        Args:
            path: Destination file path (string or pathlib.Path)
            data: Bytes to write

        Raises:
            IOError: If write fails
            PermissionError: If lacking write permissions

        Example:
            >>> io_core = RustFileIOCore()
            >>> data = b'\\x89PNG\\r\\n\\x1a\\n'
            >>> io_core.write_bytes("image.png", data)
        """

    def append_file(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """Append string content to file.

        Appends text content to the end of a file. Creates the file if it
        doesn't exist.

        Args:
            path: File path to append to (string or pathlib.Path)
            content: String content to append
            encoding: Text encoding (default: "utf-8")

        Raises:
            IOError: If append fails
            PermissionError: If lacking write permissions

        Example:
            >>> io_core = RustFileIOCore()
            >>> io_core.append_file("log.txt", "New log entry\\n")
        """

    def file_exists(self, path: str | Path) -> bool:
        """Check if file exists.

        Tests whether a file exists at the given path. Works for both
        files and directories.

        Args:
            path: File path to check (string or pathlib.Path)

        Returns:
            True if file exists, False otherwise

        Example:
            >>> io_core = RustFileIOCore()
            >>> if io_core.file_exists("config.txt"):
            ...     content = io_core.read_file("config.txt")
        """

    def get_file_size(self, path: str | Path) -> int:
        """Get file size in bytes.

        Returns the size of a file in bytes.

        Args:
            path: File path to check (string or pathlib.Path)

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file doesn't exist

        Example:
            >>> io_core = RustFileIOCore()
            >>> size = io_core.get_file_size("large_file.dat")
            >>> print(f"Size: {size / 1024 / 1024:.2f} MB")
        """

    def read_dds_header(self, path: str | Path) -> dict[str, Any] | None:
        """Parse DDS texture file header (40x speedup).

        Parses the header of a DirectDraw Surface (DDS) texture file and
        extracts key information about the texture format.

        Args:
            path: Path to DDS file (string or pathlib.Path)

        Returns:
            Dictionary with DDS header information, or None if invalid:
                - 'width': Texture width in pixels
                - 'height': Texture height in pixels
                - 'format': Pixel format (e.g., 'DXT1', 'BC7')
                - 'mipmap_count': Number of mipmap levels
                - 'depth': Texture depth (for 3D textures)
                - 'array_size': Number of textures in array

        Example:
            >>> io_core = RustFileIOCore()
            >>> header = io_core.read_dds_header("texture.dds")
            >>> if header:
            ...     print(f"Size: {header['width']}x{header['height']}")
            ...     print(f"Format: {header['format']}")
            ...     print(f"Mipmaps: {header['mipmap_count']}")
        """

    def read_dds_headers_batch(self, paths: list[str | Path]) -> list[dict[str, Any] | None]:
        """Parse multiple DDS headers in parallel.

        Parses multiple DDS texture file headers in parallel for improved
        performance when processing many texture files.

        Args:
            paths: List of DDS file paths

        Returns:
            List of header dictionaries (None for invalid files)
            Length matches input list, order preserved

        Example:
            >>> io_core = RustFileIOCore()
            >>> texture_files = ["tex1.dds", "tex2.dds", "tex3.dds"]
            >>> headers = io_core.read_dds_headers_batch(texture_files)
            >>> for path, header in zip(texture_files, headers):
            ...     if header:
            ...         print(f"{path}: {header['width']}x{header['height']}")
        """

    def clear_cache(self) -> None:
        """Clear the file content cache to free memory.

        Removes all cached file contents from memory. Useful for releasing
        memory after processing many files.

        Example:
            >>> io_core = RustFileIOCore()
            >>> # ... read many files ...
            >>> io_core.clear_cache()  # Free cached content
        """

    def py_read_file_mmap(self, path: str | Path) -> bytes:
        """Read file using memory mapping for large files.

        Uses memory-mapped I/O to efficiently read large files. This is
        significantly faster than normal file reading for files larger than
        available RAM.

        Args:
            path: File path to read (string or pathlib.Path)

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If memory mapping fails

        Example:
            >>> io_core = RustFileIOCore()
            >>> data = io_core.py_read_file_mmap("huge_file.dat")
            >>> print(f"Read {len(data)} bytes using mmap")
        """

    def py_read_multiple_files(
        self,
        paths: list[str | Path],
        encoding: str | None = None
    ) -> list[str | None]:
        """Read multiple files in parallel.

        Reads multiple text files in parallel for improved performance.
        Files are read concurrently using a thread pool.

        Args:
            paths: List of file paths to read
            encoding: Explicit encoding for all files (auto-detected if None)

        Returns:
            List of file contents (None for failed reads)
            Length matches input list, order preserved

        Example:
            >>> io_core = RustFileIOCore()
            >>> files = ["config1.txt", "config2.txt", "config3.txt"]
            >>> contents = io_core.py_read_multiple_files(files)
            >>> for path, content in zip(files, contents):
            ...     if content:
            ...         print(f"{path}: {len(content)} chars")
        """

    def py_write_multiple_files(
        self,
        path_content_pairs: list[tuple[str | Path, str]],
        encoding: str = "utf-8"
    ) -> list[bool]:
        """Write multiple files in parallel.

        Writes multiple files in parallel for improved performance.
        Files are written concurrently using a thread pool.

        Args:
            path_content_pairs: List of (path, content) tuples
            encoding: Text encoding for all files (default: "utf-8")

        Returns:
            List of success flags (True for successful writes)
            Length matches input list, order preserved

        Example:
            >>> io_core = RustFileIOCore()
            >>> writes = [
            ...     ("file1.txt", "Content 1"),
            ...     ("file2.txt", "Content 2"),
            ...     ("file3.txt", "Content 3")
            ... ]
            >>> results = io_core.py_write_multiple_files(writes)
            >>> print(f"Successful writes: {sum(results)}")
        """

    def py_walk_directory(
        self,
        root_path: str | Path,
        pattern: str | None = None,
        recursive: bool = True
    ) -> list[str]:
        """Walk directory tree and collect file paths.

        Traverses a directory tree and collects file paths matching an
        optional pattern. Supports recursive traversal.

        Args:
            root_path: Root directory to start from
            pattern: Optional glob pattern to filter files (e.g., "*.txt", "**/*.py")
            recursive: Whether to traverse subdirectories (default: True)

        Returns:
            List of file paths (absolute paths)

        Example:
            >>> io_core = RustFileIOCore()
            >>> # Find all Python files
            >>> py_files = io_core.py_walk_directory("src", pattern="**/*.py")
            >>> print(f"Found {len(py_files)} Python files")
            >>>
            >>> # Find all files (no pattern)
            >>> all_files = io_core.py_walk_directory("data", recursive=True)
        """

class EncodingDetector:
    """Encoding detection utility using chardet.

    Detects text file encoding through statistical analysis of byte patterns.
    Uses the chardet library for accurate encoding detection.
    """

    @staticmethod
    def detect_encoding(data: bytes) -> str | None:
        """Detect encoding of byte data.

        Analyzes byte data to determine the most likely text encoding.
        Uses statistical analysis and heuristics for accurate detection.

        Args:
            data: Bytes to analyze (typically first few KB of file)

        Returns:
            Detected encoding name (e.g., 'utf-8', 'windows-1252', 'iso-8859-1'),
            or None if detection fails

        Example:
            >>> from classic_file_io import EncodingDetector
            >>> with open("file.txt", "rb") as f:
            ...     data = f.read(1024)  # Read first 1KB
            >>> encoding = EncodingDetector.detect_encoding(data)
            >>> print(f"Detected encoding: {encoding}")
        """
