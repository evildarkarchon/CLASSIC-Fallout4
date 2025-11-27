"""Data fixtures for sample files and test data."""

from collections.abc import Callable
from pathlib import Path

import pytest

# Cache for test file generation to avoid repeated I/O
_test_file_cache = {}


@pytest.fixture(scope="session")
def cached_test_files(tmp_path_factory) -> dict[str, Path]:
    """Generate and cache common test files to avoid repeated I/O operations.

    IMPORTANT: These files are cached across the entire test session and shared
    between parallel test workers. Tests MUST treat these files as READ-ONLY.

    Do NOT modify, write to, or delete these cached files during tests.
    If a test needs to modify files, use the tmp_path fixture instead to get
    a unique temporary directory for that specific test.

    Returns:
        dict[str, Path]: Dictionary containing paths to cached test files:
            - crash_log: Path to a sample crash log file
            - crash_log_dir: Directory containing crash logs
            - yaml_settings: Path to a sample YAML settings file
            - yaml_dir: Directory containing YAML files
    """
    global _test_file_cache

    if not _test_file_cache:
        tmp_path = tmp_path_factory.mktemp("cached_test_files")

        # Create cached crash log
        crash_log_dir = tmp_path / "cached_crash_logs"
        crash_log_dir.mkdir()

        crash_log_file = crash_log_dir / "cached_crash.log"
        crash_log_file.write_text("""Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] TestMod.esp
""")

        # Create cached YAML file
        yaml_dir = tmp_path / "cached_yaml"
        yaml_dir.mkdir()

        yaml_file = yaml_dir / "cached_settings.yaml"
        yaml_file.write_text("""CLASSIC_Settings:
  Managed Game: Fallout4
  VR Mode: false
  FCX Mode: true
  Update Check: true
""")

        _test_file_cache = {
            "crash_log": crash_log_file,
            "crash_log_dir": crash_log_dir,
            "yaml_settings": yaml_file,
            "yaml_dir": yaml_dir,
        }

    return _test_file_cache


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


@pytest.fixture(scope="session")
def temp_game_installation(tmp_path_factory) -> Path:
    """Fixture to create a temporary game installation directory structure."""
    tmp_path = tmp_path_factory.mktemp("game_install")
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


@pytest.fixture(scope="session")
def sample_ini_files(tmp_path_factory) -> Path:
    """Create sample INI files for testing."""
    tmp_path = tmp_path_factory.mktemp("ini_files")
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
