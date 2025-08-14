"""Progress bar widget for TUI."""

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import ProgressBar as TextualProgressBar
from textual.widgets import Static


class ProgressBar(Static):
    """Enhanced progress bar with label and percentage display."""

    progress = reactive(0.0)
    total = reactive(100.0)
    label = reactive("")

    def __init__(
        self, label: str = "", total: float = 100.0, show_percentage: bool = True, show_eta: bool = False, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.label = label
        self.total = total
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self._progress_bar: TextualProgressBar | None = None
        self._label_widget: Static | None = None
        self._percentage_widget: Static | None = None

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        if self.label:
            self._label_widget = Static(self.label, classes="progress-label")
            yield self._label_widget

        self._progress_bar = TextualProgressBar(total=self.total, classes="progress-bar")
        yield self._progress_bar

        if self.show_percentage:
            self._percentage_widget = Static("0%", classes="progress-percentage")
            yield self._percentage_widget

    def update_progress(self, value: float) -> None:
        """Update the progress value."""
        self.progress = min(max(value, 0.0), self.total)

        if self._progress_bar:
            self._progress_bar.update(progress=self.progress)

        if self._percentage_widget and self.show_percentage:
            percentage = int((self.progress / self.total) * 100)
            self._percentage_widget.update(f"{percentage}%")

    def set_label(self, label: str) -> None:
        """Update the progress label."""
        self.label = label
        if self._label_widget:
            self._label_widget.update(label)

    def reset(self) -> None:
        """Reset the progress bar."""
        self.progress = 0.0
        if self._progress_bar:
            self._progress_bar.update(progress=0)
        if self._percentage_widget:
            self._percentage_widget.update("0%")

    def complete(self) -> None:
        """Mark progress as complete."""
        self.update_progress(self.total)
        if self._label_widget:
            self._label_widget.update(f" {self.label}")
            self._label_widget.add_class("complete")

    def set_indeterminate(self, active: bool = True) -> None:
        """Set progress bar to indeterminate mode."""
        if self._progress_bar:
            if active:
                self._progress_bar.update(total=None)
                if self._percentage_widget:
                    self._percentage_widget.update("...")
            else:
                self._progress_bar.update(total=self.total)
                self.update_progress(self.progress)
