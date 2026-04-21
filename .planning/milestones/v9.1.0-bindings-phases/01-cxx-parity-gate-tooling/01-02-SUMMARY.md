---
phase: 01-cxx-parity-gate-tooling
plan: 02
subsystem: tooling
tags: [cxx, parity-gate, integration-tests, baseline, born-green]

# Dependency graph
requires:
  - phase: 01-cxx-parity-gate-tooling
    provides: 01-01-SUMMARY parser (parse_cxx_bridge_surface 202-entry deterministic output); D-03/D-04/D-05/D-06/D-08/D-12/D-13/D-14 from 01-CONTEXT.md
provides:
  - tools/cxx_api_parity/check_parity_gate.py — read-only gate with --update-baseline; exits 1 on drift or stale committed artifacts
  - tools/cxx_api_parity/generate_baseline.py extended with generate_diff_report(), render_diff_markdown(), and a --write-baseline bootstrap path in main()
  - docs/implementation/cxx_api_parity/baseline/ — 5 born-green committed artifacts (parity_contract.json, rust_api_surface.json, cxx_diff_report.json, cxx_diff_report.md, cxx_gate_report.md)
  - tools/cxx_api_parity/tests/test_gate.py — 13 integration tests (subprocess-driven) covering CXXG-02, CXXG-03, CXXG-04
affects:
  - 01-03 (CI integration uses these scripts and the committed baseline)
  - 02 cxx-bridge-narrowing-closure (every bridge edit must keep this gate green; new entries flow through --update-baseline)

# Tech tracking
tech-stack:
  added: [no new third-party deps — pure stdlib (json, shutil, subprocess, argparse)]
  patterns:
    - "Two-script gate skeleton mirroring tools/python_api_parity/{generate_baseline,check_parity_gate}.py"
    - "Synthetic single-file bridge under tmp_path for hermetic drift tests (_bootstrap_synthetic_gate)"
    - "Bootstrap reconciliation: bootstrap writes a placeholder cxx_gate_report.md, the first --update-baseline run replaces it with the real gate output"
    - "Stale-artifact detection via artifacts_match() that pops generated_at_utc from JSON and skips '- Generated:' lines from markdown before comparing"

key-files:
  created:
    - tools/cxx_api_parity/check_parity_gate.py
    - tools/cxx_api_parity/tests/test_gate.py
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/rust_api_surface.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  modified:
    - tools/cxx_api_parity/generate_baseline.py

key-decisions:
  - "Compare contract rows by id (sha256(sym:kind:module)[:16]) and semantic content only — sourceFile is excluded so moving a file across modules does not register as drift unless the bridgeModule changes."
  - "_normalize_row_for_compare() strips id from the comparable shape and only keeps signature/fields/variants/blockOrigin per row kind."
  - "Bootstrap path writes a placeholder cxx_gate_report.md (just contract row count + matched count), then expects an immediate `check_parity_gate.py --update-baseline` to replace it with the real render. This is documented in the synthetic-test helper as a single reconciliation run."
  - "schema_version=1 is locked into parity_contract.json now so future schema migrations have a discriminator without breaking old gates."
  - "Drift integration tests use a synthetic single-file bridge (_SIMPLE_BRIDGE) so each test is hermetic and never depends on the real 202-entry surface."

requirements-completed: [CXXG-02, CXXG-03, CXXG-04]

# Metrics
duration: 8min
completed: 2026-04-07
---

# Phase 01 Plan 02: CXX Parity Gate Bootstrap & Integration Tests Summary

**Wraps the Plan 01 parser in a read-only gate script with stale-artifact detection plus a `--write-baseline` bootstrap path; commits a 202-entry born-green baseline for the real 14-file bridge and 13 subprocess-driven integration tests covering every drift case from RESEARCH.md.**

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Extend generate_baseline.py with diff/report helpers + create check_parity_gate.py | c4566a20 | 2 (1 modified, 1 created) |
| 2A | Bootstrap born-green baseline (5 artifacts under docs/implementation/cxx_api_parity/baseline/) | bcf8e768 | 5 created |
| 2B | Integration test suite (13 tests in test_gate.py) | 45c0a25d | 1 created |

## Born-Green Baseline — Per-Module Entry Counts

The bootstrap (`python tools/cxx_api_parity/generate_baseline.py --repo-root . --write-baseline`) emitted 202 deterministic entries across all 14 bridge modules. Counts mirror Plan 01's parser sanity-check exactly:

