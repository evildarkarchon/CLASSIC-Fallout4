"""Registry fixtures for singleton management in tests.

This module provides standardized fixtures for managing singleton state
in tests, ensuring proper isolation and preventing test pollution.
Covers GlobalRegistry, MessageHandler, and AsyncBridge singletons.
"""

import gc
import threading
from collections.abc import Generator
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.Logger import logger
from ClassicLib.MessageHandler import MessageHandler, init_message_handler
from ClassicLib.YamlSettings import YamlSettingsCache

# Thread-local storage for singleton state tracking
_handler_lock = threading.Lock()
_handler_states = threading.local()
_bridge_lock = threading.Lock()
_bridge_states = threading.local()


@pytest.fixture
def init_message_handler_fixture() -> Generator[MessageHandler, None, None]:
    """Initialize the MessageHandler for non-GUI tests.

    This fixture ensures proper cleanup of the MessageHandler singleton
    between tests to prevent state leakage. Thread-safe for parallel testing.

    Returns:
        MessageHandler instance configured for non-GUI mode.

    Usage:
        def test_something(init_message_handler_fixture):
            # MessageHandler is automatically initialized and cleaned up
            from ClassicLib.MessageHandler import msg_info
            msg_info("Test message")
    """
    import ClassicLib.MessageHandler

    with _handler_lock:
        # Store any existing handler (for nested fixtures)
        old_handler = getattr(ClassicLib.MessageHandler, "_message_handler", None)

        # Track if this thread already has a handler to prevent double initialization
        if not hasattr(_handler_states, "handler_stack"):
            _handler_states.handler_stack = []

        _handler_states.handler_stack.append(old_handler)

        try:
            # Initialize fresh handler for this test
            handler = init_message_handler(parent=None, is_gui_mode=False)
            yield handler
        finally:
            # Restore previous state or clean up completely
            if _handler_states.handler_stack:
                previous = _handler_states.handler_stack.pop()
                ClassicLib.MessageHandler._message_handler = previous  # type: ignore
            else:
                ClassicLib.MessageHandler._message_handler = None  # type: ignore

            # Clear any cached references
            if hasattr(ClassicLib.MessageHandler, "_cached_handler"):
                delattr(ClassicLib.MessageHandler, "_cached_handler")

            # Force garbage collection to ensure cleanup
            gc.collect()


@pytest.fixture
def message_handler(init_message_handler_fixture: MessageHandler) -> MessageHandler:
    """Alias for init_message_handler_fixture for more intuitive naming.

    This is the preferred fixture name for new tests.
    """
    return init_message_handler_fixture


@pytest.fixture(autouse=True)
def ensure_message_handler_cleanup() -> Generator[None, None, None]:
    """Automatically ensure MessageHandler is cleaned up after each test.

    This autouse fixture runs for ALL tests and ensures that any MessageHandler
    state is properly cleaned up, even if tests don't use the fixtures properly.
    This prevents test pollution from tests that might initialize MessageHandler
    directly without proper cleanup.
    """
    yield

    # Post-test cleanup - only if MessageHandler module was used
    try:
        import ClassicLib.MessageHandler

        # Check if the module has the singleton attribute
        handler = getattr(ClassicLib.MessageHandler, "_message_handler", None)
        # Only clean up if not managed by another fixture
        if handler is not None and (not hasattr(_handler_states, "handler_stack") or not _handler_states.handler_stack):
            ClassicLib.MessageHandler._message_handler = None  # type: ignore

            # Clear cached references
            if hasattr(ClassicLib.MessageHandler, "_cached_handler"):
                delattr(ClassicLib.MessageHandler, "_cached_handler")
    except (ImportError, AttributeError):
        # Module not imported or attribute doesn't exist - nothing to clean
        pass


# ============================================================================
# AsyncBridge Fixtures
# ============================================================================


