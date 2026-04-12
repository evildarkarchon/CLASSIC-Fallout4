---
phase: 02-crashgen-config-merge
plan: 01
subsystem: infra
tags: [rust, cargo-workspace, crate-merge, crashgen-rules, pyo3, napi-rs]

requires:
  - phase: 01-yaml-settings-merge
    provides: 18-crate business-logic topology (post-Phase-1 baseline)
provides:
  - crashgen_rules module living inside classic-config-core
  - classic-config-core re-exports the full crashgen rule model (pub use crashgen_rules::*)
  - 17-crate business-logic topology (down from 18)
  - new classic-scangame-core -> classic-config-core dep edge
  - new classic-scangame-py -> classic-config-core dep edge
affects: [02-02 parity gates, phase-03 constants merge, phase-04 gate validation]

tech-stack:
  added: []
  patterns:
    - "Two-commit rename+edit pattern (Phase 1 precedent D-15) preserves git blame via git mv"
    - "Temporary stub lib.rs to keep workspace manifest loadable during intermediate state"

key-files:
  created:
    - ClassicLib-rs/business-logic/classic-config-core/src/crashgen_rules.rs
  modified:
    - ClassicLib-rs/business-logic/classic-config-core/src/lib.rs
    - ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs
    - ClassicLib-rs/business-logic/classic-config-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/crashgen_registry.rs
    - ClassicLib-rs/business-logic/classic-scangame-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-scangame-core/src/orchestrator.rs
    - ClassicLib-rs/business-logic/classic-scangame-core/src/crashgen_orchestrator.rs
    - ClassicLib-rs/business-logic/classic-scangame-core/src/toml.rs
    - ClassicLib-rs/node-bindings/classic-node/Cargo.toml
    - ClassicLib-rs/node-bindings/classic-node/src/crashgen_rules.rs
    - ClassicLib-rs/python-bindings/classic-config-py/Cargo.toml
    - ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/Cargo.toml
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/crashgen_rules.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/settings_validator.rs
    - ClassicLib-rs/python-bindings/classic-scangame-py/Cargo.toml
    - ClassicLib-rs/python-bindings/classic-scangame-py/src/crashgen_rules.rs
    - ClassicLib-rs/Cargo.toml

key-decisions:
  - "Added temporary stub lib.rs to classic-crashgen-settings-core in Task 2 so cargo could parse the workspace manifest during intermediate state (Rule 3 deviation — plan assumed package-scoped builds would bypass full workspace parse)"
  - "yamldata.rs.bak was gitignored (.gitignore:47 *.bak) so Task 5's git rm was replaced with a plain filesystem delete — no separate commit produced"

patterns-established:
  - "Workspace-member crate merges require an intermediate stub lib.rs so cargo can load the manifest until the directory is deleted in the cleanup task"

requirements-completed: [CGEN-01, CGEN-02, CGEN-03]

duration: ~18 min
completed: 2026-04-11
---

# Phase 2 Plan 1: Crashgen-Config Merge Summary

**classic-crashgen-settings-core absorbed into classic-config-core — crashgen rule model now lives in config-core::crashgen_rules with all 3 Rust cores + 4 bindings migrated, workspace trimmed from 18 to 17 business-logic crates.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-11T11:25Z
- **Completed:** 2026-04-11T11:43Z
- **Tasks:** 4 of 5 (Task 5 was a no-op — see Deviations)
- **Files modified:** 22 (1 created, 21 modified, 2 deleted via git rm -r)

## Accomplishments

- Moved `classic-crashgen-settings-core/src/lib.rs` -> `classic-config-core/src/crashgen_rules.rs` via isolated `git mv` commit (blame preserved, R100)
- Wired `mod crashgen_rules; pub use crashgen_rules::*;` into `classic-config-core/src/lib.rs`
- Migrated 3 Rust core crates (config-core, scanlog-core, scangame-core) to import crashgen types from `classic_config_core::`
- Migrated 4 binding crates (classic-node, classic-config-py, classic-scanlog-py, classic-scangame-py) to same path — no file renames per D-09, doc comments updated per M1
- Added new dep edge `classic-scangame-core -> classic-config-core` (D-05)
- Added new dep edge `classic-scangame-py -> classic-config-core` (D-10 trap guard)
- Deleted `classic-crashgen-settings-core/` directory and removed workspace-member entry
- Full workspace `cargo build`, `cargo test`, `cargo clippy --all-targets --all-features -- -D warnings`, and `cargo fmt --check` all green

