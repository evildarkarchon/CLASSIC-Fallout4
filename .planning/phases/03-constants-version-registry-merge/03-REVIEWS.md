---
phase: 3
reviewers: [gemini, claude, codex]
reviewed_at: 2026-04-11T16:45:41.3719018-07:00
plans_reviewed: [03-01-PLAN.md, 03-02-PLAN.md, 03-03-PLAN.md, 03-04-PLAN.md]
---

# Cross-AI Plan Review - Phase 3

## Gemini Review

### Summary
The four subplans correctly distribute the structural work across the Rust core (03-01), Python bindings (03-02), Node/CXX bindings (03-03), and parity/doc closure (03-04), faithfully following the three-target redistribution strategy established in the Phase 3 Context. The integration of the CXX `classic::shared` namespace (with the 5-place registration rule) and the comprehensive updates across the workspace are accurately mapped out. However, there is a critical sequence flaw inherited from the Context document: `classic-constants-core` is slated for full deletion in 03-01, but the test migration for its contents is deferred until 03-04.

### Strengths
- **Thorough Dependency Management**: Correctly maps the `classic-constants-core` symbol split (`Fallout4Version`, `YamlFile`, `GameId`) to their respective destinations.
- **Strict Registration**: Reuses the 5-place registration checklist for the new `classic-cpp-bridge/src/shared.rs` CXX module, ensuring the build scripts and CMake headers won't silently drop the module.
- **Binding Accuracy**: The carve-up of Python and Node constants into semantic modules aligns perfectly with the Rust layer changes without leaving legacy compatibility buckets.
- **Appropriate Tooling Usage**: Delegates the `index.d.ts` update to the NAPI-RS build step instead of hand-editing, avoiding type signature drift.

### Concerns
- **HIGH: Orphaned/Deleted Test Coverage**: 03-01-PLAN deletes `classic-constants-core` and its directory, but 03-04-PLAN Task 1 is scheduled to split the old `classic-constants-core/src/lib.rs` test coverage. By the time 03-04 executes, the source file containing the tests will be gone.
- **MEDIUM: Redundant Test Updates**: Both 03-02-PLAN Task 2 and 03-04-PLAN Task 1 include `test_promoted_residuals_smoke.py`, which risks duplicate or conflicting changes.
- **LOW: Parity Helper Limitations**: 03-04-PLAN Task 3 references the Phase 1 helper pattern for owner reparenting, but this is a 1-to-3 split rather than a 1-to-1 merge.

### Suggestions
- Move test migration into 03-01-PLAN so tests travel with the code before source deletion.
- Remove `test_promoted_residuals_smoke.py` from 03-04 to avoid duplicate migration work.
- Clarify that parity ownership reparenting may need a one-off split-aware helper instead of blindly reusing a 1-to-1 merge helper.

### Risk Assessment
**HIGH**. The sequence flaw around test deletion is the main risk. Fixing the task alignment lowers overall risk significantly.

---

## the agent Review

# Phase 3: Constants Redistribution — Cross-AI Plan Review

## Two Critical Cross-Plan Issues

### 1. Crate Deletion Timing (HIGH)

03-01 Task 2 deletes `classic-constants-core` from the workspace. But multiple binding crates still have it in their `Cargo.toml`:
- `classic-scanlog-py/Cargo.toml` (updated in 03-02)
- `classic-node/Cargo.toml` (updated in 03-03)
- `classic-cpp-bridge/Cargo.toml` (updated in 03-03)

**This creates a broken workspace between 03-01 and 03-02/03-03** — `cargo build --workspace` will fail.

**Fix:** Expand 03-01 Task 2 to update all `Cargo.toml` dependency references workspace-wide, not just the 5 Rust core consumers. Binding crate `Cargo.toml` dependency swaps happen in 03-01; 03-02/03-03 only handle source file content moves and registrations.

### 2. Test Migration Timing (HIGH)

03-04 Task 1 says to split the old `classic-constants-core/src/lib.rs` test coverage. But that file is deleted in 03-01 Task 2. By the time 03-04 executes, the source tests are gone from disk.

**Fix:** Move test migration into 03-01 Task 1. Add `#[cfg(test)] mod tests { ... }` blocks to `fallout4_version.rs`, `yaml_file.rs`, and `game_id.rs` during the initial redistribution.

