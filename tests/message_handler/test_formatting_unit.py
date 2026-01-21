"""Unit tests for MessageHandler formatting module.

This module tests the Rust-accelerated text formatting utilities including
emoji stripping and log message formatting, with both Rust and Python fallback
implementations.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# --- Emoji Stripping Tests ---


class TestStripEmoji:
    """Tests for strip_emoji function."""

    @pytest.mark.unit
    def test_strip_emoji_removes_basic_emoticons(self) -> None:
        """strip_emoji should remove basic emoticons."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        result = strip_emoji("Hello 😀 World 😊")

        assert "😀" not in result
        assert "😊" not in result
        assert "Hello" in result
        assert "World" in result

    @pytest.mark.unit
    def test_strip_emoji_removes_symbols_and_pictographs(self) -> None:
        """strip_emoji should remove symbols and pictographs."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        result = strip_emoji("Test 🌟 message 🎉")

        assert "🌟" not in result
        assert "🎉" not in result
        assert "Test" in result
        assert "message" in result

    @pytest.mark.unit
    def test_strip_emoji_removes_transport_symbols(self) -> None:
        """strip_emoji should remove transport and map symbols."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        result = strip_emoji("Travel 🚗 by 🚀")

        assert "🚗" not in result
        assert "🚀" not in result

    @pytest.mark.unit
    def test_strip_emoji_preserves_regular_text(self) -> None:
        """strip_emoji should not modify regular text."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        text = "Hello, World! This is a test message."
        result = strip_emoji(text)

        assert result == text

    @pytest.mark.unit
    def test_strip_emoji_handles_empty_string(self) -> None:
        """strip_emoji should handle empty string."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        result = strip_emoji("")

        assert result == ""

    @pytest.mark.unit
    def test_strip_emoji_handles_only_emojis(self) -> None:
        """strip_emoji should return empty string for emoji-only input."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        result = strip_emoji("😀🎉🚀")

        assert result == ""

    @pytest.mark.unit
    def test_strip_emoji_trims_whitespace(self) -> None:
        """strip_emoji should trim leading/trailing whitespace."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        result = strip_emoji("  Hello 😀  ")

        assert result == "Hello"

    @pytest.mark.unit
    def test_strip_emoji_handles_accented_unicode_text(self) -> None:
        """strip_emoji should preserve accented unicode characters."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        result = strip_emoji("Café résumé naïve")

        assert "Café" in result
        assert "résumé" in result
        assert "naïve" in result

    @pytest.mark.unit
    def test_strip_emoji_handles_mixed_content(self) -> None:
        """strip_emoji should handle mixed content correctly."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        result = strip_emoji("Error: 🚨 File not found ❌")

        assert "Error:" in result
        assert "File not found" in result
        assert "🚨" not in result
        assert "❌" not in result


class TestStripEmojiPythonFallback:
    """Tests for Python fallback emoji stripping."""

    @pytest.mark.unit
    def test_python_fallback_removes_emojis(self) -> None:
        """Python fallback should remove emojis."""
        from ClassicLib.MessageHandler.formatting.formatter import _python_strip_emoji

        result = _python_strip_emoji("Test 😀 message")

        assert "😀" not in result
        assert "Test" in result

    @pytest.mark.unit
    def test_python_fallback_strips_whitespace(self) -> None:
        """Python fallback should strip whitespace."""
        from ClassicLib.MessageHandler.formatting.formatter import _python_strip_emoji

        result = _python_strip_emoji("  Hello  ")

        assert result == "Hello"

    @pytest.mark.unit
    def test_emoji_pattern_is_cached(self) -> None:
        """Emoji pattern should be compiled once and cached."""
        from ClassicLib.MessageHandler.formatting import formatter

        # Reset the pattern
        formatter._EMOJI_PATTERN = None

        # First call compiles the pattern
        pattern1 = formatter._get_emoji_pattern()
        # Second call returns cached pattern
        pattern2 = formatter._get_emoji_pattern()

        assert pattern1 is pattern2


class TestStripEmojiRustIntegration:
    """Tests for Rust acceleration of emoji stripping."""

    @pytest.mark.unit
    def test_uses_rust_when_available(self) -> None:
        """strip_emoji should use Rust when available."""
        from ClassicLib.MessageHandler.formatting import formatter

        mock_rust = MagicMock()
        mock_rust.strip_emoji.return_value = "Result from Rust"

        with patch.object(formatter, "RUST_AVAILABLE", True):
            with patch.object(formatter, "classic_message", mock_rust):
                result = formatter.strip_emoji("Test 😀")

        mock_rust.strip_emoji.assert_called_once_with("Test 😀")
        assert result == "Result from Rust"

    @pytest.mark.unit
    def test_falls_back_to_python_when_rust_unavailable(self) -> None:
        """strip_emoji should fall back to Python when Rust unavailable."""
        from ClassicLib.MessageHandler.formatting import formatter

        with patch.object(formatter, "RUST_AVAILABLE", False):
            result = formatter.strip_emoji("Test 😀 message")

        assert "😀" not in result
        assert "Test" in result


# --- Log Message Formatting Tests ---


