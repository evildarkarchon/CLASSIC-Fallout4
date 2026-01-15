"""
E2E tests for ui_structure - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

from ClassicLib.Constants import YAML
from ClassicLib.Interface.Settings.dialog import SettingsDialog


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_dialog_with_no_parent(self, app):
        """Test that dialog works without a parent widget."""
        dialog = SettingsDialog(None, yaml_store=YAML.TEST)
        assert dialog is not None
        assert dialog.windowTitle() == "CLASSIC Settings"
        dialog.close()

    def test_multiple_dialog_instances(self, app):
        """Test that multiple dialog instances don't interfere."""
        from tests.fixtures.gui_settings_fixtures import get_game_version_value, set_game_version_by_value

        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        set_game_version_by_value(dialog1.game_version_combo, "VR")  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue, reportArgumentType]
        set_game_version_by_value(dialog2.game_version_combo, "Original")  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue, reportArgumentType]
        assert get_game_version_value(dialog1.game_version_combo) == "VR"  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue, reportArgumentType]
        assert get_game_version_value(dialog2.game_version_combo) == "Original"  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue, reportArgumentType]
        dialog1.close()
        dialog2.close()

    def test_default_values_created(self, app):
        """Test that default values are created for missing settings."""
        from ClassicLib.YamlSettings import yaml_settings

        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Game Version", None)
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        # Default should be "auto" (Auto-detect)
        assert dialog.game_version_combo.currentIndex() == 0  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue, reportArgumentType]
        dialog.close()
