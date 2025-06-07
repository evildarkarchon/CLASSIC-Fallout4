from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ClassicLib.Interface.Papyrus import PapyrusStats


class PapyrusMonitorDialog(QDialog):
    """
    A custom dialog that displays real-time statistics from Papyrus log monitoring.

    This dialog presents Papyrus statistics in an organized layout, updating in real-time
    as new stats are received. It includes counters for dumps, stacks, warnings, and errors,
    along with derived metrics like the dumps-to-stacks ratio. The dialog provides a stop
    button to halt monitoring and handles proper cleanup when closed.

    Attributes:
        stop_monitoring (Signal): Signal emitted when monitoring should be stopped.
    """

    stop_monitoring = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the Papyrus Monitor Dialog.

        Sets up the UI components including labels for statistics, a timestamp display,
        and a stop button.

        Args:
            parent: The parent widget for this dialog
        """
        super().__init__(parent)
        self.setWindowTitle("Papyrus Log Monitor")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)  # Use a simpler approach - just use standard dialog flags
        self.setWindowFlags(Qt.WindowType.Dialog)

        # Create the main layout
        main_layout = QVBoxLayout(self)

        # Create title label
        title_label = QLabel("Papyrus Log Monitoring")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)  # Add timestamp label
        self.timestamp_label = QLabel()
        self.timestamp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.timestamp_label)

        # Create a grid layout for the stats
        stats_layout = QGridLayout()
        stats_layout.setSpacing(10)

        # Create and add labels for stats
        # Headers row
        stats_layout.addWidget(QLabel("<b>Metric</b>"), 0, 0)
        stats_layout.addWidget(QLabel("<b>Value</b>"), 0, 1)
        stats_layout.addWidget(QLabel("<b>Status</b>"), 0, 2)  # Data rows with labels
        stat_labels: list[str] = ["Dumps", "Stacks", "Dumps/Stacks Ratio", "Warnings", "Errors"]
        self.stat_value_labels = {}
        self.stat_status_labels = {}

        for row, label_text in enumerate(stat_labels, 1):
            # Label
            label = QLabel(label_text)
            stats_layout.addWidget(label, row, 0)  # Value
            value_label = QLabel("0")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Create a safe key for the dictionary
            key: str = label_text.lower().replace("/", "_").replace(" ", "_")
            self.stat_value_labels[key] = value_label
            stats_layout.addWidget(value_label, row, 1)  # Status
            status_label = QLabel("✓")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Use the same key format for consistency
            key = label_text.lower().replace("/", "_").replace(" ", "_")
            self.stat_status_labels[key] = status_label
            stats_layout.addWidget(status_label, row, 2)

        main_layout.addLayout(stats_layout)  # Add a message label for errors or info
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.message_label)

        # Add a spacer to push everything up
        main_layout.addStretch(1)

        # Add a button to stop monitoring
        button_layout = QHBoxLayout()
        self.stop_button = QPushButton("Stop Monitoring")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        button_layout.addWidget(self.stop_button)
        main_layout.addLayout(button_layout)

        # Initialize with default values
        self.update_stats(PapyrusStats(timestamp=datetime.now(), dumps=0, stacks=0, warnings=0, errors=0, ratio=0.0))

    def update_stats(self, stats: PapyrusStats) -> None:
        """
        Update the dialog with new statistics.

        Args:
            stats: The PapyrusStats object containing the current statistics
        """
        # Update timestamp
        self.timestamp_label.setText(f"Last Updated: {stats.timestamp.strftime('%H:%M:%S')}")  # Update stat values
        self.stat_value_labels["dumps"].setText(str(stats.dumps))
        self.stat_value_labels["stacks"].setText(str(stats.stacks))
        # Use the same key format we've established
        self.stat_value_labels["dumps_stacks_ratio"].setText(f"{stats.ratio:.3f}")
        self.stat_value_labels["warnings"].setText(str(stats.warnings))
        self.stat_value_labels["errors"].setText(str(stats.errors))

        # Update status indicators
        self._update_status_indicators(stats)

        # Check for errors or warnings and update message
        self._update_message(stats)

    def _update_status_indicators(self, stats: PapyrusStats) -> None:
        """
        Update the status indicators based on the current statistics.

        Args:
            stats: The PapyrusStats object containing the current statistics
        """  # A high ratio is bad
        if stats.ratio > 0.8:
            self.stat_status_labels["dumps_stacks_ratio"].setText("❌")
            self.stat_status_labels["dumps_stacks_ratio"].setStyleSheet("color: red;")
        elif stats.ratio > 0.5:
            self.stat_status_labels["dumps_stacks_ratio"].setText("⚠️")
            self.stat_status_labels["dumps_stacks_ratio"].setStyleSheet("color: orange;")
        else:
            self.stat_status_labels["dumps_stacks_ratio"].setText("✓")
            self.stat_status_labels["dumps_stacks_ratio"].setStyleSheet("color: green;")

        # Warnings
        if stats.warnings > 0:
            self.stat_status_labels["warnings"].setText("⚠️")
            self.stat_status_labels["warnings"].setStyleSheet("color: orange;")
        else:
            self.stat_status_labels["warnings"].setText("✓")
            self.stat_status_labels["warnings"].setStyleSheet("color: green;")

        # Errors
        if stats.errors > 0:
            self.stat_status_labels["errors"].setText("❌")
            self.stat_status_labels["errors"].setStyleSheet("color: red;")
        else:
            self.stat_status_labels["errors"].setText("✓")
            self.stat_status_labels["errors"].setStyleSheet("color: green;")

    def _update_message(self, stats: PapyrusStats) -> None:
        """
        Update the message label based on the current statistics.

        Args:
            stats: The PapyrusStats object containing the current statistics
        """
        if stats.errors > 0:
            self.message_label.setText(f"{stats.errors} errors detected in Papyrus log!")
            self.message_label.setStyleSheet("color: red; font-weight: bold;")
        elif stats.warnings > 0:
            self.message_label.setText(f"{stats.warnings} warnings detected in Papyrus log.")
            self.message_label.setStyleSheet("color: orange; font-weight: bold;")
        elif stats.ratio > 0.8:
            self.message_label.setText("Warning: High dumps-to-stacks ratio detected!")
            self.message_label.setStyleSheet("color: red; font-weight: bold;")
        elif stats.ratio > 0.5:
            self.message_label.setText("Caution: Elevated dumps-to-stacks ratio.")
            self.message_label.setStyleSheet("color: orange;")
        else:
            self.message_label.setText("Papyrus log appears normal.")
            self.message_label.setStyleSheet("color: green;")

    def on_stop_clicked(self) -> None:
        """
        Handle the stop button click.

        Emits the stop_monitoring signal and closes the dialog.
        """
        self.stop_monitoring.emit()
        self.accept()

    def handle_error(self, error_msg: str) -> None:
        """
        Handle errors from the Papyrus monitor.

        Args:
            error_msg: The error message to display
        """
        self.message_label.setText(f"Error: {error_msg}")
        self.message_label.setStyleSheet("color: red; font-weight: bold;")

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handle the dialog close event.

        Ensures that monitoring is stopped when the dialog is closed.

        Args:
            event: The close event
        """
        self.stop_monitoring.emit()
        event.accept()
