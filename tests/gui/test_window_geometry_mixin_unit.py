"""
Unit tests for WindowGeometryMixin module.

This module tests window geometry management for tab-specific sizing,
including save/restore functionality, minimum size calculations, and
window state handling with properly mocked Qt components.
"""

from pathlib import Path
from unittest.mock import ANY, MagicMock, Mock, call, patch

import pytest

from ClassicLib.Interface.WindowGeometryMixin import WindowGeometryMixin


@pytest.mark.unit
@pytest.mark.gui
class TestWindowGeometryMixin:
    """Unit tests for WindowGeometryMixin class."""

    @pytest.fixture
    def mock_qt_window(self):
        """Create a mock window class with WindowGeometryMixin and mocked Qt components."""
        # Create test class that includes the mixin with fully mocked Qt dependencies
        class TestWindow(WindowGeometryMixin):
            """Test window class with mocked Qt components."""

            def __init__(self):
                # Initialize mock Qt components
                self.tab_widget = MagicMock()
                self.tab_widget.currentIndex.return_value = 0
                self.tab_widget.currentChanged = MagicMock()
                self.tab_widget.currentChanged.connect = MagicMock()

                # Mock window methods
                self._mock_size = MagicMock()
                self._mock_size.width.return_value = 800
                self._mock_size.height.return_value = 600

                self._mock_normal_geometry = MagicMock()
                self._mock_normal_geometry.width.return_value = 700
                self._mock_normal_geometry.height.return_value = 500

                self._window_state = 0  # Normal state
                self._maximized = False

                # Initialize the mixin
                super().__init__()

            def size(self):
                """Mock size method."""
                return self._mock_size

            def windowState(self):
                """Mock windowState method."""
                return self._window_state

            def showMaximized(self):
                """Mock showMaximized method."""
                self._maximized = True

            def showNormal(self):
                """Mock showNormal method."""
                self._maximized = False

            def normalGeometry(self):
                """Mock normalGeometry method."""
                return self._mock_normal_geometry

            def setMinimumSize(self, width, height):
                """Mock setMinimumSize method."""
                self.min_width = width
                self.min_height = height

            def resize(self, width, height):
                """Mock resize method."""
                self.resized_width = width
                self.resized_height = height

        return TestWindow()

    @pytest.fixture
    def mock_qt_disabled(self):
        """Create a window with Qt disabled (Qt = None)."""
        class TestWindowNoQt(WindowGeometryMixin):
            def __init__(self):
                self.tab_widget = MagicMock()
                self.tab_widget.currentIndex.return_value = 0
                self.tab_widget.currentChanged = MagicMock()
                self.tab_widget.currentChanged.connect = MagicMock()

                super().__init__()

            def size(self):
                mock_size = MagicMock()
                mock_size.width.return_value = 800
                mock_size.height.return_value = 600
                return mock_size

            def setMinimumSize(self, width, height):
                self.min_width = width
                self.min_height = height

            def resize(self, width, height):
                self.resized_width = width
                self.resized_height = height

        # Mock Qt as None to simulate disabled Qt
        with patch("ClassicLib.Interface.WindowGeometryMixin.Qt", None):
            return TestWindowNoQt()


