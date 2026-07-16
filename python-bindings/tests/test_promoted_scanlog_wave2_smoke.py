"""Per-class smoke tests for Phase 3 Plan 03 - scanlog Wave 2
(detection and analysis).

Covers the independently useful mod detection, suspect scanning, settings
validation, run-result configuration issue, and GPU detection surfaces.

Each ``#[pyclass]`` gets at least one test that constructs it and
calls one real method (per Phase 3 D-07). Related free functions are
grouped into one test each. Constructor signatures were verified in
``.planning/phases/03-python-tier-collapse/03-03-CONSTRUCTOR-INVENTORY.md``.

Process-global FCX controls are intentionally absent; FCX setup data is
observed only through the final Crash Log Scan Run result.
"""

from __future__ import annotations

import pytest

import classic_scanlog

# =============================================================================
# mod_detector sub-module (grouped free functions)
# =============================================================================


def test_detect_mods_single_empty_returns_list() -> None:
    """``detect_mods_single({}, {})`` returns an empty ``list[str]``."""
    result = classic_scanlog.detect_mods_single({}, {})
    assert isinstance(result, list)
    assert result == []


def test_detect_mods_double_empty_returns_list() -> None:
    """``detect_mods_double([], {})`` returns an empty ``list[str]``."""
    result = classic_scanlog.detect_mods_double([], {})
    assert isinstance(result, list)
    assert result == []


def test_detect_mods_important_empty_returns_list() -> None:
    """``detect_mods_important([], {})`` returns an empty ``list[str]``."""
    result = classic_scanlog.detect_mods_important([], {})
    assert isinstance(result, list)
    assert result == []


def test_detect_mods_batch_empty_returns_list_of_lists() -> None:
    """``detect_mods_batch({}, [{}, {}])`` returns one sub-list per plugin dict."""
    result = classic_scanlog.detect_mods_batch({}, [{}, {}])
    assert isinstance(result, list)
    assert len(result) == 2
    for sub in result:
        assert isinstance(sub, list)


# =============================================================================
# suspect_scanner sub-module: SuspectScanner
# =============================================================================


def test_suspect_scanner_construct_empty_rules() -> None:
    """``SuspectScanner([], [])`` constructs with zero error and zero stack rules."""
    scanner = classic_scanlog.SuspectScanner([], [])
    assert scanner is not None


def test_suspect_scanner_scan_mainerror_empty() -> None:
    """``suspect_scan_mainerror("", 100)`` returns ``(list, bool)`` tuple."""
    scanner = classic_scanlog.SuspectScanner([], [])
    result = scanner.suspect_scan_mainerror("", 100)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], list)
    assert isinstance(result[1], bool)
    assert result[1] is False  # no rules => no suspects found


def test_suspect_scanner_scan_stack_empty() -> None:
    """``suspect_scan_stack("", "", 100)`` returns ``(list, bool)`` tuple."""
    scanner = classic_scanlog.SuspectScanner([], [])
    result = scanner.suspect_scan_stack("", "", 100)
    assert isinstance(result, tuple)
    assert isinstance(result[0], list)
    assert isinstance(result[1], bool)


def test_suspect_scanner_batch_empty() -> None:
    """``scan_suspects_batch([], 100)`` returns an empty list."""
    scanner = classic_scanlog.SuspectScanner([], [])
    result = scanner.scan_suspects_batch([], 100)
    assert isinstance(result, list)
    assert result == []


def test_suspect_scanner_check_dll_crash_static() -> None:
    """``SuspectScanner.check_dll_crash("")`` returns a list (static method)."""
    result = classic_scanlog.SuspectScanner.check_dll_crash("")
    assert isinstance(result, list)


# =============================================================================
# settings_validator sub-module: SettingsValidator
# =============================================================================


def test_settings_validator_construct_minimal() -> None:
    """``SettingsValidator("Buffout 4", {})`` constructs with an empty entry."""
    validator = classic_scanlog.SettingsValidator("Buffout 4", {})
    assert validator is not None


def test_settings_validator_scan_all_settings_empty() -> None:
    """``scan_all_settings({}, set())`` returns a ``list[list[str]]``."""
    validator = classic_scanlog.SettingsValidator("Buffout 4", {})
    result = validator.scan_all_settings({}, set())
    assert isinstance(result, list)
    # Each fragment is itself a list
    for frag in result:
        assert isinstance(frag, list)


def test_settings_validator_scan_all_settings_includes_disabled_notices() -> None:
    """``scan_all_settings`` includes universal disabled-setting notices."""
    validator = classic_scanlog.SettingsValidator("Buffout 4", {})
    result = validator.scan_all_settings({"Compatibility": {"SomeSetting": "false"}}, set())
    assert isinstance(result, list)
    assert any("SomeSetting is disabled" in line for fragment in result for line in fragment)


def test_settings_validator_scan_all_settings_rejects_flat_settings() -> None:
    """``scan_all_settings`` rejects the obsolete flat settings shape."""
    validator = classic_scanlog.SettingsValidator("Buffout 4", {})
    with pytest.raises(TypeError):
        validator.scan_all_settings({"SomeSetting": "false"}, set())