@pytest.fixture
def async_bridge() -> Generator[Any, None, None]:
    """Provide a clean AsyncBridge instance for testing.

    This fixture ensures AsyncBridge is properly isolated between tests,
    preventing event loop and thread pollution in parallel testing.

    Returns:
        AsyncBridge instance for the current test.

    Usage:
        def test_async_operations(async_bridge):
            result = async_bridge.run_async(some_async_function())
            assert result == expected
    """
    from ClassicLib.AsyncBridge import AsyncBridge

    with _bridge_lock:
        # Store current thread's instance if it exists
        thread_id = threading.get_ident()
        original_instance = AsyncBridge._instances.get(thread_id)

        # Track bridge state
        if not hasattr(_bridge_states, "instance_stack"):
            _bridge_states.instance_stack = []

        _bridge_states.instance_stack.append(original_instance)

        try:
            # Get or create instance for this test
            bridge = AsyncBridge.get_instance()
            yield bridge
        finally:
            # Clean up the bridge instance
            if thread_id in AsyncBridge._instances:
                current = AsyncBridge._instances[thread_id]
                # Shutdown the current instance
                current.shutdown()

            # Restore or remove instance
            if _bridge_states.instance_stack:
                previous = _bridge_states.instance_stack.pop()
                if previous is not None:
                    AsyncBridge._instances[thread_id] = previous
                else:
                    # Remove from instances dict
                    AsyncBridge._instances.pop(thread_id, None)
            else:
                AsyncBridge._instances.pop(thread_id, None)

            # Force garbage collection
            gc.collect()


def _cleanup_lingering_threads() -> None:
    """Cleanup any lingering AsyncBridge threads."""

    from ClassicLib.AsyncBridge import AsyncBridge

    # Call _cleanup_all to ensure all instances are shutdown

    AsyncBridge._cleanup_all()

    # Clear the instances dict

    with AsyncBridge._lock:
        AsyncBridge._instances.clear()

    # Collect AsyncBridge threads that need cleanup
    # Try to join threads with a bit more patience
    for _ in range(3):
        async_bridge_threads = [
            t for t in threading.enumerate() if (t.name.startswith("AsyncBridge-") or t.name.startswith("asyncio_")) and t.is_alive()
        ]

        if not async_bridge_threads:
            break

        for thread in async_bridge_threads:
            if thread.is_alive():
                thread.join(timeout=0.5)

    # Final check for lingering threads
    final_threads = [
        t for t in threading.enumerate() if (t.name.startswith("AsyncBridge-") or t.name.startswith("asyncio_")) and t.is_alive()
    ]

    for thread in final_threads:
        logger.debug(f"AsyncBridge thread {thread.name} lingering after cleanup.")


@pytest.fixture(autouse=True)
def ensure_async_bridge_cleanup() -> Generator[None, None, None]:
    """Automatically ensure AsyncBridge is cleaned up after each test.
    This autouse fixture runs for ALL tests and ensures that any AsyncBridge
    instances are properly cleaned up, preventing event loop leakage between tests.
    Only performs expensive thread cleanup (including waiting for thread termination)
    when AsyncBridge was actually used in the test, keeping test suite fast.
    """

    yield

    # Post-test cleanup - only if AsyncBridge was imported

    try:
        from ClassicLib.AsyncBridge import AsyncBridge

        # Quick check: if no instances exist, skip expensive cleanup

        thread_id = threading.get_ident()

        has_instances = bool(AsyncBridge._instances)

        # Only clean up if not managed by another fixture

        if (not hasattr(_bridge_states, "instance_stack") or not _bridge_states.instance_stack) and thread_id in AsyncBridge._instances:
            instance = AsyncBridge._instances[thread_id]

            # Shutdown and remove

            instance.shutdown()

            AsyncBridge._instances.pop(thread_id, None)

        # Clean up any orphaned instances from other threads (e.g., from async tasks)

        current_thread_ids = {t.ident for t in threading.enumerate()}

        dead_threads = [tid for tid in AsyncBridge._instances if tid != thread_id and tid not in current_thread_ids]

        # Clean up dead thread instances

        for tid in dead_threads:
            if tid in AsyncBridge._instances:
                instance = AsyncBridge._instances[tid]

                instance.shutdown()

                AsyncBridge._instances.pop(tid, None)

        # Check thread-local instance and shut it down if it exists

        if hasattr(AsyncBridge._thread_local, "instance"):
            try:
                instance = AsyncBridge._thread_local.instance

                if instance is not None:
                    instance.shutdown()

            except Exception:  # noqa: BLE001
                pass

            # Clear thread-local storage

            if hasattr(AsyncBridge._thread_local, "__dict__"):
                AsyncBridge._thread_local.__dict__.clear()

        # Only do expensive thread cleanup if instances were actually used

        if has_instances:
            _cleanup_lingering_threads()

    except (ImportError, AttributeError):
        # Module not imported or doesn't exist - nothing to clean

        pass


