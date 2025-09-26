"""Test GameIntegrity with synthetic game file structures.

This module tests game file integrity checking using only synthetic/mock
data structures that simulate game files without using any actual
copyrighted game content.
"""

import pytest
import tempfile
import json
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open
from typing import Dict, List, Any, Optional
import shutil
import os
import random

# Mark all tests in this module
pytestmark = [pytest.mark.unit, pytest.mark.integration]


class SyntheticGameFileGenerator:
    """Generate synthetic game file structures for testing."""

    @staticmethod
    def generate_formid(plugin_index: int = 0, local_id: Optional[int] = None) -> str:
        """Generate a synthetic FormID in proper hex format."""
        if local_id is None:
            local_id = random.randint(0x000001, 0xFFFFFF)
        # FormID format: XX######
        # XX = plugin load order index (00 for base game, FE for light plugins)
        return f"{plugin_index:02X}{local_id:06X}"

    @staticmethod
    def generate_light_formid(plugin_index: int = 0xFE, local_id: Optional[int] = None) -> str:
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
    def create_mock_archive(name: str, num_files: int = 10) -> bytes:
        """Create mock archive file content."""
        # Synthetic archive header
        header = b"SYNTH_ARCHIVE_V1"
        # Mock file entries
        entries = []
        for i in range(num_files):
            entry = f"file_{i}.dds:offset:{i*1000}:size:1000\n".encode()
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
    def synthetic_game_dir(self):
        """Create a temporary directory with synthetic game structure."""
        temp_dir = tempfile.mkdtemp(prefix="synthetic_game_")

        # Create directory structure
        (Path(temp_dir) / "Data").mkdir()
        (Path(temp_dir) / "Data" / "Scripts").mkdir()
        (Path(temp_dir) / "Data" / "Meshes").mkdir()
        (Path(temp_dir) / "Data" / "Textures").mkdir()
        (Path(temp_dir) / "F4SE" / "Plugins").mkdir(parents=True)

        yield Path(temp_dir)

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_game_files(self, synthetic_game_dir):
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

        return synthetic_game_dir

    def test_game_directory_validation(self, mock_game_files):
        """Test validation of game directory structure."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        checker = GameIntegrityChecker(str(mock_game_files))

        # Should detect the synthetic game structure
        assert checker.validate_game_directory()

        # Check required directories exist
        assert checker.has_data_directory()
        assert checker.has_required_masters()

    def test_missing_master_file_detection(self, synthetic_game_dir):
        """Test detection of missing master files."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        # Create directory with missing masters
        (synthetic_game_dir / "Data").mkdir(exist_ok=True)

        checker = GameIntegrityChecker(str(synthetic_game_dir))

        # Should detect missing masters
        missing = checker.get_missing_masters()
        assert len(missing) > 0
        assert "Fallout4.esm" in missing

    def test_plugin_load_order_validation(self, mock_game_files):
        """Test plugin load order validation with synthetic plugins."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        checker = GameIntegrityChecker(str(mock_game_files))

        # Create synthetic load order
        load_order = [
            "Fallout4.esm",
            "DLCRobot.esm",
            "DLCworkshop01.esm",
            "SyntheticLight.esl",  # Light plugins can load early
            "SyntheticMod_0.esp",
            "SyntheticMod_1.esp",
        ]

        # Validate load order
        issues = checker.validate_load_order(load_order)

        # Masters should come before regular plugins
        assert len(issues) == 0 or all("order" in issue.lower() for issue in issues)

    def test_formid_conflict_detection(self, mock_game_files):
        """Test FormID conflict detection with proper hex FormIDs."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        checker = GameIntegrityChecker(str(mock_game_files))

        # Create synthetic FormID conflicts using proper hex format
        plugin_formids = {
            "SyntheticMod_0.esp": [
                "03001000", "03001001", "03001002",  # Plugin index 03
                "00000014"  # Override from base game
            ],
            "SyntheticMod_1.esp": [
                "04001000", "04001001",  # Plugin index 04
                "03001000",  # Conflict! Same FormID as Mod_0
                "00000014"  # Another base game override
            ],
            "SyntheticLight.esl": [
                "FE000800", "FE000801", "FE000802"  # Light plugin FormIDs
            ]
        }

        # Detect conflicts
        conflicts = checker.detect_formid_conflicts(plugin_formids)

        # Should detect the overlapping FormIDs
        assert len(conflicts) > 0
        # Should find the conflict on 03001000
        assert any("03001000" in str(conflict) for conflict in conflicts)
        # Should find base game overrides
        assert any("00000014" in str(conflict) for conflict in conflicts)

    def test_corrupt_file_detection(self, mock_game_files):
        """Test detection of corrupted files using synthetic data."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        # Corrupt a synthetic plugin
        plugin_path = mock_game_files / "Data" / "SyntheticMod_0.esp"
        plugin_path.write_bytes(b"CORRUPTED_DATA_XXXXX")

        checker = GameIntegrityChecker(str(mock_game_files))

        # Should detect the corrupted file
        corrupted = checker.scan_for_corrupted_files()
        assert len(corrupted) > 0
        assert any("SyntheticMod_0.esp" in str(f) for f in corrupted)

    def test_file_hash_verification(self, mock_game_files):
        """Test file hash verification with synthetic files."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        checker = GameIntegrityChecker(str(mock_game_files))

        # Calculate hashes for synthetic files
        hashes = {}
        for file_path in (mock_game_files / "Data").glob("*.esm"):
            content = file_path.read_bytes()
            hashes[file_path.name] = hashlib.sha256(content).hexdigest()

        # Verify hashes
        verification_results = checker.verify_file_hashes(hashes)

        # All should match since we just calculated them
        assert all(result["valid"] for result in verification_results.values())

    def test_dependency_chain_analysis(self, mock_game_files):
        """Test plugin dependency chain analysis with synthetic data."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        checker = GameIntegrityChecker(str(mock_game_files))

        # Create synthetic dependency chain with hex plugin indices
        dependencies = {
            "SyntheticMod_0.esp": ["Fallout4.esm"],  # Index 03 depends on 00
            "SyntheticMod_1.esp": ["Fallout4.esm", "DLCRobot.esm"],  # Index 04 depends on 00, 01
            "SyntheticMod_2.esp": ["Fallout4.esm", "SyntheticMod_0.esp"],  # Index 05 depends on 00, 03
            "SyntheticLight.esl": ["Fallout4.esm"],  # Light plugin FE depends on 00
        }

        # Analyze dependency chain
        issues = checker.analyze_dependencies(dependencies)

        # Check for circular dependencies or missing masters
        assert isinstance(issues, list)
        # Should not have circular dependencies in this synthetic data
        assert not any("circular" in str(issue).lower() for issue in issues)

    def test_light_plugin_validation(self, mock_game_files):
        """Test light plugin (ESL) validation with proper FormID ranges."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        checker = GameIntegrityChecker(str(mock_game_files))

        # Light plugins should have FormIDs in FE000800-FE000FFF range
        light_plugin_data = {
            "SyntheticLight.esl": {
                "formids": ["FE000800", "FE000801", "FE000900", "FE000FFF"],  # Valid range
                "type": "light"
            },
            "InvalidLight.esl": {
                "formids": ["FE001000", "FE002000"],  # Outside valid range!
                "type": "light"
            }
        }

        # Validate light plugins
        issues = checker.validate_light_plugins(light_plugin_data)

        # Should detect FormIDs outside valid range for light plugins
        assert any("range" in str(issue).lower() or "invalid" in str(issue).lower() for issue in issues)

    def test_mod_conflict_detection_with_hex_formids(self, mock_game_files):
        """Test mod conflict detection with proper hex FormIDs."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        checker = GameIntegrityChecker(str(mock_game_files))

        # Create synthetic conflict data with hex FormIDs
        mod_overrides = {
            "SyntheticMod_0.esp": ["00000014", "0000001A", "03001000"],  # Overrides base game FormIDs
            "SyntheticMod_1.esp": ["00000014", "01000100", "04001000"],  # Also overrides 00000014
            "SyntheticMod_2.esp": ["03001000", "05001000"],  # Conflicts with Mod_0's FormID
        }

        # Detect conflicts
        conflicts = checker.detect_mod_conflicts(mod_overrides)

        # Should detect the overlapping FormIDs
        assert len(conflicts) > 0
        # Should detect base game override conflict
        assert any("00000014" in str(conflict) for conflict in conflicts)
        # Should detect mod-to-mod conflict
        assert any("03001000" in str(conflict) for conflict in conflicts)

    def test_formid_parsing_validation(self):
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

    def test_archive_integrity_check(self, mock_game_files):
        """Test archive file integrity checking."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        checker = GameIntegrityChecker(str(mock_game_files))

        # Check synthetic archives
        archive_results = checker.check_archive_integrity()

        # Should detect our synthetic archives
        assert len(archive_results) > 0
        assert all(
            result["valid"] or result["reason"] == "synthetic"
            for result in archive_results.values()
        )

    def test_performance_with_many_formids(self, synthetic_game_dir):
        """Test performance with many synthetic FormIDs."""
        from ClassicLib.ScanGame.GameIntegrity import GameIntegrityChecker

        # Create plugin with many FormIDs
        data_dir = synthetic_game_dir / "Data"
        data_dir.mkdir(exist_ok=True)

        generator = SyntheticGameFileGenerator()

        # Generate 10000 unique FormIDs
        formids = set()
        for i in range(10000):
            plugin_index = (i // 1000) % 256
            local_id = i % 0xFFFFFF + 1
            formids.add(generator.generate_formid(plugin_index, local_id))

        # Create test plugin with these FormIDs
        plugin_path = data_dir / "MassivePlugin.esp"
        content = b"SYNTH_PLUGIN_V1.0\nFORMIDS:" + b",".join(f.encode() for f in formids)
        plugin_path.write_bytes(content)

        import time
        start = time.time()

        checker = GameIntegrityChecker(str(synthetic_game_dir))
        # Process the FormIDs
        checker.analyze_plugin_formids("MassivePlugin.esp", list(formids))

        elapsed = time.time() - start

        # Should complete quickly even with 10000 FormIDs
        assert elapsed < 5.0  # 5 seconds for 10000 FormIDs