"""Exercise actual Crashgen checker and orchestration surfaces on isolated files."""

import tempfile
from pathlib import Path
from typing import Any

from file_operations_conformance import _files, _owned_path


def observe_crashgen_check(fixture: dict[str, Any]) -> dict[str, Any]:
    """Compare native aliases before exposing the full report and durable input bytes."""
    import classic_scangame as native

    with tempfile.TemporaryDirectory(prefix="classic-crashgen-") as directory:
        root = Path(directory)
        for path, content in fixture["files"].items():
            target = _owned_path(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))

        def issues(values: Any) -> list[dict[str, str]]:
            """Project every public issue field, normalizing only the owned root."""
            return [
                {
                    "path": str(value.file_path.relative_to(root)).replace("\\", "/"),
                    "section": value.section,
                    "setting": value.setting,
                    "current": value.current_value,
                    "recommended": value.recommended_value,
                    "description": value.description,
                    "severity": str(value.severity).split(".")[-1],
                }
                for value in values
            ]

        before = _files(root)
        checker = native.CrashgenChecker(root, "Buffout4")
        message, values = checker.check()
        projected = issues(values)
        direct_message, direct_issues = native.check_crashgen_config(root, "Buffout4")
        orchestrator = native.CrashgenCheckOrchestrator()
        report = orchestrator.check(root, "Buffout4")
        alias_message, alias_issues = native.check_crashgen_settings(root, "Buffout4")
        resolved = orchestrator.resolve_config_path(root)
        plugins = sorted(report.installed_plugins)
        if (
                direct_message != message
                or issues(direct_issues) != projected
                or report.message != message
                or issues(report.issues) != projected
                or alias_message != message
                or issues(alias_issues) != projected
                or report.config_path != resolved
                or sorted(orchestrator.detect_plugins(root)) != plugins
        ):
            raise ValueError("native Crashgen aliases disagree")
        if (
                repr(checker) != "CrashgenChecker(...)"
                or repr(orchestrator) != "CrashgenCheckOrchestrator()"
        ):
            raise ValueError("native Crashgen constructors returned wrong types")
        return {
            "message": message,
            "issues": projected,
            "name": report.crashgen_name,
            "config": resolved.relative_to(root).as_posix() if resolved else None,
            "plugins": plugins,
            "beforeFiles": before,
            "files": _files(root),
        }
