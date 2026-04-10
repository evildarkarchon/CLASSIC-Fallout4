---
phase: 06-documentation-reset
plan: 02
subsystem: documentation
tags: [governance-cleanup, binding-parity, error-contract, documentation-reset]

# Dependency graph
requires:
  - phase: 06-documentation-reset plan 01
    provides: Audit trail committed, gate scripts cleaned, baselines refreshed
provides:
  - Clean docs/ tree with no Tier-2 governance artifacts
  - Harmony-achieved binding parity overview with source-verified per-crate table
  - One-tier binding parity policy with new-API contributor workflow
  - Per-binding error contract documentation with factually correct examples
affects: [docs/api/, docs/development/ci_cd_guide.md]

# Tech tracking
tech-stack:
  added: []
  patterns: [harmony-achieved documentation, one-tier parity policy, error-contract-as-design-choice]

key-files:
  created:
    - docs/api/binding-parity-policy.md
    - docs/api/error-contract.md
  modified:
    - docs/api/binding-parity-overview.md
    - docs/api/binding-contract-refresh-note.md
    - docs/api/node-python-contract-map.md
    - docs/api/README.md
    - docs/development/ci_cd_guide.md
  deleted:
    - docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json
    - docs/implementation/python_api_parity/governance/tier2_wave_manifest.json
    - docs/implementation/node_api_parity/governance/per_wave_acceptance_template.md
    - docs/implementation/node_api_parity/governance/tier2_wave_manifest.json
    - docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md
    - docs/implementation/node_api_parity/governance/gate_contract_baseline.md
    - docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json

key-decisions:
  - "Full rewrite of binding-parity-overview.md with harmony-achieved framing instead of patching the existing narrowing/omission document"
  - "classic-resource-core honestly marked as Not exposed through C++ bridge -- no false (via files.rs) claim"
  - "Error contract documented as intentional design, not inconsistencies to fix, with source-verified examples"

patterns-established:
  - "One-tier parity policy: no deferred tier, no backlog tier, no graduated promotion"
  - "All three binding gates (CXX, Node, Python) referenced consistently across docs"

requirements-completed: [DOC-02, DOC-03, DOC-05, DOC-06, DOC-07, HARM-05]

# Metrics
duration: 7min
completed: 2026-04-10
---

# Phase 6 Plan 02: Governance Deletion and Documentation Rewrite Summary

**Deleted all 8 Tier-2 governance files, rewrote binding-parity-overview as harmony-achieved reference with source-verified per-crate table, created one-tier parity policy doc and error-contract doc, and cleaned all stale governance references from docs/**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-10T07:44:27Z
- **Completed:** 2026-04-10T07:52:00Z
- **Tasks:** 2
- **Files modified/created/deleted:** 15

## Accomplishments
- Deleted 3 Python and 5 Node governance files (tier2_backlog, wave_manifest, deferred_runtime_backlog, gate_contract_baseline, per_wave_acceptance_template)
- Rewrote binding-parity-overview.md from scratch with harmony-achieved framing and 20-row source-verified per-crate table
- Created binding-parity-policy.md with one-tier policy statement, gate ownership for all three surfaces, and step-by-step new-API workflow
- Created error-contract.md documenting C++ empty-string sentinels, Node error.code strings, and Python typed exceptions with correct source examples
- Updated binding-contract-refresh-note.md with new C++ Bridge section and three-gate coverage
- Updated node-python-contract-map.md removing deferred/governance language
- Updated ci_cd_guide.md replacing governance references with triple-gate parity workflow
- Updated README.md index with both new docs and revised descriptions

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete governance files and update docs with governance references** - `d86c77f5` (chore)
2. **Task 2: Create binding-parity-overview rewrite, binding-parity-policy, and error-contract docs** - `6585f6cc` (docs)

## Files Created/Modified/Deleted

### Created
- `docs/api/binding-parity-policy.md` - One-tier parity policy with gate ownership and new-API contributor workflow
- `docs/api/error-contract.md` - Per-binding error shape conventions with C++, Node, Python examples

### Modified
- `docs/api/binding-parity-overview.md` - Full rewrite as harmony-achieved reference with source-verified per-crate table
- `docs/api/binding-contract-refresh-note.md` - Added C++ Bridge section, three-gate coverage, removed governance links
- `docs/api/node-python-contract-map.md` - Replaced deferred/governance language with policy links
- `docs/api/README.md` - Added entries 35-36 for new docs, updated entry 30 description
- `docs/development/ci_cd_guide.md` - Replaced governance references with triple-gate parity workflow

### Deleted
- `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md`
- `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`
- `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json`
- `docs/implementation/node_api_parity/governance/per_wave_acceptance_template.md`
- `docs/implementation/node_api_parity/governance/tier2_wave_manifest.json`
- `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md`
- `docs/implementation/node_api_parity/governance/gate_contract_baseline.md`
- `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`

## Decisions Made
- Full rewrite of binding-parity-overview.md rather than patching existing doc -- the old narrowing/omission framing was incompatible with harmony-achieved state
- classic-resource-core honestly marked as "Not exposed" through C++ bridge -- no false "(via files.rs)" claim
- Error shapes documented as intentional design choices, not inconsistencies -- references Out of Scope decision

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - no stubs or placeholder data in this plan's output.

## Next Phase Readiness
- All governance files deleted, audit trail preserved in Plan 01
- Documentation tree is clean: zero stale governance references
- Three new/rewritten reference docs cover the full binding surface story

## Self-Check: PASSED

- docs/api/binding-parity-policy.md: FOUND
- docs/api/error-contract.md: FOUND
- docs/api/binding-parity-overview.md: FOUND (rewritten)
- docs/api/binding-contract-refresh-note.md: FOUND (updated)
- docs/api/README.md: FOUND (updated)
- Commit d86c77f5: FOUND
- Commit 6585f6cc: FOUND
- Governance files deleted: all 8 confirmed absent from git index
- grep sweep for stale governance references: zero matches

---
*Phase: 06-documentation-reset*
*Completed: 2026-04-10*
