---
phase: 06-repo-root-workspace-cutover
plan: 03
subsystem: infra
tags: [cargo, ci, docs, benchmarks, validation]

# Dependency graph
requires:
  - phase: 06-repo-root-workspace-cutover
    provides: repo-root workspace shell, moved benchmark support files, phase validation scaffold
provides:
  - Repo-root Rust CI commands and target caching
  - Cargo-native workspace-root and target-directory proof audits
  - Clean repo-root validation pass guarded from legacy ClassicLib-rs/target reuse
  - Always-on docs and agent skills aligned to repo-root Cargo commands
affects: [phase-07, phase-09, rust-ci, benchmark-workflow, agent-guidance]

# Tech tracking
tech-stack:
  added: []
  patterns: [Cargo-native root detection via cargo locate-project and cargo metadata, repo-root cargo command contract, validation audits for active workflow/docs surfaces]

key-files:
  created: [.planning/phases/06-repo-root-workspace-cutover/06-03-SUMMARY.md]
  modified: [.github/workflows/ci-rust.yml, .github/workflows/benchmarks.yml, tests/planning/test_phase06_validation.py, tests/planning/phase06_clean_run.ps1, README.md, AGENTS.md, CLAUDE.md, docs/api/QUICK_START.md, .claude/skills/ci-check/SKILL.md, .agents/skills/classic-project-guide/references/repo-guide.md]

key-decisions:
  - "Keep Rust CI on plain repo-root cargo commands and repo-root target caching with no --manifest-path compatibility shim."
  - "Use cargo locate-project --workspace plus cargo metadata --format-version 1 --no-deps as the authoritative Phase 6 root proof."
  - "Limit benchmark workflow changes in Phase 6 to the minimum repo-root path/config fixes needed to keep moved benchmark assets viable."
  - "Treat active always-on docs and quick-start surfaces as closure-critical and audit them for stale ClassicLib-rs workspace guidance."

patterns-established:
  - "Phase validation audits should cover workflows, clean-run helpers, and always-on docs together when a workspace contract changes."
  - "Clean proof scripts should rename legacy target directories before running repo-root cargo commands to prevent stale-cache false positives."

requirements-completed: [ROOT-01, ROOT-02]

# Metrics
duration: 1h 19m
completed: 2026-04-12
---

# Phase 6 Plan 3: Repo-root cargo workflow closure summary

**Repo-root Rust CI, Cargo-native workspace proof, and always-on guidance now align around the repository-root Cargo contract.**

## Performance

- **Duration:** 1h 19m
- **Started:** 2026-04-12T04:06:58-07:00
- **Completed:** 2026-04-12T05:26:03-07:00
- **Tasks:** 3
- **Files modified:** 32

## Accomplishments
- Rewired `ci-rust.yml` to plain repo-root cargo commands and repo-root `target` caching.
- Made the benchmark workflow's minimum Phase 6 repo-root path assumptions explicit and auditable.
- Added Cargo-native workspace-root/target-directory proof plus a clean validation helper that guards against `ClassicLib-rs/target` reuse.
- Synced active contributor docs, always-on agent instructions, and classic-project-guide copies to the repo-root Cargo contract.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewire Rust CI and enumerate the minimum repo-root benchmark workflow fixes** - `cf4b8853` (feat)
2. **Task 2: Add Cargo-native proof audits and run the clean root-workflow validation suite** - `a716e331` (feat)
3. **Task 3: Sync always-on and quick-start docs/skills to the repo-root Cargo contract** - `54cdf5f6` (docs)

**Related deviation fix:** `941b3abd` (fix)

## Files Created/Modified
- `.github/workflows/ci-rust.yml` - repo-root Rust CI commands and `target` cache paths.
- `.github/workflows/benchmarks.yml` - minimum repo-root path/config fixes for moved benchmark assets.
- `tests/planning/test_phase06_validation.py` - workflow, benchmark, root-detection, clean-run, and doc-sync audits.
- `tests/planning/phase06_clean_run.ps1` - clean proof helper that renames legacy `ClassicLib-rs/target` before validation.
- `README.md` - contributor-facing repo-root cargo quick reference.
- `AGENTS.md` - always-on repo guidance updated for the repo-root workspace shell.
- `CLAUDE.md` - always-loaded Claude instructions updated to repo-root cargo commands.
- `docs/README.md` - docs index routing aligned with the live repo-root workspace contract.
- `docs/api/QUICK_START.md` - contributor quick-start commands aligned to repo-root cargo.
- `.claude/skills/ci-check/SKILL.md` and classic-project-guide copies under `.claude/`, `.agents/`, `.opencode/`, `.agent/` - agent skill guidance aligned with repo-root cargo validation commands.

## Decisions Made
- Kept `ci-rust.yml` on plain repo-root cargo commands rather than any manifest-path compatibility layer so Phase 6 has one canonical workspace entrypoint.
- Used `cargo locate-project --workspace` and `cargo metadata --format-version 1 --no-deps` as the authoritative cutover proof instead of custom path checks.
- Limited `benchmarks.yml` changes to repo-root working/config/target viability instead of expanding Phase 6 into full benchmark CI closure.
- Treated `CLAUDE.md`, `docs/api/QUICK_START.md`, and agent skill copies as active contract surfaces that must pass the same stale-path audit as workflows.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cleared clean-run validation blockers exposed by the repo-root proof suite**
- **Found during:** Task 2
- **Issue:** The clean pass surfaced clippy/doc hygiene blockers on active public APIs and a Windows handle issue in the cargo-root audit path, preventing the required clean validation run from completing.
- **Fix:** Added missing public API documentation on the touched Rust/binding surfaces and updated the validation audit to use `subprocess.DEVNULL` stdin so the root-detection checks keep working after the legacy target directory is renamed.
- **Files modified:** `ClassicLib-rs/business-logic/classic-settings-core/src/yaml_file.rs`, `ClassicLib-rs/business-logic/classic-version-registry-core/src/fallout4_version.rs`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/{path,settings,version_registry,web,xse}.rs`, `ClassicLib-rs/foundation/classic-shared-core/src/game_id.rs`, `ClassicLib-rs/foundation/classic-shared-py/src/{game_id,lib}.rs`, `ClassicLib-rs/node-bindings/classic-node/src/{scanlog,shared,version_registry}.rs`, `ClassicLib-rs/python-bindings/classic-version-registry-py/src/lib.rs`, `tests/planning/test_phase06_validation.py`
- **Verification:** `pwsh -File tests/planning/phase06_clean_run.ps1`
- **Committed in:** `941b3abd`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix was required to complete the mandated clean-state proof. No architectural scope change.

## Issues Encountered
- The first clean-run proof exposed clippy/doc-comment failures and a Windows stdin-handle problem in the validation audit; both were fixed in `941b3abd` and the clean suite then passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 now has a complete repo-root Cargo contract, auditable workflow/doc coverage, and a clean proof artifact path.
- Ready for Phase 7 crate relocation work to move the crate tree while preserving the repo-root workspace entrypoint.

## Self-Check: PASSED

- Found `.planning/phases/06-repo-root-workspace-cutover/06-03-SUMMARY.md` on disk.
- Verified referenced commits `cf4b8853`, `a716e331`, `54cdf5f6`, and `941b3abd` exist in `git log --oneline --all`.
