"""
Tests for classic_config.YamlData, ensuring parity with Rust implementation.

This module focuses on verifying the correct loading, initialization,
property access, and error handling of the YamlData class, which
provides structured access to the CLASSIC configuration loaded from YAML files.
"""
# ruff: noqa: ANN201, ANN001, PLR6301, ARG002, PLC2701

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ClassicLib import GlobalRegistry, Keys
from ClassicLib.GlobalRegistry import _registry, _registry_lock  # Import internal registry

if TYPE_CHECKING:
    import classic_config
    RUST_CONFIG_AVAILABLE = True
else:
    try:
        import classic_config
        RUST_CONFIG_AVAILABLE = True
    except ImportError:
        classic_config = None
        RUST_CONFIG_AVAILABLE = False


@pytest.fixture
def setup_global_registry(create_mock_yaml_config: Path):
    """
    Fixture to initialize and clear the GlobalRegistry for tests.
    Sets up game, vr_mode, and local_dir.
    """
    # Clear YAML cache to ensure clean state between tests
    if RUST_CONFIG_AVAILABLE and classic_config:
        classic_config.clear_yaml_cache() # pyright: ignore[reportAttributeAccessIssue]

    # Ensure registry is clear before each test
    with _registry_lock:
        _registry.clear()

    # Register mock values
    GlobalRegistry.register(Keys.GAME, "Fallout4")
    GlobalRegistry.register(Keys.VR, "")  # Not in VR mode by default
    GlobalRegistry.register(Keys.LOCAL_DIR, create_mock_yaml_config)
    GlobalRegistry.register(Keys.IS_GUI_MODE, False)  # Assume CLI mode for these tests

    yield

    # Ensure registry is clear after each test
    with _registry_lock:
        _registry.clear()

    # Clear YAML cache after test
    if RUST_CONFIG_AVAILABLE and classic_config:
        classic_config.clear_yaml_cache() # pyright: ignore[reportAttributeAccessIssue]


