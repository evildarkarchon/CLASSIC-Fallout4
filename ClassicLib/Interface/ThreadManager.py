"""
Central thread management system for CLASSIC application.

This module provides a ThreadManager class that centralizes thread lifecycle management,
ensures proper cleanup, and provides thread-safe operations for all worker threads.
"""

from enum import Enum

from PySide6.QtCore import QMutex, QObject, QThread, Signal

from ClassicLib.Logger import logger


class ThreadType(Enum):
    """Enumeration of thread types managed by ThreadManager."""

    UPDATE_CHECK = "update_check"
    PAPYRUS_MONITOR = "papyrus_monitor"
    PASTEBIN_FETCH = "pastebin_fetch"
    CRASH_LOGS_SCAN = "crash_logs_scan"
    GAME_FILES_SCAN = "game_files_scan"


class ManagedThread:
    """Container for a managed thread and its worker."""

    def __init__(self, thread: QThread, worker: QObject, thread_type: ThreadType) -> None:
        self.thread = thread
        self.worker = worker
        self.thread_type = thread_type
        self.start_time = None

    def is_running(self) -> bool:
        """Check if the thread is currently running."""
        return self.thread is not None and self.thread.isRunning()


class ThreadManager(QObject):
    """
    Centralized thread management system.

    This class provides thread-safe management of all worker threads in the application,
    including lifecycle management, cleanup, and graceful shutdown capabilities.
    """

    # Signals
    threadStarted: Signal = Signal(str)  # Thread type
    threadFinished: Signal = Signal(str)  # Thread type
    threadError: Signal = Signal(str, str)  # Thread type, error message

    def __init__(self) -> None:
        super().__init__()
        self._threads: dict[ThreadType, ManagedThread] = {}
        self._mutex = QMutex()
        self._shutdown_in_progress = False

    def register_thread(self, thread_type: ThreadType, thread: QThread, worker: QObject) -> bool:
        """
        Register a new thread with the manager.

        Args:
            thread_type: The type of thread being registered
            thread: The QThread instance
            worker: The worker QObject

        Returns:
            bool: True if registered successfully, False if a thread of this type is already running
        """
        self._mutex.lock()
        try:
            # Check if a thread of this type is already running
            if thread_type in self._threads and self._threads[thread_type].is_running():
                logger.warning(f"Thread type {thread_type.value} is already running")
                return False

            # Create managed thread
            managed_thread = ManagedThread(thread, worker, thread_type)
            self._threads[thread_type] = managed_thread

            # Connect cleanup signals
            thread.finished.connect(lambda: self._on_thread_finished(thread_type))

            logger.info(f"Registered thread: {thread_type.value}")
            return True

        finally:
            self._mutex.unlock()

    def start_thread(self, thread_type: ThreadType) -> bool:
        """
        Start a registered thread.

        Args:
            thread_type: The type of thread to start

        Returns:
            bool: True if started successfully, False otherwise
        """
        self._mutex.lock()
        try:
            if self._shutdown_in_progress:
                logger.warning("Cannot start thread during shutdown")
                return False

            if thread_type not in self._threads:
                logger.error(f"Thread type {thread_type.value} not registered")
                return False

            managed_thread = self._threads[thread_type]
            if managed_thread.is_running():
                logger.warning(f"Thread {thread_type.value} is already running")
                return False

            # Start the thread
            managed_thread.thread.start()
            logger.info(f"Started thread: {thread_type.value}")

            # Emit signal
            self.threadStarted.emit(thread_type.value)
            return True

        finally:
            self._mutex.unlock()

    def stop_thread(self, thread_type: ThreadType, wait_ms: int = 5000) -> bool:
        """
        Stop a running thread gracefully.

        Args:
            thread_type: The type of thread to stop
            wait_ms: Maximum time to wait for thread to stop (milliseconds)

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        self._mutex.lock()
        try:
            if thread_type not in self._threads:
                return True  # Thread doesn't exist, consider it stopped

            managed_thread = self._threads[thread_type]
            if not managed_thread.is_running():
                return True  # Already stopped

            logger.info(f"Stopping thread: {thread_type.value}")

            # Signal the worker to stop if it has a stop method
            if managed_thread.worker and hasattr(managed_thread.worker, "stop"):
                managed_thread.worker.stop()  # type: ignore[reportAttributeAccessIssue]

            # Signal the thread to quit
            managed_thread.thread.quit()

            # Wait for thread to finish
            if not managed_thread.thread.wait(wait_ms):
                logger.warning(f"Thread {thread_type.value} did not stop within {wait_ms}ms")
                return False

            return True

        finally:
            self._mutex.unlock()

    def stop_all_threads(self, wait_ms: int = 5000) -> None:
        """
        Stop all running threads gracefully.

        Args:
            wait_ms: Maximum time to wait for each thread to stop
        """
        logger.info("Stopping all threads...")
        self._shutdown_in_progress = True

        # Get list of running threads
        self._mutex.lock()
        running_threads = [tt for tt, mt in self._threads.items() if mt.is_running()]
        self._mutex.unlock()

        # Stop each thread
        for thread_type in running_threads:
            self.stop_thread(thread_type, wait_ms)

        logger.info("All threads stopped")

    def get_running_threads(self) -> set[ThreadType]:
        """
        Get a set of currently running thread types.

        Returns:
            Set of ThreadType enums for running threads
        """
        self._mutex.lock()
        try:
            return {tt for tt, mt in self._threads.items() if mt.is_running()}
        finally:
            self._mutex.unlock()

    def is_thread_running(self, thread_type: ThreadType) -> bool:
        """
        Check if a specific thread type is running.

        Args:
            thread_type: The type of thread to check

        Returns:
            bool: True if running, False otherwise
        """
        self._mutex.lock()
        try:
            if thread_type not in self._threads:
                return False
            return self._threads[thread_type].is_running()
        finally:
            self._mutex.unlock()

    def cleanup_finished_threads(self) -> None:
        """Remove references to finished threads."""
        self._mutex.lock()
        try:
            finished_types = [tt for tt, mt in self._threads.items() if not mt.is_running()]
            for thread_type in finished_types:
                del self._threads[thread_type]
                logger.debug(f"Cleaned up thread: {thread_type.value}")
        finally:
            self._mutex.unlock()

    def _on_thread_finished(self, thread_type: ThreadType) -> None:
        """Handle thread finished signal."""
        logger.info(f"Thread finished: {thread_type.value}")
        self.threadFinished.emit(thread_type.value)

        # Clean up the thread reference
        self._mutex.lock()
        try:
            if thread_type in self._threads:
                del self._threads[thread_type]
        finally:
            self._mutex.unlock()


# Global thread manager instance
_thread_manager: ThreadManager | None = None


def get_thread_manager() -> ThreadManager:
    """Get the global ThreadManager instance."""
    global _thread_manager  # noqa: PLW0603
    if _thread_manager is None:
        _thread_manager = ThreadManager()
    return _thread_manager
