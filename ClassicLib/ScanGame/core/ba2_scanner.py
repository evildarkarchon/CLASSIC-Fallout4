"""BA2 archive scanner component for CLASSIC_ScanGame.

This module provides specialized scanning functionality for Bethesda BA2 archive files,
including texture (DX10) and general (GNRL) format processing. It handles subprocess
coordination with BSArch.exe for archive inspection and validation.
"""

import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor
from itertools import starmap
from pathlib import Path

try:
    import aiofiles
except ImportError:
    aiofiles = None  # Handle gracefully if not installed

from ClassicLib import msg_error, msg_info, msg_warning


class BA2ArchiveScanner:
    """Handle BA2 archive scanning and analysis.

    This class provides specialized functionality for scanning and validating Bethesda
    BA2 archive files, supporting both texture-format (DX10) and general-format (GNRL)
    archives. It coordinates with BSArch.exe for archive inspection and performs
    comprehensive validation of textures, sounds, and other game assets.

    Attributes:
        process_semaphore (asyncio.Semaphore): Semaphore to limit concurrent subprocess execution.
        walk_executor (ThreadPoolExecutor): Thread pool for handling async directory operations.

    """

    def __init__(self, process_semaphore: asyncio.Semaphore, walk_executor: ThreadPoolExecutor) -> None:
        """Initialize the BA2ArchiveScanner.

        Args:
            process_semaphore: Semaphore to control concurrent subprocess execution.
            walk_executor: Thread pool executor for async directory operations.

        """
        self.process_semaphore = process_semaphore
        self.walk_executor = walk_executor

    async def find_ba2_files_async(self, mod_path: Path) -> list[tuple[Path, str]]:
        """Find all BA2 files in the mod directory.

        This method recursively searches the specified directory for all .ba2 and .BA2
        files, excluding specific files like "prp - main.ba2". The search is performed
        asynchronously to avoid blocking.

        Args:
            mod_path: The mod directory path to search.

        Returns:
            List of tuples containing BA2 file path and filename.

        Example:
            >>> scanner = BA2ArchiveScanner(semaphore, executor)
            >>> files = await scanner.find_ba2_files_async(Path("/mods"))
            >>> len(files)
            15

        """

        def _find() -> list[tuple[Path, str]]:
            """Optimized BA2 file finding using pathlib.rglob().

            Returns:
                list[tuple[Path, str]]: List of BA2 file paths and filenames.

            """
            result = []
            try:
                # Use rglob to find all .ba2 files directly - much faster
                for ba2_path in mod_path.rglob("*.ba2"):
                    filename = ba2_path.name
                    filename_lower = filename.lower()
                    if filename_lower != "prp - main.ba2":
                        result.append((ba2_path, filename))

                # Also check for uppercase extension on case-sensitive systems
                for ba2_path in mod_path.rglob("*.BA2"):
                    filename = ba2_path.name
                    filename_lower = filename.lower()
                    if filename_lower != "prp - main.ba2" and (ba2_path, filename) not in result:
                        result.append((ba2_path, filename))

            except (OSError, PermissionError):
                # Return empty list if we can't access the directory
                pass

            return result

        # Collect all BA2 files
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self.walk_executor, _find)
        except OSError as e:
            msg_error(f"Error scanning for BA2 files: {e}")
            return []

    async def process_ba2_files_async(
        self, ba2_files: list[tuple[Path, str]], bsarch_path: Path, xse_scriptfiles: dict[str, str]
    ) -> list[dict[str, set[str]]]:
        """Process multiple BA2 files concurrently.

        This method processes all provided BA2 files concurrently, using the process
        semaphore to control the number of simultaneous subprocess executions. Each
        file is analyzed for format issues, texture problems, sound format issues,
        and other asset validation concerns.

        Args:
            ba2_files: List of BA2 file tuples (path, filename).
            bsarch_path: Path to BSArch executable.
            xse_scriptfiles: Dictionary of XSE script files.

        Returns:
            List of dictionaries containing detected issues for each file.

        Example:
            >>> results = await scanner.process_ba2_files_async(files, bsarch, xse)
            >>> for result in results:
            ...     if result["tex_frmt"]:
            ...         print(f"Found texture format issues: {len(result['tex_frmt'])}")

        """

        async def process_single_ba2(file_path: Path, filename: str) -> dict[str, set[str]]:
            """Process a single BA2 file to identify and collect potential issues.

            The function first determines the format of the BA2 file and accordingly processes
            either texture-format or general-format files. It uses BSArch for extracting file data
            and validates various aspects such as texture dimensions, sound formats, and the
            presence of specific file groups like animation data or previs files.

            Args:
                file_path: The path to the BA2 file to be processed.
                filename: The name of the BA2 file.

            Returns:
                Dictionary categorizing identified issues with the BA2 file.

            """
            local_issues: dict[str, set[str]] = {
                "ba2_frmt": set(),
                "tex_dims": set(),
                "tex_frmt": set(),
                "snd_frmt": set(),
                "xse_file": set(),
            }

            # Read BA2 header
            header = await self.read_ba2_header_async(file_path, filename)
            if header is None:
                return local_issues

            # Validate BA2 format
            if not self.validate_ba2_header(header, filename, local_issues):
                return local_issues

            async with self.process_semaphore:  # Limit concurrent subprocesses
                if header[8:] == b"DX10":
                    # Process texture-format BA2
                    texture_issues = await self.process_texture_ba2_async(file_path, filename, bsarch_path)
                    local_issues.update(texture_issues)
                else:
                    # Process general-format BA2
                    general_issues = await self.process_general_ba2_async(file_path, filename, bsarch_path, xse_scriptfiles)
                    local_issues.update(general_issues)

            return local_issues

        # Process BA2 files with improved concurrency control
        msg_info(f"Processing {len(ba2_files)} BA2 files with dynamic batching...")

        # Create all tasks upfront - let the semaphore handle concurrency naturally
        # The semaphore in process_single_ba2 already limits concurrent subprocesses,
        # so we don't need artificial batching or delays
        all_tasks = list(starmap(process_single_ba2, ba2_files))

        # Process all tasks with natural backpressure from the semaphore
        # This is more efficient than artificial batching with delays
        raw_results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Filter out exceptions and log them, returning only successful results
        results: list[dict[str, set[str]]] = []
        for result in raw_results:
            if isinstance(result, Exception):
                msg_error(f"BA2 processing task failed with exception: {result}")
            elif isinstance(result, dict):
                results.append(result)

        return results

    @staticmethod
    async def read_ba2_header_async(file_path: Path, filename: str) -> bytes | None:
        """Read the BA2 file header asynchronously.

        This method reads the first 12 bytes of a BA2 file, which contain the file
        signature and format identifier. Uses aiofiles if available for true async I/O.

        Args:
            file_path: The path to the BA2 file.
            filename: The name of the BA2 file for error reporting.

        Returns:
            The 12-byte header if successful, None if read fails.

        Example:
            >>> header = await BA2ArchiveScanner.read_ba2_header_async(path, "mod.ba2")
            >>> header[:4]
            b'BTDX'

        """
        try:
            if aiofiles:
                async with aiofiles.open(file_path, "rb") as f:
                    return await f.read(12)
            else:
                # Fallback to sync read if aiofiles not available
                with file_path.open("rb") as f:
                    return f.read(12)
        except OSError:
            msg_warning(f"Failed to read file: {filename}")
            return None

    @staticmethod
    def validate_ba2_header(header: bytes, filename: str, local_issues: dict[str, set[str]]) -> bool:
        """Validate BA2 file header format.

        Checks if the header contains the correct BA2 signature (BTDX) and a valid
        format identifier (DX10 for textures or GNRL for general archives).

        Args:
            header: The BA2 file header bytes.
            filename: The name of the BA2 file for error reporting.
            local_issues: Dictionary to store format issues if validation fails.

        Returns:
            True if header is valid, False otherwise.

        Example:
            >>> issues = {"ba2_frmt": set()}
            >>> BA2ArchiveScanner.validate_ba2_header(b"BTDX....DX10", "mod.ba2", issues)
            True

        """
        if header[:4] != b"BTDX" or header[8:] not in {b"DX10", b"GNRL"}:
            local_issues["ba2_frmt"].add(f"  - {filename} : {header!s}\n")
            return False
        return True

    async def process_texture_ba2_async(self, file_path: Path, filename: str, bsarch_path: Path) -> dict[str, set[str]]:
        """Process a texture-format BA2 file (DX10).

        Uses BSArch.exe to dump texture information from the archive and validates
        texture formats and dimensions. Checks for non-DDS textures and odd-numbered
        dimensions that can cause issues in-game.

        Args:
            file_path: The path to the BA2 file.
            filename: The name of the BA2 file.
            bsarch_path: Path to BSArch executable.

        Returns:
            Dictionary of detected texture issues.

        Raises:
            TimeoutError: If BSArch subprocess exceeds 30 second timeout.
            OSError: If subprocess execution fails.

        Example:
            >>> issues = await scanner.process_texture_ba2_async(path, "textures.ba2", bsarch)
            >>> if issues["tex_dims"]:
            ...     print("Found dimension issues")

        """
        local_issues: dict[str, set[str]] = {"tex_dims": set(), "tex_frmt": set()}
        proc: asyncio.subprocess.Process | None = None  # Initialize to None for exception handler access

        try:
            proc = await asyncio.create_subprocess_exec(
                str(bsarch_path),
                str(file_path),
                "-dump",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,  # 1MB buffer limit to prevent memory issues
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=30)
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            if proc.returncode != 0:
                msg_error(f"BSArch command failed for {filename}:\n{stderr}")
                return local_issues

            output_split: list[str] = stdout.split("\n\n")
            if output_split[-1].startswith("Error:"):
                msg_error(f"BSArch error for {filename}:\n{output_split[-1]}\n\n{stderr}")
                return local_issues

            # Process texture information
            for file_block in output_split[4:]:
                if not file_block:
                    continue

                self.process_texture_block(file_block, filename, local_issues)

        except TimeoutError:
            msg_error(f"BSArch command timed out processing {filename}")
            # Clean up the subprocess to prevent zombie processes
            if proc is not None:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass  # Process already terminated
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            msg_error(f"Error processing {filename}: {e}")

        return local_issues

    @staticmethod
    def process_texture_block(file_block: str, filename: str, local_issues: dict[str, set[str]]) -> None:
        """Process a single texture block from BSArch output.

        Parses texture information from BSArch dump output and checks for:
        - Non-DDS texture formats
        - Odd-numbered dimensions (width or height)

        Args:
            file_block: The texture block data from BSArch output.
            filename: The name of the BA2 file for error reporting.
            local_issues: Dictionary to store detected issues.

        Example:
            >>> issues = {"tex_frmt": set(), "tex_dims": set()}
            >>> BA2ArchiveScanner.process_texture_block(block, "mod.ba2", issues)
            >>> len(issues["tex_dims"])
            0

        """
        block_split: list[str] = file_block.split("\n", 3)

        # Check texture format
        if "Ext: dds" not in block_split[1]:
            local_issues["tex_frmt"].add(f"  - {block_split[0].rsplit('.', 1)[-1].upper()} : {filename} > {block_split[0]}\n")
            return

        # Check texture dimensions
        try:
            _, width, _, height, _ = block_split[2].split(maxsplit=4)
            if (width.isdecimal() and int(width) % 2 != 0) or (height.isdecimal() and int(height) % 2 != 0):
                local_issues["tex_dims"].add(f"  - {width}x{height} : {filename} > {block_split[0]}")
        except (ValueError, IndexError):
            # Skip if we can't parse dimensions
            pass

    async def process_general_ba2_async(
        self, file_path: Path, filename: str, bsarch_path: Path, xse_scriptfiles: dict[str, str]
    ) -> dict[str, set[str]]:
        """Process a general-format BA2 file (GNRL).

        Uses BSArch.exe to list files in the archive and validates:
        - Sound file formats (checks for MP3/M4A which should be XWM)
        - XSE script files

        Args:
            file_path: The path to the BA2 file.
            filename: The name of the BA2 file.
            bsarch_path: Path to BSArch executable.
            xse_scriptfiles: Dictionary of XSE script files to detect.

        Returns:
            Dictionary of detected issues.

        Raises:
            TimeoutError: If BSArch subprocess exceeds 30 second timeout.
            OSError: If subprocess execution fails.

        Example:
            >>> issues = await scanner.process_general_ba2_async(path, "main.ba2", bsarch, xse)
            >>> if issues["snd_frmt"]:
            ...     print("Found sound format issues")

        """
        local_issues: dict[str, set[str]] = {
            "snd_frmt": set(),
            "xse_file": set(),
        }
        proc: asyncio.subprocess.Process | None = None  # Initialize to None for exception handler access

        try:
            proc = await asyncio.create_subprocess_exec(
                str(bsarch_path),
                str(file_path),
                "-list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,  # 1MB buffer limit to prevent memory issues
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=30)
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            if proc.returncode != 0:
                msg_error(f"BSArch command failed for {filename}:\n{stderr}")
                return local_issues

            # Process file list
            output_split = stdout.lower().split("\n")
            self.analyze_general_files(output_split[15:], filename, file_path, xse_scriptfiles, local_issues)

        except TimeoutError:
            msg_error(f"BSArch command timed out processing {filename}")
            # Clean up the subprocess to prevent zombie processes
            if proc is not None:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass  # Process already terminated
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            msg_error(f"Error processing {filename}: {e}")

        return local_issues

    @staticmethod
    def analyze_general_files(
        files: list[str], filename: str, file_path: Path, xse_scriptfiles: dict[str, str], local_issues: dict[str, set[str]]
    ) -> None:
        r"""Analyze files in a general-format BA2 for various issues.

        Scans through the file list from a GNRL BA2 archive and checks for:
        - MP3/M4A sound files (should be XWM for Bethesda games)
        - XSE script files (F4SE, SKSE, etc.)

        Args:
            files: List of file paths in the BA2 (lowercase).
            filename: The name of the BA2 file for error reporting.
            file_path: The path to the BA2 file for additional checks.
            xse_scriptfiles: Dictionary of XSE script files to detect.
            local_issues: Dictionary to store detected issues.

        Example:
            >>> issues = {"snd_frmt": set(), "xse_file": set()}
            >>> files = ["sounds\\music.mp3", "scripts\\f4se\\example.pex"]
            >>> BA2ArchiveScanner.analyze_general_files(files, "mod.ba2", path, xse, issues)
            >>> len(issues["snd_frmt"])
            1

        """
        has_xse_files = False

        for file in files:
            # Check sound formats
            if file.endswith((".mp3", ".m4a")):
                local_issues["snd_frmt"].add(f"  - {file[-3:].upper()} : {filename} > {file}\n")
                continue

            # Check XSE files
            if (
                not has_xse_files
                and any(f"scripts\\{key.lower()}" in file for key in xse_scriptfiles)
                and "workshop framework" not in str(file_path.parent).lower()
            ):
                has_xse_files = True
                local_issues["xse_file"].add(f"  - {filename}\n")
                continue

    @staticmethod
    def merge_scan_results(results: list, target_issues: dict[str, set[str]]) -> None:
        """Merge scan results from multiple BA2 files into a target dictionary.

        This method consolidates results from concurrent BA2 processing, handling
        both successful results (dictionaries) and exceptions. Failed tasks are
        logged but don't stop the overall process.

        Args:
            results: List of scan results from BA2 processing (dicts or Exceptions).
            target_issues: Target dictionary to merge all results into.

        Example:
            >>> results = [{"tex_frmt": {"issue1"}}, {"tex_frmt": {"issue2"}}]
            >>> target = {"tex_frmt": set(), "tex_dims": set()}
            >>> BA2ArchiveScanner.merge_scan_results(results, target)
            >>> len(target["tex_frmt"])
            2

        """
        for result in results:
            if isinstance(result, Exception):
                msg_error(f"Task failed with exception: {result}")
                continue
            if isinstance(result, dict):
                for issue_type, items in result.items():
                    target_issues[issue_type].update(items)
