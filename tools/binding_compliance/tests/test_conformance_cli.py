"""Behavior tests for the canonical conformance command-line contract."""

from __future__ import annotations

from check_compliance import _argument_error, build_argument_parser  # type: ignore


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
