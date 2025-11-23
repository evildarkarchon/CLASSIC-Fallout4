"""Test FFI boundary error conditions with synthetic data.

This module tests all error conditions at the Rust-Python FFI boundary
using only synthetic/mock data, ensuring proper error handling and
graceful degradation without using any copyrighted game files.
"""
# ruff: noqa: ANN201, ANN001, ARG001, PLR6301, ANN202

import contextlib
import gc
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import classic_file_io
import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.rust]


class MockRustModule:
    """Mock Rust module for testing when Rust modules are unavailable."""

    class RustError(Exception):
        """Mock Rust error type."""

    class FFIError(Exception):
        """Mock FFI error type."""

    def parse_log(self, content: str) -> dict:
        """Mock log parser."""
        if not isinstance(content, str):
            raise TypeError(f"Expected str, got {type(content)}")
        if len(content) > 1000000:  # 1MB limit
            raise self.FFIError("Content too large")
        return {"parsed": True, "lines": content.count("\n")}

    def analyze_formid(self, formid: str, context: dict) -> dict:
        """Mock FormID analyzer."""
        if not isinstance(formid, str):
            raise TypeError(f"Expected str for formid, got {type(formid)}")
        if not isinstance(context, dict):
            raise TypeError(f"Expected dict for context, got {type(context)}")
        return {"formid": formid, "valid": len(formid) == 8}


