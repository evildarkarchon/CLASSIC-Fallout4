"""Crash log test fixtures.

This module provides all crash log-related fixtures with clear naming:
- `crash_log_*` for file-based fixtures
- `sample_*_content` for string content

All crash log fixtures are consolidated here for consistency.
"""

from pathlib import Path

import pytest

# ============================================================================
# Crash Log Content Constants
# ============================================================================

STANDARD_CRASH_LOG = """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512|nvwgf2umx.dll+00FF1234

\t[Compatibility]
\tAchievements: true
\tMemoryManager: false
\tF4EE: false
\tActorIsHostileToActor: true
\tBSTextureStreamerLocalHeap: true
\tHavokMemorySystem: true
\tSmallBlockAllocator: false
\tScaleformAllocator: true
\tMaxStdIO: 8192
\tWorkshopMenu: true
\tLoadScreenFix: true

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]
\tGPU #2: AMD RX 6800
\tPHYSICAL MEMORY: 32.0 GB

PROBABLE CALL STACK:
\t[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> TESForm::SetReference+0x12
\t[ 1] 0x7FF6EF4C3600 Fallout4.exe+0733600 -> BGSInventoryItem::GetOwner+0x30
\t[ 2] 0x7FFB12340000 nvwgf2umx.dll+00FF1234 -> ?
\t[ 3] 0x7FF6EF500000 Fallout4.exe+0800000 -> BSResource::LoaderThread::Run+0x100
\t[ 4] 0x7FFB23450000 kernel32.dll+0001000 -> BaseThreadInitThunk
\t[ 5] 0x7FFB34560000 ntdll.dll+00023000 -> RtlUserThreadStart

MODULES:
\tFallout4.exe v1.10.163.0
\tnvwgf2umx.dll v31.0.15.3713
\tkernel32.dll v10.0.22621.1
\tntdll.dll v10.0.22621.1
\tbuffer_allocator.dll v1.28.6
\tAchievements.dll v2.3.0
\tBakaScrapHeap.dll v1.1.0
\tLooksMenu.dll v1.6.23

F4SE PLUGINS:
\tAchievements.dll v2.3.0
\tBakaScrapHeap.dll v1.1.0
\tLooksMenu.dll v1.6.23
\tbuffer_allocator.dll v1.28.6
\tHighFPSPhysicsFix.dll v0.8.6
\tTestPlugin.dll v1.0.0

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] DLCworkshop01.esm
\t[03] DLCCoast.esm
\t[04] DLCworkshop02.esm
\t[05] DLCworkshop03.esm
\t[06] DLCNukaWorld.esm
\t[FE:000] ccBGSFO4001-PipBoy(Black).esl
\t[FE:001] TestMod.esl
\t[07] Unofficial Fallout 4 Patch.esp
\t[08] ArmorKeywords.esm
\t[09] ProblemPlugin.esp
\t[0A] AnotherMod.esp
"""

MINIMAL_CRASH_LOG = """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

\t[Compatibility]
\tAchievements: true

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro

PROBABLE CALL STACK:
\t[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512

MODULES:
\tFallout4.exe v1.10.163.0

F4SE PLUGINS:
\tAchievements.dll v2.3.0

PLUGINS:
\t[00] Fallout4.esm
"""

MALFORMED_CRASH_LOG = """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro

"""

SMALL_CRASH_LOG_WITH_FORMIDS = """
Buffout 4 Crash Log
EXCEPTION_ACCESS_VIOLATION (0xc0000005)
Unhandled exception at 0x7FF6DEADBEEF

PROBABLE CALL STACK:
[0] 0x7FF6DEADBEEF    FormID: 0x00012345    TestMod.esp
[1] 0x7FF6CAFEBABE    FormID: 0x00023456    Fallout4.esm
[2] 0x7FF6BADF00D5    FormID: 0x00034567    DLCCoast.esm

PLUGINS:
[FE:000] ccBGSFO4001-PipBoy(Camo01).esl
[FE:001] ccBGSFO4003-PipBoy(Camo02).esl
[00] Fallout4.esm
[01] DLCRobot.esm
[02] DLCworkshop01.esm
[03] DLCCoast.esm
[04] TestMod.esp
"""


# ============================================================================
# Content Fixtures
# ============================================================================


