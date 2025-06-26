"""
Pytest configuration file for CLASSIC-Fallout4 test suite.

This file contains shared fixtures and configuration that are available to all test modules.
"""

import sys
import tempfile
import shutil
import os
from collections.abc import Callable, Generator
from pathlib import Path
from types import ModuleType
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Ensure the parent directory is in sys.path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.YamlSettingsCache import YamlSettingsCache


@pytest.fixture
def init_message_handler_fixture() -> Generator[None, None, None]:
    """Initialize the MessageHandler for tests that need it."""
    handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    # Clear the handler after the test
    import ClassicLib.MessageHandler

    ClassicLib.MessageHandler._message_handler = None


@pytest.fixture
def sample_crash_logs_dir() -> Callable[[Path], Path]:
    """Fixture to create a temporary crash logs directory with sample files."""

    # Create a temporary directory with pytest's tmp_path
    def _create_sample_logs(tmp_path: Path) -> Path:
        crash_logs_dir: Path = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir(exist_ok=True)

        # Create a simple crash log file
        simple_log: Path = crash_logs_dir / "crash-2023-01-01-00-00-00.log"
        simple_log.write_text("""Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] ProblemPlugin.esp
""")

        return crash_logs_dir

    return _create_sample_logs


@pytest.fixture
def mock_global_registry() -> Generator[ModuleType, None, None]:
    """Mock the GlobalRegistry to return test values."""
    """Mock the GlobalRegistry to return test values."""
    original_values = {}

    # Save original values
    for key in GlobalRegistry._registry:
        original_values[key] = GlobalRegistry.get(key)

    # Set test values
    GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
    GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

    yield GlobalRegistry

    # Restore original values
    for key, value in original_values.items():
        GlobalRegistry.register(key, value)


@pytest.fixture
def mock_yaml_settings() -> Generator[MagicMock, None, None]:
    """Mock YAML settings for testing."""
    with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:

        def side_effect(_type_arg: Any, yaml_store: Any, key_path: str, new_value: Any = None) -> Any:  # noqa: ARG001
            if key_path == "catch_log_records":
                return ["Record1", "Record2"]
            if key_path == "Game_Info.CRASHGEN_LogName":
                return "Buffout 4"
            if key_path == "Game_Info.XSE_Acronym":
                return "F4SE"
            if key_path == "CLASSIC_Info.default_settings":
                return r"""# This file contains settings for CLASSIC v7.00+, used by both source scripts and the executable.

CLASSIC_Settings:

# Set the game that you want CLASSIC to currently manage. (Fallout 4 | Skyrim SE | Starfield)
  Managed Game: Fallout 4

# Set to true if you want CLASSIC to periodically check for its own updates online through GitHub.
  Update Check: true

# Set to true if you want CLASSIC to prioritize scanning the Virtual Reality version of your game.
  VR Mode: false

# FCX - File Check Xtended | Set to true if you want CLASSIC to check the integrity of your game files and core mods.
  FCX Mode: true

# Set to true if you want CLASSIC to remove some unnecessary lines and redundant information from your crash log files.
# CAUTION: Changes will be permanent for each crash log you scan after. May hide info useful for debugger programs.
  Simplify Logs: false

# Set to true if you want CLASSIC to show extra stats about scanned logs in the command line / terminal window.
# NOTICE: This setting currently has no effect, crash log stats will be fully implemented in a future update.
  Show Statistics: false

# Set to true if you want CLASSIC to look up FormID values (names) automatically while scanning crash logs.
# This will show some extra details for Possible FormID Suspects at the expense of longer scanning times.
  Show FormID Values: false

# Set to true if you want CLASSIC to move all unsolved crash logs and their autoscans to CLASSIC UNSOLVED folder.
# Unsolved logs are all crash logs that are incomplete or in the wrong format.
  Move Unsolved Logs: true

# Copy-paste your INI folder path below, where your main game INI files are located (Documents\My Games\*game*)
# If you are using MO2, I recommend disabling Profile Specific Game INI Files, located in Tools > Profiles
# This is only required if CLASSIC has problems detecting your game files or is scanning the wrong game.
  INI Folder Path:

# Copy-paste your staging mods folder path below. (Folder where your mod manager keeps all extracted mod files).
# MO2 Ex. MODS Folder Path: C:\Mod Organizer 2\*game*\mods | Vortex Ex. MODS Folder Path: C:\Vortex Mods\*game*
# You can also set this path to your game's Data folder, but then the scan results will be much less accurate.
  MODS Folder Path:

# Copy-paste your custom crash logs folder path below. Ex. SCAN Custom Path: C:\My Crash Logs
# Crash logs are generated in Documents\My Games\*game*\XSE folder by default. If no path is set,
# crash logs from that Scrip Extender folder and where the CLASSIC.exe is located will be scanned.
  SCAN Custom Path:

# Toggle audio notifications for when CLASSIC finishes scanning your crash logs and mod files.
  Audio Notifications: true

# Set the source where CLASSIC will check for updates. (Nexus | GitHub)
  Update Source: Both

# Enable or disable the use of an asynchronous pipeline for processing. This setting should not be changed and is primarily for testing purposes.
# If you are not a developer or do not know what this means, leave it as is.
  Use Async Pipeline: true

# Set to true if you want CLASSIC to disable progress bars when running in command line mode.
# This can be useful for cleaner output when running CLASSIC in scripts or automated environments.
  Disable CLI Progress: false"""
            if key_path == "Crashlog_Error_Check":
                return {"HIGH | Test Error": "error_signal"}
            if key_path == "Crashlog_Stack_Check":
                return {"MEDIUM | Stack Error": ["required:signal1", "optional:signal2"]}
            if isinstance(yaml_store, YAML) and yaml_store == YAML.Game and "Mods_" in key_path:
                return {"test_mod": "Test mod warning message"}
            return None

        mock_yaml.side_effect = side_effect
        yield mock_yaml


