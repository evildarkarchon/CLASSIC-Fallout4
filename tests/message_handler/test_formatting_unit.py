"""Unit tests for MessageHandler formatting module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# --- Emoji Stripping Tests ---


class TestStripEmoji:
    """Tests for strip_emoji function."""

    @pytest.mark.unit
    def test_strip_emoji_removes_basic_emoticons(self) -> None:
        """strip_emoji should remove basic emoticons."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        result = strip_emoji("Hello 😀 World 😊")

        assert "😀" not in result
        assert "😊" not in result
        assert "Hello" in result
        assert "World" in result

    @pytest.mark.unit
    def test_strip_emoji_removes_symbols_and_pictographs(self) -> None:
        """strip_emoji should remove symbols and pictographs."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        result = strip_emoji("Test 🌟 message 🎉")

        assert "🌟" not in result
        assert "🎉" not in result
        assert "Test" in result
        assert "message" in result

    @pytest.mark.unit
    def test_strip_emoji_removes_transport_symbols(self) -> None:
        """strip_emoji should remove transport and map symbols."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        result = strip_emoji("Travel 🚗 by 🚀")

        assert "🚗" not in result
        assert "🚀" not in result

    @pytest.mark.unit
    def test_strip_emoji_preserves_regular_text(self) -> None:
        """strip_emoji should not modify regular text."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        text = "Hello, World! This is a test message."
        result = strip_emoji(text)

        assert result == text

    @pytest.mark.unit
    def test_strip_emoji_handles_empty_string(self) -> None:
        """strip_emoji should handle empty string."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        result = strip_emoji("")

        assert result == ""

    @pytest.mark.unit
    def test_strip_emoji_handles_only_emojis(self) -> None:
        """strip_emoji should return empty string for emoji-only input."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        result = strip_emoji("😀🎉🚀")

        assert result == ""

    @pytest.mark.unit
    def test_strip_emoji_trims_whitespace(self) -> None:
        """strip_emoji should trim leading/trailing whitespace."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        result = strip_emoji("  Hello 😀  ")

        assert result == "Hello"

    @pytest.mark.unit
    def test_strip_emoji_handles_accented_unicode_text(self) -> None:
        """strip_emoji should preserve accented unicode characters."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        result = strip_emoji("Café résumé naïve")

        assert "Café" in result
        assert "résumé" in result
        assert "naïve" in result

    @pytest.mark.unit
    def test_strip_emoji_handles_mixed_content(self) -> None:
        """strip_emoji should handle mixed content correctly."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        result = strip_emoji("Error: 🚨 File not found ❌")

        assert "Error:" in result
        assert "File not found" in result
        assert "🚨" not in result
        assert "❌" not in result


class TestStripEmojiRustIntegration:
    """Tests for Rust acceleration of emoji stripping."""

    @pytest.mark.unit
    def test_uses_rust_when_available(self) -> None:
        """strip_emoji should delegate to Rust binding."""
        from ClassicLib.messaging.formatting import formatter

        mock_rust = MagicMock()
        mock_rust.strip_emoji.return_value = "Result from Rust"

        with patch.object(formatter, "classic_message", mock_rust):
            result = formatter.strip_emoji("Test 😀")

        mock_rust.strip_emoji.assert_called_once_with("Test 😀")
        assert result == "Result from Rust"

    @pytest.mark.unit
    def test_propagates_rust_errors(self) -> None:
        """strip_emoji should propagate Rust binding errors."""
        from ClassicLib.messaging.formatting import formatter

        mock_rust = MagicMock()
        mock_rust.strip_emoji.side_effect = RuntimeError("binding failure")

        with patch.object(formatter, "classic_message", mock_rust):
            with pytest.raises(RuntimeError, match="binding failure"):
                formatter.strip_emoji("Test 😀 message")


# --- Log Message Formatting Tests ---


