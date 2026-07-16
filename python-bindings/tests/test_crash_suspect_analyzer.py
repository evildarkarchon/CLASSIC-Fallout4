"""Runtime contract tests for semantic Crash Suspect analysis."""

from concurrent.futures import ThreadPoolExecutor

import pytest

import classic_scanlog


def _analyzer() -> classic_scanlog.CrashSuspectAnalyzer:
    return classic_scanlog.CrashSuspectAnalyzer(
        [
            classic_scanlog.CrashSuspectMainErrorRule(
                "main-rule", "Main Rule", 5, ["plugin.dll"]
            )
        ],
        [
            classic_scanlog.CrashSuspectStackRule(
                "stack-rule",
                "Stack Rule",
                4,
                [],
                [],
                ["StackSignal"],
                [],
                [],
            )
        ],
    )


def _analyze(
    analyzer: classic_scanlog.CrashSuspectAnalyzer,
    main_error: str = "plugin.dll",
) -> classic_scanlog.CrashSuspectAnalysisResult:
    return analyzer.analyze(
        classic_scanlog.CrashSuspectAnalysisInput(main_error, "StackSignal")
    )


def test_crash_suspect_analyzer_returns_individual_semantic_findings() -> None:
    analyzer = _analyzer()

    result = _analyze(analyzer)

    assert analyzer.kind.code == "crash_suspect"
    assert [finding.kind.value for finding in result.findings] == [
        "main_error_rule",
        "stack_rule",
        "dll_involvement",
    ]
    assert result.findings[0].rule_id == "main-rule"
    assert result.findings[0].name == "Main Rule"
    assert result.findings[0].severity == 5
    assert result.findings[2].rule_id is None
    assert result.findings[2].name is None
    assert result.findings[2].severity is None
    with pytest.raises(AttributeError):
        result.findings = []


def test_crash_suspect_analyzer_returns_explicit_empty_result() -> None:
    analyzer = classic_scanlog.CrashSuspectAnalyzer([], [])

    result = analyzer.analyze(classic_scanlog.CrashSuspectAnalysisInput("", ""))

    assert result.findings == []


def test_crash_suspect_analyzer_error_exposes_kind_code_and_message() -> None:
    with pytest.raises(classic_scanlog.AnalyzerError) as raised:
        classic_scanlog.CrashSuspectAnalyzer(
            [classic_scanlog.CrashSuspectMainErrorRule("", "Invalid", 1, ["signal"])],
            [],
        )

    assert raised.value.analyzer_kind.code == "crash_suspect"
    assert raised.value.code == "invalid_configuration"
    assert raised.value.message == "Crash Suspect main-error rule id must not be empty"


def test_crash_suspect_analyzer_handle_is_reusable_across_python_threads() -> None:
    analyzer = _analyzer()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(
                lambda index: _analyze(
                    analyzer, "plugin.dll" if index % 2 == 0 else "no main finding"
                ),
                range(12),
            )
        )

    assert [len(result.findings) for result in results] == [3, 1] * 6
