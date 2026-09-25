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
from conformance.repository import (  # type: ignore
    build_repository_report,
    discover_repository_receipts,
)
from gate_evidence import (  # type: ignore
    GateEvidenceError,
    current_source_revision,
    github_run_identity,
    load_gate_evidence,
    write_gate_evidence,
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
        "--receipt-directory",
        type=Path,
        help="Full profile: recursively collect downloaded receipts with sibling plans.",
    )
    parser.add_argument(
        "--gate-evidence-out",
        type=Path,
        help="Participant source profile: write same-run retained-gate evidence.",
    )
    parser.add_argument(
        "--gate-evidence-directory",
        type=Path,
        help="Full profile: import current-run retained-gate evidence without rerunning commands.",
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
    if args.gate_evidence_out and args.profile not in {"cxx-ci", "node-ci", "python-ci"}:
        return "--gate-evidence-out requires cxx-ci, node-ci, or python-ci profile"
    if args.gate_evidence_directory and args.profile != "full":
        return "--gate-evidence-directory requires --profile full"
    if args.gate_evidence_out and args.gate_evidence_directory:
        return "gate evidence output and import cannot be combined"
    if args.skip_commands and (args.gate_evidence_out or args.gate_evidence_directory):
        return "gate evidence cannot be produced or imported with --skip-commands"
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
    if args.profile == "full":
        try:
            receipts = tuple(Path(value) for value in args.receipt)
            if args.receipt_directory:
                receipts += discover_repository_receipts(
                    repo_root, args.receipt_directory
                )
            conformance_report = build_repository_report(repo_root, receipts)
        except ConformanceCommandError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    elif args.profile == "conformance":
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

    imported_gate_results = None
    gate_evidence_error = None
    if args.gate_evidence_directory:
        try:
            run_id, run_attempt = github_run_identity()
            imported_gate_results = load_gate_evidence(
                repo_root,
                args.gate_evidence_directory,
                requirements,
                source_revision=current_source_revision(repo_root),
                run_id=run_id,
                run_attempt=run_attempt,
            )
        except GateEvidenceError as exc:
            # Keep a red full report after a producer failure; rerunning its
            # missing commands here would erase the same-run evidence boundary.
            gate_evidence_error = str(exc)
            imported_gate_results = {}
            print(gate_evidence_error, file=sys.stderr)

    suite = ComplianceSuite(
        repo_root=repo_root,
        profile=args.profile,
        requirements=requirements,
        skip_commands=args.skip_commands,
        fail_on_gaps=args.fail_on_gaps,
        conformance_report=conformance_report,
        imported_gate_results=imported_gate_results,
    )
    report = suite.run()
    if gate_evidence_error is not None:
        report["gateEvidenceError"] = gate_evidence_error
        report["summary"]["result"] = "fail"
        report["summary"]["repository_complete"] = False
    json_path, markdown_path = write_report_files(report, repo_root / args.output_dir)
    if args.gate_evidence_out:
        try:
            destination = (
                args.gate_evidence_out
                if args.gate_evidence_out.is_absolute()
                else repo_root / args.gate_evidence_out
            )
            write_gate_evidence(repo_root, destination, report, requirements)
        except GateEvidenceError as exc:
            print(str(exc), file=sys.stderr)
            return 2

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