## Task Commits

1. **Task 1: git mv rename-only** — `68fe50d9` (Refactor) — pure R100 rename, blame preserved
2. **Task 2: Rust core content edits** — `48f1958d` (Refactor) — config-core re-export, 3 consumer migrations, stub lib.rs for intermediate state
3. **Task 3: Binding migration** — `e1db8e49` (Refactor) — 4 bindings migrated, scangame-py gains new config-core dep
4. **Task 4: Delete crate + workspace entry + full verify** — `a8b8f6bd` (Refactor) — directory deletion, workspace member trim, cargo fmt cleanup of Task 2/3 touched files

## Cargo Tree Delta

`classic-scangame-core` (new edge):
```
classic-scangame-core v9.0.0
├── classic-config-core v9.0.0  <-- NEW
├── classic-file-io-core v9.0.0
├── classic-path-core v9.0.0
├── classic-shared-core v9.0.0
└── classic-version-registry-core v9.0.0
```
(formerly had `classic-crashgen-settings-core` here — now gone)

`classic-scangame-py` (new edge):
```
classic-scangame-py v9.0.0
├── classic-config-core v9.0.0  <-- NEW
├── classic-file-io-core v9.0.0
├── classic-scangame-core v9.0.0
├── classic-shared-core v9.0.0
└── classic-shared-py v9.0.0
```

## Workspace Crate Count

- Pre-Phase-2: 18 business-logic crates
- Post-Phase-2: **17 business-logic crates** (verified via `Select-String -Path ClassicLib-rs/Cargo.toml -Pattern 'business-logic/' | Measure-Object`)

## Decisions Made

1. **Intermediate stub lib.rs for workspace parse (Rule 3 deviation)** — Plan assumed `cargo build -p <pkg>` would bypass the broken workspace member. It does not: cargo parses the full workspace manifest for any invocation under that manifest, so the orphaned `classic-crashgen-settings-core/Cargo.toml` (whose `src/lib.rs` was removed by Task 1's git mv) prevented even package-scoped builds. Fix: add a minimal stub `src/lib.rs` (~3 doc lines) to the orphaned crate as part of Task 2, then delete the whole directory in Task 4. The stub never contains real code and is removed with `git rm -rf` in Task 4.

2. **Task 5 (yamldata.rs.bak delete) became a filesystem-only op** — `.gitignore` line 47 (`*.bak`) excluded the file from git tracking, so `git rm` fails with "pathspec did not match any files". The file has been deleted from the filesystem, but no separate Chore commit was produced because there was nothing to stage. This matches D-17's intent (clean up the stray) but not its letter (separate commit).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added stub lib.rs to orphaned classic-crashgen-settings-core**
- **Found during:** Task 2 Step E (package-scoped build verification)
- **Issue:** `cargo build -p classic-config-core -p classic-scanlog-core -p classic-scangame-core` failed with `failed to load manifest for workspace member 'classic-crashgen-settings-core' / can't find library 'classic_crashgen_settings_core', rename file to 'src/lib.rs'`. The plan's D-13 design assumed package-scoped builds would bypass the broken crate, but cargo always parses the full workspace manifest — the orphaned Cargo.toml (whose lib.rs was removed by Task 1's git mv) broke everything.
- **Fix:** Wrote a 3-line stub `src/lib.rs` in `classic-crashgen-settings-core` containing only a doc comment explaining it's a placeholder. Commited as part of Task 2. Task 4's `git rm -rf` removed it cleanly.
- **Files modified:** `ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs` (stub, later deleted)
- **Verification:** `cargo build -p classic-config-core -p classic-scanlog-core -p classic-scangame-core` exit 0 after the stub was added.
- **Committed in:** `48f1958d` (Task 2 commit); removed in `a8b8f6bd` (Task 4 commit)

