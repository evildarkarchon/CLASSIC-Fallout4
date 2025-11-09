"""DDS texture file processing utilities with Rust acceleration."""

from __future__ import annotations

import asyncio
import mmap
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from classic_file_io import DDSHeader as RustDDSHeader

    from ClassicLib.ScanGame.core.dds_analyzer import DDSInfo, EnhancedDDSAnalyzer

# Try to import Rust DDS parser (10-50x faster) - runtime import
try:
    from classic_file_io import DDSHeader as _RuntimeRustDDSHeader

    HAS_RUST_DDS = True
except ImportError:
    HAS_RUST_DDS = False
    _RuntimeRustDDSHeader = None

# Try to import enhanced analyzer for advanced features (runtime import)
try:
    from ClassicLib.ScanGame.core.dds_analyzer import EnhancedDDSAnalyzer as _RuntimeEnhancedDDSAnalyzer

    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False
    _RuntimeEnhancedDDSAnalyzer = None


class DDSProcessor:
    """
    Handles processing and validation of DDS (DirectDraw Surface) files, including header reading,
    detailed analysis, and validation for specific game requirements.

    This class provides various methods to read DDS file headers, perform enhanced analysis when
    available, and validate DDS files for specific game constraints. With support for both
    synchronous and asynchronous operations, it is designed to handle single or batch processing
    of DDS files efficiently. The class also includes concurrency control through a semaphore.

    Attributes:
        dds_read_semaphore (asyncio.Semaphore): Semaphore instance for controlling concurrent reads.
        use_enhanced (bool): Flag indicating whether enhanced analysis is enabled.
        analyzer (EnhancedDDSAnalyzer | None): Instance of the `EnhancedDDSAnalyzer` class or None if
            enhanced analyzer is not utilized.
    """

    def __init__(self, dds_read_semaphore: asyncio.Semaphore, use_enhanced: bool = False) -> None:
        """
        Initializes an instance of the class with required synchronization and optional enhanced functionality.

        Args:
            dds_read_semaphore (asyncio.Semaphore): A semaphore instance used to manage concurrent
                access to DDS reading operations.
            use_enhanced (bool, optional): Flag to determine whether enhanced features should
                be utilized. Default is False.
        """
        self.dds_read_semaphore = dds_read_semaphore
        self.use_enhanced = use_enhanced and HAS_ANALYZER
        self.analyzer: EnhancedDDSAnalyzer | None = None
        if self.use_enhanced and _RuntimeEnhancedDDSAnalyzer is not None:
            self.analyzer = _RuntimeEnhancedDDSAnalyzer()

    @staticmethod
    def read_dds_header_rust(file_path: Path) -> RustDDSHeader | None:
        """
        Reads the header of a DirectDraw Surface (DDS) file using the Rust parser (10-50x faster).

        This method uses the Rust-based DDSHeader parser which provides full format information,
        validation methods, and better error handling than the mmap-based approach.

        Args:
            file_path (Path): The path to the DDS file.

        Returns:
            RustDDSHeader | None: A DDSHeader object with full texture information, or None if
            the file is not a valid DDS file or Rust acceleration is not available.

        Example:
            >>> header = processor.read_dds_header_rust(Path("texture.dds"))
            >>> if header:
            ...     print(f"Size: {header.width}x{header.height}")
            ...     print(f"Format: {header.format}")
            ...     if not header.has_power_of_2_dimensions():
            ...         print("Warning: Non-power-of-2 dimensions")
        """
        if not HAS_RUST_DDS:
            return None

        try:
            # Read first 256 bytes (enough for DDS header including DX10 extension)
            with file_path.open("rb") as f:
                header_bytes = f.read(256)

            if _RuntimeRustDDSHeader is not None:
                return _RuntimeRustDDSHeader.from_bytes(header_bytes)
            return None  # noqa: TRY300
        except (OSError, ValueError):
            return None

    @staticmethod
    def read_dds_header_mmap(file_path: Path) -> tuple[int, int] | None:
        """
        Reads the header of a DirectDraw Surface (DDS) file using memory mapping to extract
        the width and height. This function checks if the file has the correct DDS signature
        and retrieves the width and height values from the header.

        Args:
            file_path (Path): The path to the DDS file.

        Returns:
            tuple[int, int] | None: A tuple containing the width and height of the DDS file.
            Returns None if the file is not a valid DDS file, is too small, or an error
            occurs during reading.
        """
        try:
            with file_path.open("rb") as f:
                # Check if file is at least 20 bytes
                f.seek(0, 2)  # Seek to end
                file_size = f.tell()
                if file_size < 20:
                    return None
                f.seek(0)  # Seek back to start

                # Use mmap for efficient header reading
                with mmap.mmap(f.fileno(), length=20, access=mmap.ACCESS_READ) as mm:
                    if mm[:4] == b"DDS ":
                        width = struct.unpack("<I", mm[12:16])[0]
                        height = struct.unpack("<I", mm[16:20])[0]
                        return width, height
        except (OSError, ValueError):
            return None
        return None

    def get_detailed_info(self, file_path: Path) -> DDSInfo | None:
        """
        Analyzes a file and retrieves detailed information.

        This method processes the given file path using the `analyze_file`
        method of the `analyzer` attribute, if available. If no `analyzer`
        is set, it returns None.

        Args:
            file_path (Path): Path to the file that needs to be analyzed.

        Returns:
            DDSInfo | None: Returns an instance of `DDSInfo` if the file
            is successfully analyzed; otherwise, returns None.
        """
        if self.analyzer:
            return self.analyzer.analyze_file(file_path)
        return None

    async def get_detailed_info_async(self, file_path: Path) -> DDSInfo | None:
        """
        Analyzes a file asynchronously to retrieve detailed DDS (Direct Draw Surface) file information.

        The method utilizes an analyzer object to perform asynchronous analysis on the provided file
        and returns the detailed DDS information if available. If no analyzer is defined, the method
        returns None.

        Args:
            file_path (Path): The path of the file to be analyzed.

        Returns:
            DDSInfo | None: The detailed information of the DDS file if the analysis is successful,
            otherwise None.
        """
        if self.analyzer:
            return await self.analyzer.analyze_file_async(file_path)
        return None

    def validate_dds_for_game(self, file_path: Path, game: str = "Fallout4") -> list[str]:
        """
        Validates a DDS (DirectDraw Surface) file for compatibility with a specified game.

        This method uses multiple validation strategies in order of preference:
        1. Rust-based parser (fastest, most accurate)
        2. Enhanced analyzer (if available and enabled)
        3. Basic mmap-based validation (fallback)

        Args:
            file_path (Path): Path to the DDS file to be validated.
            game (str): Name of the target game the DDS should be validated for. Defaults to "Fallout4".

        Returns:
            list[str]: A list of issues identified during the validation. If the file passes validation,
                it returns an empty list. Returns a message indicating validation failure if unable
                to parse the file.
        """
        # Try Rust parser first (fastest and most accurate)
        if HAS_RUST_DDS:
            header = self.read_dds_header_rust(file_path)
            if header:
                issues = []

                # Check for reasonable size
                if not header.is_reasonable_size():
                    issues.append(f"Unusual texture size: {header.width}x{header.height}")

                # Check BC compression requirements
                if header.is_bc_compressed() and not header.has_valid_bc_dimensions():
                    issues.append(f"BC-compressed texture has invalid dimensions (must be multiple of 4): {header.width}x{header.height}")

                # Check for power-of-2 dimensions (recommended for mipmaps)
                if not header.has_power_of_2_dimensions():
                    issues.append(f"Non-power-of-2 dimensions (may reduce performance): {header.width}x{header.height}")

                # Check for mipmaps (recommended for game textures)
                if not header.has_mipmaps():
                    issues.append("No mipmaps (may cause performance issues)")

                # Check for very large textures
                if header.width > 4096 or header.height > 4096:
                    issues.append(f"Very large texture dimensions: {header.width}x{header.height}")

                return issues

        # Fall back to enhanced analyzer if available
        if self.analyzer:
            info = self.analyzer.analyze_file(file_path)
            if info:
                return self.analyzer.validate_for_game(info, game)

        # Final fallback to basic mmap validation
        dimensions = self.read_dds_header_mmap(file_path)
        if dimensions:
            width, height = dimensions
            issues = []
            if width % 2 != 0 or height % 2 != 0:
                issues.append(f"Non-even dimensions: {width}x{height}")
            if width > 4096 or height > 4096:
                issues.append(f"Large texture dimensions: {width}x{height}")
            return issues

        return ["Unable to read DDS header"]

    async def _process_single_dds_file(
        self, dds_file: Path, mod_dir: Path
    ) -> list[str]:
        """
        Process a single DDS file and return any validation issues.

        Args:
            dds_file: Path to the DDS file to validate.
            mod_dir: Path to the mod directory containing the file.

        Returns:
            List of formatted issue strings ready to append to issue_lists.
            Empty list if no issues found.
        """
        loop = asyncio.get_event_loop()

        # Try Rust parser first (much faster and more accurate)
        if HAS_RUST_DDS:
            issues = await loop.run_in_executor(None, self.validate_dds_for_game, dds_file, "Fallout4")
            if issues:
                rel_path = dds_file.relative_to(mod_dir)
                return [f"  MOD > {mod_dir.name}\\{rel_path}: {issue}\n" for issue in issues]
            return []

        # Use enhanced analysis for more detailed checks
        if self.use_enhanced and self.analyzer:
            info = await self.analyzer.analyze_file_async(dds_file)
            if info:
                issues = self.analyzer.validate_for_game(info, "Fallout4")
                if issues:
                    rel_path = dds_file.relative_to(mod_dir)
                    return [f"  MOD > {mod_dir.name}\\{rel_path}: {issue}\n" for issue in issues]
            return []

        # Use basic dimension checking (fallback)
        dimensions = await loop.run_in_executor(None, self.read_dds_header_mmap, dds_file)
        if dimensions:
            width, height = dimensions
            if width % 2 != 0 or height % 2 != 0:
                return [f"  MOD > {mod_dir.name}\\{dds_file.relative_to(mod_dir)}\n"]

        return []

    async def check_dds_batch_async(self, dds_files: list[tuple[Path, Path]], issue_lists: dict, issue_locks: dict) -> None:
        """
        Performs a batch check on DDS files asynchronously, analyzing texture dimensions and
        validating them for compatibility with "Fallout 4".

        This method uses multiple validation strategies in order of preference:
        1. Rust-based parser (fastest, 10-50x speedup)
        2. Enhanced analyzer (if available and enabled)
        3. Basic mmap-based dimension checks (fallback)

        Args:
            dds_files (list[tuple[Path, Path]]): List of tuples, each containing the path to
                a DDS file and its associated mod directory.
            issue_lists (dict): Dictionary for collecting issue descriptions organized by
                issue category (e.g., texture dimensions).
            issue_locks (dict): Dictionary containing asynchronous locks to ensure thread-safe
                updates to `issue_lists`.
        """
        async with self.dds_read_semaphore:
            for dds_file, mod_dir in dds_files:
                issues = await self._process_single_dds_file(dds_file, mod_dir)
                if issues:
                    async with issue_locks["tex_dims"]:
                        issue_lists["tex_dims"].extend(issues)
