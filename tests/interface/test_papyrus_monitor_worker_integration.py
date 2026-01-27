"""
Unit tests for PapyrusMonitorWorker with Rust-accelerated file I/O.

This test module verifies that:
1. PapyrusMonitorWorker uses Rust-accelerated file I/O via read_lines_sync
2. Continuous monitoring loop works correctly
3. Stats parsing and signal emissions work properly
4. Thread-safe stop mechanism works
5. Error handling works correctly
6. Rust acceleration detection and logging work
"""

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from PySide6.QtCore import QObject, QThread

# Test worker initialization


@pytest.mark.unit
def test_papyrus_monitor_worker_exists():
    """Test that PapyrusMonitorWorker can be imported."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    assert PapyrusMonitorWorker is not None, "PapyrusMonitorWorker should be importable"
    assert hasattr(PapyrusMonitorWorker, "run"), "Should have run method"
    assert hasattr(PapyrusMonitorWorker, "stop"), "Should have stop method"
    assert hasattr(PapyrusMonitorWorker, "statsUpdated"), "Should have statsUpdated signal"
    assert hasattr(PapyrusMonitorWorker, "error"), "Should have error signal"


@pytest.mark.unit
def test_worker_signals():
    """Test that worker has all required signals."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    worker = PapyrusMonitorWorker()

    # Verify signals exist
    assert hasattr(worker, "statsUpdated"), "Should have statsUpdated signal"
    assert hasattr(worker, "error"), "Should have error signal"


@pytest.mark.unit
def test_worker_initialization():
    """Test that worker initializes with correct default state."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    worker = PapyrusMonitorWorker()

    # Verify initial state
    assert worker._should_run is True, "Should start with _should_run = True"
    assert worker._last_stats is None, "Should start with no last stats"
    assert worker.error_sound_played is False, "Should start with error_sound_played = False"
    assert worker._should_run_mutex is not None, "Should have mutex for thread safety"


# Test Rust acceleration detection


@pytest.mark.unit
@pytest.mark.rust
def test_rust_acceleration_detection():
    """Test that Rust file I/O acceleration is detected."""
    from ClassicLib.integration.status import is_rust_accelerated

    # Check if Rust is available
    rust_available = is_rust_accelerated("file_io")

    # Verify it returns a boolean
    assert isinstance(rust_available, bool), "Should return a boolean"

    @pytest.mark.unit
    def test_rust_status_logging():
        """Test that Streaming I/O status is logged."""
        from ClassicLib.core.logger import logger
        from ClassicLib.support.papyrus import papyrus_logging

        # Mock dependencies
        with (
            patch("ClassicLib.support.papyrus.yaml_settings") as mock_settings,
            patch("ClassicLib.support.papyrus.stream_lines_sync") as mock_stream,
        ):
            mock_settings.return_value = Path("test.log")
            mock_stream.return_value = iter(["line1", "line2"])

            # Ensure status hasn't been logged yet
            if hasattr(papyrus_logging, "_logged_status"):
                delattr(papyrus_logging, "_logged_status")

            # Spy on logger
            with patch.object(logger, "debug") as mock_debug:
                papyrus_logging()

                # Verify it logged the status
                mock_debug.assert_any_call("Papyrus log reading using Streaming I/O (Memory Efficient)")

            # Verify it sets the flag
            assert getattr(papyrus_logging, "_logged_status") is True

    # Test papyrus_logging function with Rust file I/O

    @pytest.mark.unit
    def test_papyrus_logging_uses_streaming_io():
        """Test that papyrus_logging uses stream_lines_sync for memory efficiency."""
        from ClassicLib.support.papyrus import papyrus_logging

        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True

        # Mock log data
        mock_log_data = [
            "Dumping Stacks\n",
            "Dumping Stack\n",
            "Dumping Stack\n",
            " warning: Something\n",
            " error: Something else\n",
        ]

        # Mock dependencies
        with (
            patch("ClassicLib.support.papyrus.yaml_settings") as mock_settings,
            patch("ClassicLib.support.papyrus.stream_lines_sync") as mock_stream,
        ):
            mock_settings.return_value = mock_path
            # stream_lines_sync returns an iterator
            mock_stream.return_value = iter(mock_log_data)

            # Reset logging flag
            if hasattr(papyrus_logging, "_logged_status"):
                delattr(papyrus_logging, "_logged_status")

            message, count = papyrus_logging()

            # Verify stream_lines_sync was called
            mock_stream.assert_called_once_with(mock_path)

            # Verify logic
            assert count == 1  # 1 "Dumping Stacks"
            assert "NUMBER OF DUMPS    : 1" in message
            assert "NUMBER OF STACKS   : 2" in message
            assert "NUMBER OF WARNINGS : 1" in message
            assert "NUMBER OF ERRORS   : 1" in message


@pytest.mark.unit
def test_papyrus_logging_handles_missing_file():
    """Test that papyrus_logging handles missing log file gracefully."""
    from ClassicLib.support.papyrus import papyrus_logging

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = False

    with patch("ClassicLib.support.papyrus.yaml_settings") as mock_settings:
        mock_settings.return_value = mock_path

        # Clear the logged flag if it exists
        if hasattr(papyrus_logging, "_logged_status"):
            delattr(papyrus_logging, "_logged_status")

        message, count = papyrus_logging()

        # Verify error message
        assert "[!] ERROR : UNABLE TO FIND *Papyrus.0.log*" in message
        assert count == 0


@pytest.mark.unit
def test_papyrus_logging_handles_none_path():
    """Test that papyrus_logging handles None path gracefully."""
    from ClassicLib.support.papyrus import papyrus_logging

    with patch("ClassicLib.support.papyrus.yaml_settings") as mock_settings:
        mock_settings.return_value = None

        # Clear the logged flag if it exists
        if hasattr(papyrus_logging, "_logged_status"):
            delattr(papyrus_logging, "_logged_status")

        message, count = papyrus_logging()

        # Verify error message
        assert "[!] ERROR : UNABLE TO FIND *Papyrus.0.log*" in message
        assert count == 0


# Test stats parsing


@pytest.mark.unit
def test_parse_stats():
    """Test that _parse_stats correctly parses log message."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    message = """NUMBER OF DUMPS    : 5