| bridgeModule | entries |
|--------------|---------|
| config       | 47      |
| files        | 28      |
| scanner      | 26      |
| game         | 19      |
| yaml         | 19      |
| registry     | 14      |
| types        | 13      |
| database     | 10      |
| message      | 9       |
| perf         | 5       |
| scangame     | 4       |
| runtime      | 3       |
| update       | 3       |
| markdown     | 2       |
| **TOTAL**    | **202** |

`schema_version=1`, no `tier1Mappings`, no `tier2*` keys (D-03/D-04). Entries are sorted by `(bridgeModule, kind, rustSymbol)` for byte-level determinism.

This is the **sizing signal for Phase 2** — every cxx-bridge-narrowing-closure plan can budget against the per-module counts above. The largest current owner is `config` at 47 entries; the smallest is `markdown` at 2.

## Bootstrap Reconciliation Workflow (placeholder vs. real gate report)

The `--write-baseline` path in `generate_baseline.py` writes 5 artifacts. Four of them are the same shape `check_parity_gate.py` would write (`parity_contract.json`, `rust_api_surface.json`, `cxx_diff_report.json`, `cxx_diff_report.md`). The fifth — `cxx_gate_report.md` — is intentionally a **short placeholder** because the bootstrap does not run the gate logic itself; only the real `check_parity_gate.py` knows the full report format.

Result: the very first `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` after a fresh bootstrap will exit 1 with `Checked-in CXX parity artifacts are stale: cxx_gate_report.md`. This is **expected behaviour**, not a bug.

The reconciliation step (run exactly once after the bootstrap):

```
python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline
```

After that, every subsequent `check_parity_gate.py --repo-root .` exits 0 cleanly. This sequence is now baked into the synthetic-test helper `_bootstrap_synthetic_gate()` so every drift integration test starts from a clean state.

This pattern is also the documented **Phase 2 add-a-new-bridge-file workflow**:

1. Add the new `.rs` file to `build.rs` and to the bridge crate
2. Run `python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline`
3. Inspect the diff in `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md` to confirm only the intended new entries appeared
4. Commit the baseline diff + the new bridge file in the same commit

## Real-Surface Edge Cases (no surprises)

The 202-entry committed baseline parses the real bridge cleanly. Plan 01's parser pitfalls (the 7 documented in `01-RESEARCH.md`) all hold up under the real-surface scan — no new pitfalls surfaced when wiring the diff layer on top:

- The diff report's `_normalize_row_for_compare()` ignores `sourceFile` and `id`, so the comparison is purely semantic. No false-positive drift was reported on the born-green run.
- `BatchProgressEventKind` (scanner) and `BatchProgressEvent` (scanner) — the only enum + the only nested-DTO struct in the bridge — round-trip cleanly into the contract.
- All 12 opaque types and 169 functions are covered by the same comparison shape; opaque rows have no `signature/fields/variants` keys, which `_normalize_row_for_compare()` handles by branching on `kind`.

## Drift-Detection Test Matrix (13 integration tests, 2.94s wall time)

| Test class | Test | Drift kind | Expected gate exit |
|---|---|---|---|
| TestBaselineExists | test_baseline_file_exists | n/a (existence) | 0 (read-only assert) |
| TestBaselineExists | test_baseline_covers_14_modules | n/a (coverage) | 0 |
| TestBaselineExists | test_baseline_schema_shape | n/a (D-03/D-04 schema) | 0 |
| TestBaselineExists | test_baseline_entries_are_sorted | n/a (determinism) | 0 |
| TestGateSmoke | test_gate_passes_on_unchanged_source | none | 0 |
| TestDriftDetection | test_gate_fails_on_added_function | missing_from_contract | 1 |
| TestDriftDetection | test_gate_fails_on_removed_function | missing_from_current | 1 |
| TestDriftDetection | test_gate_fails_on_struct_field_rename | signature_mismatch | 1 |
| TestDriftDetection | test_gate_fails_on_function_signature_change | signature_mismatch | 1 |
| TestStaleArtifact | test_gate_fails_on_stale_artifact | stale committed md | 1 |
| TestStaleArtifact | test_update_baseline_clears_stale | stale -> refreshed | 1 -> 0 |
| TestNoDeferredRegistry | test_no_deferred_registry_arg | --help inspection | 0 |
| TestNoDeferredRegistry | test_unknown_deferred_registry_arg_rejected | argparse rejection | 2 |

