"""Tests for shared binding runtime coverage tooling."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_PATH = REPO_ROOT / "tools" / "binding_parity_runtime_coverage.py"


def load_tool_module():
    spec = importlib.util.spec_from_file_location(
        "binding_parity_runtime_coverage", TOOL_PATH
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_coverage_summary_classifies_runtime_deferred_and_new() -> None:
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
    deferred_registry = {
        "entries": [
            {
                "coverageId": "node-aux-deferred-logger",
                "bindingIdentifiers": ["JsLogger"],
                "classification": "deferred",
                "ownerModule": "aux",
                "wave": "wave4",
                "deferReason": "Low-priority utility surface",
            }
        ]
    }

    summary = module.build_coverage_summary(
        binding="node",
        contract=contract,
        diff_report=diff_report,
        runtime_registry=runtime_registry,
        deferred_registry=deferred_registry,
    )

    assert summary["summary"]["runtime_verified_total"] == 1
    assert summary["summary"]["deferred_total"] == 1
    assert summary["summary"]["newly_uncovered_total"] == 1
    assert summary["summary"]["tier1_missing_runtime_total"] == 0

    classifications = {
        item["trackedId"]: item["classification"] for item in summary["trackedSurface"]
    }
    assert classifications["contract:scanlog-parser"] == "runtime_verified"
    assert classifications["binding:JsLogger"] == "deferred"
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
        deferred_registry={"entries": []},
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
        deferred_registry={"entries": []},
    )

    assert summary["summary"]["registry_mismatch_total"] == 1
    assert summary["summary"]["tier1_missing_runtime_total"] == 1
