"""Unicode output guard coverage for PyO3 binding imports."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_BINDING_MODULES = [
    "classic_config",
    "classic_database",
    "classic_file_io",
    "classic_message",
    "classic_path",
    "classic_perf",
    "classic_registry",
    "classic_resource",
    "classic_scangame",
    "classic_scanlog",
    "classic_settings",
    "classic_shared",
    "classic_update",
    "classic_version",
    "classic_version_registry",
    "classic_web",
    "classic_xse",
]


def _run_with_strict_cp1252_stdio(script: str) -> subprocess.CompletedProcess[bytes]:
    """Run Python with a legacy strict stdout encoding."""

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252:strict"
    env["PYTHONUTF8"] = "0"
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


@pytest.mark.parametrize("module_name", PYTHON_BINDING_MODULES)
def test_binding_import_makes_legacy_stdio_safe(module_name: str) -> None:
    """Each binding module applies the shared import-time stdout/stderr guard."""

    completed = _run_with_strict_cp1252_stdio(
        "import importlib, sys\n"
        f"importlib.import_module({module_name!r})\n"
        "assert sys.stdout.errors == 'backslashreplace', sys.stdout.errors\n"
        "print('INFO ✅')\n"
    )

    assert completed.returncode == 0, completed.stderr.decode("ascii", errors="backslashreplace")
    assert completed.stdout.decode("ascii").splitlines() == ["INFO \\u2705"]


def test_classic_message_import_makes_emoji_output_safe_on_legacy_stdio() -> None:
    """The binding keeps Unicode strings intact but makes legacy printing safe."""

    completed = _run_with_strict_cp1252_stdio(
        "import classic_message\n"
        "text = classic_message.format_log_message('INFO ✅', 'test message 🎉')\n"
        "assert text == 'INFO ✅\\nDetails: test message 🎉'\n"
        "print(text)\n"
    )

    assert completed.returncode == 0, completed.stderr.decode("ascii", errors="backslashreplace")
    assert completed.stdout.decode("ascii").splitlines() == [
        "INFO \\u2705",
        "Details: test message \\U0001f389",
    ]
