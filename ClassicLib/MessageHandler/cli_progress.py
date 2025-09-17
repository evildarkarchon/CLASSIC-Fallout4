"""
A command-line interface (CLI) progress bar utility.

This module implements a class that provides a CLI-based progress bar for
tracking iterative tasks in command-line applications. The progress bar
supports both percentage-based and item count representations based on
the task requirements. The user can update the progress, set a description,
and manage the lifecycle of the progress bar using dedicated methods.
"""


class CLIProgressBar:
    """
    A command-line interface (CLI) progress bar utility.

    This class provides a text-based progress indicator for tracking the progress
    of iterative tasks in command-line applications. It can display the progress
    in the form of a percentage-based bar when a total is provided, or as simply
    the count of processed items if no total is defined. The progress bar can be
    updated as the task progresses, and a description can be set for improved
    context.

    Attributes:
        desc (str): A description displayed alongside the progress bar.
        total (int | None): The total number of items to process.
        current (int): The current progress or number of items processed.
    """

    def __init__(self, desc: str = "", total: int | None = None) -> None:
        """Initialize CLI progress bar.

        Args:
            desc: Description to show
            total: Total number of items
        """
        self.desc = desc
        self.total = total
        self.current = 0
        self._closed = False

    def update(self, n: int = 1) -> None:
        """
        Updates the current progress of the operation and displays it to the user
        in the form of a progress bar. If the total value for the progress operation
        is specified, it will show a percentage-based progress bar. Otherwise, it will
        display an ongoing count of processed items.

        Args:
            n (int): The number of items to increment the progress by. Default is 1.
        """
        if self._closed:
            return

        self.current += n
        if self.total:
            percent = int((self.current / self.total) * 100)
            bar_length = 40
            filled = int(bar_length * self.current / self.total)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\r{self.desc}: [{bar}] {percent}%", end="", flush=True)
        else:
            print(f"\r{self.desc}: {self.current} items processed", end="", flush=True)

    def set_description(self, desc: str) -> None:
        """
        Sets the description for the instance.

        This method updates the `desc` attribute of the object to the
        specified description string.

        Args:
            desc (str): The description to set for the instance.
        """
        self.desc = desc

    def close(self) -> None:
        """
        Closes the resource.

        Ensures that the resource is only closed once. If the resource is not already
        closed, adds a new line after the progress output and marks the resource as
        closed.

        """
        if not self._closed:
            print(flush=True)  # New line after progress
            self._closed = True
