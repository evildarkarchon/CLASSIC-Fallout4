"""Unit tests for MessageHandler enums module.

This module tests the MessageType and MessageTarget enums, including
their basic values, display logic methods, and Rust interop methods
(to_rust() and from_rust()).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# --- Fixtures ---


@pytest.fixture
def mock_rust_unavailable() -> Generator[None, None, None]:
    """Mock Rust enums as unavailable.

    Yields:
        None after patching the module to disable Rust.

    """
    with patch.dict(
        "ClassicLib.MessageHandler.core.enums.__dict__",
        {
            "RUST_ENUMS": False,
            "_RUST_ENUMS_AVAILABLE": False,
            "RustMessageType": None,
            "RustMessageTarget": None,
        },
    ):
        # Need to reload the module to pick up patched values
        # Instead, we'll patch at the point of use
        yield


@pytest.fixture
def mock_rust_available() -> Generator[tuple[MagicMock, MagicMock], None, None]:
    """Mock Rust enums as available with fake Rust types.

    Yields:
        Tuple of (mock_rust_message_type, mock_rust_message_target).

    """
    # Create mock Rust enum values
    mock_rust_type = MagicMock()
    mock_rust_type.Info = MagicMock()
    mock_rust_type.Warning = MagicMock()
    mock_rust_type.Error = MagicMock()
    mock_rust_type.Success = MagicMock()
    mock_rust_type.Progress = MagicMock()
    mock_rust_type.Debug = MagicMock()
    mock_rust_type.Critical = MagicMock()

    mock_rust_target = MagicMock()
    mock_rust_target.All = MagicMock()
    mock_rust_target.Gui = MagicMock()
    mock_rust_target.Console = MagicMock()
    mock_rust_target.LogOnly = MagicMock()

    with patch.multiple(
        "ClassicLib.MessageHandler.core.enums",
        RUST_ENUMS=True,
        _RUST_ENUMS_AVAILABLE=True,
        RustMessageType=mock_rust_type,
        RustMessageTarget=mock_rust_target,
    ):
        yield mock_rust_type, mock_rust_target


# --- MessageType Basic Tests ---


class TestMessageTypeValues:
    """Tests for MessageType enum values."""

    @pytest.mark.unit
    def test_message_type_has_info(self) -> None:
        """MessageType should have INFO value."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        assert hasattr(MessageType, "INFO")
        assert MessageType.INFO.name == "INFO"

    @pytest.mark.unit
    def test_message_type_has_warning(self) -> None:
        """MessageType should have WARNING value."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        assert hasattr(MessageType, "WARNING")
        assert MessageType.WARNING.name == "WARNING"

    @pytest.mark.unit
    def test_message_type_has_error(self) -> None:
        """MessageType should have ERROR value."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        assert hasattr(MessageType, "ERROR")
        assert MessageType.ERROR.name == "ERROR"

    @pytest.mark.unit
    def test_message_type_has_success(self) -> None:
        """MessageType should have SUCCESS value."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        assert hasattr(MessageType, "SUCCESS")
        assert MessageType.SUCCESS.name == "SUCCESS"

    @pytest.mark.unit
    def test_message_type_has_progress(self) -> None:
        """MessageType should have PROGRESS value."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        assert hasattr(MessageType, "PROGRESS")
        assert MessageType.PROGRESS.name == "PROGRESS"

    @pytest.mark.unit
    def test_message_type_has_debug(self) -> None:
        """MessageType should have DEBUG value."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        assert hasattr(MessageType, "DEBUG")
        assert MessageType.DEBUG.name == "DEBUG"

    @pytest.mark.unit
    def test_message_type_has_critical(self) -> None:
        """MessageType should have CRITICAL value."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        assert hasattr(MessageType, "CRITICAL")
        assert MessageType.CRITICAL.name == "CRITICAL"

    @pytest.mark.unit
    def test_message_type_has_seven_members(self) -> None:
        """MessageType should have exactly 7 members."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        assert len(MessageType) == 7

    @pytest.mark.unit
    def test_message_type_values_are_unique(self) -> None:
        """MessageType values should all be unique."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        values = [member.value for member in MessageType]
        assert len(values) == len(set(values))


# --- MessageTarget Basic Tests ---


