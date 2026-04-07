---
phase: 01-deprecated-api-migration
verified: 2026-04-07T03:12:55Z
status: gaps_found
score: 4/5 success criteria verified
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "Replaced the stale REQUIREMENTS-sync narrative with fresh Rust and Python rerun evidence for DEBT-05, DEBT-06, DEBT-07, and DEBT-10."
    - "Confirmed the Python parity gate still passes with 59/59 Tier-1 rows matched during the closure rerun."
  gaps_remaining:
    - "Success Criterion 5 is still open until the repo-standard Node local parity gate is rerun and recorded."
  regressions: []
---

# Phase 01: Deprecated API Migration Verification Report

**Phase Goal:** All binding surfaces use current APIs with deprecation warnings emitted for end-users still calling legacy Python methods.
**Verified:** 2026-04-07T03:12:55Z
**Status:** gaps_found — fresh Rust and Python proof is green, but the Node local parity rerun required for full SC5 closure is not yet recorded in this artifact.
**Re-verification:** Yes — Phase 09 closure refresh.

## Re-Verification Summary

Phase 09 exists because this artifact still centered an old documentation-gap story after the planning files changed. That stale story is now retired. This refresh records fresh command-backed evidence for the Phase 1 requirements instead of relying on summary prose or on the old “`REQUIREMENTS.md` is out of sync” blocker.

The Phase 1 summaries (`01-01-SUMMARY.md`, `01-02-SUMMARY.md`) are treated here as historical claims only. They are used for provenance, not as standalone proof.

## Rerun Command Results

| Surface | Command | Result | Evidence captured |
|---|---|---|---|
| Rust DEBT-07 proof | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests` | PASS | 24 tests passed; targeted `version::tests` suite stays green under `check_version_status()` coverage |
| Python warning proof | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning"` | PASS | 3 passed, 11 deselected |
| Python parity gate | `python tools/python_api_parity/check_parity_gate.py --repo-root .` | PASS | Tier-1 gate report shows 59/59 matched, 0 missing Rust, 0 missing Python, 0 signature mismatches |

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Current evidence |
|---|---|---|---|
| SC1 | Python `parse_segments_parallel` internally delegates to `parse_all_sections_arc` and `.pyi` contract updated | VERIFIED | Targeted pytest warning coverage reran green; Phase 1 implementation summary and current source still align on deprecated wrapper behavior |
| SC2 | Python `generate_suspect_section` internally calls `generate_suspect_section_header` + `generate_suspect_found_footer` | VERIFIED | Targeted pytest warning coverage reran green for the deprecated report surface |
| SC3 | All tests formerly using `#[allow(deprecated)]` on `is_outdated` now exercise `check_version_status()` | VERIFIED | Fresh `version::tests` cargo rerun passed all 24 targeted tests |
| SC4 | `PyFormIDAnalyzerCore::new` emits `DeprecationWarning` when receiving legacy `PyDict` format for `mods_single` | VERIFIED | Targeted pytest warning coverage reran green for `formid_analyzer_legacy_dict_deprecation_warning` |
| SC5 | Python and Node parity gates pass after all migrations | PARTIAL | Python parity gate rerun passed; Node local parity rerun is still pending in this intermediate refresh |

**Score:** 4/5 truths currently verified.

## Requirement Coverage

| Requirement | Source plan | Status | Current proof |
|---|---|---|---|
| DEBT-05 | `01-02-PLAN.md` | SATISFIED | Fresh targeted pytest rerun covers `parse_segments_parallel` deprecation-warning behavior; current verification now records that runtime proof explicitly instead of inferring it from old summaries |
| DEBT-06 | `01-02-PLAN.md` | SATISFIED | Fresh targeted pytest rerun covers `generate_suspect_section` delegation + deprecation-warning behavior |
| DEBT-07 | `01-01-PLAN.md` | SATISFIED | Fresh `cargo test ... version::tests` rerun passed, confirming the `check_version_status()` replacement suite remains green |
| DEBT-10 | `01-02-PLAN.md` | SATISFIED | Fresh targeted pytest rerun covers the legacy `mods_single` warning path in `PyFormIDAnalyzerCore::new` |

## Python Parity Gate Snapshot

- Tier-1 contract rows: **59**
- Tier-1 matched: **59**
- Tier-1 missing Rust: **0**
- Tier-1 missing Python: **0**
- Tier-1 signature mismatch: **0**
- Runtime coverage summary generated with **1 newly uncovered** Python surface; this does not fail the Tier-1 gate and should be handled through the parity-governance workflow rather than misreported as a Phase 1 regression.

## Supporting Artifact Cross-Check

| Artifact | Role in closure | Status |
|---|---|---|
| `01-VALIDATION.md` | Execution contract for the targeted Rust and Python commands | Used |
| `01-01-SUMMARY.md` | Historical completion claim for DEBT-07 | Cross-checked, not treated as proof by itself |
| `01-02-SUMMARY.md` | Historical completion claim for DEBT-05/06/10 | Cross-checked, not treated as proof by itself |
| `.planning/REQUIREMENTS.md` | Current milestone traceability file | Cross-checked; no longer used as the primary blocker narrative in this artifact |

## Remaining Gap Before Full Closure

The remaining blocker is narrow and current: rerun the repo-standard Node local parity gate from `ClassicLib-rs/node-bindings/classic-node` and record the result here so Success Criterion 5 has fresh cross-binding proof. No requirement in this report is being held open because of the old REQUIREMENTS-sync story.

## Gaps Summary

- **Closed:** The stale claim that this phase was blocked primarily by `REQUIREMENTS.md` bookkeeping.
- **Closed:** Missing fresh Rust and Python runtime proof for DEBT-05, DEBT-06, DEBT-07, and DEBT-10.
- **Open:** Fresh recorded Node local parity proof for SC5.

---

_Verified: 2026-04-07T03:12:55Z_
_Verifier: GPT-5.4 (gsd plan executor)_
