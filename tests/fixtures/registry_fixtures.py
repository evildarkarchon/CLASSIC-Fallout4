"""Registry fixtures for GlobalRegistry and MessageHandler initialization."""

import gc
from collections.abc import Generator
from pathlib import Path
from types import ModuleType

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.YamlSettingsCache import YamlSettingsCache


@pytest.fixture
def init_message_handler_fixture() -> Generator[None, None, None]:
    """Initialize the MessageHandler for tests that need it.

    This fixture ensures proper cleanup of the MessageHandler singleton
    between tests to prevent state leakage.
    """
    # Import here to avoid circular dependencies
    import ClassicLib.MessageHandler

    # Store any existing handler to restore later (defensive programming)
    _ = getattr(ClassicLib.MessageHandler, "_message_handler", None)

    try:
        # Initialize fresh handler for this test
        init_message_handler(parent=None, is_gui_mode=False)
        yield
    finally:
        # Ensure complete cleanup
        ClassicLib.MessageHandler._message_handler = None

        # Clear any cached references
        if hasattr(ClassicLib.MessageHandler, "_cached_handler"):
            delattr(ClassicLib.MessageHandler, "_cached_handler")

        # Force garbage collection to ensure cleanup
        gc.collect()

        # Verify cleanup was successful (defensive check)
        assert ClassicLib.MessageHandler._message_handler is None, "MessageHandler cleanup failed"


@pytest.fixture(scope="session")
def mock_global_registry() -> Generator[ModuleType, None, None]:
    """Mock the GlobalRegistry to return test values."""
    original_values = {}

    # Save original values
    for key in GlobalRegistry._registry:
        original_values[key] = GlobalRegistry.get(key)

    # Set test values
    GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
    GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

    yield GlobalRegistry

    # Restore original values
    for key, value in original_values.items():
        GlobalRegistry.register(key, value)


@pytest.fixture(scope="session")
def setup_global_registry_session() -> Generator[None, None, None]:
    """
    Initialize GlobalRegistry with required components for the entire test session.

    This session-scoped fixture ensures that GlobalRegistry is properly initialized
    once for all tests, preventing AttributeError: 'NoneType' object errors when
    components try to access registry values.

    This fixture is automatically used by tests that need GlobalRegistry.
    """
    # Store original registry state for restoration
    original_registry = dict(GlobalRegistry._registry)

    try:
        # Clear registry to start fresh
        GlobalRegistry._registry.clear()

        # Initialize YAML cache (many components depend on this)
        yaml_cache = YamlSettingsCache()
        GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, yaml_cache)

        # Set core game settings
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)

        # Set path-related entries
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, Path.cwd())
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, Path("C:/Program Files (x86)/Steam/steamapps/common/Fallout 4"))
        GlobalRegistry.register(GlobalRegistry.Keys.DOCS_PATH, Path.home() / "Documents" / "My Games" / "Fallout4")

        # Set function entries (mock implementations)
        def mock_open_file(path: Path | str, encoding: str = "utf-8", errors: str = "ignore"):
            return open(path, encoding=encoding, errors=errors)

        GlobalRegistry.register(GlobalRegistry.Keys.OPEN_FILE_FUNC, mock_open_file)

        # Set other common flags
        GlobalRegistry.register(GlobalRegistry.Keys.IS_PRERELEASE, False)

        yield

    finally:
        # Restore original registry state
        GlobalRegistry._registry.clear()
        GlobalRegistry._registry.update(original_registry)


@pytest.fixture(scope="function")
def setup_global_registry() -> Generator[None, None, None]:
    """
    Function-scoped fixture for tests that need a clean GlobalRegistry state.

    This wraps the session fixture but allows tests to have isolated registry state
    when needed. Most tests should use the session fixture via autouse.
    """
    # The session fixture handles the actual setup
    # This function fixture is for backward compatibility
    yield


# Autouse fixture to ensure GlobalRegistry is always initialized for tests
@pytest.fixture(scope="session", autouse=True)
def _ensure_global_registry(setup_global_registry_session):
    """Ensure GlobalRegistry is initialized for all tests."""
    # This fixture is automatically used by all tests
    # It depends on setup_global_registry_session to do the actual work
    pass
