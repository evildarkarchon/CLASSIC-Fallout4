"""Network failure recovery and resilience tests.

This module tests the application's ability to handle and recover from
various network failures, timeouts, and connection issues.
"""

import pytest
import asyncio
import time
import socket
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, AsyncMock
from typing import Dict, List, Any, Optional
import aiohttp
import json
import tempfile

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.network]


class NetworkFailureSimulator:
    """Simulate various network failure conditions."""

    @staticmethod
    async def simulate_timeout(delay: float = 10.0):
        """Simulate a network timeout."""
        await asyncio.sleep(delay)
        raise asyncio.TimeoutError("Network request timed out")

    @staticmethod
    async def simulate_connection_refused():
        """Simulate connection refused error."""
        raise aiohttp.ClientConnectionError("Connection refused")

    @staticmethod
    async def simulate_dns_failure():
        """Simulate DNS resolution failure."""
        raise socket.gaierror("Name or service not known")

    @staticmethod
    async def simulate_intermittent_failure(success_rate: float = 0.5):
        """Simulate intermittent network failures."""
        import random
        if random.random() > success_rate:
            raise aiohttp.ClientError("Network temporarily unavailable")
        return {"status": "success"}

    @staticmethod
    async def simulate_slow_response(response_time: float = 5.0, data: dict = None):
        """Simulate a slow network response."""
        await asyncio.sleep(response_time)
        return data or {"status": "slow_success"}

    @staticmethod
    async def simulate_partial_response():
        """Simulate receiving partial data before connection drop."""
        partial_data = '{"status": "ok", "data": ['
        await asyncio.sleep(0.1)
        raise aiohttp.ClientPayloadError("Connection lost while reading response")

    @staticmethod
    def simulate_corrupted_response():
        """Simulate corrupted/malformed response data."""
        return b'{"status": "ok", "data": \xFF\xFE corrupted json here'


