"""Runtime contract tests for semantic Crashgen Settings Analysis."""

from concurrent.futures import ThreadPoolExecutor

import pytest

import classic_scanlog


def _entry(version: int = 1) -> dict[str, object]:
    return {
        "display_section": "[Compatibility]",
        "ignore_keys": ["IgnoredSetting"],
        "settings_rules": {
            "version": version,
            "preflight": [
                {
                    "id": "compatibility_notice",
                    "when": {"plugin_any": ["MixedCase.dll"]},
                    "action": {
                        "kind": "notice",
                        "placement": "error_information",
                        "severity": "warning",
                        "message": "Authored guidance for {crashgen_name}",
                        "fix": "Authored fix",
                    },
                }
            ],
        },
    }


def _analyze(
    analyzer: classic_scanlog.CrashgenSettingsAnalyzer,
) -> classic_scanlog.CrashgenSettingsAnalysisResult:
    input = classic_scanlog.CrashgenSettingsAnalysisInput(
        settings={
            "Compatibility": {
                "DisabledSetting": "false",
                "IgnoredSetting": "false",
            }
        },
        installed_plugins={"MIXEDCASE.DLL"},
        config_layout="og",
    )
    return analyzer.analyze(input)


def test_crashgen_analyzer_returns_typed_semantics_and_explicit_empty_result() -> None:
    analyzer = classic_scanlog.CrashgenSettingsAnalyzer("Buffout 4", _entry())

    result = _analyze(analyzer)

    assert analyzer.kind.code == "crashgen_settings"
    assert len(result.expectation_outcomes) == 1
    outcome = result.expectation_outcomes[0]
    assert outcome.rule_id == "compatibility_notice"
    assert outcome.kind.value == "notice"
    assert outcome.severity.value == "warning"
    assert outcome.message == "Authored guidance for Buffout 4"
    assert outcome.fix == "Authored fix"
    assert outcome.placement.value == "error_information"
    assert [notice.setting_name for notice in result.disabled_setting_notices] == [
        "DisabledSetting"
    ]
    with pytest.raises(AttributeError):
        result.expectation_outcomes = []

    empty = analyzer.analyze(classic_scanlog.CrashgenSettingsAnalysisInput({}, set()))
    assert empty.expectation_outcomes == []
    assert empty.disabled_setting_notices == []


def test_crashgen_analyzer_error_exposes_kind_code_and_message() -> None:
    with pytest.raises(classic_scanlog.AnalyzerError) as raised:
        classic_scanlog.CrashgenSettingsAnalyzer("Buffout 4", _entry(version=2))

    assert raised.value.analyzer_kind.code == "crashgen_settings"
    assert raised.value.code == "unsupported_configuration_version"
    assert raised.value.message == "unsupported Crashgen Expectations version 2"


def test_crashgen_analyzer_rejects_tolerantly_parsed_rule_diagnostics() -> None:
    entry = _entry()
    rules = entry["settings_rules"]
    assert isinstance(rules, dict)
    preflight = rules["preflight"]
    assert isinstance(preflight, list)
    preflight[0]["action"]["kind"] = "not_a_real_action"

    with pytest.raises(classic_scanlog.AnalyzerError) as raised:
        classic_scanlog.CrashgenSettingsAnalyzer("Buffout 4", entry)

    assert raised.value.code == "invalid_configuration"
    assert "configuration is invalid" in raised.value.message


def test_crashgen_analyzer_validates_sibling_rules_version_when_rules_omit_it() -> None:
    entry = _entry()
    rules = entry["settings_rules"]
    assert isinstance(rules, dict)
    del rules["version"]
    entry["settings_rules_version"] = 2

    with pytest.raises(classic_scanlog.AnalyzerError) as raised:
        classic_scanlog.CrashgenSettingsAnalyzer("Buffout 4", entry)

    assert raised.value.code == "unsupported_configuration_version"
    assert raised.value.message == "unsupported Crashgen Expectations version 2"


def test_crashgen_analyzer_handle_is_reusable_across_python_threads() -> None:
    analyzer = classic_scanlog.CrashgenSettingsAnalyzer("Buffout 4", _entry())

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: _analyze(analyzer), range(12)))

    assert all(len(result.expectation_outcomes) == 1 for result in results)
    assert all(len(result.disabled_setting_notices) == 1 for result in results)
