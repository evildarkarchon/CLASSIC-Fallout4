"""Public-seam tests for semantic FormID Finding analysis."""

from __future__ import annotations

import pytest

import classic_scanlog


def plugin(name: str, prefix: str) -> classic_scanlog.FormIDPlugin:
    """Create one owned plugin-prefix fact."""

    return classic_scanlog.FormIDPlugin(name, prefix)


def test_formid_finding_analyzer_returns_hits_misses_and_unresolved_data() -> None:
    """The Python result keeps all semantic states without rendered report lines."""

    analyzer = classic_scanlog.FormIDFindingAnalyzer.in_memory(
        [
            classic_scanlog.FormIDFindingLookupEntry(
                "123456",
                "Found.esp",
                classic_scanlog.FormIDFindingLookupReplyKind.Found,
                value="Resolved value",
            )
        ]
    )
    result = analyzer.analyze(
        classic_scanlog.FormIDFindingAnalysisInput(
            [
                "Form ID: 0x01123456",
                "Form ID: 0x01123456",
                "Form ID: 0x02ABCDEF",
                "Form ID: 0x03999999",
            ],
            [plugin("Found.esp", "01"), plugin("Missing.esp", "02")],
        )
    )

    assert [(finding.identifier, finding.occurrences) for finding in result.findings] == [
        ("01123456", 2),
        ("02ABCDEF", 1),
        ("03999999", 1),
    ]
    assert result.findings[0].plugin == "Found.esp"
    assert result.findings[0].value == "Resolved value"
    assert (
        result.findings[0].value_lookup_status
        == classic_scanlog.FormIDValueLookupStatus.Found
    )
    assert result.findings[1].value is None
    assert (
        result.findings[1].value_lookup_status
        == classic_scanlog.FormIDValueLookupStatus.Missing
    )
    assert result.findings[2].plugin is None
    assert (
        result.findings[2].value_lookup_status
        == classic_scanlog.FormIDValueLookupStatus.NotApplicable
    )


def test_formid_finding_analyzer_raises_shared_typed_lookup_error() -> None:
    """Operational lookup failure uses the common analyzer exception envelope."""

    analyzer = classic_scanlog.FormIDFindingAnalyzer.in_memory(
        [
            classic_scanlog.FormIDFindingLookupEntry(
                "123456",
                "Broken.esp",
                classic_scanlog.FormIDFindingLookupReplyKind.OperationalFailure,
                error_message="fixture offline",
            )
        ]
    )

    with pytest.raises(classic_scanlog.AnalyzerError) as captured:
        analyzer.analyze(
            classic_scanlog.FormIDFindingAnalysisInput(
                ["Form ID: 0x01123456"],
                [plugin("Broken.esp", "01")],
            )
        )

    assert captured.value.analyzer_kind == classic_scanlog.AnalyzerKind.FormIdFinding
    assert captured.value.code == "operational_failure"
    assert "fixture offline" in captured.value.message