## 03-01-PLAN.md — Rust Core Redistribution

**Summary:** Well-structured with the proven move-then-sweep pattern, but consumer enumeration is incomplete.

**Strengths:**
- Clean two-task structure matching Phase 1/2 precedent.
- Correctly references all locked decisions D-02 through D-14.
- Includes doc-comment-only references (`classic-registry-core` / `keys.rs`).
- Verification targets both moved crates and consumers separately.

**Concerns:**
- **HIGH** — Missing binding crate `Cargo.toml` updates.
- **HIGH** — `classic-config-core` not verified as a consumer; Phase 2 may have carried a constants dependency forward.
- **MEDIUM** — `classic-path-core/src/docs_path.rs` is listed in frontmatter but absent from Task 2's `<files>` and action text.
- **MEDIUM** — `phf` dependency question is unresolved.
- **LOW** — No intermediate `cargo build --workspace` between Task 1 and Task 2.

**Suggestions:**
- Add all binding crate `Cargo.toml` dependency swaps to Task 2.
- Grep for `classic-constants-core` and `classic_constants_core` across all `Cargo.toml` and `.rs` files as the first action in Task 2.
- Resolve `phf` usage explicitly before moving code.
- Move test code from 03-04 into Task 1.

**Risk:** MEDIUM, or HIGH if the cross-plan issues remain.

## 03-02-PLAN.md — Python Binding Carve

**Summary:** Well-scoped with established PyO3 patterns, but it has a subtle correctness issue with `#[pyclass(module)]` attributes.

**Strengths:**
- Clean separation between creating the new surface and migrating consumers.
- Correctly identifies `classic-scanlog-py` as a consumer.
- Explicit `.pyi` updates alongside Rust wrapper moves.
- Rejects a compatibility shim, aligned with locked decisions.

**Concerns:**
- **HIGH** — `#[pyclass(module = "classic_constants")]` must be retagged to the new module names (`classic_settings`, `classic_shared`, `classic_version_registry`).
- **MEDIUM** — `NULL_VERSION` is not explicitly tracked in the dispersal checklist.
- **MEDIUM** — Verification scripts should be checked for hardcoded `classic_constants` assumptions.
- **LOW** — Verify dependency wiring for the new `YamlFile` wrapper.

**Suggestions:**
- Add an explicit instruction to rename `#[pyclass(module = ...)]` attributes.
- Track `NULL_VERSION` and `SETTINGS_IGNORE_NONE` as module-level constants.
- Add a runtime module-name check for the moved Python classes.

**Risk:** MEDIUM.

## 03-03-PLAN.md — Node + CXX Bridge Dispersal

**Summary:** This is the most mechanically complex plan. The CXX five-place registration is well-covered, but there is a test migration gap and a namespace/type-collision check that should be explicit.

**Strengths:**
- Explicitly carries forward the five-place CXX registration lesson.
- Identifies all three CXX consumer files needing import swaps.
- Correctly leaves `index.d.ts` regeneration to the normal Node build.
- Uses the right dependency on 03-01.

**Concerns:**
- **HIGH** — `constants.spec.ts` is listed in `files_modified` but not addressed in Task 1 action text.
- **MEDIUM** — CXX bridge type names should be pre-checked for conflicts in existing bridge blocks.
- **MEDIUM** — `Cargo.toml` delta should be explicit if dependency swaps stay in this plan.
- **LOW** — Clarify whether `include/classic_cxx_bridge/` is fully regenerated from `build.rs`.

**Suggestions:**
- Explicitly migrate or defer `constants.spec.ts` with rationale.
- Pre-check for conflicting CXX type names.
- If dependency-swap timing is fixed in 03-01, remove the `Cargo.toml` dependency edits from this plan.

**Risk:** MEDIUM-HIGH.

## 03-04-PLAN.md — Tests, Docs, Parity Gates

**Summary:** Broad but sensible closeout scope. The parity and doc work are well-defined, but test timing and generator sequencing need tightening.

**Strengths:**
- Correctly regenerates all three parity gates.
- Explicitly requires verifying the Phase 1 submodule-scan fix.
- Covers the main active doc sweep targets.
- Uses the right wave dependency ordering.