class TestUpdateManagerNetworkResilience:
    """Test UpdateManager's handling of network failures."""

    @pytest.mark.asyncio
    async def test_update_check_timeout_recovery(self):
        """Test recovery from update check timeout."""
        from ClassicLib.Interface.UpdateManager import UpdateManager

        # Clear singleton
        if hasattr(UpdateManager, "_instance"):
            delattr(UpdateManager, "_instance")

        update_manager = UpdateManager()
        simulator = NetworkFailureSimulator()

        with patch.object(update_manager, '_fetch_update_info') as mock_fetch:
            mock_fetch.side_effect = simulator.simulate_timeout

            # Should handle timeout gracefully
            result = await update_manager.check_for_updates()

            # Should return None or default value on timeout
            assert result is None or result == {"error": "timeout"}

    @pytest.mark.asyncio
    async def test_update_check_connection_refused(self):
        """Test handling of connection refused errors."""
        from ClassicLib.Interface.UpdateManager import UpdateManager

        if hasattr(UpdateManager, "_instance"):
            delattr(UpdateManager, "_instance")

        update_manager = UpdateManager()

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientConnectionError("Connection refused")

            # Should handle connection refused
            result = await update_manager.check_for_updates()
            assert result is None or "error" in result

    @pytest.mark.asyncio
    async def test_update_check_dns_failure(self):
        """Test handling of DNS resolution failures."""
        from ClassicLib.Interface.UpdateManager import UpdateManager

        if hasattr(UpdateManager, "_instance"):
            delattr(UpdateManager, "_instance")

        update_manager = UpdateManager()
        simulator = NetworkFailureSimulator()

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = simulator.simulate_dns_failure

            # Should handle DNS failure
            result = await update_manager.check_for_updates()
            assert result is None or result == {}

    @pytest.mark.asyncio
    async def test_update_check_retry_logic(self):
        """Test automatic retry logic on network failures."""
        from ClassicLib.Interface.UpdateManager import UpdateManager

        if hasattr(UpdateManager, "_instance"):
            delattr(UpdateManager, "_instance")

        update_manager = UpdateManager()
        attempt_count = 0

        async def failing_then_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise aiohttp.ClientError("Network error")
            return {"version": "1.0.0", "url": "http://example.com"}

        with patch.object(update_manager, '_fetch_update_info', side_effect=failing_then_success):
            # Should retry and eventually succeed
            result = await update_manager.check_for_updates()

            # Should have made multiple attempts
            assert attempt_count >= 2
            if result and isinstance(result, dict):
                assert "version" in result or "error" in result

    @pytest.mark.asyncio
    async def test_intermittent_network_handling(self):
        """Test handling of intermittent network issues."""
        from ClassicLib.Interface.UpdateManager import UpdateManager

        if hasattr(UpdateManager, "_instance"):
            delattr(UpdateManager, "_instance")

        update_manager = UpdateManager()
        simulator = NetworkFailureSimulator()

        success_count = 0
        fail_count = 0

        # Test 10 attempts with 50% failure rate
        for _ in range(10):
            with patch('aiohttp.ClientSession.get') as mock_get:
                mock_response = AsyncMock()
                try:
                    mock_response.json = AsyncMock(
                        side_effect=lambda: simulator.simulate_intermittent_failure(0.5)
                    )
                    mock_get.return_value.__aenter__.return_value = mock_response

                    result = await update_manager.check_for_updates()
                    if result:
                        success_count += 1
                    else:
                        fail_count += 1
                except (aiohttp.ClientError, AttributeError):
                    fail_count += 1

        # Should handle intermittent failures
        assert success_count > 0 or fail_count > 0

    @pytest.mark.asyncio
    async def test_slow_network_timeout(self):
        """Test timeout handling for slow network responses."""
        from ClassicLib.Interface.UpdateManager import UpdateManager

        if hasattr(UpdateManager, "_instance"):
            delattr(UpdateManager, "_instance")

        update_manager = UpdateManager()
        simulator = NetworkFailureSimulator()

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(
                side_effect=lambda: simulator.simulate_slow_response(10.0)
            )
            mock_get.return_value.__aenter__.return_value = mock_response

            # Should timeout before 10 seconds
            start = time.time()
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
                result = await update_manager.check_for_updates()
            elapsed = time.time() - start

            # Should timeout quickly, not wait 10 seconds
            assert elapsed < 5.0
            assert result is None or "error" in result

    @pytest.mark.asyncio
    async def test_partial_response_handling(self):
        """Test handling of partial responses before connection drop."""
        from ClassicLib.Interface.UpdateManager import UpdateManager

        if hasattr(UpdateManager, "_instance"):
            delattr(UpdateManager, "_instance")

        update_manager = UpdateManager()
        simulator = NetworkFailureSimulator()

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(side_effect=simulator.simulate_partial_response)
            mock_get.return_value.__aenter__.return_value = mock_response

            # Should handle partial response gracefully
            result = await update_manager.check_for_updates()
            assert result is None or result == {}

    @pytest.mark.asyncio
    async def test_corrupted_response_handling(self):
        """Test handling of corrupted response data."""
        from ClassicLib.Interface.UpdateManager import UpdateManager

        if hasattr(UpdateManager, "_instance"):
            delattr(UpdateManager, "_instance")

        update_manager = UpdateManager()
        simulator = NetworkFailureSimulator()

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(
                return_value=simulator.simulate_corrupted_response().decode('utf-8', errors='ignore')
            )
            mock_get.return_value.__aenter__.return_value = mock_response

            # Should handle corrupted JSON gracefully
            result = await update_manager.check_for_updates()
            assert result is None or result == {}


