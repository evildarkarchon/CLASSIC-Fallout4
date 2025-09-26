"""Comprehensive tests for malformed crash log handling.

This module tests the application's resilience when processing various types
of malformed, corrupted, or unusual crash logs that might be encountered in
production environments.
"""

import pytest
import tempfile
import random
import string
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, patch
import json
import asyncio

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.edge_cases]


class MalformedLogGenerator:
    """Generate various types of malformed crash logs for testing."""

    @staticmethod
    def generate_truncated_log() -> str:
        """Generate a log that appears to be cut off mid-write."""
        return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512

PLUGINS:
    [00] Fallout4.esm
    [01] DLCRobot.esm
    [02] DLCworkshop01.esm
    [FE:000] PRP.esp
    [FE:001] SS2_Addon.esp
    [FE:002]
STACK TRACE:
    [0] 0x7FF6EF4C3512 Fallout4.exe+073351"""  # Truncated mid-line

    @staticmethod
    def generate_corrupted_binary_log() -> bytes:
        """Generate a log with binary corruption."""
        valid_start = b"Fallout 4 v1.10.163\nBuffout 4 v1.28.6\n\n"
        corruption = bytes(random.randint(0, 255) for _ in range(500))
        valid_end = b"\nPLUGINS:\n    [00] Fallout4.esm\n"
        return valid_start + corruption + valid_end

    @staticmethod
    def generate_mixed_encoding_log() -> bytes:
        """Generate a log with mixed character encodings."""
        # Mix UTF-8, CP1252, and invalid sequences
        parts = [
            "Fallout 4 v1.10.163\n".encode('utf-8'),
            "Exception à l'adresse ".encode('cp1252'),  # French with CP1252
            b"\xFF\xFE\xFD\xFC",  # Invalid UTF-8 bytes
            "\nКрах игры\n".encode('utf-8'),  # Russian in UTF-8
            "PLUGINS:\n".encode('ascii'),
        ]
        return b"".join(parts)

    @staticmethod
    def generate_circular_reference_log() -> str:
        """Generate a log with circular/recursive references."""
        return """Fallout 4 v1.10.163

EXCEPTION at FormID: 00000014 -> references 00000015
FormID: 00000015 -> references 00000016
FormID: 00000016 -> references 00000014  // Circular reference!

PLUGINS:
    [00] Fallout4.esm -> depends on [01]
    [01] DLCRobot.esm -> depends on [02]
    [02] Mod.esp -> depends on [00]  // Circular dependency!
"""

    @staticmethod
    def generate_malformed_formids() -> str:
        """Generate a log with invalid FormID formats."""
        return """Fallout 4 v1.10.163

FORMIDS FOUND:
FormID: GGGGGGGG  // Invalid hex
FormID: 0000000   // Too short (7 chars)
FormID: 000000000 // Too long (9 chars)
FormID: 00 00 00 14  // Spaces in FormID
FormID: 0x00000014  // With 0x prefix
FormID: FE00080G  // Invalid character G
FormID: -00000014  // Negative FormID
FormID: 00000014.esp  // FormID with extension
"""

    @staticmethod
    def generate_extreme_nesting() -> str:
        """Generate a log with extreme nesting that could cause stack issues."""
        nested_structure = "BEGIN\n"
        for i in range(1000):  # Very deep nesting
            nested_structure += "  " * min(i, 50) + f"Level {i} {\n"
        nested_structure += "  " * 50 + "CRASH HERE\n"
        for i in range(999, -1, -1):
            nested_structure += "  " * min(i, 50) + "}\n"
        return nested_structure

    @staticmethod
    def generate_null_byte_log() -> bytes:
        """Generate a log with null bytes that might confuse parsers."""
        return b"Fallout 4 v1.10.163\x00\x00\x00Buffout 4\x00v1.28.6\n\x00PLUGINS:\x00\n"

    @staticmethod
    def generate_infinite_repeat_pattern() -> str:
        """Generate a log with infinite repeating patterns."""
        base = "ERROR: Stack overflow at 0x"
        # Create a 2MB file of repeating error lines (typical crash log size)
        line = base + "7FF6EF4C3512\n"
        repeat_count = (2 * 1024 * 1024) // len(line)  # Fill 2MB
        return line * repeat_count

    @staticmethod
    def generate_missing_critical_sections() -> str:
        """Generate a log missing critical sections."""
        return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Some random text here
More random text
No proper sections
No plugin list
No stack trace
Just random log data
"""

    @staticmethod
    def generate_conflicting_data() -> str:
        """Generate a log with conflicting/contradictory data."""
        return """Fallout 4 v1.10.163
Fallout 4 v1.10.164  // Different version!

EXCEPTION_ACCESS_VIOLATION at 0x00000000
EXCEPTION_STACK_OVERFLOW at 0x00000000  // Different exception!

PLUGINS: 0 loaded
PLUGINS: 255 loaded  // Conflicting count!

[00] Fallout4.esm
[00] DLCRobot.esm  // Duplicate index!
[01] Fallout4.esm  // Duplicate plugin!
"""


