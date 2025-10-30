"""DDS texture file processing utilities."""

import asyncio
import mmap
import struct
from pathlib import Path

# Try to import enhanced analyzer for advanced features
try:
    from .dds_analyzer import DDSInfo, EnhancedDDSAnalyzer, analyze_dds
    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False
    DDSInfo = None


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
        if self.use_enhanced:
            self.analyzer = EnhancedDDSAnalyzer()

    def read_dds_header_mmap(self, file_path: Path) -> tuple[int, int] | None:
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
        The method uses an available analyzer for detailed validation, if present; otherwise,
        it performs basic validation, verifying dimensions and other attributes of the DDS file.

        Args:
            file_path (Path): Path to the DDS file to be validated.
            game (str): Name of the target game the DDS should be validated for. Defaults to "Fallout4".

        Returns:
            list[str]: A list of issues identified during the validation. If the file passes validation,
                it may return an empty list. It returns a message indicating any validation failure
                or inability to parse the file.
        """
        if self.analyzer:
            info = self.analyzer.analyze_file(file_path)
            if info:
                return self.analyzer.validate_for_game(info, game)

        # Fallback to basic validation
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

    async def check_dds_batch_async(self, dds_files: list[tuple[Path, Path]], issue_lists: dict, issue_locks: dict) -> None:
        """
        Performs a batch check on DDS files asynchronously, analyzing texture dimensions and
        validating them for compatibility with "Fallout 4". Depending on the configuration,
        it uses either enhanced file analysis or basic dimension checks. Discovered issues
        are recorded in the `issue_lists` dictionary under the associated issue category.

        Args:
            dds_files (list[tuple[Path, Path]]): List of tuples, each containing the path to
                a DDS file and its associated mod directory.
            issue_lists (dict): Dictionary for collecting issue descriptions organized by
                issue category (e.g., texture dimensions).
            issue_locks (dict): Dictionary containing asynchronous locks to ensure thread-safe
                updates to `issue_lists`.

        Returns:
            None
        """
        async with self.dds_read_semaphore:
            # Run header reading in executor to avoid blocking
            loop = asyncio.get_event_loop()
            for dds_file, mod_dir in dds_files:
                if self.use_enhanced and self.analyzer:
                    # Use enhanced analysis for more detailed checks
                    info = await self.analyzer.analyze_file_async(dds_file)
                    if info:
                        issues = self.analyzer.validate_for_game(info, "Fallout4")
                        if issues:
                            async with issue_locks["tex_dims"]:
                                rel_path = dds_file.relative_to(mod_dir)
                                for issue in issues:
                                    issue_lists["tex_dims"].append(
                                        f"  MOD > {mod_dir.name}\\{rel_path}: {issue}\n"
                                    )
                else:
                    # Use basic dimension checking
                    dimensions = await loop.run_in_executor(None, self.read_dds_header_mmap, dds_file)
                    if dimensions:
                        width, height = dimensions
                        if width % 2 != 0 or height % 2 != 0:
                            async with issue_locks["tex_dims"]:
                                issue_lists["tex_dims"].append(f"  MOD > {mod_dir.name}\\{dds_file.relative_to(mod_dir)}\n")
