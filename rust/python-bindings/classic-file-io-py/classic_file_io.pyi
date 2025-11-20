"""Type stubs for classic_file_io.

Python bindings for classic-file-io-core, providing high-performance async file I/O
operations with automatic encoding detection and DDS texture header parsing.
This module offers 10-40x speedup over Python's built-in file operations.

Architecture:
    - classic-file-io-core: Business logic (file I/O, encoding detection, DDS parsing)
    - classic-file-io-py: Python bindings (this module - PyO3 adapters)

Features:
    - Automatic encoding detection (chardet)
    - Async parallel file operations
    - DDS texture header parsing (40x speedup)
    - Directory walking
    - Intelligent caching
    - True async I/O (non-blocking)

Usage:
    import asyncio
    from classic_file_io import FileIOCore

    async def main():
        # Create file I/O core
        io_core = FileIOCore()

        # Read file with auto-detection (async)
        content = await io_core.read_file("config.txt")

        # Read multiple files in parallel (async)
        contents = await io_core.py_read_multiple_files(["file1.txt", "file2.txt"])

        # Parse DDS header (sync)
        header = io_core.read_dds_header("texture.dds")

    asyncio.run(main())
"""

from __future__ import annotations

from typing import Any, Coroutine

__version__: str

class FileIOCore:
    """High-performance async file I/O core with caching and encoding detection.

    Optimized file operations with 10x speedup over Python I/O through true async
    operations, parallel reading, and intelligent caching.

    The FileIOCore provides:
    - True async I/O (non-blocking coroutines)
    - Automatic text encoding detection
    - Parallel file operations for batch processing
    - DDS texture header parsing (40x faster)
    - Directory traversal utilities
    - Intelligent file content caching

    Note:
        All read/write methods return coroutines and must be awaited.
        Utility methods (file_exists, get_file_size, etc.) are synchronous.
    """

    def __init__(
        self,
        encoding: str = "utf-8",
        errors: str = "ignore",
        cache_size: int = 100,
        max_concurrent_io: int = 50
    ) -> None:
        """Create a new file I/O core with specified configuration.

        Initializes internal caching structures and async runtime for improved
        performance on file operations.

        Args:
            encoding: Default text encoding for file operations (default: "utf-8").
            errors: Error handling strategy for encoding issues (default: "ignore").
                   Possible values: "ignore", "strict", "replace".
            cache_size: Maximum number of cached file contents (default: 100).
            max_concurrent_io: Maximum concurrent I/O operations (default: 50).

        Example:
            >>> # Create with defaults
            >>> io_core = FileIOCore()
            >>> # Create with custom settings
            >>> io_core = FileIOCore(encoding="utf-8", errors="strict", cache_size=200)
        """

    def read_file(self, path: str) -> Coroutine[Any, Any, str]:
        """Read entire file as string with automatic encoding detection.

        Reads a text file asynchronously and returns its contents as a string.
        If no encoding was specified in constructor, automatically detects the
        file encoding using chardet.

        This method returns a coroutine that must be awaited.

        Args:
            path: File path to read (string or pathlib.Path converted to str)

        Returns:
            Coroutine that resolves to file contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails
            UnicodeDecodeError: If encoding is incorrect

        Example:
            >>> io_core = FileIOCore()
            >>> content = await io_core.read_file("config.txt")
        """

    def read_lines(self, path: str) -> Coroutine[Any, Any, list[str]]:
        """Read file as list of lines asynchronously.

        Reads a text file and returns its contents as a list of lines.
        Newline terminators are removed from each line.

        This method returns a coroutine that must be awaited.

        Args:
            path: File path to read (string or pathlib.Path converted to str)

        Returns:
            Coroutine that resolves to list of lines (without newline terminators)

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails

        Example:
            >>> io_core = FileIOCore()
            >>> lines = await io_core.read_lines("log.txt")
            >>> for line in lines:
            ...     print(line)
        """

    def read_bytes(self, path: str) -> Coroutine[Any, Any, bytes]:
        """Read entire file as raw bytes asynchronously.

        Reads a file in binary mode and returns its raw byte content.
        Useful for binary files or when encoding is unknown.

        This method returns a coroutine that must be awaited.

        Args:
            path: File path to read (string or pathlib.Path converted to str)

        Returns:
            Coroutine that resolves to file contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails

        Example:
            >>> io_core = FileIOCore()
            >>> data = await io_core.read_bytes("image.png")
            >>> print(f"File size: {len(data)} bytes")
        """

    def write_file(self, path: str, content: str) -> Coroutine[Any, Any, None]:
        """Write string content to file asynchronously.

        Writes text content to a file. Creates parent directories if they
        don't exist. Overwrites existing files.

        This method returns a coroutine that must be awaited.

        Args:
            path: Destination file path (string or pathlib.Path converted to str)
            content: String content to write

        Returns:
            Coroutine that resolves to None

        Raises:
            IOError: If write fails
            PermissionError: If lacking write permissions

        Example:
            >>> io_core = FileIOCore()
            >>> await io_core.write_file("output.txt", "Hello, World!")
        """

    def write_lines(self, path: str, lines: list[str]) -> Coroutine[Any, Any, None]:
        """Write list of lines to file asynchronously.

        Writes a list of lines to a file. Newline terminators are added
        automatically to each line.

        This method returns a coroutine that must be awaited.

        Args:
            path: Destination file path (string or pathlib.Path converted to str)
            lines: Lines to write (newlines added automatically)

        Returns:
            Coroutine that resolves to None

        Raises:
            IOError: If write fails
            PermissionError: If lacking write permissions

        Example:
            >>> io_core = FileIOCore()
            >>> lines = ["Line 1", "Line 2", "Line 3"]
            >>> await io_core.write_lines("output.txt", lines)
        """

    def write_bytes(self, path: str, data: bytes) -> Coroutine[Any, Any, None]:
        r"""Write raw bytes to file asynchronously.

        Writes binary data to a file. Creates parent directories if they
        don't exist. Overwrites existing files.

        This method returns a coroutine that must be awaited.

        Args:
            path: Destination file path (string or pathlib.Path converted to str)
            data: Bytes to write

        Returns:
            Coroutine that resolves to None

        Raises:
            IOError: If write fails
            PermissionError: If lacking write permissions

        Example:
            >>> io_core = FileIOCore()
            >>> data = b'\\x89PNG\\r\\n\\x1a\\n'
            >>> await io_core.write_bytes("image.png", data)
        """

    def append_file(self, path: str, content: str) -> Coroutine[Any, Any, None]:
        r"""Append string content to file asynchronously.

        Appends text content to the end of a file. Creates the file if it
        doesn't exist.

        This method returns a coroutine that must be awaited.

        Args:
            path: File path to append to (string or pathlib.Path converted to str)
            content: String content to append

        Returns:
            Coroutine that resolves to None

        Raises:
            IOError: If append fails
            PermissionError: If lacking write permissions

        Example:
            >>> io_core = FileIOCore()
            >>> await io_core.append_file("log.txt", "New log entry\\n")
        """

    def file_exists(self, path: str) -> bool:
        """Check if file exists (synchronous).

        Tests whether a file exists at the given path. Works for both
        files and directories. This is a fast synchronous operation.

        Args:
            path: File path to check (string or pathlib.Path converted to str)

        Returns:
            True if file exists, False otherwise

        Example:
            >>> io_core = FileIOCore()
            >>> if io_core.file_exists("config.txt"):
            ...     content = await io_core.read_file("config.txt")
        """

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes (synchronous).

        Returns the size of a file in bytes. This is a fast synchronous operation.
        Returns -1 if the file doesn't exist or an error occurs.

        Args:
            path: File path to check (string or pathlib.Path converted to str)

        Returns:
            File size in bytes, or -1 if file doesn't exist

        Example:
            >>> io_core = FileIOCore()
            >>> size = io_core.get_file_size("large_file.dat")
            >>> print(f"Size: {size / 1024 / 1024:.2f} MB")
        """

    def read_dds_header(self, path: str) -> tuple[int, int] | None:
        """Parse DDS texture file header (synchronous, 40x speedup).

        Parses the header of a DirectDraw Surface (DDS) texture file and
        extracts width and height. This is a synchronous operation.

        Args:
            path: Path to DDS file (string or pathlib.Path converted to str)

        Returns:
            Tuple of (width, height) in pixels, or None if invalid

        Example:
            >>> io_core = FileIOCore()
            >>> header = io_core.read_dds_header("texture.dds")
            >>> if header:
            ...     width, height = header
            ...     print(f"Size: {width}x{height}")
        """

    def read_dds_headers_batch(self, paths: list[str]) -> dict[str, tuple[int, int] | None]:
        """Parse multiple DDS headers in parallel (synchronous).

        Parses multiple DDS texture file headers in parallel for improved
        performance when processing many texture files. This is a synchronous
        operation that uses parallel processing internally.

        Args:
            paths: List of DDS file paths

        Returns:
            Dictionary mapping file paths to (width, height) tuples
            None values indicate invalid files

        Example:
            >>> io_core = FileIOCore()
            >>> texture_files = ["tex1.dds", "tex2.dds", "tex3.dds"]
            >>> headers = io_core.read_dds_headers_batch(texture_files)
            >>> for path, header in headers.items():
            ...     if header:
            ...         width, height = header
            ...         print(f"{path}: {width}x{height}")
        """

    def clear_cache(self) -> None:
        """Clear the file content cache to free memory (synchronous).

        Removes all cached file contents from memory. Useful for releasing
        memory after processing many files.

        Example:
            >>> io_core = FileIOCore()
            >>> # ... read many files ...
            >>> io_core.clear_cache()  # Free cached content
        """

    def py_walk_directory(
        self,
        path: str,
        pattern: str | None = None,
        max_depth: int | None = None
    ) -> list[str]:
        r"""Walk directory tree and collect file paths (synchronous).

        Traverses a directory tree and collects file paths matching an
        optional pattern. Supports depth limiting. This is a synchronous
        operation that uses parallel processing internally.

        Args:
            path: Root directory to start from
            pattern: Optional regex pattern to filter files
            max_depth: Maximum depth to recurse (None = unlimited)

        Returns:
            List of file paths (absolute paths as strings)

        Example:
            >>> io_core = FileIOCore()
            >>> # Find all Python files
            >>> py_files = io_core.py_walk_directory("src", pattern=r"\.py$")
            >>> print(f"Found {len(py_files)} Python files")
            >>>
            >>> # Find all files with depth limit
            >>> all_files = io_core.py_walk_directory("data", max_depth=2)
        """

    def py_read_multiple_files(
        self,
        paths: list[str]
    ) -> Coroutine[Any, Any, dict[str, str]]:
        """Read multiple files in parallel (asynchronous).

        Reads multiple text files in parallel for improved performance.
        Files are read concurrently with automatic concurrency control.

        This method returns a coroutine that must be awaited.

        Args:
            paths: List of file paths to read

        Returns:
            Coroutine that resolves to dictionary mapping paths to contents
            Empty strings indicate failed reads

        Example:
            >>> io_core = FileIOCore()
            >>> files = ["config1.txt", "config2.txt", "config3.txt"]
            >>> contents = await io_core.py_read_multiple_files(files)
            >>> for path, content in contents.items():
            ...     print(f"{path}: {len(content)} chars")
        """

    def py_write_multiple_files(
        self,
        files: dict[str, str]
    ) -> Coroutine[Any, Any, None]:
        """Write multiple files in parallel (asynchronous).

        Writes multiple files in parallel for improved performance.
        Files are written concurrently with automatic concurrency control.

        This method returns a coroutine that must be awaited.

        Args:
            files: Dictionary mapping file paths to content strings

        Returns:
            Coroutine that resolves to None

        Raises:
            IOError: If any write fails

        Example:
            >>> io_core = FileIOCore()
            >>> writes = {
            ...     "file1.txt": "Content 1",
            ...     "file2.txt": "Content 2",
            ...     "file3.txt": "Content 3"
            ... }
            >>> await io_core.py_write_multiple_files(writes)
        """

class DDSHeader:
    """DDS texture file header parser.

    Parses and validates DirectDraw Surface (DDS) texture files used in games.
    Provides detailed texture metadata and validation methods for proper
    texture configuration in modding workflows.

    This class provides access to:
    - Texture dimensions (width, height, depth)
    - Compression format (BC1-BC7, DXT1-DXT5, etc.)
    - Mipmap levels
    - Validation methods for texture conformance

    Example:
        >>> with open("texture.dds", "rb") as f:
        ...     data = f.read()
        >>> header = DDSHeader.from_bytes(data)
        >>> if header:
        ...     print(f"Size: {header.width}x{header.height}")
        ...     print(f"Format: {header.format}")
        ...     if header.is_bc_compressed() and not header.has_valid_bc_dimensions():
        ...         print("ERROR: Invalid BC compression dimensions")
    """

    width: int
    """Texture width in pixels."""

    height: int
    """Texture height in pixels."""

    depth: int
    """Texture depth (for 3D textures, 1 for 2D textures)."""

    mipmap_count: int
    """Number of mipmap levels."""

    format: str
    """Texture compression format (e.g., 'BC7', 'DXT5')."""

    @staticmethod
    def from_bytes(data: bytes) -> DDSHeader | None:
        """Parse DDS header from bytes.

        Args:
            data: Raw bytes of the DDS file (at least first 128 bytes)

        Returns:
            DDSHeader object if valid DDS file, None otherwise

        Raises:
            RuntimeError: If DDS parsing encounters an error

        Example:
            >>> with open("texture.dds", "rb") as f:
            ...     header = DDSHeader.from_bytes(f.read())
        """

    def has_power_of_2_dimensions(self) -> bool:
        """Check if dimensions are power of 2 (optimal for mipmaps).

        Returns:
            True if both width and height are powers of 2

        Example:
            >>> if header.has_power_of_2_dimensions():
            ...     print("Optimal for mipmaps")
        """

    def has_valid_bc_dimensions(self) -> bool:
        """Check if dimensions are valid for BC compression (multiple of 4).

        Returns:
            True if both width and height are multiples of 4

        Note:
            BC-compressed textures (BC1-BC7/DXT) require dimensions that are
            multiples of 4 for proper compression block alignment.

        Example:
            >>> if header.is_bc_compressed() and not header.has_valid_bc_dimensions():
            ...     print("ERROR: BC texture with invalid dimensions")
        """

    def is_reasonable_size(self) -> bool:
        """Check if dimensions are within reasonable bounds (1-16384 pixels).

        Returns:
            True if dimensions are reasonable for game textures

        Example:
            >>> if not header.is_reasonable_size():
            ...     print(f"WARNING: Unusual texture size {header.width}x{header.height}")
        """

    def has_mipmaps(self) -> bool:
        """Check if texture has mipmaps (mipmap_count > 1).

        Returns:
            True if texture has mipmap levels

        Example:
            >>> if not header.has_mipmaps():
            ...     print("No mipmaps - may cause performance issues")
        """

    def is_bc_compressed(self) -> bool:
        """Check if format is a BC compressed format.

        Returns:
            True if format is BC1-BC7 or DXT1-DXT5

        Example:
            >>> if header.is_bc_compressed():
            ...     print(f"BC-compressed: {header.format}")
        """

class EncodingDetector:
    """File encoding detection using chardet.

    Provides automatic text encoding detection for files with unknown
    encoding. Uses the chardet library to analyze byte patterns and
    determine the most likely encoding.

    Example:
        >>> detector = EncodingDetector()
        >>> with open("unknown_encoding.txt", "rb") as f:
        ...     data = f.read()
        >>> encoding = detector.detect_encoding(data)
        >>> print(f"Detected encoding: {encoding}")
    """

    def __init__(self) -> None:
        """Create a new encoding detector instance."""

    def detect_encoding(self, bytes: bytes) -> str:
        """Detect encoding from bytes.

        Args:
            bytes: Raw bytes to analyze for encoding detection

        Returns:
            Detected encoding name (e.g., 'utf-8', 'windows-1252')

        Example:
            >>> detector = EncodingDetector()
            >>> with open("file.txt", "rb") as f:
            ...     encoding = detector.detect_encoding(f.read())
        """

class FileHasher:
    """File hashing utilities with SHA256 and caching.

    Provides SHA256 hashing operations with intelligent caching and
    parallel batch processing. Ideal for verifying file integrity,
    detecting duplicates, and tracking file changes.

    Features:
    - SHA256 hash calculation with caching
    - Parallel batch hashing for multiple files
    - Automatic cache management

    Example:
        >>> # Single file hash
        >>> hash_val = FileHasher.hash_file("data.bin")
        >>> print(f"SHA256: {hash_val}")
        >>>
        >>> # Batch parallel hashing
        >>> files = ["file1.bin", "file2.bin", "file3.bin"]
        >>> hashes = FileHasher.hash_files_parallel(files)
        >>> for path, hash_val in hashes.items():
        ...     if hash_val:
        ...         print(f"{path}: {hash_val}")
    """

    @staticmethod
    def hash_file(path: str) -> str:
        """Calculate SHA256 hash of a file with caching.

        Args:
            path: Path to the file to hash

        Returns:
            Lowercase hexadecimal SHA256 hash (64 characters)

        Raises:
            RuntimeError: If file doesn't exist, cannot be read, or I/O error occurs

        Example:
            >>> hash_val = FileHasher.hash_file("game.exe")
            >>> print(len(hash_val))  # 64 (SHA256 is 256 bits = 64 hex chars)
            64
        """

    @staticmethod
    def hash_files_parallel(paths: list[str]) -> dict[str, str | None]:
        """Calculate SHA256 hashes for multiple files in parallel.

        Uses Rayon to parallelize hash calculations across available CPU cores.
        Files that fail to hash will have None values in the result.

        Args:
            paths: List of file paths to hash

        Returns:
            Dictionary mapping paths to hashes. Successful hashes are strings,
            failures are None.

        Raises:
            RuntimeError: If batch hashing fails

        Example:
            >>> files = ["file1.bin", "file2.bin", "nonexistent.bin"]
            >>> results = FileHasher.hash_files_parallel(files)
            >>> for path, hash_val in results.items():
            ...     if hash_val:
            ...         print(f"{path}: {hash_val}")
            ...     else:
            ...         print(f"{path}: FAILED")
        """

    @staticmethod
    def hash_files_to_map(paths: list[str]) -> dict[str, str]:
        """Calculate hashes and return only successful results.

        This is a convenience wrapper that filters out failures and returns
        only files that were successfully hashed.

        Args:
            paths: List of file paths to hash

        Returns:
            Dictionary mapping paths to hashes (failures excluded)

        Raises:
            RuntimeError: If batch hashing fails

        Example:
            >>> files = ["file1.bin", "file2.bin", "nonexistent.bin"]
            >>> hashes = FileHasher.hash_files_to_map(files)
            >>> print(len(hashes))  # Only successful hashes (e.g., 2)
            2
        """

    @staticmethod
    def clear_cache() -> None:
        """Clear the hash cache.

        Useful for testing or when files are known to have changed.

        Example:
            >>> FileHasher.clear_cache()
        """

    @staticmethod
    def cache_size() -> int:
        """Get the number of cached hashes.

        Returns:
            Number of hashes currently in cache

        Example:
            >>> count = FileHasher.cache_size()
            >>> print(f"Cached hashes: {count}")
        """

class PyLogCollector:
    """Crash log collection and organization.

    Organizes crash logs from multiple locations:
    - Copies logs from XSE folder (My Games) to Crash Logs
    - Moves logs from working directory to Crash Logs
    - Collects logs from custom scan directories

    This class helps centralize crash logs from various game and mod
    locations into a single organized directory for easier analysis.

    Example:
        >>> import asyncio
        >>> # Create log collector
        >>> collector = PyLogCollector(
        ...     base_folder=".",
        ...     xse_folder="C:/Users/Username/Documents/My Games/Fallout4/F4SE",
        ...     custom_folder=None
        ... )
        >>> # Collect all crash logs
        >>> async def main():
        ...     log_paths = await collector.collect_all()
        ...     print(f"Found {len(log_paths)} crash logs")
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        base_folder: str,
        xse_folder: str | None = None,
        custom_folder: str | None = None
    ) -> None:
        """Create a new LogCollector.

        Args:
            base_folder: Working directory where Crash Logs folder will be created
            xse_folder: Optional path to game's XSE folder (e.g., My Games/Fallout4/F4SE)
            custom_folder: Optional path to custom scan directory
        """

    def collect_all(self) -> list[str]:
        """Execute full log collection workflow (synchronous).

        This performs all log collection steps in order:
        1. Ensure directory structure exists
        2. Move logs from base folder to Crash Logs
        3. Copy logs from XSE folder to Crash Logs
        4. Collect all crash log paths for processing

        Returns:
            List of paths to all crash log files

        Raises:
            IOError: If file operations fail

        Example:
            >>> collector = PyLogCollector(base_folder=".")
            >>> log_paths = collector.collect_all()  # No await needed!
            >>> print(f"Found {len(log_paths)} crash logs")
        """

    def move_from_base_folder(self) -> int:
        """Move crash logs and AUTOSCAN reports from base folder (synchronous).

        Returns:
            Number of files moved

        Raises:
            IOError: If file operations fail
        """

    def copy_from_xse_folder(self) -> int:
        """Copy crash logs from XSE folder (synchronous).

        This is where the game stores crash logs. We copy (not move) them to preserve
        the originals in case the user wants to reference them.

        Returns:
            Number of files copied

        Raises:
            IOError: If file operations fail
        """

    def collect_crash_logs(self) -> list[str]:
        """Collect all crash log file paths (synchronous).

        This searches for crash-*.log files in:
        - Crash Logs directory (after moving/copying operations)
        - Custom scan folder (if configured)

        Returns:
            List of paths to all crash log files found

        Raises:
            IOError: If file operations fail
        """

    def crash_logs_dir(self) -> str:
        """Get the path to the Crash Logs directory.

        Returns:
            Path to Crash Logs directory as a string
        """

    def pastebin_dir(self) -> str:
        """Get the path to the Pastebin subdirectory.

        Returns:
            Path to Pastebin directory as a string

        Example:
            >>> collector = PyLogCollector(base_folder=".")
            >>> pastebin_dir = collector.pastebin_dir()
            >>> print(f"Pastebin directory: {pastebin_dir}")
        """

