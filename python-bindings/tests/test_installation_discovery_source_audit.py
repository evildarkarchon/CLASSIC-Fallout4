"""Retained structural evidence for platform discovery without host execution.

This analyzer proves ordering and delegation only. It never claims that a live
Windows registry, Steam installation, or home directory was discovered correctly.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_valid_cached_paths_return_before_platform_discovery() -> None:
    """Keep fixture-backed smoke calls ahead of the non-injectable OS fallback."""
    cases = (
        (
            "docs_path.rs",
            "pub fn find_docs_path(",
            "return Ok(cached_path);",
            "self.find_docs_path_windows()",
        ),
        (
            "game_path.rs",
            "pub fn find_game_path(",
            "return Ok(path.to_path_buf());",
            "self.find_via_registry()",
        ),
    )
    for name, method, returned, fallback in cases:
        source = (ROOT / "business-logic/classic-path-core/src" / name).read_text()
        body = source[source.index(method) :]
        assert (
            body.index("self.validate_") < body.index(returned) < body.index(fallback)
        )


def test_platform_discovery_retains_native_owner_delegation() -> None:
    """Retain source ownership evidence without inventing registry runtime facts."""
    owner = ROOT / "business-logic/classic-path-core/src"
    game = (owner / "game_path.rs").read_text()
    docs = (owner / "docs_path.rs").read_text()
    assert "query_game_registry(&self.game_name, vr_suffix, try_gog)?" in game
    assert "get_documents_path().map_err" in docs
    binding = (ROOT / "python-bindings/classic-path-py/src/lib.rs").read_text()
    assert ".find_game_path(cached.as_deref(), xse_log.as_deref())" in binding
    assert ".find_docs_path(cached_path.as_deref())" in binding
    xse = (ROOT / "business-logic/classic-xse-core/src/lib.rs").read_text()
    resolver = xse[xse.index("pub fn resolve_xse_folder_for_scan(") :]
    assert resolver.index(
        "configured_docs_root.and_then(non_empty_path)"
    ) < resolver.index("discover_xse_folder(version_info)")
    version = xse[
        xse.index("fn resolve_version_info(") : xse.index("fn clean_path_value(")
    ]
    assert version.index(
        'if !matches!(game, "Fallout4" | "Fallout4VR")'
    ) < version.index("return None;")
    fallback = xse[xse.index("fn discover_xse_folder(") :]
    assert fallback.index("let info = version_info?;") < fallback.index(
        "DocsPathFinder::new(relative_docs)"
    )
    assert "finder.find_docs_path(None)" in fallback


def test_discovery_smoke_requires_explicit_paths_and_propagates_failures() -> None:
    """Reject accidental reintroduction of host probes or swallowed call errors."""
    source = (
        ROOT / "python-bindings/tests/test_promoted_residuals_smoke.py"
    ).read_text()
    tree = ast.parse(source)
    selected = {
        "test_path_docs_path_finder_construct_and_find": "find_docs_path",
        "test_path_game_path_finder_construct_and_find": "find_game_path",
        "test_path_documents_checker_construct_and_run_checks": "run_all_checks",
    }
    for function in tree.body:
        if not isinstance(function, ast.FunctionDef) or function.name not in selected:
            continue
        method = selected.pop(function.name)
        nodes = list(ast.walk(function))
        assert not any(isinstance(node, ast.ExceptHandler) for node in nodes)
        calls = [
            node
            for node in nodes
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == method
        ]
        assert len(calls) == 1
        call = calls[0]
        if method == "run_all_checks":
            assert len(call.args) == 1 and isinstance(call.args[0], ast.Name)
            assert call.args[0].id == "directory"
        else:
            cached = next(
                keyword.value
                for keyword in call.keywords
                if keyword.arg == "cached_path"
            )
            assert isinstance(cached, ast.Name) and cached.id == "directory"
        assert any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "TemporaryDirectory"
            for node in nodes
        )
    assert not selected
