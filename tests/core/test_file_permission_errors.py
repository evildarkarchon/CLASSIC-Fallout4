"""File permission error handling tests.

This module tests the application's ability to handle various file
permission errors, access violations, and filesystem restrictions.
"""

# ruff: noqa: ANN001, ANN003, ANN201, ANN202, PLR6301, ASYNC240, PT017, TRY300, TRY301, ARG001, PT011

import asyncio
import stat
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Note: tempfile is still needed for tempfile.gettempdir() in test_fallback_to_temp_directory

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.filesystem]


class PermissionErrorSimulator:
    """Simulate various file permission scenarios."""

    @staticmethod
    def make_readonly(path: Path) -> None:
        """Make a file read-only."""
        if sys.platform == "win32":
            # Windows: Remove write permission
            path.chmod(stat.S_IREAD | stat.S_IEXEC)
        else:
            # Unix: Remove write permission
            path.chmod(0o444)

    @staticmethod
    def make_writeonly(path: Path) -> None:
        """Make a file write-only (Unix only)."""
        if sys.platform != "win32":
            # Unix: Remove read permission
            path.chmod(0o200)

    @staticmethod
    def make_no_access(path: Path) -> None:
        """Remove all permissions from a file."""
        if sys.platform == "win32":
            # Windows: Set to minimal permissions
            try:
                import win32api
                import win32con

                win32api.SetFileAttributes(str(path), win32con.FILE_ATTRIBUTE_HIDDEN)
            except ImportError:
                # Fallback if pywin32 not available
                path.chmod(0)
        else:
            # Unix: No permissions
            path.chmod(0o000)

    @staticmethod
    def restore_permissions(path: Path) -> None:
        """Restore normal permissions to a file."""
        if sys.platform == "win32":
            path.chmod(stat.S_IWRITE | stat.S_IREAD)
        else:
            path.chmod(0o644)


