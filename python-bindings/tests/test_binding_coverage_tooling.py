"""Tests for shared binding runtime coverage tooling."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO_ROOT / "tools" / "binding_parity_runtime_coverage.py"
PYTHON_RUNTIME_REGISTRY = (
    REPO_ROOT
    / "python-bindings"
    / "tests"
    / "fixtures"
    / "runtime_coverage_registry.json"
)


def load_tool_module():
    spec = importlib.util.spec_from_file_location(
        "binding_parity_runtime_coverage", TOOL_PATH
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_coverage_summary_classifies_runtime_and_newly_uncovered() -> None:
    module = load_tool_module()

    contract = {
        "tier1Mappings": [
            {
                "id": "scanlog-parser",
                "tier": "tier1",
                "ownerModule": "scanlog",
                "rustSymbol": "LogParser",
                "nodeExport": "parseLogSegments",
            }
        ]
    }
    diff_report = {
        "contract_results": [
            {
                "id": "scanlog-parser",
                "tier": "tier1",
                "owner_module": "scanlog",
                "rust_symbol": "LogParser",
                "node_export": "parseLogSegments",
                "status": "matched",
            }
        ],
        "gaps": [
            {
                "gap_type": "node_unmapped",
                "tier": "tier2",
                "owner_module": "aux",
                "rust_symbol": None,
                "node_export": "JsLogger",
            },
            {
                "gap_type": "node_unmapped",
                "tier": "tier2",
                "owner_module": "aux",
                "rust_symbol": None,
                "node_export": "FutureExport",
            },
        ],
    }
    runtime_registry = {
        "entries": [
            {
                "coverageId": "node-tier1-scanlog",
                "contractIds": ["scanlog-parser"],
                "classification": "runtime_verified",
                "verificationMode": "direct_call",
                "testSuite": "node/__test__/parity_tier1.spec.ts",
                "testCaseId": "scanlog-tier1",
            }
        ]
    }

    summary = module.build_coverage_summary(
        binding="node",
        contract=contract,
        diff_report=diff_report,
        runtime_registry=runtime_registry,
    )

    assert summary["summary"]["runtime_verified_total"] == 1
    assert summary["summary"]["newly_uncovered_total"] == 2
    assert summary["summary"]["tier1_missing_runtime_total"] == 0

    classifications = {
        item["trackedId"]: item["classification"] for item in summary["trackedSurface"]
    }
    assert classifications["contract:scanlog-parser"] == "runtime_verified"
    assert classifications["binding:JsLogger"] == "newly_uncovered"
    assert classifications["binding:FutureExport"] == "newly_uncovered"


def test_build_coverage_summary_flags_tier1_rows_without_runtime_metadata() -> None:
    module = load_tool_module()

    contract = {
        "tier1Mappings": [
            {
                "id": "config-main",
                "tier": "tier1",
                "ownerModule": "config",
                "rustSymbol": "YamlDataCore",
                "pythonModule": "classic_config",
                "pythonExportPath": "YamlData.from_yaml_content",
            }
        ]
    }
    diff_report = {
        "contract_results": [
            {
                "id": "config-main",
                "tier": "tier1",
                "owner_module": "config",
                "rust_symbol": "YamlDataCore",
                "python_module": "classic_config",
                "python_export_path": "YamlData.from_yaml_content",
                "status": "matched",
            }
        ],
        "gaps": [],
    }

    summary = module.build_coverage_summary(
        binding="python",
        contract=contract,
        diff_report=diff_report,
        runtime_registry={"entries": []},
    )

    assert summary["summary"]["tier1_missing_runtime_total"] == 1
    assert summary["summary"]["contract_mapped_total"] == 1
    assert summary["trackedSurface"][0]["classification"] == "contract_mapped"
    assert summary["trackedSurface"][0]["status"] == "matched"


def test_build_coverage_summary_reports_selector_snapshot_mismatch() -> None:
    module = load_tool_module()

    contract = {
        "tier1Mappings": [
            {
                "id": "aux-runtime-info",
                "tier": "tier1",
                "ownerModule": "aux",
                "rustSymbol": "RuntimeInfo",
                "nodeExport": "getRuntimeInfo",
            }
        ]
    }
    diff_report = {
        "contract_results": [
            {
                "id": "aux-runtime-info",
                "tier": "tier1",
                "owner_module": "aux",
                "rust_symbol": "RuntimeInfo",
                "node_export": "getRuntimeInfo",
                "status": "matched",
            }
        ],
        "gaps": [],
    }

    summary = module.build_coverage_summary(
        binding="node",
        contract=contract,
        diff_report=diff_report,
        runtime_registry={
            "entries": [
                {
                    "coverageId": "node-tier1-aux",
                    "classification": "runtime_verified",
                    "contractSelector": {"ownerModule": "aux", "tier": "tier1"},
                    "contractCount": 2,
                    "contractIdsHash": "mismatch",
                }
            ]
        },
    )

    assert summary["summary"]["registry_mismatch_total"] == 1
    assert summary["summary"]["tier1_missing_runtime_total"] == 1


def test_python_runtime_registry_tracks_application_dir_surfaces() -> None:
    registry = json.loads(PYTHON_RUNTIME_REGISTRY.read_text(encoding="utf-8"))
    binding_identifiers = {
        binding_identifier
        for entry in registry["entries"]
        for binding_identifier in entry.get("bindingIdentifiers", [])
    }

    assert "classic_config.get_application_dir" in binding_identifiers
    assert "classic_config.set_application_dir" in binding_identifiers
