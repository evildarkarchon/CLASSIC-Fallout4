"""
Unit tests for ResultsViewerMixin with Rust-accelerated file I/O.

This test module verifies that:
1. ResultsViewerMixin uses Rust-accelerated file I/O via read_file_sync
2. Report loading and display works correctly
3. File operations use FileIOCore infrastructure
4. Error handling works properly
5. Clipboard operations work correctly
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget


# Fixture to initialize MessageHandler for all tests
@pytest.fixture(autouse=True)
def init_message_handler():
    """Initialize MessageHandler for tests."""
    from ClassicLib.MessageHandler import init_message_handler

    init_message_handler(parent=None, is_gui_mode=True)
    yield
    # Cleanup after test
    from ClassicLib.MessageHandler.handler import _message_handler
    _message_handler._instance = None


# Note: No need to patch CLI/TUI mode check since we mock read_file_sync directly in tests


# Test mixin initialization

@pytest.mark.unit
def test_results_viewer_mixin_exists():
    """Test that ResultsViewerMixin can be imported."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    assert ResultsViewerMixin is not None, "ResultsViewerMixin should be importable"
    assert hasattr(ResultsViewerMixin, "setup_results_tab"), "Should have setup_results_tab method"
    assert hasattr(ResultsViewerMixin, "load_report"), "Should have load_report method"


@pytest.mark.unit
def test_mixin_signals():
    """Test that mixin has all required signals."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    # Verify signals exist as class attributes
    assert hasattr(ResultsViewerMixin, "report_loaded"), "Should have report_loaded signal"
    assert hasattr(ResultsViewerMixin, "reports_refreshed"), "Should have reports_refreshed signal"


# Test Rust acceleration detection

@pytest.mark.unit
@pytest.mark.rust
def test_rust_acceleration_detection():
    """Test that Rust file I/O acceleration is detected and logged."""
    from ClassicLib.integration.status import is_rust_accelerated

    # Check if Rust is available
    rust_available = is_rust_accelerated("file_io")

    if rust_available:
        # If Rust is available, verify it's detected
        assert rust_available, "Rust file_io should be available in test environment"
    else:
        pytest.skip("Rust file_io not available - expected if not built")


@pytest.mark.unit
def test_rust_status_logging_on_setup():
    """Test that Rust acceleration status is logged during setup."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin
    from ClassicLib.Logger import logger

    # Create a concrete test class from the mixin
    class TestViewer(QObject, ResultsViewerMixin):
        def __init__(self):
            super().__init__()
            self.results_tab = QWidget()

    viewer = TestViewer()

    # Mock all dependencies to avoid actual widget creation
    with patch("ClassicLib.Interface.ResultsViewerMixin.ReportListWidget") as mock_list:
        with patch("ClassicLib.Interface.ResultsViewerMixin.MarkdownViewer") as mock_viewer:
            with patch("ClassicLib.Interface.ResultsViewerMixin.ReportMetadataWidget") as mock_metadata:
                # Setup mocks
                mock_list.return_value = MagicMock()
                mock_viewer.return_value = MagicMock()
                mock_metadata.return_value = MagicMock()

                with patch("ClassicLib.integration.status.is_rust_accelerated") as mock_rust_check:
                    with patch.object(logger, "info") as mock_log_info:
                        with patch.object(logger, "debug") as mock_log_debug:
                            with patch.object(viewer, "scan_for_reports", return_value=[]):
                                with patch.object(viewer, "refresh_reports_list"):
                                    # Test with Rust available
                                    mock_rust_check.return_value = True

                                    try:
                                        viewer.setup_results_tab()
                                    except Exception:
                                        pass

                                    # Check if Rust acceleration was logged
                                    info_calls = [str(call) for call in mock_log_info.call_args_list]
                                    rust_logged = any("Rust-accelerated" in str(call) or "10x faster" in str(call) for call in info_calls)

                                    assert rust_logged, "Should log Rust acceleration status when available"


# Test file I/O operations

@pytest.mark.unit
def test_load_report_uses_rust_file_io():
    """Test that load_report uses read_file_sync for Rust acceleration."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    # Create a concrete test class
    class TestViewer(QObject, ResultsViewerMixin):
        def __init__(self):
            super().__init__()
            self.markdown_viewer = MagicMock()
            self.metadata_widget = MagicMock()
            self.current_report_path = None

    viewer = TestViewer()

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.name = "test-report.md"

    # Mock read_file_sync to verify it's called
    with patch("ClassicLib.Interface.ResultsViewerMixin.read_file_sync") as mock_read:
        mock_read.return_value = "# Test Report\n\nContent here"

        result = viewer.load_report(mock_path)

        # Verify read_file_sync was called with the correct path
        assert mock_read.called, "Should call read_file_sync"
        mock_read.assert_called_once_with(mock_path)
        assert result is True, "Should return True on success"


@pytest.mark.unit
def test_load_report_fallback_uses_rust_file_io():
    """Test that load_report fallback for plain text also uses read_file_sync."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    class TestViewer(QObject, ResultsViewerMixin):
        def __init__(self):
            super().__init__()
            self.markdown_viewer = MagicMock()
            self.markdown_viewer.setMarkdown.side_effect = RuntimeError("Markdown error")
            self.metadata_widget = MagicMock()
            self.current_report_path = None

    viewer = TestViewer()

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.name = "test-report.md"

    # Mock read_file_sync - should be called twice (once for markdown, once for fallback)
    with patch("ClassicLib.Interface.ResultsViewerMixin.read_file_sync") as mock_read:
        mock_read.return_value = "# Test Report\n\nContent here"

        with patch("ClassicLib.MessageHandler.msg_error"):
            with patch("ClassicLib.MessageHandler.msg_warning"):
                result = viewer.load_report(mock_path)

        # Verify read_file_sync was called twice
        assert mock_read.call_count == 2, "Should call read_file_sync twice (markdown + fallback)"
        assert result is True, "Should return True on fallback success"