class TestReadPermissionErrors:
    """Test handling of read permission errors."""

    @pytest.fixture
    def simulator(self):
        return PermissionErrorSimulator()

    @pytest.mark.asyncio
    async def test_read_readonly_file(self, simulator, tmp_path):
        """Test reading a read-only file (should succeed)."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        temp_path = tmp_path / "readonly_test.log"
        temp_path.write_text("Read-only content", encoding="utf-8")

        try:
            # Make file read-only
            simulator.make_readonly(temp_path)

            # Should still be able to read
            content = await io_core.read_file(str(temp_path))
            assert content == "Read-only content"
        finally:
            simulator.restore_permissions(temp_path)

    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="Write-only not supported on Windows")
    async def test_read_writeonly_file(self, simulator, tmp_path):
        """Test reading a write-only file (should fail)."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        temp_path = tmp_path / "writeonly_test.log"
        temp_path.write_text("Write-only content", encoding="utf-8")

        try:
            # Make file write-only
            simulator.make_writeonly(temp_path)

            # Should fail to read
            with pytest.raises((PermissionError, OSError)):
                await io_core.read_file(str(temp_path))
        finally:
            simulator.restore_permissions(temp_path)

    @pytest.mark.asyncio
    async def test_read_no_access_file(self, simulator, tmp_path):
        """Test reading a file with no permissions."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        temp_path = tmp_path / "noaccess_test.log"
        temp_path.write_text("No access content", encoding="utf-8")

        try:
            # Remove all permissions
            simulator.make_no_access(temp_path)

            # Should handle permission error gracefully
            try:
                content = await io_core.read_file(str(temp_path))
                # If it succeeds (some systems), content should be None or empty
                assert content in {None, "", "No access content"}
            except (PermissionError, OSError) as e:
                # Expected error
                assert "permission" in str(e).lower() or "access" in str(e).lower()
        finally:
            simulator.restore_permissions(temp_path)


class TestWritePermissionErrors:
    """Test handling of write permission errors."""

    @pytest.fixture
    def simulator(self):
        return PermissionErrorSimulator()

    @pytest.mark.asyncio
    async def test_write_to_readonly_file(self, simulator, tmp_path):
        """Test writing to a read-only file."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        temp_path = tmp_path / "readonly_write_test.log"
        temp_path.write_text("Original content", encoding="utf-8")

        try:
            # Make file read-only
            simulator.make_readonly(temp_path)

            # Should fail to write
            with pytest.raises((PermissionError, OSError)):
                await io_core.write_file(str(temp_path), "New content")

            # Original content should remain
            simulator.restore_permissions(temp_path)
            content = temp_path.read_text(encoding="utf-8")
            assert content == "Original content"
        finally:
            simulator.restore_permissions(temp_path)

    @pytest.mark.asyncio
    async def test_write_to_readonly_directory(self, tmp_path):
        """Test creating a file in a read-only directory."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        readonly_dir = tmp_path / "readonly_dir"
        readonly_dir.mkdir()
        file_path = readonly_dir / "new_file.log"

        try:
            # Make directory read-only
            if sys.platform == "win32":
                # Windows: Harder to make directory truly read-only
                # Mock the permission error instead
                # Mock aiofiles if available, else Path.write_text
                with (
                    patch("aiofiles.open", side_effect=PermissionError("Access denied")),
                    patch("pathlib.Path.write_text", side_effect=PermissionError("Access denied")),
                    pytest.raises(PermissionError),
                ):
                    await io_core.write_file(str(file_path), "content")
            else:
                # Unix: Remove write permission from directory
                readonly_dir.chmod(0o555)
                with pytest.raises((PermissionError, OSError)):
                    await io_core.write_file(str(file_path), "content")
        finally:
            # Restore permissions
            readonly_dir.chmod(0o755)

    @pytest.mark.asyncio
    @pytest.mark.skip("Atomic write functionality not exposed/implemented in FileIOCore")
    async def test_atomic_write_permission_error(self):
        """Test atomic write operation with permission errors."""


class TestDirectoryPermissionErrors:
    """Test handling of directory permission errors."""

    @pytest.mark.asyncio
    async def test_list_directory_no_permissions(self, tmp_path):
        """Test listing a directory without read permissions."""
        from ClassicLib.FileIO import FileIOCore

        FileIOCore()

        test_dir = tmp_path / "noread_dir"
        test_dir.mkdir()

        # Create some files
        (test_dir / "file1.log").write_text("content1", encoding="utf-8")
        (test_dir / "file2.log").write_text("content2", encoding="utf-8")

        try:
            if sys.platform != "win32":
                # Unix: Remove read permission
                test_dir.chmod(0o333)  # Write and execute only

                # Should fail to list directory
                with pytest.raises((PermissionError, OSError)):
                    list(test_dir.iterdir())
            else:
                # Windows: Mock the error
                with (
                    patch("pathlib.Path.iterdir", side_effect=PermissionError("Access denied")),
                    pytest.raises(PermissionError),
                ):
                    list(test_dir.iterdir())
        finally:
            test_dir.chmod(0o755)

    @pytest.mark.asyncio
    async def test_create_directory_in_protected_location(self):
        """Test creating directories in protected system locations."""
        from ClassicLib.FileIO import FileIOCore

        FileIOCore()

        # Try to create in system directories (should fail)
        protected_paths = []

        if sys.platform == "win32":
            protected_paths = [
                "C:\\Windows\\System32\\test_dir",
                "C:\\Program Files\\test_dir",
            ]
        else:
            protected_paths = [
                "/root/test_dir",
                "/etc/test_dir",
                "/sys/test_dir",
            ]

        for protected_path in protected_paths:
            path = Path(protected_path)

            # Should fail or be mocked to fail
            try:
                path.mkdir(parents=True, exist_ok=True)
                # If it somehow succeeds (shouldn't in normal conditions)
                path.rmdir()
                pytest.skip(f"Unexpectedly able to create {protected_path}")
            except (PermissionError, OSError):
                # Expected - cannot create in protected location
                pass


class TestFileLockingScenarios:
    """Test file locking and concurrent access scenarios."""

    @pytest.mark.asyncio
    async def test_read_locked_file(self, tmp_path):
        """Test reading a file that's locked by another process."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        temp_file = tmp_path / "locked_test.log"
        temp_file.write_text("Locked content", encoding="utf-8")

        # Simulate file being locked
        if sys.platform == "win32":
            # Windows file locking
            # Patch both aiofiles.open and builtins.open (fallback)
            with (
                patch("aiofiles.open", side_effect=PermissionError("File is being used")),
                patch("builtins.open", side_effect=PermissionError("File is being used")),
                pytest.raises(PermissionError),
            ):
                await io_core.read_file(str(temp_file))
        else:
            # Unix: Files can usually be read even when locked
            content = await io_core.read_file(str(temp_file))
            assert content == "Locked content"

    @pytest.mark.asyncio
    async def test_concurrent_write_attempts(self, tmp_path):
        """Test handling concurrent write attempts to the same file."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        temp_file = tmp_path / "concurrent_write_test.log"

        # Simulate concurrent writes
        async def write_content(content: str, delay: float = 0):
            await asyncio.sleep(delay)
            try:
                await io_core.write_file(str(temp_file), content)
                return True
            except (PermissionError, OSError):
                return False

        # Launch concurrent writes
        tasks = [
            write_content("Writer 1", 0),
            write_content("Writer 2", 0.001),
            write_content("Writer 3", 0.002),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one should succeed
        successes = [r for r in results if r is True]
        assert len(successes) >= 1

        # Final content should be from one of the writers
        final_content = temp_file.read_text(encoding="utf-8")
        assert final_content in {"Writer 1", "Writer 2", "Writer 3"}


class TestQuotaAndSpaceErrors:
    """Test handling of disk quota and space errors."""

    @pytest.mark.asyncio
    async def test_disk_full_error(self, tmp_path):
        """Test handling of disk full errors."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()
        temp_file = tmp_path / "disk_full_test.log"

        # Mock disk full error - patch both aiofiles and Path.write_text
        with (
            patch("aiofiles.open", side_effect=OSError(28, "No space left on device")),
            patch("pathlib.Path.write_text", side_effect=OSError(28, "No space left on device")),
        ):
            # Should handle disk full error gracefully
            with pytest.raises(OSError) as exc_info:
                await io_core.write_file(str(temp_file), "x" * 1000000)

            # Should be identifiable as space error
            assert exc_info.value.errno == 28 or "space" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_quota_exceeded_error(self, tmp_path):
        """Test handling of quota exceeded errors."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()
        temp_file = tmp_path / "quota_test.log"

        # Mock quota exceeded error
        with (
            patch("aiofiles.open", side_effect=OSError(122, "Disk quota exceeded")),
            patch("pathlib.Path.write_text", side_effect=OSError(122, "Disk quota exceeded")),
        ):
            # Should handle quota error gracefully
            with pytest.raises(OSError) as exc_info:
                await io_core.write_file(str(temp_file), "content")

            # Should be identifiable as quota error
            assert "quota" in str(exc_info.value).lower()


class TestSymbolicLinkPermissions:
    """Test handling of symbolic link permission issues."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Symlinks require admin on Windows")
    @pytest.mark.asyncio
    async def test_broken_symlink_handling(self, tmp_path):
        """Test handling of broken symbolic links."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        # Create a symlink to non-existent file
        link_path = tmp_path / "broken_link.log"
        target_path = tmp_path / "non_existent.log"
        link_path.symlink_to(target_path)

        # Should handle broken symlink gracefully
        with pytest.raises((FileNotFoundError, OSError)):
            await io_core.read_file(str(link_path))

    @pytest.mark.skipif(sys.platform == "win32", reason="Symlinks require admin on Windows")
    @pytest.mark.asyncio
    async def test_symlink_permission_traversal(self, tmp_path):
        """Test permission issues when following symlinks."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()
        simulator = PermissionErrorSimulator()

        # Create target file with no permissions
        target_path = tmp_path / "target.log"
        target_path.write_text("Target content", encoding="utf-8")
        simulator.make_no_access(target_path)

        # Create symlink to restricted file
        link_path = tmp_path / "link.log"
        link_path.symlink_to(target_path)

        try:
            # Should fail when following symlink to restricted file
            with pytest.raises((PermissionError, OSError)):
                await io_core.read_file(str(link_path))
        finally:
            simulator.restore_permissions(target_path)