@pytest.fixture
def sample_crash_log_content() -> str:
    """Provide a realistic crash log content string for testing.

    Returns:
        str: Complete crash log content with all standard sections.
    """
    return STANDARD_CRASH_LOG


@pytest.fixture
def sample_crash_log_lines(sample_crash_log_content: str) -> list[str]:
    """Provide crash log content as list of lines.

    Args:
        sample_crash_log_content: The full crash log content string.

    Returns:
        list[str]: List of individual lines from the crash log.
    """
    return sample_crash_log_content.splitlines()


@pytest.fixture
def sample_crash_log_minimal() -> str:
    """Provide a minimal valid crash log for edge case testing.

    Returns:
        str: Minimal crash log with only essential sections.
    """
    return MINIMAL_CRASH_LOG


@pytest.fixture
def minimal_crash_log_content() -> str:
    """Alias for sample_crash_log_minimal for compatibility.

    Returns:
        str: Minimal crash log with only essential sections.
    """
    return MINIMAL_CRASH_LOG


@pytest.fixture
def sample_crash_log_malformed() -> str:
    """Provide a malformed crash log for error handling tests.

    Returns:
        str: Incomplete crash log content missing standard sections.
    """
    return MALFORMED_CRASH_LOG


@pytest.fixture
def malformed_crash_log_content() -> str:
    """Alias for sample_crash_log_malformed for compatibility.

    Returns:
        str: Incomplete crash log content missing standard sections.
    """
    return MALFORMED_CRASH_LOG


@pytest.fixture
def crash_log_with_formids() -> str:
    """Provide a crash log with FormID entries for FormID testing.

    Returns:
        str: Crash log with FormID entries in call stack.
    """
    return SMALL_CRASH_LOG_WITH_FORMIDS


# ============================================================================
# File Fixtures
# ============================================================================


@pytest.fixture
def crash_log_file(tmp_path: Path, sample_crash_log_content: str) -> Path:
    """Create a temporary crash log file for testing.

    Args:
        tmp_path: Pytest temporary directory fixture.
        sample_crash_log_content: The crash log content to write.

    Returns:
        Path: Path to the created crash log file.
    """
    crash_log = tmp_path / "crash-2024-01-15-12-30-45.log"
    crash_log.write_text(sample_crash_log_content, encoding="utf-8")
    return crash_log


@pytest.fixture
def malformed_crash_log_file(tmp_path: Path, malformed_crash_log_content: str) -> Path:
    """Create a temporary malformed crash log file for error handling tests.

    Args:
        tmp_path: Pytest temporary directory fixture.
        malformed_crash_log_content: The malformed crash log content.

    Returns:
        Path: Path to the created malformed crash log file.
    """
    crash_log = tmp_path / "crash-malformed.log"
    crash_log.write_text(malformed_crash_log_content, encoding="utf-8")
    return crash_log


@pytest.fixture
def crash_log_directory(tmp_path: Path, sample_crash_log_content: str) -> Path:
    """Create a temporary directory with multiple crash log files.

    Args:
        tmp_path: Pytest temporary directory fixture.
        sample_crash_log_content: Content to use for crash logs.

    Returns:
        Path: Path to the directory containing crash logs.
    """
    crash_dir = tmp_path / "Crash Logs"
    crash_dir.mkdir()

    # Create multiple crash logs with different timestamps
    for i, timestamp in enumerate(["2024-01-15-10-00-00", "2024-01-15-11-00-00", "2024-01-15-12-00-00"]):
        crash_file = crash_dir / f"crash-{timestamp}.log"
        # Vary content slightly for testing
        content = sample_crash_log_content.replace("0733512", f"073351{i}")
        crash_file.write_text(content, encoding="utf-8")

    return crash_dir


@pytest.fixture
def crash_logs_directory(tmp_path: Path, sample_crash_log_content: str) -> Path:
    """Alias for crash_log_directory for compatibility.

    Args:
        tmp_path: Pytest temporary directory fixture.
        sample_crash_log_content: Content to use for crash logs.

    Returns:
        Path: Path to the directory containing crash logs.
    """
    crash_dir = tmp_path / "Crash Logs"
    crash_dir.mkdir()

    for i, timestamp in enumerate(["2024-01-15-10-00-00", "2024-01-15-11-00-00", "2024-01-15-12-00-00"]):
        crash_file = crash_dir / f"crash-{timestamp}.log"
        content = sample_crash_log_content.replace("0733512", f"073351{i}")
        crash_file.write_text(content, encoding="utf-8")

    return crash_dir


