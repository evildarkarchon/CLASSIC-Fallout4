---
phase: 01-cxx-parity-gate-tooling
plan: 03
subsystem: tooling
tags: [cxx, parity-gate, docs, gitignore, validation, phase-finalization]

# Dependency graph
requires:
  - phase: 01-cxx-parity-gate-tooling
    provides: 01-01-SUMMARY (parser + 9 unit tests); 01-02-SUMMARY (gate script + born-green baseline + 13 integration tests); 01-CONTEXT.md decisions D-08 (ephemeral vs committed) and D-15 (doc location) and D-16 (local invocation command); 01-RESEARCH.md Pitfall 7 (gitignore coverage); 01-VALIDATION.md per-task verification map
provides:
  - docs/api/cxx-parity-gate.md — CXXG-05 contributor doc (233 lines, all 7 required sections)
  - tools/cxx_api_parity/README.md — thin pointer to canonical doc (D-15 convention)
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/.gitignore — hides ephemeral parity-artifacts/ (D-08 / Pitfall 7)
  - docs/api/README.md updated — new doc linked at position 31 (between binding-parity-overview and node-python-contract-map)
  - .planning/phases/01-cxx-parity-gate-tooling/01-VALIDATION.md — concrete task IDs for every row; nyquist_compliant and wave_0_complete now true
  - Final end-to-end smoke: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with clean git status (no parity-artifacts pollution)
affects:
  - Phase 2 cxx-bridge-narrowing-closure — every bridge edit must keep this gate green; contributors follow docs/api/cxx-parity-gate.md for refresh workflow
  - Phase 5 CI integration — ci-cpp.yml will add a cxx-parity-gate job that runs before cli-tests/gui-tests
  - Any future contributor touching `#[cxx::bridge]` surface now has a discoverable, substantive local doc

# Tech tracking
tech-stack:
  added: [no new dependencies — all three artifacts are plain markdown or gitignore syntax]
  patterns:
    - "Two-tier doc pattern: thin README in tool directory pointing at canonical docs/api/*.md page (D-15 convention)"
    - "Local .gitignore at bridge crate root hiding ephemeral tool output (mirrors ClassicLib-rs/node-bindings/classic-node/.gitignore pattern)"
    - "Numbered doc index (docs/api/README.md) insertion near conceptually-adjacent entries rather than strict renumber-from-end"

key-files:
  created:
    - docs/api/cxx-parity-gate.md
    - tools/cxx_api_parity/README.md
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/.gitignore
  modified:
    - docs/api/README.md (added entry 31; renumbered 31-33 to 32-34)
    - .planning/phases/01-cxx-parity-gate-tooling/01-VALIDATION.md (TBD → concrete task IDs; frontmatter flipped; File Exists column flipped; approval line updated)

key-decisions:
  - "docs/api/cxx-parity-gate.md structured with the 7 required headings in the order specified by the plan — Overview first for context, then Local Run (the single most common command), then Refresh Workflow, Bootstrap From Scratch (recovery), Contract Row Schema (reference), build.rs Relationship (workflow), Ephemeral vs Committed Artifacts (what to commit), CI Integration (forward-looking). Troubleshooting and Related Docs added at the end as conventional docs/api/ footers."
  - "Doc inserted at position 31 in docs/api/README.md between binding-parity-overview.md (position 30) and node-python-contract-map.md (now position 32) because all three are conceptually in the 'binding parity' cluster. Subsequent entries renumbered by +1 rather than appended at the end so the reading order stays semantically grouped."
  - "tools/cxx_api_parity/README.md kept at exactly 3 lines per D-15 — no duplication of content that lives in docs/api/cxx-parity-gate.md."
  - ".gitignore uses repository-relative pattern `parity-artifacts/` (trailing slash) so only the directory is hidden, not any future file that happens to start with 'parity-artifacts'."
  - "VALIDATION.md task IDs were filled using pytest class::method form (e.g., TestParseExternRust::test_parse_extern_rust_functions) rather than bare method names, because Plan 01 actually organized tests by class. This matches what the Plan 01 SUMMARY recorded and keeps the automated commands runnable as-is."

patterns-established:
  - "CXXG-05 contributor doc structure: Overview + Local Run + Refresh Workflow + Bootstrap From Scratch + Contract Row Schema + build.rs Relationship + Ephemeral vs Committed Artifacts + CI Integration + Troubleshooting + Related Docs. This becomes the template for any future binding gate contributor docs."
  - "Bridge crate .gitignore pattern: short, commented, references the D-decision and the regeneration command so contributors can find the rationale in-source."

requirements-completed: [CXXG-04, CXXG-05]

# Metrics
duration: 4min
completed: 2026-04-07
---

# Phase 01 Plan 03: CXX Parity Gate Finalization Summary

**Phase 1 of the v9.1.0-bindings milestone ends with a discoverable contributor doc, a gitignored ephemeral artifacts directory, and a concrete Nyquist-compliant validation map — the gate is now ready to serve as the acceptance criterion for every Phase 2 cxx-bridge-narrowing-closure edit.**

