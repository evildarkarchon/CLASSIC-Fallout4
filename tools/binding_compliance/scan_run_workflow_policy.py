#!/usr/bin/env python3
"""Validate blocking Scan Run and User Settings receipt placement in tracked CI."""

from __future__ import annotations

import argparse
from pathlib import Path

from conformance.workflow_policy import (
    WorkflowPolicyError,
    validate_scan_run_workflow_policy,
)


def main(argv: list[str] | None = None) -> int:
    """Validate the repository workflow ratchet and return a process status."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args(argv)
    try:
        validate_scan_run_workflow_policy(args.repo_root)
    except WorkflowPolicyError as error:
        print(f"Scan Run and User Settings workflow policy failed: {error}")
        return 1
    print("Scan Run and User Settings workflow policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
