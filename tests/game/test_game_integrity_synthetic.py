"""Test GameIntegrity with synthetic game file structures.

This module tests game file integrity checking using only synthetic/mock
data structures that simulate game files without using any actual
copyrighted game content.
"""

import random
from collections.abc import Generator
from pathlib import Path

import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.integration]


class SyntheticGameFileGenerator:
    """Generate synthetic game file structures for testing."""

    @staticmethod
    def generate_formid(plugin_index: int = 0, local_id: int | None = None) -> str:
        """Generate a synthetic FormID in proper hex format."""
        if local_id is None:
            local_id = random.randint(0x000001, 0xFFFFFF)
        # FormID format: XX######
        # XX = plugin load order index (00 for base game, FE for light plugins)
        return f"{plugin_index:02X}{local_id:06X}"

    @staticmethod
    def generate_light_formid(plugin_index: int = 0xFE, local_id: int | None = None) -> str:
        """Generate a light plugin FormID (FE prefix)."""
        if local_id is None:
            local_id = random.randint(0x000800, 0x000FFF)  # Light plugin range
        return f"{plugin_index:02X}{local_id:06X}"

    @staticmethod
    def create_mock_plugin(name: str, size: int = 1000, num_formids: int = 10) -> bytes:
        """Create mock plugin file content with proper FormIDs."""
        # Synthetic plugin header (not real game format)
        header = b"SYNTH_PLUGIN_V1.0"

        # Determine plugin index based on name
        if ".esm" in name:
            if "Fallout4" in name:
                plugin_index = 0x00
            elif "DLC" in name:
                plugin_index = 0x01
            else:
                plugin_index = 0x02
        elif ".esl" in name:
            plugin_index = 0xFE  # Light plugin
        else:  # .esp
            plugin_index = random.randint(0x03, 0x7F)

        # Add mock FormIDs in hex format
        formids = []
        for i in range(num_formids):
            if ".esl" in name:
                formid = SyntheticGameFileGenerator.generate_light_formid(plugin_index, 0x000800 + i)
            else:
                formid = SyntheticGameFileGenerator.generate_formid(plugin_index, 0x001000 + i)
            formids.append(formid.encode())

        formid_section = b"FORMIDS:" + b",".join(formids) + b"\n"

        # Add padding to reach desired size
        padding = b"\x00" * max(0, size - len(header) - len(formid_section))
        return header + formid_section + padding

    @staticmethod
    def create_mock_archive(_name: str, num_files: int = 10) -> bytes:
        """Create mock archive file content."""
        # Synthetic archive header
        header = b"SYNTH_ARCHIVE_V1"
        # Mock file entries
        entries = []
        for i in range(num_files):
            entry = f"file_{i}.dds:offset:{i * 1000}:size:1000\n".encode()
            entries.append(entry)
        return header + b"".join(entries)

    @staticmethod
    def create_mock_script(name: str) -> str:
        """Create mock script file content."""
        return f"""
        ; Synthetic Script File: {name}
        ScriptName Synthetic_{name}

        Function MockFunction()
            ; This is synthetic test content
            Debug.Trace("Synthetic script execution")
        EndFunction

        Event OnInit()
            MockFunction()
        EndEvent
        """

    @staticmethod
    def create_mock_ini_file() -> str:
        """Create mock INI configuration."""
        return """
        [General]
        sLanguage=en
        bSynthetic=1
        iTestValue=42

        [Display]
        iWidth=1920
        iHeight=1080
        bFullscreen=0

        [Archive]
        bInvalidateOlderFiles=1
        sResourceDataDirsFinal=STRINGS\\, MESHES\\, TEXTURES\\
        """