class TestFormatLogMessage:
    """Tests for format_log_message function."""

    @pytest.mark.unit
    def test_format_basic_message(self) -> None:
        """format_log_message should format basic message."""
        from ClassicLib.messaging.formatting.formatter import format_log_message

        result = format_log_message("Test content")

        assert "Test content" in result

    @pytest.mark.unit
    def test_format_message_with_details(self) -> None:
        """format_log_message should append details."""
        from ClassicLib.messaging.formatting.formatter import format_log_message

        result = format_log_message("Main message", "Additional details")

        assert "Main message" in result
        assert "Details:" in result
        assert "Additional details" in result

    @pytest.mark.unit
    def test_format_strips_emojis_from_content(self) -> None:
        """format_log_message should strip emojis from content."""
        from ClassicLib.messaging.formatting.formatter import format_log_message

        result = format_log_message("Success 🎉 Complete")

        assert "🎉" not in result
        assert "Success" in result
        assert "Complete" in result

    @pytest.mark.unit
    def test_format_strips_emojis_from_details(self) -> None:
        """format_log_message should strip emojis from details."""
        from ClassicLib.messaging.formatting.formatter import format_log_message

        result = format_log_message("Message", "Details 🚀 here")

        assert "🚀" not in result
        assert "Details" in result

    @pytest.mark.unit
    def test_format_with_none_details(self) -> None:
        """format_log_message should handle None details."""
        from ClassicLib.messaging.formatting.formatter import format_log_message

        result = format_log_message("Message only", None)

        assert "Message only" in result
        assert "Details:" not in result

    @pytest.mark.unit
    def test_format_with_empty_details(self) -> None:
        """format_log_message should handle empty details."""
        from ClassicLib.messaging.formatting.formatter import format_log_message

        result = format_log_message("Message", "")

        assert "Message" in result


class TestFormatLogMessageRustIntegration:
    """Tests for Rust acceleration of log message formatting."""

    @pytest.mark.unit
    def test_uses_rust_when_available(self) -> None:
        """format_log_message should delegate to Rust binding."""
        from ClassicLib.messaging.formatting import formatter

        mock_rust = MagicMock()
        mock_rust.format_log_message.return_value = "Rust formatted"

        with patch.object(formatter, "classic_message", mock_rust):
            result = formatter.format_log_message("Content", "Details")

        mock_rust.format_log_message.assert_called_once_with("Content", "Details")
        assert result == "Rust formatted"

    @pytest.mark.unit
    def test_propagates_rust_errors(self) -> None:
        """format_log_message should propagate Rust binding errors."""
        from ClassicLib.messaging.formatting import formatter

        mock_rust = MagicMock()
        mock_rust.format_log_message.side_effect = RuntimeError("binding failure")

        with patch.object(formatter, "classic_message", mock_rust):
            with pytest.raises(RuntimeError, match="binding failure"):
                formatter.format_log_message("Content 😀", "Details 🎉")


# --- Module State Tests ---


class TestFormatterModuleState:
    """Tests for formatter module state."""

    @pytest.mark.unit
    def test_module_exports_main_functions(self) -> None:
        """Module should export main functions."""
        from ClassicLib.messaging.formatting import formatter

        assert hasattr(formatter, "strip_emoji")
        assert hasattr(formatter, "format_log_message")
        assert callable(formatter.strip_emoji)
        assert callable(formatter.format_log_message)


# --- Edge Case Tests ---


class TestFormattingEdgeCases:
    """Edge case tests for formatting functions."""

    @pytest.mark.unit
    def test_strip_emoji_very_long_string(self) -> None:
        """strip_emoji should handle very long strings."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        long_text = "Test 😀 " * 1000
        result = strip_emoji(long_text)

        assert "😀" not in result
        assert "Test" in result

    @pytest.mark.unit
    def test_strip_emoji_consecutive_emojis(self) -> None:
        """strip_emoji should handle consecutive emojis."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        result = strip_emoji("Before😀😊😎After")

        assert result == "BeforeAfter"

    @pytest.mark.unit
    def test_strip_emoji_special_characters(self) -> None:
        """strip_emoji should preserve special characters."""
        from ClassicLib.messaging.formatting.formatter import strip_emoji

        text = "Path: C:\\Users\\test\\file.txt"
        result = strip_emoji(text)

        assert result == text

    @pytest.mark.unit
    def test_format_message_with_newlines(self) -> None:
        """format_log_message should handle content with newlines."""
        from ClassicLib.messaging.formatting.formatter import format_log_message

        result = format_log_message("Line 1\nLine 2", "Detail 1\nDetail 2")

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Detail 1" in result
        assert "Detail 2" in result

    @pytest.mark.unit
    def test_format_message_with_tabs(self) -> None:
        """format_log_message should handle content with tabs."""
        from ClassicLib.messaging.formatting.formatter import format_log_message

        result = format_log_message("Column1\tColumn2", None)

        assert "Column1\tColumn2" in result
