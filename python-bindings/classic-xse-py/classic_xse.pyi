r"""Type stubs for classic_xse.

Python bindings for classic-xse-core, providing comprehensive Script Extender (XSE)
handling for Bethesda games, including version detection, file location, and status checking.

Architecture:
    - classic-xse-core: Business logic (XSE detection, version parsing)
    - classic-xse-py: Python bindings (this module - PyO3 adapters)

Features:
    - XSE type enumeration (F4SE, SKSE, SFSE, etc.)
    - Version detection from loader executables
    - Installation status checking
    - File path utilities

Usage:
    import classic_xse

    # Check if F4SE is installed
    if classic_xse.is_xse_installed("C:\\Games\\Fallout4", classic_xse.XseType.f4se()):
        print("F4SE is installed")

    # Get detailed info
    info = classic_xse.get_xse_info("C:\\Games\\Fallout4", classic_xse.XseType.f4se())
    if info.installed():
        version = info.version()
        if version:
            print(f"F4SE version: {version[0]}.{version[1]}.{version[2]}")
"""

__version__: str

# Type alias for version tuples
type Version = tuple[int, int, int]

class XseType:
    """XSE type enumeration for Python.

    Each variant corresponds to a specific Script Extender for a Bethesda game.
    """

    @staticmethod
    def f4se() -> XseType:
        """Create an F4SE type."""

    @staticmethod
    def f4sevr() -> XseType:
        """Create an F4SEVR type."""

    @staticmethod
    def skse() -> XseType:
        """Create an SKSE type."""

    @staticmethod
    def skse64() -> XseType:
        """Create an SKSE64 type."""

    @staticmethod
    def sksevr() -> XseType:
        """Create an SKSEVR type."""

    @staticmethod
    def sfse() -> XseType:
        """Create an SFSE type."""

    def as_str(self) -> str:
        """Get the XSE type name as a string.

        Example:
            >>> xse = XseType.f4se()
            >>> assert xse.as_str() == "F4SE"

        """

    def loader_name(self) -> str:
        """Get the loader executable name.

        Example:
            >>> xse = XseType.f4se()
            >>> assert xse.loader_name() == "f4se_loader.exe"

        """

    def dll_prefix(self) -> str:
        """Get the DLL prefix for this XSE type.

        Example:
            >>> xse = XseType.f4se()
            >>> assert xse.dll_prefix() == "f4se_"

        """

    def __eq__(self, other: object) -> bool:
        """Compare XSE types for equality."""

    def __str__(self) -> str:
        """Return the short variant name (e.g. ``"F4SE"``)."""

    def __repr__(self) -> str:
        """Return a debug representation suitable for logs and REPL output."""

class XseInfo:
    """XSE installation information for Python.

    Contains detailed information about an XSE installation including
    its type, path, version, and installation status.
    """

    def __init__(self, xse_type: XseType, path: str) -> None:
        r"""Create a new XseInfo.

        Args:
            xse_type: The XSE type.
            path: The installation path.

        Example:
            >>> info = XseInfo(XseType.f4se(), "C:\\Games\\Fallout4")
            >>> assert info.xse_type().as_str() == "F4SE"

        """

    def xse_type(self) -> XseType:
        """Get the XSE type."""

    def path(self) -> str:
        """Get the installation path."""

    def version(self) -> Version | None:
        """Get the detected version.

        Returns:
            A tuple of (major, minor, patch) if version was detected, None otherwise.

        """

    def installed(self) -> bool:
        """Check if XSE is installed."""

    def check_installed(self) -> bool:
        """Check if the XSE loader executable exists."""

    def loader_path(self) -> str:
        """Get the full path to the loader executable."""

    def __str__(self) -> str:
        """Return a human-readable description of the XSE installation."""

    def __repr__(self) -> str:
        """Return a debug representation suitable for logs and REPL output."""

def parse_xse_type(type_name: str) -> XseType:
    """Parse an XSE type from a string.

    Args:
        type_name: The XSE type name (case-insensitive).

    Returns:
        The corresponding XseType.

    Raises:
        ValueError: If the type name is invalid.

    Example:
        >>> xse = parse_xse_type("f4se")
        >>> assert xse.as_str() == "F4SE"
        >>> xse = parse_xse_type("SKSE64")
        >>> assert xse.as_str() == "SKSE64"

    """

def detect_xse_version(loader_path: str, xse_type: XseType) -> Version:
    """Detect XSE version from a loader executable.

    Args:
        loader_path: Path to the XSE loader executable.
        xse_type: The XSE type to detect.

    Returns:
        The detected version as a tuple of (major, minor, patch).

    Raises:
        IOError: If the loader doesn't exist or version cannot be detected.

    Example:
        >>> try:
        ...     version = detect_xse_version("f4se_loader.exe", XseType.f4se())
        ...     print(f"F4SE version: {version}")
        ... except IOError as e:
        ...     print(f"Detection failed: {e}")

    """

def is_xse_installed(game_path: str, xse_type: XseType) -> bool:
    r"""Check if XSE is installed in a directory.

    Args:
        game_path: The game installation directory.
        xse_type: The XSE type to check.

    Returns:
        True if the XSE loader executable exists.

    Example:
        >>> if is_xse_installed("C:\\Games\\Fallout4", XseType.f4se()):
        ...     print("F4SE is installed")

    """

def get_xse_info(game_path: str, xse_type: XseType) -> XseInfo:
    r"""Get XSE information for a game directory.

    Args:
        game_path: The game installation directory.
        xse_type: The XSE type to check.

    Returns:
        XseInfo with installation and version details.

    Example:
        >>> info = get_xse_info("C:\\Games\\Fallout4", XseType.f4se())
        >>> if info.installed():
        ...     print(f"F4SE version: {info.version()}")

    """
