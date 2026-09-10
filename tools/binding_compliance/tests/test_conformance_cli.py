"""Behavior tests for the canonical conformance command-line contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import check_compliance  # type: ignore
import pytest
from check_compliance import (  # type: ignore
    _argument_error,
    build_argument_parser,
    main,
)
from conformance.command import _diagnostic_failures


def test_conformance_cli_exposes_the_native_receipt_contract() -> None:
    """One native job can name its exact participant and companion artifacts."""

    args = build_argument_parser().parse_args(
        [
            "--profile",
            "conformance",
            "--participant",
            "cxx",
            "--execution-instance",
            "windows-msvc",
            "--receipt",
            "receipt.json",
            "--receipt",
            "second-receipt.json",
            "--attempt",
            "attempt.json",
            "--junit",
            "ctest.junit.xml",
        ]
    )

    assert args.receipt == ["receipt.json", "second-receipt.json"]
    assert _argument_error(args) is None


def test_conformance_cli_requires_participant_and_receipt() -> None:
    """A scope label alone cannot create a passing native conformance job."""

    missing_participant = build_argument_parser().parse_args(
        ["--profile", "conformance", "--receipt", "receipt.json"]
    )
    missing_receipt = build_argument_parser().parse_args(
        ["--profile", "conformance", "--participant", "node"]
    )

    assert "--participant" in str(_argument_error(missing_participant))
    assert "--receipt" in str(_argument_error(missing_receipt))


def test_cxx_conformance_requires_attempt_and_junit_companions() -> None:
    """Native CXX receipt validation retains command and JUnit diagnostics."""

    args = build_argument_parser().parse_args(
        [
            "--profile",
            "conformance",
            "--participant",
            "cxx",
            "--receipt",
            "receipt.json",
        ]
    )

    assert "--attempt and --junit" in str(_argument_error(args))


def test_public_main_returns_nonzero_for_a_blocking_scoped_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The supported command seam propagates a promoted report failure."""

    monkeypatch.setattr(
        check_compliance,
        "build_conformance_report_from_receipts",
        lambda *_args, **_kwargs: {
            "schemaVersion": 1,
            "enforcement": "blocking",
            "result": "fail",
            "failures": [{"kind": "missing_receipt"}],
        },
    )

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--output-dir",
            "artifacts",
            "--profile",
            "conformance",
            "--participant",
            "rust",
            "--receipt",
            "missing-receipt.json",
        ]
    )

    assert exit_code == 1


def _write_cxx_attempt(
    root: Path, *, stdout: str = "", stderr: str = "", exit_code: int = 1
) -> Path:
    """Write one digest-bound failing native attempt for classification tests."""

    stdout_path = root / "stdout.log"
    stderr_path = root / "stderr.log"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    attempt_path = root / "attempt.json"
    attempt_path.write_text(
        json.dumps(
            {
                "launchError": None,
                "timedOut": False,
                "exitCode": exit_code,
                "stdout": {
                    "path": str(stdout_path.resolve()),
                    "sha256": hashlib.sha256(stdout_path.read_bytes()).hexdigest(),
                },
                "stderr": {
                    "path": str(stderr_path.resolve()),
                    "sha256": hashlib.sha256(stderr_path.read_bytes()).hexdigest(),
                },
            }
        ),
        encoding="utf-8",
    )
    return attempt_path


def test_cxx_attempt_classifies_wrapper_prerequisite_output_as_local_environment(
    tmp_path: Path,
) -> None:
    """A started pwsh process can still fail because its toolchain is absent."""

    outputs = (
        "Missing required tool: clang-cl.exe\nBuild prerequisites are missing.\n",
        "CMake Error: Could not find toolchain file: D:/missing/vcpkg.cmake\n",
        "CMake Error: Could not resolve link.exe from CMAKE_LINKER, the compiler directory, or PATH.\n",
        "CMake Error: Resolved linker is NOT an MSVC-compatible linker.\n",
    )
    for output in outputs:
        attempt_path = _write_cxx_attempt(tmp_path, stdout=output)
        failures = _diagnostic_failures(
            tmp_path,
            participant_id="cxx",
            execution_instance_id="windows-clang-cl",
            attempt_path=attempt_path,
            junit_path=None,
        )

        assert [failure.kind.value for failure in failures] == [
            "local_environment_failure"
        ]


def test_cxx_attempt_keeps_adapter_failures_distinct_from_toolchain_failures(
    tmp_path: Path,
) -> None:
    """Ordinary native compile/test errors remain adapter command failures."""

    attempt_path = _write_cxx_attempt(
        tmp_path,
        stderr="classic_cxx_conformance.cpp(42): error C2065: undeclared identifier\n",
    )

    failures = _diagnostic_failures(
        tmp_path,
        participant_id="cxx",
        execution_instance_id="windows-msvc",
        attempt_path=attempt_path,
        junit_path=None,
    )

    assert [failure.kind.value for failure in failures] == ["adapter_command_failure"]


def test_cxx_attempt_rejects_output_changed_after_finalization(tmp_path: Path) -> None:
    """Only the log bytes authenticated by attempt.json may affect classification."""

    attempt_path = _write_cxx_attempt(
        tmp_path,
        stdout="Missing required tool: clang-cl.exe\n",
        exit_code=0,
    )
    (tmp_path / "stdout.log").write_text("changed after hashing", encoding="utf-8")

    failures = _diagnostic_failures(
        tmp_path,
        participant_id="cxx",
        execution_instance_id="windows-clang-cl",
        attempt_path=attempt_path,
        junit_path=None,
    )

    assert [failure.kind.value for failure in failures] == ["adapter_command_failure"]
    assert "SHA-256" in failures[0].message
