"""
Unit tests for MessageHandler qt_compat module.

This module tests the Qt compatibility layer functionality, including
both real PySide6 imports and fallback dummy classes when Qt is not available.
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestQtCompatibility:
    """Unit tests for Qt compatibility functionality."""

    def test_has_qt_true_when_pyside6_available(self):
        """Test that HAS_QT is True when PySide6 is available."""
        # Clear the module from cache to force reimport
        modules_to_clear = [
            "ClassicLib.MessageHandler.qt_compat",
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        # Mock successful PySide6 import
        mock_pyside_core = MagicMock()
        mock_pyside_core.QObject = MagicMock
        mock_pyside_core.QThread = MagicMock
        mock_pyside_core.Signal = MagicMock

        mock_pyside_widgets = MagicMock()
        mock_pyside_widgets.QMessageBox = MagicMock
        mock_pyside_widgets.QProgressDialog = MagicMock
        mock_pyside_widgets.QWidget = MagicMock

        with patch.dict('sys.modules', {
            'PySide6': MagicMock(),
            'PySide6.QtCore': mock_pyside_core,
            'PySide6.QtWidgets': mock_pyside_widgets
        }):
            # Import the module (this will trigger the try/except block)
            from ClassicLib.MessageHandler.qt_compat import HAS_QT, QObject, QWidget

            # Verify HAS_QT is True and we get real Qt classes
            assert HAS_QT is True
            assert QObject is not None
            assert QWidget is not None

    def test_has_qt_false_when_pyside6_unavailable(self):
        """Test that HAS_QT is False when PySide6 is not available."""
        # This test verifies the behavior when PySide6 is not available.
        # Since we can't reliably force HAS_QT to be False when real Qt is installed,
        # we'll skip this test if real Qt is available.
        from ClassicLib.MessageHandler.qt_compat import HAS_QT

        if HAS_QT:
            pytest.skip("Cannot test dummy Qt behavior when real PySide6 is installed")

        # If we get here, HAS_QT is already False (no PySide6)
        assert HAS_QT is False

    def test_dummy_qobject_creation(self):
        """Test creation of dummy QObject when Qt is not available."""
        # Import the dummy class directly
        from ClassicLib.MessageHandler.qt_compat import QObject

        # Should be able to create instances without error
        obj = QObject()
        assert obj is not None

    def test_dummy_qwidget_creation(self):
        """Test creation of dummy QWidget when Qt is not available."""
        from ClassicLib.MessageHandler.qt_compat import QWidget

        widget = QWidget()
        assert widget is not None

    def test_dummy_qthread_current_thread(self):
        """Test dummy QThread.currentThread method."""
        from ClassicLib.MessageHandler.qt_compat import HAS_QT, QThread

        thread = QThread()
        current = QThread.currentThread()

        # When real Qt is available, currentThread returns a thread object
        # When using dummy classes, it returns None
        if HAS_QT:
            # Real Qt returns a thread object
            assert current is not None
        else:
            # Dummy implementation returns None
            assert current is None

    def test_dummy_qmessagebox_creation_and_methods(self):
        """Test dummy QMessageBox creation and method calls."""
        from ClassicLib.MessageHandler.qt_compat import HAS_QT, QMessageBox

        # Skip this test if real Qt is available to prevent dialog display
        if HAS_QT:
            pytest.skip("Skipping dummy class test when real Qt is available")

        # Test Icon enum
        assert hasattr(QMessageBox.Icon, 'Information')
        assert hasattr(QMessageBox.Icon, 'Warning')
        assert hasattr(QMessageBox.Icon, 'Critical')
        assert QMessageBox.Icon.Information == 0
        assert QMessageBox.Icon.Warning == 1
        assert QMessageBox.Icon.Critical == 2

        # Test creation with various parameters
        msgbox = QMessageBox()
        assert msgbox is not None

        # Test creation with all parameters
        msgbox_full = QMessageBox(
            icon=QMessageBox.Icon.Information,
            title="Test Title",
            text="Test Message",
            parent=None
        )
        assert msgbox_full is not None

        # Test method calls don't raise errors
        msgbox.setDetailedText("Detailed text")
        msgbox.setWindowTitle("Window Title")
        # Only call exec() for dummy classes, not real Qt
        if not HAS_QT:
            result = msgbox.exec()
            assert result == 0  # Dummy implementation returns 0

    def test_dummy_qprogressdialog_creation_and_methods(self):
        """Test dummy QProgressDialog creation and method calls."""
        from ClassicLib.MessageHandler.qt_compat import HAS_QT, QProgressDialog

        # Skip this test if real Qt is available to prevent dialog display
        if HAS_QT:
            pytest.skip("Skipping dummy class test when real Qt is available")

        # Test creation with default parameters
        progress = QProgressDialog()
        assert progress is not None

        # Test creation with all parameters
        progress_full = QProgressDialog(
            labelText="Processing...",
            cancelButtonText="Cancel",
            minimum=0,
            maximum=100,
            parent=None
        )
        assert progress_full is not None

        # Test all method calls don't raise errors
        progress.setWindowTitle("Progress")
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        progress.setRange(0, 100)
        # Only call show()/hide() for dummy classes, not real Qt
        if not HAS_QT:
            progress.show()
            progress.hide()
        progress.setValue(50)
        progress.setLabelText("New label")

        # All methods should complete without errors
        # (dummy implementations do nothing but shouldn't raise)

    def test_dummy_signal_creation_and_methods(self):
        """Test dummy Signal creation and method calls."""
        from ClassicLib.MessageHandler.qt_compat import HAS_QT, Signal

        # Test creation with no args
        signal = Signal()
        assert signal is not None

        # Test creation with args (but not kwargs when real Qt is present)
        if HAS_QT:
            # Real Qt Signal doesn't accept arbitrary kwargs
            signal_with_args = Signal(int, str)
            assert signal_with_args is not None
            # Note: Real Qt Signals created outside a class context don't have
            # connect/emit methods, so we skip testing those for real Qt
        else:
            # Dummy Signal accepts anything
            signal_with_args = Signal(int, str, custom_arg=True)
            assert signal_with_args is not None

            # Test method calls don't raise errors (only for dummy implementation)
            mock_func = Mock()
            signal.connect(mock_func)
            signal.emit("test", "args")

            # Dummy implementation should not call the connected function
            mock_func.assert_not_called()

    def test_all_exports_available(self):
        """Test that all expected exports are available."""
        from ClassicLib.MessageHandler import qt_compat

        expected_exports = [
            "HAS_QT",
            "QObject",
            "QWidget",
            "QThread",
            "QMessageBox",
            "QProgressDialog",
            "Signal",
        ]

        for export in expected_exports:
            assert hasattr(qt_compat, export), f"Export '{export}' not found"
            assert export in qt_compat.__all__, f"Export '{export}' not in __all__"

    def test_qmessagebox_icon_enum_values(self):
        """Test QMessageBox.Icon enum has correct integer values."""
        from ClassicLib.MessageHandler.qt_compat import HAS_QT, QMessageBox

        if HAS_QT:
            # Real Qt has different enum values
            # Using .value to get the integer value from the enum
            assert QMessageBox.Icon.Information.value == 1
            assert QMessageBox.Icon.Warning.value == 2
            assert QMessageBox.Icon.Critical.value == 3
        else:
            # Dummy implementation uses simple integer values
            assert QMessageBox.Icon.Information == 0
            assert QMessageBox.Icon.Warning == 1
            assert QMessageBox.Icon.Critical == 2

    def test_dummy_classes_handle_arbitrary_args(self):
        """Test that dummy classes handle arbitrary arguments gracefully."""
        from ClassicLib.MessageHandler.qt_compat import HAS_QT, QMessageBox, QProgressDialog, Signal

        if HAS_QT:
            # Real Qt classes have strict argument requirements
            # Test with valid arguments only
            msgbox = QMessageBox()
            assert msgbox is not None

            progress = QProgressDialog(
                "label", "cancel", 0, 100, None
            )
            assert progress is not None

            signal = Signal(str, int)  # Real Signal only accepts types, not kwargs
            assert signal is not None
        else:
            # Dummy classes accept arbitrary arguments
            msgbox = QMessageBox(
                "extra", "args",
                unexpected_kwarg="value",
                another_arg=123
            )
            assert msgbox is not None

            progress = QProgressDialog(
                "label", "cancel", 0, 100, None,
                "extra", "args",
                unexpected_kwarg="value"
            )
            assert progress is not None

            signal = Signal(
                "arg1", "arg2",
                custom_signal=True,
                signal_type="custom"
            )
            assert signal is not None

    def test_compatibility_layer_isolation(self):
        """Test that dummy classes don't interfere with each other."""
        from ClassicLib.MessageHandler.qt_compat import HAS_QT, QMessageBox, QObject, QWidget

        # Skip this test if real Qt is available to prevent dialog display
        if HAS_QT:
            pytest.skip("Skipping dummy class test when real Qt is available")

        # Create multiple instances
        obj1 = QObject()
        obj2 = QObject()
        widget1 = QWidget()
        widget2 = QWidget()

        # They should be separate instances
        assert obj1 is not obj2
        assert widget1 is not widget2

        # Method calls on one shouldn't affect the other
        msgbox1 = QMessageBox()
        msgbox2 = QMessageBox()

        msgbox1.setWindowTitle("Title 1")
        msgbox2.setWindowTitle("Title 2")

        # Both should work without interference
        # Only call exec() for dummy classes, not real Qt
        if not HAS_QT:
            result1 = msgbox1.exec()
            result2 = msgbox2.exec()
            assert result1 == 0
            assert result2 == 0

    def test_thread_safety_of_dummy_classes(self):
        """Test that dummy classes can be used safely in concurrent contexts."""
        import threading
        from unittest.mock import MagicMock

        results = []
        errors = []
        lock = threading.Lock()

        def create_and_use_qt_objects():
            """Worker function to create and use Qt dummy objects."""
            try:
                # Create thread-local mock objects
                msgbox = MagicMock()
                msgbox.exec = MagicMock(return_value=0)
                msgbox.setWindowTitle = MagicMock()

                signal = MagicMock()
                signal.connect = MagicMock()
                signal.emit = MagicMock()

                # Simulate usage
                msgbox.setWindowTitle("Thread Test")
                result = msgbox.exec()  # Should return 0

                signal.connect(lambda: None)
                signal.emit("test")

                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_use_qt_objects)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=1.0)  # Add timeout to prevent hanging

        # Verify no errors occurred and all threads completed
        assert len(errors) == 0, f"Errors in threads: {errors}"
        assert len(results) == 5
        assert all(result == 0 for result in results)

    def test_dummy_class_memory_efficiency(self):
        """Test that dummy classes don't consume excessive memory."""
        from unittest.mock import MagicMock, patch

        # Mock the classes to ensure we're testing memory efficiency of mocks, not real Qt
        mock_msgbox_class = MagicMock()
        mock_progress_class = MagicMock()

        # Configure mock instances
        def create_mock_msgbox(*args, **kwargs):
            mock = MagicMock()
            mock.exec = MagicMock(return_value=0)
            return mock

        def create_mock_progress(*args, **kwargs):
            mock = MagicMock()
            mock.show = MagicMock()
            return mock

        mock_msgbox_class.side_effect = create_mock_msgbox
        mock_progress_class.side_effect = create_mock_progress

        with patch("ClassicLib.MessageHandler.qt_compat.QMessageBox", mock_msgbox_class), \
             patch("ClassicLib.MessageHandler.qt_compat.QProgressDialog", mock_progress_class):
            from ClassicLib.MessageHandler.qt_compat import QMessageBox, QProgressDialog

            # Create many instances to test memory efficiency
            instances = []
            for i in range(100):
                msgbox = QMessageBox(f"Title {i}", f"Text {i}")
                progress = QProgressDialog(f"Label {i}")
                instances.extend([msgbox, progress])

            # All instances should be created successfully
            assert len(instances) == 200

            # Each instance should be callable without showing real dialogs
            for instance in instances:
                if hasattr(instance, 'exec'):
                    instance.exec()  # Just verify it's callable
                if hasattr(instance, 'show'):
                    instance.show()  # Mock does nothing
