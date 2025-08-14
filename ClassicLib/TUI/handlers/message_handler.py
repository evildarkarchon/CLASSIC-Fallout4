"""TUI-specific message handler implementation."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ClassicLib.MessageHandler import MessageHandler


class TuiMessageHandler(MessageHandler):
    """Routes messages to appropriate TUI widgets."""

    def __init__(self, output_widget=None):
        """Initialize TUI message handler.

        Args:
            output_widget: The output viewer widget to send messages to
        """
        super().__init__(parent=None, is_gui_mode=False)
        self.output_widget = output_widget

    def set_output_widget(self, widget) -> None:
        """Set the output widget for message routing."""
        self.output_widget = widget

    def _send_to_output(self, message: str, style: str | None = None) -> None:
        """Send message to output widget if available."""
        if self.output_widget and hasattr(self.output_widget, "append_output"):
            self.output_widget.append_output(message, style=style)
        else:
            # Fallback to console output
            print(message)

    def show_message(self, message: str, title: str = "") -> None:
        """Show an information message."""
        if title:
            self._send_to_output(f"ℹ️ {title}: {message}", style="info")
        else:
            self._send_to_output(f"ℹ️ {message}", style="info")

    def show_warning(self, message: str, title: str = "Warning") -> None:
        """Show a warning message."""
        self._send_to_output(f"⚠️ {title}: {message}", style="warning")

    def show_error(self, message: str, title: str = "Error") -> None:
        """Show an error message."""
        self._send_to_output(f"❌ {title}: {message}", style="error")

    def show_success(self, message: str, title: str = "") -> None:
        """Show a success message."""
        if title:
            self._send_to_output(f"✅ {title}: {message}", style="success")
        else:
            self._send_to_output(f"✅ {message}", style="success")

    def ask_yes_no(self, message: str, title: str = "Question") -> bool:
        """Ask a yes/no question.

        Note: In TUI mode, this currently defaults to 'yes' as modal dialogs
        are not yet implemented. This should be enhanced in future versions.
        """
        self._send_to_output(f"❓ {title}: {message} [Auto-answering: Yes]", style="info")
        return True

    def ask_ok_cancel(self, message: str, title: str = "Confirm") -> bool:
        """Ask for OK/Cancel confirmation.

        Note: In TUI mode, this currently defaults to 'OK' as modal dialogs
        are not yet implemented. This should be enhanced in future versions.
        """
        self._send_to_output(f"❓ {title}: {message} [Auto-confirming: OK]", style="info")
        return True

    def show_progress(self, message: str, value: int = 0, maximum: int = 100) -> None:
        """Show progress information."""
        percentage = int((value / maximum) * 100) if maximum > 0 else 0
        self._send_to_output(f"📊 {message} ({percentage}%)", style=None)

    def log_output(self, text: str) -> None:
        """Log output text."""
        self._send_to_output(text, style=None)

    def clear_output(self) -> None:
        """Clear the output display."""
        if self.output_widget and hasattr(self.output_widget, "clear"):
            self.output_widget.clear()

    @staticmethod
    def format_list(items: list, bullet: str = "•") -> str:
        """Format a list of items for display."""
        return "\n".join(f"  {bullet} {item}" for item in items)

    @staticmethod
    def format_table(data: list[list], headers: list | None = None) -> str:
        """Format data as a simple table."""
        if not data:
            return ""

        # Calculate column widths
        if headers:
            all_rows = [headers] + data
        else:
            all_rows = data

        col_widths = []
        for col_idx in range(len(all_rows[0])):
            max_width = max(len(str(row[col_idx])) for row in all_rows)
            col_widths.append(max_width)

        # Format table
        lines = []

        # Add headers if provided
        if headers:
            header_line = " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths, strict=False))
            lines.append(header_line)
            lines.append("-" * len(header_line))

        # Add data rows
        for row in data:
            row_line = " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths, strict=False))
            lines.append(row_line)

        return "\n".join(lines)
