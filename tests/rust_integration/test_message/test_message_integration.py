"""Integration tests for classic-message Rust module.

This module tests the message routing and formatting with Rust acceleration.
"""

import pytest

try:
    import classic_message

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

pytestmark = [
    pytest.mark.integration,
    pytest.mark.rust,
    pytest.mark.skipif(not RUST_AVAILABLE, reason="classic_message not available"),
]


class TestMessageType:
    """Test MessageType enum."""

    def test_message_type_values(self):
        """Test that all message types exist."""
        assert classic_message.MessageType.Info
        assert classic_message.MessageType.Warning
        assert classic_message.MessageType.Error
        assert classic_message.MessageType.Success
        assert classic_message.MessageType.Progress
        assert classic_message.MessageType.Debug
        assert classic_message.MessageType.Critical

    def test_message_type_name(self):
        """Test message type name method."""
        assert classic_message.MessageType.Info.name() == "Info"
        assert classic_message.MessageType.Warning.name() == "Warning"
        assert classic_message.MessageType.Error.name() == "Error"

    def test_message_type_str(self):
        """Test message type string representation."""
        msg_type = classic_message.MessageType.Info
        assert str(msg_type) == "Info"
        assert "MessageType" in repr(msg_type)


class TestMessageTarget:
    """Test MessageTarget enum."""

    def test_message_target_values(self):
        """Test that all message targets exist."""
        assert classic_message.MessageTarget.All
        assert classic_message.MessageTarget.GuiOnly
        assert classic_message.MessageTarget.CliOnly
        assert classic_message.MessageTarget.LogOnly
        assert classic_message.MessageTarget.Gui
        assert classic_message.MessageTarget.Console

    def test_should_display_in_gui(self):
        """Test GUI display logic."""
        assert classic_message.MessageTarget.All.should_display_in_gui()
        assert classic_message.MessageTarget.Gui.should_display_in_gui()
        assert classic_message.MessageTarget.GuiOnly.should_display_in_gui()
        assert not classic_message.MessageTarget.Console.should_display_in_gui()
        assert not classic_message.MessageTarget.LogOnly.should_display_in_gui()

    def test_should_display_in_cli(self):
        """Test CLI display logic."""
        assert classic_message.MessageTarget.All.should_display_in_cli()
        assert classic_message.MessageTarget.Console.should_display_in_cli()
        assert classic_message.MessageTarget.CliOnly.should_display_in_cli()
        assert not classic_message.MessageTarget.Gui.should_display_in_cli()
        assert not classic_message.MessageTarget.LogOnly.should_display_in_cli()

    def test_should_display(self):
        """Test display logic."""
        assert classic_message.MessageTarget.All.should_display()
        assert classic_message.MessageTarget.Gui.should_display()
        assert classic_message.MessageTarget.Console.should_display()
        assert not classic_message.MessageTarget.LogOnly.should_display()


class TestMessage:
    """Test Message class."""

    def test_message_creation(self):
        """Test basic message creation."""
        msg = classic_message.Message("Test content", classic_message.MessageType.Info)
        assert msg.content() == "Test content"
        assert msg.msg_type() == classic_message.MessageType.Info
        assert msg.target() == classic_message.MessageTarget.All

    def test_message_with_target(self):
        """Test message creation with target."""
        msg = classic_message.Message.with_target(
            "GUI message", classic_message.MessageType.Info, classic_message.MessageTarget.Gui
        )
        assert msg.content() == "GUI message"
        assert msg.target() == classic_message.MessageTarget.Gui

    def test_message_with_title(self):
        """Test message builder with title."""
        msg = classic_message.Message("Content", classic_message.MessageType.Info)
        msg = msg.with_title("Title")
        assert msg.title() == "Title"

    def test_message_with_details(self):
        """Test message builder with details."""
        msg = classic_message.Message("Error", classic_message.MessageType.Error)
        msg = msg.with_details("Stack trace here")
        assert msg.details() == "Stack trace here"

    def test_message_builder_chain(self):
        """Test method chaining."""
        msg = classic_message.Message("Content", classic_message.MessageType.Success)
        msg = msg.with_title("Success").with_details("Operation completed")

        assert msg.content() == "Content"
        assert msg.title() == "Success"
        assert msg.details() == "Operation completed"

    def test_message_setters(self):
        """Test message setters."""
        msg = classic_message.Message("Original", classic_message.MessageType.Info)

        msg.set_content("Updated")
        assert msg.content() == "Updated"

        msg.set_msg_type(classic_message.MessageType.Warning)
        assert msg.msg_type() == classic_message.MessageType.Warning

        msg.set_target(classic_message.MessageTarget.Gui)
        assert msg.target() == classic_message.MessageTarget.Gui

        msg.set_title("New Title")
        assert msg.title() == "New Title"

        msg.set_details("New Details")
        assert msg.details() == "New Details"

    def test_message_optional_fields(self):
        """Test message optional fields."""
        msg = classic_message.Message("Content", classic_message.MessageType.Info)
        assert msg.title() is None
        assert msg.details() is None

    def test_message_str_repr(self):
        """Test message string representation."""
        msg = classic_message.Message("Test", classic_message.MessageType.Info)
        assert str(msg) == "Test"
        assert "Message" in repr(msg)


