"""Unit tests for WindowGeometryManager controller.

This module tests the WindowGeometryManager class that handles per-tab
window sizing, saving, and restoring window dimensions.

All tests in this module mock Qt widgets and YAML settings to prevent
UI interactions and file system changes during testing.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# Skip Qt-dependent tests in parallel workers
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


class TestWindowGeometryManagerInit:
    """Tests for WindowGeometryManager initialization."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.tab_widget = MagicMock()
        context.signal_hub = MagicMock()
        context.signal_hub.tab_changed = MagicMock()
        context.signal_hub.refresh_reports_requested = MagicMock()
        return context

    @pytest.mark.unit
    def test_init_creates_manager(self, mock_context):
        """Test WindowGeometryManager initializes correctly."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        manager = WindowGeometryManager(mock_context)

        assert manager._ctx is mock_context
        assert manager._last_tab_index is None
        assert manager._geometry_initialized is False

    @pytest.mark.unit
    def test_default_min_sizes_defined(self):
        """Test DEFAULT_MIN_SIZES class attribute is properly defined."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        assert WindowGeometryManager.DEFAULT_MIN_SIZES is not None
        assert 0 in WindowGeometryManager.DEFAULT_MIN_SIZES
        assert 1 in WindowGeometryManager.DEFAULT_MIN_SIZES
        assert 2 in WindowGeometryManager.DEFAULT_MIN_SIZES
        assert 3 in WindowGeometryManager.DEFAULT_MIN_SIZES

    @pytest.mark.unit
    def test_tab_names_defined(self):
        """Test TAB_NAMES class attribute is properly defined."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        assert WindowGeometryManager.TAB_NAMES is not None
        assert WindowGeometryManager.TAB_NAMES[0] == "main_tab"
        assert WindowGeometryManager.TAB_NAMES[1] == "backups_tab"
        assert WindowGeometryManager.TAB_NAMES[2] == "articles_tab"
        assert WindowGeometryManager.TAB_NAMES[3] == "results_tab"


class TestWindowGeometryManagerSetup:
    """Tests for setup method."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.tab_widget = MagicMock()
        context.ui_widgets.tab_widget.currentIndex.return_value = 0
        context.signal_hub = MagicMock()
        context.signal_hub.tab_changed = MagicMock()
        return context

    @pytest.mark.unit
    @patch(
        "ClassicLib.Interface.controllers.window_geometry.yaml_settings",
        return_value=None,
    )
    def test_setup_connects_signals(self, mock_yaml, mock_context):
        """Test setup connects tab change signal."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        manager = WindowGeometryManager(mock_context)
        manager.setup()

        mock_context.ui_widgets.tab_widget.currentChanged.connect.assert_called_once()
        mock_context.signal_hub.tab_changed.connect.assert_called_once()

    @pytest.mark.unit
    @patch(
        "ClassicLib.Interface.controllers.window_geometry.yaml_settings",
        return_value=None,
    )
    def test_setup_initializes_geometry(self, mock_yaml, mock_context):
        """Test setup restores geometry for initial tab."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        mock_context.ui_widgets.tab_widget.currentIndex.return_value = 2

        manager = WindowGeometryManager(mock_context)
        manager.setup()

        assert manager._last_tab_index == 2
        assert manager._geometry_initialized is True

    @pytest.mark.unit
    def test_setup_handles_missing_tab_widget(self, mock_context):
        """Test setup handles missing tab widget gracefully."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        mock_context.ui_widgets.tab_widget = None

        manager = WindowGeometryManager(mock_context)
        manager.setup()

        # Should not raise and should not initialize
        assert manager._geometry_initialized is False


class TestWindowGeometryManagerTabChanged:
    """Tests for handle_tab_changed method."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.main_window.size.return_value = MagicMock(width=lambda: 800, height=lambda: 600)
        context.ui_widgets = MagicMock()
        context.ui_widgets.tab_widget = MagicMock()
        context.signal_hub = MagicMock()
        context.signal_hub.tab_changed = MagicMock()
        context.signal_hub.refresh_reports_requested = MagicMock()
        return context

    @pytest.mark.unit
    def test_handle_tab_changed_returns_early_when_not_initialized(self, mock_context):
        """Test handle_tab_changed returns early when geometry not initialized."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        manager = WindowGeometryManager(mock_context)
        # _geometry_initialized is False by default

        manager.handle_tab_changed(1)

        # Should not emit signal when not initialized
        mock_context.signal_hub.tab_changed.emit.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_handle_tab_changed_saves_previous_geometry(
        self, mock_yaml, mock_context
    ):
        """Test handle_tab_changed saves geometry for previous tab."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        mock_yaml.return_value = None

        manager = WindowGeometryManager(mock_context)
        manager._geometry_initialized = True
        manager._last_tab_index = 0

        manager.handle_tab_changed(1)

        # Should have saved geometry for tab 0 and restored for tab 1
        assert manager._last_tab_index == 1

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_handle_tab_changed_emits_signal(self, mock_yaml, mock_context):
        """Test handle_tab_changed emits tab_changed signal."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        mock_yaml.return_value = None

        manager = WindowGeometryManager(mock_context)
        manager._geometry_initialized = True
        manager._last_tab_index = 0

        manager.handle_tab_changed(2)

        mock_context.signal_hub.tab_changed.emit.assert_called_once_with(2)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_on_tab_changed_signal_requests_refresh_for_results_tab(
        self, mock_yaml, mock_context
    ):
        """Test _on_tab_changed_signal requests refresh when switching to results tab."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        manager = WindowGeometryManager(mock_context)
        manager._on_tab_changed_signal(3)  # Results tab index

        mock_context.signal_hub.refresh_reports_requested.emit.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_on_tab_changed_signal_no_refresh_for_other_tabs(
        self, mock_yaml, mock_context
    ):
        """Test _on_tab_changed_signal does not request refresh for non-results tabs."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        manager = WindowGeometryManager(mock_context)

        for tab_index in [0, 1, 2]:
            manager._on_tab_changed_signal(tab_index)

        mock_context.signal_hub.refresh_reports_requested.emit.assert_not_called()


class TestWindowGeometryManagerSaveRestore:
    """Tests for save_tab_geometry and restore_tab_geometry methods."""

    @pytest.fixture
    def mock_context_with_qt(self):
        """Create a mock FeatureContext with proper window and Qt mocking."""
        from PySide6.QtCore import Qt

        context = MagicMock()

        # Mock window with proper size object
        mock_size = MagicMock()
        mock_size.width.return_value = 800
        mock_size.height.return_value = 600

        mock_normal_geom = MagicMock()
        mock_normal_geom.width.return_value = 750
        mock_normal_geom.height.return_value = 550

        context.main_window = MagicMock()
        context.main_window.size.return_value = mock_size
        context.main_window.normalGeometry.return_value = mock_normal_geom
        # Return a Qt WindowState (not maximized) for compatibility
        context.main_window.windowState.return_value = Qt.WindowState.WindowNoState

        context.ui_widgets = MagicMock()
        context.ui_widgets.tab_widget = MagicMock()
        context.signal_hub = MagicMock()
        return context

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_save_tab_geometry_saves_size(self, mock_yaml, mock_context_with_qt):
        """Test save_tab_geometry saves current window size to YAML."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        manager = WindowGeometryManager(mock_context_with_qt)
        manager.save_tab_geometry(0)

        # Should save maximized state, width, and height
        assert mock_yaml.call_count >= 2

    @pytest.mark.unit
    def test_save_tab_geometry_ignores_unknown_tab(self):
        """Test save_tab_geometry ignores unknown tab index."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        context = MagicMock()
        manager = WindowGeometryManager(context)

        # Should not raise for unknown tab
        manager.save_tab_geometry(99)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_save_tab_geometry_handles_maximized_window(
        self, mock_yaml, mock_context_with_qt
    ):
        """Test save_tab_geometry saves normal geometry when maximized."""
        from PySide6.QtCore import Qt

        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        # Set window to maximized state
        mock_context_with_qt.main_window.windowState.return_value = (
            Qt.WindowState.WindowMaximized
        )

        manager = WindowGeometryManager(mock_context_with_qt)
        manager.save_tab_geometry(0)

        # Should save maximized state as True
        first_yaml_call = mock_yaml.call_args_list[0]
        assert first_yaml_call[0][0] is bool  # First arg is type
        assert first_yaml_call[0][3] is True  # is_maximized should be True

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_restore_tab_geometry_uses_saved_size(
        self, mock_yaml, mock_context_with_qt
    ):
        """Test restore_tab_geometry uses saved size from YAML."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        mock_yaml.side_effect = [900, 700, False]  # width, height, maximized

        manager = WindowGeometryManager(mock_context_with_qt)
        manager.restore_tab_geometry(0)

        mock_context_with_qt.main_window.resize.assert_called_once_with(900, 700)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_restore_tab_geometry_uses_default_when_no_saved_size(
        self, mock_yaml, mock_context_with_qt
    ):
        """Test restore_tab_geometry uses default min size when no saved size."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        mock_yaml.side_effect = [None, None, False]  # No saved sizes

        manager = WindowGeometryManager(mock_context_with_qt)
        manager.restore_tab_geometry(0)

        # Should use default minimum size for tab 0 (550, 350)
        mock_context_with_qt.main_window.resize.assert_called_once_with(550, 350)

    @pytest.mark.unit
    def test_restore_tab_geometry_ignores_unknown_tab(self):
        """Test restore_tab_geometry ignores unknown tab index."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        context = MagicMock()
        manager = WindowGeometryManager(context)

        # Should not raise for unknown tab
        manager.restore_tab_geometry(99)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_restore_tab_geometry_enforces_minimum_size(
        self, mock_yaml, mock_context_with_qt
    ):
        """Test restore_tab_geometry enforces minimum size constraints."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        # Return saved size smaller than minimum
        mock_yaml.side_effect = [100, 100, False]  # Too small

        manager = WindowGeometryManager(mock_context_with_qt)
        manager.restore_tab_geometry(0)

        # Should use minimum size (550, 350) instead of (100, 100)
        mock_context_with_qt.main_window.resize.assert_called_once_with(550, 350)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_restore_tab_geometry_restores_maximized_state(
        self, mock_yaml, mock_context_with_qt
    ):
        """Test restore_tab_geometry restores maximized state."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        mock_yaml.side_effect = [800, 600, True]  # was_maximized = True

        manager = WindowGeometryManager(mock_context_with_qt)
        manager.restore_tab_geometry(0)

        mock_context_with_qt.main_window.showMaximized.assert_called_once()


