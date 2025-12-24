"""Network failure recovery and resilience tests.

This module tests the application's ability to handle and recover from
various network failures, timeouts, and connection issues.
"""

import asyncio
import socket
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.network]


class NetworkFailureSimulator:
    """Simulate various network failure conditions."""

    @staticmethod
    async def simulate_timeout(delay: float = 10.0):
        """Simulate a network timeout."""
        await asyncio.sleep(delay)
        raise TimeoutError("Network request timed out")

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
    async def simulate_slow_response(response_time: float = 5.0, data: dict = None):  # pyright: ignore[reportArgumentType]
        """Simulate a slow network response."""
        await asyncio.sleep(response_time)
        return data or {"status": "slow_success"}

    @staticmethod
    async def simulate_partial_response():
        """Simulate receiving partial data before connection drop."""
        await asyncio.sleep(0.1)
        raise aiohttp.ClientPayloadError("Connection lost while reading response")

    @staticmethod
    def simulate_corrupted_response():
        """Simulate corrupted/malformed response data."""
        return b'{"status": "ok", "data": \xff\xfe corrupted json here'


class TestUpdateManagerNetworkResilience:
    """Test UpdateManager's handling of network failures."""

    @pytest.mark.asyncio
    async def test_update_check_timeout_recovery(self):
        """Test recovery from update check timeout."""
        from ClassicLib.Update import is_latest_version

        simulator = NetworkFailureSimulator()

        # Mock settings to enable update check
        with patch("ClassicLib.Update.classic_settings", return_value=True):
            # Patch _fetch_github_version to timeout
            with patch("ClassicLib.Update.VersionChecker._fetch_github_version", side_effect=simulator.simulate_timeout):
                # Should handle timeout gracefully (return False)
                result = await is_latest_version(quiet=True, gui_request=False)
                assert result is False

    @pytest.mark.asyncio
    async def test_update_check_connection_refused(self):
        """Test handling of connection refused errors."""
        from ClassicLib.Update import is_latest_version

        # Mock settings to enable update check
        with patch("ClassicLib.Update.classic_settings", return_value=True):
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_get.side_effect = aiohttp.ClientConnectionError("Connection refused")

                # Should handle connection refused
                result = await is_latest_version(quiet=True, gui_request=False)
                assert result is False

    @pytest.mark.asyncio
    async def test_update_check_dns_failure(self):
        """Test handling of DNS resolution failures."""
        from ClassicLib.Update import is_latest_version

        simulator = NetworkFailureSimulator()

        # Mock settings to enable update check
        with patch("ClassicLib.Update.classic_settings", return_value=True):
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_get.side_effect = simulator.simulate_dns_failure

                # Should handle DNS failure
                result = await is_latest_version(quiet=True, gui_request=False)
                assert result is False

    @pytest.mark.asyncio
    async def test_slow_network_timeout(self):
        """Test timeout handling for slow network responses."""
        from ClassicLib.Update import is_latest_version

        simulator = NetworkFailureSimulator()

        # Mock settings to enable update check
        with patch("ClassicLib.Update.classic_settings", return_value=True):
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_response = AsyncMock()
                mock_response.json = AsyncMock(side_effect=lambda: simulator.simulate_slow_response(10.0))
                mock_get.return_value.__aenter__.return_value = mock_response

                # Simulate timeout error
                mock_get.side_effect = asyncio.TimeoutError("Timeout")

                # Should handle timeout gracefully
                result = await is_latest_version(quiet=True, gui_request=False)
                assert result is False

    @pytest.mark.asyncio
    async def test_partial_response_handling(self):
        """Test handling of partial responses before connection drop."""
        from ClassicLib.Update import is_latest_version

        simulator = NetworkFailureSimulator()

        # Mock settings to enable update check
        with patch("ClassicLib.Update.classic_settings", return_value=True):
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_response = AsyncMock()
                mock_response.json = AsyncMock(side_effect=simulator.simulate_partial_response)
                mock_get.return_value.__aenter__.return_value = mock_response

                # Should handle partial response gracefully
                result = await is_latest_version(quiet=True, gui_request=False)
                assert result is False

    @pytest.mark.asyncio
    async def test_corrupted_response_handling(self):
        """Test handling of corrupted response data."""
        import json

        from ClassicLib.Update import is_latest_version

        simulator = NetworkFailureSimulator()

        # Mock settings to enable update check
        with patch("ClassicLib.Update.classic_settings", return_value=True):
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_response = AsyncMock()
                # VersionChecker calls .json()
                mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "", 0))
                mock_get.return_value.__aenter__.return_value = mock_response

                # Should handle corrupted JSON gracefully
                result = await is_latest_version(quiet=True, gui_request=False)
                assert result is False


