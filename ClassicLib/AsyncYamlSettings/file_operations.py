"""
Manage YAML file operations, providing functionalities for reading, writing,
and parsing YAML files. It supports optional Rust acceleration for performance
on static database files and uses Python-based implementations for preserving
comments in user-editable files.
"""

import asyncio
from io import StringIO
from pathlib import Path
from typing import Any, ClassVar

import ruamel.yaml

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.Logger import logger
from ClassicLib.ResourceLoader import ResourceLoader


# TODO: Make Static YAML Stores read-only in the future  # noqa: FIX002
# Static stores should not be written to at runtime.
class YamlFileOperations:
    """
    Handles operations for YAML files including parsing, dumping, and caching.

    This class provides methods to work with YAML files, leveraging both Python
    and Rust capabilities for enhanced performance and specific feature handling.
    Static read-only files utilize Rust for speed, while user-editable files use
    Python to preserve comments. File-level caching is also implemented for
    performance optimization.

    Attributes:
        STATIC_YAML_STORES (set[YAML]): A collection of static database files
            that can use Rust acceleration for performance enhancement.
    """

    # Static YAML stores that don't change based on game selection
    # These are read-only database files that ship with the application
    STATIC_YAML_STORES: ClassVar[set[YAML]] = {
        YAML.Main,
        YAML.Game,  # Game database files are static
    }

    def __init__(self, io_core: FileIOCore | None = None) -> None:
        """
        Initializes a YamlFileOperations object. Responsible for managing YAML file
        operations using either Python or Rust-based implementations, depending on
        availability. The Rust implementation is used for static database files, while
        Python is preferred for user-editable files to preserve comments.

        Args:
            io_core (FileIOCore | None): An optional FileIOCore instance for handling
                file I/O operations. If not provided, a new FileIOCore instance is created.
        """
        self.io_core = io_core or FileIOCore()
        self._file_cache: dict[str, dict[str, Any]] = {}

        # Try to get Rust YAML operations for static database files only
        # User-editable files will use Python to preserve comments
        self.rust_yaml: Any | None = None
        try:
            from ClassicLib.integration.factory import get_yaml_operations
            self.rust_yaml = get_yaml_operations()
            if self.rust_yaml:
                logger.debug("YamlFileOperations: Rust available for static database files (user files use Python for comment preservation)")
        except ImportError:
            logger.debug("YamlFileOperations: Rust YAML operations not available, using Python for all files")

    def _should_use_rust_for_file(self, file_path: Path) -> bool:
        """
        Determines whether Rust should be used for processing a given file path.

        This method evaluates a given file path to determine whether it is a static
        YAML store or a user-editable file. Static YAML stores are read-only and do
        not require comment preservation; in such cases, Rust should be used. For
        user-editable files, Python is preferred to ensure comment preservation.

        Args:
            file_path (Path): The file path to check.

        Returns:
            bool: True if Rust should be used for the given file path, False otherwise.
        """
        # Check if this file path corresponds to a static YAML store
        # Static stores are read-only and don't need comment preservation
        for store in self.STATIC_YAML_STORES:
            try:
                store_path = YamlFileOperations.get_path_for_store(store)

                # Exact path match
                if file_path == store_path:
                    return True
                # Exact filename match
                if file_path.name == store_path.name:
                    return True
                # Check if the resolved paths match (handles relative vs absolute)
                if file_path.resolve() == store_path.resolve():
                    return True
            except (ValueError, OSError, RuntimeError):
                # If we can't determine the path for this store, skip it
                continue

        # For all user-editable files (Settings, Ignore, Game_Local, Cache),
        # use Python to preserve comments
        return False

    @staticmethod
    def get_path_for_store(yaml_store: YAML) -> Path:
        """
        Determines the file path for a given YAML store type.

        This method dynamically computes and returns a relevant file path based on the specified
        YAML store. The function accounts for different scenarios, including development and
        installed package setups, and supports multiple types of YAML configurations.

        Args:
            yaml_store (YAML): The type of YAML store for which the path is required.

        Returns:
            Path: The computed file path corresponding to the given YAML store.

        Raises:
            ValueError: If the provided `yaml_store` does not match any known type.
        """
        # Use ResourceLoader to get the data directory
        # This handles both development and installed package scenarios
        base_path: Path = ResourceLoader.get_data_directory()

        match yaml_store:
            case YAML.Settings:
                return base_path / "CLASSIC Settings.yaml"
            case YAML.Main:
                return base_path / "databases" / "CLASSIC Main.yaml"
            case YAML.Ignore:
                return base_path.parent / "CLASSIC Ignore.yaml"  # Ignore is at root level
            case YAML.Game:
                game_name = GlobalRegistry.get_game()
                return base_path / "databases" / f"CLASSIC {game_name}.yaml"
            case YAML.Game_Local:
                game_name = GlobalRegistry.get_game()
                return base_path / f"CLASSIC {game_name} Local.yaml"
            case YAML.TEST:
                # Test store for unit tests
                return Path(GlobalRegistry.get_local_dir()) / "tests" / "test_settings.yaml"
            case YAML.Cache:
                # User-specific persistent cache for uvx compatibility
                # This uses the user's config directory which persists across uvx invocations
                try:
                    import appdirs
                    cache_dir = Path(appdirs.user_config_dir("CLASSIC-Fallout4", "CLASSIC"))
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    return cache_dir / "cache.yaml"
                except ImportError:
                    # Fallback to local data directory if appdirs not available
                    logger.warning("appdirs not available, using local cache")
                    return base_path / "cache.yaml"
            case _:
                raise ValueError(f"Unknown YAML store: {yaml_store}")

    async def parse_yaml_content(self, content: str, preserve_comments: bool = True) -> dict[str, Any]:
        """
        Parses a YAML content string and returns its equivalent dictionary representation. Optionally, it can preserve
        comments using the Python-based parser if specified, or leverage an accelerated Rust implementation if available
        and comments preservation is not required.

        Args:
            content (str): The YAML content as a string to be parsed.
            preserve_comments (bool, optional): A flag indicating whether to preserve comments. Defaults to True.

        Returns:
            dict: A dictionary representation of the parsed YAML content.

        Raises:
            ruamel.yaml.YAMLError: If YAML parsing fails with the Python parser.
        """
        # Use Rust acceleration for read-only files
        if not preserve_comments and self.rust_yaml:
            try:
                result = self.rust_yaml.parse_yaml(content)
                return result if isinstance(result, dict) else {}
            except (RuntimeError, ValueError, TypeError) as e:
                logger.debug(f"Rust YAML parsing failed, falling back to Python: {e}")

        # Use Python implementation to preserve comments
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        yaml.width = 120

        try:
            # Use StringIO for parsing
            data = yaml.load(StringIO(content))
            return data if isinstance(data, dict) else {}
        except ruamel.yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML content: {e}")
            raise

    @staticmethod
    async def dump_yaml_content(data: dict[str, Any]) -> str:
        """
        Writes a dictionary as a YAML formatted string while preserving comments from
        the input data. The function applies a specific YAML formatting style
        including preserving quotes, setting a maximum line width, and explicit
        indentation for mappings and sequences.

        If the operation fails, an error is logged, and the exception is re-raised.

        Args:
            data (dict[str, Any]): A dictionary representing the structured data
                to be converted into a YAML formatted string.

        Returns:
            str: A string containing the YAML representation of the input `data`.

        Raises:
            Exception: Propagates exceptions encountered during the YAML dumping
                process.
        """
        # Always use Python implementation to preserve comments from CommentedMap
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        yaml.width = 120
        yaml.indent(mapping=2, sequence=4, offset=2)

        try:
            output = StringIO()
            yaml.dump(data, output)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to dump YAML content: {e}")
            raise

    async def load_yaml_file(self, file_path: Path, use_cache: bool = True) -> dict[str, Any]:
        """
        Asynchronously loads a YAML file and returns its contents as a dictionary.

        The method supports optional caching for faster subsequent access of the same file and
        can use Rust-based acceleration for reading static (read-only) files when applicable. If
        Rust acceleration fails or is not applicable, the method falls back to a Python-based
        implementation. YAML comments can be preserved when using the Python implementation,
        particularly for user-editable files.

        Args:
            file_path (Path): The path to the YAML file to load.
            use_cache (bool): A flag indicating whether to use caching for the YAML file.
                Defaults to True.

        Returns:
            dict[str, Any]: The parsed YAML content as a dictionary. If the file is empty or
            not found, returns an empty dictionary.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            Exception: If any error occurs during file reading or parsing.
        """
        # Check cache first if enabled
        file_key = str(file_path)
        if use_cache and hasattr(self, '_file_cache') and file_key in self._file_cache:
            logger.debug(f"Loaded {file_path.name} from cache")
            return self._file_cache[file_key]

        try:
            # Determine if this is a static (read-only) file that can use Rust acceleration
            use_rust = self._should_use_rust_for_file(file_path)

            if use_rust and self.rust_yaml:
                try:
                    result = self.rust_yaml.load_yaml_file(str(file_path))
                    logger.debug(f"Loaded {file_path.name} with Rust acceleration")
                    data = result if isinstance(result, dict) else {}
                except (RuntimeError, ValueError, TypeError, OSError) as e:
                    logger.debug(f"Rust YAML loading failed for {file_path.name}, falling back to Python: {e}")
                    # Fall through to Python loading
                    content = await self.io_core.read_file(file_path)
                    if not content:
                        logger.warning(f"Empty YAML file: {file_path}")
                        return {}
                    preserve_comments = not use_rust
                    logger.debug(f"Loaded {file_path.name} with Python (preserve_comments={preserve_comments})")
                    data = await self.parse_yaml_content(content, preserve_comments=preserve_comments)
            else:
                # Use Python implementation (preserves comments for user-editable files)
                content = await self.io_core.read_file(file_path)

                if not content:
                    logger.warning(f"Empty YAML file: {file_path}")
                    return {}

                # Only preserve comments for user-editable files (use_rust=False)
                preserve_comments = not use_rust
                logger.debug(f"Loaded {file_path.name} with Python (preserve_comments={preserve_comments})")
                data = await self.parse_yaml_content(content, preserve_comments=preserve_comments)

        except FileNotFoundError:
            logger.debug(f"YAML file not found: {file_path}")
            return {}
        except (ruamel.yaml.YAMLError, OSError, ValueError) as e:
            logger.error(f"Failed to load YAML file {file_path}: {e}")
            return {}
        else:
            # Cache the result if caching is enabled (only on success)
            if use_cache:
                if not hasattr(self, '_file_cache'):
                    self._file_cache: dict[str, dict[str, Any]] = {}
                self._file_cache[file_key] = data

            return data

    async def save_yaml_file(self, file_path: Path, data: dict[str, Any]) -> bool:
        """
        Asynchronously saves a dictionary as a YAML file while preserving comments and formatting.
        Ensures the parent directory for the file exists before writing. Utilizes an async
        file-writing functionality to handle the operation.

        Args:
            file_path (Path): Path to the YAML file to be written.
            data (dict[str, Any]): The data to be written into the YAML file.

        Returns:
            bool: Returns True if the operation is successful, otherwise False.
        """
        try:
            # Always use Python implementation for writing to preserve comments
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to YAML string (ruamel.yaml preserves comments and formatting)
            content = await self.dump_yaml_content(data)

            # Use FileIOCore for async file writing
            await self.io_core.write_file(file_path, content)

        except (OSError, ValueError, ruamel.yaml.YAMLError) as e:
            logger.error(f"Failed to save YAML file {file_path}: {e}")
            return False
        else:
            return True

    async def ensure_file_exists(self, file_path: Path) -> None:
        """
        Ensures that the given file exists at the specified path. If the file does not exist,
        it will create the required directories (if needed) and create an empty YAML file
        at the specified location.

        Args:
            file_path (Path): The path to the file that needs to be checked or created.
        """
        if not await asyncio.to_thread(file_path.exists):
            logger.debug(f"Creating missing YAML file: {file_path}")
            await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
            # Create empty YAML file
            await self.io_core.write_file(file_path, "{}\n")

    async def backup_file(self, file_path: Path, backup_suffix: str = ".bak") -> Path:
        """
        Creates a backup of the given file by appending a backup suffix.

        This method asynchronously reads the content of the specified file and creates
        a backup by writing the content to a new file with an appended suffix. If the
        specified file does not exist, no backup is created, and a warning is logged.

        Args:
            file_path (Path): Path to the file that needs to be backed up.
            backup_suffix (str, optional): Suffix to add to the file's extension when
                creating the backup. Defaults to ".bak".

        Returns:
            Path: The path to the newly created backup file.
        """
        backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)

        if await asyncio.to_thread(file_path.exists):
            content = await self.io_core.read_file(file_path)
            await self.io_core.write_file(backup_path, content)
            logger.debug(f"Created backup: {backup_path}")
        else:
            logger.warning(f"Cannot backup non-existent file: {file_path}")

        return backup_path

    async def regenerate_settings_file(self, yaml_store: YAML) -> dict[str, Any]:
        """
        Regenerates a YAML settings file and reloads it.

        This method currently only supports regenerating user-specific files (Ignore and Game_Local).
        Static database files (Settings, Main, Game) cannot be regenerated as they are shipped with
        the application.

        Args:
            yaml_store (YAML): An enumeration representing the type of YAML file
                to regenerate. Supported values: YAML.Ignore, YAML.Game_Local.

        Returns:
            dict[str, Any]: A dictionary containing the contents of the regenerated
                YAML file if successful, or an empty dictionary if the operation
                fails or the store type is not supported.
        """
        logger.info(f"Regenerating {yaml_store} file")

        # Import file generation module
        try:
            from ClassicLib.FileGeneration import FileGenerator

            # Determine which file to regenerate
            # Only user-specific files can be regenerated
            if yaml_store == YAML.Ignore:
                await FileGenerator.generate_ignore_file_async()
                file_path = YamlFileOperations.get_path_for_store(yaml_store)
                return await self.load_yaml_file(file_path)

            if yaml_store == YAML.Game_Local:
                await FileGenerator.generate_local_yaml_async()
                file_path = YamlFileOperations.get_path_for_store(yaml_store)
                return await self.load_yaml_file(file_path)

        except ImportError:
            logger.error("FileGeneration module not available")
            return {}
        except (TypeError, OSError, PermissionError) as e:
            logger.error(f"Failed to regenerate {yaml_store} file: {e}")
            return {}
        else:
            # Static database files (Settings, Main, Game) cannot be regenerated
            # They are shipped with the application
            logger.warning(f"Cannot regenerate {yaml_store} file - static files are read-only")
            return {}