class TestWindowGeometryManagerHelpers:
    """Tests for helper methods."""

    @pytest.mark.unit
    def test_get_minimum_size_for_known_tab(self):
        """Test get_minimum_size_for_tab returns correct size for known tabs."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        manager = WindowGeometryManager(MagicMock())

        assert manager.get_minimum_size_for_tab(0) == (550, 350)
        assert manager.get_minimum_size_for_tab(1) == (750, 580)
        assert manager.get_minimum_size_for_tab(2) == (550, 350)
        assert manager.get_minimum_size_for_tab(3) == (750, 450)

    @pytest.mark.unit
    def test_get_minimum_size_for_unknown_tab(self):
        """Test get_minimum_size_for_tab returns default for unknown tabs."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        manager = WindowGeometryManager(MagicMock())

        assert manager.get_minimum_size_for_tab(99) == (550, 350)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.window_geometry.yaml_settings")
    def test_save_current_tab_geometry(self, mock_yaml):
        """Test save_current_tab_geometry saves geometry for current tab."""
        from PySide6.QtCore import Qt

        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        context = MagicMock()
        mock_size = MagicMock()
        mock_size.width.return_value = 800
        mock_size.height.return_value = 600
        context.main_window = MagicMock()
        context.main_window.size.return_value = mock_size
        context.main_window.windowState.return_value = Qt.WindowState.WindowNoState
        context.ui_widgets = MagicMock()
        context.ui_widgets.tab_widget = MagicMock()
        context.ui_widgets.tab_widget.currentIndex.return_value = 2
        context.signal_hub = MagicMock()

        manager = WindowGeometryManager(context)
        manager._geometry_initialized = True

        manager.save_current_tab_geometry()

        # Verify save was called (yaml_settings invoked for geometry)
        assert mock_yaml.call_count >= 2

    @pytest.mark.unit
    def test_save_current_tab_geometry_not_initialized(self):
        """Test save_current_tab_geometry does nothing when not initialized."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        context = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.tab_widget = MagicMock()

        manager = WindowGeometryManager(context)
        # _geometry_initialized is False

        # Should not call save
        manager.save_current_tab_geometry()
        # Just verify it doesn't raise

    @pytest.mark.unit
    def test_save_current_tab_geometry_no_tab_widget(self):
        """Test save_current_tab_geometry handles missing tab widget."""
        from ClassicLib.Interface.controllers.window_geometry import (
            WindowGeometryManager,
        )

        context = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.tab_widget = None

        manager = WindowGeometryManager(context)
        manager._geometry_initialized = True

        # Should not raise
        manager.save_current_tab_geometry()
