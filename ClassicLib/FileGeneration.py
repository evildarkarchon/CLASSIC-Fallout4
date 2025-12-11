"""File generation module for CLASSIC configuration files."""

import asyncio
from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger


class FileGenerator:
    """
    This class is responsible for generating essential configuration files required
    by the CLASSIC application. It ensures the presence of default files like CLASSIC Ignore.yaml
    and CLASSIC Data/CLASSIC <GAME> Local.yaml. These files are created with default content
    retrieved from YAML settings.

    The class provides both synchronous and asynchronous methods for generating files, enabling
    flexibility in various runtime environments. The asynchronous methods allow files to be generated
    concurrently, ensuring better performance and fail-fast error handling.
    """

    @staticmethod
    def generate_ignore_file() -> None:
        """
        Generate CLASSIC Ignore.yaml if it doesn't exist.

        Creates the ignore file with default content from YAML settings.
        The file content is written in UTF-8 encoding.

        Raises:
            TypeError: If the default content retrieved for the ignore file
                is not of type str.
        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        ignore_path = Path("CLASSIC Ignore.yaml")
        if not ignore_path.exists():
            default_ignorefile = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_ignorefile")
            if not isinstance(default_ignorefile, str):
                raise TypeError("Default ignore file content must be a string")
            ignore_path.write_text(default_ignorefile, encoding="utf-8")
            logger.debug(f"Generated CLASSIC Ignore.yaml at {ignore_path}")

    @staticmethod
    def generate_local_yaml() -> None:
        """
        Generate CLASSIC Data/CLASSIC <GAME> Local.yaml if it doesn't exist.

        Creates the local YAML file with default content from YAML settings,
        where <GAME> is dynamically determined from GlobalRegistry.
        The file content is written in UTF-8 encoding.

        Raises:
            TypeError: If the default content retrieved for the local YAML file
                is not of type str.
        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        local_path = Path(f"CLASSIC Data/CLASSIC {GlobalRegistry.get_game()} Local.yaml")
        if not local_path.exists():
            default_yaml = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_localyaml")
            if not isinstance(default_yaml, str):
                raise TypeError("Default local YAML content must be a string")
            # Create parent directory if it doesn't exist
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(default_yaml, encoding="utf-8")
            logger.debug(f"Generated local YAML at {local_path}")

    @staticmethod
    async def generate_ignore_file_async() -> None:
        """
        Generates a "CLASSIC Ignore.yaml" file asynchronously if it does not already exist.

        This method checks for the existence of a "CLASSIC Ignore.yaml" file in the current
        directory. If the file does not exist, it retrieves the default ignore file content
        asynchronously from YAML settings and writes it to the file. This process ensures
        the creation of the default ignore file with appropriate content required for
        CLASSIC configurations.

        Raises:
            TypeError: If the retrieved default ignore file content is not a string.
        """
        from ClassicLib.FileIO import FileIOCore
        from ClassicLib.YamlSettings import yaml_settings_async

        ignore_path = Path("CLASSIC Ignore.yaml")
        io_core = FileIOCore()

        if not io_core.file_exists(ignore_path):
            default_ignorefile = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.default_ignorefile")
            if not isinstance(default_ignorefile, str):
                raise TypeError("Default ignore file content must be a string")
            await io_core.write_file(ignore_path, default_ignorefile)
            logger.debug(f"Generated CLASSIC Ignore.yaml at {ignore_path} (async)")

    @staticmethod
    async def generate_local_yaml_async() -> None:
        """
        Generates a local YAML file asynchronously for the CLASSIC application if it doesn't already exist.

        This static method checks for the existence of a local YAML configuration file specific to the CLASSIC
        application. If the file is missing, it retrieves a default YAML configuration, validates it, creates
        necessary directories (if required), and saves the configuration to the local path, all performed
        asynchronously.

        Raises:
            TypeError: If the retrieved default YAML content is not a string.
        """
        from ClassicLib.FileIO import FileIOCore
        from ClassicLib.YamlSettings import yaml_settings_async

        local_path = Path(f"CLASSIC Data/CLASSIC {GlobalRegistry.get_game()} Local.yaml")
        io_core = FileIOCore()

        if not io_core.file_exists(local_path):
            default_yaml = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.default_localyaml")
            if not isinstance(default_yaml, str):
                raise TypeError("Default local YAML content must be a string")
            # Create parent directory if it doesn't exist (using sync method in executor)
            await asyncio.to_thread(local_path.parent.mkdir, parents=True, exist_ok=True)
            await io_core.write_file(local_path, default_yaml)
            logger.debug(f"Generated local YAML at {local_path} (async)")

    @staticmethod
    async def generate_all_files_async() -> None:
        """
        Executes asynchronous file generation of multiple files concurrently with a fail-fast
        behavior. This method ensures that all files are generated correctly, handles allowable
        errors such as type or filesystem errors, and logs relevant events or issues that
        occur during the process.

        Raises:
            TypeError: Raised if there is an issue with the YAML content that causes type
                errors during file generation. All type errors are logged.
            OSError: Raised if there is an operating system-level error such as file system
                access issues. All relevant file system errors are logged.
            PermissionError: Raised if there are permission issues with file operations.
                All relevant permission-related errors are logged.
            Exception: Raised for any unexpected errors during file generation that do not
                fall into the known error categories. Such errors are logged for troubleshooting.
        """
        import time

        start = time.perf_counter()

        try:
            # Generate files concurrently with fail-fast behavior
            async with asyncio.TaskGroup() as tg:
                tg.create_task(FileGenerator.generate_ignore_file_async())
                tg.create_task(FileGenerator.generate_local_yaml_async())

            # All files generated successfully if we reach here
            elapsed = time.perf_counter() - start
            logger.info(f"Async file generation completed successfully in {elapsed:.3f}s")

        except* TypeError as eg:
            # Handle type errors from invalid YAML content
            logger.error("File generation failed due to invalid content type")
            for e in eg.exceptions:
                logger.error(f"  - {e}")
            raise
        except* (OSError, PermissionError) as eg:
            # Handle file system errors
            logger.error("File generation failed due to file system error")
            for e in eg.exceptions:
                logger.error(f"  - {e}")
            raise
        except* Exception as eg:
            # Catch-all for unexpected errors
            logger.error("Unexpected error during file generation")
            for e in eg.exceptions:
                logger.error(f"  - {e}")
            raise

    @staticmethod
    def generate_all_files() -> None:
        """
        Generates all files synchronously by invoking an asynchronous method through
        a bridge. This method ensures the generation process is executed within the
        asynchronous context of the AsyncBridge.
        """
        from ClassicLib.AsyncBridge import AsyncBridge

        bridge = AsyncBridge.get_instance()
        bridge.run_async(FileGenerator.generate_all_files_async())