@pytest.fixture
def mock_async_bridge(monkeypatch: pytest.MonkeyPatch) -> Generator[Any, None, None]:
    """Mock AsyncBridge for tests that don't need actual async execution.

    This fixture is useful for unit tests where you want to test code that
    uses AsyncBridge without actually running async code.

    Usage:
        def test_sync_wrapper(mock_async_bridge):
            mock_async_bridge.run_async.return_value = "mocked_result"
            result = some_function_using_bridge()
            assert result == "mocked_result"
    """
    from unittest.mock import MagicMock

    mock_bridge = MagicMock()
    mock_bridge.run_async = MagicMock(side_effect=lambda coro: coro)
    mock_bridge.run_async_with_timeout = MagicMock(side_effect=lambda coro, _timeout: coro)
    mock_bridge.shutdown = MagicMock()

    # Mock the get_instance method
    with monkeypatch.context() as m:
        m.setattr("ClassicLib.AsyncBridge.AsyncBridge.get_instance", lambda: mock_bridge)
        yield mock_bridge

        # Ensure cleanup
        mock_bridge.shutdown.assert_not_called()  # Can be checked in tests


# ============================================================================
# GlobalRegistry Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clean_global_registry() -> Generator[None, None, None]:
    """Automatically clear GlobalRegistry before and after each test.

    This ensures complete isolation of GlobalRegistry state between tests,
    preventing test pollution from registry modifications. This is critical
    for parallel test execution with pytest-xdist.

    Uses the public GlobalRegistry.clear() API which is designed for testing
    and includes safety checks to prevent accidental use in production.
    """
    # Clear before test using the public API
    GlobalRegistry.clear()
    yield
    # Clear after test using the public API
    GlobalRegistry.clear()


@pytest.fixture
def global_registry() -> Generator[ModuleType, None, None]:
    """Provide a clean GlobalRegistry instance for testing.

    This fixture ensures the registry is clean before use and properly
    cleaned up after the test completes.

    Uses the public GlobalRegistry.clear() API which is designed for testing
    and includes safety checks to prevent accidental use in production.

    Usage:
        def test_registry(global_registry):
            global_registry.register("key", "value")
            assert global_registry.get("key") == "value"
    """
    # Clear registry before test using the public API
    GlobalRegistry.clear()

    yield GlobalRegistry

    # Clear registry after test using the public API
    GlobalRegistry.clear()