class TestMalformedCrashLogHandling:
    """Test handling of various malformed crash logs."""

    @pytest.fixture
    def generator(self):
        """Malformed log generator."""
        return MalformedLogGenerator()

    @pytest.fixture
    def setup_parser(self):
        """Setup parser with proper error handling."""
        from ClassicLib.integration.factory import get_parser
        return get_parser()

    def test_truncated_log_handling(self, generator, setup_parser):
        """Test handling of truncated/incomplete logs."""
        truncated_log = generator.generate_truncated_log()

        # Should handle truncation gracefully
        result = setup_parser.parse(truncated_log)

        # Should still extract what it can
        assert result is not None
        if isinstance(result, dict):
            # Should parse the complete plugin entries
            if "plugins" in result:
                complete_plugins = [p for p in result["plugins"] if p.get("name")]
                assert len(complete_plugins) >= 2  # At least Fallout4.esm and DLCRobot.esm

    def test_binary_corruption_handling(self, generator, setup_parser):
        """Test handling of binary corruption in logs."""
        corrupted_log = generator.generate_corrupted_binary_log()

        # Try to parse as text with error handling
        try:
            text_log = corrupted_log.decode('utf-8', errors='ignore')
            result = setup_parser.parse(text_log)

            # Should handle corruption without crashing
            assert result is not None or result == {}
        except (UnicodeDecodeError, ValueError) as e:
            # Acceptable to fail with proper exception
            assert "decode" in str(e).lower() or "corrupt" in str(e).lower()

    def test_mixed_encoding_handling(self, generator, setup_parser):
        """Test handling of mixed character encodings."""
        mixed_log = generator.generate_mixed_encoding_log()

        # Should handle mixed encodings
        for encoding in ['utf-8', 'cp1252', 'latin-1']:
            try:
                text_log = mixed_log.decode(encoding, errors='ignore')
                result = setup_parser.parse(text_log)

                # Should parse something even with encoding issues
                assert result is not None
                break
            except UnicodeDecodeError:
                continue

    def test_circular_reference_handling(self, generator, setup_parser):
        """Test handling of circular references in data."""
        circular_log = generator.generate_circular_reference_log()

        result = setup_parser.parse(circular_log)

        # Should detect and handle circular references
        assert result is not None
        # Parser should not get stuck in infinite loop

    def test_malformed_formid_handling(self, generator, setup_parser):
        """Test handling of invalid FormID formats."""
        from ClassicLib.integration.factory import get_formid_analyzer

        malformed_log = generator.generate_malformed_formids()
        mock_yamldata = MagicMock()
        analyzer = get_formid_analyzer(mock_yamldata, True, False)

        # Extract FormID-like patterns
        import re
        formid_pattern = re.compile(r'FormID:\s*([^\s\n]+)')
        matches = formid_pattern.findall(malformed_log)

        valid_formids = []
        for match in matches:
            try:
                # Try to analyze each FormID
                result = analyzer.analyze(match)
                if result:
                    valid_formids.append(match)
            except (ValueError, TypeError):
                # Should handle invalid FormIDs gracefully
                pass

        # Should only process valid FormIDs
        for valid in valid_formids:
            assert len(valid) == 8
            assert all(c in "0123456789ABCDEFabcdef" for c in valid)

    def test_extreme_nesting_handling(self, generator, setup_parser):
        """Test handling of extremely nested structures."""
        nested_log = generator.generate_extreme_nesting()

        # Should handle deep nesting without stack overflow
        try:
            result = setup_parser.parse(nested_log)
            assert result is not None
        except RecursionError:
            # Acceptable to limit recursion depth
            pass

    def test_null_byte_handling(self, generator, setup_parser):
        """Test handling of null bytes in logs."""
        null_log = generator.generate_null_byte_log()

        # Remove null bytes or handle them
        cleaned_log = null_log.replace(b'\x00', b'').decode('utf-8', errors='ignore')
        result = setup_parser.parse(cleaned_log)

        # Should parse after cleaning
        assert result is not None

    def test_infinite_pattern_handling(self, generator, setup_parser):
        """Test handling of infinite repeating patterns (2MB typical size)."""
        import time

        infinite_log = generator.generate_infinite_repeat_pattern()

        # Should handle efficiently without hanging
        start_time = time.time()
        result = setup_parser.parse(infinite_log)
        elapsed = time.time() - start_time

        # Should complete in reasonable time for 2MB
        assert elapsed < 5.0  # 5 seconds max for 2MB
        assert result is not None

    def test_missing_sections_handling(self, generator, setup_parser):
        """Test handling of logs missing critical sections."""
        incomplete_log = generator.generate_missing_critical_sections()

        result = setup_parser.parse(incomplete_log)

        # Should return result even without standard sections
        assert result is not None
        if isinstance(result, dict):
            # Might have empty sections but shouldn't crash
            assert "error" not in str(result).lower() or result.get("error") is None

    def test_conflicting_data_handling(self, generator, setup_parser):
        """Test handling of conflicting/contradictory data."""
        conflicting_log = generator.generate_conflicting_data()

        result = setup_parser.parse(conflicting_log)

        # Should handle conflicts (usually takes first or last occurrence)
        assert result is not None


