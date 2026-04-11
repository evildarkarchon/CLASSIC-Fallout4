"""Tests for Node/Python parity gate baseline refresh behavior."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
NODE_CHECK_PARITY_GATE = (
    REPO_ROOT / "tools" / "node_api_parity" / "check_parity_gate.py"
)
PYTHON_CHECK_PARITY_GATE = (
    REPO_ROOT / "tools" / "python_api_parity" / "check_parity_gate.py"
)


def load_module(module_name: str, module_path: Path):
    original_generate_baseline = sys.modules.pop("generate_baseline", None)
    original_sys_path = list(sys.path)

    try:
        sys.path.insert(0, str(module_path.parent.parent))
        sys.path.insert(0, str(module_path.parent))
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        assert spec is not None
        assert spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = original_sys_path
        if original_generate_baseline is None:
            sys.modules.pop("generate_baseline", None)
        else:
            sys.modules["generate_baseline"] = original_generate_baseline


def test_load_module_restores_import_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_dir = tmp_path / "tools" / "python_api_parity"
    module_dir.mkdir(parents=True)
    module_path = module_dir / "temp_module.py"
    module_path.write_text("VALUE = 1\n", encoding="utf-8")

    original_sys_path = list(sys.path)
    original_generate_baseline = types.ModuleType("generate_baseline")
    monkeypatch.setitem(sys.modules, "generate_baseline", original_generate_baseline)

    try:
        module = load_module("temp_module", module_path)

        assert module.VALUE == 1
        assert sys.path == original_sys_path
        assert sys.modules["generate_baseline"] is original_generate_baseline
    finally:
        sys.path[:] = original_sys_path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def minimal_diff_report(binding: str) -> dict:
    summary = {
        "tier1_contract_total": 0,
        "tier1_matched": 0,
        "tier1_missing_rust": 0,
        "tier1_signature_mismatch": 0,
        "total_gaps": 0,
    }
    if binding == "node":
        summary["tier1_missing_node"] = 0
    else:
        summary["tier1_missing_python"] = 0

    return {
        "generated_at_utc": "2026-03-27T00:00:00+00:00",
        "summary": summary,
        "contract_results": [],
        "gaps": [],
        "gap_counts_by_owner_tier": {},
    }


def minimal_coverage_summary(binding: str) -> dict:
    return {
        "generated_at_utc": "2026-03-27T00:00:00+00:00",
        "binding": binding,
        "summary": {
            "tracked_surface_total": 0,
            "runtime_verified_total": 0,
            "contract_mapped_total": 0,
            "deferred_total": 0,
            "newly_uncovered_total": 0,
            "tier1_missing_runtime_total": 0,
            "registry_mismatch_total": 0,
        },
        "perOwnerModule": {},
        "trackedSurface": [],
        "registryMismatches": [],
    }


@pytest.mark.parametrize(
    ("binding", "module_path", "module_name"),
    [
        ("node", NODE_CHECK_PARITY_GATE, "node_check_parity_gate"),
        ("python", PYTHON_CHECK_PARITY_GATE, "python_check_parity_gate"),
    ],
)
def test_update_baseline_flag_refreshes_stale_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binding: str,
    module_path: Path,
    module_name: str,
) -> None:
    module = load_module(module_name, module_path)

    contract_rel = "contract.json"
    runtime_rel = "runtime_registry.json"
    output_rel = "generated"
    baseline_rel = "baseline"

    write_json(tmp_path / contract_rel, {"tier1Mappings": []})
    write_json(tmp_path / runtime_rel, {"entries": []})

    if binding == "node":
        index_dts_rel = "index.d.ts"
        (tmp_path / index_dts_rel).write_text("export {}\n", encoding="utf-8")
        monkeypatch.setattr(
            module, "parse_node_surface", lambda *args, **kwargs: {"exports": []}
        )
    else:
        index_dts_rel = None
        monkeypatch.setattr(
            module, "parse_python_surface", lambda *args, **kwargs: {"exports": []}
        )

    monkeypatch.setattr(
        module, "parse_rust_surface", lambda *args, **kwargs: {"symbols": []}
    )
    monkeypatch.setattr(
        module,
        "generate_diff_report",
        lambda *args, **kwargs: minimal_diff_report(binding),
    )
    monkeypatch.setattr(
        module,
        "build_coverage_summary",
        lambda *args, **kwargs: minimal_coverage_summary(binding),
    )

    stale_baseline = tmp_path / baseline_rel / "parity_diff_report.json"
    write_json(stale_baseline, {"generated_at_utc": "old", "summary": {"stale": True}})

    argv = [
        module_path.name,
        "--repo-root",
        str(tmp_path),
        "--contract",
        contract_rel,
        "--output-dir",
        output_rel,
        "--runtime-registry",
        runtime_rel,
        "--baseline-output-dir",
        baseline_rel,
        "--update-baseline",
    ]
    if index_dts_rel is not None:
        argv.extend(["--index-dts", index_dts_rel])

    monkeypatch.setattr(sys, "argv", argv)

    assert module.main() == 0

    generated_report = json.loads(
        (tmp_path / output_rel / "parity_diff_report.json").read_text(encoding="utf-8")
    )
    baseline_report = json.loads(
        (tmp_path / baseline_rel / "parity_diff_report.json").read_text(
            encoding="utf-8"
        )
    )
    generated_report.pop("generated_at_utc", None)
    baseline_report.pop("generated_at_utc", None)
    assert baseline_report == generated_report
