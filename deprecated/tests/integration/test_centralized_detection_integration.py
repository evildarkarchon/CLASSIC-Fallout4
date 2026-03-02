"""Tests for Phase 3 technical debt improvements.

Tests centralized detection and runtime diagnostics.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.rust
def test_centralized_detection_basic():
    """Test basic component detection."""
    from ClassicLib.integration.factory import detect_component, is_component_available

    # Test successful detection
    available, component = detect_component("classic_yaml", "YamlOperations")
    assert available is True
    assert component is not None

    # Test convenience method
    assert is_component_available("classic_yaml", "YamlOperations") is True

    # Test non-existent component
    available, component = detect_component("nonexistent_module", "FakeClass")
    assert available is False
    assert component is None


@pytest.mark.integration
@pytest.mark.rust
def test_centralized_detection_repeated_calls():
    """Test that repeated detection calls work (sys.modules caches imports)."""
    from ClassicLib.integration.factory import detect_component

    # First call
    avail1, comp1 = detect_component("classic_yaml", "YamlOperations")
    # Second call should return same result (Python's import system caches)
    avail2, comp2 = detect_component("classic_yaml", "YamlOperations")

    assert avail1 == avail2
    assert comp1 is comp2


@pytest.mark.integration
@pytest.mark.rust
def test_get_component_success():
    """Test get_component for existing component."""
    from ClassicLib.integration.factory import get_component

    component = get_component("classic_yaml", "YamlOperations")
    assert component is not None

    # Verify it's the actual class
    assert callable(component)


@pytest.mark.integration
@pytest.mark.rust
def test_get_component_failure():
    """Test get_component raises for missing component."""
    from ClassicLib.integration.exceptions import RustBindingImportError
    from ClassicLib.integration.factory import get_component

    with pytest.raises(RustBindingImportError, match="nonexistent_module.FakeClass"):
        get_component("nonexistent_module", "FakeClass")


@pytest.mark.integration
@pytest.mark.rust
def test_validate_rust_modules_reports_import_failures():
    """Startup contract validation should classify missing imports."""
    import builtins

    from ClassicLib.integration.exceptions import RustBindingImportError
    from ClassicLib.integration.factory import validate_rust_modules

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "classic_yaml":
            raise ImportError("No module named 'classic_yaml'")
        return original_import(name, *args, **kwargs)

    with pytest.raises(RustBindingImportError, match="classic_yaml.YamlOperations"):
        with pytest.MonkeyPatch.context() as patcher:
            patcher.setattr(builtins, "__import__", mock_import)
            validate_rust_modules("startup_all")


@pytest.mark.integration
@pytest.mark.rust
def test_validate_rust_modules_reports_init_failures():
    """Startup contract validation should classify invalid binding initialization."""
    import builtins
    import types

    from ClassicLib.integration.exceptions import RustBindingInitError
    from ClassicLib.integration.factory_internal.detection import validate_rust_modules

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "classic_yaml":
            module = types.SimpleNamespace(YamlOperations=None)
            return module
        return original_import(name, *args, **kwargs)

    with pytest.raises(RustBindingInitError, match="classic_yaml.YamlOperations"):
        with pytest.MonkeyPatch.context() as patcher:
            patcher.setattr(builtins, "__import__", mock_import)
            validate_rust_modules("startup_all")


@pytest.mark.integration
@pytest.mark.rust
def test_runtime_diagnostics():
    """Test runtime diagnostic functions."""
    from ClassicLib.integration.diagnostics import (
        get_runtime_stats,
        is_runtime_healthy,
    )

    # Test get_runtime_stats
    stats = get_runtime_stats()
    assert stats is not None
    assert "worker_threads" in stats
    assert "is_healthy" in stats
    assert isinstance(stats["worker_threads"], int)
    assert isinstance(stats["is_healthy"], bool)
    assert stats["worker_threads"] > 0  # Should have at least one thread

    # Test is_runtime_healthy
    healthy = is_runtime_healthy()
    assert isinstance(healthy, bool)
    assert healthy is True  # Should be healthy in tests


@pytest.mark.integration
@pytest.mark.rust
def test_runtime_diagnostics_print(capsys):
    """Test print_runtime_status output."""
    from ClassicLib.integration.diagnostics import print_runtime_status

    print_runtime_status()

    captured = capsys.readouterr()
    assert "Tokio Runtime Status" in captured.out
    assert "Worker Threads:" in captured.out
    assert "Health Status:" in captured.out


@pytest.mark.integration
@pytest.mark.rust
def test_wrapper_modules_use_centralized_detection():
    """Verify wrapper modules use centralized detection."""
    # Import remaining wrapper modules and check they work
    from ClassicLib.integration.factory import is_component_available
    from ClassicLib.integration.rust.file_io_rust import FileIOCore
    from ClassicLib.integration.rust.mod_detector_rust import is_rust_accelerated
    from ClassicLib.integration.rust.orchestrator_api import ClassicOrchestrator
    from ClassicLib.integration.rust.parser_rust import RustLogParser
    from ClassicLib.integration.rust.report_rust import ReportGenerator
    from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool

    # Wrappers should resolve to concrete Rust-backed implementations
    assert FileIOCore is not None
    assert RustAsyncDatabasePool is not None
    assert ReportGenerator is not None
    assert ClassicOrchestrator is not None
    assert is_rust_accelerated() is True

    # Test factory-based components (wrappers deleted, now use factory detection)
    assert is_component_available("classic_scanlog", "SuspectScanner") is True
    assert is_component_available("classic_scanlog", "SettingsValidator") is True
    assert is_component_available("classic_scanlog", "GpuDetector") is True
    assert is_component_available("classic_scanlog", "FcxModeHandler") is True

    # Test parser instance
    parser = RustLogParser()
    assert parser.is_rust_accelerated is True


@pytest.mark.integration
@pytest.mark.rust
def test_integration_exports():
    """Test that all Phase 3 functions are exported from integration module."""
    from ClassicLib.integration import (
        detect_component,
        get_component,
        get_runtime_stats,
        is_component_available,
        is_runtime_healthy,
        print_runtime_status,
    )

    # Just verify they're callable
    assert callable(detect_component)
    assert callable(is_component_available)
    assert callable(get_component)
    assert callable(get_runtime_stats)
    assert callable(is_runtime_healthy)
    assert callable(print_runtime_status)


@pytest.mark.integration
@pytest.mark.rust
def test_detection_with_module_only():
    """Test detection without class name (module-level)."""
    from ClassicLib.integration.factory import detect_component

    # Test module-only detection
    available, module = detect_component("classic_yaml")
    assert available is True
    assert module is not None


@pytest.mark.integration
@pytest.mark.rust
def test_runtime_stats_structure():
    """Test RuntimeStats structure from Rust."""
    try:
        import classic_shared

        stats = classic_shared.get_runtime_stats()

        # Verify it has the expected attributes
        assert hasattr(stats, "worker_threads")
        assert hasattr(stats, "is_healthy")

        # Verify __repr__ works
        repr_str = repr(stats)
        assert "RuntimeStats" in repr_str
        assert "worker_threads" in repr_str
        assert "is_healthy" in repr_str

    except ImportError:
        pytest.skip("classic_shared module not available")