NUMBER OF STACKS   : 10
DUMPS/STACKS RATIO : 0.5
NUMBER OF WARNINGS : 3
NUMBER OF ERRORS   : 2
"""

    stats = PapyrusMonitorWorker._parse_stats(message, 5)

    # Verify stats
    assert stats.dumps == 5, "Should parse dumps correctly"
    assert stats.stacks == 10, "Should parse stacks correctly"
    assert stats.warnings == 3, "Should parse warnings correctly"
    assert stats.errors == 2, "Should parse errors correctly"
    assert stats.ratio == 0.5, "Should calculate ratio correctly"
    assert isinstance(stats.timestamp, datetime), "Should have timestamp"


@pytest.mark.unit
def test_parse_stats_zero_dumps():
    """Test that _parse_stats handles zero dumps correctly."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    message = "NUMBER OF STACKS   : 0\n"

    stats = PapyrusMonitorWorker._parse_stats(message, 0)

    # Verify ratio calculation for zero dumps
    assert stats.dumps == 0, "Should have zero dumps"
    assert stats.ratio == 0.0, "Should have zero ratio when dumps = 0"


# Test monitoring loop


@pytest.mark.unit
def test_monitoring_loop_emits_stats_signal():
    """Test that monitoring loop emits statsUpdated signal."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    worker = PapyrusMonitorWorker()

    # Track signal emissions
    stats_emitted = []
    worker.statsUpdated.connect(lambda s: stats_emitted.append(s))

    mock_message = "NUMBER OF DUMPS    : 1\nNUMBER OF STACKS   : 2\n"

    # Mock papyrus_logging to return data once, then trigger stop
    call_count = [0]

    def mock_logging():
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_message, 1
        # Stop after first iteration
        worker.stop()
        return mock_message, 1

    with patch("ClassicLib.Interface.widgets.Papyrus.papyrus_logging", side_effect=mock_logging), patch.object(QThread, "msleep"):
        worker.run()

    # Verify signal was emitted
    assert len(stats_emitted) >= 1, "Should emit statsUpdated signal at least once"
    assert stats_emitted[0].dumps == 1, "Should emit correct stats"


@pytest.mark.unit
def test_monitoring_loop_does_not_emit_duplicate_stats():
    """Test that monitoring loop doesn't emit signal for unchanged stats."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    worker = PapyrusMonitorWorker()

    # Track signal emissions
    stats_emitted = []
    worker.statsUpdated.connect(lambda s: stats_emitted.append(s))

    mock_message = "NUMBER OF DUMPS    : 1\nNUMBER OF STACKS   : 2\n"

    # Mock papyrus_logging to return same data multiple times
    call_count = [0]

    def mock_logging():
        call_count[0] += 1
        if call_count[0] >= 3:
            worker.stop()
        return mock_message, 1

    with patch("ClassicLib.Interface.widgets.Papyrus.papyrus_logging", side_effect=mock_logging), patch.object(QThread, "msleep"):
        worker.run()

    # Verify signal was only emitted once (stats didn't change)
    assert len(stats_emitted) == 1, "Should only emit once when stats don't change"


