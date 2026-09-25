#!/usr/bin/env python3
"""Run one retained runtime/build gate and publish its CI evidence."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path

from catalog import ComplianceRequirement, requirements_for_profile  # type: ignore
from gate_evidence import (  # type: ignore
    SINGLE_GATE_IDS,
    GateEvidenceError,
    current_source_revision,
    github_run_identity,
    write_gate_evidence,
)
from suite import ComplianceSuite  # type: ignore


def run_one_requirement(
    repo_root: Path,
    requirement: ComplianceRequirement,
    evidence_path: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> int:
    """Execute one catalog gate and record its real result for full aggregation.

    The Git and GitHub identity preflight happens before a potentially expensive
    build. Failed commands still write a failing evidence artifact and log their
    captured output so the producer job remains diagnosable.
    """
    if requirement.id not in SINGLE_GATE_IDS or requirement.command is None:
        raise GateEvidenceError(f"unsupported single retained gate: {requirement.id}")
    github_run_identity(environment)
    revision = current_source_revision(repo_root)
    report = ComplianceSuite(
        repo_root=repo_root,
        profile="single-gate",
        requirements=(requirement,),
    ).run()
    for result in report["requirements"]:
        if result.get("stdout"):
            print(result["stdout"], end="", file=sys.stdout)
        if result.get("stderr"):
            print(result["stderr"], end="", file=sys.stderr)
    destination = evidence_path if evidence_path.is_absolute() else repo_root / evidence_path
    write_gate_evidence(
        repo_root,
        destination,
        report,
        (requirement,),
        source_revision=revision,
        environment=environment,
    )
    return 0 if report["summary"]["result"] == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    """Select one approved retained gate and run it at the current checkout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--gate-id", required=True, choices=sorted(SINGLE_GATE_IDS))
    parser.add_argument("--gate-evidence-out", type=Path, required=True)
    args = parser.parse_args(argv)
    requirement = next(
        requirement
        for requirement in requirements_for_profile("full")
        if requirement.id == args.gate_id
    )
    try:
        return run_one_requirement(
            args.repo_root.resolve(), requirement, args.gate_evidence_out
        )
    except GateEvidenceError as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