@pytest.fixture(scope="session")
def mock_global_registry() -> Generator[ModuleType, None, None]:
    """Mock the GlobalRegistry to return test values for session-wide use.

    Note: Use with caution as this is session-scoped and may affect
    multiple tests. Prefer the function-scoped 'global_registry' fixture
    for better isolation.
    """
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

    Note: This fixture uses direct _registry access for session-scoped operations
    where copy() semantics are needed. The public clear() API is preferred for
    function-scoped fixtures.
    """
    # Store original registry state for restoration
    # Use direct access for copy semantics (needed for restoration)
    original_registry = dict(GlobalRegistry._registry)

    try:
        # Clear registry to start fresh using the public API
        GlobalRegistry.clear()

        # Initialize YAML cache (many components depend on this)
        # Check if yaml_cache already exists in the module to avoid re-initialization issues
        try:
            from ClassicLib.YamlSettings import yaml_cache

            # Re-register the existing instance
            GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, yaml_cache)
        except ImportError:
            # If import fails, create a new instance
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
        def mock_open_file(path: Path | str, encoding: str = "utf-8", errors: str = "ignore") -> Any:
            return Path(path).open(encoding=encoding, errors=errors)

        GlobalRegistry.register(GlobalRegistry.Keys.OPEN_FILE_FUNC, mock_open_file)

        # Set other common flags
        GlobalRegistry.register(GlobalRegistry.Keys.IS_PRERELEASE, False)

        yield

    finally:
        # Restore original registry state
        # Use direct access for update semantics (needed for restoration)
        GlobalRegistry._registry.clear()
        GlobalRegistry._registry.update(original_registry)


@pytest.fixture
def setup_global_registry() -> None:
    """
    Function-scoped fixture for tests that need a clean GlobalRegistry state.

    This wraps the session fixture but allows tests to have isolated registry state
    when needed. Most tests should use the session fixture via autouse.
    """
    # Ensure YAML cache is always registered for function-scoped tests
    # This is critical for parallel test execution where each worker needs initialization
    if not GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE):
        try:
            from ClassicLib.YamlSettings import yaml_cache

            GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, yaml_cache)
        except (ImportError, TypeError):
            # If we can't import or yaml_cache initialization failed, create a new one
            yaml_cache = YamlSettingsCache()
            GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, yaml_cache)


# Autouse fixture to ensure GlobalRegistry is always initialized for tests
@pytest.fixture(scope="session", autouse=True)
def _ensure_global_registry(_setup_global_registry_session: Any) -> None:
    """Ensure GlobalRegistry is initialized for all tests."""
    # This fixture is automatically used by all tests
    # It depends on setup_global_registry_session to do the actual work
    return


# ============================================================================
# YAML Cache Fixtures
# ============================================================================

# Thread-local storage for YAML cache state tracking
_yaml_cache_lock = threading.Lock()
_yaml_cache_states = threading.local()


@pytest.fixture
def clean_yaml_cache_singleton() -> Generator[Any, None, None]:
    """Provide a clean YamlSettingsCache singleton instance for testing.

    This fixture ensures YamlSettingsCache singleton is properly isolated between tests,
    similar to how AsyncBridge is handled. Critical for parallel testing.

    Returns:
        YamlSettingsCache instance for the current test.

    Usage:
        def test_yaml_operations(clean_yaml_cache_singleton):
            from ClassicLib.YamlSettings import yaml_settings
            result = yaml_settings(str, YAML.TEST, "test.key")
    """
    import importlib

    YamlSettingsCacheModule = importlib.import_module("ClassicLib.YamlSettings")
    from ClassicLib.YamlSettings import YamlSettingsCache

    with _yaml_cache_lock:
        # Store the original singleton instance if it exists
        original_instance = YamlSettingsCache._instance if hasattr(YamlSettingsCache, "_instance") else None
        original_module_cache = getattr(YamlSettingsCacheModule, "yaml_cache", None)

        # Track cache state
        if not hasattr(_yaml_cache_states, "instance_stack"):
            _yaml_cache_states.instance_stack = []

        _yaml_cache_states.instance_stack.append((original_instance, original_module_cache))

        cache = None
        try:
            # Clear the singleton to force fresh instance
            YamlSettingsCache._instance = None

            # Get or create new instance for this test
            cache = YamlSettingsCache.get_instance()
            YamlSettingsCacheModule.yaml_cache = cache  # type: ignore

            # Register in GlobalRegistry if needed
            if GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE):
                GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, cache)

            yield cache
        finally:
            # Clear any cached data in the instance
            if cache and hasattr(cache, "_async_core") and hasattr(cache._async_core, "cache"):
                assert cache._async_core.cache is not None  # pyright: ignore[reportOptionalMemberAccess]
                cache._async_core.cache.settings_cache.clear()  # pyright: ignore[reportOptionalMemberAccess]
                cache._async_core.cache.file_mod_times.clear()  # pyright: ignore[reportOptionalMemberAccess]
                if hasattr(cache._async_core.cache, "path_cache"):  # pyright: ignore[reportOptionalMemberAccess]
                    cache._async_core.cache.path_cache.clear()  # pyright: ignore[reportOptionalMemberAccess]

            # Restore or clear singleton
            if _yaml_cache_states.instance_stack:
                prev_instance, prev_module_cache = _yaml_cache_states.instance_stack.pop()
                YamlSettingsCache._instance = prev_instance
                if prev_module_cache is not None:
                    YamlSettingsCacheModule.yaml_cache = prev_module_cache  # type: ignore
                    if GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE):
                        GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, prev_module_cache)
            else:
                YamlSettingsCache._instance = None
                # Clear the internal global _yaml_cache to reset the proxy target
                if hasattr(YamlSettingsCacheModule, "_yaml_cache"):
                    YamlSettingsCacheModule._yaml_cache = None  # type: ignore

            # Force garbage collection
            gc.collect()


@pytest.fixture
def yaml_cache_fixture(tmp_path: Path) -> Generator[Any, None, None]:
    """Initialize a clean YAML cache instance for testing.

    This fixture provides a properly initialized YAML cache with test-safe
    configuration, preventing pollution between tests and avoiding actual
    file I/O to production YAML files.

    Returns:
        YamlSettingsCache instance configured for testing.

    Usage:
        def test_something(yaml_cache_fixture):
            # YAML cache is automatically initialized and cleaned up
            from ClassicLib.YamlSettings import yaml_settings
            result = yaml_settings(str, YAML.TEST, "test.key")
    """
    import importlib
    from unittest.mock import MagicMock, patch

    YamlSettingsCacheModule = importlib.import_module("ClassicLib.YamlSettings")

    # Save the original yaml_cache if it exists
    original_cache = getattr(YamlSettingsCacheModule, "yaml_cache", None)

    # Create a mock async core that doesn't need actual files
    mock_async_core = MagicMock()
    mock_async_core.file_ops.get_path_for_store = MagicMock(return_value=tmp_path / "test.yaml")
    mock_async_core.cache.settings_cache = {}
    mock_async_core.cache.file_mod_times = {}

    # Create a mock YamlSettingsCache that doesn't initialize AsyncBridge
    with patch("ClassicLib.YamlSettings.AsyncBridge") as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge

        # Make run_async return values directly (not coroutines)
        def run_async_side_effect(coro: Any) -> Any:
            # If it's already a value, return it
            if not hasattr(coro, "__await__"):
                return coro
            # Otherwise mock it as returning the mock_async_core
            return mock_async_core

        mock_bridge.run_async.side_effect = run_async_side_effect

        # Create a new cache instance
        from ClassicLib.YamlSettings import YamlSettingsCache

        test_cache = YamlSettingsCache()
        test_cache._async_core = mock_async_core

        # Mock the async_yaml_settings method to return test values
        def async_yaml_settings_side_effect(_type: Any, _yaml_store: Any, key_path: str, _new_value: Any = None) -> Any:
            # Return sensible defaults for common settings
            defaults = {
                "FCX Mode": False,
                "Game_Info.CRASHGEN_LogName": "Buffout 4",
                "Game_Info.XSE_Acronym": "F4SE",
            }
            return defaults.get(key_path)

        test_cache.async_yaml_settings = MagicMock(side_effect=async_yaml_settings_side_effect)

        # Replace the module-level yaml_cache
        YamlSettingsCacheModule.yaml_cache = test_cache  # type: ignore

        # Register in GlobalRegistry
        GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, test_cache)

        try:
            yield test_cache
        finally:
            # Restore original cache
            if original_cache is not None:
                YamlSettingsCacheModule.yaml_cache = original_cache  # type: ignore
                GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, original_cache)
            else:
                # Clean up if there was no original
                if hasattr(YamlSettingsCacheModule, "yaml_cache"):
                    delattr(YamlSettingsCacheModule, "yaml_cache")
                if GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE):
                    GlobalRegistry._registry.pop(GlobalRegistry.Keys.YAML_CACHE, None)


@pytest.fixture
def mock_yaml_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[Any, None, None]:
    """Mock yaml_settings function for tests that don't need actual YAML files.

    This fixture is useful for unit tests where you want to control what
    yaml_settings returns without actual file I/O.

    Usage:
        def test_something(mock_yaml_settings):
            mock_yaml_settings.return_value = "test_value"
            result = some_function_using_yaml_settings()
            assert result == "test_value"
    """
    mock = MagicMock()

    # Common default return values
    def yaml_side_effect(_type: Any, _yaml_store: Any, key_path: str, _new_value: Any = None) -> Any:
        # Provide sensible defaults for common settings
        defaults = {
            "Game_Info.CRASHGEN_LogName": "Buffout 4",
            "Game_Info.XSE_Acronym": "F4SE",
            "exclude_log_records": (),
            "exclude_log_files": [],
            "exclude_log_errors": [],
            "catch_log_errors": ["error", "warning", "critical"],
        }

        if key_path in defaults:
            return defaults[key_path]
        return mock.return_value

    mock.side_effect = yaml_side_effect

    # yaml_settings is a module-level function, not a class attribute
    # Use importlib to ensure we get the module, not the class (if shadowed)
    import importlib

    YamlSettingsCacheModule = importlib.import_module("ClassicLib.YamlSettings")

    with monkeypatch.context() as m:
        m.setattr(YamlSettingsCacheModule, "yaml_settings", mock)
        yield mock


@pytest.fixture(autouse=True)
def ensure_yaml_cache_cleanup() -> Generator[None, None, None]:
    """Automatically ensure YAML cache is cleaned up after each test.

    This autouse fixture runs for ALL tests and ensures that any YAML cache
    modifications are properly cleaned up, preventing test pollution.
    """
    yield

    # Post-test cleanup - clear any cached data if YamlSettingsCache was used
    try:
        import importlib

        YamlSettingsCacheModule = importlib.import_module("ClassicLib.YamlSettings")
        from ClassicLib.YamlSettings import YamlSettingsCache

        # Clear caches BEFORE clearing singleton reference
        # This ensures we access cache data while the instance is still valid
        cache = getattr(YamlSettingsCacheModule, "yaml_cache", None)

        # Flattened access to core_cache to reduce nesting
        async_core = getattr(cache, "_async_core", None) if cache is not None else None
        core_cache = getattr(async_core, "cache", None) if async_core is not None else None

        if core_cache is not None:
            # Clear internal caches if they exist
            try:
                for attr in ("settings_cache", "file_mod_times", "path_cache"):
                    if hasattr(core_cache, attr):
                        getattr(core_cache, attr).clear()
            except (AttributeError, TypeError):
                # Silently handle cases where cache was partially initialized
                pass

        # NOW clear the singleton reference (after cache cleanup)
        if hasattr(YamlSettingsCache, "_instance"):
            YamlSettingsCache._instance = None

        # Clear the internal global _yaml_cache to reset the proxy target
        if hasattr(YamlSettingsCacheModule, "_yaml_cache"):
            YamlSettingsCacheModule._yaml_cache = None  # type: ignore

    except (ImportError, AttributeError):
        # Module not imported or doesn't exist - nothing to clean
        pass
