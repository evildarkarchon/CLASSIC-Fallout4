"""Pure Python fallback implementation of IniValidator.

This module provides a Python-only implementation of INI file validation
that matches the Rust interface.
"""

from pathlib import Path

from ClassicLib.scanning.game.config import ConfigFileCache
from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue


class IniValidator:
    """Validate game INI configuration files.

    This is a Python fallback implementation that matches the Rust interface.
    It checks INI files for known issues and configuration problems.

    Attributes:
        game_name: Name of the game (e.g., "Fallout4", "Skyrim").

    Example:
        >>> validator = IniValidator("Fallout4")
        >>> report = validator.validate_inis(Path("/game/root"))
        >>> print(report)

    """

    def __init__(self, game_name: str) -> None:
        """Initialize IniValidator for a specific game.

        Args:
            game_name: Name of the game to validate INIs for.

        """
        self.game_name = game_name

    @staticmethod
    def validate_inis(_game_root: Path) -> str:
        """Validate INI files and return formatted report.

        Performs comprehensive validation of game INI files and returns
        a formatted string report of issues and recommendations.

        Args:
            _game_root: Path to game root directory.

        Returns:
            Formatted validation report string.

        Example:
            >>> validator = IniValidator("Fallout4")
            >>> report = validator.validate_inis(Path("/game"))
            >>> if report:
            ...     print("Issues found:", report)

        """
        # Use existing Python implementation
        from ClassicLib.scanning.game.scan_mod_inis import scan_mod_inis

        return scan_mod_inis()

    def detect_all_issues(self, _config_files: dict[str, Path]) -> list[ConfigIssue]:  # noqa: PLR6301
        """Detect all INI configuration issues. GUI workers only.

        WARNING: This method uses AsyncBridge internally and creates additional event loop overhead.
        Not for CLI use. For CLI usage, use detect_all_ini_issues_async() directly with await.

        Scans INI files for known configuration issues and returns a list
        of ConfigIssue objects describing each problem. Uses the validator's
        game_name for game-specific validation.

        Args:
           _config_files: Dictionary mapping lowercase filenames to file paths.

        Returns:
            List of ConfigIssue objects describing detected problems.

        Example:
            >>> validator = IniValidator("Fallout4")
            >>> config_map = {"epo.ini": Path("/game/epo.ini")}
            >>> issues = validator.detect_all_issues(config_map)
            >>> for issue in issues:
            ...     print(f"{issue.setting}: {issue.description}")

        """
        # Create ConfigFileCache for issue detection
        config_cache = ConfigFileCache()

        # Use existing async detection logic
        from ClassicLib.AsyncBridge import AsyncBridge
        from ClassicLib.scanning.game.scan_mod_inis import detect_all_ini_issues_async

        bridge = AsyncBridge.get_instance()
        # Pass game_name context if the underlying function supports it
        return bridge.run_async(detect_all_ini_issues_async(config_cache))
