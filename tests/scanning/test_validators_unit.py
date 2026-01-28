"""Unit tests for ClassicLib.scanning.game.checks.validators module.

This module tests the ScanValidators class for validation utilities.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestScanValidatorsInit:
    """Tests for ScanValidators initialization."""

    def test_init_creates_empty_scan_settings_cache(self) -> None:
        """Test __init__ creates empty scan settings cache."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        assert validators._scan_settings_cache is None

    def test_init_creates_empty_issue_messages_cache(self) -> None:
        """Test __init__ creates empty issue messages cache."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        assert validators._issue_messages_cache == {}


class TestGetScanSettings:
    """Tests for get_scan_settings method."""

    @pytest.mark.asyncio
    async def test_returns_tuple(self) -> None:
        """Test returns a tuple with expected structure."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        mock_registry = MagicMock()
        mock_registry.get_all_script_hashes.return_value = {"script1.pex": {"hash1", "hash2"}}

        with patch("ClassicLib.scanning.game.checks.validators.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = "F4SE"
            with patch("ClassicLib.scanning.game.checks.validators.classic_settings_async", new_callable=AsyncMock) as mock_classic:
                mock_classic.return_value = Path("C:/mods")
                with patch("ClassicLib.scanning.game.checks.validators.get_vr", return_value=""):
                    with patch("ClassicLib.support.versions.get_version_registry", return_value=mock_registry):
                        result = await validators.get_scan_settings()

        assert isinstance(result, tuple)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_returns_xse_acronym(self) -> None:
        """Test returns XSE acronym as first element."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        mock_registry = MagicMock()
        mock_registry.get_all_script_hashes.return_value = {}

        with patch("ClassicLib.scanning.game.checks.validators.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = "F4SE"
            with patch("ClassicLib.scanning.game.checks.validators.classic_settings_async", new_callable=AsyncMock) as mock_classic:
                mock_classic.return_value = None
                with patch("ClassicLib.scanning.game.checks.validators.get_vr", return_value=""):
                    with patch("ClassicLib.support.versions.get_version_registry", return_value=mock_registry):
                        result = await validators.get_scan_settings()

        assert result[0] == "F4SE"

    @pytest.mark.asyncio
    async def test_returns_default_xse_acronym_when_none(self) -> None:
        """Test returns 'XSE' when yaml returns None."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        mock_registry = MagicMock()
        mock_registry.get_all_script_hashes.return_value = {}

        with patch("ClassicLib.scanning.game.checks.validators.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = None  # Return None
            with patch("ClassicLib.scanning.game.checks.validators.classic_settings_async", new_callable=AsyncMock) as mock_classic:
                mock_classic.return_value = None
                with patch("ClassicLib.scanning.game.checks.validators.get_vr", return_value=""):
                    with patch("ClassicLib.support.versions.get_version_registry", return_value=mock_registry):
                        result = await validators.get_scan_settings()

        assert result[0] == "XSE"

    @pytest.mark.asyncio
    async def test_returns_script_hashes_dict(self) -> None:
        """Test returns script hashes dictionary as second element."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        expected_hashes = {"script1.pex": {"hash1"}, "script2.pex": {"hash2"}}
        mock_registry = MagicMock()
        mock_registry.get_all_script_hashes.return_value = expected_hashes

        with patch("ClassicLib.scanning.game.checks.validators.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = "F4SE"
            with patch("ClassicLib.scanning.game.checks.validators.classic_settings_async", new_callable=AsyncMock) as mock_classic:
                mock_classic.return_value = None
                with patch("ClassicLib.scanning.game.checks.validators.get_vr", return_value=""):
                    with patch("ClassicLib.support.versions.get_version_registry", return_value=mock_registry):
                        result = await validators.get_scan_settings()

        assert result[1] == expected_hashes

    @pytest.mark.asyncio
    async def test_returns_mod_path(self) -> None:
        """Test returns mod path as third element."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()
        expected_path = Path("C:/Games/Fallout4/Mods")

        mock_registry = MagicMock()
        mock_registry.get_all_script_hashes.return_value = {}

        with patch("ClassicLib.scanning.game.checks.validators.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = "F4SE"
            with patch("ClassicLib.scanning.game.checks.validators.classic_settings_async", new_callable=AsyncMock) as mock_classic:
                mock_classic.return_value = expected_path
                with patch("ClassicLib.scanning.game.checks.validators.get_vr", return_value=""):
                    with patch("ClassicLib.support.versions.get_version_registry", return_value=mock_registry):
                        result = await validators.get_scan_settings()

        assert result[2] == expected_path

    @pytest.mark.asyncio
    async def test_caches_result(self) -> None:
        """Test caches result after first call."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        mock_registry = MagicMock()
        mock_registry.get_all_script_hashes.return_value = {}

        with patch("ClassicLib.scanning.game.checks.validators.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = "F4SE"
            with patch("ClassicLib.scanning.game.checks.validators.classic_settings_async", new_callable=AsyncMock) as mock_classic:
                mock_classic.return_value = None
                with patch("ClassicLib.scanning.game.checks.validators.get_vr", return_value=""):
                    with patch("ClassicLib.support.versions.get_version_registry", return_value=mock_registry):
                        # First call
                        result1 = await validators.get_scan_settings()
                        # Second call should use cache
                        result2 = await validators.get_scan_settings()

        assert result1 is result2
        assert validators._scan_settings_cache is not None

    @pytest.mark.asyncio
    async def test_uses_vr_mode_correctly(self) -> None:
        """Test passes VR mode to version registry correctly."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        mock_registry = MagicMock()
        mock_registry.get_all_script_hashes.return_value = {}

        with patch("ClassicLib.scanning.game.checks.validators.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = "F4SE"
            with patch("ClassicLib.scanning.game.checks.validators.classic_settings_async", new_callable=AsyncMock) as mock_classic:
                mock_classic.return_value = None
                with patch("ClassicLib.scanning.game.checks.validators.get_vr", return_value="VR"):
                    with patch("ClassicLib.support.versions.get_version_registry", return_value=mock_registry):
                        await validators.get_scan_settings()

        # Should pass is_vr=True when VR mode
        mock_registry.get_all_script_hashes.assert_called_once_with("Fallout4", True)


class TestGetIssueMessages:
    """Tests for get_issue_messages method."""

    def test_returns_dict(self) -> None:
        """Test returns a dictionary."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("F4SE", "unpacked")

        assert isinstance(result, dict)

    def test_unpacked_mode_contains_base_messages(self) -> None:
        """Test unpacked mode contains base message keys."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("F4SE", "unpacked")

        assert "tex_dims" in result
        assert "tex_frmt" in result
        assert "snd_frmt" in result

    def test_unpacked_mode_contains_unpacked_specific_messages(self) -> None:
        """Test unpacked mode contains unpacked-specific keys."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("F4SE", "unpacked")

        assert "xse_file" in result
        assert "previs" in result
        assert "animdata" in result
        assert "cleanup" in result

    def test_archived_mode_contains_base_messages(self) -> None:
        """Test archived mode contains base message keys."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("F4SE", "archived")

        assert "tex_dims" in result
        assert "tex_frmt" in result
        assert "snd_frmt" in result

    def test_archived_mode_contains_archived_specific_messages(self) -> None:
        """Test archived mode contains archived-specific keys."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("F4SE", "archived")

        assert "xse_file" in result
        assert "ba2_frmt" in result

    def test_archived_mode_does_not_contain_unpacked_messages(self) -> None:
        """Test archived mode does not contain unpacked-specific keys."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("F4SE", "archived")

        assert "previs" not in result
        assert "animdata" not in result
        assert "cleanup" not in result

    def test_xse_acronym_appears_in_messages(self) -> None:
        """Test XSE acronym appears in relevant messages."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("F4SE", "unpacked")

        xse_message = "".join(result.get("xse_file", []))
        assert "F4SE" in xse_message

    def test_different_xse_acronym_used_correctly(self) -> None:
        """Test different XSE acronym is used in messages."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("SKSE", "unpacked")

        xse_message = "".join(result.get("xse_file", []))
        assert "SKSE" in xse_message

    def test_caches_result(self) -> None:
        """Test caches result after first call."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result1 = validators.get_issue_messages("F4SE", "unpacked")
        result2 = validators.get_issue_messages("F4SE", "unpacked")

        assert result1 is result2
        assert ("F4SE", "unpacked") in validators._issue_messages_cache

    def test_different_keys_get_separate_cache_entries(self) -> None:
        """Test different mode/acronym combinations are cached separately."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        validators.get_issue_messages("F4SE", "unpacked")
        validators.get_issue_messages("F4SE", "archived")
        validators.get_issue_messages("SKSE", "unpacked")

        assert len(validators._issue_messages_cache) == 3

    def test_message_values_are_lists(self) -> None:
        """Test all message values are lists."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("F4SE", "unpacked")

        for value in result.values():
            assert isinstance(value, list)

    def test_message_list_items_are_strings(self) -> None:
        """Test all items in message lists are strings."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        validators = ScanValidators()

        result = validators.get_issue_messages("F4SE", "unpacked")

        for value in result.values():
            for item in value:
                assert isinstance(item, str)


class TestModuleImports:
    """Tests for module-level imports."""

    def test_scan_validators_class_exists(self) -> None:
        """Test ScanValidators class can be imported."""
        from ClassicLib.scanning.game.checks.validators import ScanValidators

        assert ScanValidators is not None
