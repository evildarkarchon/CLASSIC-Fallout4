"""Tests for Rust-accelerated game path detection.

Verifies that the Rust GamePathFinder and PathValidator are properly
integrated as the only code path (no Python fallback).
"""

from pathlib import Path

import pytest

# Mark all tests as integration tests requiring Rust
pytestmark = [pytest.mark.integration]


class TestRustGamePathFinder:
    """Test GamePathFinder with Rust backend."""

    def test_rust_import_required(self) -> None:
        """Verify classic_path import is required (not optional)."""
        # Should succeed - Rust module is required
        from classic_path import GamePathFinder, PathValidator

        assert GamePathFinder is not None
        assert PathValidator is not None

    def test_finder_creation(self) -> None:
        """Test creating a GamePathFinder instance."""
        from classic_path import GamePathFinder

        finder = GamePathFinder(
            "Fallout4.exe",
            "f4se_loader.exe",
            "Fallout4",
            False,  # is_vr
        )
        assert finder.game_exe == "Fallout4.exe"
        assert finder.xse_loader == "f4se_loader.exe"
        assert finder.is_vr is False

    def test_finder_vr_mode(self) -> None:
        """Test VR mode finder creation."""
        from classic_path import GamePathFinder

        finder = GamePathFinder(
            "Fallout4VR.exe",
            None,  # No XSE loader specified
            "Fallout4",
            True,  # is_vr
        )
        assert finder.game_exe == "Fallout4VR.exe"
        assert finder.xse_loader is None
        assert finder.is_vr is True

    def test_path_validator_exists(self) -> None:
        """Test PathValidator static methods."""
        from classic_path import PathValidator

        # Test with known existing path
        assert PathValidator.is_valid_path(str(Path.cwd())) is True

        # Test with non-existent path
        assert PathValidator.is_valid_path("/nonexistent/path/xyz") is False

    def test_find_game_path_not_found(self, tmp_path: Path) -> None:
        """Test FileNotFoundError when game not found."""
        from classic_path import GamePathFinder

        finder = GamePathFinder(
            "NonExistent.exe",
            None,
            "NonExistent",
            False,
        )

        with pytest.raises(FileNotFoundError):
            finder.find_game_path(
                cached_path=str(tmp_path),  # Empty temp dir
                xse_log_path=None,
            )

    def test_validate_game_path_invalid(self, tmp_path: Path) -> None:
        """Test ValueError for invalid game path."""
        from classic_path import GamePathFinder

        finder = GamePathFinder(
            "Fallout4.exe",
            None,
            "Fallout4",
            False,
        )

        with pytest.raises(ValueError):
            # Empty directory - no game exe
            finder.validate_game_path(str(tmp_path))


class TestGamePathFactory:
    """Test factory integration."""

    def test_factory_returns_module(self) -> None:
        """Verify factory returns Rust module (not None)."""
        from ClassicLib.integration.factory import get_path_operations

        module = get_path_operations()
        assert module is not None
        assert hasattr(module, "GamePathFinder")
        assert hasattr(module, "PathValidator")

    def test_factory_no_fallback(self) -> None:
        """Verify factory has no try-except fallback (ImportError propagates)."""
        import inspect

        from ClassicLib.integration import factory

        source = inspect.getsource(factory.get_path_operations)
        assert "except ImportError" not in source, "ImportError must propagate"
        assert "except:" not in source, "Bare except not allowed"


class TestPythonWrapperThin:
    """Test that Python wrapper is truly thin."""

    def test_no_python_fallback(self) -> None:
        """Verify game_path.py has no Python fallback code."""
        import ClassicLib.support.game_path as gp

        # Should not have winreg imported
        assert not hasattr(gp, "winreg")

        # Should not have _HAS_RUST_PATH check
        source_path = Path(gp.__file__) if gp.__file__ else None
        if source_path:
            source = source_path.read_text()
            assert "_HAS_RUST_PATH" not in source
            assert "import winreg" not in source

    def test_rust_finder_used_directly(self) -> None:
        """Verify Rust GamePathFinder is imported."""
        source = Path("j:/CLASSIC-Fallout4/ClassicLib/support/game_path.py").read_text()
        assert "from classic_path import" in source or "import classic_path" in source


class TestGlobalRegistryIntegration:
    """Test GlobalRegistry integration for both sync and async paths."""

    def test_sync_path_registers_to_registry(self) -> None:
        """Verify find_game_path registers detected path to GlobalRegistry."""
        source = Path("j:/CLASSIC-Fallout4/ClassicLib/support/game_path.py").read_text()
        # Should have at least 2 registrations (sync and async)
        registration_count = source.count("GlobalRegistry.register")
        game_path_registrations = source.count("GlobalRegistry.Keys.GAME_PATH") + source.count("Keys.GAME_PATH")
        assert game_path_registrations >= 2, "Both sync and async paths must register GAME_PATH"
