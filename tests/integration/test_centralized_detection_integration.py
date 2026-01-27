"""Tests for Phase 3 technical debt improvements.

Tests centralized detection and runtime diagnostics.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.rust
def test_centralized_detection_basic():
    """Test basic component detection."""
    from ClassicLib.integration.detector import detect_component, is_component_available

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
def test_centralized_detection_caching():
    """Test that detection results are cached."""
    from ClassicLib.integration.detector import _detection_cache, detect_component

    # Clear cache
    _detection_cache.clear()

    # First call should populate cache
    detect_component("classic_yaml", "YamlOperations")
    assert "classic_yaml:YamlOperations" in _detection_cache

    # Second call should use cache
    cache_size_before = len(_detection_cache)
    detect_component("classic_yaml", "YamlOperations")
    cache_size_after = len(_detection_cache)

    assert cache_size_before == cache_size_after


@pytest.mark.integration
@pytest.mark.rust
def test_get_component_success():
    """Test get_component for existing component."""
    from ClassicLib.integration.detector import get_component

    component = get_component("classic_yaml", "YamlOperations")
    assert component is not None

    # Verify it's the actual class
    assert callable(component)


@pytest.mark.integration
@pytest.mark.rust
def test_get_component_failure():
    """Test get_component raises for missing component."""
    from ClassicLib.integration.detector import get_component

    with pytest.raises(ImportError, match="Rust component.*not available"):
        get_component("nonexistent_module", "FakeClass")


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
    # Import all wrapper modules and check they work
    from ClassicLib.integration.rust.fcx_rust import RUST_AVAILABLE as fcx_avail
    from ClassicLib.integration.rust.file_io_rust import RUST_AVAILABLE as file_io_avail
    from ClassicLib.integration.rust.gpu_rust import RUST_AVAILABLE as gpu_avail
    from ClassicLib.integration.rust.mod_detector_rust import RUST_AVAILABLE as mod_avail
    from ClassicLib.integration.rust.orchestrator_api import RUST_AVAILABLE as orch_avail
    from ClassicLib.integration.rust.parser_rust import RustLogParser
    from ClassicLib.integration.rust.report_rust import RUST_AVAILABLE as report_avail
    from ClassicLib.integration.rust.settings_rust import RUST_AVAILABLE as settings_avail
    from ClassicLib.integration.rust.suspect_rust import RUST_AVAILABLE as suspect_avail
    from ClassicLib.io.database.rust_pool import RUST_AVAILABLE as database_avail

    # All should be True in test environment with Rust built
    assert file_io_avail is True
    assert settings_avail is True
    assert database_avail is True
    assert gpu_avail is True
    assert fcx_avail is True
    assert mod_avail is True
    assert report_avail is True
    assert suspect_avail is True
    assert orch_avail is True

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
    from ClassicLib.integration.detector import detect_component

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
