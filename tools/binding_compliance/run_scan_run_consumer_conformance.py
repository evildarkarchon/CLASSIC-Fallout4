#!/usr/bin/env python3
"""Run the TUI Crash Log Scan Run consumer and publish a scoped report."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
sys.path.insert(0, str(SCRIPT_PATH.parent))

from conformance.command import (
    ConformanceCommandError,
    build_conformance_report_from_receipts,
)
from conformance.consumers import (
    ConsumerObligationError,
    prepare_consumer_run,
)
from conformance.packs import (
    MaterializationError,
    PackValidationError,
    load_and_validate_pack,
)

PACK_PATH = (
    REPO_ROOT / "tests" / "conformance" / "packs" / "crash_log_scan_run" / "v1.json"
)
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "tools" / "binding_compliance" / "artifacts"
RUN_PLAN_ENV = "CLASSIC_CONSUMER_CONFORMANCE_RUN_PLAN"
OUTPUT_ENV = "CLASSIC_CONSUMER_CONFORMANCE_OUTPUT"
TUI_COMMAND = (
    "cargo",
    "test",
    "-p",
    "classic-tui",
    "--test",
    "scan_run_consumer_conformance",
    "--",
    "--ignored",
    "--exact",
    "writes_tui_scan_run_consumer_receipt",
    "--nocapture",
)


def _atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    """Publish one diagnostic JSON document without exposing partial bytes."""

    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Stop the owned Cargo process and descendants before receipt validation."""

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
            # The process may exit between poll() and killpg().
            pass
        except PermissionError:
            process.kill()
    if process.poll() is None:
        process.kill()
    process.wait()


def _run_tui_command(
    environment: dict[str, str], timeout_seconds: int
) -> tuple[subprocess.CompletedProcess[str] | None, str | None, bool]:
    """Run the bounded Cargo consumer test and retain launch/timeout state."""

    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            TUI_COMMAND,
            cwd=REPO_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags,
            start_new_session=os.name != "nt",
        )
    except OSError as error:
        return None, str(error), False

    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_tree(process)
        stdout, stderr = process.communicate()
    return (
        subprocess.CompletedProcess(
            TUI_COMMAND,
            process.returncode,
            stdout,
            stderr,
        ),
        None,
        timed_out,
    )


def _attempt_document(
    completed: subprocess.CompletedProcess[str] | None,
    launch_error: str | None,
    timed_out: bool,
) -> dict[str, Any]:
    """Return bounded diagnostics for the exact TUI Cargo attempt."""

    return {
        "schemaVersion": 1,
        "participantId": "tui",
        "command": list(TUI_COMMAND),
        "workingDirectory": ".",
        "exitCode": completed.returncode if completed is not None else None,
        "timedOut": timed_out,
        "launchError": launch_error,
        "stdout": completed.stdout if completed is not None else "",
        "stderr": completed.stderr if completed is not None else "",
    }


def run_tui_consumer(
    *,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    timeout_seconds: int = 1_200,
) -> tuple[int, Path]:
    """Execute the maintained TUI seam and build its exact consumer report."""

    pack = load_and_validate_pack(REPO_ROOT, PACK_PATH)
    prepared = prepare_consumer_run(
        pack,
        participant_id="tui",
        execution_instance_id="tui",
        artifact_root=artifact_root,
    )
    environment = os.environ.copy()
    environment[RUN_PLAN_ENV] = str(prepared.run_plan_path)
    environment[OUTPUT_ENV] = str(prepared.receipt_path)
    completed, launch_error, timed_out = _run_tui_command(environment, timeout_seconds)

    attempt_path = prepared.artifact_dir / "attempt.json"
    _atomic_write_json(
        attempt_path,
        _attempt_document(completed, launch_error, timed_out),
    )
    report = build_conformance_report_from_receipts(
        REPO_ROOT,
        profile="conformance",
        participant_id="tui",
        execution_instance_id="tui",
        receipt_paths=(prepared.receipt_path,),
        attempt_path=attempt_path,
    )
    report_path = prepared.artifact_dir / "conformance_report.json"
    _atomic_write_json(report_path, report)

    command_passed = (
        completed is not None
        and completed.returncode == 0
        and launch_error is None
        and not timed_out
    )
    return (
        0 if command_passed and report["result"] == "pass" else 1,
        prepared.artifact_dir,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the private TUI-only consumer launcher argument contract."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", choices=("tui",), required=True)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=1_200)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Launch the TUI consumer and print its artifact directory."""

    args = build_argument_parser().parse_args(argv)
    try:
        result, artifact_dir = run_tui_consumer(
            artifact_root=args.artifact_root,
            timeout_seconds=args.timeout_seconds,
        )
    except (
        ConformanceCommandError,
        ConsumerObligationError,
        MaterializationError,
        PackValidationError,
        OSError,
        ValueError,
    ) as error:
        print(f"TUI consumer conformance launch failed: {error}", file=sys.stderr)
        return 1
    print(artifact_dir.relative_to(REPO_ROOT).as_posix())
    return result


if __name__ == "__main__":
    raise SystemExit(main())
