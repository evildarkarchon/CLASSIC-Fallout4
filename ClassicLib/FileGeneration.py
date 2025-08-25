"""File generation module for CLASSIC configuration files."""

import asyncio
from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger


class FileGenerator:
    """Manages generation of CLASSIC configuration files."""

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
        Async version of generate_ignore_file.

        Generate CLASSIC Ignore.yaml if it doesn't exist using async I/O.

        Raises:
            TypeError: If the default content retrieved for the ignore file
                is not of type str.
        """
        from ClassicLib.AsyncYamlSettingsCore import yaml_settings_async
        from ClassicLib.FileIOCore import FileIOCore

        ignore_path = Path("CLASSIC Ignore.yaml")
        io_core = FileIOCore()

        if not await io_core.file_exists(ignore_path):
            default_ignorefile = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.default_ignorefile")
            if not isinstance(default_ignorefile, str):
                raise TypeError("Default ignore file content must be a string")
            await io_core.write_file(ignore_path, default_ignorefile)
            logger.debug(f"Generated CLASSIC Ignore.yaml at {ignore_path} (async)")

    @staticmethod
    async def generate_local_yaml_async() -> None:
        """
        Async version of generate_local_yaml.

        Generate CLASSIC Data/CLASSIC <GAME> Local.yaml if it doesn't exist using async I/O.

        Raises:
            TypeError: If the default content retrieved for the local YAML file
                is not of type str.
        """
        from ClassicLib.AsyncYamlSettingsCore import yaml_settings_async
        from ClassicLib.FileIOCore import FileIOCore

        local_path = Path(f"CLASSIC Data/CLASSIC {GlobalRegistry.get_game()} Local.yaml")
        io_core = FileIOCore()

        if not await io_core.file_exists(local_path):
            default_yaml = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.default_localyaml")
            if not isinstance(default_yaml, str):
                raise TypeError("Default local YAML content must be a string")
            # Create parent directory if it doesn't exist (using sync method in executor)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: local_path.parent.mkdir(parents=True, exist_ok=True))
            await io_core.write_file(local_path, default_yaml)
            logger.debug(f"Generated local YAML at {local_path} (async)")

    @staticmethod
    async def generate_all_files_async() -> None:
        """
        Async version: Generate all required CLASSIC configuration files concurrently.

        This method generates files in parallel using asyncio.gather:
        - CLASSIC Ignore.yaml: Contains ignore patterns for file scanning
        - CLASSIC Data/CLASSIC <GAME> Local.yaml: Contains game-specific local settings

        Files are generated concurrently for improved performance.
        """
        import time
        start = time.perf_counter()

        # Generate files concurrently
        await asyncio.gather(
            FileGenerator.generate_ignore_file_async(),
            FileGenerator.generate_local_yaml_async()
        )

        elapsed = time.perf_counter() - start
        logger.info(f"Async file generation completed in {elapsed:.3f}s")

    @staticmethod
    def generate_all_files() -> None:
        """
        Generate all required CLASSIC configuration files.

        This method generates:
        - CLASSIC Ignore.yaml: Contains ignore patterns for file scanning
        - CLASSIC Data/CLASSIC <GAME> Local.yaml: Contains game-specific local settings

        The method ensures all necessary configuration files exist before
        the application starts processing.

        This is a sync wrapper that uses the async implementation for better performance.
        """
        from ClassicLib.AsyncBridge import AsyncBridge

        bridge = AsyncBridge.get_instance()
        bridge.run_async(FileGenerator.generate_all_files_async())