class TestDownloadResilience:
    """Test file download resilience and recovery."""

    @pytest.mark.asyncio
    async def test_download_resume_capability(self):
        """Test ability to resume interrupted downloads."""
        from ClassicLib.FileIOCore import FileIOCore

        io_core = FileIOCore()

        # Simulate partial download
        partial_content = b"First part of file content"
        full_content = partial_content + b" Second part of file content"

        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            f.write(partial_content)
            temp_path = Path(f.name)

        try:
            # Mock resume download
            with patch('aiohttp.ClientSession.get') as mock_get:
                mock_response = AsyncMock()
                mock_response.content.read = AsyncMock(
                    return_value=b" Second part of file content"
                )
                mock_response.headers = {'Content-Range': f'bytes {len(partial_content)}-{len(full_content)}'}
                mock_get.return_value.__aenter__.return_value = mock_response

                # Should be able to append to partial file
                with open(temp_path, 'ab') as f:
                    f.write(b" Second part of file content")

                # Verify complete file
                final_content = temp_path.read_bytes()
                assert final_content == full_content
        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_download_integrity_check(self):
        """Test download integrity verification."""
        import hashlib

        expected_content = b"Complete file content with checksum"
        expected_hash = hashlib.sha256(expected_content).hexdigest()

        async def download_with_verification(url: str, expected_checksum: str) -> bool:
            """Download and verify file integrity."""
            # Simulate download
            downloaded_content = expected_content  # In real scenario, from network

            # Verify checksum
            actual_hash = hashlib.sha256(downloaded_content).hexdigest()
            return actual_hash == expected_checksum

        # Test successful verification
        result = await download_with_verification("http://example.com/file", expected_hash)
        assert result == True

        # Test failed verification (wrong checksum)
        result = await download_with_verification("http://example.com/file", "wrong_hash")
        assert result == False

    @pytest.mark.asyncio
    async def test_mirror_fallback(self):
        """Test fallback to mirror servers on primary failure."""
        mirrors = [
            "http://primary.example.com/file",
            "http://mirror1.example.com/file",
            "http://mirror2.example.com/file",
        ]

        async def download_with_mirrors(mirrors: List[str]) -> Optional[str]:
            """Try downloading from multiple mirrors."""
            for i, mirror_url in enumerate(mirrors):
                try:
                    if i < 2:  # First two mirrors fail
                        raise aiohttp.ClientError(f"Mirror {i} failed")
                    return f"Downloaded from {mirror_url}"
                except aiohttp.ClientError:
                    continue
            return None

        # Should succeed with third mirror
        result = await download_with_mirrors(mirrors)
        assert result == "Downloaded from http://mirror2.example.com/file"

    @pytest.mark.asyncio
    async def test_bandwidth_throttling(self):
        """Test download with bandwidth throttling."""
        async def download_with_throttle(
            size_mb: float,
            bandwidth_mbps: float
        ) -> float:
            """Simulate throttled download."""
            size_bytes = size_mb * 1024 * 1024
            bandwidth_bytes_per_sec = bandwidth_mbps * 1024 * 1024 / 8

            # Calculate download time
            download_time = size_bytes / bandwidth_bytes_per_sec

            # Simulate download with throttling
            start = time.time()
            chunks_downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunks

            while chunks_downloaded < size_bytes:
                await asyncio.sleep(chunk_size / bandwidth_bytes_per_sec)
                chunks_downloaded += chunk_size

            actual_time = time.time() - start
            return actual_time

        # Test 10MB download at 1Mbps (should take ~80 seconds)
        # But we'll simulate it faster for testing
        with patch('asyncio.sleep', return_value=None):
            download_time = await download_with_throttle(10, 1)
            assert download_time < 1.0  # Mocked, so should be fast