class TestGameIntegritySynthetic:
    """Test GameIntegrity with synthetic data."""

    @pytest.fixture
    def synthetic_game_dir(self, tmp_path) -> Generator[Path, None, None]:  # noqa: PLR6301
        """Create a temporary directory with synthetic game structure."""
        game_dir = tmp_path / "synthetic_game"
        game_dir.mkdir()

        # Create directory structure
        (game_dir / "Data").mkdir()
        (game_dir / "Data" / "Scripts").mkdir()
        (game_dir / "Data" / "Meshes").mkdir()
        (game_dir / "Data" / "Textures").mkdir()
        (game_dir / "F4SE" / "Plugins").mkdir(parents=True)

        return game_dir
        # Cleanup handled by tmp_path fixture

    @pytest.fixture
    def mock_game_files(self, synthetic_game_dir: Path) -> Path:  # noqa: PLR6301
        """Create mock game files in the synthetic directory."""
        generator = SyntheticGameFileGenerator()

        # Create mock master files
        masters = [
            ("Fallout4.esm", 50000000, 1000),  # filename, size, num_formids
            ("DLCRobot.esm", 30000000, 500),
            ("DLCworkshop01.esm", 20000000, 300),
        ]

        for filename, size, num_formids in masters:
            file_path = synthetic_game_dir / "Data" / filename
            content = generator.create_mock_plugin(filename, min(size, 10000), num_formids)
            file_path.write_bytes(content)

        # Create mock mod plugins with proper FormIDs
        for i in range(5):
            plugin_name = f"SyntheticMod_{i}.esp"
            file_path = synthetic_game_dir / "Data" / plugin_name
            content = generator.create_mock_plugin(plugin_name, 1000, 20)
            file_path.write_bytes(content)

        # Create a light plugin
        light_plugin = "SyntheticLight.esl"
        file_path = synthetic_game_dir / "Data" / light_plugin
        content = generator.create_mock_plugin(light_plugin, 500, 10)
        file_path.write_bytes(content)

        # Create mock archives
        archives = ["Textures.ba2", "Meshes.ba2", "Sounds.ba2"]
        for archive in archives:
            file_path = synthetic_game_dir / "Data" / archive
            content = generator.create_mock_archive(archive)
            file_path.write_bytes(content)

        # Create mock scripts
        for i in range(3):
            script_name = f"TestScript_{i}"
            file_path = synthetic_game_dir / "Data" / "Scripts" / f"{script_name}.pex"
            content = generator.create_mock_script(script_name).encode()
            file_path.write_bytes(content)

        # Create mock INI file
        ini_path = synthetic_game_dir / "Fallout4.ini"
        ini_path.write_text(generator.create_mock_ini_file())

        # Create mock executable
        exe_path = synthetic_game_dir / "Fallout4.exe"
        exe_path.write_bytes(b"Fake Fallout 4 Executable")

        return synthetic_game_dir

    @pytest.mark.asyncio
    async def test_game_directory_validation(self, mock_game_files: Path) -> None:  # noqa: PLR6301
        """Test validation of game directory structure."""
        from unittest.mock import AsyncMock, patch

        from ClassicLib.GameIntegrity import GameIntegrityChecker

        # Mock dependencies for load_configuration_async
        with (
            patch("ClassicLib.GlobalRegistry.get_vr", return_value="") as _mock_get_vr,
            patch("ClassicLib.YamlSettings.yaml_settings_async", new_callable=AsyncMock) as mock_yaml_settings_async,
            patch("ClassicLib.GameIntegrity.calculate_file_hash", return_value="some_new_hash"),
        ):  # Mock file hash calc
            # Configure mock_yaml_settings_async to return values expected by load_configuration_async
            mock_yaml_settings_async.side_effect = [
                "some/steam/ini/path",  # steam_ini_path
                "some_old_hash",  # exe_hash_old
                "some_new_hash",  # exe_hash_new
                str(mock_game_files / "Fallout4.exe"),  # game_exe_path
                "Fallout4",  # root_name
                "Some warning message",  # root_warn
            ]

            checker = GameIntegrityChecker()
            await checker.load_configuration_async()  # Load config internally

            # Should detect the synthetic game structure
            result = await checker.run_full_check_async()
            assert "Your Fallout4 game files are installed outside of the Program Files folder!" in result
            assert "You have the latest version of Fallout4!" in result

    @pytest.mark.asyncio
    async def test_missing_master_file_detection(self, synthetic_game_dir: Path) -> None:  # noqa: PLR6301
        """Test detection of missing master files."""
        from unittest.mock import AsyncMock, patch

        from ClassicLib.GameIntegrity import GameIntegrityChecker

        # Create directory with missing masters - now this means the mocked config will point to non-existent files
        (synthetic_game_dir / "Data").mkdir(exist_ok=True)

        # Mock dependencies for load_configuration_async
        with (
            patch("ClassicLib.GlobalRegistry.get_vr", return_value="") as _mock_get_vr,
            patch("ClassicLib.YamlSettings.yaml_settings_async", new_callable=AsyncMock) as mock_yaml_settings_async,
            patch("ClassicLib.GameIntegrity.calculate_file_hash", return_value="some_new_hash"),
        ):  # Mock file hash calc
            # Configure mock_yaml_settings_async to return values expected by load_configuration_async
            mock_yaml_settings_async.side_effect = [
                "some/nonexistent/steam/ini/path",  # steam_ini_path (non-existent to trigger out-of-date)
                "some_old_hash",  # exe_hash_old
                "some_new_hash",  # exe_hash_new
                str(synthetic_game_dir / "nonexistent_game.exe"),  # game_exe_path (non-existent)
                "Fallout4",  # root_name
                "Some warning message",  # root_warn
            ]

            checker = GameIntegrityChecker()
            await checker.load_configuration_async()  # Load config internally

            # Should detect missing masters (reported as "Game executable not found" or "out of date")
            result = await checker.run_full_check_async()
            assert "Game executable not found" in result or "OUT OF DATE" in result

    def test_formid_parsing_validation(self) -> None:  # noqa: PLR6301
        """Test that FormIDs are properly validated as hex values."""
        generator = SyntheticGameFileGenerator()

        # Valid FormIDs
        valid_formids = [
            "00000001",  # Base game
            "01A3B4C5",  # DLC
            "FE000800",  # Light plugin minimum
            "FE000FFF",  # Light plugin maximum
            "7FFFFFFF",  # Maximum valid FormID
        ]

        for formid in valid_formids:
            # Should be valid 8-character hex strings
            assert len(formid) == 8
            assert all(c in "0123456789ABCDEFabcdef" for c in formid)
            # Should convert to integer
            int(formid, 16)

        # Test generated FormIDs
        for i in range(100):
            formid = generator.generate_formid(i % 256)
            assert len(formid) == 8
            assert all(c in "0123456789ABCDEF" for c in formid)
            value = int(formid, 16)
            assert 0 <= value <= 0xFFFFFFFF
