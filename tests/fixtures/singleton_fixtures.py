"""Centralized singleton reset for test isolation.

This module provides the implementation for resetting all singleton state
between tests. It is consumed by the autouse fixture in conftest.py.

All known singletons, caches, and module-level state are reset after each
test to prevent state leakage between tests.
"""

import logging
import os
from typing import Generator

logger = logging.getLogger(__name__)


def reset_all_singletons_impl() -> Generator[None, None, None]:
    """Reset all singleton and cached global state after each test.

    Yields control to the test, then resets all known singletons,
    caches, and module-level state on teardown.
    """
    yield

    # Post-test teardown -- reset all state
    # Only proceed if in test context
    if "PYTEST_CURRENT_TEST" not in os.environ:
        return

    # 1. Singletons with reset_instance()
    _reset_class_singletons()

    # 2. Module-level singletons without reset_instance()
    _reset_module_singletons()

    # 3. Lazy-import caches
    _reset_lazy_import_caches()

    # 4. lru_cache functions
    _reset_lru_caches()


def _reset_class_singletons() -> None:
    """Reset singletons that have reset_instance() classmethods."""
    # RustAcceleration coordinator
    try:
        from ClassicLib.acceleration.coordinator import RustAcceleration

        RustAcceleration.reset_instance()
    except (ImportError, RuntimeError):
        pass

    # VersionRegistry
    try:
        from ClassicLib.support.versions.core import VersionRegistry

        VersionRegistry.reset_instance()
    except (ImportError, RuntimeError):
        pass

    # YamlSettingsCache
    try:
        from ClassicLib.io.yaml.sync.cache import YamlSettingsCache

        YamlSettingsCache.reset_instance()
    except (ImportError, RuntimeError):
        pass

    # DatabasePoolManager
    try:
        from ClassicLib.io.database.pool_manager import DatabasePoolManager

        DatabasePoolManager.reset_instance()
    except (ImportError, RuntimeError):
        pass


def _reset_module_singletons() -> None:
    """Reset module-level singleton globals.

    These are singletons managed via module-level variables with
    lazy initialization in getter functions. We reset them by
    setting the module-level variable back to None.
    """
    # MessageHandler
    try:
        import ClassicLib.messaging.handler as handler_mod

        with handler_mod._message_handler_lock:
            handler_mod._message_handler = None
    except (ImportError, AttributeError):
        pass

    # GameIntegrityOrchestratorCore
    try:
        import ClassicLib.scanning.game.orchestrator as orch_mod

        orch_mod._game_integrity_orchestrator_core = None
    except (ImportError, AttributeError):
        pass

    # GameFilesManagerCore
    try:
        import ClassicLib.scanning.game.game_files_manager as gfm_mod

        gfm_mod._game_files_manager_core = None
    except (ImportError, AttributeError):
        pass

    # AsyncYamlSettingsCore
    try:
        import ClassicLib.io.yaml.async_.core as async_yaml_mod

        async_yaml_mod._async_yaml_core = None
        async_yaml_mod._core_lock = None
    except (ImportError, AttributeError):
        pass

    # FileIO factory singleton and factory cache
    try:
        from ClassicLib.integration.factory import reset_cache

        reset_cache()
    except (ImportError, AttributeError):
        pass

    # ThreadManager (GUI-only, but reset for completeness)
    try:
        import ClassicLib.Interface.workers.ThreadManager as tm_mod

        tm_mod._thread_manager = None
    except (ImportError, AttributeError):
        pass

    # Emoji pattern cache
    try:
        import ClassicLib.messaging.formatting.formatter as fmt_mod

        fmt_mod._EMOJI_PATTERN = None
    except (ImportError, AttributeError):
        pass

    # Address library info cache
    try:
        import ClassicLib.scanning.game.check_xse_plugins as xse_mod

        xse_mod._ALL_ADDRESS_LIB_INFO_CACHE = None
    except (ImportError, AttributeError):
        pass

    # GlobalRegistry (has its own clear function)
    try:
        from ClassicLib.core.registry import clear as registry_clear

        registry_clear()
    except (ImportError, RuntimeError):
        pass


def _reset_lazy_import_caches() -> None:
    """Reset lazy-import class caches in integration/rust/report/.

    These cache class references from lazy imports of Rust modules.
    """
    # Report fragment caches (multiple modules cache _PyReportFragment)
    for mod_path in [
        "ClassicLib.integration.rust.report.parallel",
        "ClassicLib.integration.rust.report.generator",
        "ClassicLib.integration.rust.report.fragment",
        "ClassicLib.integration.rust.report.composer",
    ]:
        try:
            import importlib

            mod = importlib.import_module(mod_path)
            if hasattr(mod, "_PyReportFragment"):
                mod._PyReportFragment = None
        except (ImportError, AttributeError):
            pass

    # Report generator and composer class caches
    try:
        import importlib

        gen_mod = importlib.import_module("ClassicLib.integration.rust.report.generator")
        if hasattr(gen_mod, "_PyReportGenerator"):
            gen_mod._PyReportGenerator = None
    except (ImportError, AttributeError):
        pass

    try:
        import importlib

        comp_mod = importlib.import_module("ClassicLib.integration.rust.report.composer")
        if hasattr(comp_mod, "_PyReportComposer"):
            comp_mod._PyReportComposer = None
    except (ImportError, AttributeError):
        pass

    # Version tooltip and game version options (GUI lazy caches)
    try:
        import ClassicLib.Interface.Settings.tab_creators as tc_mod

        tc_mod._VERSION_TOOLTIP = ""
        tc_mod.GAME_VERSION_OPTIONS = []
    except (ImportError, AttributeError):
        pass


def _reset_lru_caches() -> None:
    """Clear lru_cache functions that cache one-shot results."""
    # _log_version_warning in game_path.py
    try:
        from ClassicLib.support.game_path import _log_version_warning

        _log_version_warning.cache_clear()
    except (ImportError, AttributeError):
        pass
