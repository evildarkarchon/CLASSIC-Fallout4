"""Tests for method-aware Python parity tooling."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATE_BASELINE_PATH = (
    REPO_ROOT / "tools" / "python_api_parity" / "generate_baseline.py"
)


def load_generate_baseline_module():
    spec = importlib.util.spec_from_file_location(
        "python_api_parity_generate_baseline", GENERATE_BASELINE_PATH
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_python_surface_tracks_method_export_paths(tmp_path, monkeypatch) -> None:
    module = load_generate_baseline_module()

    stub_path = tmp_path / "sample_module.pyi"
    stub_path.write_text(
        "\n".join(
            (
                "class Demo:",
                "    @staticmethod",
                "    def from_content(raw: str, mode: str) -> Demo: ...",
                "",
                "    def parse(self, text: str) -> bool: ...",
                "",
                "def top_level(name: str) -> str: ...",
            )
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        module, "PYTHON_TARGET_MODULES", {"sample_module": "sample_module.pyi"}
    )
    monkeypatch.setattr(module, "PYTHON_OWNER_BY_MODULE", {"sample_module": "scanlog"})

    manifest = module.parse_python_surface(
        tmp_path,
        {"Demo", "Demo.from_content", "Demo.parse", "top_level"},
    )
    exports = {
        (entry["module"], entry["export_path"]): entry for entry in manifest["exports"]
    }

    assert ("sample_module", "Demo") in exports
    assert ("sample_module", "Demo.from_content") in exports
    assert ("sample_module", "Demo.parse") in exports
    assert ("sample_module", "top_level") in exports
    assert exports[("sample_module", "Demo.from_content")]["kind"] == "method"
    assert exports[("sample_module", "Demo.from_content")]["arity"] == 2
    assert exports[("sample_module", "Demo.parse")]["arity"] == 1
    assert exports[("sample_module", "top_level")]["kind"] == "function"


def test_generate_diff_report_matches_python_export_paths() -> None:
    module = load_generate_baseline_module()

    contract = {
        "tier1Mappings": [
            {
                "id": "demo-static-factory",
                "tier": "tier1",
                "ownerModule": "scanlog",
                "rustSymbol": "Demo",
                "pythonModule": "sample_module",
                "pythonExportPath": "Demo.from_content",
                "pythonKind": "method",
                "pythonArity": 2,
            }
        ]
    }
    rust_manifest = {
        "symbols": [
            {
                "symbol": "Demo",
                "kind": "reexport",
                "crate": "classic-scanlog-core",
                "owner_module": "scanlog",
                "source_file": "sample.rs",
            }
        ]
    }
    python_manifest = {
        "exports": [
            {
                "module": "sample_module",
                "export": "Demo",
                "export_path": "Demo",
                "kind": "class",
                "owner_module": "scanlog",
            },
            {
                "module": "sample_module",
                "export": "from_content",
                "export_path": "Demo.from_content",
                "kind": "method",
                "arity": 2,
                "owner_module": "scanlog",
            },
        ]
    }

    report = module.generate_diff_report(contract, rust_manifest, python_manifest)

    assert report["contract_results"][0]["status"] == "matched"


def test_generate_diff_report_flags_missing_contract_python_export_identifier() -> None:
    module = load_generate_baseline_module()

    contract = {
        "tier1Mappings": [
            {
                "id": "demo-missing-python-export",
                "tier": "tier1",
                "ownerModule": "scanlog",
                "rustSymbol": "Demo",
                "pythonModule": "sample_module",
                "pythonKind": "function",
            }
        ]
    }
    rust_manifest = {
        "symbols": [
            {
                "symbol": "Demo",
                "kind": "reexport",
                "crate": "classic-scanlog-core",
                "owner_module": "scanlog",
                "source_file": "sample.rs",
            }
        ]
    }
    python_manifest = {
        "exports": [
            {
                "module": "sample_module",
                "export": "top_level",
                "export_path": "top_level",
                "kind": "function",
                "arity": 0,
                "owner_module": "scanlog",
            }
        ]
    }

    report = module.generate_diff_report(contract, rust_manifest, python_manifest)

    assert report["contract_results"][0]["status"] == "missing_python"
    assert report["contract_results"][0]["reason"] == (
        "Tier-1 mapping is missing a Python export identifier "
        "(`pythonExportPath` or legacy `pythonExport`)."
    )
    assert report["gaps"][0]["gap_type"] == "tier1_missing_python"
    assert report["gaps"][1]["gap_type"] == "python_unmapped"


def test_expand_pub_use_statement_does_not_reannotate_alias_name() -> None:
    module_ast = ast.parse(GENERATE_BASELINE_PATH.read_text(encoding="utf-8"))

    expand_function = next(
        node
        for node in module_ast.body
        if isinstance(node, ast.FunctionDef) and node.name == "expand_pub_use_statement"
    )
    alias_annotations = [
        node
        for node in ast.walk(expand_function)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "alias_name"
    ]

    assert len(alias_annotations) <= 1