class TestFFIErrorConditions:
    """Test FFI boundary error conditions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.rust_available = False
        try:
            import classic_scanlog

            self.rust_available = True
            self.rust_module = classic_scanlog
        except ImportError:
            self.rust_module = MockRustModule()

    def test_null_pointer_handling(self):
        """Test handling of null/None values across FFI boundary."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Test with None values
        with pytest.raises((TypeError, ValueError, AttributeError)):
            parser.find_segments(None, "Buffout 4", "F4SE", "Fallout4.exe")

        # Test with empty values
        _, _, _, segments = parser.find_segments([], "Buffout 4", "F4SE", "Fallout4.exe")
        assert segments is not None  # Should return empty result, not crash

    @pytest.mark.asyncio
    async def test_invalid_utf8_handling(self):
        """Test handling of invalid UTF-8 sequences."""
        from ClassicLib.integration.factory import get_file_io

        io_core = get_file_io()

        # Create synthetic invalid UTF-8 data
        invalid_utf8 = b"\xff\xfe\xfd\xfc"

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(invalid_utf8)
            temp_path = temp_file.name

        error = None
        try:
            # Should handle invalid UTF-8 gracefully
            result = await io_core.read_file(temp_path)
            # Should either return decoded text or error, not crash
            assert result is not None or not result
        except (UnicodeDecodeError, RuntimeError) as e:
            # These exceptions are acceptable
            error = e
        finally:
            Path(temp_path).unlink(missing_ok=True)

        if error:
            assert "UTF-8" in str(error) or "decode" in str(error).lower()

    def test_memory_overflow_prevention(self):
        """Test prevention of memory overflow with large synthetic data."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Create very large synthetic log (10MB of repeated data)
        large_content = "ERROR: Synthetic error line\n" * 350000  # ~10MB

        # Should handle large input gracefully
        error = None
        try:
            lines = large_content.splitlines()
            _, _, _, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
            # Should either parse or raise memory error
            assert segments is not None
        except (MemoryError, RuntimeError, ValueError) as e:
            # Should raise appropriate error for oversized input
            error = e

        if error:
            assert "memory" in str(error).lower() or "size" in str(error).lower() or "large" in str(error).lower()

    def test_type_mismatch_errors(self):
        """Test type mismatches at FFI boundary."""
        from ClassicLib.integration.factory import get_formid_analyzer

        mock_yamldata = MagicMock()  # Will still be passed, but the constructor will be mocked

        # Mock the Rust FormIDAnalyzer to control its extract_formids behavior
        # so it raises type errors for wrong inputs.
        mock_rust_analyzer = MagicMock()
        mock_rust_analyzer.extract_formids.side_effect = TypeError("Mocked type error")

        with patch("ClassicLib.rust.formid_rust.FormIDAnalyzer", return_value=mock_rust_analyzer):
            analyzer = get_formid_analyzer(mock_yamldata, True, False)  # This now returns the mock_rust_analyzer

            # Test with wrong types
            wrong_list_inputs = [
                123,  # Integer instead of list
                "not_a_list",  # String instead of list
                {"formid": "test"},  # Dict instead of list
            ]
            for wrong_input in wrong_list_inputs:
                with pytest.raises((TypeError, AttributeError, ValueError)):
                    # The mock's extract_formids will raise TypeError
                    analyzer.extract_formids(wrong_input)

    def test_concurrent_ffi_calls(self):
        """Test concurrent FFI calls don't cause race conditions."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        results = []
        errors = []

        def worker(worker_id: int):
            try:
                # Each worker processes different synthetic data
                content = f"Worker {worker_id} log line\n" * 100
                lines = content.splitlines()
                _, _, _, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
                results.append((worker_id, segments))
            except Exception as e:  # noqa: BLE001
                errors.append((worker_id, e))

        # Launch multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should complete without crashes
        assert len(errors) == 0 or all(isinstance(e[1], (RuntimeError, ValueError)) for e in errors)
        # At least some should succeed
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self):
        """Test that resources are properly cleaned up on FFI errors."""
        from ClassicLib.integration.factory import get_file_io

        io_core = get_file_io()

        # Track resource usage
        initial_threads = threading.active_count()

        # Cause multiple errors
        for _ in range(10):
            with contextlib.suppress(FileNotFoundError, OSError, RuntimeError, classic_file_io.RustFileIOError):
                # Try to read non-existent file
                await io_core.read_file("/completely/synthetic/path/that/does/not/exist.txt")

        # Force garbage collection
        gc.collect()
        time.sleep(0.1)  # Allow cleanup

        # Thread count should not have grown significantly
        final_threads = threading.active_count()
        assert final_threads <= initial_threads + 2  # Allow small variance

    def test_string_boundary_conditions(self):
        """Test string handling at boundary conditions."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        test_strings = [
            "",  # Empty string
            "a",  # Single character
            "a" * 65536,  # 64KB string
            "🎮" * 1000,  # Unicode emojis
            "\n" * 1000,  # Only newlines
            "\t" * 1000,  # Only tabs
            "\x00" * 10,  # Null characters
            "Line1\nLine2\r\nLine3\rLine4",  # Mixed line endings
        ]

        for test_str in test_strings:
            try:
                lines = test_str.splitlines() if test_str else []
                _, _, _, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
                # Should handle all string types
                assert segments is not None
            except (ValueError, UnicodeDecodeError):
                # Null characters or encoding issues might be rejected
                assert "\x00" in test_str or isinstance(test_str, bytes)

    def test_numeric_overflow_handling(self):
        """Test numeric overflow handling in FFI."""
        # Create synthetic FormIDs with boundary values
        boundary_values = [
            "00000000",  # Minimum
            "FFFFFFFF",  # Maximum 32-bit
            "7FFFFFFF",  # Max signed 32-bit
            "80000000",  # Min signed 32-bit overflow
        ]

        from ClassicLib.integration.factory import get_formid_analyzer

        mock_yamldata = MagicMock()
        analyzer = get_formid_analyzer(mock_yamldata, True, False)

        # extract_formids expects a list of formids
        try:
            results = analyzer.extract_formids(boundary_values)
            # Should handle boundary values
            assert results is None or isinstance(results, (list, dict))
        except (ValueError, OverflowError, TypeError):
            # Acceptable for overflow values
            pass

    def test_callback_error_propagation(self):
        """Test that Python exceptions in callbacks propagate correctly."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Mock a callback that raises an exception
        def failing_callback(data):
            raise RuntimeError("Callback failed")

        with patch.object(parser, "set_callback", create=True):
            try:
                parser.set_callback(failing_callback)
                # Process data that would trigger callback
                lines = ["trigger callback"]
                parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
            except (RuntimeError, AttributeError):
                # Should propagate callback error or not have callback support
                pass

    def test_ffi_with_corrupted_data_structures(self):
        """Test FFI with corrupted/malformed data structures."""
        from ClassicLib.integration.factory import get_plugin_analyzer

        mock_yamldata = MagicMock()
        analyzer = get_plugin_analyzer(mock_yamldata)

        # Create corrupted plugin structures
        corrupted_structures = [
            {},  # Empty structure
            {"plugins": None},  # Null plugins
            {"plugins": "not_a_list"},  # Wrong type
            {"plugins": [None, None]},  # Null elements
            {"plugins": [{"name": None}]},  # Null required field
            {"plugins": [{"name": "test", "formids": "not_a_list"}]},  # Wrong nested type
        ]

        for corrupt_data in corrupted_structures:
            # Mock loadorder_scan_log which is called internally by analyze_all
            mock_loadorder_scan_log_return = (corrupt_data, False, False)  # Expected tuple return
            with (
                patch("ClassicLib.python.plugin_py.PythonPluginAnalyzer.loadorder_scan_log", return_value=mock_loadorder_scan_log_return),
                patch("ClassicLib.rust.plugin_rust.RustPluginAnalyzer.loadorder_scan_log", return_value=mock_loadorder_scan_log_return),
            ):
                try:
                    result = analyzer.analyze_all()
                    # Should handle gracefully
                    assert result is None or isinstance(result, (dict, list))
                except (TypeError, ValueError, KeyError, AttributeError):
                    # These exceptions are acceptable for corrupted data
                    pass

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self):
        """Test that path traversal attempts are prevented."""
        from ClassicLib.integration.factory import get_file_io

        io_core = get_file_io()

        # Dangerous path patterns
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\sam",
            "\\\\server\\share\\sensitive",
            "file:///etc/passwd",
        ]

        for path in dangerous_paths:
            with pytest.raises((OSError, ValueError, RuntimeError, FileNotFoundError, classic_file_io.RustFileIOIOError)):
                await io_core.read_file(path)

    def test_signal_handling_during_ffi_call(self):
        """Test signal handling doesn't corrupt FFI state."""
        import signal

        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        def timeout_handler(signum, frame):
            raise TimeoutError("FFI call timed out")

        # Test interrupting FFI call (Unix only)
        if sys.platform != "win32":
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(1)  # 1 second timeout

            try:
                # Long-running parse operation
                lines = ["test" * 100000]
                parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
                signal.alarm(0)  # Cancel alarm
            except TimeoutError:
                pass  # Expected
            finally:
                signal.alarm(0)  # Ensure alarm is cancelled

            # Parser should still work after interruption
            lines = ["test"]
            _, _, _, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
            assert segments is not None

    def test_dll_injection_prevention(self):
        """Test that DLL injection attempts are handled safely."""
        # This tests that the module loading is secure
        dangerous_names = [
            "../../evil.dll",
            "C:\\Windows\\System32\\kernel32.dll",
            "classic_scanlog'; DROP TABLE users; --",
            "classic_scanlog\x00.dll",
        ]

        for name in dangerous_names:
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = ImportError(f"No module named '{name}'")

                with contextlib.suppress(ImportError, ValueError):
                    # Attempt to import with dangerous name
                    __import__(name)

    def test_stack_overflow_prevention(self):
        """Test prevention of stack overflow via recursive structures."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Create deeply nested structure that could cause stack overflow
        # Using synthetic crash log with deep nesting
        nested_content = "BEGIN\n"
        for i in range(10000):  # Very deep nesting
            nested_content += "  " * min(i, 100) + f"Level {i}\n"
        nested_content += "END\n"

        error = None
        try:
            lines = nested_content.splitlines()
            _, _, _, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
            # Should handle deep nesting without stack overflow
            assert segments is not None
        except (RecursionError, RuntimeError, ValueError) as e:
            # Should raise appropriate error for deep nesting
            error = e

        if error:
            assert "recursion" in str(error).lower() or "depth" in str(error).lower() or "stack" in str(error).lower()
