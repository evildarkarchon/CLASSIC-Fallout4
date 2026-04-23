"""Unit tests for the ``check_dts_freshness`` helper.

These tests lock the intended behavior after the git-diff-based approach:

- freshness verification regenerates ``index.d.ts`` into a temporary output
  directory rather than mutating the tracked file in place
- freshness compares file contents directly, normalizing line endings so
  Windows CRLF vs LF alone does not report false drift
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import check_dts_freshness as freshness


def _completed(
    command: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        command,
        returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_main_uses_temp_generated_dts_and_normalizes_line_endings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Freshness should be content-based, not git-diff-based.

    The tracked file uses CRLF while the temp-generated file uses LF. That
    should still pass because the declaration content is otherwise identical.
    """

    repo_root = tmp_path / "repo"
    package_dir = repo_root / "node-bindings" / "classic-node"
    output_dir = package_dir / "parity-artifacts"
    package_dir.mkdir(parents=True)

    (package_dir / "index.d.ts").write_bytes(
        b"export declare const value: number;\r\n"
    )

    commands: list[list[str]] = []

    def fake_run_command(
        command: list[str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert cwd == package_dir
        assert command[:3] == ["bun", "x", "napi"], command
        assert "--output-dir" in command, command
        assert "--dts" in command, command
        assert "git" not in command, command

        out_dir = Path(command[command.index("--output-dir") + 1])
        dts_name = command[command.index("--dts") + 1]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / dts_name).write_bytes(
            b"export declare const value: number;\n"
        )
        return _completed(command)

    monkeypatch.setattr(freshness, "run_command", fake_run_command)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_dts_freshness.py", "--repo-root", str(repo_root)],
    )

    assert freshness.main() == 0

    report = json.loads(
        (output_dir / "dts_freshness_report.json").read_text(encoding="utf-8")
    )
    assert report["fresh"] is True
    assert (output_dir / "index_dts.diff").read_text(encoding="utf-8") == ""
    assert commands != []