Combined parser + gate suite: **22 tests pass in 2.95s**, 0 failures, 0 errors.

## Decisions Made

1. **id-based diff key** — Rows match on `id` (`sha256(rustSymbol:kind:bridgeModule)[:16]`) so renaming a function in the same module is reported as one removal + one addition (not as a "rename"). This keeps the diff report simple and conservative.
2. **sourceFile excluded from comparison** — Moving a function across files in the same bridgeModule does not trigger drift. This decouples file-organization refactors from API-contract drift.
3. **schema_version=1 locked** — The contract JSON now carries an explicit version discriminator. Future schema changes (e.g., adding a `deprecation` key) will bump this and the gate can branch.
4. **Synthetic-bridge drift tests** — Drift tests use `_SIMPLE_BRIDGE` (a 10-line synthetic single-file bridge) under `tmp_path`. This is hermetic and never depends on the real 202-entry surface, so the tests don't break when bridges are added or removed in Phase 2.
5. **Reconciliation in `_bootstrap_synthetic_gate()`** — The synthetic-test helper bakes in the bootstrap → `--update-baseline` → clean-run sequence so every drift test starts from a known clean state.

## Deviations from Plan

### Auto-fixed Issues

None. The plan executed exactly as written. Both tasks landed without rule-1/2/3 fixes:

- Task 1: `check_parity_gate.py --help` ran cleanly on first invocation; argparse surface matched the locked CLI surface; no `--deferred-registry` arg present.
- Task 2A: `generate_baseline.py --write-baseline` produced 202 entries on first run, matching Plan 01's sanity check exactly. The expected post-bootstrap stale `cxx_gate_report.md` was reconciled with one `--update-baseline` run as the plan documented.
- Task 2B: All 13 integration tests passed on first invocation (no test debugging required). Combined parser + gate suite: 22 tests, 0 failures.

### Out-of-Scope Discoveries

`.planning/config.json` shows as modified in `git status` but was not touched by this plan — it was modified before Plan 02 started and was carried in the working tree. Not committed by this plan; left for the orchestrator/user to handle.

`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/` is now an untracked directory containing the ephemeral gate output. Per D-08, Plan 03 will add this to `.gitignore`. Not committed by this plan.

## Authentication Gates

None.

## Schema Notes for Phase 2 Executors

When Phase 2 (cxx-bridge-narrowing-closure) adds a new bridge file or new symbol:

1. **Add the new file/symbol** to the bridge crate.
2. **Refresh the baseline:**
   ```
   python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline
   ```
3. **Inspect** `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md` — every "missing_from_contract" row should be an intended new entry. If anything unexpected appears, revert the baseline refresh and investigate.
4. **Commit** the bridge file change AND the 5 baseline files in the same commit so the gate stays green at every revision.
5. **Verify** by running `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — it should exit 0.

If a Phase 2 task removes a bridge symbol, the same workflow applies; the diff report will show "missing_from_current" rows for the removed entries.

## Self-Check: PASSED

Created files exist (verified post-commit):
- `tools/cxx_api_parity/check_parity_gate.py` FOUND
- `tools/cxx_api_parity/tests/test_gate.py` FOUND
- `docs/implementation/cxx_api_parity/baseline/parity_contract.json` FOUND
- `docs/implementation/cxx_api_parity/baseline/rust_api_surface.json` FOUND
- `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json` FOUND
- `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md` FOUND
- `docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md` FOUND

Modified files updated:
- `tools/cxx_api_parity/generate_baseline.py` MODIFIED (added generate_diff_report, render_diff_markdown, --write-baseline flag)

Commits exist on current branch:
- `c4566a20` (Task 1: gate scripts) FOUND
- `bcf8e768` (Task 2A: baseline) FOUND
- `45c0a25d` (Task 2B: integration tests) FOUND

Test results:
- 22 tests pass (9 parser from Plan 01 + 13 gate from Plan 02), 0 failures, 0 errors
- Real-bridge gate run: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with "CXX parity gate passed."
- `--help` lists exactly: `--repo-root`, `--contract`, `--output-dir`, `--baseline-output-dir`, `--update-baseline`. Does NOT mention `--deferred-registry` or `--runtime-registry`.
