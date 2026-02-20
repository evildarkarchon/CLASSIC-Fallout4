"""Entry-point contract tests.

These tests lock in the externally visible entry-point experience so that
internal refactors do not change script targets or top-level callable names.
"""

import inspect
import tomllib
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]


def test_console_script_targets_are_stable() -> None:
    """Ensure console script mappings remain stable."""
    pyproject_path = Path("pyproject.toml")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]

    expected = {
        "classic": "classic_interface:main",
        "classic-gui": "classic_interface:main",
        "classic-tui": "ClassicLib.TUI:main",
        "classic-cli": "classic_scanlogs:main",
        "classic-scan": "classic_scangame:main",
    }

    assert scripts == expected


@pytest.mark.parametrize(
    ("module_name", "callable_name"),
    [
        ("classic_interface", "main"),
        ("classic_scanlogs", "main"),
        ("classic_scangame", "main"),
        ("ClassicLib.TUI", "main"),
    ],
)
def test_entrypoint_callables_exist(module_name: str, callable_name: str) -> None:
    """Ensure expected module-level entry-point callables are present."""
    module = __import__(module_name, fromlist=[callable_name])
    entrypoint = getattr(module, callable_name)

    assert callable(entrypoint)
    signature = inspect.signature(entrypoint)
    assert len(signature.parameters) == 0