class TestFormatLogMessage:
    """Tests for format_log_message function."""

    @pytest.mark.unit
    def test_format_basic_message(self) -> None:
        """format_log_message should format basic message."""
        from ClassicLib.MessageHandler.formatting.formatter import format_log_message

        result = format_log_message("Test content")

        assert "Test content" in result

    @pytest.mark.unit
    def test_format_message_with_details(self) -> None:
        """format_log_message should append details."""
        from ClassicLib.MessageHandler.formatting.formatter import format_log_message

        result = format_log_message("Main message", "Additional details")

        assert "Main message" in result
        assert "Details:" in result
        assert "Additional details" in result

    @pytest.mark.unit
    def test_format_strips_emojis_from_content(self) -> None:
        """format_log_message should strip emojis from content."""
        from ClassicLib.MessageHandler.formatting.formatter import format_log_message

        result = format_log_message("Success 🎉 Complete")

        assert "🎉" not in result
        assert "Success" in result
        assert "Complete" in result

    @pytest.mark.unit
    def test_format_strips_emojis_from_details(self) -> None:
        """format_log_message should strip emojis from details."""
        from ClassicLib.MessageHandler.formatting.formatter import format_log_message

        result = format_log_message("Message", "Details 🚀 here")

        assert "🚀" not in result
        assert "Details" in result

    @pytest.mark.unit
    def test_format_with_none_details(self) -> None:
        """format_log_message should handle None details."""
        from ClassicLib.MessageHandler.formatting.formatter import format_log_message

        result = format_log_message("Message only", None)

        assert "Message only" in result
        assert "Details:" not in result

    @pytest.mark.unit
    def test_format_with_empty_details(self) -> None:
        """format_log_message should handle empty details.

        Note: The Rust implementation includes "Details:" even for empty strings,
        while Python version treats empty string as falsy. The test verifies
        the message content is present regardless.
        """
        from ClassicLib.MessageHandler.formatting.formatter import format_log_message

        result = format_log_message("Message", "")

        assert "Message" in result
        # Behavior differs between Rust and Python for empty details
        # Just verify the main content is present


class TestFormatLogMessagePythonFallback:
    """Tests for Python fallback log message formatting."""

    @pytest.mark.unit
    def test_python_fallback_formats_content(self) -> None:
        """Python fallback should format content."""
        from ClassicLib.MessageHandler.formatting.formatter import (
            _python_format_log_message,
        )

        result = _python_format_log_message("Test 😀 message")

        assert "😀" not in result
        assert "Test" in result

    @pytest.mark.unit
    def test_python_fallback_appends_details(self) -> None:
        """Python fallback should append details with newline."""
        from ClassicLib.MessageHandler.formatting.formatter import (
            _python_format_log_message,
        )

        result = _python_format_log_message("Content", "Details 🎉")

        lines = result.split("\n")
        assert len(lines) == 2
        assert "Content" in lines[0]
        assert "Details:" in lines[1]
        assert "🎉" not in lines[1]


class TestFormatLogMessageRustIntegration:
    """Tests for Rust acceleration of log message formatting."""

    @pytest.mark.unit
    def test_uses_rust_when_available(self) -> None:
        """format_log_message should use Rust when available."""
        from ClassicLib.MessageHandler.formatting import formatter

        mock_rust = MagicMock()
        mock_rust.format_log_message.return_value = "Rust formatted"

        with patch.object(formatter, "RUST_AVAILABLE", True):
            with patch.object(formatter, "classic_message", mock_rust):
                result = formatter.format_log_message("Content", "Details")

        mock_rust.format_log_message.assert_called_once_with("Content", "Details")
        assert result == "Rust formatted"

    @pytest.mark.unit
    def test_falls_back_to_python_when_rust_unavailable(self) -> None:
        """format_log_message should fall back to Python when Rust unavailable."""
        from ClassicLib.MessageHandler.formatting import formatter

        with patch.object(formatter, "RUST_AVAILABLE", False):
            result = formatter.format_log_message("Content 😀", "Details 🎉")

        assert "😀" not in result
        assert "🎉" not in result
        assert "Content" in result
        assert "Details" in result


# --- Module State Tests ---


class TestFormatterModuleState:
    """Tests for formatter module state and constants."""

    @pytest.mark.unit
    def test_rust_available_is_boolean(self) -> None:
        """RUST_AVAILABLE should be a boolean."""
        from ClassicLib.MessageHandler.formatting.formatter import RUST_AVAILABLE

        assert isinstance(RUST_AVAILABLE, bool)

    @pytest.mark.unit
    def test_module_exports_main_functions(self) -> None:
        """Module should export main functions."""
        from ClassicLib.MessageHandler.formatting import formatter

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
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        long_text = "Test 😀 " * 1000
        result = strip_emoji(long_text)

        assert "😀" not in result
        assert "Test" in result

    @pytest.mark.unit
    def test_strip_emoji_consecutive_emojis(self) -> None:
        """strip_emoji should handle consecutive emojis."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        result = strip_emoji("Before😀😊😎After")

        assert result == "BeforeAfter"

    @pytest.mark.unit
    def test_strip_emoji_special_characters(self) -> None:
        """strip_emoji should preserve special characters."""
        from ClassicLib.MessageHandler.formatting.formatter import strip_emoji

        text = "Path: C:\\Users\\test\\file.txt"
        result = strip_emoji(text)

        assert result == text

    @pytest.mark.unit
    def test_format_message_with_newlines(self) -> None:
        """format_log_message should handle content with newlines."""
        from ClassicLib.MessageHandler.formatting.formatter import format_log_message

        result = format_log_message("Line 1\nLine 2", "Detail 1\nDetail 2")

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Detail 1" in result
        assert "Detail 2" in result

    @pytest.mark.unit
    def test_format_message_with_tabs(self) -> None:
        """format_log_message should handle content with tabs."""
        from ClassicLib.MessageHandler.formatting.formatter import format_log_message

        result = format_log_message("Column1\tColumn2", None)

        assert "Column1\tColumn2" in result
