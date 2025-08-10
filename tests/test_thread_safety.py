"""
Unit tests for thread safety improvements in CLASSIC application.

This module tests the thread-safe implementations including:
- ThreadManager functionality
- Mutex-protected operations
- Thread lifecycle management
- Graceful shutdown
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication

from ClassicLib.Interface.Papyrus import PapyrusMonitorWorker
from ClassicLib.Interface.ThreadManager import ThreadManager, ThreadType


# Test worker class
class ThreadTestWorker(QObject):
    """Simple test worker for thread testing."""
    
    finished = Signal()
    result = Signal(str)
    
    def __init__(self, work_time: float = 0.1) -> None:
        super().__init__()
        self._work_time = work_time
        self._should_run = True
        
    @Slot()
    def run(self) -> None:
        """Simulate some work."""
        start_time = time.time()
        while self._should_run and (time.time() - start_time) < self._work_time:
            QThread.msleep(10)
        self.result.emit("Work completed")
        self.finished.emit()
        
    def stop(self) -> None:
        """Stop the worker."""
        self._should_run = False


class TestThreadManager:
    """Test cases for ThreadManager class."""
    
    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
        
    @pytest.fixture
    def thread_manager(self) -> ThreadManager:
        """Create a fresh ThreadManager instance."""
        return ThreadManager()
        
    def test_register_thread(self, thread_manager: ThreadManager, app: QApplication) -> None:
        """Test thread registration."""
        thread = QThread()
        worker = ThreadTestWorker()
        
        # Should successfully register
        assert thread_manager.register_thread(ThreadType.UPDATE_CHECK, thread, worker)
        
        # Should fail to register same type while running
        thread.start()
        assert not thread_manager.register_thread(ThreadType.UPDATE_CHECK, QThread(), ThreadTestWorker())
        
        # Cleanup
        thread.quit()
        thread.wait()
        
    def test_start_thread(self, thread_manager: ThreadManager, app: QApplication) -> None:
        """Test thread starting."""
        thread = QThread()
        worker = ThreadTestWorker()
        
        # Register thread
        thread_manager.register_thread(ThreadType.PAPYRUS_MONITOR, thread, worker)
        
        # Connect worker
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        
        # Start should succeed
        assert thread_manager.start_thread(ThreadType.PAPYRUS_MONITOR)
        
        # Should not start again while running
        assert not thread_manager.start_thread(ThreadType.PAPYRUS_MONITOR)
        
        # Wait for completion
        thread.wait(1000)
        
    def test_stop_thread(self, thread_manager: ThreadManager, app: QApplication) -> None:
        """Test thread stopping."""
        thread = QThread()
        worker = ThreadTestWorker(work_time=0.5)
        
        # Setup thread
        thread_manager.register_thread(ThreadType.CRASH_LOGS_SCAN, thread, worker)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        
        # Start thread
        thread_manager.start_thread(ThreadType.CRASH_LOGS_SCAN)
        
        # Thread should be running
        assert thread_manager.is_thread_running(ThreadType.CRASH_LOGS_SCAN)
        
        # Stop thread
        worker.stop()
        assert thread_manager.stop_thread(ThreadType.CRASH_LOGS_SCAN, wait_ms=2000)
        
        # Thread should not be running
        assert not thread_manager.is_thread_running(ThreadType.CRASH_LOGS_SCAN)
        
    def test_get_running_threads(self, thread_manager: ThreadManager, app: QApplication) -> None:
        """Test getting running threads."""
        # No threads initially
        assert len(thread_manager.get_running_threads()) == 0
        
        # Add and start multiple threads
        threads = []
        workers = []
        thread_types = [ThreadType.UPDATE_CHECK, ThreadType.PAPYRUS_MONITOR]
        
        for thread_type in thread_types:
            thread = QThread()
            worker = ThreadTestWorker()
            threads.append(thread)
            workers.append(worker)
            
            thread_manager.register_thread(thread_type, thread, worker)
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            thread_manager.start_thread(thread_type)
            
        # Should have 2 running threads
        running = thread_manager.get_running_threads()
        assert len(running) == 2
        assert ThreadType.UPDATE_CHECK in running
        assert ThreadType.PAPYRUS_MONITOR in running
        
        # Stop threads
        for worker in workers:
            worker.stop()
            
        for thread in threads:
            thread.quit()
            thread.wait(1000)
            
    def test_stop_all_threads(self, thread_manager: ThreadManager, app: QApplication) -> None:
        """Test stopping all threads."""
        # Start multiple threads
        thread_types = [
            ThreadType.UPDATE_CHECK,
            ThreadType.PAPYRUS_MONITOR,
            ThreadType.PASTEBIN_FETCH
        ]
        
        threads = []
        workers = []
        
        for thread_type in thread_types:
            thread = QThread()
            worker = ThreadTestWorker(work_time=0.3)
            threads.append(thread)
            workers.append(worker)
            
            thread_manager.register_thread(thread_type, thread, worker)
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            thread_manager.start_thread(thread_type)
            
        # All threads should be running
        assert len(thread_manager.get_running_threads()) == 3
        
        # Stop all threads
        for worker in workers:
            worker.stop()
        thread_manager.stop_all_threads(wait_ms=2000)
        
        # No threads should be running
        assert len(thread_manager.get_running_threads()) == 0


class TestPapyrusMonitorThreadSafety:
    """Test thread safety in PapyrusMonitorWorker."""
    
    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    def test_papyrus_monitor_stop(self) -> None:
        """Test thread-safe stop method."""
        worker = PapyrusMonitorWorker()
        
        # Initial state
        assert worker._should_run is True
        
        # Stop should be thread-safe
        worker.stop()
        assert worker._should_run is False
        
    @patch('ClassicLib.Interface.Papyrus.papyrus_logging')
    def test_papyrus_monitor_run_loop(self, mock_logging: MagicMock, app: QApplication) -> None:
        """Test the run loop respects thread-safe stop."""
        # Create a mock that simulates papyrus_logging and allows controlled stopping
        call_count = [0]
        
        def mock_logging_func():
            call_count[0] += 1
            # Return different data to trigger stats update
            if call_count[0] == 1:
                return ("NUMBER OF DUMPS    : 5\nNUMBER OF STACKS   : 10\n", 5)
            else:
                # Raise exception to exit the loop after first iteration
                raise OSError("Test controlled exit")
        
        mock_logging.side_effect = mock_logging_func
        
        # Test 1: Worker stops immediately when _should_run is False
        worker = PapyrusMonitorWorker()
        stats_received = []
        error_received = []
        
        worker.statsUpdated.connect(lambda stats: stats_received.append(stats))
        worker.error.connect(lambda err: error_received.append(err))
        
        # Stop before running
        worker.stop()
        worker.run()
        
        # Should not have received any stats since it was stopped
        assert len(stats_received) == 0
        assert call_count[0] == 0  # Should not have called papyrus_logging
        
        # Test 2: Worker processes stats and exits on error
        worker2 = PapyrusMonitorWorker()
        stats_received2 = []
        error_received2 = []
        call_count[0] = 0  # Reset counter
        
        worker2.statsUpdated.connect(lambda stats: stats_received2.append(stats))
        worker2.error.connect(lambda err: error_received2.append(err))
        
        # Run the worker (will exit after one iteration due to mock)
        worker2.run()
        
        # Should have received exactly one stats update before the error
        assert len(stats_received2) == 1
        assert stats_received2[0].dumps == 5
        assert stats_received2[0].stacks == 10
        assert len(error_received2) == 1
        assert "Test controlled exit" in error_received2[0]


class TestThreadReusePrevention:
    """Test that threads are not reused."""
    
    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
        
    @pytest.mark.usefixtures("init_message_handler_fixture")
    def test_pastebin_thread_not_reused(self, app: QApplication) -> None:
        """Test that Pastebin fetch creates new thread each time."""
        # Test pastebin thread handling
        from ClassicLib.Interface.ThreadManager import ThreadManager
        
        thread_manager = ThreadManager()
        
        # Create mock thread and worker
        mock_thread = MagicMock(spec=QThread)
        mock_worker = MagicMock()
        
        # Register thread
        thread_type = ThreadType.PASTEBIN_FETCH
        assert thread_manager.register_thread(thread_type, mock_thread, mock_worker)
        
        # Should not be able to register same type again while running
        mock_thread.isRunning.return_value = True
        assert not thread_manager.register_thread(thread_type, MagicMock(), MagicMock())
        
        # After thread finishes, manager should detect it's not running
        mock_thread.isRunning.return_value = False
        # Remove from internal dict to simulate cleanup
        thread_manager._threads.pop(thread_type, None)
        assert thread_manager.register_thread(thread_type, MagicMock(), MagicMock())


class TestRaceConditionPrevention:
    """Test race condition prevention in button state management."""
    
    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.mark.usefixtures("init_message_handler_fixture")
    def test_scan_mutex_protection(self, app: QApplication) -> None:
        """Test that scan operations are protected by mutex."""
        # Test the ScanOperationsMixin directly instead of full MainWindow
        from ClassicLib.Interface.ScanOperations import ScanOperationsMixin
        from PySide6.QtCore import QMutex
        from PySide6.QtWidgets import QWidget
        from ClassicLib.Interface.ThreadManager import get_thread_manager
        
        # Create a test class that uses the mixin and inherits from QWidget
        class TestScanClass(QWidget, ScanOperationsMixin):
            def __init__(self):
                super().__init__()
                self._scan_mutex = QMutex()
                self._running_scans = set()
                self.thread_manager = get_thread_manager()
                self.crash_logs_thread = None
                self.crash_logs_worker = None
                self.game_files_thread = None
                self.game_files_worker = None
                self.audio_player = MagicMock()
                self.scan_button_group = MagicMock()
                self.papyrus_button = None
        
        # Create instance and test
        test_obj = TestScanClass()
        
        # Simulate concurrent scan attempts
        test_obj._running_scans.add("crash_logs")
        
        # Try to start another crash logs scan
        # Should be prevented by mutex check
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            test_obj.crash_logs_scan()
            # Should show warning about scan in progress
            mock_warning.assert_called_once_with(
                test_obj, "Scan in Progress", "A crash logs scan is already in progress."
            )


class TestGracefulShutdown:
    """Test graceful shutdown functionality."""
    
    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
        
    @pytest.mark.usefixtures("init_message_handler_fixture")
    def test_close_event_cleanup(self, app: QApplication) -> None:
        """Test that closeEvent properly cleans up all threads."""
        # Test thread cleanup on close
        from ClassicLib.Interface.ThreadManager import ThreadManager, ThreadType
        
        thread_manager = ThreadManager()
        
        # Register multiple mock threads
        threads = []
        workers = []
        for thread_type in [ThreadType.UPDATE_CHECK, ThreadType.PASTEBIN_FETCH]:
            mock_thread = MagicMock(spec=QThread)
            mock_worker = MagicMock()
            # Add stop method to worker mock
            mock_worker.stop = MagicMock()
            mock_thread.isRunning.return_value = True
            threads.append(mock_thread)
            workers.append(mock_worker)
            thread_manager.register_thread(thread_type, mock_thread, mock_worker)
        
        # Stop all threads
        thread_manager.stop_all_threads(wait_ms=100)
        
        # Verify all threads were asked to quit
        for thread in threads:
            thread.quit.assert_called()
        
        # Verify all workers were asked to stop (if they have stop method)
        for worker in workers:
            worker.stop.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])