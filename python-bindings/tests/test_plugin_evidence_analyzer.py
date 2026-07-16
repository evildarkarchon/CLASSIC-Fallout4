from concurrent.futures import ThreadPoolExecutor

import pytest

import classic_scanlog


def test_plugin_evidence_analyzer_returns_typed_counts_and_empty_success() -> None:
    analyzer = classic_scanlog.PluginEvidenceAnalyzer(["Fallout4.esm"])
    populated = analyzer.analyze(
        classic_scanlog.PluginEvidenceAnalysisInput(
            ["Example.ESP", "example.esp", "modified by: example.esp"],
            ["Example.ESP", "Fallout4.esm", " "],
        )
    )
    empty = analyzer.analyze(
        classic_scanlog.PluginEvidenceAnalysisInput([], ["Example.ESP"])
    )

    assert analyzer.kind is classic_scanlog.AnalyzerKind.PluginEvidence
    assert [(item.plugin, item.occurrences) for item in populated.evidence] == [
        ("example.esp", 2)
    ]
    assert empty.evidence == []


def test_plugin_evidence_analyzer_preserves_shared_error_contract() -> None:
    with pytest.raises(classic_scanlog.AnalyzerError) as caught:
        classic_scanlog.PluginEvidenceAnalyzer([" "])

    assert caught.value.analyzer_kind.code == "plugin_evidence"
    assert caught.value.code == "invalid_configuration"
    assert caught.value.message == "Plugin Evidence ignored plugin must not be empty"


def test_plugin_evidence_analyzer_carriers_are_frozen_and_handle_reuse_is_concurrent() -> None:
    analyzer = classic_scanlog.PluginEvidenceAnalyzer([])
    input_value = classic_scanlog.PluginEvidenceAnalysisInput(
        ["Example.esp"], ["Example.esp"]
    )
    result = analyzer.analyze(input_value)

    with pytest.raises(AttributeError):
        input_value.plugins = []
    with pytest.raises(AttributeError):
        result.evidence = []
    with pytest.raises(AttributeError):
        result.evidence[0].plugin = "changed.esp"

    def analyze_count(line_count: int) -> int:
        concurrent_result = analyzer.analyze(
            classic_scanlog.PluginEvidenceAnalysisInput(
                ["Example.esp"] * line_count, ["Example.esp"]
            )
        )
        return concurrent_result.evidence[0].occurrences

    with ThreadPoolExecutor(max_workers=8) as executor:
        observed = list(executor.map(analyze_count, range(1, 9)))

    assert observed == list(range(1, 9))
