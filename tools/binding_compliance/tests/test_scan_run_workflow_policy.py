"""Behavior tests for the promoted Crash Log Scan Run CI topology."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from conformance.workflow_policy import (
    WorkflowPolicyError,
    validate_scan_run_workflow_policy,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_repository_workflows_keep_every_promoted_execution_blocking() -> None:
    """Legacy and receipt gates dual-run while diagnostics always upload."""

    validate_scan_run_workflow_policy(REPO_ROOT)


@pytest.mark.parametrize(
    ("relative_path", "needle", "replacement", "message"),
    (
        (
            ".github/workflows/ci-rust.yml",
            "run: python tools/binding_compliance/run_scan_run_conformance.py --participant rust",
            "continue-on-error: true\n        run: python tools/binding_compliance/run_scan_run_conformance.py --participant rust",
            "launcher must be blocking",
        ),
        (
            ".github/workflows/ci-cpp.yml",
            "compiler: [msvc, clang-cl]",
            "compiler: [msvc]",
            "missing exact required matrix",
        ),
        (
            ".github/workflows/ci-cpp.yml",
            "timeout-minutes: 180",
            "timeout-minutes: 120",
            "must reserve 180 minutes",
        ),
        (
            ".github/workflows/ci-cpp.yml",
            "compiler: [msvc, clang-cl]",
            "compiler: [msvc, clang-cl]\n        exclude:\n          - compiler: clang-cl",
            "matrix cannot exclude required executions",
        ),
        (
            ".github/workflows/ci-python-bindings.yml",
            "needs: [parity-gates]",
            "needs: [parity-gates]\n    if: false",
            "job must run after upstream failures unless cancelled",
        ),
        (
            ".github/workflows/ci-cpp.yml",
            "run_cxx_conformance.ps1 -Compiler ${{ matrix.compiler }}",
            "run_cxx_conformance.ps1 -Compiler ${{ matrix.compiler }} --profile full",
            "cannot claim full-repository scope",
        ),
        (
            ".github/workflows/ci-python-bindings.yml",
            "- name: Upload Python Crash Log Scan Run conformance diagnostics\n        if: always()",
            "- name: Upload Python Crash Log Scan Run conformance diagnostics\n        if: success()",
            "diagnostics must upload even on failure",
        ),
        (
            ".github/workflows/ci-rust.yml",
            "Run Rust tests with all features",
            "Run Rust tests without conformance",
            "missing a required marker",
        ),
        (
            ".github/workflows/ci-rust.yml",
            "- name: Validate Crash Log Scan Run variant coverage\n        if: ${{ !cancelled() }}",
            "- name: Validate Crash Log Scan Run variant coverage\n        if: success()",
            "variant preflight must run after earlier failures unless cancelled",
        ),
        (
            ".github/workflows/ci-typescript.yml",
            "runtime: [bun, node]\n    env:\n      RUST_BACKTRACE: full\n    steps:\n      - uses: actions/checkout@v6",
            "runtime: [bun, node]\n    env:\n      RUST_BACKTRACE: full\n    steps:\n      - uses: actions/checkout@v6\n        with:\n          ref: classic-next",
            "cannot replace the event source revision",
        ),
        (
            ".github/workflows/ci-cpp.yml",
            "run_gui_consumer_conformance.ps1",
            "run_removed_gui_consumer_conformance.ps1",
            "missing a required marker",
        ),
    ),
)
def test_workflow_policy_rejects_weakened_topology(
    tmp_path: Path,
    relative_path: str,
    needle: str,
    replacement: str,
    message: str,
) -> None:
    """Each reviewed topology property fails closed when mutated."""

    workflow_root = tmp_path / ".github" / "workflows"
    workflow_root.parent.mkdir(parents=True)
    shutil.copytree(REPO_ROOT / ".github" / "workflows", workflow_root)
    path = tmp_path / relative_path
    source = path.read_text(encoding="utf-8")
    assert needle in source
    path.write_text(source.replace(needle, replacement, 1), encoding="utf-8")

    with pytest.raises(WorkflowPolicyError, match=message):
        validate_scan_run_workflow_policy(tmp_path)
