"""
Shared fixtures for mod detection and analysis tests.
"""


import pytest
from ClassicLib.ScanLog.fragments import ReportFragment


@pytest.fixture
def empty_fragment() -> ReportFragment:
    """Create an empty ReportFragment for testing."""
    return ReportFragment()


@pytest.fixture
def sample_yaml_dict() -> dict[str, str]:
    """Create a sample YAML dictionary for mod testing."""
    return {
        "mod1": "Warning for mod1",
        "mod2": "Warning for mod2",
        "mod3": "Warning for mod3",
    }


@pytest.fixture
def sample_conflict_dict() -> dict[str, str]:
    """Create a sample conflict dictionary for testing."""
    return {
        "mod1 | mod2": "These mods conflict with each other",
        "mod3 | mod4": "Another conflict warning",
    }


@pytest.fixture
def sample_important_dict() -> dict[str, str]:
    """Create a sample important mods dictionary for testing."""
    return {
        "important_mod | Important Mod": "This is an important mod for performance",
        "nvidia_mod | NVIDIA Mod": "This mod requires an nvidia GPU",
        "amd_mod | AMD Mod": "This mod requires an amd GPU",
    }


@pytest.fixture
def sample_crashlog_plugins() -> dict[str, str]:
    """Create a sample crashlog plugins dictionary."""
    return {
        "mod1_plugin.esp": "00",
        "mod2_plugin.esp": "01",
        "unrelated_plugin.esp": "02",
        "another_plugin.esp": "03",
    }


@pytest.fixture
def empty_crashlog_plugins() -> dict[str, str]:
    """Create an empty crashlog plugins dictionary."""
    return {}
