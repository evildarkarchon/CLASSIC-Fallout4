"""Tests for async pipeline resource management.

Phase 9: Updated to test Rust orchestrator pipeline.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
class TestAsyncPipelineResourceManagement:
    """Tests for async pipeline resource management."""

    async def test_pipeline_cleanup_on_exception(self, message_handler):
        """Test that pipeline properly cleans up resources on exception."""
        from ClassicLib.scanning.logs.reporting import AsyncCrashLogPipeline

        pipeline = AsyncCrashLogPipeline(
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        # Mock to make processing fail
        with patch("ClassicLib.scanning.logs.reporting.async_crash_log_pipeline.crashlogs_reformat_async") as mock_reformat:
            # Make reformat raise an exception
            mock_reformat.side_effect = Exception("Simulated error")

            # Processing should fail
            with pytest.raises(Exception, match="Simulated error"):
                await pipeline.process_crash_logs_async([], ("test_pattern",))

            # Pipeline should still be in a valid state for cleanup
            assert isinstance(pipeline.performance_stats, dict)

    async def test_pipeline_state_management(self, message_handler):
        """Test that pipeline maintains proper state throughout lifecycle."""
        from ClassicLib.scanning.logs.reporting import AsyncCrashLogPipeline

        pipeline = AsyncCrashLogPipeline(
            fcx_mode=True,
            show_formid_values=True,
            formid_db_exists=True,
        )

        # Check initial state
        assert pipeline.fcx_mode is True
        assert pipeline.show_formid_values is True
        assert pipeline.formid_db_exists is True
        assert isinstance(pipeline.performance_stats, dict)

        # Mock successful processing - just check initialization state
        # The pipeline maintains its state regardless of processing
        assert pipeline.fcx_mode is True
        assert pipeline.show_formid_values is True
