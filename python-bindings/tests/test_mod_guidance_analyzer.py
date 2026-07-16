"""Runtime contract tests for semantic Mod Guidance analysis."""

from concurrent.futures import ThreadPoolExecutor

import pytest

import classic_scanlog


def _analyzer() -> classic_scanlog.ModGuidanceAnalyzer:
    return classic_scanlog.ModGuidanceAnalyzer(
        [
            classic_scanlog.ModGuidanceConflictRule(
                "alpha",
                "beta",
                "Alpha Mod",
                "Beta Mod",
                "Authored conflict description",
                "Install the authored compatibility patch",
                "https://example.invalid/patch",
            )
        ],
        [
            classic_scanlog.ModGuidanceSolutionRule(
                "frequent-crash",
                classic_scanlog.ModGuidanceCriteriaKind.Any,
                ["crashfix"],
                [],
                "Frequent Crash Mod",
                "Authored frequent-crash guidance",
            )
        ],
        [
            classic_scanlog.ModGuidanceSolutionRule(
                "solution",
                classic_scanlog.ModGuidanceCriteriaKind.All,
                ["solution", "alpha"],
                [],
                "Solution Mod",
                "Authored solution guidance",
            )
        ],
        [
            classic_scanlog.ModGuidanceImportantModRule(
                "installed.dll",
                "Installed Important Mod",
                "Installed authored description",
                None,
                None,
                None,
            ),
            classic_scanlog.ModGuidanceImportantModRule(
                "missing.dll",
                "Missing Important Mod",
                "Missing authored description\nwith a second line",
                "amd",
                None,
                None,
            ),
            classic_scanlog.ModGuidanceImportantModRule(
                "wronggpu.dll",
                "Wrong GPU Important Mod",
                "Wrong GPU authored description",
                "nvidia",
                "Authored GPU mismatch warning",
                None,
            ),
        ],
    )


def _analyze(
    analyzer: classic_scanlog.ModGuidanceAnalyzer,
) -> classic_scanlog.ModGuidanceAnalysisResult:
    return analyzer.analyze(
        classic_scanlog.ModGuidanceAnalysisInput(
            {
                "Alpha.esp": "01",
                "Beta.esp": "02",
                "CrashFix.esp": "03",
                "Solution.esp": "04",
            },
            "amd",
            {"Installed.dll", "WrongGpu.dll"},
        )
    )


def test_mod_guidance_analyzer_returns_aggregate_semantic_guidance() -> None:
    analyzer = _analyzer()

    result = _analyze(analyzer)

    assert analyzer.kind.code == "mod_guidance"
    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.state.value == "matched"
    assert conflict.mod_a == "alpha"
    assert conflict.mod_b == "beta"
    assert conflict.name_a == "Alpha Mod"
    assert conflict.name_b == "Beta Mod"
    assert conflict.description == "Authored conflict description"
    assert conflict.fix == "Install the authored compatibility patch"
    assert conflict.link == "https://example.invalid/patch"

    assert len(result.frequent_crashes) == 1
    frequent = result.frequent_crashes[0]
    assert frequent.state.value == "matched"
    assert frequent.id == "frequent-crash"
    assert frequent.name == "Frequent Crash Mod"
    assert frequent.description == "Authored frequent-crash guidance"
    assert frequent.matched_plugin_ids == ["03"]

    assert len(result.solutions) == 1
    solution = result.solutions[0]
    assert solution.id == "solution"
    assert solution.matched_plugin_ids == ["04", "01"]

    assert [item.state.value for item in result.important_mods] == [
        "matched",
        "missing",
        "gpu_mismatch",
    ]
    assert result.important_mods[0].detect == "installed.dll"
    assert result.important_mods[0].name == "Installed Important Mod"
    assert result.important_mods[1].description == (
        "Missing authored description\nwith a second line"
    )
    assert result.important_mods[1].gpu == "amd"
    assert result.important_mods[2].gpu_mismatch_warning == (
        "Authored GPU mismatch warning"
    )
    with pytest.raises(AttributeError):
        result.conflicts = []


def test_mod_guidance_analyzer_returns_explicit_empty_result() -> None:
    analyzer = classic_scanlog.ModGuidanceAnalyzer([], [], [], [])

    result = analyzer.analyze(classic_scanlog.ModGuidanceAnalysisInput({}, None, set()))

    assert result.conflicts == []
    assert result.frequent_crashes == []
    assert result.solutions == []
    assert result.important_mods == []


def test_report_producing_mod_detection_functions_are_not_public() -> None:
    for obsolete_name in (
        "detect_mods_single",
        "detect_mods_double",
        "detect_mods_important",
        "detect_mods_batch",
    ):
        assert not hasattr(classic_scanlog, obsolete_name)


def test_mod_guidance_analyzer_error_exposes_kind_code_and_message() -> None:
    with pytest.raises(classic_scanlog.AnalyzerError) as raised:
        classic_scanlog.ModGuidanceAnalyzer(
            [
                classic_scanlog.ModGuidanceConflictRule(
                    "",
                    "beta",
                    "Alpha Mod",
                    "Beta Mod",
                    "Description",
                    "Fix",
                    None,
                )
            ],
            [],
            [],
            [],
        )

    assert raised.value.analyzer_kind.code == "mod_guidance"
    assert raised.value.code == "invalid_configuration"
    assert raised.value.message == "Mod Guidance conflict mod_a must not be empty"


def test_mod_guidance_analyzer_handle_is_reusable_across_python_threads() -> None:
    analyzer = _analyzer()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: _analyze(analyzer), range(12)))

    assert all(len(result.conflicts) == 1 for result in results)
    assert all(len(result.frequent_crashes) == 1 for result in results)
    assert all(len(result.solutions) == 1 for result in results)
    assert all(len(result.important_mods) == 3 for result in results)
