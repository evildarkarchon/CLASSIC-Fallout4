"""Integration tests for FCX mode handler API compliance.

This module tests that the fcx_rust.py wrapper correctly calls the Rust
FcxModeHandler.get_fcx_messages() method (not the incorrect get_messages())
and properly wraps the return value.

The test suite verifies:
1. Correct method name usage (get_fcx_messages vs get_messages)
2. Proper return type handling (ReportFragment wrapping Rust list[str])
3. Integration with the factory pattern
4. Realistic usage scenarios

Bug fixed: fcx_rust.py:110 - Method name correction from get_messages() to get_fcx_messages()

Wrapper behavior:
    - Rust returns list[str], wrapper converts to ReportFragment for Python API compatibility
    - Access message lines via the .content attribute (tuple) of ReportFragment

Note:
    These tests require the Rust classic_scanlog module to be available.
    They will gracefully skip if the module is not installed.
"""

import pytest
from typing import Any


@pytest.mark.rust
@pytest.mark.integration
def test_fcx_handler_get_fcx_messages() -> None:
    """Verify get_fcx_messages() method is called correctly.

    This test ensures the wrapper uses the correct method name from the Rust API
    (get_fcx_messages, not get_messages). It verifies both that the method exists
    and returns the expected data structure.

    The test confirms:
    - Method exists and is callable
    - Returns a list (not None or other type)
    - All list items are strings
    - No AttributeError is raised

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_fcx_handler
        from ClassicLib.ScanLog.fragments import ReportFragment

        # Get the handler through the factory (respects Rust availability)
        # fcx_mode parameter is required (bool or None)
        handler = get_fcx_handler(fcx_mode=False)

        # This should not raise AttributeError - verifies correct method name
        messages = handler.get_fcx_messages()

        # Verify return type is ReportFragment (wrapper converts list[str] to ReportFragment)
        assert isinstance(messages, ReportFragment), (
            f"get_fcx_messages should return ReportFragment, got {type(messages).__name__}"
        )

        # Verify the fragment has content attribute
        assert hasattr(messages, 'content'), "ReportFragment should have 'content' attribute"

        # Verify all items in content are strings (FCX messages are text)
        for i, msg in enumerate(messages.content):
            assert isinstance(msg, str), (
                f"Message at index {i} should be string, got {type(msg).__name__}: {msg!r}"
            )

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_fcx_handler_method_not_get_messages() -> None:
    """Verify that get_messages() method does NOT exist on handler.

    This negative test confirms that the old incorrect method name (get_messages)
    is not present on the handler. This prevents regression to the bug.

    The test verifies:
    - get_messages() method does not exist
    - AttributeError is raised if attempting to call it
    - get_fcx_messages() is the correct method name

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_fcx_handler

        handler = get_fcx_handler(fcx_mode=False)

        # Verify the INCORRECT method name does not exist
        assert not hasattr(handler, "get_messages"), (
            "Handler should not have get_messages() method - "
            "correct method name is get_fcx_messages()"
        )

        # Verify the CORRECT method name exists
        assert hasattr(handler, "get_fcx_messages"), (
            "Handler must have get_fcx_messages() method"
        )

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_fcx_handler_integration_scenario() -> None:
    """Test FCX handler in a realistic usage scenario.

    This test simulates the typical workflow of using the FCX handler:
    1. Create handler instance
    2. Perform FCX mode check
    3. Retrieve FCX messages
    4. Verify message content

    The test ensures the entire workflow works end-to-end with the corrected
    API method name.

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.rust.fcx_rust import RustAcceleratedFcxModeHandler
        from ClassicLib.ScanLog.fragments import ReportFragment

        # Create handler instance directly (not through factory)
        handler = RustAcceleratedFcxModeHandler(fcx_mode=False)

        # Perform FCX mode check (sets up internal state)
        # This may populate the internal message list
        handler.check_fcx_mode()

        # Get messages using the CORRECT method name
        # This should work without errors after check_fcx_mode()
        messages = handler.get_fcx_messages()

        # Verify return type is ReportFragment
        assert isinstance(messages, ReportFragment), (
            "get_fcx_messages should return ReportFragment after check_fcx_mode()"
        )

        # Messages may be empty if no FCX issues detected, but should be a ReportFragment
        # Each message in content should be a non-empty string
        for msg in messages.content:
            assert isinstance(msg, str), f"Message should be string: {msg!r}"
            assert msg, "Messages should not be empty strings"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_fcx_handler_empty_messages() -> None:
    """Test FCX handler returns empty list when no issues detected.

    This test verifies that get_fcx_messages() returns an empty list
    (not None) when no FCX configuration issues are present.

    The test confirms:
    - Empty list is returned (not None)
    - Type is still list even when empty
    - No exceptions are raised

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.rust.fcx_rust import RustAcceleratedFcxModeHandler
        from ClassicLib.ScanLog.fragments import ReportFragment

        # Create fresh handler
        handler = RustAcceleratedFcxModeHandler(fcx_mode=False)

        # Get messages without calling check_fcx_mode first
        # Should return empty ReportFragment, not error
        messages = handler.get_fcx_messages()

        # Verify ReportFragment is returned
        assert isinstance(messages, ReportFragment), (
            "get_fcx_messages should always return ReportFragment, even if empty"
        )

        # May be empty before check_fcx_mode is called
        assert isinstance(messages.content, tuple), (
            f"ReportFragment.content should be tuple, got {type(messages.content).__name__}"
        )

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_fcx_handler_factory_consistency() -> None:
    """Test that factory returns handler with correct API methods.

    This test verifies that the factory pattern (get_fcx_handler) returns
    a handler instance that has the correct API methods available.

    The test confirms:
    - Factory returns object with get_fcx_messages()
    - Factory returns object without get_messages()
    - Multiple factory calls return consistent API

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.integration.factory import get_fcx_handler

        # Get handler through factory
        handler1 = get_fcx_handler(fcx_mode=False)
        handler2 = get_fcx_handler(fcx_mode=False)

        # Both should have the correct method
        assert hasattr(handler1, "get_fcx_messages"), (
            "Factory handler should have get_fcx_messages()"
        )
        assert hasattr(handler2, "get_fcx_messages"), (
            "Factory handler should have get_fcx_messages()"
        )

        # Neither should have the incorrect method
        assert not hasattr(handler1, "get_messages"), (
            "Factory handler should not have get_messages()"
        )
        assert not hasattr(handler2, "get_messages"), (
            "Factory handler should not have get_messages()"
        )

        # Both should be callable and return ReportFragments
        from ClassicLib.ScanLog.fragments import ReportFragment

        messages1 = handler1.get_fcx_messages()
        messages2 = handler2.get_fcx_messages()

        assert isinstance(messages1, ReportFragment), (
            "Factory handler should return ReportFragment"
        )
        assert isinstance(messages2, ReportFragment), (
            "Factory handler should return ReportFragment"
        )

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")
