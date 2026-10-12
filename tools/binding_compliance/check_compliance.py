#!/usr/bin/env python3
"""Run the CLASSIC executable conformance verdict (conformance or full profile).

The static requirement catalog, its suite and retained-gate evidence retired
with the Python and Node bindings (Retire, #304). Only the receipt-backed
``conformance`` profile and the conformance-only ``full`` repository verdict
remain until the Rust conformance engine replaces this command.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from conformance.command import (  # type: ignore
    ConformanceCommandError,
    build_conformance_report_from_receipts,
)
from conformance.repository import (  # type: ignore
    build_repository_report,
    discover_repository_receipts,
)

PROFILES = ("conformance", "full")
REPORT_JSON_NAME = "binding_compliance_report.json"
REPORT_MARKDOWN_NAME = "binding_compliance_report.md"


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the canonical conformance command-line contract."""

    parser = argparse.ArgumentParser(
        description="Run the CLASSIC executable conformance verdict."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--profile",
        required=True,
        choices=PROFILES,
        help="Execution profile: conformance (one participant) or full (repository).",
    )
    parser.add_argument(
        "--output-dir",
        default="tools/binding_compliance/artifacts",
        help="Directory for generated reports, relative to repo root.",
    )
    parser.add_argument(
        "--participant",
        help="Applicable participant ID for the conformance profile.",
    )
    parser.add_argument(
        "--execution-instance",
        help="Optional exact execution-instance slice for one participant.",
    )
    parser.add_argument(
        "--receipt",
        action="append",
        default=[],
        help="Receipt path; repeat to aggregate every instance in the requested scope.",
    )
    parser.add_argument(
        "--receipt-directory",
        type=Path,
        help="Full profile: recursively collect downloaded receipts with sibling plans.",
    )
    parser.add_argument(
        "--attempt",
        help="Companion native attempt diagnostics; never semantic evidence.",
    )
    parser.add_argument(
        "--junit",
        help="Companion native JUnit artifact; never semantic evidence.",
    )
    return parser


def _argument_error(args: argparse.Namespace) -> str | None:
    """Return a profile-specific CLI contract error, if any."""

    if args.receipt_directory and args.profile != "full":
        return "--receipt-directory requires --profile full"
    if args.profile == "conformance":
        if not args.participant:
            return "--profile conformance requires --participant"
        if not args.receipt:
            return "--profile conformance requires at least one --receipt"
        if args.participant == "cxx" and (not args.attempt or not args.junit):
            return "CXX conformance requires companion --attempt and --junit paths"
    elif args.execution_instance or args.participant:
        return "--participant and --execution-instance require --profile conformance"
    if args.profile != "conformance" and (args.attempt or args.junit):
        return "--attempt and --junit require --profile conformance"
    return None


def build_report(profile: str, conformance_report: dict[str, Any]) -> dict[str, Any]:
    """Wrap a conformance report in the stable top-level report document.

    ``conformance`` takes the scoped report's own result. ``full`` passes only
    when the repository report is complete and passing; ``repository_complete``
    is never true for the ``conformance`` profile.
    """

    result = str(conformance_report.get("result", "fail"))
    repository_complete = False
    if profile == "full":
        repository_complete = (
            conformance_report.get("repositoryComplete") is True and result == "pass"
        )
        if not repository_complete:
            result = "fail"
    return {
        "schemaVersion": 1,
        "profile": profile,
        "summary": {
            "result": result,
            "repository_complete": repository_complete,
        },
        "conformance": dict(conformance_report),
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a short human-readable summary of a report document."""

    summary = report["summary"]
    conformance = report["conformance"]
    lines = [
        "# Binding Compliance Report",
        "",
        f"- Profile: `{report['profile']}`",
        f"- Result: **{summary['result'].upper()}**",
        f"- Repository complete: **{'yes' if summary['repository_complete'] else 'no'}**",
        "",
        "## Executable Conformance",
        "",
        f"- Result: **{str(conformance.get('result', 'unknown')).upper()}**",
    ]
    for key, label in (("missingFamilies", "Missing families"),):
        values = conformance.get(key)
        if isinstance(values, list) and values:
            lines.append(f"- {label}: {', '.join(f'`{value}`' for value in values)}")
    lines.append("")
    return "\n".join(lines)


def write_report_files(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write the JSON and Markdown reports and return their paths.

    The file names are stable: CI uploads glob ``**/binding_compliance_report.*``.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REPORT_JSON_NAME
    markdown_path = output_dir / REPORT_MARKDOWN_NAME
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, build the selected verdict, and write reports.

    Returns 0 on a passing verdict, 1 on a failing one, and 2 when receipts or
    catalogs are invalid (argument errors exit 2 through ``argparse``).
    """

    parser = build_argument_parser()
    args = parser.parse_args(argv)
    argument_error = _argument_error(args)
    if argument_error is not None:
        parser.error(argument_error)

    repo_root = Path(args.repo_root).resolve()
    try:
        if args.profile == "full":
            receipts = tuple(Path(value) for value in args.receipt)
            if args.receipt_directory:
                receipts += discover_repository_receipts(
                    repo_root, args.receipt_directory
                )
            conformance_report = build_repository_report(repo_root, receipts)
        else:
            conformance_report = build_conformance_report_from_receipts(
                repo_root,
                profile=args.profile,
                participant_id=args.participant,
                execution_instance_id=args.execution_instance,
                receipt_paths=tuple(Path(value) for value in args.receipt),
                attempt_path=Path(args.attempt) if args.attempt else None,
                junit_path=Path(args.junit) if args.junit else None,
            )
    except ConformanceCommandError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    report = build_report(args.profile, conformance_report)
    json_path, markdown_path = write_report_files(report, repo_root / args.output_dir)
    summary = report["summary"]
    print(f"Binding compliance profile: {args.profile}")
    print(f"Result: {summary['result'].upper()}")
    print(f"- JSON report: {json_path}")
    print(f"- Markdown report: {markdown_path}")
    return 0 if summary["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