class FileGeneratorConfig:
    r"""Configuration for file generation.

    Holds configuration data for generating CLASSIC configuration files.
    Used by FileGenerator to create properly structured files with
    game-specific paths and content.

    Example:
        >>> config = FileGeneratorConfig(
        ...     ignore_file_content="# Ignore patterns\\n*.tmp",
        ...     local_yaml_content="# Local config\\nCustomPath: C:\\\\Mods",
        ...     game_name="Fallout4"
        ... )
        >>> print(config.game_name)
        Fallout4
    """

    ignore_file_content: str
    """Default content for CLASSIC Ignore.yaml."""

    local_yaml_content: str
    """Default content for local YAML file."""

    game_name: str
    """Game name for local YAML path (e.g., 'Fallout4', 'Skyrim')."""

    def __init__(
        self,
        ignore_file_content: str,
        local_yaml_content: str,
        game_name: str
    ) -> None:
        """Create a new file generator configuration.

        Args:
            ignore_file_content: Default content for CLASSIC Ignore.yaml
            local_yaml_content: Default content for local YAML file
            game_name: Game name for local YAML path (e.g., "Fallout4", "Skyrim")
        """

class FileGenerator:
    r"""File generation operations.

    Generates CLASSIC configuration files with proper structure and content.
    Handles creation of both Ignore.yaml and game-specific local YAML files.

    Features:
    - Async file generation with proper error handling
    - Automatic directory creation
    - Concurrent file generation support
    - Idempotent operations (only creates if missing)

    Example:
        >>> import asyncio
        >>> config = FileGeneratorConfig(
        ...     ignore_file_content="# Patterns\\n*.tmp",
        ...     local_yaml_content="# Config",
        ...     game_name="Fallout4"
        ... )
        >>> generator = FileGenerator(config)
        >>> async def main():
        ...     ignore_created = await generator.generate_ignore_file_async()
        ...     local_created = await generator.generate_local_yaml_async()
        ...     print(f"Ignore: {ignore_created}, Local: {local_created}")
        >>> asyncio.run(main())
    """

    def __init__(self, config: FileGeneratorConfig) -> None:
        """Create a new file generator.

        Args:
            config: File generation configuration
        """

    def generate_ignore_file_async(self) -> Coroutine[Any, Any, bool]:
        """Generate CLASSIC Ignore.yaml if it doesn't exist (async).

        Creates the ignore file with default content from configuration.
        The file is written in UTF-8 encoding.

        Returns:
            Coroutine that resolves to True if file was generated,
            False if it already existed

        Raises:
            IOError: If file I/O fails
            PermissionError: If lacking permissions to write file

        Example:
            >>> generator = FileGenerator(config)
            >>> created = await generator.generate_ignore_file_async()
            >>> if created:
            ...     print("Ignore file created")
        """

    def generate_local_yaml_async(self) -> Coroutine[Any, Any, bool]:
        """Generate CLASSIC Data/CLASSIC <GAME> Local.yaml if it doesn't exist (async).

        Creates the local YAML file with default content from configuration,
        where <GAME> is dynamically determined from config.
        The file is written in UTF-8 encoding.
        Creates parent directories if they don't exist.

        Returns:
            Coroutine that resolves to True if file was generated,
            False if it already existed

        Raises:
            IOError: If file I/O or directory creation fails
            PermissionError: If lacking permissions to create directory/file

        Example:
            >>> generator = FileGenerator(config)
            >>> created = await generator.generate_local_yaml_async()
            >>> if created:
            ...     print("Local YAML created")
        """

    def generate_all_files_async(self) -> Coroutine[Any, Any, tuple[bool, bool]]:
        """Generate all files asynchronously with concurrent execution.

        Generates both the ignore file and local YAML file concurrently.
        Uses Tokio's try_join for fail-fast error handling.

        Returns:
            Coroutine that resolves to (ignore_generated, local_yaml_generated)
            indicating which files were created

        Raises:
            IOError: If any file generation fails
            PermissionError: If lacking permissions

        Example:
            >>> generator = FileGenerator(config)
            >>> ignore_created, local_created = await generator.generate_all_files_async()
            >>> print(f"Generated: ignore={ignore_created}, local={local_created}")
        """

    def ignore_file_path(self) -> str:
        """Get the ignore file path.

        Returns:
            Path to CLASSIC Ignore.yaml
        """

    def local_yaml_path(self) -> str:
        """Get the local YAML file path.

        Returns:
            Path to CLASSIC Data/CLASSIC <GAME> Local.yaml
        """

    def config(self) -> FileGeneratorConfig:
        """Get the configuration.

        Returns:
            FileGeneratorConfig object
        """