class TestEdgeCaseFileOperations:
    """Test edge cases in file operations."""

    @pytest.mark.asyncio
    async def test_zero_byte_file(self):
        """Test handling of empty/zero-byte files."""
        from ClassicLib.FileIOCore import FileIOCore

        io_core = FileIOCore()

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            # Write nothing - zero byte file
            temp_path = Path(f.name)

        try:
            content = await io_core.read_file(str(temp_path))
            assert content == "" or content is None
        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_massive_single_line(self):
        """Test handling of file with single massive line."""
        from ClassicLib.FileIOCore import FileIOCore

        io_core = FileIOCore()

        # Create 10MB single line
        massive_line = "x" * (10 * 1024 * 1024)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(massive_line)
            temp_path = Path(f.name)

        try:
            content = await io_core.read_file(str(temp_path))
            assert len(content) == len(massive_line)
        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_rapid_file_deletion(self):
        """Test handling when file is deleted during read."""
        from ClassicLib.FileIOCore import FileIOCore

        io_core = FileIOCore()

        temp_path = Path(tempfile.mktemp(suffix='.log'))
        temp_path.write_text("Test content")

        async def delete_file_soon():
            await asyncio.sleep(0.001)
            temp_path.unlink(missing_ok=True)

        # Start deletion task
        delete_task = asyncio.create_task(delete_file_soon())

        # Try to read (might fail due to deletion)
        try:
            content = await io_core.read_file(str(temp_path))
            # If successful, should have content
            if content:
                assert "Test" in content
        except (FileNotFoundError, OSError):
            # Expected if file was deleted
            pass
        finally:
            await delete_task
            temp_path.unlink(missing_ok=True)


class TestUnicodeAndEncodingEdgeCases:
    """Test Unicode and encoding edge cases."""

    def test_emoji_overload(self):
        """Test handling of logs full of emojis."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Create log with many emojis
        emoji_log = """Fallout 4 v1.10.163 🎮

💥💥💥 CRASH 💥💥💥
Exception: 😱 at 0x7FF6EF4C3512

PLUGINS 📁:
    [00] Fallout4.esm ✅
    [01] DLCRobot.esm ⚙️
    [FE:000] PRP.esp 🏗️

