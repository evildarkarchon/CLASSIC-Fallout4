"""Concurrent game-check composition and nonfatal missing-mod-root behavior."""

from collections.abc import Mapping

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def matches_orchestration(observation: Mapping) -> bool:
    """Require all scheduled jobs, verified report assembly, and retained mod errors."""
    game = observation.get("game")
    return (
        set(observation) == {"game", "mods", "files"}
        and isinstance(game, Mapping)
        and set(game)
        == {"checkResults", "reportMatchesChecks", "configIssueCount", "errors"}
        and game["reportMatchesChecks"] is True
        and game["configIssueCount"] == 0
        and game["errors"] == []
        and isinstance(game["checkResults"], list)
        and [
            row.get("name") for row in game["checkResults"] if isinstance(row, Mapping)
        ]
        == ["crashgen", "enb", "game_logs", "mod_inis", "wrye_bash", "xse_plugins"]
        and all(
            set(row) == {"name", "output"} and isinstance(row["output"], str)
            for row in game["checkResults"]
        )
        and observation["mods"]
        == {
            "report": "",
            "unpackedIssueCount": 0,
            "archivedIssueCount": 0,
            "errors": ["Mods folder path not configured"],
        }
        and observation["files"] == [{"path": "sentinel.txt", "content": "unchanged\n"}]
    )


GAME_ORCHESTRATION_COVERAGE_POLICY = FamilyCoveragePolicy(
    "game-orchestration",
    (
        CoveragePredicate(
            "game-orchestration.composed",
            "game-orchestration.composed",
            "game-orchestration.composed",
            "values",
            (
                "GameScanConfig",
                "GameScanOrchestrator",
                "GameScanResult",
                "ModScanResult",
                "CheckResult",
                "run_game_checks",
                "run_mod_scans",
            ),
            matches_orchestration,
            runtime_operations=(
                None,
                "__init__",
                "run_game_checks",
                "run_mod_scans",
                "run_full_scan",
                "runGameChecks",
                "runModScans",
            ),
        ),
    ),
)
