"""
Resource loader for accessing bundled data files and managing persistent cache.

This module provides utilities to access data files that are bundled with
the package, whether running from source or as an installed package.
It also manages persistent caching for uvx compatibility.
"""

import os
from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Logger import logger


class ResourceLoader:
    """Handles loading of bundled resource files."""

    @staticmethod
    def _check_local_dir() -> Path | None:
        """Check GlobalRegistry LOCAL_DIR for CLASSIC Data."""
        local_dir = GlobalRegistry.get_local_dir()
        if local_dir:
            try:
                data_dir = Path(local_dir) / "CLASSIC Data"
                if data_dir.exists():
                    logger.debug(f"Using CLASSIC Data from LOCAL_DIR: {data_dir}")
            except Exception:
                return None
            else:
                return data_dir
        return None

    @staticmethod
    def _check_package_installation() -> Path | None:
        """Check for CLASSIC Data in package installation."""
        try:
            # Get the distribution with either naming convention
            dist = ResourceLoader._get_distribution()
            if dist is None:
                return None

            # Check package location
            package_data = ResourceLoader._check_package_location(dist)
            if package_data:
                return package_data

            # Check if it's in the egg/wheel and extract if needed
            return ResourceLoader._extract_from_wheel()

        except ImportError:
            logger.debug("pkg_resources not available")
            return None

    @staticmethod
    def _get_distribution() -> object | None:
        """Get the package distribution object."""
        import pkg_resources

        try:
            # Try both naming conventions
            for package_name in ["classic-fallout4", "classic_fallout4"]:
                try:
                    dist = pkg_resources.get_distribution(package_name)
                    if dist.location is not None:
                        return dist
                    logger.debug("Package distribution has no location")
                except pkg_resources.DistributionNotFound:
                    continue

            logger.debug("Package not installed via pip/setuptools")
            return None  # noqa: TRY300

        except Exception as e:
            logger.debug(f"Error getting distribution: {e}")
            return None

    @staticmethod
    def _check_package_location(dist) -> Path | None:  # noqa: ANN001
        """Check for CLASSIC Data in package location."""
        package_location = Path(dist.location)
        data_dir = package_location / "CLASSIC Data"
        if data_dir.exists():
            logger.debug(f"Using CLASSIC Data from package location: {data_dir}")
            return data_dir
        return None

    @staticmethod
    def _extract_from_wheel() -> Path | None:
        """Extract CLASSIC Data from egg/wheel if needed."""
        import pkg_resources

        if not pkg_resources.resource_exists("classic_fallout4", "CLASSIC Data"):
            return None

        # Extract to a stable location (not temp)
        import appdirs

        app_data_dir = Path(appdirs.user_data_dir("CLASSIC-Fallout4", "CLASSIC"))
        data_dir = app_data_dir / "CLASSIC Data"

        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            ResourceLoader._extract_bundled_data_pkg_resources(data_dir)

        if data_dir.exists():
            logger.debug(f"Using extracted CLASSIC Data: {data_dir}")
            return data_dir
        return None

    @staticmethod
    def _check_source_installation() -> Path | None:
        """Check relative to module for source installations."""
        module_dir = Path(__file__).parent.parent
        data_dir = module_dir / "CLASSIC Data"
        if data_dir.exists():
            logger.debug(f"Using CLASSIC Data from module directory: {data_dir}")
            return data_dir
        return None

    @staticmethod
    def _check_current_directory() -> Path | None:
        """Check current working directory."""
        cwd_data = Path.cwd() / "CLASSIC Data"
        if cwd_data.exists():
            logger.debug(f"Using CLASSIC Data from current directory: {cwd_data}")
            return cwd_data
        return None

    @staticmethod
    def _create_in_app_data() -> Path:
        """Create CLASSIC Data in user's app data directory as last resort."""
        try:
            import appdirs

            app_data_dir = Path(appdirs.user_data_dir("CLASSIC-Fallout4", "CLASSIC"))
            data_dir = app_data_dir / "CLASSIC Data"
            if not data_dir.exists():
                logger.warning(f"Creating CLASSIC Data directory in: {data_dir}")
                data_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Final fallback: current directory
            cwd_data = Path.cwd() / "CLASSIC Data"
            logger.warning("Creating CLASSIC Data in current directory")
            cwd_data.mkdir(parents=True, exist_ok=True)
            return cwd_data
        else:
            return data_dir

    @staticmethod
    def get_data_directory() -> Path:
        """
        Get the path to the CLASSIC Data directory.

        Tries multiple strategies:
        1. Check GlobalRegistry LOCAL_DIR
        2. Check relative to package installation using pkg_resources
        3. Check relative to module for source installations
        4. Check current working directory
        5. Create in user app data directory as last resort

        Returns:
            Path to the CLASSIC Data directory
        """
        # Try each strategy in order
        strategies = [
            ResourceLoader._check_local_dir,
            ResourceLoader._check_package_installation,
            ResourceLoader._check_source_installation,
            ResourceLoader._check_current_directory,
        ]

        for strategy in strategies:
            result = strategy()
            if result:
                return result

        # Last resort: create in app data
        return ResourceLoader._create_in_app_data()

    @staticmethod
    def _extract_bundled_data_pkg_resources(target_dir: Path) -> None:
        """
        Extract bundled data files using pkg_resources.

        Args:
            target_dir: Directory to extract files to
        """
        import pkg_resources

        try:
            # List of essential files to extract
            essential_files = [
                "databases/CLASSIC Main.yaml",
                "databases/CLASSIC Fallout4.yaml",
                "databases/CLASSIC Skyrim.yaml",
                "databases/Fallout4 FormIDs Main.db",
                "databases/Fallout4 FID Mods.txt",
            ]

            for file_path in essential_files:
                resource_path = f"CLASSIC Data/{file_path}"

                try:
                    if pkg_resources.resource_exists("classic_fallout4", resource_path.replace("/", "/")):
                        # Read the resource
                        data = pkg_resources.resource_string("classic_fallout4", resource_path)

                        # Write to target location
                        target_file = target_dir / file_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)

                        # Write as binary to preserve exact content
                        target_file.write_bytes(data)
                        logger.debug(f"Extracted {file_path} from package")

                except Exception as e:
                    logger.warning(f"Could not extract {file_path}: {e}")

        except Exception as e:
            logger.error(f"Failed to extract bundled data: {e}")

    @staticmethod
    def ensure_data_files_exist() -> Path:
        """
        Ensure essential data files exist and are accessible.

        Returns:
            Path to the CLASSIC Data directory

        Raises:
            RuntimeError: If essential files cannot be accessed
        """
        data_dir = ResourceLoader.get_data_directory()

        # Check for essential database files
        databases_dir = data_dir / "databases"
        essential_files = [
            databases_dir / "CLASSIC Main.yaml",
            databases_dir / "CLASSIC Fallout4.yaml",
        ]

        missing_files = [f for f in essential_files if not f.exists()]

        if missing_files:
            logger.warning(f"Missing essential files: {missing_files}")
            # Let the application handle generation

        return data_dir

    @staticmethod
    def get_cached_game_path(game_name: str | None = None, vr_suffix: str = "") -> Path | None:
        """
        Get cached game path using multiple strategies for uvx compatibility.

        Checks in order:
        1. Environment variable (CLASSIC_<GAME>_PATH)
        2. Persistent cache.yaml in user config directory
        3. Local.yaml in CLASSIC Data (traditional cache)

        Args:
            game_name: Game name (defaults to GlobalRegistry.get_game())
            vr_suffix: VR suffix (defaults to GlobalRegistry.get_vr())

        Returns:
            Cached game path or None if not found
        """
        if game_name is None:
            game_name = GlobalRegistry.get_game()
        if not vr_suffix:
            vr_suffix = GlobalRegistry.get_vr()

        # Strategy 1: Check environment variable (fastest for uvx)
        env_var = f"CLASSIC_{game_name.upper()}{vr_suffix}_PATH"
        env_path = os.environ.get(env_var)
        if env_path:
            path = Path(env_path)
            if path.exists() and path.is_dir():
                logger.debug(f"Found game path from environment variable {env_var}: {path}")
                return path

        # Strategy 2: Check persistent cache.yaml
        try:
            from ClassicLib.Constants import YAML
            from ClassicLib.YamlSettingsCache import yaml_settings

            cached_path = yaml_settings(str, YAML.Cache, f"{game_name}{vr_suffix}.GamePath")
            if cached_path:
                path = Path(cached_path)
                if path.exists() and path.is_dir():
                    logger.debug(f"Found game path in cache.yaml: {path}")
                    return path
        except Exception as e:
            logger.debug(f"Could not read from cache.yaml: {e}")

        # Strategy 3: Check traditional Local.yaml
        try:
            from ClassicLib.Constants import YAML
            from ClassicLib.YamlSettingsCache import yaml_settings

            local_path = yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Root_Folder_Game")
            if local_path:
                path = Path(local_path)
                if path.exists() and path.is_dir():
                    logger.debug(f"Found game path in Local.yaml: {path}")
                    return path
        except Exception as e:
            logger.debug(f"Could not read from Local.yaml: {e}")

        return None

    @staticmethod
    def get_cached_docs_path(game_name: str | None = None, vr_suffix: str = "") -> Path | None:
        """
        Get cached documents path using multiple strategies for uvx compatibility.

        Checks in order:
        1. Environment variable (CLASSIC_<GAME>_DOCS)
        2. Persistent cache.yaml in user config directory
        3. Local.yaml in CLASSIC Data (traditional cache)

        Args:
            game_name: Game name (defaults to GlobalRegistry.get_game())
            vr_suffix: VR suffix (defaults to GlobalRegistry.get_vr())

        Returns:
            Cached documents path or None if not found
        """
        if game_name is None:
            game_name = GlobalRegistry.get_game()
        if not vr_suffix:
            vr_suffix = GlobalRegistry.get_vr()

        # Strategy 1: Check environment variable
        env_var = f"CLASSIC_{game_name.upper()}{vr_suffix}_DOCS"
        env_path = os.environ.get(env_var)
        if env_path:
            path = Path(env_path)
            if path.exists() and path.is_dir():
                logger.debug(f"Found docs path from environment variable {env_var}: {path}")
                return path

        # Strategy 2: Check persistent cache.yaml
        try:
            from ClassicLib.Constants import YAML
            from ClassicLib.YamlSettingsCache import yaml_settings

            cached_path = yaml_settings(str, YAML.Cache, f"{game_name}{vr_suffix}.DocsPath")
            if cached_path:
                path = Path(cached_path)
                if path.exists() and path.is_dir():
                    logger.debug(f"Found docs path in cache.yaml: {path}")
                    return path
        except Exception as e:
            logger.debug(f"Could not read from cache.yaml: {e}")

        # Strategy 3: Check traditional Local.yaml
        try:
            from ClassicLib.Constants import YAML
            from ClassicLib.YamlSettingsCache import yaml_settings

            local_path = yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Root_Folder_Docs")
            if local_path:
                path = Path(local_path)
                if path.exists() and path.is_dir():
                    logger.debug(f"Found docs path in Local.yaml: {path}")
                    return path
        except Exception as e:
            logger.debug(f"Could not read from Local.yaml: {e}")

        return None

    @staticmethod
    def save_path_to_cache(path: Path, path_type: str, game_name: str | None = None, vr_suffix: str = "") -> None:
        """
        Save a discovered path to all available cache locations.

        Saves to:
        1. Persistent cache.yaml (for uvx persistence)
        2. Local.yaml (for backward compatibility)
        3. Suggests environment variable to user

        Args:
            path: Path to save
            path_type: Either "GamePath" or "DocsPath"
            game_name: Game name (defaults to GlobalRegistry.get_game())
            vr_suffix: VR suffix (defaults to GlobalRegistry.get_vr())
        """
        if game_name is None:
            game_name = GlobalRegistry.get_game()
        if not vr_suffix:
            vr_suffix = GlobalRegistry.get_vr()

        from ClassicLib import msg_info
        from ClassicLib.Constants import YAML
        from ClassicLib.YamlSettingsCache import yaml_settings

        # Save to persistent cache.yaml
        try:
            yaml_settings(str, YAML.Cache, f"{game_name}{vr_suffix}.{path_type}", str(path))
            logger.debug(f"Saved {path_type} to cache.yaml")
        except Exception as e:
            logger.warning(f"Could not save to cache.yaml: {e}")

        # Save to Local.yaml for backward compatibility
        try:
            if path_type == "GamePath":
                yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Root_Folder_Game", str(path))
            elif path_type == "DocsPath":
                yaml_settings(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Root_Folder_Docs", str(path))
            logger.debug(f"Saved {path_type} to Local.yaml")
        except Exception as e:
            logger.warning(f"Could not save to Local.yaml: {e}")

        # Suggest environment variable for faster future runs
        if path_type == "GamePath":
            env_var = f"CLASSIC_{game_name.upper()}{vr_suffix}_PATH"
        else:
            env_var = f"CLASSIC_{game_name.upper()}{vr_suffix}_DOCS"

        msg_info(f"💡 For faster startup (especially with uvx), set environment variable:\n   {env_var}={path}")


# Convenience function
def get_resource_path(relative_path: str) -> Path:
    """
    Get the full path to a resource file.

    Args:
        relative_path: Path relative to CLASSIC Data directory

    Returns:
        Full path to the resource file
    """
    data_dir = ResourceLoader.get_data_directory()
    return data_dir / relative_path
