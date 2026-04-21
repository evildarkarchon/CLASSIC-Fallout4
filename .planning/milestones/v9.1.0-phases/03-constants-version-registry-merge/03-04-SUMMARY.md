---
phase: 03-constants-version-registry-merge
plan: 04
subsystem: docs
tags: [api-docs, parity, cxx, python, node, rust]
requires:
  - phase: 03-02
    provides: Python constants redistribution and module retags
  - phase: 03-03
    provides: Node/CXX constants redistribution and shared bridge module
provides:
  - Consolidated API docs for version-registry, settings, and shared owners
  - Deterministic Python and Node parity routing without retired constants owners
  - Refreshed CXX, Python, and Node parity baselines plus final workspace Rust proof
affects: [phase-04-gate-validation, api-docs, parity-gates]
tech-stack:
  added: []
  patterns: [owner-routed parity contracts, selector-based runtime coverage refresh, redistributed API doc ownership]
key-files:
  created: []
  modified:
    - docs/api/README.md
    - docs/api/classic-version-registry-core.md
    - docs/api/classic-settings-core.md
    - docs/api/classic-shared-core.md
    - tools/python_api_parity/generate_baseline.py
    - tools/node_api_parity/generate_baseline.py
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - docs/implementation/node_api_parity/baseline/parity_contract.json
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
    - ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json
key-decisions:
  - "Retire the standalone constants API doc and document Fallout4Version, YamlFile/settings constants, and GameId under their surviving owners."
  - "Keep Python parity scanning both classic-shared-core and classic-shared-py so GameId redistribution and shared PyO3 wrappers remain visible to the gate."
  - "Track Node version-core rust-only proxy rows with an explicit runtime-coverage selector after NULL_VERSION moved out of the retired constants owner."
patterns-established:
  - "Redistributed-owner docs: contributor references should point at surviving owners, not retired crate pages."
  - "Parity reparenting: rewrite owner/module metadata first, then regenerate gate artifacts and runtime coverage summaries."
requirements-completed: [CNST-01, CNST-02, CNST-03]
duration: 13 min
completed: 2026-04-12
---

# Phase 3 Plan 4: Consolidated constants-owner docs, split-aware parity baselines, and final workspace Rust closure Summary

**Contributor docs now point at version-registry/settings/shared owners, parity metadata no longer references retired constants owners, and all three parity gates plus workspace Rust closure pass after regeneration.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-12T01:09:12Z
- **Completed:** 2026-04-12T01:22:46Z
- **Tasks:** 2
- **Files modified:** 41

## Accomplishments
- Deleted `docs/api/classic-constants-core.md` and folded its active API surface into the surviving owner docs.
- Reworked Python and Node parity tooling/metadata so retired constants owners, modules, and runtime selectors no longer appear in active inputs.
- Regenerated CXX, Python, and Node parity artifacts and recorded green `cargo build --workspace` / `cargo test --workspace` closure evidence.

## Task Commits

Each task was committed atomically:

1. **Task 1: Consolidate active docs around version-registry, settings, and shared ownership** - `903661b7` (docs)
2. **Task 2: Build deterministic owner-routing, refresh all parity artifacts, and record final Rust closure proof** - `14aea8ab` (fix)

**Plan metadata:** pending

## Files Created/Modified
- `docs/api/README.md` - removed the retired constants page and pointed readers at surviving owners
- `docs/api/classic-version-registry-core.md` - added `Fallout4Version` and `NULL_VERSION` coverage
- `docs/api/classic-settings-core.md` - added `YamlFile`, `SETTINGS_IGNORE_NONE`, and `must_not_be_none()` coverage
- `docs/api/classic-shared-core.md` - added `GameId` coverage
- `tools/python_api_parity/generate_baseline.py` - removed retired constants targets and added deterministic Phase 3 routing helpers
- `tools/node_api_parity/generate_baseline.py` - removed retired constants targets and added deterministic Phase 3 routing helpers
- `docs/implementation/cxx_api_parity/baseline/*` - regenerated the CXX parity contract/surface after the bridge split
- `docs/implementation/python_api_parity/baseline/*` - regenerated Python parity artifacts against redistributed owners
- `docs/implementation/node_api_parity/baseline/*` - regenerated Node parity artifacts against redistributed owners
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` - removed the retired constants selector and refreshed owner hashes/counts
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` - removed the retired constants selector and added the version-owner selector