## Performance

- **Duration:** ~4 minutes
- **Started:** 2026-04-07T07:51:01Z
- **Completed:** 2026-04-07T07:54:50Z
- **Tasks:** 2
- **Files created:** 3 (cxx-parity-gate.md, tools README, bridge .gitignore)
- **Files modified:** 2 (docs/api/README.md, 01-VALIDATION.md)

## Accomplishments

- **CXXG-05 contributor doc** — `docs/api/cxx-parity-gate.md` at 233 lines covering Overview, Local Run, Refresh Workflow, Bootstrap From Scratch, Contract Row Schema, build.rs Relationship, Ephemeral vs Committed Artifacts, CI Integration, Troubleshooting, and Related Docs. Every section the acceptance-criteria greps look for is present in exact form.
- **Bridge crate `.gitignore`** — `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/.gitignore` hides `parity-artifacts/` so every future gate run produces a clean `git status`. `git check-ignore` confirms the pattern is active.
- **Thin tool README** — `tools/cxx_api_parity/README.md` is a 3-line pointer to the canonical doc, per D-15 ("canonical doc lives under docs/api/, not under the tool directory").
- **Doc index wired** — `docs/api/README.md` links the new doc at position 31, inserted adjacent to the other `binding-parity-*` / `classic-cpp-bridge-*` entries.
- **VALIDATION.md task-id backfill** — Every TBD row replaced with concrete `01-XX-TY` IDs; `nyquist_compliant` and `wave_0_complete` flipped to `true`; approval line updated; File Exists column flipped from "❌ W0" to "✅ created" for every row.
- **CXXG-04 requirement cleanup** — The Task 1 CLI surface (`--update-baseline` present, no `--deferred-registry`) was already satisfied by Plan 02 Task 1. Plan 03 finalization confirms that requirement ID CXXG-04 is accounted for in the VALIDATION.md map (rows for `test_no_deferred_registry_arg` and `--help` smoke).
- **End-to-end smoke green** — Final `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with "CXX parity gate passed." and the combined 22-test suite (9 parser + 13 gate) passes in 2.95–3.18s.

## Task Commits

1. **Task 1: Contributor doc + gitignore + doc index entry** — `7eb2b99b` (docs)
2. **Task 2: Backfill VALIDATION.md task IDs** — `f16cf9f4` (docs)

Final metadata commit (SUMMARY.md + STATE.md + ROADMAP.md) will be made by the closing step of this plan execution.

## Files Created / Modified

**Created:**
- `docs/api/cxx-parity-gate.md` — 233-line CXXG-05 contributor doc
- `tools/cxx_api_parity/README.md` — 3-line pointer to canonical doc
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/.gitignore` — 4-line gitignore hiding parity-artifacts/

**Modified:**
- `docs/api/README.md` — inserted entry 31 for cxx-parity-gate.md, renumbered 31-33 → 32-34
- `.planning/phases/01-cxx-parity-gate-tooling/01-VALIDATION.md` — 20 task-ID rows filled, frontmatter flipped, File Exists column flipped, approval line updated

## Git Ignore Verification

```
$ git check-ignore ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/rust_api_surface.json
ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/rust_api_surface.json
```

The pattern is active: git recognizes every file under `parity-artifacts/` as ignored. A final run of the gate produced 5 files in `parity-artifacts/` and none appeared in `git status --short`.

Only remaining entry in `git status` after Plan 03 completes: `M .planning/config.json`. This was carried in from before Plan 01-03 started (Plan 02 SUMMARY documented it as out-of-scope in "Out-of-Scope Discoveries"). Left untouched per the scope boundary rule.

## VALIDATION.md Task-ID Map (applied)

| Task ID | Plan | Wave | Requirement | Test Type | File Exists | Status |
|---------|------|------|-------------|-----------|-------------|--------|
| 01-01-T1 | 01 | 1 | CXXG-01 | scaffolding | ✅ created | ⬜ pending |
| 01-01-T2 (×8 rows) | 01 | 1 | CXXG-01 | unit | ✅ created | ⬜ pending |
| 01-02-T2 (×7 rows) | 02 | 2 | CXXG-02, CXXG-03 | integration/smoke/drift/stale-artifact | ✅ created | ⬜ pending |
| 01-02-T1 (×2 rows) | 02 | 2 | CXXG-04 | CLI surface, smoke | ✅ created | ⬜ pending |
| 01-03-T1 (×2 rows) | 03 | 3 | CXXG-02, CXXG-05 | end-to-end, doc presence | ✅ created | ⬜ pending |

**Total rows:** 20 (same as original — rows were EDITED, not added or removed). The status column stays `⬜ pending` because VALIDATION.md records plan-phase intent; the verifier will flip rows to `✅ green` after it re-runs each command.

## Decisions Made

