"""Public Game Setup Intake using fully explicit isolated path inputs."""

import tempfile
from pathlib import Path


def observe_setup(fixture: dict) -> dict:
    """Compare direct and settings-backed intake without permitting ambient path discovery."""
    import classic_scangame

    if fixture["operation"] == "normalize":
        return {
            "versions": [
                classic_scangame.normalize_game_setup_version_selection(value)
                for value in fixture["versions"]
            ],
            "needs": [
                list(classic_scangame.game_setup_needs_path_detection(*paths))
                for paths in fixture["paths"]
            ],
        }
    with tempfile.TemporaryDirectory(prefix="classic-setup-conformance-") as temporary:
        root = Path(temporary)
        for name, content in fixture["files"].items():
            if (
                    "\\" in name
                    or Path(name).is_absolute()
                    or any(part in {"", ".", ".."} for part in name.split("/"))
            ):
                raise ValueError("setup fixture escaped root")
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.replace("<ROOT>", root.as_posix()).encode())

        def tree():
            """Capture all owned files and directories before and after read-only intake."""
            return {
                path.relative_to(root).as_posix(): path.read_bytes()
                if path.is_file()
                else None
                for path in sorted(root.rglob("*"))
            }

        before = tree()
        facts = fixture["facts"]

        def fact(name):
            """Resolve one optional root-relative fact; omitted facts stay unset for discovery."""
            value = facts.get(name)
            if value is None:
                return None
            if (
                    "\\" in value
                    or Path(value).is_absolute()
                    or any(part in {"", ".", ".."} for part in value.split("/"))
            ):
                raise ValueError("setup fact escaped root")
            return root / value

        game_root = fact("gameRoot")
        intake = classic_scangame.GameSetupIntake(
            facts["gameId"],
            facts["gameVersion"],
            game_root=game_root,
            docs_root=fact("docsRoot"),
            game_exe_path=fact("gameExePath"),
        )
        if (
                intake.game_id != facts["gameId"]
                or intake.game_version != facts["gameVersion"]
                or (None if intake.game_root is None else Path(intake.game_root))
                != game_root
        ):
            raise ValueError("setup constructor lost supplied facts")

        def project(result):
            """Read stable summary fields and verify typed checks agree with rendered output."""
            report = result.combined()
            if (
                    report != result.rendered_report
                    or result.total_checks != len(result.checks)
                    or result.failed_checks
                    != sum(check.state == "failed" for check in result.checks)
            ):
                raise ValueError("setup summary lost typed diagnostic facts")
            for check in result.checks:
                if (
                        f"[{check.state}] {check.kind}: {check.message}" not in report
                        or any(detail not in report for detail in check.details)
                ):
                    raise ValueError("setup report lost diagnostic content")
            return {
                "status": result.status,
                "hasErrors": result.has_errors,
                "totalChecks": result.total_checks,
                "failedChecks": result.failed_checks,
                "actionCount": result.action_count,
                "pathUpdateCount": result.path_update_count,
                "pathUpdates": [
                    {
                        "kind": update.kind,
                        "path": Path(update.path).relative_to(root).as_posix(),
                    }
                    for update in result.path_updates
                ],
                "gameRoot": Path(result.game_root).relative_to(root).as_posix(),
                "docsRoot": Path(result.docs_root).relative_to(root).as_posix(),
                "gameExecutable": Path(result.game_executable)
                .relative_to(root)
                .as_posix(),
                "reportFlags": {
                    "gameNamed": "Game Setup Intake: Starfield" in report,
                    "metadataUnsupported": "[unsupported] registry_metadata:" in report,
                    "versionWarning": "[warning] executable_version:" in report,
                    "documentsPassed": "[passed] documents_folder:" in report,
                    "loaderFailed": "[failed] xse_loader:" in report,
                },
            }

        direct = project(classic_scangame.run_game_setup_intake(intake))
        result = project(
            classic_scangame.run_game_setup_intake_from_user_settings(root)
        )
        if result != direct:
            raise ValueError(
                "settings-backed intake differs from equivalent explicit facts"
            )
        after = tree()
        return {
            **result,
            "files": [name for name, content in after.items() if content is not None],
            "unchanged": before == after,
        }
