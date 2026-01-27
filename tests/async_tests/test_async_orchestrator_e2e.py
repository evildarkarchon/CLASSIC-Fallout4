"""
E2E tests for async_orchestrator - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

# IMPORTANT: Async Test Pattern Documentation
# ============================================
# This test file follows correct AsyncBridge patterns:
# 1. For sync wrappers using AsyncBridge: Mock bridge.run_async(), not the async function
# 2. For pure async tests: Use @pytest.mark.asyncio and real async/await
# 3. Never use AsyncMock for methods called through AsyncBridge
# 4. See docs/async_test_patterns_guide.md for comprehensive patterns

from collections import Counter
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ClassicLib.scanning.logs.OrchestratorCore import OrchestratorCore

pytestmark = pytest.mark.e2e


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrchestratorCore:
    """Integration tests for OrchestratorCore."""

    async def test_orchestrator_core_batch_processing(self, crash_log_files: list[Path], mock_yamldata: MagicMock) -> None:
        """Test batch processing of crash logs.

        Note: ThreadSafeLogCache was removed for performance reasons.
        OrchestratorCore no longer requires crashlogs parameter and reads files directly.
        """
        # Mock DatabasePoolManager to avoid actual database connections in tests
        with patch("ClassicLib.scanning.logs.OrchestratorCore.DatabasePoolManager") as mock_pool_manager_class:
            mock_pool_manager: MagicMock = MagicMock()
            mock_pool: AsyncMock = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_manager.get_pool = AsyncMock(return_value=mock_pool)
            mock_pool_manager_class.return_value = mock_pool_manager

            async with OrchestratorCore(
                yamldata=mock_yamldata, fcx_mode=False, show_formid_values=False, formid_db_exists=False
            ) as orchestrator:
                with patch.object(orchestrator, "process_crash_log", return_value=(Path("test.log"), ["report"], False, {})):
                    results: list[tuple[Path, list[str], bool, Counter[str]]] = await orchestrator.process_crash_logs_batch(crash_log_files)
                    assert len(results) == 3
                    for result in results:
                        assert len(result) == 4
                        assert isinstance(result[0], Path)
                        assert isinstance(result[1], list)
                        assert isinstance(result[2], bool)
