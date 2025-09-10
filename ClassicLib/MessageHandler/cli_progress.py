"""CLI progress bar implementation for when tqdm is not available."""


class CLIProgressBar:
    """Simple progress bar for CLI when tqdm is not available."""

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
        Updates the progress bar or item processing status.

        This method increments the current progress by a specified amount
        and prints the updated progress to the console. If the total value is
        set, it displays a progress bar along with the percentage of completion.
        If the total is not specified, it shows the number of items processed.
        The progress will not update if the related task or process is marked
        as closed.

        Parameters:
            n (int): The number by which to increment the current progress. Defaults to 1.

        Returns:
            None

        Raises:
            None
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
        Sets a description for the object.

        This method assigns the given string description to the `desc`
        attribute of the object.

        Parameters:
            desc (str): The description to assign to the object.
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