@pytest.fixture
def sample_crash_logs(tmp_path: Path) -> list[Path]:
    """Create sample crash log files for testing with realistic content.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        list[Path]: List of paths to created crash log files.
    """
    crash_logs = []

    sample_content = b"""Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF7D5058F6A Fallout4.exe+1AF8F6A

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AuthenticAMD AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]
\tPHYSICAL MEMORY: 15.62 GB/63.15 GB

PROBABLE CALL STACK:
\t[0] 0x7FF7D5058F6A Fallout4.exe+1AF8F6A
\t[1] 0x7FF7D4058F6B Fallout4.exe+0AF8F6B

REGISTERS:
\tRAX 0x0
\tRCX 0x0
"""

    for i in range(5):
        log_file = tmp_path / f"crash-2023-09-15-0{i}.log"
        log_file.write_bytes(sample_content)
        crash_logs.append(log_file)
    return crash_logs


@pytest.fixture
def crash_log_files(tmp_path: Path) -> list[Path]:
    """Create test crash log files for batch processing tests.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        list[Path]: List of paths to created crash log files.
    """
    crash_logs = []
    for i in range(3):
        log_file = tmp_path / f"crash_{i}.log"
        log_file.write_text("Test crash log content")
        crash_logs.append(log_file)
    return crash_logs


@pytest.fixture
def crash_log_samples(tmp_path: Path) -> dict[str, Path]:
    """Create sample crash logs of various sizes for testing.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        dict[str, Path]: Dictionary mapping size name to crash log path.
    """
    samples = {}

    # Small sample - basic crash with FormID
    small_log = tmp_path / "small.log"
    small_log.write_text(SMALL_CRASH_LOG_WITH_FORMIDS)
    samples["small"] = small_log

    # Medium sample - more complex crash
    medium_log = tmp_path / "medium.log"
    medium_content = """
Buffout 4 Crash Log

EXCEPTION_ACCESS_VIOLATION (0xc0000005)

SYSTEM SPECS:
OS: Windows 10
GPU: NVIDIA RTX 3080
RAM: 32GB

PROBABLE CALL STACK:
"""
    # Add many stack frames
    for i in range(100):
        medium_content += f"[{i}] 0x7FF6{i:08X}    FormID: 0x{i:08X}    TestMod{i % 5}.esp\n"

    medium_content += "\nPLUGINS:\n"
    for i in range(50):
        medium_content += f"[{i:02X}] Plugin_{i}.esm\n"

    medium_log.write_text(medium_content)
    samples["medium"] = medium_log

    # Large sample - stress test
    large_log = tmp_path / "large.log"
    large_content = "Buffout 4 Crash Log\n" + ("Line of log data\n" * 10000)
    large_log.write_text(large_content)
    samples["large"] = large_log

    return samples


# ============================================================================
# Parser Test Fixtures
# ============================================================================


@pytest.fixture
def segment_boundaries() -> list[tuple[str, str]]:
    """Provide standard segment boundaries for crash log parsing.

    Returns:
        list[tuple[str, str]]: List of (start_marker, end_marker) tuples.
    """
    return [
        ("\t[Compatibility]", "SYSTEM SPECS:"),
        ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
        ("PROBABLE CALL STACK:", "MODULES:"),
        ("MODULES:", "F4SE PLUGINS:"),
        ("F4SE PLUGINS:", "PLUGINS:"),
        ("PLUGINS:", "EOF"),
    ]


@pytest.fixture
def expected_segments() -> dict[str, list[str]]:
    """Provide expected parsed segments from sample crash log.

    Returns:
        dict[str, list[str]]: Dictionary mapping segment names to expected content.
    """
    return {
        "crashgen": [
            "Achievements: true",
            "MemoryManager: false",
            "F4EE: false",
        ],
        "system": [
            "OS: Microsoft Windows 11 Pro v10.0.22621",
            "CPU: AMD Ryzen 7 7800X3D 8-Core Processor",
            "GPU #1: Nvidia AD104 [GeForce RTX 4070]",
        ],
        "callstack": [
            "[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512",
        ],
        "plugins": [
            "[00] Fallout4.esm",
            "[01] DLCRobot.esm",
        ],
    }
