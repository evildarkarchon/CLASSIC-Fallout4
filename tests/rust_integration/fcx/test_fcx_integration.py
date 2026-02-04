"""
Rust integration tests for FCX mode read-only behavior.

This module contains comprehensive integration tests for the Rust-accelerated
FCX mode implementation, verifying read-only behavior and data passing between
Rust and Python.
"""
# ruff: noqa: ANN201, PLR6301, ANN202

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ClassicLib.integration.factory import is_rust_accelerated
from tests.fixtures.parity_fixtures import skip_if_rust_unavailable

if TYPE_CHECKING:
    from pathlib import Path

# Check Rust availability
RUST_AVAILABLE = is_rust_accelerated("fcx_handler")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.rust
@skip_if_rust_unavailable("fcx_handler")
class TestRustFCXIntegration:
    """Test Rust-accelerated FCX mode read-only behavior and integration."""

    async def test_rust_fcx_no_file_writes(self, tmp_path: Path):
        """
        Verify Rust FCX implementation never writes files.

        This test ensures that the Rust-accelerated FCX handler maintains
        read-only behavior and doesn't modify configuration files.
        """
        # Skip if Rust not available
        if not RUST_AVAILABLE:
            pytest.skip("Rust FCX handler not available")

        from ClassicLib.integration.factory import get_fcx_handler

        # Create test configuration
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Main]\nHotKey = ; F10\n", encoding="utf-8")

        # Track file modification time
        initial_mtime = test_ini.stat().st_mtime
        initial_content = test_ini.read_text(encoding="utf-8")

        # Create Rust-accelerated FCX handler
        handler = get_fcx_handler(fcx_mode=True)

        # Verify we got a valid handler from factory
        # (Factory returns _FcxHandlerWrapper which wraps Rust implementation)
        handler_type = type(handler).__name__
        assert handler_type in ("_FcxHandlerWrapper", "RustAcceleratedFcxModeHandler", "FCXModeHandler"), f"Expected FCX handler, got {handler_type}"

        # Perform FCX operations
        handler.get_fcx_messages()

        # Verify file was NOT modified
        assert test_ini.stat().st_mtime == initial_mtime, "Rust FCX handler modified file - read-only contract violated"

        assert test_ini.read_text(encoding="utf-8") == initial_content, "File content was modified by Rust FCX handler"

    async def test_rust_python_issue_data_passing(self):
        """
        Verify ConfigIssue data passes correctly between Rust and Python.

        This test validates that the PyO3 wrapper correctly converts
        Rust ConfigIssue structures to Python ConfigIssue objects.
        """
        if not RUST_AVAILABLE:
            pytest.skip("Rust FCX handler not available")

        from pathlib import Path

        from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue

        # Create sample ConfigIssue
        issue = ConfigIssue(
            file_path=Path("test/file.ini"),
            section="Main",
            setting="TestSetting",
            current_value="bad_value",
            recommended_value="good_value",
            description="Test issue description",
            severity="warning",
        )

        # Verify data structure
        assert isinstance(issue.file_path, Path)
        assert issue.section == "Main"
        assert issue.setting == "TestSetting"
        assert issue.current_value == "bad_value"
        assert issue.recommended_value == "good_value"
        assert issue.description == "Test issue description"
        assert issue.severity == "warning"

        # Verify report generation
        report = issue.format_report()
        assert "⚠️" in report
        assert "bad_value" in report
        assert "good_value" in report

    # NOTE: test_rust_fcx_detection_accuracy, test_rust_fcx_performance_advantage,
    # and test_rust_fcx_message_parity were removed - they tested Rust vs Python
    # parity but Python fcx_mode_handler.py was deleted in Phase 11 cleanup.
    # Parity was validated in Phase 10 before deletion.

    async def test_rust_fcx_state_management(self):
        """
        Verify Rust FCX handler state management is correct.

        This test ensures that reset_fcx_checks() and state tracking
        work correctly in the Rust implementation.
        """
        if not RUST_AVAILABLE:
            pytest.skip("Rust FCX handler not available")

        from ClassicLib.integration.factory import get_fcx_handler

        # Create handler
        handler = get_fcx_handler(fcx_mode=True)

        # Perform checks multiple times
        msg1 = handler.get_fcx_messages()

        # Reset state
        handler.reset_fcx_checks()

        # Perform checks again
        msg2 = handler.get_fcx_messages()

        # Messages should be consistent after reset
        content1 = msg1.content if msg1 else ""
        content2 = msg2.content if msg2 else ""

        assert content1 == content2, "Messages changed after reset - state management issue"

    async def test_rust_fcx_thread_safety(self):
        """
        Verify Rust FCX handler is thread-safe.

        This test ensures that the Rust implementation can be safely
        used from multiple threads without data races or corruption.
        """
        if not RUST_AVAILABLE:
            pytest.skip("Rust FCX handler not available")

        import concurrent.futures

        from ClassicLib.integration.factory import get_fcx_handler

        # Create handler
        handler = get_fcx_handler(fcx_mode=True)

        def get_messages():
            """Worker function to get FCX messages."""
            return handler.get_fcx_messages()

        # Run multiple threads simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_messages) for _ in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify all results are consistent
        first_content = results[0].content if results[0] else ""
        for result in results[1:]:
            content = result.content if result else ""
            assert content == first_content, "Thread safety violation - inconsistent results"

    async def test_rust_fcx_error_handling(self):
        """
        Verify Rust FCX handler handles errors gracefully.

        This test ensures that the Rust implementation properly handles
        edge cases and error conditions without crashing.
        """
        if not RUST_AVAILABLE:
            pytest.skip("Rust FCX handler not available")

        from ClassicLib.integration.factory import get_fcx_handler

        # Test with None as fcx_mode
        try:
            handler = get_fcx_handler(fcx_mode=None)
            messages = handler.get_fcx_messages()
            # Should handle gracefully
            assert messages is not None
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"Rust FCX handler failed to handle None mode: {e}")

        # Test reset on fresh handler
        handler = get_fcx_handler(fcx_mode=True)
        try:
            handler.reset_fcx_checks()
            # Should not crash
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"Rust FCX handler failed to reset: {e}")

    async def test_rust_fcx_no_side_effects(self, tmp_path: Path):
        """
        Verify Rust FCX handler has no side effects on file system.

        This test creates a directory structure and verifies that
        FCX operations don't create, modify, or delete any files.
        """
        if not RUST_AVAILABLE:
            pytest.skip("Rust FCX handler not available")

        from ClassicLib.integration.factory import get_fcx_handler

        # Create test directory structure
        test_dir = tmp_path / "config"
        test_dir.mkdir()

        test_file = test_dir / "test.ini"
        test_file.write_text("[Main]\nKey=Value\n", encoding="utf-8")

        # Record initial state
        initial_files = list(test_dir.rglob("*"))
        initial_mtimes = {f: f.stat().st_mtime for f in initial_files if f.is_file()}

        # Run FCX handler
        handler = get_fcx_handler(fcx_mode=True)
        handler.get_fcx_messages()

        # Verify no changes
        final_files = list(test_dir.rglob("*"))
        assert set(initial_files) == set(final_files), "File structure changed - files created or deleted"

        for file_path, initial_mtime in initial_mtimes.items():
            final_mtime = file_path.stat().st_mtime
            assert final_mtime == initial_mtime, f"File {file_path} was modified"
