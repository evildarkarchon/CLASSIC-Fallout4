"""Permanent structural and negative analyzer owners for executable conformance.

These gates survive evidence migration. Neither diagnostic ledger targets nor
migration states authorize a retained analyzer or contribute runtime coverage.
"""

from __future__ import annotations

from typing import Any

try:
    from .catalog import REQUIREMENTS
except ImportError:
    from catalog import REQUIREMENTS  # type: ignore[no-redef]

BLOCKING_REQUIREMENT_IDS = frozenset(
    requirement.id for requirement in REQUIREMENTS if requirement.blocking
)

WORKFLOW_BLOCKING_OWNERS: dict[str, dict[str, str]] = {
    "cli": {
        "path": ".github/workflows/ci-cpp.yml",
        "commandMarker": "classic-cli/build_cli.ps1 -Test",
    },
    "gui": {
        "path": ".github/workflows/ci-cpp.yml",
        "commandMarker": "classic-gui/build_gui.ps1",
    },
    "node": {
        "path": ".github/workflows/ci-typescript.yml",
        "commandMarker": "bun run test:bun",
    },
    "python-cli": {
        "path": ".github/workflows/ci-python-bindings.yml",
        "commandMarker": "python -m pytest python-bindings/tests -q",
    },
    "tui": {
        "path": ".github/workflows/ci-rust.yml",
        "commandMarker": "cargo test --workspace --release",
    },
}

BASE_ANALYZER_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "cxx-opaque-map-reachability",
        "evidenceKind": "negative",
        "paths": [
            "tools/binding_compliance/cxx_opaque_map_reachability.py",
            "cpp-bindings/classic-cpp-bridge/src/types.rs",
            "cpp-bindings/classic-cpp-bridge/src/types_tests.rs",
            "cpp-bindings/classic-cpp-bridge/build.rs",
        ],
        "blockingRequirementId": "cxx-opaque-map-reachability",
    },
    {
        "id": "node-package-metadata",
        "evidenceKind": "structural",
        "paths": [
            "tools/binding_compliance/node_package_metadata.py",
            "node-bindings/classic-node/src/lib.rs",
            "node-bindings/classic-node/Cargo.toml",
            "node-bindings/classic-node/index.d.ts",
            "Cargo.toml",
        ],
        "blockingRequirementId": "node-package-metadata",
    },
    {
        "id": "installation-discovery-source-boundary",
        "evidenceKind": "structural",
        "paths": [
            "python-bindings/tests/test_installation_discovery_source_audit.py",
            "business-logic/classic-xse-core/src/lib.rs",
            "business-logic/classic-path-core/src/docs_path.rs",
            "business-logic/classic-path-core/src/game_path.rs",
            "business-logic/classic-path-core/src/platform/windows.rs",
            "python-bindings/classic-path-py/src/lib.rs",
        ],
        "blockingWorkflow": WORKFLOW_BLOCKING_OWNERS["python-cli"],
    },
    {
        "id": "cxx-source-parity",
        "evidenceKind": "structural",
        "paths": [
            "tools/cxx_api_parity/check_parity_gate.py",
            "docs/implementation/cxx_api_parity/baseline/parity_contract.json",
        ],
        "blockingRequirementId": "cxx-parity-gate",
    },
    {
        "id": "node-source-and-declaration-parity",
        "evidenceKind": "structural",
        "paths": [
            "tools/node_api_parity/check_parity_gate.py",
            "tools/node_api_parity/check_dts_freshness.py",
            "docs/implementation/node_api_parity/baseline/parity_contract.json",
        ],
        "blockingRequirementId": "node-parity-gate",
    },
    {
        "id": "python-source-and-stub-parity",
        "evidenceKind": "structural",
        "paths": [
            "tools/python_api_parity/check_parity_gate.py",
            "validate_stubs.py",
            "docs/implementation/python_api_parity/baseline/parity_contract.json",
        ],
        "blockingRequirementId": "python-parity-gate",
    },
    {
        "id": "scan-run-contract-validator",
        "evidenceKind": "structural",
        "paths": [
            "tools/binding_compliance/scan_run_contract.py",
            "tests/fixtures/crash_log_scan_run/manifest.json",
        ],
        "blockingRequirementId": "scan-run-contract-variants",
    },
    {
        "id": "scan-run-forbidden-export-audit",
        "evidenceKind": "negative",
        "paths": ["tools/binding_compliance/scan_run_contract.py"],
        "blockingRequirementId": "scan-run-contract-variants",
    },
    {
        "id": "scan-run-rust-enum-inventory",
        "evidenceKind": "structural",
        "paths": ["tools/binding_compliance/scan_run_contract.py"],
        "blockingRequirementId": "scan-run-contract-variants",
    },
    {
        "id": "scan-run-local-ignore-reset-internal-faults",
        "evidenceKind": "structural",
        "paths": [
            "tools/binding_compliance/scan_run_contract.py",
            "tests/fixtures/crash_log_scan_run/manifest.json",
            "business-logic/classic-durable-publication/src/publication_fault.rs",
            "business-logic/classic-config-core/src/installed_yaml_data_reset_fault.rs",
            "business-logic/classic-config-core/src/installed_yaml_data_tests.rs",
            "business-logic/classic-scanlog-core/src/scan_run/contract_tests.rs",
            "cpp-bindings/classic-cpp-bridge/src/scanner/contract_tests.rs",
            "node-bindings/classic-node/src/scan_run_tests.rs",
            "python-bindings/classic-scanlog-py/src/scan_run_tests.rs",
        ],
        "blockingRequirementId": "scan-run-contract-variants",
    },
    {
        "id": "scan-run-structured-failure-internal-faults",
        "evidenceKind": "structural",
        "paths": [
            "tools/binding_compliance/scan_run_contract.py",
            "tests/fixtures/crash_log_scan_run/manifest.json",
            "business-logic/classic-scanlog-core/src/scan_run_test_support.rs",
            "business-logic/classic-scanlog-core/src/scan_run/contract_tests.rs",
            "cpp-bindings/classic-cpp-bridge/src/scanner/contract_tests.rs",
            "node-bindings/classic-node/src/scan_run_tests.rs",
            "python-bindings/classic-scanlog-py/src/scan_run_tests.rs",
        ],
        "blockingRequirementId": "scan-run-contract-variants",
    },
    {
        "id": "tui-shared-runtime-ownership",
        "evidenceKind": "structural",
        "paths": ["ui-applications/classic-tui/tests/shared_runtime_audit.rs"],
        "blockingWorkflow": WORKFLOW_BLOCKING_OWNERS["tui"],
    },
    {
        "id": "user-settings-exclusive-ownership",
        "evidenceKind": "negative",
        "paths": ["tools/user_settings_ownership/check.py"],
        "blockingRequirementId": "user-settings-exclusive-ownership",
    },
)
