"""Factory class and methods for creating settings dialog tabs in a PySide6 GUI application.

This module provides the `TabCreator` class, which includes static methods to generate
different tabs in a settings dialog. Each tab is implemented as a QWidget with a set of
associated settings widgets. These settings widgets allow users to configure various
preferences for the application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from ClassicLib.Interface.Settings.path_manager import PathManager


def get_game_version_options() -> list[tuple[str, str]]:
    """Get game version options from the VersionRegistry.

    Dynamically generates version options for the Game Version dropdown
    by querying the VersionRegistry. This ensures that if new versions
    are added to the registry, they will automatically appear in the UI.

    Returns:
        List of tuples containing (display_name, value_to_store) for each version.
        Always includes "Auto-detect" as the first option.

    Example:
        >>> options = get_game_version_options()
        >>> options[0]
        ('Auto-detect', 'auto')
        >>> # Subsequent options come from VersionRegistry

    """
    from ClassicLib.Logger import logger
    from ClassicLib.VersionRegistry import get_version_registry

    # Always start with Auto-detect option
    options: list[tuple[str, str]] = [("Auto-detect", "auto")]

    try:
        registry = get_version_registry()

        # Get all versions for Fallout4, sorted by priority (descending)
        all_versions = registry.get_all()

        for version_info in all_versions:
            if version_info.deprecated:
                continue  # Skip deprecated versions

            # Format: "Display Name (version)" -> short_name
            display_version = version_info.version_string
            display_name = f"{version_info.display_name or version_info.short_name} ({display_version})"
            # Use short_name as the stored value (Original, NextGen, VR, etc.)
            # Map to expected values for backward compatibility
            value = version_info.short_name
            if value == "OG":
                value = "Original"
            elif value == "NG":
                value = "NextGen"
            # VR stays as "VR"

            options.append((display_name, value))

    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to load version options from registry: {e}, using defaults")
        # Fallback to hardcoded defaults if registry fails
        options.extend([
            ("Fallout 4 Original (1.10.163.0)", "Original"),
            ("Fallout 4 Next-Gen (1.10.984.0)", "NextGen"),
            ("Fallout 4 VR (1.2.72.0)", "VR"),
        ])

    return options


def get_version_tooltip() -> str:
    """Generate version tooltip dynamically from VersionRegistry.

    Creates a tooltip string describing available Fallout 4 versions
    by querying the VersionRegistry for display names and version strings.

    Returns:
        Formatted tooltip string for the Game Version dropdown.

    """
    from ClassicLib.Logger import logger
    from ClassicLib.VersionRegistry import get_version_registry

    # Build tooltip dynamically
    tooltip_lines = ["Select your Fallout 4 version:", "• Auto-detect - Automatically determine version from game files"]

    try:
        registry = get_version_registry()
        for version_info in registry.get_all():
            if version_info.deprecated:
                continue
            # Format: "• Display Name - Description (version)"
            version_str = version_info.version_string
            display = version_info.display_name or version_info.short_name
            desc = version_info.description or ""
            if desc:
                tooltip_lines.append(f"• {display} - {desc} ({version_str})")
            else:
                tooltip_lines.append(f"• {display} ({version_str})")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Failed to generate version tooltip from registry: {e}")
        # Fallback to hardcoded tooltip
        tooltip_lines.extend([
            "• Original - Pre-Next-Gen update version (1.10.163)",
            "• Next-Gen - Next-Gen update version (1.10.984)",
            "• VR - Fallout 4 VR (1.2.72)",
        ])

    return "\n".join(tooltip_lines)


# Version options for Game Version dropdown - loaded dynamically
# This is called at module load time; if VersionRegistry isn't available yet,
# it will use fallback defaults
GAME_VERSION_OPTIONS: list[tuple[str, str]] = []
_VERSION_TOOLTIP: str = ""


def ensure_game_version_options() -> list[tuple[str, str]]:
    """Ensure GAME_VERSION_OPTIONS is populated.

    Lazily loads the version options on first access to avoid import-time
    issues with VersionRegistry initialization.

    Returns:
        List of game version options.

    """
    global GAME_VERSION_OPTIONS  # noqa: PLW0603
    if not GAME_VERSION_OPTIONS:
        GAME_VERSION_OPTIONS = get_game_version_options()
    return GAME_VERSION_OPTIONS


def ensure_version_tooltip() -> str:
    """Ensure the version tooltip is populated.

    Lazily generates the tooltip on first access.

    Returns:
        The version tooltip string.

    """
    global _VERSION_TOOLTIP  # noqa: PLW0603
    if not _VERSION_TOOLTIP:
        _VERSION_TOOLTIP = get_version_tooltip()
    return _VERSION_TOOLTIP


class TabCreator:
    """A utility class for creating and organizing settings tabs in a graphical user interface.

    This class provides methods for generating various tabs, such as General settings, Scanning settings,
    Paths settings, and Updates settings. Each method dynamically constructs the required widgets and layouts,
    associating user input widgets with logical settings for seamless user configuration.
    """

    @staticmethod
    def create_general_tab(parent: QWidget | None = None) -> tuple[QWidget, dict[str, QWidget]]:
        """Create the general settings tab UI with specific settings widgets.

        The method initializes a QWidget containing a layout for general settings
        and populates it with a dropdown for game version selection. The created
        widgets are arranged into a group box with appropriate spacing and tooltips.

        Args:
            parent (QWidget | None): Parent widget to which the general settings
                tab belongs. It can be None.

        Returns:
            tuple[QWidget, dict[str, QWidget]]: A tuple containing the general
                settings QWidget and a dictionary that maps string keys to
                their corresponding widget instances for programmatic access.

        """
        general_widget = QWidget(parent)
        layout = QVBoxLayout(general_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        settings_widgets = {}

        # Create general settings group
        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout(general_group)
        general_layout.setSpacing(10)

        # Game Version dropdown (replaces VR Mode checkbox)
        version_layout = QHBoxLayout()
        version_layout.setSpacing(10)

        version_label = QLabel("Game Version:")
        # Use dynamically generated tooltip from VersionRegistry
        version_label.setToolTip(ensure_version_tooltip())
        version_layout.addWidget(version_label)

        game_version_combo = QComboBox()
        # Load version options dynamically from VersionRegistry
        version_options = ensure_game_version_options()
        for display_name, _value in version_options:
            game_version_combo.addItem(display_name)
        game_version_combo.setToolTip(
            "Choose which Fallout 4 version to use for scanning and checks.\nAuto-detect will determine the version from your game files."
        )
        version_layout.addWidget(game_version_combo)
        version_layout.addStretch()

        general_layout.addLayout(version_layout)
        settings_widgets["game_version"] = game_version_combo

        layout.addWidget(general_group)
        layout.addStretch()

        return general_widget, settings_widgets

    @staticmethod
    def create_scanning_tab(parent: QWidget | None = None) -> tuple[QWidget, dict[str, QWidget]]:
        """Create a scanning settings tab with various options and their corresponding widgets.

        Returns a QWidget containing the layout and the created settings widgets. The method initializes
        a group of checkboxes to allow the user to customize scanning options. Each checkbox comes with
        a descriptive tooltip to indicate its functional implications.

        Args:
            parent (QWidget | None): The parent widget for the created scanning tab, or None if no parent is specified.

        Returns:
            tuple[QWidget, dict[str, QWidget]]: A tuple containing the root QWidget for the scanning tab and
            a dictionary mapping widget keys to the corresponding QWidgets.

        """
        scanning_widget = QWidget(parent)
        layout = QVBoxLayout(scanning_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        settings_widgets = {}

        # Create scanning settings group
        scanning_group = QGroupBox("Scanning Options")
        scanning_layout = QVBoxLayout(scanning_group)
        scanning_layout.setSpacing(10)

        # FCX Mode checkbox
        fcx_checkbox = QCheckBox("FCX Mode")
        fcx_checkbox.setToolTip("Enable extended file integrity checks for more thorough scanning")
        scanning_layout.addWidget(fcx_checkbox)
        settings_widgets["fcx_mode"] = fcx_checkbox

        # Simplify Logs checkbox
        simplify_checkbox = QCheckBox("Simplify Logs")
        simplify_checkbox.setToolTip("Remove redundant and repetitive lines from crash logs for easier reading")
        scanning_layout.addWidget(simplify_checkbox)
        settings_widgets["simplify_logs"] = simplify_checkbox

        # Show FID Values checkbox
        show_fid_checkbox = QCheckBox("Show FID Values")
        show_fid_checkbox.setToolTip("Look up FormID names during scan (slower but more informative)")
        scanning_layout.addWidget(show_fid_checkbox)
        settings_widgets["show_fid_values"] = show_fid_checkbox

        # Move Invalid Logs checkbox
        move_invalid_checkbox = QCheckBox("Move Invalid Logs")
        move_invalid_checkbox.setToolTip("Automatically move incomplete or unscannable logs to a separate folder")
        scanning_layout.addWidget(move_invalid_checkbox)
        settings_widgets["move_invalid_logs"] = move_invalid_checkbox

        # Auto-Switch to Results checkbox
        auto_switch_checkbox = QCheckBox("Auto-Switch to Results Tab")
        auto_switch_checkbox.setToolTip("Automatically switch to the Results tab after a scan completes")
        scanning_layout.addWidget(auto_switch_checkbox)
        settings_widgets["auto_switch_results"] = auto_switch_checkbox

        layout.addWidget(scanning_group)
        layout.addStretch()

        return scanning_widget, settings_widgets

    @staticmethod
    def create_paths_tab(parent: QWidget | None, path_manager: PathManager) -> tuple[QWidget, dict[str, QWidget]]:
        """Create the Paths tab within a user interface and returns the created widget
        along with a dictionary of specific settings widgets.

        This function initializes a settings widget for managing file paths, particularly the
        INI folder path required by the application. Users can manually input the path, use
        automatic detection, or browse their file system to locate the desired folder. It also
        provides an optional reset functionality to rollback to default settings. A help text
        offers guidance for cases where file detection fails.

        Args:
            parent (QWidget | None): The parent widget for the paths tab. If None, the
                paths tab will not have a parent.
            path_manager (PathManager): Instance for managing, validating, and resetting
                file path configurations.

        Returns:
            tuple[QWidget, dict[str, QWidget]]: A tuple containing the created paths tab
                widget and a dictionary of individual path-related widgets. Each dictionary
                key is the name of the setting, and the value is the corresponding widget.

        """
        paths_widget = QWidget(parent)
        layout = QVBoxLayout(paths_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        settings_widgets = {}

        # Create paths settings group
        paths_group = QGroupBox("Path Settings")
        paths_layout = QVBoxLayout(paths_group)
        paths_layout.setSpacing(15)

        # INI Folder Path setting
        ini_path_label = QLabel("INI Folder Path:")
        ini_path_label.setToolTip("Path to your game's INI files directory\nUsually located in Documents/My Games/[Game Name]")
        paths_layout.addWidget(ini_path_label)

        # Create horizontal layout for input and browse button
        ini_path_layout = QHBoxLayout()
        ini_path_layout.setSpacing(10)

        ini_folder_input = QLineEdit()
        ini_folder_input.setPlaceholderText("Enter INI folder path or click Browse...")
        ini_folder_input.setToolTip(
            "Specify the folder containing your game's INI configuration files\nLeave empty to use automatic detection"
        )
        ini_path_layout.addWidget(ini_folder_input)
        settings_widgets["ini_folder_path"] = ini_folder_input

        # Set the input widget reference in path manager
        path_manager.set_ini_folder_input(ini_folder_input)

        # Reset button for INI folder
        ini_reset_button = QPushButton("Reset")
        ini_reset_button.setToolTip("Reset to auto-detected INI folder location")
        ini_reset_button.setMaximumWidth(80)
        ini_reset_button.clicked.connect(path_manager.reset_ini_folder)
        ini_path_layout.addWidget(ini_reset_button)

        # Browse button for INI folder
        ini_browse_button = QPushButton("Browse...")
        ini_browse_button.setToolTip("Browse for INI folder location")
        ini_browse_button.setMaximumWidth(100)
        ini_browse_button.clicked.connect(path_manager.browse_ini_folder)
        ini_path_layout.addWidget(ini_browse_button)

        paths_layout.addLayout(ini_path_layout)

        # Help text
        help_label = QLabel(
            "If CLASSIC has trouble detecting your game files, specify the INI folder manually.\n"
            "This is typically found in your Documents folder under 'My Games'."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("QLabel { color: #888888; font-size: 11px; }")
        paths_layout.addWidget(help_label)

        layout.addWidget(paths_group)
        layout.addStretch()

        return paths_widget, settings_widgets

    @staticmethod
    def create_updates_tab(parent: QWidget | None = None) -> tuple[QWidget, dict[str, QWidget], QPushButton]:
        """Create and configures the 'Updates' tab within the application.

        This method generates a QWidget containing the layout and widgets for update
        settings, including a checkbox for enabling updates, a combo box for selecting
        the update source, and a button to check for updates immediately. The method
        returns the widget, a dictionary of the settings widgets, and the "Check for
        Updates Now" button.

        Args:
            parent (QWidget | None): The parent widget for the updates widget.
                Defaults to None.

        Returns:
            tuple[QWidget, dict[str, QWidget], QPushButton]: A tuple containing the
            updates widget, a dictionary of update settings widgets, and the "Check
            for Updates Now" button.

        """
        updates_widget = QWidget(parent)
        layout = QVBoxLayout(updates_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        settings_widgets = {}

        # Create update settings group
        updates_group = QGroupBox("Update Settings")
        updates_layout = QVBoxLayout(updates_group)
        updates_layout.setSpacing(15)

        # Update Check checkbox
        update_check_checkbox = QCheckBox("Check for Updates")
        update_check_checkbox.setToolTip("Automatically check for CLASSIC updates on startup")
        updates_layout.addWidget(update_check_checkbox)
        settings_widgets["update_check"] = update_check_checkbox

        # Update Source selection
        source_layout = QHBoxLayout()
        source_layout.setSpacing(10)

        source_label = QLabel("Update Source:")
        source_label.setToolTip("Choose where to check for updates")
        source_layout.addWidget(source_label)

        update_source_combo = QComboBox()
        update_source_combo.addItems(["Nexus", "GitHub", "Both"])
        update_source_combo.setToolTip(
            "Select which source to check for updates:\n"
            "• Nexus - Check Nexus Mods for updates\n"
            "• GitHub - Check GitHub releases for updates\n"
            "• Both - Check both sources"
        )
        source_layout.addWidget(update_source_combo)
        source_layout.addStretch()

        updates_layout.addLayout(source_layout)
        settings_widgets["update_source"] = update_source_combo

        # Check Now button
        check_now_button = QPushButton("Check for Updates Now")
        check_now_button.setToolTip("Immediately check for available updates")
        check_now_button.setMaximumWidth(200)
        updates_layout.addWidget(check_now_button)

        layout.addWidget(updates_group)
        layout.addStretch()

        # Return the button separately so it can be connected in the main dialog
        return updates_widget, settings_widgets, check_now_button