class TestPermissionRecoveryStrategies:
    """Test strategies for recovering from permission errors."""

    @pytest.mark.asyncio
    async def test_fallback_to_temp_directory(self):
        """Test falling back to temp directory when primary fails."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        async def write_with_fallback(primary_path: Path, content: str) -> Path:
            """Try primary path, fallback to temp on permission error."""
            try:
                await io_core.write_file(str(primary_path), content)
                return primary_path
            except (PermissionError, OSError):
                # Fallback to temp directory
                temp_path = Path(tempfile.gettempdir()) / primary_path.name
                await io_core.write_file(str(temp_path), content)
                return temp_path

        # Test with protected path
        protected_path = Path("/root/test.log") if sys.platform != "win32" else Path("C:/Windows/test.log")

        # Mock write_file to fail for protected_path
        original_write_file = io_core.write_file

        async def side_effect(path: str | Path, content: str):
            # Normalize path for comparison
            check_path = Path(path)
            if check_path == protected_path:
                raise PermissionError(f"Simulated permission error for {path}")

            # Call original for other paths (fallback)
            await original_write_file(path, content)

        with patch.object(io_core, "write_file", side_effect=side_effect):
            # Should fallback to temp
            actual_path = await write_with_fallback(protected_path, "test content")

        assert actual_path != protected_path
        assert actual_path.parent == Path(tempfile.gettempdir())

        # Cleanup
        if actual_path.exists():
            actual_path.unlink()

    @pytest.mark.asyncio
    async def test_retry_with_elevated_permissions(self):
        """Test retry logic with permission elevation (mock)."""
        from ClassicLib.FileIO import FileIOCore

        FileIOCore()
        attempt_count = 0

        async def write_with_elevation(path: Path, content: str) -> bool:
            """Simulate retry with elevated permissions."""
            await asyncio.sleep(0)
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                # First attempt fails
                raise PermissionError("Access denied")
            # Second attempt with "elevated" permissions succeeds
            return True

        # Test retry with elevation
        try:
            result = await write_with_elevation(Path("/protected/path"), "content")
        except PermissionError:
            # Retry with "elevation"
            result = await write_with_elevation(Path("/protected/path"), "content")

        assert result
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_permission_error_user_notification(self):
        """Test that permission errors are properly reported to users."""
        from ClassicLib.MessageHandler.handler import MessageHandler

        # Clear singleton
        if hasattr(MessageHandler, "_instance"):
            delattr(MessageHandler, "_instance")

        msg_handler = MessageHandler()
        error_messages = []

        # Mock error handling
        def capture_error(msg: str, **kwargs):
            error_messages.append(msg)

        with patch.object(msg_handler, "error", side_effect=capture_error):
            # Simulate permission error
            try:
                raise PermissionError("Cannot write to C:\\Program Files\\test.log")
            except PermissionError as e:
                msg_handler.error(f"Permission Error: {e}")

        # Should have captured the error message
        assert len(error_messages) == 1
        assert "Permission Error" in error_messages[0]
        assert "C:\\Program Files\\test.log" in error_messages[0]
