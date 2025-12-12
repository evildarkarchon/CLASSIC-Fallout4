"""Central thread management system for CLASSIC application.

This module provides a ThreadManager class that centralizes thread lifecycle management,
ensures proper cleanup, and provides thread-safe operations for all worker threads.
"""

from enum import Enum

from PySide6.QtCore import QMutex, QObject, QThread, Signal

from ClassicLib.Logger import logger


class ThreadType(Enum):
    """Define an enumeration for different types of threads.

    This class is used to specify various thread types for specific operations. Each thread
    type corresponds to a distinct functionality in the system.

    Attributes:
        UPDATE_CHECK (str): Represents threads responsible for checking updates.
        PAPYRUS_MONITOR (str): Represents threads monitoring Papyrus logs.
        PASTEBIN_FETCH (str): Represents threads fetching data from Pastebin.
        CRASH_LOGS_SCAN (str): Represents threads scanning crash logs.
        GAME_FILES_SCAN (str): Represents threads scanning game files.

    """

    UPDATE_CHECK = "update_check"
    PAPYRUS_MONITOR = "papyrus_monitor"
    PASTEBIN_FETCH = "pastebin_fetch"
    CRASH_LOGS_SCAN = "crash_logs_scan"
    GAME_FILES_SCAN = "game_files_scan"


class ManagedThread:
    """Manage a thread and its associated worker with specific threading types.

    This class serves as a manager to handle operations involving a thread,
    a worker, and their associated configurations. It provides functionality
    to check the running status of the thread and other related operations.

    Attributes:
        thread: The QThread object being managed.
        worker: The QObject worker assigned to handle tasks.
        thread_type: The ThreadType indicating the purpose of this thread.
        start_time: Timestamp when the thread started, or None if not started.

    """

    def __init__(self, thread: QThread, worker: QObject, thread_type: ThreadType) -> None:
        """Initialize an instance of the class with the given thread, worker, and thread type.

        Args:
            thread (QThread): The thread associated with the instance.
            worker (QObject): The worker object for performing tasks in the thread.
            thread_type (ThreadType): The type of thread indicating its purpose or category.

        """
        self.thread = thread
        self.worker = worker
        self.thread_type = thread_type
        self.start_time = None

    def is_running(self) -> bool:
        """Determine if the associated thread is currently running.

        This method checks the status of the thread to determine if it is active
        and running. It returns a boolean indicating the running state of the
        thread.

        Returns:
            bool: True if the thread is running, False otherwise.

        """
        return self.thread is not None and self.thread.isRunning()


