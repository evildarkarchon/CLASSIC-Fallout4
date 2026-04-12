---
phase: 06-repo-root-workspace-cutover
plan: 01
subsystem: infra
tags: [cargo, workspace, rust, powershell, python]
requires:
  - phase: 06-00
    provides: validation scaffold and clean-run helper for Phase 6 audits
provides:
  - repo-root virtual Cargo workspace manifest and shared lock/config files
  - repo-root validate_stubs.py entrypoint with explicit Phase 6 rust-dir normalization
  - rebuild_rust.ps1 repo-root cargo invocation without legacy manifest-path usage
affects: [06-02, 06-03, ci-rust, python-bindings, benchmark-support]
tech-stack:
  added: []
  patterns: [repo-root virtual Cargo workspace, transitional rust-dir normalization, plain cargo workspace invocation]
key-files:
  created: [.planning/phases/06-repo-root-workspace-cutover/06-01-SUMMARY.md]
  modified: [Cargo.toml, Cargo.lock, .cargo/config.toml, validate_stubs.py, rebuild_rust.ps1, tests/planning/test_phase06_validation.py]
key-decisions:
  - "Keep the promoted root manifest as a virtual workspace with resolver = \"2\" and no default-members so plain repo-root cargo commands still cover the full workspace."
  - "Normalize both repo-root and explicit ClassicLib-rs --rust-dir inputs to the live ClassicLib-rs/python-bindings tree during the Phase 6 transition."
  - "Remove rebuild_rust.ps1 dependence on ClassicLib-rs/Cargo.toml and use plain repo-root cargo commands while preserving real crate and bindings paths."
patterns-established:
  - "Workspace shell promotion: move Cargo.toml, Cargo.lock, and .cargo/config.toml to repo root together and retire the legacy copies in the same cutover."
  - "Helper transition compatibility: root tools may accept legacy ClassicLib-rs paths temporarily, but the default contract is the repo root."
requirements-completed: [ROOT-01, ROOT-02]
duration: 5 min
completed: 2026-04-12
---

# Phase 06 Plan 01: Promote the repo-root workspace shell and root-aware helper scripts Summary

**Repo-root virtual Cargo workspace with migrated lock/config files, root-default stub validation, and repo-root rebuild orchestration**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-12T12:38:21Z
- **Completed:** 2026-04-12T12:43:21Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Promoted the authoritative Cargo workspace shell to the repository root and removed the legacy `ClassicLib-rs` manifest/config/lockfile copies.
- Retargeted `validate_stubs.py` so repo root is the default contract while explicit `ClassicLib-rs` input still resolves correctly during Phase 6.
- Rewired `rebuild_rust.ps1` to use plain repo-root Cargo commands and expanded the Phase 6 planning audit to assert the new invariants.

## Task Commits

Each task was committed atomically:

1. **Task 1: Promote the workspace shell and root-scoped Cargo files to repo root** - `c5a92a85` (feat)
2. **Task 2: Retarget `validate_stubs.py` and `rebuild_rust.ps1` to the new repo-root contract** - `2d3b773e` (feat)

**Plan metadata:** pending docs commit created after summary/state updates.

## Files Created/Modified
- `Cargo.toml` - Canonical repo-root virtual workspace manifest with `ClassicLib-rs/...` member paths.
- `Cargo.lock` - Shared workspace lockfile moved to repo root.
- `.cargo/config.toml` - Repo-root Cargo aliases and profile command discovery.
- `validate_stubs.py` - Repo-root stub validation entrypoint with transitional `--rust-dir` normalization.
- `rebuild_rust.ps1` - Repo-root Cargo rebuild orchestration without legacy manifest-path usage.
- `tests/planning/test_phase06_validation.py` - Phase 6 audits for root manifest, helper-script, and alias invariants.

## Decisions Made
- Preserved the workspace as a virtual root manifest with `resolver = "2"` and no `default-members` to keep plain repo-root Cargo behavior stable.
- Treated repo root as the default `validate_stubs.py` contract but preserved explicit `ClassicLib-rs` compatibility during the transition.
- Replaced old manifest-path calls in `rebuild_rust.ps1` with plain repo-root Cargo invocations while leaving real crate and binding directories untouched for later phases.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The two task commits for this plan were already present on the working branch; I verified their audit commands and finalized the execution metadata instead of duplicating code commits.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 now has a single live repo-root Cargo workspace shell and root-aware helper entrypoints.
- Ready for `06-02-PLAN.md` to move benchmark-owned support files and remove the old benchmark copies.

## Self-Check: PASSED
- FOUND: `.planning/phases/06-repo-root-workspace-cutover/06-01-SUMMARY.md`
- FOUND: `c5a92a85`
- FOUND: `2d3b773e`

---
*Phase: 06-repo-root-workspace-cutover*
*Completed: 2026-04-12*