- **Doc section ordering** — Overview → Local Run → Refresh Workflow → Bootstrap From Scratch → Contract Row Schema → build.rs Relationship → Ephemeral vs Committed Artifacts → CI Integration → Troubleshooting → Related Docs. Puts the single most common command (Local Run) near the top; defers ABI-level detail (Contract Row Schema) to the middle; ends with forward-looking CI plus troubleshooting.
- **Doc index placement** — Inserted at position 31 between `binding-parity-overview.md` and `node-python-contract-map.md` rather than appended at the end. Keeps all the "binding parity" topics clustered in the reading order.
- **Task ID format in VALIDATION.md** — `{phase}-{plan}-T{n}` (e.g., `01-01-T1`). Matches the convention in the plan's explicit mapping table.
- **Pytest class::method form in VALIDATION.md commands** — Plan 01 actually wrote tests inside pytest classes (`TestParseExternRust`, `TestParseSharedStructs`, etc.) per its SUMMARY. VALIDATION.md now reflects that exact class::method form so every automated command is runnable as-is.

## Deviations from Plan

None — Task 1 and Task 2 executed exactly as written. The plan's verbatim doc content (the ~100-line markdown template under Part B of Task 1) was accepted and extended with a Troubleshooting + Related Docs footer to match existing `docs/api/` pages. The `.gitignore` content was used verbatim. The VALIDATION.md mapping table was applied 1:1 with the plan's mapping.

The only notable refinement: the VALIDATION.md automated commands were updated to use pytest `ClassName::method` form (e.g. `TestParseExternRust::test_parse_extern_rust_functions`) rather than bare method names, because that is the actual test layout recorded in Plan 01's SUMMARY. This matches the plan's mapping instructions verbatim — the plan explicitly listed commands in the `TestClass::test_method` form under the "Specifically the Per-Task Verification Map table should look like this after the edit" block.

### Out-of-Scope Discoveries

- `.planning/config.json` remains modified (carried in from before Plan 01-03 started, documented by Plan 02 as out-of-scope). Not touched by this plan.

## Issues Encountered

None. Both tasks committed cleanly on first attempt; the gate ran green before and after each commit; the test suite held at 22 passed with no failures.

## Authentication Gates

None.

## Phase 1 Exit Criteria — All Met

| Criterion | Evidence |
|---|---|
| CXXG-01 parser working + tests | Plan 01 (9 unit tests passing; 202-entry real-surface scan) |
| CXXG-02 baseline + gate script | Plan 02 (born-green baseline, 5 committed artifacts) |
| CXXG-03 drift detection | Plan 02 (4 drift integration tests + 2 stale-artifact tests) |
| CXXG-04 CLI surface locked | Plan 02 (`--update-baseline` present, no `--deferred-registry`) |
| CXXG-05 contributor doc | Plan 03 Task 1 (`docs/api/cxx-parity-gate.md` with all 7 required headings) |
| Ephemeral artifacts gitignored | Plan 03 Task 1 (`.gitignore` active, `git check-ignore` confirms) |
| VALIDATION.md task IDs backfilled | Plan 03 Task 2 (0 TBD markers, nyquist_compliant true) |
| End-to-end gate exits 0 | Plan 03 Task 1 (post-commit smoke, 22-test suite green) |

## Phase 1 Complete — Phase 2 Ready

**Phase 1 (CXX Parity Gate Tooling) is complete; Phase 2 (CXX Bridge Surface Expansion) can now start and use `--update-baseline` to accept new bridge entries as it widens the surface.**

Every cxx-bridge-narrowing-closure plan in Phase 2 should:

1. Add the new bridge file or symbol to the bridge crate.
2. Run `python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline` to accept the intended new entries.
3. Inspect `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md` to confirm only the intended entries appeared.
4. Commit the bridge source change and the 5 refreshed baseline files in the same commit so the gate stays green at every revision.
5. Verify with a plain `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` run before committing.

The contributor doc at `docs/api/cxx-parity-gate.md` documents this workflow end-to-end; Phase 2 executors can treat it as the canonical reference.

## Self-Check: PASSED

- Created files exist (verified post-commit):
  - `docs/api/cxx-parity-gate.md` FOUND (233 lines, all 7 required sections present)
  - `tools/cxx_api_parity/README.md` FOUND (3 lines, D-15 pointer)
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/.gitignore` FOUND
- Modified files updated:
  - `docs/api/README.md` — entry 31 links cxx-parity-gate.md (verified with grep)
  - `.planning/phases/01-cxx-parity-gate-tooling/01-VALIDATION.md` — 0 TBD markers, nyquist_compliant: true, wave_0_complete: true, approval line updated
- Commits exist on current branch:
  - `7eb2b99b` (Task 1: doc + gitignore + index) FOUND
  - `f16cf9f4` (Task 2: VALIDATION.md task IDs) FOUND
- Tooling verification:
  - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with "CXX parity gate passed."
  - `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/ -q` → 22 passed, 0 failed
  - `git check-ignore ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts/rust_api_surface.json` → pattern matched
  - `git status --short` shows NO files under `parity-artifacts/`
