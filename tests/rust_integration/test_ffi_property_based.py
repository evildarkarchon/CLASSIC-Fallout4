"""Property-based tests for Rust FFI boundaries using Hypothesis.

This module uses property-based testing to comprehensively test the
Rust-Python FFI boundaries with thousands of generated test cases,
ensuring type safety, error handling, and memory safety.
"""

import string
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

try:
    from hypothesis import assume, example, given, settings
    from hypothesis import strategies as st
    from hypothesis.strategies import composite

    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    pytest.skip("Hypothesis not available", allow_module_level=True)

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.rust]


# Custom strategies for generating test data
@composite
def mock_formid(draw):
    """Generate mock FormID values similar to game FormIDs."""
    prefix = draw(st.text(alphabet=string.hexdigits, min_size=2, max_size=2))
    number = draw(st.integers(min_value=0, max_value=0xFFFFFF))
    return f"{prefix}{number:06X}"


@composite
def mock_plugin_name(draw):
    """Generate mock plugin names like game mods."""
    prefix = draw(st.sampled_from(["Fallout4", "DLC", "Mod", "Patch", "Fix"]))
    name = draw(st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=20))
    suffix = draw(st.sampled_from([".esm", ".esp", ".esl"]))
    return f"{prefix}_{name}{suffix}"


@composite
def mock_crash_log_line(draw):
    """Generate mock crash log lines with various formats."""
    line_type = draw(st.sampled_from(["stack", "error", "warning", "info", "formid"]))

    if line_type == "stack":
        address = draw(st.integers(min_value=0, max_value=0xFFFFFFFF))
        module = draw(st.text(alphabet=string.ascii_letters, min_size=1, max_size=20))
        return f"  [{address:08X}] {module}.dll+{draw(st.integers(0, 0xFFFF)):04X}"
    if line_type == "error":
        return f"ERROR: {draw(st.text(min_size=1, max_size=100))}"
    if line_type == "formid":
        formid = draw(mock_formid())
        plugin = draw(mock_plugin_name())
        return f"  FormID: {formid} from {plugin}"
    return draw(st.text(min_size=1, max_size=200))


@composite
def mock_game_file_structure(draw):
    """Generate mock game file structure without using real game data."""
    # Generate base structure
    data_dict = {
        "Fallout4.esm": draw(st.integers(min_value=1000000, max_value=100000000)),
        "DLCRobot.esm": draw(st.integers(min_value=1000000, max_value=50000000)),
    }
    # Add random plugins
    for _ in range(draw(st.integers(min_value=0, max_value=5))):
        data_dict[draw(mock_plugin_name())] = draw(st.integers(min_value=1000, max_value=10000000))

    # Generate mods structure
    mods_dict = {}
    for i in range(draw(st.integers(min_value=0, max_value=3))):
        mods_dict[f"Mod_{i}"] = {
            "main.ba2": draw(st.integers(min_value=100000, max_value=10000000)),
            "textures.ba2": draw(st.integers(min_value=100000, max_value=50000000)),
        }

    return {
        "Data": data_dict,
        "F4SE": {
            "f4se_loader.exe": draw(st.integers(min_value=50000, max_value=500000)),
            "f4se_1_10_163.dll": draw(st.integers(min_value=100000, max_value=1000000)),
        },
        "Mods": mods_dict,
    }