def test_settings_validator_scan_all_settings_uses_target_section() -> None:
    """``scan_all_settings`` evaluates rules against the targeted settings section."""
    validator = classic_scanlog.SettingsValidator(
        "Buffout 4",
        {
            "display_section": "[Compatibility]",
            "ignore_keys": [],
            "settings_rules": {
                "checks": [
                    {
                        "id": "patches_achievements",
                        "target": {
                            "section": "Patches",
                            "key": "Achievements",
                            "type": "bool",
                        },
                        "expect": {"equals": False},
                        "messages": {
                            "fail": "Patches Achievements failed",
                            "pass": "Patches Achievements passed",
                        },
                    }
                ]
            },
        },
    )

    result = validator.scan_all_settings(
        {
            "Compatibility": {"Achievements": "true"},
            "Patches": {"Achievements": "false"},
        },
        set(),
    )

    assert any(
        "Patches Achievements passed" in line for fragment in result for line in fragment
    )


def test_settings_validator_check_disabled_settings_empty() -> None:
    """``check_disabled_settings({})`` returns a list."""
    validator = classic_scanlog.SettingsValidator("Buffout 4", {})
    result = validator.check_disabled_settings({})
    assert isinstance(result, list)


def test_settings_validator_check_disabled_settings_rejects_flat_settings() -> None:
    """``check_disabled_settings`` rejects the obsolete flat settings shape."""
    validator = classic_scanlog.SettingsValidator("Buffout 4", {})
    with pytest.raises(TypeError):
        validator.check_disabled_settings({"SomeSetting": "false"})


# =============================================================================
# Run-scoped FCX result data: ConfigIssue
# =============================================================================


def test_config_issue_construct_and_field_access() -> None:
    """``ConfigIssue(...)`` exposes its getters."""
    issue = classic_scanlog.ConfigIssue(
        "/tmp/fake.ini",
        "General",
        "iSetting",
        "0",
        "1",
        "description goes here",
        "warning",
    )
    assert issue.file_path == "/tmp/fake.ini"
    assert issue.section == "General"
    assert issue.setting == "iSetting"
    assert issue.current_value == "0"
    assert issue.recommended_value == "1"
    assert issue.description == "description goes here"
    assert issue.severity == "warning"


def test_config_issue_format_report_returns_string() -> None:
    """``ConfigIssue.format_report()`` returns a non-empty markdown string."""
    issue = classic_scanlog.ConfigIssue(
        "/tmp/fake.ini", None, "s", "c", "r", "d",
    )
    report = issue.format_report()
    assert isinstance(report, str)


def test_config_issue_section_none_allowed() -> None:
    """``ConfigIssue`` accepts ``section=None`` for TOML-style files."""
    issue = classic_scanlog.ConfigIssue(
        "/tmp/fake.toml", None, "key", "0", "1", "desc",
    )
    assert issue.section is None


# =============================================================================
# gpu_detector sub-module: GpuDetector + GpuInfo + GpuVendor
# =============================================================================


def test_gpu_detector_construct_default() -> None:
    """``GpuDetector()`` constructs with no arguments."""
    detector = classic_scanlog.GpuDetector()
    assert detector is not None


def test_gpu_detector_extract_gpu_info_empty_returns_gpu_info() -> None:
    """``extract_gpu_info([])`` returns an empty-state ``GpuInfo`` instance."""
    detector = classic_scanlog.GpuDetector()
    info = detector.extract_gpu_info([])
    assert info is not None
    # Field access should work even on empty input
    assert isinstance(info.primary, str)


def test_gpu_detector_extract_gpu_info_batch_empty() -> None:
    """``extract_gpu_info_batch([])`` returns an empty list."""
    detector = classic_scanlog.GpuDetector()
    results = detector.extract_gpu_info_batch([])
    assert isinstance(results, list)
    assert results == []


def test_gpu_detector_extract_gpu_info_batch_multi() -> None:
    """``extract_gpu_info_batch([[], []])`` returns one GpuInfo per segment."""
    detector = classic_scanlog.GpuDetector()
    results = detector.extract_gpu_info_batch([[], []])
    assert len(results) == 2


def test_gpu_info_construct_default() -> None:
    """``GpuInfo()`` constructs an empty instance."""
    info = classic_scanlog.GpuInfo()
    assert info is not None


def test_gpu_info_field_getters() -> None:
    """``GpuInfo`` primary/secondary/manufacturer/rival getters return strings or None."""
    info = classic_scanlog.GpuInfo()
    assert isinstance(info.primary, str)
    assert info.secondary is None or isinstance(info.secondary, str)
    assert isinstance(info.manufacturer, str)
    assert info.rival is None or isinstance(info.rival, str)


def test_gpu_info_to_dict_returns_dict() -> None:
    """``GpuInfo.to_dict()`` returns a dict representation."""
    info = classic_scanlog.GpuInfo()
    d = info.to_dict()
    assert isinstance(d, dict)


def test_gpu_vendor_construct_amd() -> None:
    """``GpuVendor("AMD")`` constructs the AMD variant.

    The Python wrapper is a ``#[pyclass]``, not a true Python enum, so
    the constructor takes a vendor-name string and there are no
    class-level ``NVIDIA``/``AMD``/``INTEL`` attributes. Verified from
    ``classic-scanlog-py/src/gpu_detector.rs``.
    """
    vendor = classic_scanlog.GpuVendor("AMD")
    assert vendor is not None


def test_gpu_vendor_construct_nvidia_intel_unknown() -> None:
    """``GpuVendor`` accepts case-insensitive vendor-name strings."""
    classic_scanlog.GpuVendor("NVIDIA")
    classic_scanlog.GpuVendor("INTEL")
    classic_scanlog.GpuVendor("something-else")  # falls through to Unknown