async def generate_ignore_file_async(content: str) -> bool:
    r"""Generate CLASSIC Ignore.yaml if it doesn't exist (async).

    Standalone function that creates the ignore file with provided content.

    Args:
        content: Default content for CLASSIC Ignore.yaml

    Returns:
        True if the file was generated, False if it already existed

    Raises:
        IOError: If file I/O fails
        PermissionError: If lacking permissions to write file

    Example:
        >>> import asyncio
        >>> from classic_file_io import generate_ignore_file_async
        >>> result = asyncio.run(generate_ignore_file_async("# Ignore patterns\\n*.tmp"))
        >>> print(f"File generated: {result}")
    """

async def generate_local_yaml_async(content: str, game_name: str) -> bool:
    """Generate CLASSIC Data/CLASSIC <GAME> Local.yaml if it doesn't exist (async).

    Standalone function that creates the local YAML file with provided content.

    Args:
        content: Default content for local YAML file
        game_name: Game name for local YAML path (e.g., "Fallout4", "Skyrim")

    Returns:
        True if the file was generated, False if it already existed

    Raises:
        IOError: If file I/O or directory creation fails
        PermissionError: If lacking permissions

    Example:
        >>> import asyncio
        >>> from classic_file_io import generate_local_yaml_async
        >>> result = asyncio.run(generate_local_yaml_async("# Config", "Fallout4"))
        >>> print(f"File generated: {result}")
    """
