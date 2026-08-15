# Evidence Migration Ledger

> **Diagnostic only.** This ledger classifies migration targets and does **not** grant compliance, runtime coverage, or permission to remove a gate.

- Obligations: **3,650**
- Named retained analyzers: **18**
- Documented policy exceptions: **1**

## Target dispositions

| Classification | Obligations |
| --- | ---: |
| `negative_analyzer` | 207 |
| `policy_exception` | 1 |
| `runtime_verifiable` | 3,043 |
| `structural_analyzer` | 399 |

## Current evidence sources

| Source kind | Occurrences |
| --- | ---: |
| `consumer_audit` | 6 |
| `consumer_required_participant` | 3 |
| `consumer_source_audit` | 58 |
| `display_content_consumer_audit` | 3 |
| `display_content_source_audit` | 11 |
| `parity_row` | 2,776 |
| `policy_exception` | 1 |
| `runtime_registry_claim` | 67 |
| `rust_enum_inventory_audit` | 15 |
| `scan_run_contract_variant` | 73 |
| `scan_run_required_participant` | 28 |
| `scan_run_source_marker` | 119 |
| `scan_run_supported_adapter` | 4 |
| `scan_run_variant_acknowledgement` | 292 |
| `shared_runtime_source_audit` | 1 |
| `source_audit` | 189 |
| `user_settings_source_audit` | 4 |

## Retained analyzers

- `consumer-source-audit:test_mainwindow_geometry:negative` (negative): `classic-gui/tests/test_mainwindow_geometry.cpp`
- `consumer-source-audit:test_scan_settings_wiring:negative` (negative): `classic-gui/tests/test_scan_settings_wiring.cpp`
- `consumer-source-audit:test_scan_settings_wiring:structural` (structural): `classic-gui/tests/test_scan_settings_wiring.cpp`
- `consumer-source-audit:test_yaml_update_wiring:negative` (negative): `classic-gui/tests/test_yaml_update_wiring.cpp`
- `consumer-source-audit:test_yaml_update_wiring:structural` (structural): `classic-gui/tests/test_yaml_update_wiring.cpp`
- `cxx-source-parity` (structural): `tools/cxx_api_parity/check_parity_gate.py`, `docs/implementation/cxx_api_parity/baseline/parity_contract.json`
- `display-content-ownership-cli` (negative): `classic-cli/tests/test_display_label_audit.cpp`
- `display-content-ownership-gui` (negative): `classic-gui/tests/test_display_label_audit.cpp`
- `display-content-ownership-node` (negative): `node-bindings/classic-node/__test__/display_label_audit.spec.ts`
- `display-content-ownership-python-cli` (negative): `python-bindings/tests/test_classic_py_cli_display_label_audit.py`
- `display-content-ownership-tui` (negative): `ui-applications/classic-tui/tests/shared_runtime_audit.rs`
- `node-source-and-declaration-parity` (structural): `tools/node_api_parity/check_parity_gate.py`, `tools/node_api_parity/check_dts_freshness.py`, `docs/implementation/node_api_parity/baseline/parity_contract.json`
- `python-source-and-stub-parity` (structural): `tools/python_api_parity/check_parity_gate.py`, `validate_stubs.py`, `docs/implementation/python_api_parity/baseline/parity_contract.json`
- `scan-run-contract-validator` (structural): `tools/binding_compliance/scan_run_contract.py`, `tests/fixtures/crash_log_scan_run/manifest.json`
- `scan-run-forbidden-export-audit` (negative): `tools/binding_compliance/scan_run_contract.py`
- `scan-run-rust-enum-inventory` (structural): `tools/binding_compliance/scan_run_contract.py`
- `tui-shared-runtime-ownership` (structural): `ui-applications/classic-tui/tests/shared_runtime_audit.rs`
- `user-settings-exclusive-ownership` (negative): `tools/user_settings_ownership/check.py`

## Policy exceptions

- `cxx-classic-resource-core-transitive-access` (cxx): classic-resource-core has no dedicated CXX bridge; C++ reaches its behavior transitively through classic-file-io-core. See `docs/api/binding-parity-policy.md`.

The JSON artifact is the complete occurrence ledger. Runtime entries remain `shadow` until executed receipts independently justify a later ratchet state; ledger text alone can never do so.
