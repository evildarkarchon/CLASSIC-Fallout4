"""
Mod detection and analysis fixtures for CLASSIC-Fallout4 test suite.

This module provides fixtures for testing mod detection, conflict analysis,
and plugin list handling.

Consolidated from:
- tests/mods/conftest.py
"""

import pytest

from ClassicLib.ScanLog.fragments import ReportFragment


@pytest.fixture
def mods_empty_fragment() -> ReportFragment:
    """Create an empty ReportFragment for testing.

    Returns:
        An empty ReportFragment instance.
    """
    return ReportFragment.empty()


@pytest.fixture
def mods_sample_yaml_dict() -> dict[str, str]:
    """Create a sample YAML dictionary for mod testing.

    Returns:
        A dictionary mapping mod names to warning messages.
    """
    return {
        "mod1": "Warning for mod1",
        "mod2": "Warning for mod2",
        "mod3": "Warning for mod3",
    }


@pytest.fixture
def mods_sample_conflict_dict() -> dict[str, str]:
    """Create a sample conflict dictionary for testing.

    Returns:
        A dictionary mapping mod conflict pairs to conflict messages.
    """
    return {
        "mod1 | mod2": "These mods conflict with each other",
        "mod3 | mod4": "Another conflict warning",
    }


@pytest.fixture
def mods_sample_important_dict() -> dict[str, str]:
    """Create a sample important mods dictionary for testing.

    Returns:
        A dictionary mapping important mod identifiers to their descriptions.
    """
    return {
        "important_mod | Important Mod": "This is an important mod for performance",
        "nvidia_mod | NVIDIA Mod": "This mod requires an nvidia GPU",
        "amd_mod | AMD Mod": "This mod requires an amd GPU",
    }


@pytest.fixture
def mods_sample_crashlog_plugins() -> dict[str, str]:
    """Create a sample crashlog plugins dictionary.

    Returns:
        A dictionary mapping plugin filenames to load order indices.
    """
    return {
        "mod1_plugin.esp": "00",
        "mod2_plugin.esp": "01",
        "unrelated_plugin.esp": "02",
        "another_plugin.esp": "03",
    }


@pytest.fixture
def mods_empty_crashlog_plugins() -> dict[str, str]:
    """Create an empty crashlog plugins dictionary.

    Returns:
        An empty dictionary for testing edge cases.
    """
    return {}


# Backward compatibility aliases (deprecated - use prefixed names)
empty_fragment = mods_empty_fragment
sample_yaml_dict = mods_sample_yaml_dict
sample_conflict_dict = mods_sample_conflict_dict
sample_important_dict = mods_sample_important_dict
sample_crashlog_plugins = mods_sample_crashlog_plugins
empty_crashlog_plugins = mods_empty_crashlog_plugins
