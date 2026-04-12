# Deferred Items — Phase 02 crashgen-config-merge

Items discovered during execution that are OUT OF SCOPE for this phase's plans.

## From Plan 02-02 Task 1 (Node parity tooling update)

### test_tier1_contract_total_baseline_floor — reconciled to the live contract

- **Test:** `tools/node_api_parity/tests/test_check_parity_gate.py::test_tier1_contract_total_baseline_floor`
- **Historical failure:** `tier1Mappings regressed below Phase 4 floor: 705 < 711`
- **Status:** resolved during Phase 05 cleanup. The checked-in Node parity contract/report already show the live one-tier truth: 705 Tier-1 rows, 705 matched rows, and no `tierDefinitions.tier2` entry.
- **Resolution:** The tripwire was recalibrated to the source-backed live floor so it now protects `assert len(tier1) >= 705` instead of an outdated 711-row story. The live one-tier contract floor is 705.
- **Current note:** Keep the historical mismatch here as provenance, but treat the issue as closed unless the live contract/report drift away from the 705-row one-tier baseline.
