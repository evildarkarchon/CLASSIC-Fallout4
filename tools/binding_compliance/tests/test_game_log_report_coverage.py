"""Game log/report calls require complete authored observations."""

from tools.binding_compliance.conformance.families.scan_game import (
    SCAN_GAME_COVERAGE_POLICY,
)


def test_log_and_report_actions_have_exact_operation_scopes():
    """Missing methods cannot inherit unrelated INI/ENB proof."""
    predicates = {p.action: p for p in SCAN_GAME_COVERAGE_POLICY.predicates}
    logs = predicates["scan-game.process-logs"]
    reports = predicates["scan-game.assemble-reports"]
    assert "processGameLogs" in logs.runtime_operations
    assert "build_combined_scan_report" in reports.runtime_operations
    assert not logs.matches({"report": ""})
    assert not reports.matches({"combined": ""})
