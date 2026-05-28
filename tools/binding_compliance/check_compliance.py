#!/usr/bin/env python3
"""Run the canonical CLASSIC binding compliance suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from catalog import requirements_for_profile # type: ignore
from suite import ComplianceSuite, write_report_files # type: ignore


def main() -> int:
    """Parse CLI arguments, run the selected profile, and write reports."""

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
        help="Execution profile: ci, full, static, cxx-ci, node-ci, or python-ci.",
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
    args = parser.parse_args()

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

    suite = ComplianceSuite(
        repo_root=repo_root,
        profile=args.profile,
        requirements=requirements,
        skip_commands=args.skip_commands,
        fail_on_gaps=args.fail_on_gaps,
    )
    report = suite.run()
    json_path, markdown_path = write_report_files(
        report, repo_root / args.output_dir
    )

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