## Decisions Made
- Retired constants docs were deleted instead of left as forwarding pages so contributors have one canonical owner per symbol family.
- Python parity now scans both `classic-shared-core` and `classic-shared-py` because the gate must see GameId's new Rust home without losing shared PyO3 wrapper rows.
- Node runtime coverage gained a dedicated `version` selector entry so rust-only version proxies remain runtime-accounted after `NULL_VERSION` left the old constants owner.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Swept additional active API guides with stale constants references**
- **Found during:** Task 1 (doc consolidation)
- **Issue:** Several active `docs/api/` guides outside the task's explicit file list still referenced the retired constants owner, which would violate the contributor-doc truth the plan requires.
- **Fix:** Updated `classic-path-core.md`, `classic-registry-core.md`, `classic-resource-core.md`, and `classic-version-core.md` alongside the listed docs.
- **Files modified:** `docs/api/classic-path-core.md`, `docs/api/classic-registry-core.md`, `docs/api/classic-resource-core.md`, `docs/api/classic-version-core.md`
- **Verification:** Task 1 doc sweep grep returned no `classic-constants-core` or `classic_constants_core` hits under `docs/api/`
- **Committed in:** `903661b7`

**2. [Rule 1 - Bug] Restored Python parity scanning for shared PyO3 wrappers while adding shared-core scanning**
- **Found during:** Task 2 (Python parity regeneration)
- **Issue:** Replacing `classic-shared-py` with only `classic-shared-core` caused the Python gate's existing shared wrapper rows to disappear from the parsed Rust surface.
- **Fix:** Updated `tools/python_api_parity/generate_baseline.py` to scan both `classic-shared-core` and `classic-shared-py` under the shared owner.
- **Files modified:** `tools/python_api_parity/generate_baseline.py`
- **Verification:** `python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline`
- **Committed in:** `14aea8ab`

**3. [Rule 3 - Blocking] Added Node version-owner runtime coverage metadata during parity refresh**
- **Found during:** Task 2 (Node parity regeneration)
- **Issue:** Node parity refresh surfaced 13 `version` owner rust-only proxy rows with no runtime coverage selector, blocking the gate.
- **Fix:** Added a deterministic `node-tier1-version` selector entry to the runtime coverage registry and refreshed baseline summaries.
- **Files modified:** `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json`, `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json`, `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md`
- **Verification:** `bun run parity:gate:update-baseline` and `bun run parity:gate`
- **Committed in:** `14aea8ab`

---

**Total deviations:** 3 auto-fixed (1 missing critical, 1 bug, 1 blocking)
**Impact on plan:** All fixes were required to make the redistributed docs/parity inputs truthful and to get the planned parity gates green. No architectural scope change.

## Issues Encountered
- `python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline` initially failed because the existing CXX contract still described the retired `constants` bridge module. Regenerated the committed contract with `tools/cxx_api_parity/generate_baseline.py --write-baseline`, then reran the gate successfully.
- The first `cargo build --workspace` attempt hit a transient `LNK1105` file-lock on `classic_database.dll` immediately after parity refreshes. A clean retry succeeded once the lock cleared.

## User Setup Required

None - no external service configuration required.

## Authentication Gates

None.

## Known Stubs

None.

## Next Phase Readiness
- Phase 3 is closed with consolidated docs, refreshed parity baselines, and green workspace Rust closure.
- Phase 4 can consume the refreshed gate artifacts and treat GATE-01 through GATE-06 as ready for cross-phase validation rather than cleanup.

## Self-Check: PASSED

- Found `.planning/phases/03-constants-version-registry-merge/03-04-SUMMARY.md`
- Found task commit `903661b7`
- Found task commit `14aea8ab`

---
*Phase: 03-constants-version-registry-merge*
*Completed: 2026-04-12*
