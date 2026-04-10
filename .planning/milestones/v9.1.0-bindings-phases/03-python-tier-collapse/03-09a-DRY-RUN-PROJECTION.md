# Plan 09a — Dry-Run Projection (REVIEWS.md Round 2 H6 fix)

**Generated:** 2026-04-09 (Task 0 Step 6)
**Purpose:** Empirically project post-09a and post-09b `deferred_total` BEFORE Task 1 commits any rows.
**Live source:** Computed via `build_coverage_summary` in `tools/binding_parity_runtime_coverage.py` against the freshly regenerated baseline.

## Why this is NOT a gate

Plan 09a alone cannot drive `deferred_total` to 0. The live `build_coverage_summary` at
`tools/binding_parity_runtime_coverage.py` L264-292 contains a `registry_only` fallback
that promotes every `deferred_runtime_backlog.json::entries` item into `tracked_surface`
with `classification="deferred"` EVEN IF its gap row has disappeared from
`parity_diff_report.json::gaps`.

Therefore:
- After Plan 09a row promotions + baseline refresh, the `gap` path contribution to
  `deferred_total` drops to ~0 (all promoted residuals no longer appear as gaps).
- But the `registry_only` path contribution remains ~1008 because 1,202 deferred backlog
  entries still exist in the file.
- **Plan 09b explicitly EMPTIES `deferred_runtime_backlog.json::entries`** to drive
  `deferred_total` to 0. This is legitimate Phase 3 hygiene (the file's contents no
  longer reflect the promoted state); it does NOT cross the Phase 6 DOC-02/DOC-04
  boundary because Phase 6 owns DELETING the file, not editing its contents.

This projection is **diagnostic, not a gate**. Plan 09a's 5-step verification chain will
check that `registry_mismatch_total == 0`, `newly_uncovered_total == 0`, and
`tier1_missing_runtime_total == 0` — but NOT `deferred_total == 0`. The deferred_total
drive-to-zero is Plan 09b's responsibility.

## Empirical projection (live run 2026-04-09)

Output from `_tmp_dry_run.py` against the regenerated 09a-opening baseline:

```
Current (pre-09a): deferred_total=1040, tier1_contract_total=505, tracked_total=1714
Post-09a (gaps filtered; contract unchanged in sim): deferred_total=1008, newly_uncovered_total=0
Post-09b (gaps filtered + deferred registry empty): deferred_total=0, newly_uncovered_total=1
```

Note on the post-09b simulation `newly_uncovered_total=1`: the simulation holds the
pre-09a contract constant while filtering gaps. In reality, Plan 09a's Task 1 adds
tier1 rows covering the filtered gaps, so the post-09a (real) contract will satisfy
the `newly_uncovered` computation and this value will be 0. The simulation number is
an artifact of not applying the contract edit in the projection.

## Live residual count (fresh post-regeneration)

```
Live residual count: 735 across 15 owners
  scangame: 213
  path:     83
  constants: 58
  message:  53
  database: 46
  resource: 40
  xse:      40
  settings: 38
  registry: 37
  yaml:     37
  web:      29
  version:  27
  perf:     16
  update:   14
  scanlog:   4
```

After Task 0's parser-garbage filter (2 pathological path symbols from the
generate_baseline.py parser comment bug), the effective inventory is **733 residuals**
routed across 15 owners for Task 1 promotion.

## Gate endgame (after 09a commits + 09b Task 2 + 09b empties backlog + final refresh)

| Metric | Pre-09a | Post-09a (projected) | Post-09b (projected) |
|--------|--------:|--------------------:|---------------------:|
| `tier1_contract_total` | 505 | ~1100+ | ~1100+ |
| `deferred_total` | 1040 | ~1008 | 0 |
| `newly_uncovered_total` | 0 | 0 | 0 |
| `tier1_missing_runtime_total` | 0 | 0 | 0 |
| `registry_mismatch_total` | 0 | 0 (only if `_stable_id_hash` used correctly) | 0 |

## Task 1 count check for 09b cross-reference

After Task 1 adds rows, Task 1 will log:
- The exact `tier1_contract_total` post-Task-1
- The exact per-owner row count breakdown
- The same-row-dedup savings (how many @rust proxies were skipped because their
  rustSymbol matched a Python class row already authored in the same plan)

Task 4 SUMMARY.md then records the post-09a `deferred_total` so Plan 09b knows the exact
starting number it must drive to 0.

## Notes for Plan 09b

- Plan 09b Task 2 MUST re-verify line numbers in `generate_baseline.py` before editing
  (the rust_unmapped/python_unmapped branches Task 2 deletes were at L672-708 when this
  plan was drafted but may have drifted).
- Carry this DRY-RUN-PROJECTION.md forward for the final endgame comparison once Plan 09b
  empties the backlog and re-runs `build_coverage_summary`.
- The C3 investigation conclusion (Outcome A: fix-in-Phase-3 by editing backlog contents)
  stays the canonical resolution; Plan 09b does NOT need to re-litigate the "is editing
  the backlog Phase-6 scope?" question — it was decided in Round-2 cross-AI review.