**2. [Rule 3 - Blocking] Task 5 became filesystem-only delete (no separate commit)**
- **Found during:** Task 5 Step 1 (`git rm yamldata.rs.bak`)
- **Issue:** `git rm` failed with `pathspec 'yamldata.rs.bak' did not match any files`. Investigation with `git check-ignore -v` revealed `.gitignore:47` contains `*.bak`, so the stray file was never tracked by git. D-17's requirement of "separate commit for the .bak deletion" is mechanically impossible when there's nothing for git to stage.
- **Fix:** Deleted the file from the filesystem with a plain `rm`. The file is gone (`Test-Path` returns False). No commit produced — but the cleanup intent of D-17 is satisfied.
- **Files modified:** `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs.bak` (filesystem deletion, not a git commit)
- **Verification:** `test -f` returns "deleted".
- **Committed in:** Not committed (pre-existing gitignore rule blocked tracking).

**3. [Rule 1 - Bug] cargo fmt cleanup of Task 2 + Task 3 files**
- **Found during:** Task 4 Step C (final `cargo fmt --all -- --check`)
- **Issue:** `cargo fmt --check` flagged two files touched by Tasks 2 and 3: the regex-based path replacement in Task 2 didn't produce rustfmt-canonical `use` blocks in `classic-scanlog-core/src/orchestrator.rs`, and `classic-config-py/src/lib.rs` had its `use classic_config_core::{...}` block split across two `use` statements in wrong order.
- **Fix:** Ran `cargo fmt --all` to normalize. Two files auto-reformatted. Staged into the Task 4 commit (documented in its message).
- **Files modified:** `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs`, `ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs`
- **Verification:** `cargo fmt --all -- --check` exit 0 after fix.
- **Committed in:** `a8b8f6bd` (Task 4 commit)

---

**Total deviations:** 3 (2 blocking, 1 bug) — all auto-fixed per Rules 1/3.
**Impact on plan:** No scope creep. Deviation #1 (stub lib.rs) is a gap in the plan's build-sequencing model that should be captured as a pattern for phase 3 constants merge. Deviation #2 (Task 5 no-op) is a cosmetic plan inaccuracy — the cleanup is done, but the git log shows 4 plan commits instead of the expected 5. Deviation #3 (fmt cleanup) is standard post-edit hygiene.

## Issues Encountered

None beyond the deviations above. Full workspace build, test, and clippy sailed through on first post-fmt attempt.

## Verification Results

All Phase-level verification items passed:

| Check | Result |
|---|---|
| `cargo build --workspace` | PASS (finished in 54.82s) |
| `cargo test --workspace` | PASS (all tests green, 0 failed) |
| `cargo clippy --workspace --all-targets --all-features -- -D warnings` | PASS (finished in 33.50s) |
| `cargo fmt --all -- --check` | PASS (after Task 4 fmt cleanup) |
| Full grep `classic[-_]crashgen[-_]settings[-_]core` in `ClassicLib-rs/` (excluding `.idea/`) | 0 matches |
| `Test-Path classic-crashgen-settings-core` | False |
| `Test-Path yamldata.rs.bak` | False |
| Workspace members `business-logic/` count | 17 (down from 18) |

## Self-Check: PASSED

- Task commits `68fe50d9`, `48f1958d`, `e1db8e49`, `a8b8f6bd` all present in `git log --oneline -6`.
- `ClassicLib-rs/business-logic/classic-config-core/src/crashgen_rules.rs` exists (verified via Read).
- `ClassicLib-rs/business-logic/classic-crashgen-settings-core/` directory no longer exists (verified via `Test-Path` in the verification table above).
- Phase-level verification all green.

## Next Phase Readiness

- Rust source-level merge complete. Plan 02-02 handles parity-gate refresh (CXX, Node, Python) for the renamed symbols and new import path — deferred per plan output spec.
- Pattern captured for Phase 3 constants merge: when deleting a crate from a workspace, the intermediate state between `git mv` and final `git rm -rf` requires a stub `lib.rs` in the orphaned crate, otherwise cargo cannot parse the workspace manifest.
- No blockers for phase 03 (constants merge) or phase 04 (gate validation).

---
*Phase: 02-crashgen-config-merge*
*Completed: 2026-04-11*
