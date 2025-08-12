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
        Updates statistical data and UI elements with the given stats object.

        This method updates UI elements such as labels and status indicators with the
        latest statistics provided in the `stats` parameter. It processes various
        metrics, including dump counts, stack counts, dump-stack ratios, and warning
        and error counts. Additionally, it invokes helper methods to update status
        indicators and messages based on the state of the provided stats.

        Parameters
        ----------
        stats : PapyrusStats
            An object containing the latest statistics, including metrics such as
            timestamp, dumps, stacks, ratio, warnings, and errors.
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
        Updates the status indicators for various statistical metrics based on the provided
        statistics data. This function modifies the appearance and text of relevant status
        indicators to reflect the current state of the statistics. The status indicators
        use icons and color coding to provide a visual representation of the statistical metrics.

        Parameters:
            stats (PapyrusStats): The statistics object containing the data to be represented
            in the status indicators.
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
        Updates the message label based on the statistics provided by the PapyrusStats object.

        This method evaluates errors, warnings, and the dumps-to-stacks ratio from the
        given PapyrusStats instance and updates the message label's text and style
        accordingly. If the number of errors is greater than zero, an error message
        will be displayed in bold red. If there are warnings, a warning message will
        be displayed in bold orange. If the ratio exceeds specific thresholds, caution
        or warning messages will be displayed. If no issues are detected, the log is
        considered normal and the label is updated with this information in green.

        Parameters:
            stats (PapyrusStats): The statistics object containing error counts, warning
                counts, and the dumps-to-stacks ratio to analyze.

        Returns:
            None
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
        Emits a signal to stop monitoring and closes the dialog.

        This method is intended to be connected to a user action, such as clicking a
        stop button. It emits a signal to indicate monitoring should be stopped and
        subsequently closes the dialog by invoking the `accept` function.

        Raises:
            None
        Returns:
            None
        """
        self.stop_monitoring.emit()
        self.accept()

    def handle_error(self, error_msg: str) -> None:
        """
        Handles the display of an error message in the user interface by updating the
        text and style of a message label to indicate an error visually. It sets the
        label's text to include the given error message and changes its appearance to
        red, bold text for clearer visibility to the user.

        Args:
            error_msg: The error message to be displayed on the message label.
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
