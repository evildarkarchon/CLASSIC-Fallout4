#!/usr/bin/env python3
"""Run one base Crash Log Scan Run adapter and publish its scoped report."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from conformance.command import (
    ConformanceCommandError,
    build_conformance_report_from_receipts,
)
from conformance.packs import (
    PackValidationError,
    load_and_validate_pack,
    materialize_run_plan,
)

PACK_PATH = (
    REPO_ROOT / "tests" / "conformance" / "packs" / "crash_log_scan_run" / "v1.json"
)
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "tools" / "binding_compliance" / "artifacts"


@dataclass(frozen=True)
class ParticipantCommand:
    """One private adapter command and the source paths its receipt authenticates."""

    arguments: tuple[str, ...]
    working_directory: Path
    source_paths: tuple[Path, ...]


_COMMON_CORE_SOURCES = (
    Path(__file__).resolve(),
    REPO_ROOT / "business-logic" / "classic-scanlog-core" / "src" / "scan_run",
    REPO_ROOT / "business-logic" / "classic-scan-presentation" / "src",
)
PARTICIPANT_COMMANDS = {
    "rust": ParticipantCommand(
        arguments=(
            "cargo",
            "test",
            "-p",
            "classic-scan-presentation",
            "--test",
            "scan_run_conformance",
            "--",
            "--exact",
            "writes_scan_run_conformance_receipt",
            "--nocapture",
        ),
        working_directory=REPO_ROOT,
        source_paths=(
            REPO_ROOT
            / "business-logic"
            / "classic-scan-presentation"
            / "tests"
            / "scan_run_conformance.rs",
            REPO_ROOT / "business-logic" / "classic-scan-presentation" / "Cargo.toml",
            *_COMMON_CORE_SOURCES,
        ),
    ),
    "node": ParticipantCommand(
        arguments=("bun", "run", "conformance:scan-run"),
        working_directory=REPO_ROOT / "node-bindings" / "classic-node",
        source_paths=(
            REPO_ROOT
            / "node-bindings"
            / "classic-node"
            / "__test__"
            / "scan_run_conformance_runner.ts",
            REPO_ROOT / "node-bindings" / "classic-node" / "src" / "scan_run.rs",
            REPO_ROOT / "node-bindings" / "classic-node" / "package.json",
            *_COMMON_CORE_SOURCES,
        ),
    ),
    "python": ParticipantCommand(
        arguments=(
            "uv",
            "run",
            "--project",
            "python-bindings",
            "python",
            "python-bindings/tests/scan_run_conformance_runner.py",
        ),
        working_directory=REPO_ROOT,
        source_paths=(
            REPO_ROOT / "python-bindings" / "tests" / "scan_run_conformance_runner.py",
            REPO_ROOT
            / "python-bindings"
            / "classic-scanlog-py"
            / "src"
            / "scan_run.rs",
            *_COMMON_CORE_SOURCES,
        ),
    ),
}


def _atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    """Publish one diagnostic JSON document without exposing partial bytes."""

    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _attempt_document(
    participant_id: str,
    command: ParticipantCommand,
    completed: subprocess.CompletedProcess[str] | None,
    timeout: subprocess.TimeoutExpired | None,
    launch_error: OSError | None,
) -> dict[str, Any]:
    """Return stable diagnostics for the exact native command attempt."""

    def timeout_text(value: str | bytes | None) -> str:
        """Normalize ``TimeoutExpired`` output, which may remain raw bytes."""

        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value or ""

    return {
        "schemaVersion": 1,
        "participantId": participant_id,
        "command": list(command.arguments),
        "workingDirectory": command.working_directory.relative_to(REPO_ROOT).as_posix()
        or ".",
        "exitCode": completed.returncode if completed is not None else None,
        "timedOut": timeout is not None,
        "launchError": str(launch_error) if launch_error is not None else None,
        "stdout": (
            completed.stdout
            if completed is not None
            else timeout_text(timeout.stdout if timeout is not None else None)
        ),
        "stderr": (
            completed.stderr
            if completed is not None
            else timeout_text(timeout.stderr if timeout is not None else None)
        ),
    }


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Stop an adapter command and its descendants before validating artifacts.

    Native build/test launchers can outlive their direct parent on timeout. The
    whole owned tree must be gone before central validation, or a descendant
    could publish a stale receipt after the conformance report is finalized.
    """

    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ("taskkill", "/PID", str(process.pid), "/T", "/F"),
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            # The process tree exited between poll() and killpg().
            pass
        except PermissionError:
            process.kill()
    if process.poll() is None:
        process.kill()
    process.wait()


