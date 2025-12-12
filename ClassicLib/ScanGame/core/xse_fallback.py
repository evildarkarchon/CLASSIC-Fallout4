"""Pure Python fallback implementation of XseChecker.

This module provides a Python-only implementation of XSE plugin validation
that matches the Rust interface.
"""

from enum import Enum
from pathlib import Path


class GameVersion(Enum):
    """Game version enumeration.

    Attributes:
        Null: Unknown/undetected game version.
        Original: Original game version.
        NextGen: Next-gen/updated game version.
        Vr: VR game version.

    """

    Null = "Null"
    Original = "Original"
    NextGen = "NextGen"
    Vr = "Vr"


class ValidationResult(Enum):
    """XSE validation result enumeration.

    Attributes:
        CorrectVersion: XSE plugin version matches game version.
        WrongVersion: XSE plugin version does not match game version.
        NotFound: XSE plugin not found.
        VersionNotDetected: Could not detect XSE plugin version.
        PluginsPathNotFound: F4SE/SKSE plugins directory not found.

    """

    CorrectVersion = "CorrectVersion"
    WrongVersion = "WrongVersion"
    NotFound = "NotFound"
    VersionNotDetected = "VersionNotDetected"
    PluginsPathNotFound = "PluginsPathNotFound"


class AddressLibInfo:
    """Address Library information.

    Attributes:
        version: Game version constant.
        filename: Filename of the Address Library file.
        description: Human-readable description.
        url: Nexus Mods URL for download.

    """

    def __init__(
        self,
        version: GameVersion,
        filename: str,
        description: str,
        url: str,
    ) -> None:
        """Initialize AddressLibInfo.

        Args:
            version: Game version constant.
            filename: Filename of the Address Library file.
            description: Human-readable description.
            url: Nexus Mods URL for download.

        """
        self.version = version
        self.filename = filename
        self.description = description
        self.url = url

    @staticmethod
    def vr() -> "AddressLibInfo":
        """Get Address Library info for VR version.

        Returns:
            AddressLibInfo for VR version.

        """
        return AddressLibInfo(
            version=GameVersion.Vr,
            filename="version-1-2-72-0.csv",
            description="Virtual Reality (VR) version",
            url="https://www.nexusmods.com/fallout4/mods/64879?tab=files",
        )

    @staticmethod
    def original() -> "AddressLibInfo":
        """Get Address Library info for original version.

        Returns:
            AddressLibInfo for original version.

        """
        return AddressLibInfo(
            version=GameVersion.Original,
            filename="version-1-10-163-0.bin",
            description="Non-VR (Regular) version",
            url="https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )

    @staticmethod
    def next_gen() -> "AddressLibInfo":
        """Get Address Library info for next-gen version.

        Returns:
            AddressLibInfo for next-gen version.

        """
        return AddressLibInfo(
            version=GameVersion.NextGen,
            filename="version-1-10-984-0.bin",
            description="Non-VR (New Game) version",
            url="https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )


class XseChecker:
    """Validate Address Library installation for F4SE/SKSE plugins.

    This is a Python fallback implementation that matches the Rust interface.

    Attributes:
        plugins_path: Path to F4SE/SKSE plugins directory.
        is_vr_mode: Whether game is in VR mode.
        game_version: Detected game version.

    Example:
        >>> # Simplest usage (defaults to Original version, non-VR)
        >>> checker = XseChecker(Path("/game/Data/F4SE/Plugins"))
        >>> result = checker.check()
        >>> message = checker.validate()
        >>> print(message)

    """

    def __init__(
        self,
        plugins_path: Path,
        is_vr_mode: bool = False,
        game_version: GameVersion = GameVersion.Original,
    ) -> None:
        """Initialize XseChecker.

        Args:
            plugins_path: Path to F4SE/SKSE plugins directory.
            is_vr_mode: Whether game is in VR mode (default: False).
            game_version: Game version enum (default: Original).

        """
        self.plugins_path = plugins_path
        self.is_vr_mode = is_vr_mode
        self.game_version = game_version

    @staticmethod
    def check() -> ValidationResult:
        """Perform the validation check.

        Note:
            This implementation uses global state from GlobalRegistry and
            YamlSettingsCache rather than instance attributes. This is a
            limitation of the current Python fallback implementation.

        Returns:
            ValidationResult indicating the status of the Address Library installation.

        Example:
            >>> result = XseChecker.check()
            >>> if result == ValidationResult.CorrectVersion:
            ...     print("Address Library is correct")

        """
        # Use existing Python implementation
        from ClassicLib.ScanGame.CheckXsePlugins import check_xse_plugins

        # Call existing function which returns a message string
        message = check_xse_plugins()

        # Parse message to determine result
        if "✔️" in message and "correct version" in message.lower():
            return ValidationResult.CorrectVersion
        if "wrong version" in message.lower():
            return ValidationResult.WrongVersion
        if "not found" in message.lower():
            return ValidationResult.NotFound
        if "unable to locate" in message.lower():
            return ValidationResult.VersionNotDetected
        if "plugins folder path" in message.lower():
            return ValidationResult.PluginsPathNotFound

        # Default to not detected if message format is unexpected
        return ValidationResult.VersionNotDetected

    @staticmethod
    def validate() -> str:
        """Perform validation and return formatted message.

        Note:
            This implementation uses global state from GlobalRegistry and
            YamlSettingsCache rather than instance attributes. This is a
            limitation of the current Python fallback implementation.

        Returns:
            Formatted message string with validation result.

        Example:
            >>> message = XseChecker.validate()
            >>> print(message)

        """
        # Use existing Python implementation
        from ClassicLib.ScanGame.CheckXsePlugins import check_xse_plugins

        return check_xse_plugins()