@pytest.fixture
def create_mock_yaml_config():
    """
    Fixture to create a temporary directory with mock YAML configuration files.
    Yields the path to the main YAML directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # Create CLASSIC Data/databases directory structure
        data_dir = base_path / "CLASSIC Data"
        db_dir = data_dir / "databases"
        db_dir.mkdir(parents=True, exist_ok=True)

        # Create CLASSIC Main.yaml in databases dir
        (db_dir / "CLASSIC Main.yaml").write_text(
            "CLASSIC_Info:\n"
            '  version: "CLASSIC v8.0.0"\n'
            '  version_date: "25.08.24"\n'
            "  is_prerelease: true\n"
            "  \n"
            "  default_settings: |\n"
            "    CLASSIC_Settings:\n"
            "      Managed Game: Fallout 4\n"
            "  default_localyaml: |\n"
            "    Game_Info:\n"
            "      Root_Folder_Game:\n"
            "  default_ignorefile: |\n"
            "    CLASSIC_Ignore_Fallout4:\n"
            "      - Example Plugin.esp\n"
        )

        # Create CLASSIC Ignore.yaml in root dir
        (base_path / "CLASSIC Ignore.yaml").write_text('CLASSIC_Ignore_Fallout4:\n  - "ignore_pattern_1"\n  - "ignore_pattern_2"\n')

        # Create CLASSIC Fallout4.yaml in databases dir
        (db_dir / "CLASSIC Fallout4.yaml").write_text(
            "Game_Info:\n"
            "  Main_Root_Name: Fallout 4\n"
            "  Main_Docs_Name: Fallout4\n"
            "  GameVersion: 1.10.163\n"
            "  GameVersionNEW: 1.10.163\n"
            "  CRASHGEN_Acronym: BO4\n"
            "  CRASHGEN_LogName: Buffout 4\n"
            "  CRASHGEN_DLL_File: buffout4.dll\n"
            "  CRASHGEN_LatestVer: 1.2.9\n"
            "  XSE_Acronym: F4SE\n"
            "\n"
            "GameVR_Info:\n"
            "  Main_Root_Name: Fallout 4 VR\n"
            "  Main_Docs_Name: Fallout4VR\n"
            "  GameVersion: 1.2.72\n"
            "  CRASHGEN_Acronym: BO4 NG\n"
            "  CRASHGEN_LogName: Buffout 4\n"
            "  CRASHGEN_DLL_File: buffout4.dll\n"
            "  CRASHGEN_LatestVer: 1.37.0\n"
            "  XSE_Acronym: F4SEVR\n"
            "\n"
            "Mods_CORE:\n"
            '  ModA: "PatternA"\n'
            "\n"
            "Mods_FREQ:\n"
            '  ModB: "PatternB"\n'
        )

        # Yield the base directory for tests to use
        yield base_path


@pytest.mark.rust
@pytest.mark.skipif(not RUST_CONFIG_AVAILABLE, reason="Rust config module not available")
class TestYamlData:
    """Tests for the classic_config.YamlData class."""

    def test_init_and_property_access(self, create_mock_yaml_config: Path, setup_global_registry):
        """
        Test successful initialization and access to various properties.
        """
        yaml_dirs: list[str | Path] = [str(create_mock_yaml_config), str(create_mock_yaml_config / "CLASSIC Data")]
        game = GlobalRegistry.get_game()
        vr_mode = bool(GlobalRegistry.get_vr())

        yaml_data = classic_config.create_yamldata(yaml_dirs, game, vr_mode)

        # Test CLASSIC version information
        assert yaml_data.classic_version == "CLASSIC v8.0.0"
        assert yaml_data.classic_version_date == "25.08.24"
        assert yaml_data.game_version == "1.10.163"
        assert yaml_data.game_version_new == "1.10.163"  # From Game_Info.GameVersionNEW
        assert yaml_data.game_version_vr == "1.2.72"  # From GameVR_Info.GameVersion

        # Test Crash generator settings
        assert yaml_data.crashgen_name == "Buffout 4"  # From Game_Info.CRASHGEN_LogName
        assert yaml_data.crashgen_latest_og == "1.2.9"  # From Game_Info.CRASHGEN_LatestVer
        assert yaml_data.crashgen_latest_vr == "1.37.0"  # From GameVR_Info.CRASHGEN_LatestVer

        # Test Script extender configuration
        assert yaml_data.xse_acronym == "F4SE"  # From Game_Info.XSE_Acronym

        # Test Ignore lists
        assert yaml_data.ignore_list == ["ignore_pattern_1", "ignore_pattern_2"]
        assert yaml_data.game_ignore_plugins == []  # Not defined in mock
        assert yaml_data.game_ignore_records == []  # Not defined in mock
        assert isinstance(yaml_data.crashgen_ignore, set)
        assert len(yaml_data.crashgen_ignore) == 0  # Not defined in mock

        # Test Mod detection lists
        assert yaml_data.game_mods_core == {"ModA": "PatternA"}
        assert yaml_data.game_mods_freq == {"ModB": "PatternB"}

        # Test Records configuration
        assert yaml_data.classic_records_list == []  # Not defined in mock

        # Test Suspect detection lists
        assert yaml_data.suspects_error_list == {}
        assert yaml_data.suspects_stack_list == {}

    def test_init_missing_yaml_dir(self, create_mock_yaml_config: Path, setup_global_registry):
        """Test initialization with a non-existent YAML directory."""
        # Test with missing data directory
        yaml_dirs: list[str | Path] = [str(create_mock_yaml_config), str(create_mock_yaml_config / "YAML" / "NonExistent")]
        game = GlobalRegistry.get_game()
        vr_mode = bool(GlobalRegistry.get_vr())
        with pytest.raises(classic_config.RustConfigIOError, match="YAML file not found"): # pyright: ignore[reportAttributeAccessIssue]
            classic_config.YamlData(yaml_dirs, game, vr_mode)

    def test_init_malformed_yaml(self, create_mock_yaml_config: Path, setup_global_registry):
        """Test initialization with a malformed YAML file."""
        # Overwrite Main config with malformed content
        main_yaml_path = create_mock_yaml_config / "CLASSIC Data" / "databases" / "CLASSIC Main.yaml"
        main_yaml_path.write_text("{ key: value:")

        yaml_dirs: list[str | Path] = [str(create_mock_yaml_config), str(create_mock_yaml_config / "CLASSIC Data")]
        game = GlobalRegistry.get_game()
        vr_mode = bool(GlobalRegistry.get_vr())

        with pytest.raises(classic_config.RustConfigParseError, match="Parse error"): # pyright: ignore[reportAttributeAccessIssue]
            classic_config.create_yamldata(yaml_dirs, game, vr_mode)

    def test_init_invalid_game(self, create_mock_yaml_config: Path, setup_global_registry):
        """Test initialization with an invalid game name."""
        yaml_dirs: list[str | Path] = [str(create_mock_yaml_config), str(create_mock_yaml_config / "CLASSIC Data")]
        # This test specifically sets an invalid game name
        game = "InvalidGame"
        vr_mode = bool(GlobalRegistry.get_vr())  # Use the mocked VR mode

        # Assuming the Rust backend would validate game names and raise an error
        # The exact error type might need adjustment based on Rust's PyO3 error handling
        with pytest.raises(classic_config.RustConfigIOError, match=r"YAML file not found: .*CLASSIC InvalidGame.yaml"): # pyright: ignore[reportAttributeAccessIssue]
            classic_config.YamlData(yaml_dirs, game, vr_mode)

    def test_create_yamldata_factory(self, create_mock_yaml_config: Path, setup_global_registry):
        """Test the create_yamldata factory function."""
        yaml_dirs: list[str | Path] = [str(create_mock_yaml_config), str(create_mock_yaml_config / "CLASSIC Data")]
        game = GlobalRegistry.get_game()
        vr_mode = bool(GlobalRegistry.get_vr())

        yaml_data = classic_config.create_yamldata(yaml_dirs, game, vr_mode)
        assert isinstance(yaml_data, classic_config.YamlData)
        assert yaml_data.classic_version == "CLASSIC v8.0.0"

    def test_singleton_behavior(self, create_mock_yaml_config: Path, setup_global_registry):
        """
        Test that YamlData exhibits singleton-like behavior or effective caching
        where subsequent identical initializations return the same data.
        """
        yaml_dirs: list[str | Path] = [str(create_mock_yaml_config), str(create_mock_yaml_config / "CLASSIC Data")]
        game = GlobalRegistry.get_game()
        vr_mode = bool(GlobalRegistry.get_vr())

        # First instance
        instance1 = classic_config.create_yamldata(yaml_dirs, game, vr_mode)
        # Second instance with same parameters
        instance2 = classic_config.create_yamldata(yaml_dirs, game, vr_mode)

        # Due to caching, the internal data should be identical and not reloaded
        # We can't directly compare objects for identity (is), but their data should be the same.
        # This checks if the properties are consistent.
        assert instance1.classic_version == instance2.classic_version
        assert instance1.classic_version_date == instance2.classic_version_date
        assert instance1.game_version == instance2.game_version
        assert instance1.game_version_new == instance2.game_version_new
        assert instance1.game_version_vr == instance2.game_version_vr
        assert instance1.crashgen_name == instance2.crashgen_name
        assert instance1.crashgen_latest_og == instance2.crashgen_latest_og
        assert instance1.crashgen_latest_vr == instance2.crashgen_latest_vr
        assert instance1.xse_acronym == instance2.xse_acronym
        assert instance1.ignore_list == instance2.ignore_list
        assert instance1.game_mods_core == instance2.game_mods_core
        assert instance1.game_mods_freq == instance2.game_mods_freq

        # Test if modifying the underlying files affects subsequent loads
        # This requires an actual file change
        version_file = create_mock_yaml_config / "CLASSIC Data" / "databases" / "CLASSIC Main.yaml"
        original_content = version_file.read_text()

        # Change a value
        version_file.write_text(original_content.replace("CLASSIC v8.0.0", "CLASSIC v8.0.1"))

        # A new instance should reflect the change, demonstrating proper cache invalidation
        # or non-strict singleton behavior when files change.
        # This assumes the Rust backend reloads if file timestamps/content change.
        instance3 = classic_config.create_yamldata(yaml_dirs, game, vr_mode)
        assert instance3.classic_version == "CLASSIC v8.0.1"

    @pytest.mark.skip(reason="Skyrim support not fully implemented in Rust backend yet")
    def test_different_game_instance(self, create_mock_yaml_config: Path, setup_global_registry):
        """
        Test that different game parameters result in distinct YamlData instances
        with different data, even if sharing some YAML files.
        """
        # This test is currently skipped as Skyrim support is not yet fully implemented.
        # It would typically involve setting up Skyrim-specific YAMLs and GlobalRegistry entries
        # and asserting Skyrim-specific properties.

    def test_different_vr_mode_instance(self, create_mock_yaml_config: Path, setup_global_registry):
        """
        Test that different VR mode parameters result in distinct YamlData instances
        with potentially different data.
        """
        yaml_dirs: list[str | Path] = [str(create_mock_yaml_config), str(create_mock_yaml_config / "CLASSIC Data")]

        # Non-VR instance
        non_vr_data = classic_config.create_yamldata(yaml_dirs, "Fallout4", False)
        assert non_vr_data.game_version == "1.10.163"  # Non-VR specific version

        # VR instance
        vr_data = classic_config.create_yamldata(yaml_dirs, "Fallout4", True)
        assert vr_data.game_version == "1.10.163"  # Non-VR specific version
        assert vr_data.game_version_vr == "1.2.72"  # VR specific version
        assert non_vr_data.game_version != vr_data.game_version_vr  # They should be different