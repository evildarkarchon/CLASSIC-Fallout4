"""Worker runtime contract tests.

These tests protect the GUI threading model by ensuring QThread workers keep
using ``asyncio.run(...)`` and do not call ``AsyncBridge.run_async(...)``.
"""

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]


def _load_workers_tree() -> ast.Module:
    workers_path = Path("ClassicLib/Interface/workers/Workers.py")
    return ast.parse(workers_path.read_text(encoding="utf-8"))


def test_workers_module_does_not_import_asyncbridge() -> None:
    """Workers must not depend on AsyncBridge (cross-thread hazard)."""
    tree = _load_workers_tree()

    import_from_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    async_bridge_imports = [n for n in import_from_nodes if n.module == "ClassicLib.core.async_bridge"]

    assert async_bridge_imports == []


def test_workers_module_uses_asyncio_run_calls() -> None:
    """Workers should use ``asyncio.run`` in their QThread execution paths."""
    tree = _load_workers_tree()

    asyncio_run_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "asyncio"
    ]

    # CrashLogsScanWorker, GameFilesScanWorker, UpdateCheckWorker
    assert len(asyncio_run_calls) == 3


def test_workers_module_does_not_call_bridge_run_async() -> None:
    """Workers should never call bridge run_async from a QThread."""
    tree = _load_workers_tree()

    run_async_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run_async"
    ]

    assert run_async_calls == []
