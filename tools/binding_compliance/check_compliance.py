#!/usr/bin/env python3
"""Run the canonical CLASSIC binding compliance suite."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from catalog import requirements_for_profile  # type: ignore
from conformance.command import (  # type: ignore
    ConformanceCommandError,
    build_conformance_report_from_receipts,
)
from suite import ComplianceSuite, write_report_files  # type: ignore


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the canonical compliance command-line contract."""

    parser = argparse.ArgumentParser(
        description="Run the CLASSIC binding compliance suite."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--profile",
        default="ci",
        help=(
            "Execution profile: ci, full, conformance, static, cxx-ci, "
            "node-ci, or python-ci."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="tools/binding_compliance/artifacts",
        help="Directory for generated compliance reports, relative to repo root.",
    )
    parser.add_argument(
        "--skip-commands",
        action="store_true",
        help="Only run static requirement checks; command-backed checks are marked skipped.",
    )
    parser.add_argument(
        "--fail-on-gaps",
        action="store_true",
        help="Treat known coverage gaps as a failing CI result.",
    )
    parser.add_argument(
        "--list-requirements",
        action="store_true",
        help="Print the selected requirement catalog as JSON and exit.",
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

    if args.profile == "conformance":
        if not args.participant:
            return "--profile conformance requires --participant"
        if not args.receipt:
            return "--profile conformance requires at least one --receipt"
        if args.participant == "cxx" and (not args.attempt or not args.junit):
            return "CXX conformance requires companion --attempt and --junit paths"
    elif args.execution_instance or args.participant:
        return "--participant and --execution-instance require --profile conformance"
    if args.profile not in {"conformance", "full"} and args.receipt:
        return "--receipt is supported only by conformance and full profiles"
    if args.profile != "conformance" and (args.attempt or args.junit):
        return "--attempt and --junit require --profile conformance"
    return None


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, run the selected profile, and write reports."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    try:
        requirements = requirements_for_profile(args.profile)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.list_requirements:
        print(
            json.dumps(
                [
                    {
                        "id": requirement.id,
                        "title": requirement.title,
                        "surface": requirement.surface,
                        "classification": requirement.classification,
                        "blocking": requirement.blocking,
                    }
                    for requirement in requirements
                ],
                indent=2,
            )
        )
        return 0

    argument_error = _argument_error(args)
    if argument_error is not None:
        parser.error(argument_error)

    conformance_report = None
    if args.profile == "conformance" or (args.profile == "full" and args.receipt):
        try:
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

    suite = ComplianceSuite(
        repo_root=repo_root,
        profile=args.profile,
        requirements=requirements,
        skip_commands=args.skip_commands,
        fail_on_gaps=args.fail_on_gaps,
        conformance_report=conformance_report,
    )
    report = suite.run()
    json_path, markdown_path = write_report_files(report, repo_root / args.output_dir)

    summary = report["summary"]
    print(f"Binding compliance profile: {args.profile}")
    print(f"Result: {summary['result'].upper()}")
    print(f"- JSON report: {json_path}")
    print(f"- Markdown report: {markdown_path}")
    print(
        "Summary: passed={passed}, failed={failed}, gaps={coverage_gaps}, skipped={skipped}".format(
            **summary
        )
    )
    return 0 if summary["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