class TestMessageTargetValues:
    """Tests for MessageTarget enum values."""

    @pytest.mark.unit
    def test_message_target_has_all(self) -> None:
        """MessageTarget should have ALL value."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert hasattr(MessageTarget, "ALL")
        assert MessageTarget.ALL.name == "ALL"

    @pytest.mark.unit
    def test_message_target_has_gui(self) -> None:
        """MessageTarget should have GUI value."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert hasattr(MessageTarget, "GUI")
        assert MessageTarget.GUI.name == "GUI"

    @pytest.mark.unit
    def test_message_target_has_console(self) -> None:
        """MessageTarget should have CONSOLE value."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert hasattr(MessageTarget, "CONSOLE")
        assert MessageTarget.CONSOLE.name == "CONSOLE"

    @pytest.mark.unit
    def test_message_target_has_log_only(self) -> None:
        """MessageTarget should have LOG_ONLY value."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert hasattr(MessageTarget, "LOG_ONLY")
        assert MessageTarget.LOG_ONLY.name == "LOG_ONLY"

    @pytest.mark.unit
    def test_message_target_has_four_members(self) -> None:
        """MessageTarget should have exactly 4 members."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert len(MessageTarget) == 4


# --- MessageTarget Display Logic Tests ---


class TestMessageTargetNormalize:
    """Tests for MessageTarget.normalize() method."""

    @pytest.mark.unit
    def test_normalize_returns_self_for_all(self) -> None:
        """normalize() should return self for ALL."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.ALL.normalize() is MessageTarget.ALL

    @pytest.mark.unit
    def test_normalize_returns_self_for_gui(self) -> None:
        """normalize() should return self for GUI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.GUI.normalize() is MessageTarget.GUI

    @pytest.mark.unit
    def test_normalize_returns_self_for_console(self) -> None:
        """normalize() should return self for CONSOLE."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.CONSOLE.normalize() is MessageTarget.CONSOLE

    @pytest.mark.unit
    def test_normalize_returns_self_for_log_only(self) -> None:
        """normalize() should return self for LOG_ONLY."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.LOG_ONLY.normalize() is MessageTarget.LOG_ONLY


class TestMessageTargetShouldDisplayInGui:
    """Tests for MessageTarget.should_display_in_gui() method."""

    @pytest.mark.unit
    def test_all_should_display_in_gui(self) -> None:
        """ALL target should display in GUI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.ALL.should_display_in_gui() is True

    @pytest.mark.unit
    def test_gui_should_display_in_gui(self) -> None:
        """GUI target should display in GUI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.GUI.should_display_in_gui() is True

    @pytest.mark.unit
    def test_console_should_not_display_in_gui(self) -> None:
        """CONSOLE target should NOT display in GUI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.CONSOLE.should_display_in_gui() is False

    @pytest.mark.unit
    def test_log_only_should_not_display_in_gui(self) -> None:
        """LOG_ONLY target should NOT display in GUI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.LOG_ONLY.should_display_in_gui() is False


class TestMessageTargetShouldDisplayInCli:
    """Tests for MessageTarget.should_display_in_cli() method."""

    @pytest.mark.unit
    def test_all_should_display_in_cli(self) -> None:
        """ALL target should display in CLI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.ALL.should_display_in_cli() is True

    @pytest.mark.unit
    def test_console_should_display_in_cli(self) -> None:
        """CONSOLE target should display in CLI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.CONSOLE.should_display_in_cli() is True

    @pytest.mark.unit
    def test_gui_should_not_display_in_cli(self) -> None:
        """GUI target should NOT display in CLI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.GUI.should_display_in_cli() is False

    @pytest.mark.unit
    def test_log_only_should_not_display_in_cli(self) -> None:
        """LOG_ONLY target should NOT display in CLI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.LOG_ONLY.should_display_in_cli() is False


class TestMessageTargetShouldDisplay:
    """Tests for MessageTarget.should_display() method."""

    @pytest.mark.unit
    def test_all_should_display(self) -> None:
        """ALL target should display."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.ALL.should_display() is True

    @pytest.mark.unit
    def test_gui_should_display(self) -> None:
        """GUI target should display."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.GUI.should_display() is True

    @pytest.mark.unit
    def test_console_should_display(self) -> None:
        """CONSOLE target should display."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.CONSOLE.should_display() is True

    @pytest.mark.unit
    def test_log_only_should_not_display(self) -> None:
        """LOG_ONLY target should NOT display (log only)."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        assert MessageTarget.LOG_ONLY.should_display() is False


# --- MessageType Rust Interop Tests ---


class TestMessageTypeToRust:
    """Tests for MessageType.to_rust() method."""

    @pytest.mark.unit
    def test_to_rust_returns_none_when_rust_unavailable(self) -> None:
        """to_rust() should return None when Rust is unavailable."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        with patch("ClassicLib.MessageHandler.core.enums.RUST_ENUMS", False):
            result = MessageType.INFO.to_rust()
            assert result is None

    @pytest.mark.unit
    def test_to_rust_maps_info_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map INFO to Rust Info."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_type, _ = mock_rust_available

        result = MessageType.INFO.to_rust()
        assert result is mock_rust_type.Info

    @pytest.mark.unit
    def test_to_rust_maps_warning_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map WARNING to Rust Warning."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_type, _ = mock_rust_available

        result = MessageType.WARNING.to_rust()
        assert result is mock_rust_type.Warning

    @pytest.mark.unit
    def test_to_rust_maps_error_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map ERROR to Rust Error."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_type, _ = mock_rust_available

        result = MessageType.ERROR.to_rust()
        assert result is mock_rust_type.Error

    @pytest.mark.unit
    def test_to_rust_maps_success_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map SUCCESS to Rust Success."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_type, _ = mock_rust_available

        result = MessageType.SUCCESS.to_rust()
        assert result is mock_rust_type.Success

    @pytest.mark.unit
    def test_to_rust_maps_progress_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map PROGRESS to Rust Progress."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_type, _ = mock_rust_available

        result = MessageType.PROGRESS.to_rust()
        assert result is mock_rust_type.Progress

    @pytest.mark.unit
    def test_to_rust_maps_debug_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map DEBUG to Rust Debug."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_type, _ = mock_rust_available

        result = MessageType.DEBUG.to_rust()
        assert result is mock_rust_type.Debug

    @pytest.mark.unit
    def test_to_rust_maps_critical_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map CRITICAL to Rust Critical."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_type, _ = mock_rust_available

        result = MessageType.CRITICAL.to_rust()
        assert result is mock_rust_type.Critical


