from PySide6.QtCore import QObject, Signal, Slot


class PastebinFetchWorker(QObject):
    """
    Handles fetching data from a given Pastebin URL within a PyQt framework.

    This class is designed as a worker object for performing asynchronous operations to retrieve data from a specified
    Pastebin URL. The class uses signals to emit the success, error, or completion states of the operation. It ensures
    robust handling of exceptions, including network errors, import failures, configuration issues, and other unforeseen
    problems, making it suitable for integration into PyQt applications.

    Attributes:
        finished (Signal): Signal emitted when the operation finishes, regardless of success or failure.
        error (Signal): Signal emitted with an error message in case of failure.
        success (Signal): Signal emitted with the URL upon successful data fetch.
    """

    finished: Signal = Signal()
    error: Signal = Signal(str)
    success: Signal = Signal(str)

    def __init__(self, url: str) -> None:
        """
        Initializes an instance of the class with a given URL.

        This constructor method assigns the provided URL to the instance attribute.

        Args:
            url (str): The URL to be assigned to the instance.
        """
        super().__init__()
        self.url = url

    # noinspection PyUnresolvedReferences
    @Slot()
    def run(self) -> None:
        """
        Executes a slot function to fetch data from a specified URL using the `pastebin_fetch_async` function. This
        function emits corresponding signals based on the success or failure of the operation.

        The function is aimed to handle possible exceptions such as network-related issues, module import
        failures, and other unforeseen exceptions. Upon successful completion or encountering an error,
        appropriate signals are emitted to handle the outcome.

        Attributes:
            url (str): The URL to fetch data from. It is expected to be a valid and properly formatted URL.

        Signals:
            success (pyqtSignal): Emitted with the `url` attribute upon a successful data fetch.
            error (pyqtSignal): Emitted with a formatted string containing an error message in case of failure.
            finished (pyqtSignal): Emitted irrespective of success or failure, signaling the completion of
                the operation.

        Raises:
            OSError: If there are file-system-related issues.
            ValueError: If invalid configuration or input data is encountered.
            aiohttp.ClientError: For network-related issues such as connection problems.
            ImportError: If the required import operation for a module fails to execute.
            Exception: If a general exception is encountered outside specific types mentioned.
        """
        try:
            # Make sure pastebin_fetch_async is properly imported
            import asyncio

            import aiohttp

            from ClassicLib.Util import pastebin_fetch_async

            # Create and run async event loop
            loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(pastebin_fetch_async(self.url))
                self.success.emit(self.url)
            except aiohttp.ClientError as e:
                self.error.emit(f"Network error: {e!s}")
            finally:
                loop.close()

        except (OSError, ValueError) as e:
            self.error.emit(f"File system or value error: {e!s}")
        except ImportError as e:
            self.error.emit(f"Failed to import required module: {e!s}")
        except Exception as e:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {e!s}")
        finally:
            self.finished.emit()