class TestWindowGeometryInitialization:
    """Test window geometry initialization and setup."""

    def test_mixin_initialization(self, mock_qt_window):
        """Test that the mixin initializes with correct default values."""
        assert mock_qt_window._last_tab_index is None
        assert mock_qt_window._geometry_initialized is False

    def test_setup_window_geometry_success(self, mock_qt_window):
        """Test successful window geometry setup."""
        with patch.object(mock_qt_window, 'restore_tab_geometry') as mock_restore:
            mock_qt_window.setup_window_geometry()

            # Verify connection was made to tab change signal
            mock_qt_window.tab_widget.currentChanged.connect.assert_called_once_with(
                mock_qt_window.handle_tab_changed
            )

            # Verify initial geometry was restored
            mock_restore.assert_called_once_with(0)

            # Verify initialization state
            assert mock_qt_window._last_tab_index == 0
            assert mock_qt_window._geometry_initialized is True

    def test_setup_window_geometry_no_tab_widget(self, mock_qt_window):
        """Test setup when tab widget is missing."""
        # Remove tab widget to simulate missing widget
        del mock_qt_window.tab_widget

        with patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:
            mock_qt_window.setup_window_geometry()

            # Should log warning and return early
            mock_logger.warning.assert_called_once_with(
                "Tab widget not found, skipping geometry setup"
            )

            # Should not initialize
            assert mock_qt_window._geometry_initialized is False

    def test_handle_tab_changed_not_initialized(self, mock_qt_window):
        """Test tab change handling when not initialized."""
        # Should return early if not initialized
        with patch.object(mock_qt_window, 'save_tab_geometry') as mock_save, \
             patch.object(mock_qt_window, 'restore_tab_geometry') as mock_restore:

            mock_qt_window.handle_tab_changed(1)

            # No operations should be performed
            mock_save.assert_not_called()
            mock_restore.assert_not_called()

    def test_handle_tab_changed_initialized(self, mock_qt_window):
        """Test tab change handling when initialized."""
        # Setup initialized state
        mock_qt_window._geometry_initialized = True
        mock_qt_window._last_tab_index = 0

        with patch.object(mock_qt_window, 'save_tab_geometry') as mock_save, \
             patch.object(mock_qt_window, 'restore_tab_geometry') as mock_restore, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

            mock_qt_window.handle_tab_changed(2)

            # Should save previous tab geometry
            mock_save.assert_called_once_with(0)

            # Should restore new tab geometry
            mock_restore.assert_called_once_with(2)

            # Should update last tab index
            assert mock_qt_window._last_tab_index == 2

            # Should log the change
            mock_logger.debug.assert_called_once()
            debug_call = mock_logger.debug.call_args[0][0]
            assert "Switched to tab 2" in debug_call