class TestMessageTypeFromRust:
    """Tests for MessageType.from_rust() method."""

    @pytest.mark.unit
    def test_from_rust_raises_when_rust_unavailable(self) -> None:
        """from_rust() should raise ValueError when Rust is unavailable."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        with patch("ClassicLib.MessageHandler.core.enums.RUST_ENUMS", False):
            with pytest.raises(ValueError, match="Rust enums not available"):
                MessageType.from_rust("Info")

    @pytest.mark.unit
    def test_from_rust_maps_info_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'info' string to INFO."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        # The from_rust uses str(rust_type).lower() for matching
        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="info")

        result = MessageType.from_rust(mock_rust_value)
        assert result is MessageType.INFO

    @pytest.mark.unit
    def test_from_rust_maps_warning_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'warning' string to WARNING."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="warning")

        result = MessageType.from_rust(mock_rust_value)
        assert result is MessageType.WARNING

    @pytest.mark.unit
    def test_from_rust_maps_error_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'error' string to ERROR."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="error")

        result = MessageType.from_rust(mock_rust_value)
        assert result is MessageType.ERROR

    @pytest.mark.unit
    def test_from_rust_maps_success_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'success' string to SUCCESS."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="success")

        result = MessageType.from_rust(mock_rust_value)
        assert result is MessageType.SUCCESS

    @pytest.mark.unit
    def test_from_rust_maps_progress_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'progress' string to PROGRESS."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="progress")

        result = MessageType.from_rust(mock_rust_value)
        assert result is MessageType.PROGRESS

    @pytest.mark.unit
    def test_from_rust_maps_debug_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'debug' string to DEBUG."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="debug")

        result = MessageType.from_rust(mock_rust_value)
        assert result is MessageType.DEBUG

    @pytest.mark.unit
    def test_from_rust_maps_critical_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'critical' string to CRITICAL."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="critical")

        result = MessageType.from_rust(mock_rust_value)
        assert result is MessageType.CRITICAL

    @pytest.mark.unit
    def test_from_rust_raises_for_unknown_type(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should raise ValueError for unknown Rust type."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="unknown_type")

        with pytest.raises(ValueError, match="Unknown Rust MessageType"):
            MessageType.from_rust(mock_rust_value)

    @pytest.mark.unit
    def test_from_rust_is_case_insensitive(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should handle case-insensitive matching."""
        from ClassicLib.MessageHandler.core.enums import MessageType

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="INFO")

        result = MessageType.from_rust(mock_rust_value)
        assert result is MessageType.INFO


