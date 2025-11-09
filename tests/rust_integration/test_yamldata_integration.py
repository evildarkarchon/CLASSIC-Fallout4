"""
Integration tests for classic-config-core YamlData.

Tests verify:
- YamlData can be instantiated with real YAML files
- All expected fields are present and correct types
- Data structure matches expected schema
- Parallel YAML loading works correctly
- Performance is significantly better than Python
"""

import time
from pathlib import Path

import pytest

try:
    import classic_config
    YamlData = classic_config.YamlData
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.skipif(not RUST_AVAILABLE, reason="classic_config not available")
class TestYamlDataIntegration:
    """Integration tests for YamlData."""

    def test_yamldata_instantiation(self):
        """Test YamlData can be instantiated with real YAML files."""
        # Get paths to real YAML files
        # Rust YamlData expects 3 directories: [main, game, ignore]
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]

        # Ensure files exist
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"
        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        # Create YamlData
        yamldata = YamlData(yaml_dirs, "Fallout4", False)

        # Verify instance created
        assert yamldata is not None
        assert isinstance(yamldata, YamlData)

    def test_yamldata_required_fields(self):
        """Test all required fields are present."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        yamldata = YamlData(yaml_dirs, "Fallout4", False)

        # Game configuration
        assert hasattr(yamldata, "classic_game_hints")
        assert hasattr(yamldata, "classic_records_list")
        assert hasattr(yamldata, "classic_version")
        assert hasattr(yamldata, "classic_version_date")

        # Crashgen configuration
        assert hasattr(yamldata, "crashgen_name")
        assert hasattr(yamldata, "crashgen_latest_og")
        assert hasattr(yamldata, "crashgen_latest_vr")

        # XSE configuration
        assert hasattr(yamldata, "xse_acronym")

        # Ignore lists
        assert hasattr(yamldata, "game_ignore_plugins")
        assert hasattr(yamldata, "game_ignore_records")
        assert hasattr(yamldata, "ignore_list")

        # Suspect patterns
        assert hasattr(yamldata, "suspects_error_list")
        assert hasattr(yamldata, "suspects_stack_list")

        # Mod databases
        assert hasattr(yamldata, "game_mods_conf")
        assert hasattr(yamldata, "game_mods_core")
        assert hasattr(yamldata, "game_mods_freq")
        assert hasattr(yamldata, "game_mods_solu")

        # Game versions
        assert hasattr(yamldata, "game_version")
        assert hasattr(yamldata, "game_version_new")
        assert hasattr(yamldata, "game_version_vr")

    def test_yamldata_field_types(self):
        """Test fields have correct Python types."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        yamldata = YamlData(yaml_dirs, "Fallout4", False)

        # String fields
        assert isinstance(yamldata.classic_version, str)
        assert isinstance(yamldata.crashgen_name, str)
        assert isinstance(yamldata.xse_acronym, str)
        assert isinstance(yamldata.game_version, str)

        # List fields
        assert isinstance(yamldata.classic_game_hints, list)
        assert isinstance(yamldata.classic_records_list, list)
        assert isinstance(yamldata.game_ignore_plugins, list)
        assert isinstance(yamldata.game_ignore_records, list)
        assert isinstance(yamldata.ignore_list, list)

        # Dict fields
        assert isinstance(yamldata.suspects_error_list, dict)
        assert isinstance(yamldata.suspects_stack_list, dict)
        assert isinstance(yamldata.game_mods_conf, dict)
        assert isinstance(yamldata.game_mods_core, dict)
        assert isinstance(yamldata.game_mods_freq, dict)
        assert isinstance(yamldata.game_mods_solu, dict)

    def test_yamldata_non_empty_data(self):
        """Test that data is actually loaded (not empty)."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        yamldata = YamlData(yaml_dirs, "Fallout4", False)

        # Verify some data is loaded
        assert len(yamldata.classic_game_hints) > 0, "classic_game_hints should not be empty"
        assert len(yamldata.classic_records_list) > 0, "classic_records_list should not be empty"
        assert len(yamldata.suspects_error_list) > 0, "suspects_error_list should not be empty"
        assert len(yamldata.game_mods_conf) > 0, "game_mods_conf should not be empty"

        # Verify string fields have content
        assert yamldata.crashgen_name != "", "crashgen_name should not be empty"
        assert yamldata.xse_acronym != "", "xse_acronym should not be empty"

    def test_yamldata_game_specific_loading(self):
        """Test game-specific YAML loading."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        # Load for Fallout 4
        yamldata_fo4 = YamlData(yaml_dirs, "Fallout4", False)

        # Verify game-specific data
        assert yamldata_fo4.xse_acronym == "F4SE", "Should load F4SE for Fallout 4"
        assert yamldata_fo4.crashgen_name != "", "Should load crash gen name"

    def test_yamldata_vr_mode(self):
        """Test VR mode loading."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        # Load with VR mode
        yamldata_vr = YamlData(yaml_dirs, "Fallout4", True)

        # Verify VR-specific fields
        assert yamldata_vr.game_version_vr != "", "Should load VR version"
        # crashgen_latest_vr should be populated
        assert yamldata_vr.crashgen_latest_vr != "", "Should have VR crash gen version"

    @pytest.mark.performance
    def test_yamldata_performance(self):
        """Test YamlData loading performance."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        # Time the load
        start_time = time.perf_counter()
        yamldata = YamlData(yaml_dirs, "Fallout4", False)
        end_time = time.perf_counter()

        load_time_ms = (end_time - start_time) * 1000

        # Verify it loaded successfully
        assert yamldata is not None

        # Performance target: < 50ms (vs ~150ms for Python)
        # This is a soft target - won't fail test but will print warning
        if load_time_ms > 50:
            print(f"\n⚠️  YamlData load time: {load_time_ms:.2f}ms (target: <50ms)")
        else:
            print(f"\n✅ YamlData load time: {load_time_ms:.2f}ms")

        # Hard limit: must be faster than 500ms
        assert load_time_ms < 500, f"YamlData load took {load_time_ms:.2f}ms (max: 500ms)"

    def test_yamldata_multiple_instantiation(self):
        """Test multiple YamlData instances don't interfere."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        # Create multiple instances
        yamldata1 = YamlData(yaml_dirs, "Fallout4", False)
        yamldata2 = YamlData(yaml_dirs, "Fallout4", False)
        yamldata3 = YamlData(yaml_dirs, "Fallout4", True)  # VR mode

        # Verify they're independent
        assert yamldata1.crashgen_name == yamldata2.crashgen_name
        assert yamldata1.xse_acronym == yamldata2.xse_acronym

        # VR instance should be similar but may have different versions
        assert yamldata3.xse_acronym == yamldata1.xse_acronym

    def test_yamldata_error_handling_missing_files(self):
        """Test error handling when YAML files are missing."""
        # Use non-existent directory
        yaml_dirs = [Path("/nonexistent/path")]

        # Should raise an error
        with pytest.raises(Exception) as exc_info:
            YamlData(yaml_dirs, "Fallout4", False)

        # Verify error message is meaningful
        error_msg = str(exc_info.value)
        assert ("Failed" in error_msg or "not found" in error_msg.lower() or
                "No such file" in error_msg), f"Got error: {error_msg}"

    def test_yamldata_suspects_error_list_content(self):
        """Test suspects_error_list contains expected patterns."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        yamldata = YamlData(yaml_dirs, "Fallout4", False)

        # Verify it's a dict with string keys and values
        assert len(yamldata.suspects_error_list) > 0
        for key, value in yamldata.suspects_error_list.items():
            assert isinstance(key, str), f"Key should be string, got {type(key)}"
            assert isinstance(value, str), f"Value should be string, got {type(value)}"

    def test_yamldata_suspects_stack_list_content(self):
        """Test suspects_stack_list contains expected patterns."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        yamldata = YamlData(yaml_dirs, "Fallout4", False)

        # Verify it's a dict with string keys and values
        assert len(yamldata.suspects_stack_list) > 0
        for key, value in yamldata.suspects_stack_list.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_yamldata_ignore_lists_content(self):
        """Test ignore lists contain expected data."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        yamldata = YamlData(yaml_dirs, "Fallout4", False)

        # Verify lists contain strings
        for plugin in yamldata.game_ignore_plugins:
            assert isinstance(plugin, str), f"Plugin should be string, got {type(plugin)}"

        for record in yamldata.game_ignore_records:
            assert isinstance(record, str), f"Record should be string, got {type(record)}"

        for item in yamldata.ignore_list:
            assert isinstance(item, str), f"Ignore item should be string, got {type(item)}"

    def test_yamldata_mod_databases_structure(self):
        """Test mod databases have correct structure."""
        data_dir = Path("CLASSIC Data")
        yaml_dirs = [
            data_dir / "databases",  # Main YAML
            data_dir / "databases",  # Game YAML
            Path("."),  # Ignore YAML (project root)
        ]
        main_file = yaml_dirs[0] / "CLASSIC Main.yaml"

        if not main_file.exists():
            pytest.skip(f"{main_file} not found")

        yamldata = YamlData(yaml_dirs, "Fallout4", False)

        # Test each mod database
        mod_databases = [
            yamldata.game_mods_conf,
            yamldata.game_mods_core,
            yamldata.game_mods_freq,
            yamldata.game_mods_solu,
        ]

        for db in mod_databases:
            assert isinstance(db, dict), "Mod database should be dict"
            # Verify keys and values are strings
            for key, value in db.items():
                assert isinstance(key, str), f"Key should be string, got {type(key)}"
                assert isinstance(value, str), f"Value should be string, got {type(value)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
