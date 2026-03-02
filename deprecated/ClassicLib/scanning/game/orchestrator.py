"""GameIntegrityOrchestrator module - Async-first game integrity checking orchestration.

This module provides async-first implementations for orchestrating multiple game
integrity checks and scans. It combines results from various components to provide
comprehensive game and mod analysis reports.
"""

import asyncio
from pathlib import Path

from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.integration.factory import get_file_io
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.scanning.game.check_crashgen import check_crashgen_settings
from ClassicLib.scanning.game.check_xse_plugins import check_xse_plugins
from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue
from ClassicLib.scanning.game.scan_mod_inis import scan_mod_inis_async
from ClassicLib.scanning.game.wrye_check import scan_wryecheck


# noinspection PyUnresolvedReferences,PyTypeChecker
class GameIntegrityOrchestratorCore:
    """Facilitates the orchestration of integrity checks for games and mods.

    This class is responsible for asynchronously performing and combining results
    from various integrity and validation checks related to game files, mod files,
    and associated documentation. It also handles writing the combined results into
    a report file for further analysis.

    Attributes:
        file_io (FileIOCore): Handles file input-output operations.

    """

    def __init__(self) -> None:
        """Initialize the game integrity orchestrator core."""
        self.file_io = get_file_io()  # Use factory for Rust acceleration

    async def generate_game_combined_result_async(self) -> tuple[str, list[ConfigIssue]]:
        """Async implementation for generating combined game integrity results with detected issues.

        This function performs a series of validations and scans on the game files
        and documentation directories. It consolidates plugin checks, crash generation
        settings, log errors, and additional configuration validations into a single
        text result. Additionally, it detects configuration issues without modifying files.

        Returns:
            tuple[str, list[ConfigIssue]]: A tuple containing:
                - str: A string summarizing the results of all performed checks and scans.
                - list[ConfigIssue]: List of detected configuration issues.
            If the necessary paths or directories are not available, an empty tuple
            with empty string and empty list is returned.

        """
        try:
            # Get required paths
            docs_path: Path | None = yaml_settings(Path, YAML.Game_Local, "Game_Info.Root_Folder_Docs")
            game_path: Path | None = yaml_settings(Path, YAML.Game_Local, "Game_Info.Root_Folder_Game")

            if not (game_path and docs_path):
                return "", []

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
                # Unpack crashgen result (returns tuple with ConfigIssues)
                crashgen_message, crashgen_issues = crashgen_task.result()

                valid_results = [
                    xse_task.result(),
                    crashgen_message,
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

            # Detect configuration issues (read-only, delegated to Rust scanner)
            from ClassicLib.scanning.game.scan_mod_inis import detect_all_ini_issues_async

            ini_issues = await detect_all_ini_issues_async()

            # Combine issues from both crashgen and INI scans
            all_detected_issues = crashgen_issues + ini_issues

            return "".join(valid_results), all_detected_issues

        except (OSError, RuntimeError) as e:
            logger.error(f"Error in generate_game_combined_result_async: {e}")
            return "", []

    @staticmethod
    async def generate_mods_combined_result_async() -> str:
        """Asynchronously generates a combined result of scans for both unpacked and archived mods.

        The method performs concurrent execution of two mod scans: one for unpacked mods and the other
        for archived mods. If a mod path is not available, a warning message from the YAML settings is returned.
        Exceptions occurring during the scan processes are logged without being raised again, and a concatenated
        result string of the successful scan(s) is returned. If both scans fail due to exceptions, an empty
        result string is returned.

        Returns:
            str: The concatenated results of the scans for unpacked and archived mods, or an appropriate
            warning message or empty string in the event of errors.

        Raises:
            OSError: If an OS-level error occurs during execution.
            RuntimeError: If a runtime error occurs during execution.

        """
        try:
            # Import here to avoid circular imports
            from ClassicLib.scanning.game.core import ScanGameCore

            # Get mod path to verify it exists before running scans
            core = ScanGameCore()
            _, _, mod_path = core.get_scan_settings()  # pyright: ignore[reportGeneralTypeIssues, reportUnknownVariableType]

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
        """Asynchronously writes combined results from game and mod reports to a file.

        This method generates game and mod reports concurrently, ensuring both tasks succeed
        before continuing. If successful, the combined content of both reports is written
        to a specified file. In case of errors during the report generation or file writing
        process, appropriate error handling is performed to log and re-raise exceptions.

        Raises:
            OSError: Raised when a file system error occurs while writing the file.
            RuntimeError: Raised when unexpected runtime issues are encountered.
            Exception: Catches and logs all other unexpected errors before re-raising.

        """
        try:
            # Generate both results concurrently with fail-fast behavior
            # Both reports must succeed for the operation to complete
            async with asyncio.TaskGroup() as tg:
                game_task = tg.create_task(self.generate_game_combined_result_async())
                mods_task = tg.create_task(self.generate_mods_combined_result_async())

            # Both reports generated successfully - combine and write
            game_result, _ = game_task.result()  # Unpack tuple, discard issues list
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

    @staticmethod
    async def _run_xse_plugins_check_async() -> str:
        """Run the XSE plugins check asynchronously.

        This static method facilitates the execution of the XSE plugins check
        function in an asynchronous manner. It utilizes an event loop to run
        the `check_xse_plugins` function in a separate thread for non-blocking
        behavior.

        Returns:
            str: The result of the `check_xse_plugins` function executed
            asynchronously.

        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, check_xse_plugins)

    @staticmethod
    async def _run_crashgen_check_async() -> tuple[str, list[ConfigIssue]]:
        """Asynchronously runs a crash generation configuration check (FCX read-only mode).

        This method uses an event loop to run a crash generation settings check in a
        separate thread executor, ensuring that the application remains responsive while
        performing potentially blocking I/O operations.

        Returns:
            tuple[str, list[ConfigIssue]]: A tuple containing:
                - Formatted message string with detected issues
                - List of ConfigIssue objects for structured reporting

        Note:
            This method follows the FCX read-only pattern. It detects configuration
            issues but does not modify files.

        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, check_crashgen_settings)

    @staticmethod
    async def _check_log_errors_async(folder_path: Path) -> str:
        """Asynchronously checks for log errors in the specified folder.

        This method interacts with a core scanning module to analyze log files
        within the provided folder path and identify any potential issues. It is
        designed to be used in asynchronous contexts.

        Args:
            folder_path (Path): Path to the folder containing log files to be checked.

        Returns:
            str: A string that contains the results of the log error check.

        """
        # Import here to avoid circular imports
        from ClassicLib.scanning.game.core import ScanGameCore

        core = ScanGameCore()
        return await core.check_log_errors(folder_path)

    @staticmethod
    async def _run_wryecheck_async() -> str:
        """Run the WryeCheck functionality asynchronously.

        This static method executes the WryeCheck process in a separate thread
        using an event loop to avoid blocking the main thread. The process is
        performed asynchronously, ensuring responsive performance when executed
        in a concurrent environment.

        Returns:
            str: The result of the WryeCheck process as returned by the
            `scan_wryecheck` function.

        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, scan_wryecheck)

    @staticmethod
    async def _run_mod_inis_scan_async() -> str:
        """Execute the `scan_mod_inis_async` function directly.

        This static method directly awaits the async scan_mod_inis_async function,
        which uses async I/O operations for better performance and non-blocking behavior.

        Returns:
            str: The result of the `scan_mod_inis_async` function.

        """
        return await scan_mod_inis_async()


# Global singleton instance
_game_integrity_orchestrator_core: GameIntegrityOrchestratorCore | None = None


def get_game_integrity_orchestrator_core() -> GameIntegrityOrchestratorCore:
    """Fetch or initializes the global instance of GameIntegrityOrchestratorCore.

    This function serves as a singleton accessor for the global instance of the
    GameIntegrityOrchestratorCore. If the instance does not already exist, it
    creates and initializes it. Subsequent calls to this function will return
    the same initialized instance, ensuring a single shared instance is used
    across the application.

    Returns:
        GameIntegrityOrchestratorCore: The global instance of
        GameIntegrityOrchestratorCore.

    """
    global _game_integrity_orchestrator_core  # noqa: PLW0603
    if _game_integrity_orchestrator_core is None:
        _game_integrity_orchestrator_core = GameIntegrityOrchestratorCore()
    return _game_integrity_orchestrator_core


# Async-first interfaces
async def generate_game_combined_result_async() -> tuple[str, list[ConfigIssue]]:
    """Generate the combined result of the game asynchronously with detected issues.

    This function interacts with the game integrity orchestrator core to
    generate and retrieve the combined result of the game in an asynchronous
    manner, along with any detected configuration issues.

    Returns:
        tuple[str, list[ConfigIssue]]: A tuple containing:
            - str: The combined result of the game.
            - list[ConfigIssue]: List of detected configuration issues.

    """
    core = get_game_integrity_orchestrator_core()
    return await core.generate_game_combined_result_async()


async def generate_mods_combined_result_async() -> str:
    """Asynchronously generates a combined result from mods data.

    This function utilizes the game integrity orchestrator core to
    generate and return a combined result based on mods data. It
    operates asynchronously to allow non-blocking execution.

    Returns:
        str: The combined mods result.

    """
    core = get_game_integrity_orchestrator_core()
    return await core.generate_mods_combined_result_async()


async def write_combined_results_async() -> None:
    """Write the combined game integrity results asynchronously.

    This method orchestrates the process of writing the combined results
    for game integrity by utilizing the core logic component. It ensures
    that the process is executed asynchronously.

    Raises:
        Any exceptions raised by the invoked methods within
        `get_game_integrity_orchestrator_core` or
        `write_combined_results_async`.

    """
    core = get_game_integrity_orchestrator_core()
    await core.write_combined_results_async()


# Sync adapters for backwards compatibility and GUI usage
def generate_game_combined_result() -> tuple[str, list[ConfigIssue]]:
    """Sync adapter for generating combined game integrity results with detected issues.

    Generates a combined result summarizing game-related checks and scans,
    along with any detected configuration issues.

    This function performs a series of validations and scans on the game files
    and documentation directories. It consolidates plugin checks, crash generation
    settings, log errors, and additional configuration validations into a single
    text result. Additionally, it detects configuration issues without modifying files.
    The returned result can be used for diagnostics or reporting purposes.

    IMPORTANT - Usage:
    ✅ GUI workers and Qt threads
    ✅ Testing and benchmarking
    ❌ Production CLI code (use generate_game_combined_result_async() instead)

    For CLI production code, use the async version:
        result, issues = await generate_game_combined_result_async()

    Returns:
        tuple[str, list[ConfigIssue]]: A tuple containing:
            - str: A string summarizing the results of all performed checks and scans.
            - list[ConfigIssue]: List of detected configuration issues.
        If the necessary paths or directories are not available, an empty tuple
        with empty string and empty list is returned.

    """
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(generate_game_combined_result_async())


def generate_mods_combined_result() -> str:
    """Sync adapter for combining the results of scanning unpacked and archived mods.

    Combines the results of scanning unpacked and archived mods.

    This function first scans for unpacked mods and checks their status. If the unpacked
    mods path is not provided, it quickly returns a relevant message. Otherwise, it
    appends the results of scanning the archived mods to the result of the unpacked
    mods scan and provides a combined status report.

    IMPORTANT - Usage:
    ✅ GUI workers and Qt threads
    ✅ Testing and benchmarking
    ❌ Production CLI code (use generate_mods_combined_result_async() instead)

    For CLI production code, use the async version:
        result = await generate_mods_combined_result_async()

    Returns:
        str: The combined results of the unpacked and archived mods scans, or a message
        indicating that the mods folder path is not provided.

    """
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(generate_mods_combined_result_async())


def write_combined_results() -> None:
    """Sync adapter for writing combined results to a markdown report file.

    Writes combined results of game and mods into a markdown report file.

    This function aggregates results from two separate processes: the game result
    and the mods result. It then writes their combined output into a markdown
    file named "CLASSIC GFS Report.md". The report file is encoded in UTF-8 and
    any errors during encoding are ignored.

    IMPORTANT - Usage:
    ✅ GUI workers and Qt threads
    ✅ Testing and benchmarking
    ❌ Production CLI code (use write_combined_results_async() instead)

    For CLI production code, use the async version:
        await write_combined_results_async()
    """
    bridge = AsyncBridge.get_instance()
    bridge.run_async(write_combined_results_async())
