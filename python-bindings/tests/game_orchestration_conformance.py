"""Run real concurrent game checks and the public full-scan composition."""

import tempfile
from pathlib import Path


def observe_orchestration(fixture: dict) -> dict:
    """Authenticate report assembly before normalizing concurrent completion order."""
    import classic_scangame

    with tempfile.TemporaryDirectory(
        prefix="classic-orchestration-conformance-"
    ) as temporary:
        root = Path(temporary)
        for name, content in fixture["files"].items():
            if name != "sentinel.txt":
                raise ValueError("unsupported orchestration fixture path")
            (root / name).write_bytes(content.encode())
        config = classic_scangame.GameScanConfig(
            root,
            fixture["xseAcronym"],
            fixture["crashgenName"],
            fixture["gameName"],
            log_catch_errors=["error"],
        )
        if (
            config.game_path != root
            or config.xse_acronym != fixture["xseAcronym"]
            or config.game_name != fixture["gameName"]
        ):
            raise ValueError(
                "orchestrator configuration lost public constructor fields"
            )
        orchestrator = classic_scangame.GameScanOrchestrator(config)

        def game_result(value):
            """Verify raw report order, then canonicalize inherently unordered job completion."""
            checks = [
                {"name": row.name, "output": row.output} for row in value.check_results
            ]
            matches = value.report == "".join(row["output"] for row in checks)
            return {
                "checkResults": sorted(checks, key=lambda row: row["name"]),
                "reportMatchesChecks": matches,
                "configIssueCount": len(value.config_issues),
                "errors": sorted(value.errors),
            }

        def mod_result(value):
            """Read every public mod-scan summary field."""
            return {
                "report": value.report,
                "unpackedIssueCount": value.unpacked_issue_count,
                "archivedIssueCount": value.archived_issue_count,
                "errors": sorted(value.errors),
            }

        game = game_result(orchestrator.run_game_checks())
        mods = mod_result(orchestrator.run_mod_scans())
        full_game, full_mods = orchestrator.run_full_scan()
        if game_result(full_game) != game or mod_result(full_mods) != mods:
            raise ValueError("full scan lost one of its native component results")
        return {
            "game": game,
            "mods": mods,
            "files": [
                {
                    "path": path.relative_to(root).as_posix(),
                    "content": path.read_bytes().decode(),
                }
                for path in sorted(root.rglob("*"))
                if path.is_file()
            ],
        }
