"""DDS texture file processing utilities."""

import asyncio
import mmap
import struct
from pathlib import Path
from typing import Optional

# Try to import enhanced analyzer for advanced features
try:
    from .dds_analyzer import EnhancedDDSAnalyzer, DDSInfo, analyze_dds
    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False
    DDSInfo = None


class DDSProcessor:
    """Handles DDS texture file validation and processing."""

    def __init__(self, dds_read_semaphore: asyncio.Semaphore, use_enhanced: bool = False) -> None:
        """Initialize with semaphore for concurrency control.

        Args:
            dds_read_semaphore: Semaphore for controlling concurrent reads
            use_enhanced: Whether to use enhanced analyzer for detailed analysis
        """
        self.dds_read_semaphore = dds_read_semaphore
        self.use_enhanced = use_enhanced and HAS_ANALYZER
        self.analyzer: Optional[EnhancedDDSAnalyzer] = None
        if self.use_enhanced:
            self.analyzer = EnhancedDDSAnalyzer()

    def read_dds_header_mmap(self, file_path: Path) -> tuple[int, int] | None:
        """Read DDS header using memory mapping for efficiency."""
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
        """Get detailed DDS information using enhanced analyzer.

        Returns:
            DDSInfo object with comprehensive texture details, or None if not available
        """
        if self.analyzer:
            return self.analyzer.analyze_file(file_path)
        return None

    async def get_detailed_info_async(self, file_path: Path) -> DDSInfo | None:
        """Async version of get_detailed_info."""
        if self.analyzer:
            return await self.analyzer.analyze_file_async(file_path)
        return None

    def validate_dds_for_game(self, file_path: Path, game: str = "Fallout4") -> list[str]:
        """Validate a DDS file against game-specific requirements.

        Args:
            file_path: Path to DDS file
            game: Game name for specific validation rules

        Returns:
            List of validation issues, empty if valid
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
        """Check a batch of DDS files for dimension issues asynchronously."""
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
