"""CLI progress handling for command-line progress display.

This module provides CLI-based progress indicators:
- CLIProgressBar: Simple text-based progress bar
- CLIProgressHandler: Wrapper implementing the ProgressHandler protocol
"""

from __future__ import annotations

import time
from typing import Final


class CLIProgressBar:
    """Simple text-based progress bar for CLI environments.

    This class provides a basic progress bar that works without any
    external dependencies (no tqdm required).

    Attributes:
        desc: Description text for the progress bar.
        total: Total number of items, or None for indeterminate.
        current: Current progress count.
    """

    def __init__(self, desc: str, total: int | None = None) -> None:
        """Initialize the progress bar.

        Args:
            desc: Description to display.
            total: Total items, or None for indeterminate progress.
        """
        self.desc = desc
        self.total = total
        self.current = 0
        self._closed = False
        self._last_print_time = 0.0
        self._print_interval = 0.1  # 100ms throttle

        # Print initial state
        self._print_progress()

    def _print_progress(self) -> None:
        """Print the current progress state."""
        if self._closed:
            return

        if self.total is not None and self.total > 0:
            percentage = min(100, (self.current / self.total) * 100)
            bar_width = 30
            filled = int(bar_width * self.current / self.total)
            bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
            line = f"\r{self.desc}: [{bar}] {percentage:5.1f}% ({self.current}/{self.total})"
        else:
            # Indeterminate progress - spinning indicator
            spinner = ["\u2580", "\u2584", "\u2588", "\u2591"]
            spin_char = spinner[self.current % len(spinner)]
            line = f"\r{self.desc}: {spin_char} {self.current} items"

        print(line, end="", flush=True)

    def update(self, n: int = 1) -> None:
        """Update the progress bar.

        Args:
            n: Number of items to increment.
        """
        if self._closed:
            return

        self.current += n

        # Throttle updates for performance
        current_time = time.time()
        if current_time - self._last_print_time >= self._print_interval:
            self._print_progress()
            self._last_print_time = current_time
        elif self.total is not None and self.current >= self.total:
            # Always print final state
            self._print_progress()

    def set_description(self, desc: str) -> None:
        """Update the description.

        Args:
            desc: New description text.
        """
        self.desc = desc

    def close(self) -> None:
        """Close the progress bar and print newline."""
        if not self._closed:
            self._print_progress()  # Final update
            print()  # Newline after progress bar
            self._closed = True


class CLIProgressHandler:
    """CLI progress handler implementing the ProgressHandler protocol.

    This handler wraps CLIProgressBar to provide the standard
    ProgressHandler interface.
    """

    # Throttle interval in seconds
    _THROTTLE_INTERVAL: Final[float] = 0.1

    def __init__(self) -> None:
        """Initialize the handler."""
        self._progress_bar: CLIProgressBar | None = None
        self._cancelled = False
        self._last_update_time = 0.0

    def start(self, description: str, total: int | None = None) -> None:
        """Start the progress indicator.

        Args:
            description: Description of the operation.
            total: Total items, or None for indeterminate.
        """
        self._progress_bar = CLIProgressBar(description, total)
        self._cancelled = False
        self._last_update_time = time.time()

    def update(self, n: int = 1, description: str | None = None) -> None:
        """Update progress.

        Args:
            n: Items completed since last update.
            description: Optional new description.
        """
        if self._progress_bar is None:
            return

        # Throttle updates
        current_time = time.time()
        if current_time - self._last_update_time < self._THROTTLE_INTERVAL:
            # Still update the count internally
            self._progress_bar.current += n
            return

        if description:
            self._progress_bar.set_description(description)
        self._progress_bar.update(n)
        self._last_update_time = current_time

    def close(self) -> None:
        """Close the progress indicator."""
        if self._progress_bar is not None:
            self._progress_bar.close()
            self._progress_bar = None

    def was_cancelled(self) -> bool:
        """Check if cancelled.

        Returns:
            False - CLI progress cannot be cancelled by user.
        """
        return self._cancelled

    def is_available(self) -> bool:  # noqa: PLR6301
        """Check if CLI progress is available.

        Returns:
            True - CLI is always available.
        """
        return True
