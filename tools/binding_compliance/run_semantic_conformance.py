#!/usr/bin/env python3
"""Run one focused semantic family through the shared authenticated lifecycle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from run_scan_run_conformance import (
    DEFAULT_ARTIFACT_ROOT,
    REPO_ROOT,
    ConformanceCommandError,
    PackValidationError,
    ParticipantCommand,
)
from run_scan_run_conformance import run_participant as run_prepared_participant

SUPPORTED_FAMILIES = (
    "crash-suspect",
    "crashgen-settings",
    "mod-guidance",
    "formid-lookup",
    "named-record",
    "plugin-evidence",
    "installed-yaml-data",
)

_COMMON_SOURCES = (
    Path(__file__).resolve(),
    REPO_ROOT / "tools/binding_compliance/run_scan_run_conformance.py",
    REPO_ROOT / "business-logic/classic-scanlog-core/src",
    REPO_ROOT / "business-logic/classic-scanlog-core/Cargo.toml",
    REPO_ROOT / "business-logic/classic-database-core/src",
    REPO_ROOT / "business-logic/classic-config-core/src",
)
PARTICIPANT_COMMANDS = {
    "rust": ParticipantCommand(
        arguments=(
            "cargo",
            "test",
            "-p",
            "classic-scanlog-core",
            "--test",
            "semantic_conformance",
            "--",
            "--nocapture",
        ),
        working_directory=REPO_ROOT,
        source_paths=(
            REPO_ROOT
            / "business-logic/classic-scanlog-core/tests/semantic_conformance.rs",
            REPO_ROOT
            / "business-logic/classic-scanlog-core/tests/semantic_conformance",
            *_COMMON_SOURCES,
        ),
    ),
    "node": ParticipantCommand(
        arguments=("bun", "run", "conformance:semantic"),
        working_directory=REPO_ROOT / "node-bindings/classic-node",
        source_paths=(
            REPO_ROOT
            / "node-bindings/classic-node/__test__/semantic_conformance_runner.ts",
            REPO_ROOT
            / "node-bindings/classic-node/__test__/installed_yaml_conformance.ts",
            REPO_ROOT / "node-bindings/classic-node/src",
            REPO_ROOT / "node-bindings/classic-node/package.json",
            *_COMMON_SOURCES,
        ),
    ),
    "python": ParticipantCommand(
        arguments=(
            "uv",
            "run",
            "--project",
            "python-bindings",
            "python",
            "python-bindings/tests/semantic_conformance_runner.py",
        ),
        working_directory=REPO_ROOT,
        source_paths=(
            REPO_ROOT / "python-bindings/tests/semantic_conformance_runner.py",
            REPO_ROOT / "python-bindings/tests/installed_yaml_conformance.py",
            REPO_ROOT / "python-bindings/classic-config-py/src",
            REPO_ROOT / "python-bindings/classic-scanlog-py/src",
            REPO_ROOT / "python-bindings/classic-database-py/src",
            *_COMMON_SOURCES,
        ),
    ),
}


def run_participant(
    participant_id: str,
    *,
    family: str,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    timeout_seconds: int = 1_200,
) -> tuple[int, Path]:
    """Execute every scenario for one family and validate fresh typed receipts.

    Family input comes only from the authenticated run plan. Each invocation
    retains the shared launcher's bounded execution and failure diagnostics.
    Native CXX runs separately through the repository's approved CLI wrapper.
    """

    if family not in SUPPORTED_FAMILIES:
        raise ValueError("unsupported semantic conformance family: " + family)
    return run_prepared_participant(
        participant_id,
        artifact_root=artifact_root,
        timeout_seconds=timeout_seconds,
        pack_path=REPO_ROOT
        / "tests/conformance/packs"
        / family.replace("-", "_")
        / "v1.json",
        command=PARTICIPANT_COMMANDS[participant_id],
    )


def main(argv: list[str] | None = None) -> int:
    """Launch one selected family/adapter and print its retained artifact path."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=SUPPORTED_FAMILIES, required=True)
    parser.add_argument(
        "--participant", choices=sorted(PARTICIPANT_COMMANDS), required=True
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=1_200)
    args = parser.parse_args(argv)
    try:
        result, artifact_dir = run_participant(
            args.participant,
            family=args.family,
            artifact_root=args.artifact_root,
            timeout_seconds=args.timeout_seconds,
        )
    except (ConformanceCommandError, PackValidationError, ValueError) as error:
        print(f"Semantic conformance launch failed: {error}", file=sys.stderr)
        return 1
    print(artifact_dir)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