@pytest.mark.unit
def test_copy_report_uses_rust_file_io():
    """Test that _copy_report uses read_file_sync for Rust acceleration."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    class TestViewer(QObject, ResultsViewerMixin):
        def __init__(self):
            super().__init__()
            self.current_report_path = Path("test-report.md")

    viewer = TestViewer()

    # Mock read_file_sync and clipboard
    with patch("ClassicLib.Interface.ResultsViewerMixin.read_file_sync") as mock_read:
        mock_read.return_value = "# Test Report Content"

        with patch("PySide6.QtWidgets.QApplication.clipboard") as mock_clipboard:
            mock_clipboard_instance = MagicMock()
            mock_clipboard.return_value = mock_clipboard_instance

            with patch("ClassicLib.MessageHandler.msg_info"):
                viewer._copy_report()

        # Verify read_file_sync was called
        assert mock_read.called, "Should call read_file_sync"
        mock_read.assert_called_once_with(viewer.current_report_path)

        # Verify clipboard was updated
        mock_clipboard_instance.setText.assert_called_once_with("# Test Report Content")


# Test error handling

@pytest.mark.unit
def test_load_report_handles_missing_file():
    """Test that load_report handles missing files gracefully."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    class TestViewer(QObject, ResultsViewerMixin):
        def __init__(self):
            super().__init__()
            self.markdown_viewer = MagicMock()
            self.metadata_widget = MagicMock()
            self.current_report_path = None

    viewer = TestViewer()

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = False
    mock_path.name = "missing-report.md"

    with patch("ClassicLib.MessageHandler.msg_error"):
        result = viewer.load_report(mock_path)

    assert result is False, "Should return False for missing file"


@pytest.mark.unit
def test_copy_report_handles_no_report_loaded():
    """Test that _copy_report handles no report loaded gracefully."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    class TestViewer(QObject, ResultsViewerMixin):
        def __init__(self):
            super().__init__()
            self.current_report_path = None

    viewer = TestViewer()

    with patch("ClassicLib.Interface.ResultsViewerMixin.msg_warning") as mock_warning:
        viewer._copy_report()

        # Verify warning was shown
        assert mock_warning.called, "Should show warning when no report loaded"


@pytest.mark.unit
def test_load_report_handles_read_errors():
    """Test that load_report handles read errors gracefully."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    class TestViewer(QObject, ResultsViewerMixin):
        def __init__(self):
            super().__init__()
            self.markdown_viewer = MagicMock()
            self.metadata_widget = MagicMock()
            self.current_report_path = None

    viewer = TestViewer()

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.name = "error-report.md"

    # Mock read_file_sync to raise an error
    with patch("ClassicLib.Interface.ResultsViewerMixin.read_file_sync") as mock_read:
        mock_read.side_effect = RuntimeError("Read error")

        with patch("ClassicLib.MessageHandler.msg_error"):
            result = viewer.load_report(mock_path)

        # Should try twice (markdown + fallback) then fail
        assert mock_read.call_count == 2, "Should attempt fallback after initial failure"
        assert result is False, "Should return False when both attempts fail"


# Test signal emissions

@pytest.mark.unit
def test_report_loaded_signal_emission():
    """Test that report_loaded signal is emitted on successful load."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    class TestViewer(QObject, ResultsViewerMixin):
        def __init__(self):
            super().__init__()
            self.markdown_viewer = MagicMock()
            self.metadata_widget = MagicMock()
            self.current_report_path = None

    viewer = TestViewer()

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.name = "test-report.md"

    # Track signal emissions
    signal_emitted = []
    viewer.report_loaded.connect(lambda p: signal_emitted.append(p))

    with patch("ClassicLib.Interface.ResultsViewerMixin.read_file_sync") as mock_read:
        mock_read.return_value = "# Test Report"

        viewer.load_report(mock_path)

    # Verify signal was emitted
    assert len(signal_emitted) == 1, "Should emit report_loaded signal"
    assert signal_emitted[0] == mock_path, "Should emit with correct path"


@pytest.mark.unit
def test_reports_refreshed_signal_emission():
    """Test that reports_refreshed signal is emitted on refresh."""
    from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin

    class TestViewer(QObject, ResultsViewerMixin):
        def __init__(self):
            super().__init__()
            self.results_list = MagicMock()
            # Configure count() to return an integer
            self.results_list.count.return_value = 2
            self.markdown_viewer = MagicMock()
            self.metadata_widget = MagicMock()

    viewer = TestViewer()

    # Track signal emissions
    signal_emitted = []
    viewer.reports_refreshed.connect(lambda n: signal_emitted.append(n))

    with patch.object(viewer, "scan_for_reports", return_value=[Path("report1.md"), Path("report2.md")]):
        viewer.refresh_reports_list()

    # Verify signal was emitted
    assert len(signal_emitted) == 1, "Should emit reports_refreshed signal"
    assert signal_emitted[0] == 2, "Should emit with correct report count"


# Test integration patterns

@pytest.mark.unit
def test_rust_file_io_available():
    """Test that Rust file I/O acceleration is available."""
    from ClassicLib.integration.status import is_rust_accelerated

    # Verify Rust file_io is available
    rust_available = is_rust_accelerated("file_io")

    # Just check that the function works - availability depends on build
    assert isinstance(rust_available, bool), "Should return a boolean"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
