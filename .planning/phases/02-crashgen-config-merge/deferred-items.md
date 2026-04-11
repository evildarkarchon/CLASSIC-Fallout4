# Deferred Items — Phase 02 crashgen-config-merge

Items discovered during execution that are OUT OF SCOPE for this phase's plans.

## From Plan 02-02 Task 1 (Node parity tooling update)

### test_tier1_contract_total_baseline_floor — pre-existing floor regression

- **Test:** `tools/node_api_parity/tests/test_check_parity_gate.py::test_tier1_contract_total_baseline_floor`
- **Failure:** `tier1Mappings regressed below Phase 4 floor: 705 < 711`
- **Status:** PRE-EXISTING, unrelated to Plan 02-02 changes. No files touched by this plan affect `parity_contract.json`.
- **Scope:** Out-of-scope for Phase 2 (crashgen-config merge). Likely belongs to a future contract-refresh task in Phase 4 gate validation, or a separate floor-recalibration chore.
- **Recommendation:** Investigate the 6-row regression root cause separately. Either (a) restore the 6 missing contract rows if they were accidentally deleted in prior work, or (b) lower the floor tripwire to match current truth after establishing that the reduction is intentional.