**Concerns:**
- **HIGH** — Test migration timing problem described above.
- **HIGH** — Generator target maps still reference `classic-constants-core`; task ordering must ensure maps are edited before regeneration.
- **MEDIUM** — Doc verification grep exclusion for `binding-parity-overview.md` may be too broad.
- **MEDIUM** — `classic-shared-core.md` placement for `GameId` should be explicit.
- **LOW** — Verify the exact parity gate CLI flags.

**Suggestions:**
- If tests move to 03-01, simplify 03-04 Task 1 accordingly.
- Reorder Task 3 to: edit maps, verify submodule scan, regenerate, run gates.
- Verify parity gate CLI flags before execution.

**Risk:** HIGH as written, LOW if the task-ordering issues are fixed.

## Overall Risk Assessment

**MEDIUM-HIGH as written.** The two structural issues are:
1. Crate deletion before all binding `Cargo.toml` files are migrated.
2. Test migration after the source crate is already deleted.

With both fixes, the plan set drops to LOW-MEDIUM risk because it otherwise follows the Phase 1/2 pattern closely.

---

## Codex Review

The plan set is close, but two issues make it unsafe as written: `03-01` tries to remove `classic-constants-core` before later waves have migrated all binding crates off it, and `03-03` misses an actual GUI consumer of `classic::constants`.

**03-01-PLAN.md**

**Summary**
Strong Rust-side decomposition and consumer sweep. The main flaw is sequencing: it deletes `classic-constants-core` and then asks for a full workspace build even though later plans still own live dependencies on that crate.

**Strengths**
- Correct semantic split for `Fallout4Version`, `YamlFile`, and `GameId`.
- Explicitly handles the convenience re-export removal in `classic-version-core`.
- Includes dead-dependency inspection for `classic-resource-core`.
- Uses destination-crate tests plus a broader build step.

**Concerns**
- `HIGH` The verification step `cargo build --workspace` is not compatible with the wave breakdown. After `03-01`, live crates still depend on `classic-constants-core`: `classic-node/Cargo.toml`, `classic-cpp-bridge/Cargo.toml`, and `classic-scanlog-py/Cargo.toml`.
- `MEDIUM` The moved source file contains many doctest examples using `classic_constants_core::*`; the plan relies on `cargo test` to catch that, but does not call the rewrites out explicitly.

**Suggestions**
- Make 03-01 verification Rust-slice only, or move crate deletion until 03-02 and 03-03 have migrated all remaining dependents.
- Add an explicit checklist to rewrite doctest and import examples during the move.

**Risk Assessment**
`HIGH` because the plan's own verification cannot pass with the current wave boundaries.

**03-02-PLAN.md**

**Summary**
Good semantic carve for Python, with the right target crates and no compatibility shim. The weak point is verification: it changes `classic-scanlog-py` but never explicitly rebuilds that module.

**Strengths**
- Correct three-way split across `classic-version-registry-py`, `classic-settings-py`, and `classic-shared-py`.
- Explicitly deletes `classic-constants-py` instead of keeping a forwarding layer.
- Includes stub validation and smoke-test updates.

**Concerns**
- `HIGH` Task 2 edits `classic-scanlog-py`, but the verify step does not rebuild `classic_scanlog`, which can hide a broken Rust extension behind stale artifacts.
- `MEDIUM` The source wrappers are annotated with `#[pyclass(module = "classic_constants", ...)]`; the plan should explicitly require retagging those module names and their doc examples.

**Suggestions**
- Rebuild `classic_scanlog` in Task 2 verification, not just the three destination modules.
- Explicitly call out `#[pyclass(module = ...)]`, `#[pymodule]`, and doctest/example rewrites as part of the carve.
- Add a targeted import smoke that loads all four affected Python modules in one run.

**Risk Assessment**
`MEDIUM` because the implementation shape is good, but the current verify steps are too narrow.

**03-03-PLAN.md**

**Summary**
The Node/CXX redistribution is conceptually right, and the five-place CXX registration note is exactly the right lesson to carry forward. The serious miss is that the plan forgets a live GUI consumer of `classic::constants`.

**Strengths**
- Correctly removes the `constants` bucket from both Node and CXX.
- Preserves stable public symbol names while moving ownership.
- Explicitly includes the CXX registration sites and dependency rewiring.