🔥🔥🔥 Stack Trace 🔥🔥🔥"""

        result = parser.parse(emoji_log)
        assert result is not None

    def test_mixed_line_endings(self):
        """Test handling of mixed line endings (CRLF, LF, CR)."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Mix different line endings
        mixed_log = "Line 1\r\nLine 2\nLine 3\rLine 4\r\n\nLine 6"

        result = parser.parse(mixed_log)
        assert result is not None

    def test_bom_markers(self):
        """Test handling of BOM (Byte Order Mark) markers."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # UTF-8 BOM
        bom_log = "\ufeffFallout 4 v1.10.163\nBuffout 4 v1.28.6"

        result = parser.parse(bom_log)
        assert result is not None

    def test_control_characters(self):
        """Test handling of control characters in logs."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Add various control characters
        control_log = "Fallout 4\x00v1.10.163\x01\x02\nException\x1b[31m colored \x1b[0m"

        result = parser.parse(control_log)
        assert result is not None


class TestPathEdgeCases:
    """Test edge cases in path handling."""

    @pytest.mark.asyncio
    async def test_extremely_long_path(self):
        """Test handling of extremely long file paths."""
        from ClassicLib.FileIOCore import FileIOCore

        io_core = FileIOCore()

        # Create a very long path (near Windows limit of 260 chars)
        long_name = "a" * 200

        with tempfile.TemporaryDirectory() as temp_dir:
            long_path = Path(temp_dir) / f"{long_name}.log"
            try:
                long_path.write_text("test")
                content = await io_core.read_file(str(long_path))
                assert content == "test"
            except OSError as e:
                # Path too long is acceptable error
                assert "too long" in str(e).lower() or "name" in str(e).lower()

    @pytest.mark.asyncio
    async def test_special_characters_in_path(self):
        """Test handling of special characters in file paths."""
        from ClassicLib.FileIOCore import FileIOCore

        io_core = FileIOCore()

        # Test various special characters (that are valid in filenames)
        special_names = [
            "test file.log",  # Space
            "test-file.log",  # Hyphen
            "test_file.log",  # Underscore
            "test.multiple.dots.log",  # Multiple dots
            "test[brackets].log",  # Brackets
            "test(parens).log",  # Parentheses
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            for name in special_names:
                try:
                    file_path = Path(temp_dir) / name
                    file_path.write_text("content")
                    content = await io_core.read_file(str(file_path))
                    assert content == "content"
                except (OSError, ValueError):
                    # Some characters might not be allowed on some systems
                    pass

    @pytest.mark.asyncio
    async def test_symlink_handling(self):
        """Test handling of symbolic links."""
        import sys

        if sys.platform == "win32":
            pytest.skip("Symlink test requires admin privileges on Windows")

        from ClassicLib.FileIOCore import FileIOCore

        io_core = FileIOCore()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create real file
            real_file = temp_path / "real.log"
            real_file.write_text("real content")

            # Create symlink
            link_file = temp_path / "link.log"
            link_file.symlink_to(real_file)

            # Should read through symlink
            content = await io_core.read_file(str(link_file))
            assert content == "real content"


class TestConcurrencyEdgeCases:
    """Test edge cases in concurrent operations."""

    @pytest.mark.asyncio
    async def test_simultaneous_same_file_access(self):
        """Test multiple simultaneous reads of the same file."""
        from ClassicLib.FileIOCore import FileIOCore

        io_core = FileIOCore()

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("shared content\n" * 1000)
            temp_path = Path(f.name)

        try:
            # Launch 20 simultaneous reads
            tasks = [
                io_core.read_file(str(temp_path))
                for _ in range(20)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed or fail gracefully
            successful = [r for r in results if isinstance(r, str)]
            assert len(successful) >= 18  # At least 90% should succeed

            # All successful reads should be identical
            if successful:
                first = successful[0]
                assert all(r == first for r in successful)
        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_race_condition_in_parsing(self):
        """Test race conditions when parsing the same log concurrently."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Create test log
        test_log = """Fallout 4 v1.10.163
PLUGINS:
    [00] Fallout4.esm
    [01] DLCRobot.esm
FormID: 00000014
FormID: FE000800
"""

        # Parse same log 50 times concurrently
        tasks = []
        for _ in range(50):
            tasks.append(
                asyncio.to_thread(parser.parse, test_log)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All results should be consistent
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 45  # At least 90% should succeed

        # All successful parses should produce same result structure
        if successful and isinstance(successful[0], dict):
            first_keys = set(successful[0].keys())
            for result in successful[1:]:
                if isinstance(result, dict):
                    assert set(result.keys()) == first_keys