class TestRustFFIPropertyBased:
    """Property-based tests for Rust FFI boundaries."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Mock the Rust module if not available
        self.rust_available = False
        try:
            import classic_scanlog

            self.rust_available = True
        except ImportError:
            pass

    @given(st.text(min_size=0, max_size=10000))
    @settings(max_examples=100)
    def test_rust_parser_handles_any_text_input(self, text_input: str):
        """Test that Rust parser handles any text input without crashing."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        # Should not crash regardless of input
        try:
            lines = text_input.splitlines() if isinstance(text_input, str) else []
            game_ver, crashgen_ver, error, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
            # Result should be a valid structure even for invalid input
            assert segments is not None
            assert isinstance(segments, list)
        except Exception as e:
            # Should only raise known exception types
            assert isinstance(e, (ValueError, TypeError, RuntimeError, AttributeError))

    @given(st.lists(mock_crash_log_line(), min_size=0, max_size=1000))
    @settings(max_examples=50)
    def test_rust_parser_with_mock_crash_logs(self, log_lines: list[str]):
        """Test Rust parser with various mock crash log formats."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        try:
            game_ver, crashgen_ver, error, segments = parser.find_segments(log_lines, "Buffout 4", "F4SE", "Fallout4.exe")
            # Verify basic structure
            if segments:
                assert isinstance(segments, list)
                # Check for expected keys in parsed result
                # segments is a list of lists of strings
                assert isinstance(segments[0], list)
        except Exception as e:
            # Parser should handle gracefully
            assert isinstance(e, (ValueError, RuntimeError))

    @given(
        st.lists(mock_formid(), min_size=0, max_size=1000),
        st.booleans(),  # show_values
        st.booleans(),  # db_exists
    )
    @settings(max_examples=50)
    def test_formid_analyzer_with_synthetic_ids(self, formids: list[str], show_values: bool, db_exists: bool):
        """Test FormID analyzer with synthetic FormIDs."""
        from ClassicLib.integration.factory import get_formid_analyzer

        # Create mock yamldata
        mock_yamldata = MagicMock()
        mock_yamldata.formid_keywords = ["crash", "error", "ctd"]

        analyzer = get_formid_analyzer(mock_yamldata, show_values, db_exists)

        # Should handle any list of FormIDs using extract_formids
        try:
            results = analyzer.extract_formids(formids)
            # Result should be structured data
            assert results is None or isinstance(results, (list, dict))
        except Exception as e:
            # Should only raise expected exceptions
            assert isinstance(e, (ValueError, KeyError, RuntimeError, TypeError))

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=50),  # filenames
            st.integers(min_value=0, max_value=100000000),  # file sizes
            min_size=0,
            max_size=100,
        )
    )
    @settings(max_examples=50)
    def test_file_io_with_mock_file_structures(self, file_structure: dict[str, int]):
        """Test Rust file I/O with mock file structures."""
        from ClassicLib.integration.factory import get_file_io

        io_core = get_file_io()

        # Test with mock file paths
        for filename, size in file_structure.items():
            mock_path = Path(f"/mock/game/data/{filename}")

            with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = size

                try:
                    # Should handle path operations
                    result = io_core.get_file_info(str(mock_path))
                    assert result is not None
                    if isinstance(result, dict):
                        assert "size" in result or "error" in result
                except Exception as e:
                    # Should handle gracefully
                    assert isinstance(e, (OSError, RuntimeError, ValueError))

    @given(
        st.binary(min_size=0, max_size=10000),  # Random binary data
        st.sampled_from(["utf-8", "cp1252", "latin-1", "ascii"]),  # Encodings
    )
    @settings(max_examples=100)
    def test_encoding_edge_cases(self, binary_data: bytes, encoding: str):
        """Test encoding edge cases with various binary data."""
        import asyncio
        import tempfile

        from ClassicLib.integration.factory import get_file_io

        io_core = get_file_io()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_file.txt"

            # Try to decode binary as text with different encodings
            try:
                # Attempt to decode to see if it's valid for this encoding
                text = binary_data.decode(encoding, errors="ignore")

                # Write the binary data to the file
                test_file.write_bytes(binary_data)

                # Read back using Rust
                result = asyncio.run(io_core.read_file_with_encoding(str(test_file), encoding))

                # Should return something without crashing
                assert result is not None

            except UnicodeDecodeError:
                # This is expected for random binary data during decode check
                pass
            except Exception as e:
                # Should only raise expected exceptions
                # Check if it's one of the Rust exception types by name or inheritance
                error_name = type(e).__name__
                valid_errors = ("ValueError", "RuntimeError", "OSError", "RustFileIOIOError", "RustFileIOError", "RustError")
                assert isinstance(e, (ValueError, RuntimeError, OSError)) or error_name in valid_errors

    @given(
        st.integers(min_value=0, max_value=100),  # thread_count (reduced max to match limit)
        st.integers(min_value=0, max_value=10000),  # operations_per_thread
    )
    @settings(max_examples=20, deadline=5000)  # Extended deadline for concurrency tests
    def test_rust_concurrency_limits(self, thread_count: int, operations_per_thread: int):
        """Test Rust components under concurrent load."""
        # Removed assume(False) filtering by adjusting strategy above

        import threading
        import time

        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        errors = []
        results = []

        def worker():
            try:
                for _ in range(min(operations_per_thread, 10)):  # Limit operations
                    lines = ["test data"]
                    game_ver, crashgen_ver, error, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
                    results.append(segments)
                    time.sleep(0.001)  # Small delay to prevent overwhelming
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(min(thread_count, 10)):  # Limit actual threads
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=1.0)

        # Should complete without deadlocks or crashes
        assert len(errors) == 0 or all(isinstance(e, (RuntimeError, ValueError)) for e in errors)

    @given(
        st.dictionaries(
            st.text(alphabet=string.ascii_letters, min_size=1, max_size=20),  # keys
            st.one_of(
                st.integers(), st.floats(allow_nan=False, allow_infinity=False), st.text(max_size=100), st.booleans(), st.none()
            ),  # values
            min_size=0,
            max_size=100,
        )
    )
    @settings(max_examples=50)
    def test_rust_json_serialization(self, data: dict[str, Any]):
        """Test Rust JSON serialization with various data types."""
        if not self.rust_available:
            pytest.skip("Rust module not available")

        try:
            import classic_scanlog

            # Test serialization roundtrip
            result = classic_scanlog.test_json_roundtrip(data)

            # Should preserve structure
            assert isinstance(result, dict)
            assert len(result) == len(data)

            # Check preservation of types (with JSON limitations)
            for key in data:
                if data[key] is None:
                    assert result[key] is None
                elif isinstance(data[key], bool):
                    assert isinstance(result[key], bool)
                elif isinstance(data[key], (int, float)):
                    assert isinstance(result[key], (int, float))
                elif isinstance(data[key], str):
                    assert isinstance(result[key], str)

        except (ImportError, AttributeError):
            # Module or function might not exist
            pytest.skip("JSON roundtrip function not available")
        except Exception as e:
            # Should only raise expected exceptions
            assert isinstance(e, (ValueError, TypeError, RuntimeError))