class ThreadManager(QObject):
    """Manage threads and their lifecycle in a concurrent application.

    The ThreadManager class is responsible for registering, starting, stopping,
    and cleaning up threads. It provides mechanisms to manage thread safety and
    ensures proper handling of threads, including graceful shutdown procedures.
    It also emits signals to notify about thread-related events.

    Attributes:
        threadStarted: Signal emitted when a thread starts (contains thread type).
        threadFinished: Signal emitted when a thread stops (contains thread type).
        threadError: Signal emitted on thread error (contains type and message).

    Example:
        >>> from ClassicLib.Interface.ThreadManager import ThreadManager, ThreadType
        >>> manager = ThreadManager()
        >>>
        >>> # Create thread and worker
        >>> thread = QThread()
        >>> worker = SomeWorker()
        >>> worker.moveToThread(thread)
        >>>
        >>> # Register and start
        >>> if manager.register_thread(ThreadType.CRASH_LOGS_SCAN, thread, worker):
        ...     thread.started.connect(worker.run)
        ...     thread.start()
        >>>
        >>> # Later, stop the thread
        >>> manager.stop_thread(ThreadType.CRASH_LOGS_SCAN)

    """

    # Signals
    threadStarted: Signal = Signal(str)  # Thread type
    threadFinished: Signal = Signal(str)  # Thread type
    threadError: Signal = Signal(str, str)  # Thread type, error message

    def __init__(self) -> None:
        """Initialize an instance of the class.

        The constructor prepares the necessary initial conditions for managing threads,
        including maintaining a dictionary of threads, a mutex for thread synchronization,
        and a flag to track shutdown operations.
        """
        super().__init__()
        self._threads: dict[ThreadType, ManagedThread] = {}
        self._mutex = QMutex()
        self._shutdown_in_progress = False

    def register_thread(self, thread_type: ThreadType, thread: QThread, worker: QObject) -> bool:
        """Register a new thread with the specified thread type, thread instance, and
        worker object. This method ensures that only one thread of a given type can
        be active at a time. If a thread of the specified type is already running,
        the registration will fail. When successfully registered, the thread is managed
        internally and cleanup operations are triggered once the thread finishes execution.

        Args:
            thread_type: The type or category of the thread being registered; used for
                uniquely identifying and managing threads.
            thread: The QThread instance representing the thread to be registered.
            worker: The QObject that performs the actual work inside the thread.

        Returns:
            bool: True if the thread is successfully registered; False if a thread
            of the same type is already running.

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
        """Start a thread of a specified type, ensuring proper setup and thread state management.

        This function attempts to start a thread of the given type. It ensures that no threads
        are started during a system shutdown, that the specified thread type is registered,
        and that the thread is not already running. If all conditions are met, the thread is
        started, and relevant signals are emitted.

        Args:
            thread_type (ThreadType): The type of thread to be started. Must be a valid and
                registered thread type.

        Returns:
            bool: True if the thread is successfully started, False otherwise.

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
        """Stop a specific thread of the given type, waits for its completion, and ensures it is not running.

        This method stops a managed thread if it exists and is currently running. It ensures
        the thread terminates properly within the specified waiting period. If the thread does
        not exist or is already stopped, the method will simply confirm its stopped state.

        Args:
            thread_type (ThreadType): The type of thread to be stopped.
            wait_ms (int): The maximum time in milliseconds to wait for the thread to stop. Defaults to 5000.

        Returns:
            bool: True if the thread has stopped successfully or is already stopped. False if the thread
                  could not be stopped within the specified time.

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
        """Stop all threads managed by the current instance.

        This method first marks that a shutdown is in progress, then retrieves a list
        of all currently running threads. It subsequently stops each thread with a
        specified wait time before concluding the operation.

        Args:
            wait_ms (int): The maximum wait time in milliseconds for each thread
                to stop. Defaults to 5000.

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
        """Return a set of currently running thread types.

        This method retrieves thread types that are actively running by checking
        the state of each thread managed in the internal thread collection.

        Returns:
            set[ThreadType]: A set containing thread types that are currently running.

        """
        self._mutex.lock()
        try:
            return {tt for tt, mt in self._threads.items() if mt.is_running()}
        finally:
            self._mutex.unlock()

    def is_thread_running(self, thread_type: ThreadType) -> bool:
        """Check whether a specific type of thread is currently running.

        This method determines whether a thread of the specified type is actively
        running. If the thread type does not exist within the managed threads, the
        method returns False. Thread safety is ensured by locking and unlocking a mutex
        during the operation.

        Args:
            thread_type: The type of thread to be checked.

        Returns:
            bool: True if the thread is running, False otherwise.

        """
        self._mutex.lock()
        try:
            if thread_type not in self._threads:
                return False
            return self._threads[thread_type].is_running()
        finally:
            self._mutex.unlock()

    def cleanup_finished_threads(self) -> None:
        """Clean up finished threads from the internal thread tracking mechanism.

        Removes threads that have finished executing from the internal dictionary
        and logs each cleanup action. Ensures thread-safe operation by locking and
        unlocking a mutex during the cleanup process.

        Raises:
            Any error occurring during thread dictionary modification or mutex operation.

        """
        self._mutex.lock()
        try:
            finished_types = [tt for tt, mt in self._threads.items() if not mt.is_running()]
            for thread_type in finished_types:
                del self._threads[thread_type]
                logger.debug(f"Cleaned up thread: {thread_type.value}")
        finally:
            self._mutex.unlock()

    def _on_thread_finished(self, thread_type: ThreadType) -> None:
        """Handle the completion of a thread operation and performs cleanup.

        This method is triggered when a thread finishes its execution. It logs the
        completion of the thread, emits a signal indicating the thread's completion,
        and removes the thread reference from internal tracking to ensure proper
        resource management.

        Args:
            thread_type: The type of the thread that has finished execution.

        """
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
    """Retrieve the global instance of ThreadManager. If the instance does not
    exist, it initializes and assigns it.

    Returns:
        ThreadManager: The global instance of the ThreadManager.

    """
    global _thread_manager  # noqa: PLW0603
    if _thread_manager is None:
        _thread_manager = ThreadManager()
    return _thread_manager