class TestTabGeometrySaving:
    """Test saving tab geometry functionality."""

    def test_save_tab_geometry_invalid_index(self, mock_qt_window):
        """Test saving geometry for invalid tab index."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:
            mock_qt_window.save_tab_geometry(999)  # Invalid index

            # No settings should be saved
            mock_yaml.assert_not_called()

    def test_save_tab_geometry_normal_window(self, mock_qt_window):
        """Test saving geometry for normal (non-maximized) window."""
        mock_qt_window._window_state = 0  # Normal state

        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

            mock_qt_window.save_tab_geometry(0)  # Main tab

            # Should save current size
            expected_calls = [
                call(bool, ANY, "UI.window_geometry.main_tab.maximized", False),
                call(int, ANY, "UI.window_geometry.main_tab.width", 800),
                call(int, ANY, "UI.window_geometry.main_tab.height", 600)
            ]

            assert mock_yaml.call_count == 3
            for expected_call in expected_calls:
                assert expected_call in mock_yaml.call_args_list

            # Should log the save operation
            mock_logger.debug.assert_called_once()
            debug_msg = mock_logger.debug.call_args[0][0]
            assert "Saved geometry for main_tab: 800x600" in debug_msg

    def test_save_tab_geometry_maximized_window_with_normal_geometry(self, mock_qt_window):
        """Test saving geometry for maximized window with normal geometry available."""
        # Mock WindowMaximized state
        with patch("ClassicLib.Interface.WindowGeometryMixin.Qt") as mock_qt:
            mock_qt.WindowState.WindowMaximized = 2
            mock_qt_window._window_state = 2  # Maximized

            with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
                 patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

                mock_qt_window.save_tab_geometry(1)  # Backups tab

                # Should save normal geometry and maximized state
                expected_calls = [
                    call(bool, ANY, "UI.window_geometry.backups_tab.maximized", True),
                    call(int, ANY, "UI.window_geometry.backups_tab.width", 700),  # Normal geometry
                    call(int, ANY, "UI.window_geometry.backups_tab.height", 500)
                ]

                assert mock_yaml.call_count == 3
                for expected_call in expected_calls:
                    assert expected_call in mock_yaml.call_args_list

                # Should log normal geometry was saved
                mock_logger.debug.assert_called_once()
                debug_msg = mock_logger.debug.call_args[0][0]
                assert "normal geometry" in debug_msg.lower()

    def test_save_tab_geometry_maximized_window_no_normal_geometry(self, mock_qt_window):
        """Test saving geometry for maximized window without normal geometry."""
        # Remove normalGeometry method to simulate fallback
        del mock_qt_window.normalGeometry

        with patch("ClassicLib.Interface.WindowGeometryMixin.Qt") as mock_qt:
            mock_qt.WindowState.WindowMaximized = 2
            mock_qt_window._window_state = 2  # Maximized

            with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
                 patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

                mock_qt_window.save_tab_geometry(0)

                # Should save current size as fallback
                expected_calls = [
                    call(bool, ANY, "UI.window_geometry.main_tab.maximized", True),
                    call(int, ANY, "UI.window_geometry.main_tab.width", 800),  # Current size
                    call(int, ANY, "UI.window_geometry.main_tab.height", 600)
                ]

                assert mock_yaml.call_count == 3
                for expected_call in expected_calls:
                    assert expected_call in mock_yaml.call_args_list

                # Should log fallback was used
                mock_logger.debug.assert_called_once()
                debug_msg = mock_logger.debug.call_args[0][0]
                assert "no normal geometry available" in debug_msg.lower()

    def test_save_tab_geometry_qt_disabled(self, mock_qt_disabled):
        """Test saving geometry when Qt is disabled."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

            mock_qt_disabled.save_tab_geometry(0)

            # Should still save geometry, treating as normal window
            expected_calls = [
                call(bool, ANY, "UI.window_geometry.main_tab.maximized", False),
                call(int, ANY, "UI.window_geometry.main_tab.width", 800),
                call(int, ANY, "UI.window_geometry.main_tab.height", 600)
            ]

            assert mock_yaml.call_count == 3
            for expected_call in expected_calls:
                assert expected_call in mock_yaml.call_args_list


