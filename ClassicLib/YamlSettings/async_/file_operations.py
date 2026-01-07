"""Async YAML file operations with optional Rust acceleration.

This module provides functionality for reading, writing, and parsing YAML files
asynchronously. It supports optional Rust acceleration for static database files
and uses Python-based implementations for preserving comments in user-editable files.

Classes:
    YamlFileOperations: Handles YAML file I/O with caching and Rust acceleration.

Example:
    >>> from ClassicLib.YamlSettings.async_.file_operations import YamlFileOperations
    >>> ops = YamlFileOperations()
    >>> data = await ops.load_yaml_file(Path("config.yaml"))
    >>> await ops.save_yaml_file(Path("config.yaml"), data)

"""

import asyncio
from io import StringIO
from pathlib import Path
from typing import Any, ClassVar

import ruamel.yaml

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.integration.factory import get_file_io
from ClassicLib.Logger import logger
from ClassicLib.ResourceLoader import ResourceLoader


class YamlFileOperations:
    """Handle YAML file operations with caching and optional Rust acceleration.

    This class provides methods for parsing, dumping, loading, and saving YAML
    files. It leverages both Python and Rust capabilities for enhanced performance.
    Static read-only files utilize Rust for speed, while user-editable files use
    Python to preserve comments. File-level caching is also implemented for
    performance optimization.

    Attributes:
        STATIC_YAML_STORES: A set of static database files that can use Rust
            acceleration for performance enhancement.
        io_core: FileIOCore instance for async file I/O operations.
        rust_yaml: Optional Rust YAML operations for static files.

    Example:
        >>> ops = YamlFileOperations()
        >>> # Load a YAML file
        >>> data = await ops.load_yaml_file(Path("settings.yaml"))
        >>> # Modify and save
        >>> data["key"] = "value"
        >>> await ops.save_yaml_file(Path("settings.yaml"), data)

    """

    # Static YAML stores that don't change based on game selection
    # These are read-only database files that ship with the application
    STATIC_YAML_STORES: ClassVar[set[YAML]] = {
        YAML.Main,
        YAML.Game,  # Game database files are static
    }

    def __init__(self, io_core: Any | None = None) -> None:
        """Initialize YamlFileOperations with optional FileIOCore.

        Sets up the file I/O core and attempts to load Rust YAML operations
        for static database files. User-editable files will always use Python
        to preserve comments.

        Args:
            io_core: Optional FileIOCore instance for handling file I/O.
                If not provided, uses the factory to get the optimal implementation.

        Note:
            Rust acceleration is only used for static database files.
            User-editable files always use Python to preserve comments.

        """
        self.io_core = io_core or get_file_io()  # Use factory for Rust acceleration
        self._file_cache: dict[str, dict[str, Any]] = {}

        # Try to get Rust YAML operations for static database files only
        # User-editable files will use Python to preserve comments
        self.rust_yaml: Any | None = None
        try:
            from ClassicLib.integration.factory import get_yaml_operations

            self.rust_yaml = get_yaml_operations()
            if self.rust_yaml:
                logger.debug(
                    "YamlFileOperations: Rust available for static database files (user files use Python for comment preservation)"
                )
        except ImportError:
            logger.debug("YamlFileOperations: Rust YAML operations not available, using Python for all files")

    def _should_use_rust_for_file(self, file_path: Path) -> bool:
        """Determine if Rust should be used for a given file.

        Static YAML stores are read-only and don't need comment preservation,
        so Rust can be used for better performance. User-editable files should
        use Python to ensure comment preservation.

        Args:
            file_path: The file path to check.

        Returns:
            True if Rust should be used (static file), False for user-editable
            files where Python should preserve comments.

        Example:
            >>> ops = YamlFileOperations()
            >>> ops._should_use_rust_for_file(Path("CLASSIC Main.yaml"))
            True
            >>> ops._should_use_rust_for_file(Path("CLASSIC Settings.yaml"))
            False

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
        """Get the file path for a given YAML store type.

        Dynamically computes and returns the file path for the specified YAML
        store, accounting for different scenarios including development and
        installed package setups.

        Args:
            yaml_store: The type of YAML store for which the path is required.

        Returns:
            The computed file path corresponding to the given YAML store.

        Raises:
            ValueError: If the provided yaml_store does not match any known type.

        Example:
            >>> path = YamlFileOperations.get_path_for_store(YAML.Main)
            >>> print(path)
            CLASSIC Data/databases/CLASSIC Main.yaml

        """
        # Use ResourceLoader to get the data directory
        # This handles both development and installed package scenarios
        base_path: Path = ResourceLoader.get_data_directory()

        match yaml_store:
            case YAML.Settings:
                return base_path.parent / "CLASSIC Settings.yaml"
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
                # Local cache in CLASSIC Data directory
                return base_path / "cache.yaml"
            case _:
                raise ValueError(f"Unknown YAML store: {yaml_store}")

    async def parse_yaml_content(self, content: str, preserve_comments: bool = True) -> dict[str, Any]:
        r"""Parse YAML content string into a dictionary.

        Can use Rust acceleration for read-only files or Python parser with
        comment preservation for user-editable files.

        Args:
            content: The YAML content as a string to be parsed.
            preserve_comments: Whether to preserve YAML comments. Set to False
                for static database files to enable Rust acceleration.

        Returns:
            A dictionary representation of the parsed YAML content.

        Raises:
            ruamel.yaml.YAMLError: If YAML parsing fails with the Python parser.

        Example:
            >>> content = "key: value\\n# comment\\nother: data"
            >>> data = await ops.parse_yaml_content(content, preserve_comments=True)

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
        """Convert a dictionary to YAML string with formatting preservation.

        Always uses Python implementation to preserve comments and formatting
        from the input data.

        Args:
            data: A dictionary to be converted into a YAML formatted string.

        Returns:
            A string containing the YAML representation of the input data.

        Raises:
            Exception: Propagates exceptions encountered during YAML dumping.

        Example:
            >>> data = {"key": "value", "list": [1, 2, 3]}
            >>> yaml_str = await YamlFileOperations.dump_yaml_content(data)

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
        """Load a YAML file and return its contents as a dictionary.

        Supports optional caching for faster subsequent access and can use
        Rust-based acceleration for reading static (read-only) files. User-editable
        files always use Python to preserve comments.

        Args:
            file_path: The path to the YAML file to load.
            use_cache: Whether to use caching for the YAML file. Defaults to True.

        Returns:
            The parsed YAML content as a dictionary. Returns empty dictionary
            if the file is empty, not found, or cannot be parsed.

        Note:
            Errors during loading are logged but do not raise exceptions.
            An empty dictionary is returned for missing or invalid files.

        Example:
            >>> data = await ops.load_yaml_file(Path("config.yaml"))
            >>> print(data.get("setting", "default"))

        """
        # Check cache first if enabled
        file_key = str(file_path)
        if use_cache and hasattr(self, "_file_cache") and file_key in self._file_cache:
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
                if not hasattr(self, "_file_cache"):
                    self._file_cache = {}
                self._file_cache[file_key] = data

            return data

    async def save_yaml_file(self, file_path: Path, data: dict[str, Any]) -> bool:
        """Save a dictionary as a YAML file with formatting preservation.

        Ensures the parent directory exists before writing. Always uses Python
        implementation to preserve comments and formatting.

        Args:
            file_path: Path to the YAML file to be written.
            data: The data to be written into the YAML file.

        Returns:
            True if the operation is successful, False otherwise.

        Example:
            >>> data = {"setting": "value"}
            >>> success = await ops.save_yaml_file(Path("config.yaml"), data)
            >>> if success:
            ...     print("File saved successfully")

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
        """Ensure a YAML file exists, creating it if necessary.

        If the file does not exist, creates the required directories and
        an empty YAML file at the specified location.

        Args:
            file_path: The path to the file that needs to be checked or created.

        Example:
            >>> await ops.ensure_file_exists(Path("new_config.yaml"))
            >>> # File now exists (empty if it was just created)

        """
        if not await asyncio.to_thread(file_path.exists):
            logger.debug(f"Creating missing YAML file: {file_path}")
            await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
            # Create empty YAML file
            await self.io_core.write_file(file_path, "{}\n")

    async def backup_file(self, file_path: Path, backup_suffix: str = ".bak") -> Path:
        """Create a backup of a YAML file.

        Creates a backup by reading the file content and writing it to a new
        file with the specified suffix appended.

        Args:
            file_path: Path to the file that needs to be backed up.
            backup_suffix: Suffix to add to the file's extension when creating
                the backup. Defaults to ".bak".

        Returns:
            The path to the newly created backup file.

        Note:
            If the specified file does not exist, no backup is created and
            a warning is logged.

        Example:
            >>> backup_path = await ops.backup_file(Path("config.yaml"))
            >>> print(backup_path)
            config.yaml.bak

        """
        backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)

        if await asyncio.to_thread(file_path.exists):
            content = await self.io_core.read_file(file_path)
            await self.io_core.write_file(backup_path, content)
            logger.debug(f"Created backup: {backup_path}")
        else:
            logger.warning(f"Cannot backup non-existent file: {file_path}")

        return backup_path

    def clear_cache(self) -> None:
        """Clear the internal file cache.

        Removes all cached file contents, forcing files to be reloaded from
        disk on next access.
        """
        if hasattr(self, "_file_cache"):
            self._file_cache.clear()

    async def regenerate_settings_file(self, yaml_store: YAML) -> dict[str, Any]:
        """Regenerate a YAML settings file and reload it.

        Currently only supports regenerating user-specific files (Ignore and
        Game_Local). Static database files (Settings, Main, Game) cannot be
        regenerated as they are shipped with the application.

        Args:
            yaml_store: An enumeration representing the type of YAML file to
                regenerate. Supported values: YAML.Ignore, YAML.Game_Local.

        Returns:
            A dictionary containing the contents of the regenerated YAML file
            if successful, or an empty dictionary if the operation fails or
            the store type is not supported.

        Example:
            >>> data = await ops.regenerate_settings_file(YAML.Ignore)
            >>> if data:
            ...     print("Ignore file regenerated successfully")

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


__all__ = ["YamlFileOperations"]
