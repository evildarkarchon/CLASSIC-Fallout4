"""Adoption checks for async runtime boundary helpers."""

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]


TARGET_FILES = [
    Path("ClassicLib/support/docs_path.py"),
    Path("ClassicLib/support/xse.py"),
    Path("ClassicLib/scanning/game/wrye_check.py"),
    Path("ClassicLib/Interface/controllers/results_viewer.py"),
]


@pytest.mark.parametrize("target", TARGET_FILES)
def test_target_uses_runtime_boundary_helper(target: Path) -> None:
    """Target modules should import and call run_sync helper."""
    tree = ast.parse(target.read_text(encoding="utf-8"))

    has_runtime_import = False
    has_bridge_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "ClassicLib.core.async_runtime":
                imported_names = {alias.name for alias in node.names}
                if "run_sync" in imported_names:
                    has_runtime_import = True
            if node.module == "ClassicLib.core.async_bridge":
                has_bridge_import = True

    run_sync_calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "run_sync"]

    assert has_runtime_import
    assert not has_bridge_import
    assert run_sync_calls
