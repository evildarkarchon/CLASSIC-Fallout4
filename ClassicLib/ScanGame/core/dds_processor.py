"""DDS texture file processing utilities."""

import asyncio
import mmap
import struct
from pathlib import Path


class DDSProcessor:
    """Handles DDS texture file validation and processing."""

    def __init__(self, dds_read_semaphore: asyncio.Semaphore) -> None:
        """Initialize with semaphore for concurrency control."""
        self.dds_read_semaphore = dds_read_semaphore

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

    async def check_dds_batch_async(self, dds_files: list[tuple[Path, Path]], issue_lists: dict, issue_locks: dict) -> None:
        """Check a batch of DDS files for dimension issues asynchronously."""
        async with self.dds_read_semaphore:
            # Run header reading in executor to avoid blocking
            loop = asyncio.get_event_loop()
            for dds_file, mod_dir in dds_files:
                dimensions = await loop.run_in_executor(None, self.read_dds_header_mmap, dds_file)
                if dimensions:
                    width, height = dimensions
                    if width % 2 != 0 or height % 2 != 0:
                        async with issue_locks["tex_dims"]:
                            issue_lists["tex_dims"].append(f"  MOD > {mod_dir.name}\\{dds_file.relative_to(mod_dir)}\n")
