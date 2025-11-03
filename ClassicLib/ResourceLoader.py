"""
Resource loader for accessing bundled data files and managing persistent cache.

This module provides utilities to access data files that are bundled with
the package, whether running from source, as an installed package, or as a
PyInstaller frozen executable. It also manages persistent caching for uvx compatibility.

It also provides integration with Rust extensions through the rust_loader module.
"""

import asyncio
import os
import sys
from importlib.metadata import PackageNotFoundError, distribution
from importlib.resources import files
from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Logger import logger


class ResourceLoader:
    """Handles loading of bundled resource files."""

    @staticmethod
    def _check_executable_directory() -> Path | None:
        """Check for CLASSIC Data next to the executable.

        For frozen executables (PyInstaller), this checks for CLASSIC Data
        in the same directory as the .exe file. This is the primary location
        for production deployments.

        Returns:
            Path to CLASSIC Data next to executable, or None if not found
        """
        if getattr(sys, 'frozen', False):
            # Get directory containing the executable
            exe_dir = Path(sys.executable).parent
            data_dir = exe_dir / "CLASSIC Data"

            if data_dir.exists():
                logger.debug(f"Using CLASSIC Data from executable directory: {data_dir}")
                return data_dir
            logger.debug(f"CLASSIC Data not found next to executable: {exe_dir}")

        return None

    @staticmethod
    def _check_frozen_bundle() -> Path | None:
        """Check PyInstaller frozen bundle for CLASSIC Data (YAML configs only).

        This is a fallback for bundled YAML configuration files extracted to
        sys._MEIPASS. Note: Database files are NOT bundled, only configs.

        Returns:
            Path to CLASSIC Data in frozen bundle, or None if not found
        """
        # Check if we're running as a PyInstaller frozen executable
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller extracts data files to sys._MEIPASS
            bundle_dir = Path(sys._MEIPASS)
            data_dir = bundle_dir / "CLASSIC Data"

            if data_dir.exists():
                logger.debug(f"Using bundled CLASSIC Data from temp extraction: {data_dir}")
                return data_dir

        return None

    @staticmethod
    def _check_local_dir() -> Path | None:
        """
        Checks the existence of a specific local directory and retrieves its path if it exists.

        This method attempts to find a directory named "CLASSIC Data" under the local directory
        defined in the `GlobalRegistry`. If the directory exists, its path is returned. Otherwise,
        it returns `None`.

        Returns:
            Path | None: Path to the "CLASSIC Data" directory if it exists; otherwise, `None`.
        """
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
        """
        Checks the installation and location of a package to ensure that it is accessible
        and provides the necessary resources. Attempts to retrieve information about the
        package distribution, verify its location, and, if required, extract the package
        resources.

        Returns:
            Path | None: Returns the path to the package's necessary resource files if
            successful, or None if the package is not installed or the resources cannot
            be accessed.
        """
        try:
            # Get the distribution with either naming convention
            dist = ResourceLoader._get_distribution()
            if dist is None:
                return None

            # Check package location
            package_data = ResourceLoader._check_package_location(dist)
            if package_data:
                return package_data

            # Check if it's in the package resources and extract if needed
            return ResourceLoader._extract_from_package()

        except (ImportError, PackageNotFoundError):
            logger.debug("Package distribution not available")
            return None

    @staticmethod
    def _get_distribution() -> object | None:
        """
        Attempts to retrieve the distribution information for specific package names
        using the `importlib.metadata` library. It tries the package names
        "classic-fallout4", "classic_fallout4", and "classic" in order.

        If the distribution cannot be found for any of these names, it logs the
        occurrence and returns `None`. In case of an unexpected error, the exception
        is caught and logged before returning `None`.

        Returns:
            object | None: The distribution object if found, otherwise `None`.
        """
        try:
            # Try both naming conventions
            for package_name in ["classic-fallout4", "classic_fallout4", "classic"]:
                try:
                    dist = distribution(package_name)
                    # Distribution object from importlib.metadata always has location info
                    return dist
                except PackageNotFoundError:
                    continue

            logger.debug("Package not installed via pip/setuptools")
            return None  # noqa: TRY300

        except Exception as e:
            logger.debug(f"Error getting distribution: {e}")
            return None

    @staticmethod
    def _check_package_location(dist) -> Path | None:  # noqa: ANN001
        """
        Checks and retrieves the data directory for a package based on its distribution
        metadata. This method examines the attributes of the distribution object or uses
        alternative methods to locate the associated "CLASSIC Data" directory.

        Args:
            dist: The distribution object of the package being checked.

        Returns:
            Path | None: The path to the "CLASSIC Data" directory if found. Returns None
            if the directory cannot be located.
        """
        try:
            # Get location from the distribution metadata
            # For wheel/installed packages, check the site-packages location
            if hasattr(dist, '_path') and dist._path:
                package_location = Path(dist._path).parent
            elif hasattr(dist, 'locate_file'):
                # Alternative method for some distributions
                package_location = Path(str(dist.locate_file('')))
            else:
                # Fallback: try to find via files() API
                try:
                    pkg_files = files('classic')
                    if pkg_files:
                        package_location = Path(str(pkg_files)).parent
                    else:
                        return None
                except Exception:
                    return None

            data_dir = package_location / "CLASSIC Data"
            if data_dir.exists():
                logger.debug(f"Using CLASSIC Data from package location: {data_dir}")
                return data_dir
        except Exception as e:
            logger.debug(f"Error checking package location: {e}")
        return None

    @staticmethod
    def _extract_from_package() -> Path | None:
        """
        Extracts the "CLASSIC Data" directory from the specified package and places it into a stable local directory.

        This method attempts to locate an installed Python package containing resources for "CLASSIC Data". If found, it
        ensures the data directory exists and extracts the bundled data resources using a stable path on the user's system.
        The method prioritizes different package name alternatives ("ClassicLib" or "classic") until one is valid. If the
        directory is successfully processed and located, the path to the data directory is returned. Otherwise, it logs
        debug information and safely handles failures.

        Returns:
            Path | None: The path to the `CLASSIC Data` directory if successfully extracted and verified, or None if the
            process fails or the resources are not available.
        """
        try:
            # Try to get package files - works for installed packages
            # Try different package name variations
            package_files = None
            for pkg_name in ["ClassicLib", "classic"]:
                try:
                    package_files = files(pkg_name)
                    if package_files:
                        break
                except (ModuleNotFoundError, TypeError):
                    continue

            if not package_files:
                logger.debug("Package files not available via importlib.resources")
                return None

            # Check if CLASSIC Data directory exists in package
            try:
                classic_data = package_files / "CLASSIC Data"
                if not classic_data.is_dir():
                    return None
            except (AttributeError, TypeError):
                return None

            # Extract to a stable location (not temp)
            import appdirs

            app_data_dir = Path(appdirs.user_data_dir("CLASSIC-Fallout4", "CLASSIC"))
            data_dir = app_data_dir / "CLASSIC Data"

            if not data_dir.exists():
                data_dir.mkdir(parents=True, exist_ok=True)
                ResourceLoader._extract_bundled_data_importlib(data_dir, package_files)

            if data_dir.exists():
                logger.debug(f"Using extracted CLASSIC Data: {data_dir}")
                return data_dir
        except Exception as e:
            logger.debug(f"Could not extract from package resources: {e}")

        return None

    @staticmethod
    def _check_source_installation() -> Path | None:
        """
        Checks the source installation for the presence of the "CLASSIC Data" directory.

        This method verifies if the "CLASSIC Data" directory exists in the parent
        directory of the module’s location. If the directory is present, its path
        is returned. Otherwise, returns None.

        Returns:
            Path | None: The path to the "CLASSIC Data" directory if it exists,
            otherwise None.
        """
        module_dir = Path(__file__).parent.parent
        data_dir = module_dir / "CLASSIC Data"
        if data_dir.exists():
            logger.debug(f"Using CLASSIC Data from module directory: {data_dir}")
            return data_dir
        return None

    @staticmethod
    def _check_current_directory() -> Path | None:
        """
        Checks if the current directory contains the "CLASSIC Data" folder.

        This method verifies the existence of a "CLASSIC Data" folder in the current
        working directory. If such a directory exists, it logs its path and returns
        it. Otherwise, it returns None.

        Returns:
            Path | None: The path to the "CLASSIC Data" folder if it exists in the
            current directory; otherwise, None.
        """
        cwd_data = Path.cwd() / "CLASSIC Data"
        if cwd_data.exists():
            logger.debug(f"Using CLASSIC Data from current directory: {cwd_data}")
            return cwd_data
        return None

    @staticmethod
    def _create_in_app_data() -> Path:
        """
        Creates and ensures the existence of a directory for application-specific data storage. The method attempts to store
        data in a user-specific directory, falling back to the current working directory in case of failure.

        Returns:
            Path: The path to the created application data directory.

        Raises:
            Exception: If a directory creation operation is unsuccessful.
        """
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
        Attempts to locate the data directory using various strategies in a prioritized
        order. The method systematically executes a list of strategies for determining
        the correct directory path for data resources and returns the first valid path
        found. If no strategies succeed, it creates and returns a path in the application
        data folder as a last resort.

        Returns:
            Path: The directory path to be used for data resources.
        """
        # Try each strategy in order
        strategies = [
            ResourceLoader._check_executable_directory,  # Check next to .exe first (production)
            ResourceLoader._check_local_dir,            # Check user override
            ResourceLoader._check_source_installation,  # Check source directory (development)
            ResourceLoader._check_current_directory,    # Check current working directory
            ResourceLoader._check_frozen_bundle,        # Check bundled configs (fallback)
            ResourceLoader._check_package_installation, # Check installed package
        ]

        for strategy in strategies:
            result = strategy()
            if result:
                return result

        # Last resort: create in app data
        return ResourceLoader._create_in_app_data()

    @staticmethod
    def _extract_bundled_data_importlib(target_dir: Path, package_files=None) -> None:  # noqa: ANN001
        """
        Extracts bundled essential data using the importlib resources API.

        This method extracts specific files (not databases) from bundled package resources
        to a target directory. It checks and maintains file hierarchy in the destination
        directory, ensuring any missing parent directories are created. This method only
        handles non-database files since database files are expected to be managed locally
        by the user for better performance and clarity in permission management.

        Args:
            target_dir (Path): The directory where the essential files will be extracted to.
            package_files (optional): A traversable object representing the package resources.
                If not specified, the method tries to locate package resources dynamically
                from default package names.

        Raises:
            Exception: If the extraction process fails for any file or operation.
        """
        try:
            # List of essential files to extract
            # NOTE: Database files (.db) are NOT extracted from package.
            # They must be present in the user's local CLASSIC Data directory to allow:
            # - Write access for WAL mode (performance)
            # - Database updates without recompiling
            # - Clear user responsibility for file permissions
            essential_files = [
                "databases/CLASSIC Main.yaml",
                "databases/CLASSIC Fallout4.yaml",
                "databases/CLASSIC Skyrim.yaml",
                "databases/Fallout4 FID Mods.txt",  # Text file, not a database
                # Databases NOT extracted: Fallout4 FormIDs Main.db, etc.
            ]

            # Get package files if not provided
            if package_files is None:
                for pkg_name in ["ClassicLib", "classic"]:
                    try:
                        package_files = files(pkg_name)
                        if package_files:
                            break
                    except (ModuleNotFoundError, TypeError):
                        continue

            if not package_files:
                logger.warning("Package files not available")
                return

            for file_path in essential_files:
                try:
                    # Navigate to the resource using the traversable interface
                    resource_parts = ["CLASSIC Data"] + file_path.split("/")
                    resource = package_files

                    for part in resource_parts:
                        resource = resource / part

                    if resource.is_file():
                        # Read the resource
                        data = resource.read_bytes()

                        # Write to target location
                        target_file = target_dir / file_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)

                        # Write as binary to preserve exact content
                        target_file.write_bytes(data)
                        logger.debug(f"Extracted {file_path} from package")
                    else:
                        logger.debug(f"Resource not found: {file_path}")

                except Exception as e:
                    logger.warning(f"Could not extract {file_path}: {e}")

        except Exception as e:
            logger.error(f"Failed to extract bundled data: {e}")

    @staticmethod
    def ensure_data_files_exist() -> Path:
        """
        Ensures that essential data files exist in the specified data directory.

        This static method checks the presence of essential database files required for the
        application's operation. If any files are missing, it logs a warning and defers handling
        file generation to the application. The method returns the path to the data directory.

        Returns:
            Path: The path object representing the data directory.

        Raises:
            None: This method does not directly raise any errors, but missing files are logged.
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
        Fetches the cached game installation directory path based on the specified game name and
        optional VR (Virtual Reality) suffix. This method attempts multiple strategies to locate
        the game path: via an environment variable, a persistent `cache.yaml` configuration file,
        and a traditional `Local.yaml` configuration file. Returns the directory path as a Path
        object if found; otherwise, returns None.

        This method is static and operates independently of object instantiations.

        Args:
            game_name (str | None): The name of the game for which the path is to be fetched. If None,
                the global registry's default value for the game is used.
            vr_suffix (str): An optional string indicating a VR-specific suffix for the game. Defaults
                to an empty string.

        Returns:
            Path | None: Returns the directory path to the game as a Path object if found. Returns
                None if the game directory is not found in any of the search strategies.

        Raises:
            This method does not explicitly raise exceptions, but any exceptions occurring during
            internal operations are logged.
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
        Retrieves the cached documentation path for a specific game and VR suffix. The method attempts
        to locate the directory path using three strategies. First, it checks for an environment variable
        with a naming convention based on the provided game name and suffix. If no valid path is found,
        it proceeds to read from a persistent `cache.yaml` file. Finally, it attempts to locate the path
        in a traditional `Local.yaml` configuration file. If none of the strategies succeed, it returns None.

        Args:
            game_name (str | None): Name of the game to retrieve the documentation path for. Defaults
                to the global game name if None.
            vr_suffix (str): Suffix for identifying VR-specific paths. Defaults to an empty string.

        Returns:
            Path | None: The cached documentation path if found, otherwise None.
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
    async def save_path_to_cache_async(path: Path, path_type: str, game_name: str | None = None, vr_suffix: str = "") -> None:
        """
        Asynchronously saves a path to persistent cache and local configuration files.

        This is the async version that should be used from async contexts.
        It uses yaml_settings_async() to properly handle async contexts without blocking.

        Args:
            path (Path): The file or directory path to be saved.
            path_type (str): The type of path being saved, e.g., "GamePath" or "DocsPath".
            game_name (str | None, optional): The name of the game for which the path is associated.
            vr_suffix (str, optional): A suffix representing a specific virtual reality context.
        """
        if game_name is None:
            game_name = GlobalRegistry.get_game()
        if not vr_suffix:
            vr_suffix = GlobalRegistry.get_vr()

        from ClassicLib.Constants import YAML
        from ClassicLib.YamlSettingsCache import yaml_settings_async

        # Save to persistent cache.yaml
        try:
            await yaml_settings_async(str, YAML.Cache, f"{game_name}{vr_suffix}.{path_type}", str(path))
            logger.debug(f"Saved {path_type} to cache.yaml")
        except Exception as e:
            logger.warning(f"Could not save to cache.yaml: {e}")

        # Save to Local.yaml for backward compatibility
        try:
            if path_type == "GamePath":
                await yaml_settings_async(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Root_Folder_Game", str(path))
            elif path_type == "DocsPath":
                await yaml_settings_async(str, YAML.Game_Local, f"Game{vr_suffix}_Info.Root_Folder_Docs", str(path))
            logger.debug(f"Saved {path_type} to Local.yaml")
        except Exception as e:
            logger.warning(f"Could not save to Local.yaml: {e}")

    @staticmethod
    def save_path_to_cache(path: Path, path_type: str, game_name: str | None = None, vr_suffix: str = "") -> None:
        """
        Saves a path to persistent cache and local configuration files (sync version).

        This method detects whether it's being called from an async context and automatically
        uses the appropriate method (async or sync). When called from async context, it runs
        the async version; otherwise, it uses AsyncBridge for sync contexts.

        Note: This method should only be used from sync contexts (GUI initialization).
        For async contexts (CLI, async functions), use save_path_to_cache_async() directly.

        Args:
            path (Path): The file or directory path to be saved.
            path_type (str): The type of path being saved, e.g., "GamePath" or "DocsPath".
            game_name (str | None, optional): The name of the game for which the path is associated.
            vr_suffix (str, optional): A suffix representing a specific virtual reality context.
        """
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # If we get here, we're in an async context - run the async version
            logger.debug("Detected async context in save_path_to_cache, using save_path_to_cache_async")
            # Create a task to run the async version
            asyncio.create_task(ResourceLoader.save_path_to_cache_async(path, path_type, game_name, vr_suffix))
            return
        except RuntimeError:
            # No running event loop - we're in a sync context, continue with sync version
            pass

        if game_name is None:
            game_name = GlobalRegistry.get_game()
        if not vr_suffix:
            vr_suffix = GlobalRegistry.get_vr()

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

        # Suggest environment variable for faster future runs (disabled - too noisy)
        # if path_type == "GamePath":
        #     env_var = f"CLASSIC_{game_name.upper()}{vr_suffix}_PATH"
        # else:
        #     env_var = f"CLASSIC_{game_name.upper()}{vr_suffix}_DOCS"
        # msg_info(f"💡 For faster startup (especially with uvx), set environment variable:\n   {env_var}={path}")

    @staticmethod
    def load_rust_extension() -> bool:
        """
        Loads Rust extensions to optimize performance if available.

        This static method checks whether Rust extensions are available and loads them
        if they are not already loaded. If Rust extensions are successfully loaded,
        it enables performance optimizations in the application. Otherwise, it falls
        back to a pure Python implementation.

        Returns:
            bool: True if Rust extensions are successfully loaded or already available,
            otherwise False.

        Raises:
            ImportError: If the required module 'rust_loader' cannot be imported.
            Exception: If any other unexpected error occurs during the loading process.
        """
        try:
            from ClassicLib.rust_loader import is_rust_available, load_rust_extensions

            if is_rust_available():
                logger.debug("Rust extensions already loaded")
                return True

            success = load_rust_extensions()
            if success:
                logger.info("Rust extensions loaded successfully for performance optimization")
            else:
                logger.info("Rust extensions not available - using pure Python implementation")

            return success
        except ImportError as e:
            logger.debug(f"Could not import rust_loader: {e}")
            return False
        except Exception as e:
            logger.warning(f"Error loading Rust extensions: {e}")
            return False

    @staticmethod
    def get_rust_extension_info() -> dict:
        """
        Retrieves information regarding the Rust extension module.

        This method attempts to import and retrieve information about the Rust extension
        module using the `get_rust_info` function from the `ClassicLib.rust_loader`
        module. If the module is unavailable or fails to import, it returns fallback
        information indicating the module is not loaded and provides details about the
        current environment.

        Returns:
            dict: A dictionary containing information about the Rust extension module:
                - "loaded" (bool): Indicates whether the Rust module is successfully loaded.
                - "path" (str or None): The path of the loaded Rust module, or `None` if not loaded.
                - "search_paths" (list): List of paths searched for the Rust module.
                - "in_pyinstaller" (bool): Indicates whether the environment is within a PyInstaller build.
                - "error" (str): An error message indicating why the Rust module could not be loaded,
                  if applicable.
        """
        try:
            from ClassicLib.rust_loader import get_rust_info
            return get_rust_info()
        except ImportError:
            return {
                "loaded": False,
                "path": None,
                "search_paths": [],
                "in_pyinstaller": getattr(sys, 'frozen', False),
                "error": "rust_loader module not available"
            }


# Convenience function
def get_resource_path(relative_path: str) -> Path:
    """
    Get the full path to a resource file.

    This function handles path resolution for both frozen (PyInstaller) and
    non-frozen execution contexts. In frozen mode, it accesses files from
    the temporary extraction directory. In development mode, it uses the
    source directory structure.

    Args:
        relative_path: Path relative to CLASSIC Data directory

    Returns:
        Full path to the resource file
    """
    data_dir = ResourceLoader.get_data_directory()
    return data_dir / relative_path


def is_frozen() -> bool:
    """
    Check if the application is running as a frozen executable.

    This is useful for conditional logic that needs to behave differently
    in development vs. production (frozen) environments.

    Returns:
        True if running as PyInstaller frozen executable, False otherwise
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