@pytest.mark.unit
def test_monitoring_loop_emits_error_signal():
    """Test that monitoring loop emits error signal on exception."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    worker = PapyrusMonitorWorker()

    # Track signal emissions
    errors_emitted = []
    worker.error.connect(lambda e: errors_emitted.append(e))

    # Mock papyrus_logging to raise an error
    with (
        patch("ClassicLib.Interface.widgets.Papyrus.papyrus_logging", side_effect=ValueError("Test error")),
        patch.object(QThread, "msleep"),
    ):
        worker.run()

    # Verify error signal was emitted
    assert len(errors_emitted) == 1, "Should emit error signal"
    assert "Test error" in errors_emitted[0], "Should emit correct error message"


# Test stop mechanism


@pytest.mark.unit
def test_stop_mechanism():
    """Test that stop() safely stops the monitoring loop."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    worker = PapyrusMonitorWorker()

    # Verify initial state
    assert worker._should_run is True, "Should start running"

    # Stop the worker
    worker.stop()

    # Verify state changed
    assert worker._should_run is False, "Should stop running"


@pytest.mark.unit
def test_stop_is_thread_safe():
    """Test that stop() is thread-safe (uses mutex)."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    worker = PapyrusMonitorWorker()

    # Call stop multiple times (simulating concurrent access)
    worker.stop()
    worker.stop()
    worker.stop()

    # Should not raise any exceptions and should be stopped
    assert worker._should_run is False, "Should be stopped"


# Test thread safety


@pytest.mark.unit
def test_worker_is_qobject():
    """Test that worker is a QObject and can be moved to thread."""
    from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker

    worker = PapyrusMonitorWorker()

    # Should be a QObject
    assert isinstance(worker, QObject), "Worker should be a QObject"

    # Should be movable to thread (basic check)
    thread = QThread()
    worker.moveToThread(thread)

    # Cleanup
    thread.quit()
    thread.wait()


# Test PapyrusStats dataclass


@pytest.mark.unit
def test_papyrus_stats_equality():
    """Test that PapyrusStats equality works correctly."""
    from datetime import datetime

    from ClassicLib.Interface.widgets.Papyrus import PapyrusStats

    stats1 = PapyrusStats(
        timestamp=datetime.now(),
        dumps=1,
        stacks=2,
        warnings=3,
        errors=4,
        ratio=0.5,
    )

    stats2 = PapyrusStats(
        timestamp=datetime.now(),  # Different timestamp
        dumps=1,
        stacks=2,
        warnings=3,
        errors=4,
        ratio=0.5,
    )

    stats3 = PapyrusStats(
        timestamp=datetime.now(),
        dumps=2,  # Different dumps
        stacks=2,
        warnings=3,
        errors=4,
        ratio=1.0,
    )

    # Same stats (ignoring timestamp) should be equal
    assert stats1 == stats2, "Should be equal when dumps/stacks/warnings/errors match"

    # Different stats should not be equal
    assert stats1 != stats3, "Should not be equal when stats differ"


@pytest.mark.unit
def test_papyrus_stats_hash():
    """Test that PapyrusStats hashing works correctly."""
    from datetime import datetime

    from ClassicLib.Interface.widgets.Papyrus import PapyrusStats

    stats1 = PapyrusStats(
        timestamp=datetime.now(),
        dumps=1,
        stacks=2,
        warnings=3,
        errors=4,
        ratio=0.5,
    )

    stats2 = PapyrusStats(
        timestamp=datetime.now(),  # Different timestamp
        dumps=1,
        stacks=2,
        warnings=3,
        errors=4,
        ratio=0.5,
    )

    # Same stats should have same hash
    assert hash(stats1) == hash(stats2), "Should have same hash when stats match"

    # Should be usable in sets
    stats_set = {stats1, stats2}
    assert len(stats_set) == 1, "Should only have one unique entry in set"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