def _run_adapter_command(
    command: ParticipantCommand,
    environment: Mapping[str, str],
    timeout_seconds: int,
) -> tuple[
    subprocess.CompletedProcess[str] | None,
    subprocess.TimeoutExpired | None,
    OSError | None,
]:
    """Run one adapter command and return complete structured attempt state."""

    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            command.arguments,
            cwd=command.working_directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags,
            start_new_session=os.name != "nt",
        )
    except OSError as error:
        return None, None, error

    timeout: subprocess.TimeoutExpired | None = None
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        timeout = error
        _terminate_process_tree(process)
        stdout, stderr = process.communicate()
    completed = subprocess.CompletedProcess(
        command.arguments,
        process.returncode,
        stdout,
        stderr,
    )
    return completed, timeout, None


def run_participant(
    participant_id: str,
    *,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    timeout_seconds: int = 1_200,
    pack_path: Path = PACK_PATH,
    command: ParticipantCommand | None = None,
) -> tuple[int, Path]:
    """Execute one public adapter seam and build its exact participant report.

    ``pack_path`` and ``command`` select another family without duplicating
    invocation isolation or failure handling. The return code reports actual
    execution/comparison success even for a shadow family; CI separately keeps
    its retained parity/runtime gates blocking.
    """

    command = command or PARTICIPANT_COMMANDS[participant_id]
    pack = load_and_validate_pack(REPO_ROOT, pack_path)
    prepared = materialize_run_plan(
        pack,
        participant_id=participant_id,
        participant_role="semantic-adapter",
        execution_instance_id=participant_id,
        source_paths=command.source_paths,
        artifact_root=artifact_root,
    )
    environment = os.environ.copy()
    environment["CLASSIC_CONFORMANCE_RUN_PLAN"] = str(prepared.run_plan_path)
    environment["CLASSIC_CONFORMANCE_OUTPUT"] = str(prepared.receipt_path)
    completed, timeout, launch_error = _run_adapter_command(
        command,
        environment,
        timeout_seconds,
    )

    attempt_path = prepared.artifact_dir / "attempt.json"
    _atomic_write_json(
        attempt_path,
        _attempt_document(
            participant_id,
            command,
            completed,
            timeout,
            launch_error,
        ),
    )
    report = build_conformance_report_from_receipts(
        REPO_ROOT,
        profile="conformance",
        participant_id=participant_id,
        execution_instance_id=participant_id,
        receipt_paths=(prepared.receipt_path,),
        attempt_path=attempt_path,
    )
    report_path = prepared.artifact_dir / "conformance_report.json"
    _atomic_write_json(report_path, report)
    command_passed = (
        completed is not None
        and completed.returncode == 0
        and timeout is None
        and launch_error is None
    )
    result_passed = report["result"] == "pass"
    return (0 if command_passed and result_passed else 1), prepared.artifact_dir


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the private base-slice launcher argument contract."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--participant", choices=sorted(PARTICIPANT_COMMANDS), required=True
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=1_200)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Launch one adapter and print the artifact directory for CI collection."""

    args = build_argument_parser().parse_args(argv)
    try:
        result, artifact_dir = run_participant(
            args.participant,
            artifact_root=args.artifact_root,
            timeout_seconds=args.timeout_seconds,
        )
    except (ConformanceCommandError, PackValidationError, ValueError) as error:
        print(f"Crash Log Scan Run conformance launch failed: {error}", file=sys.stderr)
        return 1
    print(artifact_dir.relative_to(REPO_ROOT).as_posix())
    return result


if __name__ == "__main__":
    raise SystemExit(main())
