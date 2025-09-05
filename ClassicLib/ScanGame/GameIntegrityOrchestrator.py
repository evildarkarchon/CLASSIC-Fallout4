"""
GameIntegrityOrchestrator module - Async-first game integrity checking orchestration.

This module provides async-first implementations for orchestrating multiple game
integrity checks and scans. It combines results from various components to provide
comprehensive game and mod analysis reports.
"""

import asyncio
from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.Constants import YAML
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.Logger import logger
from ClassicLib.ScanGame.CheckCrashgen import check_crashgen_settings
from ClassicLib.ScanGame.CheckXsePlugins import check_xse_plugins
from ClassicLib.ScanGame.ScanModInis import scan_mod_inis
from ClassicLib.ScanGame.WryeCheck import scan_wryecheck
from ClassicLib.YamlSettingsCache import yaml_settings


class GameIntegrityOrchestratorCore:
    """Async-first core implementation for game integrity orchestration operations."""

    def __init__(self) -> None:
        """Initialize the game integrity orchestrator core."""
        self.file_io = FileIOCore()

    async def generate_game_combined_result_async(self) -> str:
        """
        Async implementation for generating combined game integrity results.

        This function performs a series of validations and scans on the game files
        and documentation directories. It consolidates plugin checks, crash generation
        settings, log errors, and additional configuration validations into a single
        text result.

        Returns:
            str: A string summarizing the results of all performed checks and scans.
            If the necessary paths or directories are not available, an empty string
            is returned.
        """
        try:
            # Get required paths
            docs_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Docs")
            game_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")

            if not (game_path and docs_path):
                return ""

            # Run all checks concurrently with fail-fast behavior
            # If any critical check fails, abort all checks
            try:
                async with asyncio.TaskGroup() as tg:
                    xse_task = tg.create_task(self._run_xse_plugins_check_async())
                    crashgen_task = tg.create_task(self._run_crashgen_check_async())
                    docs_log_task = tg.create_task(self._check_log_errors_async(docs_path))
                    game_log_task = tg.create_task(self._check_log_errors_async(game_path))
                    wrye_task = tg.create_task(self._run_wryecheck_async())
                    mod_inis_task = tg.create_task(self._run_mod_inis_scan_async())

                # All checks completed successfully - collect results
                valid_results = [
                    xse_task.result(),
                    crashgen_task.result(),
                    docs_log_task.result(),
                    game_log_task.result(),
                    wrye_task.result(),
                    mod_inis_task.result(),
                ]
            except* Exception as eg:
                # Log all integrity check failures
                logger.error("Game integrity checks failed:")
                for e in eg.exceptions:
                    logger.error(f"  - {type(e).__name__}: {e}")
                # Re-raise to propagate the failure
                raise

            return "".join(valid_results)

        except (OSError, RuntimeError) as e:
            logger.error(f"Error in generate_game_combined_result_async: {e}")
            return ""

    async def generate_mods_combined_result_async(self) -> str:
        """
        Async implementation for combining the results of scanning unpacked and archived mods.

        This function first checks if the mods path is provided. If not, it returns a
        relevant message. Otherwise, it performs both unpacked and archived mod scans
        concurrently and combines their results.

        Returns:
            str: The combined results of the unpacked and archived mods scans, or a
            message indicating that the mods folder path is not provided.
        """
        try:
            # Import here to avoid circular imports
            from ClassicLib.ScanGame.ScanGameCore import ScanGameCore

            # Get mod path to verify it exists before running scans
            core = ScanGameCore()
            _, _, mod_path = core.get_scan_settings()

            if not mod_path:
                return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Missing"))

            # Run both scans concurrently
            unpacked_task = core.scan_mods_unpacked()
            archived_task = core.scan_mods_archived()

            unpacked_result, archived_result = await asyncio.gather(unpacked_task, archived_task, return_exceptions=True)

            # Handle any exceptions
            unpacked_str = ""
            archived_str = ""

            if isinstance(unpacked_result, Exception):
                logger.error(f"Error in unpacked mods scan: {unpacked_result}")
            else:
                unpacked_str = str(unpacked_result)

            if isinstance(archived_result, Exception):
                logger.error(f"Error in archived mods scan: {archived_result}")
            else:
                archived_str = str(archived_result)

            return unpacked_str + archived_str

        except (OSError, RuntimeError) as e:
            logger.error(f"Error in generate_mods_combined_result_async: {e}")
            return ""

    async def write_combined_results_async(self) -> None:
        """
        Async implementation for writing combined results to a markdown report file.

        This function aggregates results from both game and mods processes and writes
        their combined output into a markdown file named "CLASSIC GFS Report.md".
        The report file is encoded in UTF-8 with error handling.

        Uses TaskGroup for atomic operation - both reports must generate successfully
        before writing to file. If either report generation fails, no file is written.
        """
        try:
            # Generate both results concurrently with fail-fast behavior
            # Both reports must succeed for the operation to complete
            async with asyncio.TaskGroup() as tg:
                game_task = tg.create_task(self.generate_game_combined_result_async())
                mods_task = tg.create_task(self.generate_mods_combined_result_async())

            # Both reports generated successfully - combine and write
            game_result = game_task.result()
            mods_result = mods_task.result()

            # Write the combined results to file
            gfs_report: Path = Path("CLASSIC GFS Report.md")
            combined_content = game_result + mods_result

            await self.file_io.write_file(gfs_report, combined_content)
            logger.info(f"Successfully wrote combined results to {gfs_report}")

        except* (OSError, RuntimeError) as eg:
            # Handle file system and runtime errors
            logger.error("Failed to write combined results:")
            for e in eg.exceptions:
                logger.error(f"  - {type(e).__name__}: {e}")
            raise
        except* Exception as eg:
            # Catch-all for unexpected errors
            logger.error("Unexpected error generating reports:")
            for e in eg.exceptions:
                logger.error(f"  - {type(e).__name__}: {e}")
            raise

    async def _run_xse_plugins_check_async(self) -> str:
        """Run XSE plugins check asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, check_xse_plugins)

    async def _run_crashgen_check_async(self) -> str:
        """Run crashgen settings check asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, check_crashgen_settings)

    async def _check_log_errors_async(self, folder_path: Path) -> str:
        """Check log errors asynchronously."""
        # Import here to avoid circular imports
        from ClassicLib.ScanGame.ScanGameCore import ScanGameCore

        core = ScanGameCore()
        return await core.check_log_errors(folder_path)

    async def _run_wryecheck_async(self) -> str:
        """Run Wrye check asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, scan_wryecheck)

    async def _run_mod_inis_scan_async(self) -> str:
        """Run mod INIs scan asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, scan_mod_inis)