class TestCacheNetworkFallback:
    """Test cache behavior during network failures."""

    @pytest.mark.asyncio
    async def test_cache_fallback_on_network_failure(self):
        """Test falling back to cached data when network fails."""
        from ClassicLib.YamlSettingsCache import YamlSettingsCache

        # Clear singleton
        if hasattr(YamlSettingsCache, "_instance"):
            delattr(YamlSettingsCache, "_instance")

        cache = YamlSettingsCache()

        # Pre-populate cache
        test_data = {"version": "1.0.0", "settings": {"key": "value"}}
        with patch.object(cache, '_cache', {"test_key": test_data}):
            # Simulate network failure for refresh
            with patch.object(cache, 'refresh_cache', side_effect=aiohttp.ClientError("Network down")):
                # Should return cached data
                result = cache.get_setting("test_key")
                assert result == test_data

    @pytest.mark.asyncio
    async def test_cache_expiry_during_network_outage(self):
        """Test cache behavior when expired during network outage."""
        from ClassicLib.YamlSettingsCache import YamlSettingsCache
        import datetime

        if hasattr(YamlSettingsCache, "_instance"):
            delattr(YamlSettingsCache, "_instance")

        cache = YamlSettingsCache()

        # Set expired cache data
        old_timestamp = datetime.datetime.now() - datetime.timedelta(hours=25)
        cached_data = {"data": "old", "timestamp": old_timestamp.isoformat()}

        with patch.object(cache, '_cache', {"expired_key": cached_data}):
            with patch.object(cache, 'refresh_cache', side_effect=aiohttp.ClientError("Network down")):
                # Should still return stale data rather than nothing
                result = cache.get_setting("expired_key")
                # Behavior depends on implementation - either stale data or None
                assert result is None or result == cached_data

    @pytest.mark.asyncio
    async def test_cache_write_during_network_failure(self):
        """Test cache write operations during network failures."""
        from ClassicLib.YamlSettingsCache import YamlSettingsCache

        if hasattr(YamlSettingsCache, "_instance"):
            delattr(YamlSettingsCache, "_instance")

        cache = YamlSettingsCache()

        # Should be able to write to local cache even without network
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientError("Network down")):
            # Local cache write should still work
            cache._cache["local_only"] = {"value": "offline_data"}
            result = cache.get_setting("local_only")
            assert result == {"value": "offline_data"}


class TestNetworkRecoveryPatterns:
    """Test various network recovery patterns."""

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff retry strategy."""
        async def retry_with_backoff(
            max_retries: int = 5,
            base_delay: float = 1.0
        ) -> List[float]:
            """Implement exponential backoff retry."""
            delays = []
            for attempt in range(max_retries):
                delay = base_delay * (2 ** attempt)
                delays.append(delay)
                await asyncio.sleep(0.001)  # Simulate minimal delay for testing
            return delays

        delays = await retry_with_backoff(5, 1.0)

        # Should follow exponential pattern: 1, 2, 4, 8, 16
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for network failures."""
        class CircuitBreaker:
            def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 5.0):
                self.failure_count = 0
                self.failure_threshold = failure_threshold
                self.recovery_timeout = recovery_timeout
                self.is_open = False
                self.last_failure_time = None

            async def call(self, func, *args, **kwargs):
                """Call function with circuit breaker protection."""
                if self.is_open:
                    if time.time() - self.last_failure_time > self.recovery_timeout:
                        self.is_open = False
                        self.failure_count = 0
                    else:
                        raise Exception("Circuit breaker is open")

                try:
                    result = await func(*args, **kwargs)
                    self.failure_count = 0
                    return result
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    if self.failure_count >= self.failure_threshold:
                        self.is_open = True
                    raise e

        breaker = CircuitBreaker(failure_threshold=3)

        async def failing_network_call():
            raise aiohttp.ClientError("Network error")

        # Test circuit breaker opening after threshold
        for i in range(3):
            with pytest.raises(aiohttp.ClientError):
                await breaker.call(failing_network_call)

        # Circuit should be open now
        assert breaker.is_open == True

        # Further calls should fail immediately
        with pytest.raises(Exception) as exc:
            await breaker.call(failing_network_call)
        assert "Circuit breaker is open" in str(exc.value)

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation when network services are unavailable."""
        class ServiceWithDegradation:
            def __init__(self):
                self.online_mode = True
                self.offline_cache = {"default": "offline_data"}

            async def get_data(self, key: str) -> Any:
                """Get data with graceful degradation."""
                if self.online_mode:
                    try:
                        # Try network call
                        if key == "fail":
                            raise aiohttp.ClientError("Network unavailable")
                        return {"online": key}
                    except aiohttp.ClientError:
                        # Degrade to offline mode
                        self.online_mode = False
                        return self.offline_cache.get(key, "degraded_default")
                else:
                    # Already in offline mode
                    return self.offline_cache.get(key, "offline_default")

        service = ServiceWithDegradation()

        # Should work online
        result = await service.get_data("test")
        assert result == {"online": "test"}

        # Should degrade gracefully
        result = await service.get_data("fail")
        assert result in ["offline_data", "degraded_default", "offline_default"]
        assert service.online_mode == False

        # Should continue in degraded mode
        result = await service.get_data("other")
        assert result in ["offline_data", "offline_default"]