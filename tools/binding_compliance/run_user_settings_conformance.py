#!/usr/bin/env python3
"""Run one read-only User Settings adapter and publish its shadow report."""

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
from run_scan_run_conformance import (
    run_participant as run_prepared_participant,
)

PACK_PATH = REPO_ROOT / "tests/conformance/packs/user_settings/v1.json"
_COMMON_SOURCES = (
    Path(__file__).resolve(),
    REPO_ROOT / "tools/binding_compliance/run_scan_run_conformance.py",
    REPO_ROOT / "business-logic/classic-user-settings-core/src",
    REPO_ROOT / "business-logic/classic-user-settings-core/Cargo.toml",
)
PARTICIPANT_COMMANDS = {
    "rust": ParticipantCommand(
        arguments=(
            "cargo",
            "test",
            "-p",
            "classic-user-settings-core",
            "--test",
            "open_conformance",
            "--",
            "--exact",
            "writes_user_settings_conformance_receipt",
            "--nocapture",
        ),
        working_directory=REPO_ROOT,
        source_paths=(
            REPO_ROOT
            / "business-logic/classic-user-settings-core/tests/open_conformance.rs",
            *_COMMON_SOURCES,
        ),
    ),
    "node": ParticipantCommand(
        arguments=("bun", "run", "conformance:user-settings"),
        working_directory=REPO_ROOT / "node-bindings/classic-node",
        source_paths=(
            REPO_ROOT
            / "node-bindings/classic-node/__test__/user_settings_conformance_runner.ts",
            REPO_ROOT / "node-bindings/classic-node/src/user_settings.rs",
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
            "python-bindings/tests/user_settings_conformance_runner.py",
        ),
        working_directory=REPO_ROOT,
        source_paths=(
            REPO_ROOT / "python-bindings/tests/user_settings_conformance_runner.py",
            REPO_ROOT / "python-bindings/classic-user-settings-py/src",
            *_COMMON_SOURCES,
        ),
    ),
}


def run_participant(
    participant_id: str,
    *,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    timeout_seconds: int = 1_200,
) -> tuple[int, Path]:
    """Execute settings through shared launch/receipt validation machinery.

    Shadow enforcement leaves retained registry-backed checks authoritative.
    This diagnostic command still returns nonzero on failed execution or
    comparison so callers can distinguish shadow failure from success.
    """

    return run_prepared_participant(
        participant_id,
        artifact_root=artifact_root,
        timeout_seconds=timeout_seconds,
        pack_path=PACK_PATH,
        command=PARTICIPANT_COMMANDS[participant_id],
    )


def main(argv: list[str] | None = None) -> int:
    """Launch the selected adapter and print its fresh diagnostic location."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--participant", choices=sorted(PARTICIPANT_COMMANDS), required=True
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=1_200)
    args = parser.parse_args(argv)
    try:
        result, artifact_dir = run_participant(
            args.participant,
            artifact_root=args.artifact_root,
            timeout_seconds=args.timeout_seconds,
        )
    except (ConformanceCommandError, PackValidationError, ValueError) as error:
        print(f"User Settings conformance launch failed: {error}", file=sys.stderr)
        return 1
    print(artifact_dir.relative_to(REPO_ROOT).as_posix())
    return result


if __name__ == "__main__":
    raise SystemExit(main())
