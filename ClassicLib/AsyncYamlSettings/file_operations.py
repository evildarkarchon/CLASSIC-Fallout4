"""File operations for AsyncYamlSettings."""

from io import StringIO
from pathlib import Path
from typing import Any, ClassVar, Optional

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

        # Try to get Rust YAML operations if available
        self.rust_yaml: Optional[Any] = None
        try:
            from ClassicLib.integration.factory import get_yaml_operations
            self.rust_yaml = get_yaml_operations()
            if self.rust_yaml:
                logger.debug("YamlFileOperations: Using Rust acceleration for YAML parsing")
        except ImportError:
            logger.debug("YamlFileOperations: Rust YAML operations not available")

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

    async def parse_yaml_content(self, content: str) -> dict[str, Any]:
        """
        Parse YAML content from string.

        Args:
            content: YAML string content

        Returns:
            Parsed YAML data
        """
        # Try Rust acceleration first
        if self.rust_yaml:
            try:
                result = self.rust_yaml.parse_yaml(content)
                return result if isinstance(result, dict) else {}
            except Exception as e:
                logger.debug(f"Rust YAML parsing failed, falling back to Python: {e}")

        # Fallback to Python implementation
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

        Args:
            data: Data to serialize

        Returns:
            YAML string
        """
        # Try Rust acceleration first
        if self.rust_yaml:
            try:
                return self.rust_yaml.dump_yaml(data)
            except Exception as e:
                logger.debug(f"Rust YAML dumping failed, falling back to Python: {e}")

        # Fallback to Python implementation
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

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML data
        """
        try:
            # Try Rust acceleration first (includes caching)
            if self.rust_yaml:
                try:
                    result = self.rust_yaml.load_yaml_file(str(file_path))
                    return result if isinstance(result, dict) else {}
                except Exception as e:
                    logger.debug(f"Rust YAML file loading failed, falling back to Python: {e}")

            # Fallback to Python implementation
            # Use FileIOCore for async file reading
            content = await self.io_core.read_file(file_path)

            if not content:
                logger.warning(f"Empty YAML file: {file_path}")
                return {}

            return await self.parse_yaml_content(content)

        except FileNotFoundError:
            logger.debug(f"YAML file not found: {file_path}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load YAML file {file_path}: {e}")
            return {}

    async def save_yaml_file(self, file_path: Path, data: dict[str, Any]) -> bool:
        """
        Save data to a YAML file.

        Args:
            file_path: Path to save to
            data: Data to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Try Rust acceleration first (includes atomic write)
            if self.rust_yaml:
                try:
                    self.rust_yaml.save_yaml_file(str(file_path), data)
                    return True
                except Exception as e:
                    logger.debug(f"Rust YAML file saving failed, falling back to Python: {e}")

            # Fallback to Python implementation
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to YAML string
            content = await self.dump_yaml_content(data)

            # Use FileIOCore for async file writing
            await self.io_core.write_file(file_path, content)

            return True

        except Exception as e:
            logger.error(f"Failed to save YAML file {file_path}: {e}")
            return False

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