# Global singleton instance
_game_integrity_orchestrator_core: GameIntegrityOrchestratorCore | None = None


def get_game_integrity_orchestrator_core() -> GameIntegrityOrchestratorCore:
    """Get singleton GameIntegrityOrchestratorCore instance."""
    global _game_integrity_orchestrator_core  # noqa: PLW0603
    if _game_integrity_orchestrator_core is None:
        _game_integrity_orchestrator_core = GameIntegrityOrchestratorCore()
    return _game_integrity_orchestrator_core


# Async-first interfaces
async def generate_game_combined_result_async() -> str:
    """
    Async interface for generating combined game integrity results.

    Returns:
        str: A string summarizing the results of all performed checks and scans.
    """
    core = get_game_integrity_orchestrator_core()
    return await core.generate_game_combined_result_async()


async def generate_mods_combined_result_async() -> str:
    """
    Async interface for generating combined mods scan results.

    Returns:
        str: The combined results of the unpacked and archived mods scans.
    """
    core = get_game_integrity_orchestrator_core()
    return await core.generate_mods_combined_result_async()


async def write_combined_results_async() -> None:
    """
    Async interface for writing combined results to a markdown report file.
    """
    core = get_game_integrity_orchestrator_core()
    await core.write_combined_results_async()


# Sync adapters for backwards compatibility
def generate_game_combined_result() -> str:
    """
    Sync adapter for generating combined game integrity results.

    Generates a combined result summarizing game-related checks and scans.

    This function performs a series of validations and scans on the game files
    and documentation directories. It consolidates plugin checks, crash generation
    settings, log errors, and additional configuration validations into a single
    text result. The returned result can be used for diagnostics or reporting
    purposes.

    Returns:
        str: A string summarizing the results of all performed checks and scans.
        If the necessary paths or directories are not available, an empty string
        is returned.
    """
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(generate_game_combined_result_async())


def generate_mods_combined_result() -> str:
    """
    Sync adapter for combining the results of scanning unpacked and archived mods.

    Combines the results of scanning unpacked and archived mods.

    This function first scans for unpacked mods and checks their status. If the unpacked
    mods path is not provided, it quickly returns a relevant message. Otherwise, it
    appends the results of scanning the archived mods to the result of the unpacked
    mods scan and provides a combined status report.

    Returns:
        str: The combined results of the unpacked and archived mods scans, or a message
        indicating that the mods folder path is not provided.
    """
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(generate_mods_combined_result_async())


def write_combined_results() -> None:
    """
    Sync adapter for writing combined results to a markdown report file.

    Writes combined results of game and mods into a markdown report file.

    This function aggregates results from two separate processes: the game result
    and the mods result. It then writes their combined output into a markdown
    file named "CLASSIC GFS Report.md". The report file is encoded in UTF-8 and
    any errors during encoding are ignored.
    """
    bridge = AsyncBridge.get_instance()
    bridge.run_async(write_combined_results_async())
