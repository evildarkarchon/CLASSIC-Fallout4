"""File operations for AsyncYamlSettings."""

from io import StringIO
from pathlib import Path
from typing import Any, ClassVar

import ruamel.yaml

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.Logger import logger
from ClassicLib.ResourceLoader import ResourceLoader


# TODO: Make Static YAML Stores read-only in the future
# Static stores should not be written to at runtime.
class YamlFileOperations:
    """Handles YAML file I/O operations."""

    # Static YAML stores that don't change based on game selection
    # These are read-only database files that ship with the application
    STATIC_YAML_STORES: ClassVar[set[YAML]] = {
        YAML.Main,
        YAML.Game,  # Game database files are static
    }

    def __init__(self, io_core: FileIOCore | None = None) -> None:
        """Initialize with FileIOCore instance."""
        self.io_core = io_core or FileIOCore()

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
        Determine if a file should use Rust acceleration.

        Static/read-only database files (STATIC_YAML_STORES) can use Rust for maximum performance.
        User-editable files must use Python to preserve comments.

        Args:
            file_path: Path to the YAML file

        Returns:
            True if Rust acceleration should be used, False otherwise
        """
        # Check if this file path corresponds to a static YAML store
        # Static stores are read-only and don't need comment preservation
        for store in self.STATIC_YAML_STORES:
            try:
                store_path = self.get_path_for_store(store)
                # Exact path match
                if file_path == store_path:
                    return True
                # Exact filename match
                if file_path.name == store_path.name:
                    return True
                # Check if the resolved paths match (handles relative vs absolute)
                if file_path.resolve() == store_path.resolve():
                    return True
            except (ValueError, Exception):
                # If we can't determine the path for this store, skip it
                continue

        # For all user-editable files (Settings, Ignore, Game_Local, Cache),
        # use Python to preserve comments
        return False

    def get_path_for_store(self, yaml_store: YAML) -> Path:
        """Get the file path for a specific YAML store."""
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
        Parse YAML content from string.

        Uses Python (ruamel.yaml) when preserve_comments=True to maintain comment information.
        Can use Rust acceleration when preserve_comments=False for read-only files.

        Args:
            content: YAML string content
            preserve_comments: Whether to preserve comments (use Python) or allow Rust acceleration

        Returns:
            Parsed YAML data (ruamel.yaml.CommentedMap if preserve_comments=True)
        """
        # Use Rust acceleration for read-only files
        if not preserve_comments and self.rust_yaml:
            try:
                result = self.rust_yaml.parse_yaml(content)
                return result if isinstance(result, dict) else {}
            except Exception as e:
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

    async def dump_yaml_content(self, data: dict[str, Any]) -> str:
        """
        Convert data to YAML string.

        Always uses Python (ruamel.yaml) to preserve comments from CommentedMap objects.
        If data is a ruamel.yaml.CommentedMap (from parse_yaml_content), comments will be preserved.

        Args:
            data: Data to serialize (preferably a ruamel.yaml.CommentedMap)

        Returns:
            YAML string with preserved comments
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

    async def load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        """
        Load and parse a YAML file.

        Uses Rust acceleration for static/read-only files (Main, Game databases).
        Uses Python (ruamel.yaml) for user-editable files to preserve comments.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML data
        """
        try:
            # Determine if this is a static (read-only) file that can use Rust acceleration
            use_rust = self._should_use_rust_for_file(file_path)

            if use_rust and self.rust_yaml:
                try:
                    result = self.rust_yaml.load_yaml_file(str(file_path))
                    logger.debug(f"Loaded {file_path.name} with Rust acceleration")
                    return result if isinstance(result, dict) else {}
                except Exception as e:
                    logger.debug(f"Rust YAML loading failed for {file_path.name}, falling back to Python: {e}")

            # Use Python implementation (preserves comments for user-editable files)
            content = await self.io_core.read_file(file_path)

            if not content:
                logger.warning(f"Empty YAML file: {file_path}")
                return {}

            # Only preserve comments for user-editable files (use_rust=False)
            preserve_comments = not use_rust
            logger.debug(f"Loaded {file_path.name} with Python (preserve_comments={preserve_comments})")
            return await self.parse_yaml_content(content, preserve_comments=preserve_comments)

        except FileNotFoundError:
            logger.debug(f"YAML file not found: {file_path}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load YAML file {file_path}: {e}")
            return {}

    async def save_yaml_file(self, file_path: Path, data: dict[str, Any]) -> bool:
        """
        Save data to a YAML file.

        Note: Always uses Python (ruamel.yaml) to preserve comments and formatting.
        Rust acceleration is not used for writing because yaml-rust2 strips comments.

        Args:
            file_path: Path to save to
            data: Data to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Always use Python implementation for writing to preserve comments
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to YAML string (ruamel.yaml preserves comments and formatting)
            content = await self.dump_yaml_content(data)

            # Use FileIOCore for async file writing
            await self.io_core.write_file(file_path, content)

            return True

        except Exception as e:
            logger.error(f"Failed to save YAML file {file_path}: {e}")
            return False

    async def ensure_file_exists(self, file_path: Path) -> None:
        """
        Ensure that a YAML file exists, creating it if necessary.

        Args:
            file_path: Path to the YAML file
        """
        if not file_path.exists():
            logger.debug(f"Creating missing YAML file: {file_path}")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Create empty YAML file
            await self.io_core.write_file(file_path, "{}\n")

    async def backup_file(self, file_path: Path, backup_suffix: str = ".bak") -> Path:
        """
        Create a backup of a YAML file.

        Args:
            file_path: Path to the file to backup
            backup_suffix: Suffix to append to the backup file

        Returns:
            Path to the backup file
        """
        backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)

        if file_path.exists():
            content = await self.io_core.read_file(file_path)
            await self.io_core.write_file(backup_path, content)
            logger.debug(f"Created backup: {backup_path}")
        else:
            logger.warning(f"Cannot backup non-existent file: {file_path}")

        return backup_path

    async def regenerate_settings_file(self, yaml_store: YAML) -> dict[str, Any]:
        """
        Regenerate a settings file from defaults.

        Args:
            yaml_store: The YAML store to regenerate

        Returns:
            Default settings data
        """
        logger.info(f"Regenerating {yaml_store} file")

        # Import file generation module
        try:
            from ClassicLib.FileGeneration import FileGeneration

            file_gen = FileGeneration()

            # Determine which file to regenerate
            if yaml_store == YAML.Settings:
                success = await file_gen.generate_settings_file()
            elif yaml_store == YAML.Main:
                success = await file_gen.generate_main_file()
            elif yaml_store == YAML.Game:
                # Game-specific files
                success = await file_gen.generate_game_files()
            else:
                logger.warning(f"Cannot regenerate {yaml_store} file")
                return {}

            if success:
                # Reload the regenerated file
                file_path = self.get_path_for_store(yaml_store)
                return await self.load_yaml_file(file_path)

        except ImportError:
            logger.error("FileGeneration module not available")
        except Exception as e:
            logger.error(f"Failed to regenerate {yaml_store} file: {e}")

        return {}
