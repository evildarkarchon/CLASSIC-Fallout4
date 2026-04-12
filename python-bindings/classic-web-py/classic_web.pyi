"""Type stubs for classic_web.

Python bindings for classic-web-core, providing comprehensive web utilities
including URL validation, user agent generation, and mod site constants.

Architecture:
    - classic-web-core: Business logic (URL handling, web constants)
    - classic-web-py: Python bindings (this module - PyO3 adapters)

Features:
    - URL validation and parsing
    - User agent string generation
    - Mod site enumeration with base URLs
    - URL building with query parameters

Usage:
    import classic_web

    # User agents
    ua = classic_web.get_user_agent()  # "CLASSIC/8.0.0"
    ua = classic_web.get_user_agent_with_suffix("NexusMods")

    # URL validation
    url = classic_web.validate_url("https://www.nexusmods.com")
    if classic_web.is_valid_url(url):
        domain = classic_web.extract_domain(url)

    # URL building
    url = classic_web.join_url("https://api.github.com", "repos/evildarkarchon/CLASSIC")
    url = classic_web.build_url_with_query(
        "https://www.nexusmods.com/fallout4/mods",
        [("game_id", "1151"), ("adult", "false")]
    )
"""

__version__: str

# Constants
CLASSIC_VERSION: str
USER_AGENT_PREFIX: str

class ModSite:
    """Mod site enumeration for Python.

    Each variant corresponds to a specific mod hosting site
    with its base URL and properties.
    """

    @staticmethod
    def nexus_mods() -> ModSite:
        """Create a NexusMods site."""

    @staticmethod
    def bethesda_net() -> ModSite:
        """Create a BethesdaNet site."""

    @staticmethod
    def mod_db() -> ModSite:
        """Create a ModDB site."""

    def name(self) -> str:
        """Get the mod site name as a string.

        Returns:
            The mod site name.

        Example:
            >>> site = ModSite.nexus_mods()
            >>> assert site.name() == "Nexus Mods"

        """

    def base_url(self) -> str:
        """Get the mod site base URL.

        Returns:
            The base URL for the mod site.

        Example:
            >>> site = ModSite.nexus_mods()
            >>> assert site.base_url() == "https://www.nexusmods.com"

        """

    def __eq__(self, other: object) -> bool:
        """Compare mod sites for equality."""

    def __str__(self) -> str:
        """Return the short variant name (e.g. ``"NexusMods"``)."""

    def __repr__(self) -> str:
        """Return a debug representation suitable for logs and REPL output."""

def get_user_agent() -> str:
    """Get the default user agent string for CLASSIC.

    Returns:
        A user agent string in the format "CLASSIC/8.0.0".

    Example:
        >>> ua = get_user_agent()
        >>> assert ua.startswith("CLASSIC/")

    """

def get_user_agent_with_suffix(suffix: str) -> str:
    """Get a user agent string with a custom suffix.

    Args:
        suffix: Additional information to append to the user agent.

    Returns:
        A user agent string with the suffix appended.

    Example:
        >>> ua = get_user_agent_with_suffix("NexusMods")
        >>> assert "NexusMods" in ua

    """

def validate_url(url_str: str) -> str:
    """Validate and parse a URL string.

    Args:
        url_str: The URL string to validate.

    Returns:
        The validated URL as a string.

    Raises:
        ValueError: If the URL is invalid.

    Example:
        >>> url = validate_url("https://www.nexusmods.com")
        >>> assert url == "https://www.nexusmods.com/"

    """

def is_valid_url(url_str: str) -> bool:
    """Check if a URL string is valid.

    Args:
        url_str: The URL string to check.

    Returns:
        True if the URL is valid, False otherwise.

    Example:
        >>> assert is_valid_url("https://www.nexusmods.com")
        >>> assert not is_valid_url("not a url")

    """

def extract_domain(url_str: str) -> str:
    """Extract the domain from a URL.

    Args:
        url_str: The URL string to extract from.

    Returns:
        The domain as a string.

    Raises:
        ValueError: If the URL is invalid or has no domain.

    Example:
        >>> domain = extract_domain("https://www.nexusmods.com/fallout4/mods/123")
        >>> assert domain == "www.nexusmods.com"

    """

def join_url(base: str, path: str) -> str:
    """Join a base URL with a path.

    Args:
        base: The base URL.
        path: The path to join.

    Returns:
        The joined URL as a string.

    Raises:
        ValueError: If the base URL is invalid or joining fails.

    Example:
        >>> url = join_url("https://www.nexusmods.com", "fallout4/mods")
        >>> assert url == "https://www.nexusmods.com/fallout4/mods"

    """

def build_url_with_query(base: str, params: list[tuple[str, str]]) -> str:
    """Build a URL with query parameters.

    Args:
        base: The base URL.
        params: List of tuples containing (key, value) pairs for query parameters.

    Returns:
        The URL with query parameters as a string.

    Raises:
        ValueError: If the base URL is invalid.

    Example:
        >>> url = build_url_with_query(
        ...     "https://www.nexusmods.com/fallout4/mods",
        ...     [("game_id", "1151"), ("adult", "false")]
        ... )
        >>> assert "game_id=1151" in url

    """