class TestTabGeometryRestoring:
    """Test restoring tab geometry functionality."""

    def test_restore_tab_geometry_invalid_index(self, mock_qt_window):
        """Test restoring geometry for invalid tab index."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:
            mock_qt_window.restore_tab_geometry(999)  # Invalid index

            # No settings should be accessed
            mock_yaml.assert_not_called()

    def test_restore_tab_geometry_no_saved_data(self, mock_qt_window):
        """Test restoring geometry when no saved data exists."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

            # Mock returning None for all saved settings
            mock_yaml.side_effect = lambda *args: None if len(args) > 3 else args[3]

            mock_qt_window.restore_tab_geometry(0)

            # Should use default minimum size
            assert mock_qt_window.min_width == 550  # Default for main tab
            assert mock_qt_window.min_height == 350

            # Should resize to minimum size
            assert mock_qt_window.resized_width == 550
            assert mock_qt_window.resized_height == 350

            # Should log default usage
            mock_logger.debug.assert_called()
            debug_msg = mock_logger.debug.call_args_list[-1][0][0]
            assert "Using default minimum size" in debug_msg

    def test_restore_tab_geometry_with_saved_data(self, mock_qt_window):
        """Test restoring geometry with saved data."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

            # Mock saved settings: width=900, height=700, not maximized
            def mock_settings(*args):
                if len(args) <= 3:  # Default value provided
                    return args[3] if len(args) > 3 else None

                key = args[2]
                if "width" in key:
                    return 900
                elif "height" in key:
                    return 700
                elif "maximized" in key:
                    return False
                return None

            mock_yaml.side_effect = mock_settings

            mock_qt_window.restore_tab_geometry(1)  # Backups tab

            # Should use larger of saved or minimum size
            expected_min_width, expected_min_height = 750, 450  # Backups tab minimum
            assert mock_qt_window.min_width == expected_min_width
            assert mock_qt_window.min_height == expected_min_height

            # Should resize to saved size (larger than minimum)
            assert mock_qt_window.resized_width == 900
            assert mock_qt_window.resized_height == 700

            # Should not be maximized
            assert not mock_qt_window._maximized

            # Should log restoration
            mock_logger.debug.assert_called()
            debug_msg = mock_logger.debug.call_args_list[-1][0][0]
            assert "Restoring saved geometry" in debug_msg

    def test_restore_tab_geometry_saved_smaller_than_minimum(self, mock_qt_window):
        """Test restoring geometry when saved size is smaller than minimum."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

            # Mock saved settings: very small size
            def mock_settings(*args):
                if len(args) <= 3:
                    return args[3] if len(args) > 3 else None

                key = args[2]
                if "width" in key:
                    return 200  # Smaller than minimum
                elif "height" in key:
                    return 100  # Smaller than minimum
                elif "maximized" in key:
                    return False
                return None

            mock_yaml.side_effect = mock_settings

            mock_qt_window.restore_tab_geometry(0)  # Main tab

            # Should enforce minimum size
            min_width, min_height = 550, 350  # Main tab minimum
            assert mock_qt_window.resized_width == min_width
            assert mock_qt_window.resized_height == min_height

    def test_restore_tab_geometry_maximized_state(self, mock_qt_window):
        """Test restoring geometry for a maximized window."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

            # Mock saved settings: maximized
            def mock_settings(*args):
                if len(args) <= 3:
                    return args[3] if len(args) > 3 else None

                key = args[2]
                if "width" in key:
                    return 800
                elif "height" in key:
                    return 600
                elif "maximized" in key:
                    return True  # Was maximized
                return None

            mock_yaml.side_effect = mock_settings

            mock_qt_window.restore_tab_geometry(0)

            # Should first resize to normal size
            assert mock_qt_window.resized_width == 800
            assert mock_qt_window.resized_height == 600

            # Should then maximize
            assert mock_qt_window._maximized

            # Should log maximized restoration
            mock_logger.debug.assert_called()
            debug_msg = mock_logger.debug.call_args_list[-1][0][0]
            assert "maximized state" in debug_msg.lower()

    def test_restore_tab_geometry_un_maximize_when_needed(self, mock_qt_window):
        """Test un-maximizing when restoring to normal state."""
        # Start with maximized window
        mock_qt_window._maximized = True
        mock_qt_window._window_state = 2  # Mock maximized state

        with patch("ClassicLib.Interface.WindowGeometryMixin.Qt") as mock_qt, \
             patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:

            mock_qt.WindowState.WindowMaximized = 2

            # Mock saved settings: not maximized
            def mock_settings(*args):
                if len(args) <= 3:
                    return args[3] if len(args) > 3 else None

                key = args[2]
                if "width" in key:
                    return 700
                elif "height" in key:
                    return 500
                elif "maximized" in key:
                    return False  # Should not be maximized
                return None

            mock_yaml.side_effect = mock_settings

            # Create additional mock methods for checking window state
            mock_qt_window.windowState = Mock(return_value=2)  # Currently maximized
            mock_qt_window.showNormal = Mock()

            mock_qt_window.restore_tab_geometry(0)

            # Should call showNormal to un-maximize
            mock_qt_window.showNormal.assert_called_once()


class TestMinimumSizeCalculation:
    """Test minimum size calculation functionality."""

    def test_get_minimum_size_for_known_tabs(self, mock_qt_window):
        """Test getting minimum sizes for known tab indices."""
        # Test all known tab indices
        expected_sizes = {
            0: (550, 350),  # Main Options tab
            1: (750, 450),  # File Backup tab
            2: (550, 350),  # Articles tab
            3: (750, 450),  # Results tab
        }

        for tab_index, expected_size in expected_sizes.items():
            width, height = mock_qt_window.get_minimum_size_for_tab(tab_index)
            assert (width, height) == expected_size

    def test_get_minimum_size_for_unknown_tab(self, mock_qt_window):
        """Test getting minimum size for unknown tab index."""
        # Unknown tab should get default size
        width, height = mock_qt_window.get_minimum_size_for_tab(999)
        assert (width, height) == (550, 350)  # Default size

    def test_default_min_sizes_constant(self):
        """Test that DEFAULT_MIN_SIZES constant is properly defined."""
        expected_defaults = {
            0: (550, 350),  # Main Options tab
            1: (750, 450),  # File Backup tab (larger)
            2: (550, 350),  # Articles tab
            3: (750, 450),  # Results tab
        }

        assert WindowGeometryMixin.DEFAULT_MIN_SIZES == expected_defaults

    def test_tab_names_constant(self):
        """Test that TAB_NAMES constant is properly defined."""
        expected_names = {
            0: "main_tab",
            1: "backups_tab",
            2: "articles_tab",
            3: "results_tab"
        }

        assert WindowGeometryMixin.TAB_NAMES == expected_names


class TestCurrentTabGeometrySaving:
    """Test saving geometry of the current tab."""

    def test_save_current_tab_geometry_initialized(self, mock_qt_window):
        """Test saving current tab geometry when initialized."""
        mock_qt_window._geometry_initialized = True
        mock_qt_window.tab_widget.currentIndex.return_value = 2

        with patch.object(mock_qt_window, 'save_tab_geometry') as mock_save, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

            mock_qt_window.save_current_tab_geometry()

            # Should save current tab
            mock_save.assert_called_once_with(2)

            # Should log the operation
            mock_logger.debug.assert_called_once()
            debug_msg = mock_logger.debug.call_args[0][0]
            assert "Saved final geometry for tab 2" in debug_msg

    def test_save_current_tab_geometry_not_initialized(self, mock_qt_window):
        """Test saving current tab geometry when not initialized."""
        mock_qt_window._geometry_initialized = False

        with patch.object(mock_qt_window, 'save_tab_geometry') as mock_save:
            mock_qt_window.save_current_tab_geometry()

            # Should not save anything
            mock_save.assert_not_called()

    def test_save_current_tab_geometry_no_tab_widget(self, mock_qt_window):
        """Test saving current tab geometry when tab widget is missing."""
        mock_qt_window._geometry_initialized = True
        del mock_qt_window.tab_widget

        with patch.object(mock_qt_window, 'save_tab_geometry') as mock_save:
            mock_qt_window.save_current_tab_geometry()

            # Should not save anything
            mock_save.assert_not_called()


class TestWindowGeometryIntegration:
    """Integration tests for window geometry management."""

    def test_complete_geometry_lifecycle(self, mock_qt_window):
        """Test complete lifecycle: setup -> tab change -> save current."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger"):

            # Mock no saved settings initially
            mock_yaml.side_effect = lambda *args: args[3] if len(args) > 3 else None

            # 1. Setup geometry
            mock_qt_window.setup_window_geometry()
            assert mock_qt_window._geometry_initialized is True
            assert mock_qt_window._last_tab_index == 0

            # 2. Simulate tab change
            mock_qt_window.handle_tab_changed(1)
            assert mock_qt_window._last_tab_index == 1

            # 3. Save current tab geometry
            mock_qt_window.save_current_tab_geometry()

            # Verify settings operations occurred
            assert mock_yaml.call_count > 0

    def test_geometry_persistence_across_sessions(self, mock_qt_window):
        """Test that geometry persists across simulated sessions."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger"):

            saved_geometry = {}

            def mock_save_setting(type_cls, yaml_enum, key, value):
                """Mock saving setting to persistent storage."""
                saved_geometry[key] = value

            def mock_load_setting(*args):
                """Mock loading setting from persistent storage."""
                if len(args) <= 3:
                    return args[3] if len(args) > 3 else None
                key = args[2]
                return saved_geometry.get(key, args[3] if len(args) > 3 else None)

            mock_yaml.side_effect = mock_save_setting

            # First session: save geometry
            mock_qt_window._geometry_initialized = True
            mock_qt_window._last_tab_index = 1
            mock_qt_window.save_tab_geometry(1)

            # Verify data was saved
            assert "UI.window_geometry.backups_tab.width" in saved_geometry
            assert "UI.window_geometry.backups_tab.height" in saved_geometry

            # Second session: restore geometry
            mock_yaml.side_effect = mock_load_setting

            new_window = mock_qt_window.__class__()
            new_window.restore_tab_geometry(1)

            # Should restore to saved dimensions
            assert new_window.resized_width == saved_geometry["UI.window_geometry.backups_tab.width"]
            assert new_window.resized_height == saved_geometry["UI.window_geometry.backups_tab.height"]

    def test_multi_tab_geometry_independence(self, mock_qt_window):
        """Test that different tabs maintain independent geometry."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger"):

            # Mock different saved sizes for different tabs
            tab_geometries = {
                "UI.window_geometry.main_tab.width": 600,
                "UI.window_geometry.main_tab.height": 400,
                "UI.window_geometry.main_tab.maximized": False,
                "UI.window_geometry.backups_tab.width": 900,
                "UI.window_geometry.backups_tab.height": 650,
                "UI.window_geometry.backups_tab.maximized": True,
            }

            def mock_settings(*args):
                if len(args) <= 3:
                    return args[3] if len(args) > 3 else None
                key = args[2]
                return tab_geometries.get(key, args[3] if len(args) > 3 else None)

            mock_yaml.side_effect = mock_settings

            # Restore main tab (tab 0)
            mock_qt_window.restore_tab_geometry(0)
            main_width, main_height = mock_qt_window.resized_width, mock_qt_window.resized_height
            main_maximized = mock_qt_window._maximized

            # Restore backups tab (tab 1)
            mock_qt_window.restore_tab_geometry(1)
            backup_width, backup_height = mock_qt_window.resized_width, mock_qt_window.resized_height
            backup_maximized = mock_qt_window._maximized

            # Each tab should have its own dimensions
            assert main_width == 600
            assert main_height == 400
            assert not main_maximized

            assert backup_width == 900
            assert backup_height == 650
            assert backup_maximized

    def test_error_handling_in_geometry_operations(self, mock_qt_window):
        """Test error handling during geometry operations."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger") as mock_logger:

            # Mock yaml_settings to raise an exception
            mock_yaml.side_effect = Exception("Settings error")

            # Operations should handle errors gracefully without crashing
            try:
                mock_qt_window.save_tab_geometry(0)
                mock_qt_window.restore_tab_geometry(0)
            except Exception:
                pytest.fail("Geometry operations should handle settings errors gracefully")

    def test_window_geometry_with_extreme_values(self, mock_qt_window):
        """Test handling of extreme window geometry values."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml, \
             patch("ClassicLib.Interface.WindowGeometryMixin.logger"):

            # Test with extremely large and small values
            extreme_values = [
                (1, 1),           # Very small
                (99999, 99999),   # Very large
                (0, 0),           # Zero values
                (-100, -100),     # Negative values
            ]

            for width, height in extreme_values:
                def mock_settings(*args):
                    if len(args) <= 3:
                        return args[3] if len(args) > 3 else None
                    key = args[2]
                    if "width" in key:
                        return width
                    elif "height" in key:
                        return height
                    elif "maximized" in key:
                        return False
                    return None

                mock_yaml.side_effect = mock_settings

                mock_qt_window.restore_tab_geometry(0)

                # Should enforce minimum sizes regardless of extreme saved values
                min_width, min_height = mock_qt_window.get_minimum_size_for_tab(0)

                if width > 0:
                    expected_width = max(width, min_width)
                    expected_height = max(height, min_height)
                else:
                    # Negative/zero values should be replaced with minimums
                    expected_width = min_width
                    expected_height = min_height

                assert mock_qt_window.resized_width == expected_width
                assert mock_qt_window.resized_height == expected_height