**Concerns**
- `HIGH` The GUI still includes and uses the retired bridge surface in `classic-gui/src/app/mainwindow.cpp`, but that file is not in `files_modified`, so the plan does not complete the C++ migration.
- `MEDIUM` Task 2 edits both `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt`, but only verifies `classic-cli/build_cli.ps1 -Test`.
- `LOW` The Node verify commands should make the working directory explicit.

**Suggestions**
- Add `classic-gui/src/app/mainwindow.cpp` to the plan and migrate its include/namespace usage off `constants.h` / `classic::constants`.
- Verify both native wrappers, or at least run a GUI build after changing `classic-gui/CMakeLists.txt`.
- Make the Node working directory explicit in the verify block.

**Risk Assessment**
`HIGH` because there is a known native consumer the plan does not touch.

**03-04-PLAN.md**

**Summary**
This is a solid closeout plan: tests, docs, and parity are in the right final wave. The gaps are mostly around verification coverage rather than scope definition.

**Strengths**
- Treats parity regeneration as first-class work instead of an afterthought.
- Rehomes Rust tests into the destination crates.
- Includes the main active API docs and parity artifacts.

**Concerns**
- `MEDIUM` The docs verification grep only scans `docs/api` and `.planning/codebase`, but the task also claims updates to `CLAUDE.md` and `.planning/PROJECT.md`.
- `MEDIUM` `bun run parity:gate:local` needs to run from the Node package directory.
- `LOW` There is no explicit final structural assertion that active files no longer reference `classic-constants-core` / `classic_constants` outside approved historical/archive paths.

**Suggestions**
- Expand doc verification to include `CLAUDE.md`, `.planning/PROJECT.md`, and other active non-archived docs.
- State the Node parity working directory explicitly.
- Add one final repo-wide search over live paths to prove the old crate/module names are gone.

**Risk Assessment**
`MEDIUM` because the closeout scope is right, but the verification net should be wider.

**Overall**
`HIGH` as written. The architecture and task partitioning are strong, but `03-01` is not self-consistent with its own workspace-build gate, and `03-03` misses a real C++ frontend consumer. Fix those two points and the plan set becomes workable.

---

## Consensus Summary

The reviewers agree the phase architecture is directionally correct: the three-way semantic redistribution is sound, the binding splits match the Rust ownership model, and the CXX `classic::shared` addition is handled with the right five-place registration mindset. The main problems are execution-order and completeness gaps, not plan intent.

### Agreed Strengths
- The semantic split of `Fallout4Version`, `YamlFile`, and `GameId` is correct.
- Binding work is partitioned sensibly across Python, Node, and CXX without retaining compatibility buckets.
- The plan correctly treats CXX registration and parity regeneration as first-class work.

### Agreed Concerns
- **Highest priority:** 03-01 deletes `classic-constants-core` too early. Multiple later-wave binding crates still depend on it in `Cargo.toml`, so the workspace build step cannot pass as written.
- **High priority:** Test migration is scheduled too late. Moving tests in 03-04 after deleting the source crate in 03-01 risks losing or orphaning `classic-constants-core` coverage.
- **Medium priority:** Python moved wrappers need explicit `#[pyclass(module = ...)]` retagging and related module-name/doc updates.

### Divergent Views
- Codex uniquely flagged a likely missing GUI consumer in `classic-gui/src/app/mainwindow.cpp` that still uses the retired CXX constants surface.
- the agent uniquely flagged missing treatment of `classic-node/__test__/constants.spec.ts`, a possible carried-forward `classic-config-core` consumer, and incomplete 03-04 generator-task ordering.
- Gemini uniquely flagged duplicate ownership of `test_promoted_residuals_smoke.py` across 03-02 and 03-04, plus the risk that a Phase 1 one-to-one parity helper is a poor fit for a one-to-three split.

### Recommended Replan Inputs
1. Move all workspace-wide dependency swaps needed for crate deletion into 03-01 before removing `classic-constants-core`.
2. Move constants test migration into 03-01 alongside the initial code carve.
3. Update 03-02 to explicitly retag `#[pyclass(module = ...)]`, track `NULL_VERSION`, and rebuild `classic-scanlog-py` in verification.
4. Update 03-03 to cover `classic-gui/src/app/mainwindow.cpp` if Codex's finding is confirmed, and explicitly handle `constants.spec.ts`.
5. Tighten 03-04 verification ordering and widen final live-reference checks across active docs and parity tooling.
