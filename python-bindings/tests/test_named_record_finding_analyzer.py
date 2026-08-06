from concurrent.futures import ThreadPoolExecutor

import pytest

import classic_scanlog


def test_named_record_finding_analyzer_returns_typed_counts_and_empty_success() -> None:
    analyzer = classic_scanlog.NamedRecordFindingAnalyzer(["ActorBase"], ["System"])
    populated = analyzer.analyze(
        classic_scanlog.NamedRecordFindingAnalysisInput(
            ["ActorBase_Player", "ActorBase_System", "ActorBase_Player"]
        )
    )
    empty = analyzer.analyze(
        classic_scanlog.NamedRecordFindingAnalysisInput(["unrelated"])
    )

    assert analyzer.kind is classic_scanlog.AnalyzerKind.NamedRecordFinding
    assert [(item.record, item.occurrences) for item in populated.findings] == [
        ("ActorBase_Player", 2)
    ]
    assert empty.findings == []


def test_named_record_finding_analyzer_preserves_shared_error_contract() -> None:
    with pytest.raises(classic_scanlog.AnalyzerError) as caught:
        classic_scanlog.NamedRecordFindingAnalyzer([" "], [])

    assert caught.value.analyzer_kind.code == "named_record_finding"
    assert caught.value.code == "invalid_configuration"
    assert (
        caught.value.message
        == "Named Record Finding target record must not be empty"
    )


def test_named_record_carriers_are_frozen_and_handle_reuse_is_concurrent() -> None:
    analyzer = classic_scanlog.NamedRecordFindingAnalyzer(["ActorBase"], [])
    input_value = classic_scanlog.NamedRecordFindingAnalysisInput(["ActorBase_Player"])
    result = analyzer.analyze(input_value)

    with pytest.raises(AttributeError):
        input_value.crash_lines = []
    with pytest.raises(AttributeError):
        result.findings = []
    with pytest.raises(AttributeError):
        result.findings[0].record = "changed"

    def analyze_count(line_count: int) -> int:
        concurrent_result = analyzer.analyze(
            classic_scanlog.NamedRecordFindingAnalysisInput(
                ["ActorBase_Player"] * line_count
            )
        )
        return concurrent_result.findings[0].occurrences

    with ThreadPoolExecutor(max_workers=8) as executor:
        observed = list(executor.map(analyze_count, range(1, 9)))

    assert observed == list(range(1, 9))
