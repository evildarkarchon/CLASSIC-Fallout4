"""Per-class smoke tests for Phase 3 Plan 03 - scanlog Wave 2
(detection and analysis).

Covers 57 promoted contract rows across 5 scanlog sub-modules:
mod_detector, suspect_scanner, settings_validator, fcx_handler,
gpu_detector. Per R9, ``GLOBAL_FCX_HANDLER`` is excluded from tier1
promotion because ``LazyLock`` statics are not first-class Python
module attributes.

Each ``#[pyclass]`` gets at least one test that constructs it and
calls one real method (per Phase 3 D-07). Related free functions are
grouped into one test each. Constructor signatures were verified in
``.planning/phases/03-python-tier-collapse/03-03-CONSTRUCTOR-INVENTORY.md``.

The autouse FCX reset fixture lives in ``conftest.py`` and keeps
the ``GLOBAL_FCX_HANDLER`` singleton clean between tests so stateful
``FcxModeHandler`` tests do not pollute each other.
"""

from __future__ import annotations

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
    result = validator.scan_all_settings({"SomeSetting": "false"}, set())
    assert isinstance(result, list)
    assert any("SomeSetting is disabled" in line for fragment in result for line in fragment)


def test_settings_validator_check_disabled_settings_empty() -> None:
    """``check_disabled_settings({})`` returns a list."""
    validator = classic_scanlog.SettingsValidator("Buffout 4", {})
    result = validator.check_disabled_settings({})
    assert isinstance(result, list)


# =============================================================================
# fcx_handler sub-module: FcxModeHandler + ConfigIssue + FcxResetError
# =============================================================================


def test_fcx_mode_handler_construct_disabled() -> None:
    """``FcxModeHandler(False)`` constructs in disabled mode."""
    handler = classic_scanlog.FcxModeHandler(False)
    assert handler is not None
    assert handler.fcx_mode is False


def test_fcx_mode_handler_get_fcx_messages_empty() -> None:
    """``get_fcx_messages()`` returns a list for a disabled handler."""
    handler = classic_scanlog.FcxModeHandler(False)
    msgs = handler.get_fcx_messages()
    assert isinstance(msgs, list)


def test_fcx_mode_handler_get_status_message() -> None:
    """``get_fcx_status_message()`` returns a string."""
    handler = classic_scanlog.FcxModeHandler(False)
    status = handler.get_fcx_status_message()
    assert isinstance(status, str)


def test_fcx_mode_handler_has_results_initial_false() -> None:
    """A freshly-constructed disabled handler has no results."""
    handler = classic_scanlog.FcxModeHandler(False)
    assert handler.has_results() is False


def test_fcx_mode_handler_set_main_files_result_marks_results() -> None:
    """``set_main_files_result("foo")`` flips ``has_results()`` to ``True``.

    ``has_results()`` is gated on ``fcx_mode`` being enabled in
    ``classic-scanlog-core/src/fcx_handler.rs:267-279``; construct with
    ``FcxModeHandler(True)`` so the positive path is observable.
    """
    handler = classic_scanlog.FcxModeHandler(True)
    handler.set_main_files_result("foo")
    assert handler.has_results() is True


def test_fcx_mode_handler_set_game_files_result_roundtrip() -> None:
    """``set_game_files_result("bar")`` is accepted without raising."""
    handler = classic_scanlog.FcxModeHandler(True)
    handler.set_game_files_result("bar")
    assert handler.has_results() is True


def test_fcx_mode_handler_reset_clears_results() -> None:
    """``reset()`` clears previously-set results."""
    handler = classic_scanlog.FcxModeHandler(True)
    handler.set_main_files_result("foo")
    assert handler.has_results() is True
    handler.reset()
    assert handler.has_results() is False


def test_fcx_mode_handler_get_detected_issues_initial_empty() -> None:
    """A fresh handler has no detected issues."""
    handler = classic_scanlog.FcxModeHandler(False)
    issues = handler.get_detected_issues()
    assert isinstance(issues, list)
    assert issues == []


def test_fcx_mode_handler_add_issue_and_roundtrip() -> None:
    """``add_issue(ConfigIssue(...))`` and ``get_detected_issues()`` round-trip."""
    handler = classic_scanlog.FcxModeHandler(False)
    issue = classic_scanlog.ConfigIssue(
        "/tmp/fake.ini",
        "General",
        "iFOO",
        "0",
        "1",
        "test desc",
    )
    handler.add_issue(issue)
    issues = handler.get_detected_issues()
    assert len(issues) == 1
    assert issues[0].setting == "iFOO"


def test_fcx_mode_handler_set_detected_issues_replaces() -> None:
    """``set_detected_issues([])`` replaces the existing list with an empty one."""
    handler = classic_scanlog.FcxModeHandler(False)
    issue = classic_scanlog.ConfigIssue(
        "/tmp/x.ini", None, "s", "c", "r", "d",
    )
    handler.set_detected_issues([issue])
    assert len(handler.get_detected_issues()) == 1
    handler.set_detected_issues([])
    assert handler.get_detected_issues() == []


def test_fcx_mode_handler_reset_fcx_checks_classmethod_noop() -> None:
    """``FcxModeHandler.reset_fcx_checks()`` is a benign no-op when clean.

    Plan 03 Task 1 rewired this classmethod to raise :class:`FcxResetError`
    for non-``Unnecessary`` failures. When the global handler is already
    clean it still treats the call as success (``Unnecessary`` is suppressed).
    """
    # Should not raise on a freshly-reset singleton (the autouse fixture
    # resets it before each test).
    classic_scanlog.FcxModeHandler.reset_fcx_checks()


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


def test_fcx_reset_error_is_exception_subclass() -> None:
    """``classic_scanlog.FcxResetError`` is an ``Exception`` subclass."""
    assert issubclass(classic_scanlog.FcxResetError, Exception)
    # Can be raised and caught like any exception
    try:
        raise classic_scanlog.FcxResetError("test message")
    except classic_scanlog.FcxResetError as err:
        assert "test message" in str(err)


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