@pytest.fixture
def temp_game_installation(tmp_path: Path) -> Path:
    """Fixture to create a temporary game installation directory structure."""
    game_dir = tmp_path / "Fallout4"
    game_dir.mkdir()

    # Create essential game directories
    (game_dir / "Data").mkdir()
    (game_dir / "Data" / "Scripts").mkdir()
    (game_dir / "Data" / "Meshes").mkdir()
    (game_dir / "Data" / "Textures").mkdir()

    # Create game executable
    (game_dir / "Fallout4.exe").write_text("# Fake game executable")

    # Create essential game files
    (game_dir / "Data" / "Fallout4.esm").write_text("# Master file")
    (game_dir / "Data" / "DLCRobot.esm").write_text("# DLC file")
    (game_dir / "Data" / "DLCCoast.esm").write_text("# DLC file")

    # Create some plugin files
    (game_dir / "Data" / "TestMod.esp").write_text("# Test mod")
    (game_dir / "Data" / "AnotherMod.esp").write_text("# Another test mod")

    return game_dir


@pytest.fixture
def mock_registry_entries() -> Generator[Dict[str, Dict[str, str]], None, None]:
    """Mock Windows registry entries for game path detection."""
    mock_entries = {
        r"SOFTWARE\Bethesda Softworks\Fallout4": {"installed path": r"C:\Program Files (x86)\Steam\steamapps\common\Fallout 4"},
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 377160": {
            "InstallLocation": r"C:\Program Files (x86)\Steam\steamapps\common\Fallout 4"
        },
    }

    with patch("winreg.OpenKey"), patch("winreg.QueryValueEx") as mock_query:

        def query_side_effect(key, value_name):
            # This is a simplified mock - in real usage you'd need more sophisticated mocking
            for reg_path, values in mock_entries.items():
                if value_name in values:
                    return values[value_name], 1  # REG_SZ type
            raise FileNotFoundError()

        mock_query.side_effect = query_side_effect

        yield mock_entries


@pytest.fixture
def sample_ini_files(tmp_path: Path) -> Path:
    """Create sample INI files for testing."""
    ini_dir = tmp_path / "My Games" / "Fallout4"
    ini_dir.mkdir(parents=True)

    # Create Fallout4.ini
    fallout4_ini = ini_dir / "Fallout4.ini"
    fallout4_ini.write_text("""[Archive]
bInvalidateOlderFiles=1
sResourceDataDirsFinal=

[Display]
iSize H=1080
iSize W=1920
bFull Screen=1

[General]
sLanguage=ENGLISH
uExteriorCellBuffer=36

[Launcher]
bEnableFileSelection=1
""")

    # Create Fallout4Prefs.ini
    prefs_ini = ini_dir / "Fallout4Prefs.ini"
    prefs_ini.write_text("""[Display]
bMaximizeWindow=0
bBorderless=1
bFull Screen=0
iSize H=1080
iSize W=1920

[Imagespace]
bDoDepthOfField=1

[Launcher]
uLastAspectRatio=1
""")

    # Create Fallout4Custom.ini
    custom_ini = ini_dir / "Fallout4Custom.ini"
    custom_ini.write_text("""[Archive]
bInvalidateOlderFiles=1

[Display]
sAntiAliasing=TAA

[General]
bModManagerMenuEnabled=1
""")

    return ini_dir


@pytest.fixture
def mock_network_responses() -> Generator[Dict[str, Any], None, None]:
    """Mock network responses for testing external integrations."""

    with patch("requests.get") as mock_get, patch("requests.post") as mock_post, patch("urllib.request.urlopen") as mock_urlopen:
        # Configure mock GET responses
        def get_side_effect(url, **kwargs):
            mock_response = MagicMock()

            if "pastebin.com" in url:
                mock_response.text = """# Sample crash log from pastebin
Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512
"""
                mock_response.status_code = 200

            elif "api.github.com" in url:
                mock_response.json.return_value = {
                    "tag_name": "v7.31.0",
                    "assets": [{"browser_download_url": "https://github.com/test/download.zip"}],
                }
                mock_response.status_code = 200

            else:
                mock_response.status_code = 404

            return mock_response

        mock_get.side_effect = get_side_effect

        # Configure mock POST responses
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"success": True}

        # Configure urlopen for older URL handling
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"Sample crash log content"

        yield {"get": mock_get, "post": mock_post, "urlopen": mock_urlopen}


@pytest.fixture
def setup_global_registry() -> Generator[None, None, None]:
    """Initialize GlobalRegistry with required components for testing."""
    # Initialize YAML cache
    yaml_cache = YamlSettingsCache()
    GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, yaml_cache)

    # Set common registry values
    GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
    GlobalRegistry.register(GlobalRegistry.Keys.VR, "")
    GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)

    yield

    # Clear registry after test
    GlobalRegistry._registry.clear()
