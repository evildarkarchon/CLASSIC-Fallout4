"""Observe public Scan Game results with no installed game or ambient discovery."""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from file_operations_conformance import _files, _owned_path


def _directories(root: Path) -> list[str]:
    """Record directory artifacts as well as files to detect read-only contract drift."""
    return sorted(
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()
    )


def observe_scan_game(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Run a fresh native validator on input-only files and normalize root spelling."""
    import classic_scangame as native

    operation = fixture["operation"]
    if operation == "assemble-reports":
        unpacked = native.build_unpacked_report(fixture["unpacked"], fixture["xse"])
        archived = native.build_archived_report(fixture["archived"], fixture["xse"])
        return {
            "unpacked": unpacked,
            "archived": archived,
            "combined": native.build_combined_scan_report(
                fixture["unpacked"], fixture["archived"], fixture["xse"]
            ),
            "unpackedMessages": native.get_scan_issue_messages(
                fixture["xse"], "unpacked"
            ),
            "archivedMessages": native.get_scan_issue_messages(
                fixture["xse"], "archived"
            ),
        }
    if operation not in {"validate-ini", "validate-enb", "process-logs"}:
        raise ValueError("unsupported scan game operation")
    with tempfile.TemporaryDirectory(
            prefix="classic-scan-game-conformance-"
    ) as directory:
        root = Path(directory)
        for path in fixture["directories"]:
            _owned_path(root, path).mkdir(parents=True, exist_ok=True)
        for path, content in fixture["files"].items():
            target = _owned_path(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))
        observation = {
            "operation": operation,
            "game": fixture["game"],
            "beforeFiles": _files(root),
            "beforeDirectories": _directories(root),
        }
        if operation == "process-logs":
            processor = native.LogProcessor(
                fixture["catch"], fixture["excludeFiles"], fixture["excludeErrors"]
            )
            report = processor.process_logs(root)
            if (
                    native.process_logs(
                        root,
                        fixture["catch"],
                        fixture["excludeFiles"],
                        fixture["excludeErrors"],
                    )
                    != report
                    or repr(processor) != "LogProcessor(...)"
            ):
                raise ValueError("log processor public aliases disagree")
            return {
                "report": report.replace(str(root), "<ROOT>").replace("\\", "/"),
                "beforeFiles": observation["beforeFiles"],
                "beforeDirectories": observation["beforeDirectories"],
                "files": _files(root),
                "directories": _directories(root),
            }
        if operation == "validate-ini":
            validator = native.IniValidator(fixture["game"])
            report = validator.validate_inis(root)
            # Python exposes issue detection with an explicit path map, so fixture
            # inputs provide the transport map after native validation has loaded it.
            config_files = {
                Path(path).name.lower(): root / path
                for path in fixture["files"]
                if Path(path).suffix.lower() in {".ini", ".conf"}
            }
            issues = [
                {
                    "filePath": Path(issue.file_path).relative_to(root).as_posix(),
                    "section": issue.section,
                    "setting": issue.setting,
                    "currentValue": issue.current_value,
                    "recommendedValue": issue.recommended_value,
                    "description": issue.description,
                    "severity": str(issue.severity).split(".")[-1],
                }
                for issue in validator.detect_all_issues(config_files)
            ]
            observation["result"] = {
                "report": report.replace(str(root), "<ROOT>").replace("\\", "/"),
                "issues": issues,
            }
        else:
            checker = native.EnbChecker(str(root))
            result = checker.validate()
            if (
                    checker.check_binaries() != result.binaries
                    or checker.check_config() != result.config
            ):
                raise ValueError("ENB public check methods disagree with validate")
            observation["result"] = {
                "binaries": str(result.binaries).split(".")[-1],
                "config": str(result.config).split(".")[-1],
            }
            expected_message = (
                "ENB is installed and configured.\n"
                if observation["result"] == {"binaries": "Present", "config": "Valid"}
                else "ENB binaries found but enbseries.ini is missing or unreadable.\n"
                if observation["result"]["binaries"] == "Present"
                else "Partial ENB installation detected. Some ENB files may be missing.\n"
                if observation["result"]["binaries"] == "Partial"
                else "ENB is not installed.\n"
            )
            if checker.format_message(result) != expected_message:
                raise ValueError(
                    "ENB formatted message disagrees with typed native result"
                )
            if result.is_present() != (
                    observation["result"]["binaries"] != "NotInstalled"
            ) or result.is_fully_configured() != (
                    observation["result"] == {"binaries": "Present", "config": "Valid"}
            ):
                raise ValueError(
                    "ENB public result queries disagree with native fields"
                )
            alias = native.check_enb(root)
            if alias.binaries != result.binaries or alias.config != result.config:
                raise ValueError(
                    "ENB public convenience function disagrees with checker"
                )
        observation["files"] = _files(root)
        observation["directories"] = _directories(root)
        return observation