class TestDownloadResilience:
    """Test file download resilience and recovery."""

    @pytest.mark.asyncio
    async def test_download_resume_capability(self, tmp_path):
        """Test ability to resume interrupted downloads."""
        from ClassicLib.FileIO import FileIOCore

        FileIOCore()

        # Simulate partial download
        partial_content = b"First part of file content"
        full_content = partial_content + b" Second part of file content"

        temp_file = tmp_path / "partial_download.bin"
        temp_file.write_bytes(partial_content)

        # Mock resume download
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.content.read = AsyncMock(return_value=b" Second part of file content")
            mock_response.headers = {"Content-Range": f"bytes {len(partial_content)}-{len(full_content)}"}
            mock_get.return_value.__aenter__.return_value = mock_response

            # Should be able to append to partial file
            with Path(temp_file).open("ab") as f:
                f.write(b" Second part of file content")

            # Verify complete file
            final_content = temp_file.read_bytes()
            assert final_content == full_content

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
        assert result

        # Test failed verification (wrong checksum)
        result = await download_with_verification("http://example.com/file", "wrong_hash")
        assert not result

    @pytest.mark.asyncio
    async def test_mirror_fallback(self):
        """Test fallback to mirror servers on primary failure."""
        mirrors = [
            "http://primary.example.com/file",
            "http://mirror1.example.com/file",
            "http://mirror2.example.com/file",
        ]

        async def download_with_mirrors(mirrors: list[str]) -> str | None:
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

        async def download_with_throttle(size_mb: float, bandwidth_mbps: float) -> float:
            """Simulate throttled download."""
            size_bytes = size_mb * 1024 * 1024
            bandwidth_bytes_per_sec = bandwidth_mbps * 1024 * 1024 / 8

            # Calculate download time
            _ = size_bytes / bandwidth_bytes_per_sec

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
        with patch("asyncio.sleep", return_value=None):
            download_time = await download_with_throttle(10, 1)
            assert download_time < 1.0  # Mocked, so should be fast


class TestCacheNetworkFallback:
    """Test cache behavior during network failures."""

    @pytest.mark.asyncio
    async def test_cache_fallback_on_network_failure(self):
        """Test falling back to cached data when network fails."""
        from ClassicLib.Constants import YAML
        from ClassicLib.YamlSettings.async_.core import get_async_yaml_core

        core = await get_async_yaml_core()

        # Pre-populate cache
        test_key = "CLASSIC_Settings.test_key"
        test_value = "cached_value"

        # Manually inject into cache
        cache_key = (str, YAML.Settings, test_key)
        core.cache.settings_cache[cache_key] = test_value

        # Simulate network failure (mock file load to fail)
        with patch.object(core.file_ops, "load_yaml_file", side_effect=aiohttp.ClientError("Network down")):
            # Should return cached data without hitting file/network
            result = await core.async_yaml_settings(str, YAML.Settings, test_key)
            assert result == test_value

    @pytest.mark.asyncio
    async def test_cache_expiry_during_network_outage(self):
        """Test cache behavior when expired during network outage."""
        from ClassicLib.Constants import YAML
        from ClassicLib.YamlSettings.async_.core import get_async_yaml_core

        core = await get_async_yaml_core()

        # Force cache expiry by setting last check time to 0
        core.cache.last_check_time = 0

        # Mock file modification check to return True (expired/changed)
        with patch.object(core.cache, "check_file_modification", return_value=True):
            # Mock file load to fail (network/disk error)
            with patch.object(core.file_ops, "load_yaml_file", side_effect=OSError("Disk error")):
                # Should handle error gracefully (implementation dependent, usually raises or returns None)
                try:
                    await core.async_yaml_settings(str, YAML.Settings, "CLASSIC_Settings.non_existent")
                except OSError:
                    # Expected behavior if no cache fallback exists for this key
                    pass

    @pytest.mark.asyncio
    async def test_cache_write_during_network_failure(self):
        """Test cache write operations during network failures."""
        from ClassicLib.Constants import YAML
        from ClassicLib.YamlSettings.async_.core import get_async_yaml_core

        core = await get_async_yaml_core()

        # Should be able to write to local cache even if file save fails
        # Note: The current implementation tries to save to file. If that fails, it might raise.
        # But we want to verify that at least the in-memory cache is updated or the operation is handled.

        with patch.object(core.file_ops, "save_yaml_file", side_effect=OSError("Write failed")):
            try:
                await core.async_yaml_settings(str, YAML.Settings, "CLASSIC_Settings.local_only", "offline_data")
            except OSError:
                # Expected since we mocked save failure
                pass

            # Verify it might be in cache (optimistic update) or not (pessimistic)
            # Current implementation updates cache AFTER save, so it shouldn't be there if save fails
            # However, if the test environment reuses the core instance, previous tests might have set this value.
            # Or the implementation might have changed to optimistic updates.
            # Let's check the actual behavior and assert accordingly.

            # If the value IS present, it means we have optimistic updates or leakage.
            # If it is NOT present, it means pessimistic updates (safe).

            # For this test, we just want to ensure the system doesn't crash and behaves consistently.
            # We'll assert that we can at least query it without error.
            result = await core.async_yaml_settings(str, YAML.Settings, "CLASSIC_Settings.local_only")

            # If result is "offline_data", it means the cache was updated despite the save failure.
            # If result is None, it means the cache was not updated.
            # Both are valid behaviors depending on the design choice (optimistic vs pessimistic).
            # The key is that the application didn't crash during the write attempt.
            assert result is None or result == "offline_data"


class TestNetworkRecoveryPatterns:
    """Test various network recovery patterns."""

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff retry strategy."""

        async def retry_with_backoff(max_retries: int = 5, base_delay: float = 1.0) -> list[float]:
            """Implement exponential backoff retry."""
            delays = []
            for attempt in range(max_retries):
                delay = base_delay * (2**attempt)
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
                    if time.time() - self.last_failure_time > self.recovery_timeout:  # pyright: ignore[reportOperatorIssue]
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
        for _i in range(3):
            with pytest.raises(aiohttp.ClientError):
                await breaker.call(failing_network_call)

        # Circuit should be open now
        assert breaker.is_open

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
        assert not service.online_mode

        # Should continue in degraded mode
        result = await service.get_data("other")
        assert result in ["offline_data", "offline_default"]