# --- MessageTarget Rust Interop Tests ---


class TestMessageTargetToRust:
    """Tests for MessageTarget.to_rust() method."""

    @pytest.mark.unit
    def test_to_rust_returns_none_when_rust_unavailable(self) -> None:
        """to_rust() should return None when Rust is unavailable."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        with patch("ClassicLib.MessageHandler.core.enums.RUST_ENUMS", False):
            result = MessageTarget.ALL.to_rust()
            assert result is None

    @pytest.mark.unit
    def test_to_rust_maps_all_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map ALL to Rust All."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        _, mock_rust_target = mock_rust_available

        result = MessageTarget.ALL.to_rust()
        assert result is mock_rust_target.All

    @pytest.mark.unit
    def test_to_rust_maps_gui_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map GUI to Rust Gui."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        _, mock_rust_target = mock_rust_available

        result = MessageTarget.GUI.to_rust()
        assert result is mock_rust_target.Gui

    @pytest.mark.unit
    def test_to_rust_maps_console_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map CONSOLE to Rust Console."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        _, mock_rust_target = mock_rust_available

        result = MessageTarget.CONSOLE.to_rust()
        assert result is mock_rust_target.Console

    @pytest.mark.unit
    def test_to_rust_maps_log_only_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """to_rust() should map LOG_ONLY to Rust LogOnly."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        _, mock_rust_target = mock_rust_available

        result = MessageTarget.LOG_ONLY.to_rust()
        assert result is mock_rust_target.LogOnly


class TestMessageTargetFromRust:
    """Tests for MessageTarget.from_rust() method."""

    @pytest.mark.unit
    def test_from_rust_raises_when_rust_unavailable(self) -> None:
        """from_rust() should raise ValueError when Rust is unavailable."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        with patch("ClassicLib.MessageHandler.core.enums.RUST_ENUMS", False):
            with pytest.raises(ValueError, match="Rust enums not available"):
                MessageTarget.from_rust("All")

    @pytest.mark.unit
    def test_from_rust_maps_all_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'all' string to ALL."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="all")

        result = MessageTarget.from_rust(mock_rust_value)
        assert result is MessageTarget.ALL

    @pytest.mark.unit
    def test_from_rust_maps_gui_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'gui' string to GUI."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="gui")

        result = MessageTarget.from_rust(mock_rust_value)
        assert result is MessageTarget.GUI

    @pytest.mark.unit
    def test_from_rust_maps_console_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'console' string to CONSOLE."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="console")

        result = MessageTarget.from_rust(mock_rust_value)
        assert result is MessageTarget.CONSOLE

    @pytest.mark.unit
    def test_from_rust_maps_cli_to_console(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'cli' string to CONSOLE."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="cli")

        result = MessageTarget.from_rust(mock_rust_value)
        assert result is MessageTarget.CONSOLE

    @pytest.mark.unit
    def test_from_rust_maps_log_only_correctly(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should map 'log_only' string to LOG_ONLY."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="log_only")

        result = MessageTarget.from_rust(mock_rust_value)
        assert result is MessageTarget.LOG_ONLY

    @pytest.mark.unit
    def test_from_rust_raises_for_unknown_target(self, mock_rust_available: tuple[MagicMock, MagicMock]) -> None:
        """from_rust() should raise ValueError for unknown Rust target."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget

        mock_rust_value = MagicMock()
        mock_rust_value.__str__ = MagicMock(return_value="unknown_target")

        with pytest.raises(ValueError, match="Unknown Rust MessageTarget"):
            MessageTarget.from_rust(mock_rust_value)


# --- Module-Level Tests ---


class TestModuleLevelConstants:
    """Tests for module-level constants."""

    @pytest.mark.unit
    def test_rust_enums_constant_is_boolean(self) -> None:
        """RUST_ENUMS module constant should be a boolean."""
        from ClassicLib.MessageHandler.core.enums import RUST_ENUMS

        assert isinstance(RUST_ENUMS, bool)