class TestFormatter:
    """Test formatting functions."""

    def test_strip_emoji_no_emojis(self):
        """Test stripping with no emojis."""
        text = "Hello, world!"
        assert classic_message.strip_emoji(text) == "Hello, world!"

    def test_strip_emoji_with_emojis(self):
        """Test stripping emojis."""
        text = "Hello 👋 World 🌍!"
        result = classic_message.strip_emoji(text)
        assert "👋" not in result
        assert "🌍" not in result
        assert "Hello" in result
        assert "World" in result

    def test_strip_emoji_only_emojis(self):
        """Test stripping only emojis."""
        text = "👋🌍🎉"
        result = classic_message.strip_emoji(text)
        assert len(result) == 0 or result.strip() == ""

    def test_strip_emoji_mixed_content(self):
        """Test stripping mixed content."""
        text = "✅ Success! Operation completed 🎉"
        result = classic_message.strip_emoji(text)
        assert "✅" not in result
        assert "🎉" not in result
        assert "Success" in result
        assert "Operation completed" in result

    def test_format_log_message_no_details(self):
        """Test formatting without details."""
        formatted = classic_message.format_log_message("Test message 🎉", None)
        assert "🎉" not in formatted
        assert "Test message" in formatted
        assert "Details:" not in formatted

    def test_format_log_message_with_details(self):
        """Test formatting with details."""
        formatted = classic_message.format_log_message("Error ❌", "Stack trace 🔍")
        assert "❌" not in formatted
        assert "🔍" not in formatted
        assert "Error" in formatted
        assert "Details:" in formatted
        assert "Stack trace" in formatted

    def test_format_log_message_clean_text(self):
        """Test formatting clean text."""
        formatted = classic_message.format_log_message("Clean message", "Clean details")
        assert formatted == "Clean message\nDetails: Clean details"


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_message_routing_workflow(self):
        """Test complete message routing workflow."""
        # Create messages for different targets
        gui_msg = classic_message.Message.with_target(
            "GUI message", classic_message.MessageType.Info, classic_message.MessageTarget.Gui
        )
        cli_msg = classic_message.Message.with_target(
            "CLI message", classic_message.MessageType.Info, classic_message.MessageTarget.Console
        )
        all_msg = classic_message.Message("All message", classic_message.MessageType.Info)

        # Verify routing
        assert gui_msg.target().should_display_in_gui()
        assert not gui_msg.target().should_display_in_cli()

        assert not cli_msg.target().should_display_in_gui()
        assert cli_msg.target().should_display_in_cli()

        assert all_msg.target().should_display_in_gui()
        assert all_msg.target().should_display_in_cli()

    def test_message_formatting_workflow(self):
        """Test complete message formatting workflow."""
        msg = classic_message.Message("Success! ✅", classic_message.MessageType.Success)
        msg = msg.with_title("Operation Complete").with_details("All tests passed 🎉")

        # Format for logging
        log_text = classic_message.format_log_message(msg.content(), msg.details())

        # Verify emojis removed
        assert "✅" not in log_text
        assert "🎉" not in log_text

        # Verify content preserved
        assert "Success" in log_text
        assert "All tests passed" in log_text
        assert "Details:" in log_text

    def test_message_type_all_variants(self):
        """Test all message type variants."""
        types = [
            classic_message.MessageType.Info,
            classic_message.MessageType.Warning,
            classic_message.MessageType.Error,
            classic_message.MessageType.Success,
            classic_message.MessageType.Progress,
            classic_message.MessageType.Debug,
            classic_message.MessageType.Critical,
        ]

        for msg_type in types:
            msg = classic_message.Message("Test", msg_type)
            assert msg.msg_type() == msg_type
            assert msg.msg_type().name() is not None


class TestModuleInfo:
    """Test module information and Rust acceleration detection."""

    def test_module_imported(self):
        """Test that classic_message module is available."""
        assert classic_message is not None

    def test_all_types_available(self):
        """Test that all expected types are available."""
        assert hasattr(classic_message, "MessageType")
        assert hasattr(classic_message, "MessageTarget")
        assert hasattr(classic_message, "Message")
        assert hasattr(classic_message, "strip_emoji")
        assert hasattr(classic_message, "format_log_message")

    def test_rust_acceleration_active(self):
        """Test that Rust acceleration is being used."""
        # The module should have __file__ with a .pyd extension
        assert hasattr(classic_message, "__file__")
        # Check if there's a .pyd file in the module directory
        from pathlib import Path

        module_dir = Path(classic_message.__file__).parent
        pyd_files = list(module_dir.glob("*.pyd"))
        assert len(pyd_files) > 0, f"No .pyd files found in {module_dir}"
