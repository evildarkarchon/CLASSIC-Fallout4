---
phase: 3
reviewers: [gemini, claude, codex]
reviewed_at: 2026-04-11T17:22:36.3266045-07:00
plans_reviewed: [03-01-PLAN.md, 03-02-PLAN.md, 03-03-PLAN.md, 03-04-PLAN.md]
---

# Cross-AI Plan Review - Phase 3

## Gemini Review

### Summary
The revised plan set cleanly fixes the previous high-risk sequencing failures. `03-01` now updates binding `Cargo.toml` manifests before deleting `classic-constants-core`, moves inline tests before source deletion, and the previously missed GUI/CXX and test-file consumers are explicitly covered.

### Strengths
- `03-01` now rewrites workspace `Cargo.toml` dependencies before deleting the source crate.
- Inline tests are migrated in `03-01` Task 1 while the source still exists.
- `03-02` explicitly covers `#[pyclass(module = ...)]` retagging and Python-facing `NULL_VERSION`.
- `03-03` now includes `classic-gui/src/app/mainwindow.cpp` and `constants.spec.ts`.
- `03-04` uses a safer parity order: clean target maps, verify scan, reparent, regenerate.

### Concerns
- **LOW**: The parity generator scripts may still contain dead `SQUAD_BY_OWNER["constants"]` metadata even after target/owner map cleanup.
- **LOW**: Incremental GUI/CMake builds may need a clean reconfigure when generated headers change from `constants.h` to `shared.h`.
- **LOW**: `03-01` should explicitly verify new target-crate dependencies such as `semver` and `serde` while moving the Rust slices.

### Suggestions
- Explicitly remove the dead `constants` squad-owner metadata from both parity generator scripts.
- Be ready to force a CMake reconfigure if `build_gui.ps1` misses generated-header churn.
- Double-check dependency additions in the three Rust destination crates during execution.

### Risk Assessment
**LOW**. Gemini considers the previous HIGH/MEDIUM-HIGH issues fully mitigated and the replanned set ready for execution.

---

## the agent Review

### Resolution Check

| Prior finding | Severity | Status | Where addressed |
|---|---|---|---|
| Crate deletion before binding Cargo migrations | HIGH | Resolved | `03-01` Task 2 now sweeps all workspace Cargo manifests first |
| Test migration after source deletion | HIGH | Resolved | `03-01` Task 1 now moves tests with the code |
| Missing `#[pyclass(module = ...)]` retagging | MEDIUM | Resolved | `03-02` Task 1 plus `__module__` verification |
| GUI consumer missing from scope | HIGH | Resolved | `03-03` Task 2 includes `classic-gui/src/app/mainwindow.cpp` |
| `constants.spec.ts` not handled | HIGH | Partially resolved | `03-03` mentions it, but keep-vs-split is still left open |

### 03-01-PLAN.md

**Summary**
Strong two-task structure that fixes the prior structural issues. The plan is now self-consistent and can pass its own verification without waiting on later waves.

**Strengths**
- Tests moved into Task 1 with the code.
- Binding-crate `Cargo.toml` swaps are now included before deletion.
- `classic-resource-core` is explicitly inspected instead of assuming a replacement dependency.
- Structural verification asserts no `Cargo.toml` still references `classic-constants-core`.
- Doc-only references in `classic-registry-core` and `classic-path-core` are included.

**Concerns**
- **MEDIUM**: Updating `classic-constants-py/Cargo.toml` in `03-01` may be wasted work if the crate is deleted immediately in `03-02`, unless the intermediate workspace must compile.
- **MEDIUM**: There is still no intermediate `cargo check --workspace` at the end of Task 1 to catch doctest/import fallout before Task 2.
- **LOW**: `phf` propagation vs removal remains executor discretion and should be checked explicitly.
- **LOW**: `classic-config-core` should still be covered by the workspace Cargo sweep because Phase 2 may have carried dependencies forward.

**Suggestions**
- Add `classic-config-core/Cargo.toml` to the explicit grep/sweep list or confirm the workspace sweep covers it.
- Consider a fast `cargo check --workspace` after Task 1.
- Make the `classic-constants-py/Cargo.toml` update conditional on the need for a green intermediate state.

**Risk Assessment**
**LOW-MEDIUM**. Structurally sound, with only execution-level cleanup questions left.

### 03-02-PLAN.md

**Summary**
Well-shaped Python split plan with the key PyO3 fixes now explicit. Rebuilding `classic_scanlog` closes the stale-artifact risk called out previously.

**Strengths**
- `#[pyclass(module = ...)]` retagging is now explicit and verified.
- Python-facing `NULL_VERSION` is now tracked deliberately.
- `classic_scanlog` rebuild is part of verification.
- `test_promoted_residuals_smoke.py` is owned here rather than duplicated in `03-04`.
- Stub validation remains part of Task 1 verification.

**Concerns**
- **MEDIUM**: `rebuild_rust.ps1` argument format still needs confirmation so the scripted rebuild targets are correct.
- **MEDIUM**: The plan should be explicit about whether `SETTINGS_IGNORE_NONE` is exposed as a literal list or delegated from `classic-settings-core`.
- **LOW**: A negative import check for `classic_constants` would make stale-artifact cleanup more explicit.

**Suggestions**
- Verify the rebuild script’s target naming before execution.
- Add a negative `import classic_constants` assertion after deletion.
- Clarify the intended exposure mechanism for `SETTINGS_IGNORE_NONE`.

**Risk Assessment**
**LOW-MEDIUM**. The big Python risks are fixed; the remaining issues are mechanical.

### 03-03-PLAN.md

**Summary**
The replanned Node+CXX work now covers the missing production GUI consumer and both native wrapper builds. The biggest remaining issue is that `constants.spec.ts` still leaves some executor discretion.

**Strengths**
- `mainwindow.cpp` is explicitly included.
- Five-place CXX registration is clearly called out.
- Both CLI and GUI wrappers are in verification.
- Node verification runs from the correct package directory.
- Type-name collision checks in bridge destinations are now expected.

**Concerns**
- **MEDIUM**: `constants.spec.ts` still says “either keep or split,” which leaves avoidable decision overhead in the most mechanically complex plan.
- **MEDIUM**: `build_gui.ps1` runs without `-Test`, so GUI validation is build-only unless no test coverage exists.
- **LOW**: A quick structural check proving `classic::constants` and `constants.h` are gone would tighten the plan further.

**Suggestions**
- Commit to keeping `constants.spec.ts` as the regression suite if root exports are unchanged.
- Use `-Test` for GUI validation if relevant tests exist.
- Add a structural sweep over active C++ files for `classic::constants` and `classic_cxx_bridge/constants.h`.

**Risk Assessment**
**MEDIUM**. The critical GUI/CXX gap is fixed, but one execution choice remains too open-ended.

### 03-04-PLAN.md

**Summary**
This is now a much stronger closeout plan. The parity ordering is correct, duplicate smoke-test ownership is removed, and active docs/parity inputs are covered together.

**Strengths**
- Correct ordering: clean maps, verify scan, reparent, regenerate.
- Explicitly avoids re-editing `test_promoted_residuals_smoke.py` here.
- Broad doc verification covers all main active files.
- Allows a split-aware alternative when the Phase 1 parity helper does not fit a 1-to-3 redistribution.

**Concerns**
- **MEDIUM**: Generator/gate failures may still be hard to attribute if regeneration and gate checking stay bundled.
- **MEDIUM**: The exact symbol-to-owner mapping for parity reparenting should be made deterministic before edits.
- **LOW**: `runtime_coverage_registry.json` ownership updates are in scope but not called out explicitly in the action text.

**Suggestions**
- Build the symbol-to-owner routing table first.
- Consider splitting generator execution from final gate checks for clearer failure attribution.
- Mention runtime coverage registry reparenting explicitly.

**Risk Assessment**
**LOW-MEDIUM**. The plan is well-ordered now; remaining concerns are mechanical and tractable.

### Overall Assessment

**LOW-MEDIUM as replanned.** The original structural failures are resolved. Remaining concerns are execution-level edge cases: `constants.spec.ts` ambiguity, a couple of verification gaps, and deterministic parity reparenting details.

---

## Codex Review

### 03-01-PLAN.md

**Summary**
Codex agrees this is the right place to do the semantic Rust move, move tests early, and treat deletion as a dependency-cleanup problem. The main remaining weakness is that wave 1 still knowingly leaves later-wave binding source consumers unresolved.

**Strengths**
- Correct semantic redistribution.
- Tests and doctests move before deletion.
- Convenience re-exports are removed instead of recreated.
- Cargo manifests are swept early enough to delete the crate.
- Verification uses targeted tests for the three new Rust homes.

**Concerns**
- **HIGH**: Wave 1 still leaves Python/Node/CXX source consumers unresolved until wave 2, so the intermediate state is intentionally non-green.
- **MEDIUM**: `classic-resource-core` only appears as a `Cargo.toml` edit; if D-12 finds actual source usage, the plan does not yet declare the source files to touch.
- **MEDIUM**: Verification proves `Cargo.toml` cleanup, but there is no active-path structural sweep for remaining `classic_constants_core::...` Rust imports.
- **LOW**: The blame-preservation fallback should be tolerated explicitly if Git rename detection does not cooperate.

**Suggestions**
- Document that wave 1 may intentionally leave the workspace non-buildable until wave 2 lands.
- Add an `rg`-style structural sweep over active Rust paths for `classic_constants_core`.
- Either declare conditional `classic-resource-core/src/**` ownership or require proof the dependency is dead.
- Record accepted blame-preservation fallback in the task output, not just the commit guidance.

**Risk Assessment**
**MEDIUM**. Correct design, but the wave boundary remains fragile.

### 03-02-PLAN.md

**Summary**
Codex sees the Python split as mostly correct, with remaining ambiguity around `NULL_VERSION` and stale generated/install artifacts.

**Strengths**
- Clean semantic split across the three target Python modules.
- Correctly retags `#[pyclass(module = ...)]`.
- Rebuilds `classic_scanlog` in addition to the destination modules.
- Moves the smoke test in the same plan.
- Deletes the legacy crate instead of leaving an alias.

**Concerns**
- **MEDIUM**: The plan says preserve `NULL_VERSION` “if currently exposed,” but the success criteria assume it is exposed, which could cause parity drift.
- **MEDIUM**: `dist-rust` or other generated Python artifacts are not called out explicitly.
- **MEDIUM**: Consumer coverage may be too narrow if other active Python imports still reference `classic_constants`.
- **LOW**: A stale installed `classic_constants` module could mask failures unless cleanup is explicit.

**Suggestions**
- Lock the exact `NULL_VERSION` Python contract now.
- Add a sweep for `import classic_constants` / `from classic_constants` across active Python paths.
- Include generated-artifact cleanup or make it part of the rebuild flow.
- Add a negative import assertion after deletion.

**Risk Assessment**
**MEDIUM**. Mostly complete, but packaging/stub drift still needs guardrails.

### 03-03-PLAN.md

**Summary**
Codex still sees this as the most fragile plan. The semantic direction is right and the GUI consumer is finally in scope, but the CXX registration picture still feels under-specified relative to the locked five-place rule.

**Strengths**
- Node and CXX are treated as thin semantic mirrors of the Rust redistribution.
- `classic::constants` is explicitly retired.
- `mainwindow.cpp` is included as a real production consumer.
- Native wrapper scripts are used for validation.
- `constants.spec.ts` is at least acknowledged.

**Concerns**
- **HIGH**: `include/classic_cxx_bridge/` and `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml` are not in `files_modified`, which may make the five-place registration story incomplete if those are source-controlled touchpoints.
- **HIGH**: The plan should prove there are no remaining active uses of `classic::constants` or `classic_cxx_bridge/constants.h` anywhere, not just in `mainwindow.cpp`.
- **MEDIUM**: Node test handling is still ambiguous because “keep or split” is not a single execution target.
- **MEDIUM**: GUI verification is build-only rather than test-backed.

**Suggestions**
- Make the five registration sites concrete, either by adding the missing touchpoints or documenting which are generated-only.
- Add a repo-wide structural sweep for `classic::constants`, `classic_cxx_bridge/constants.h`, and `mod constants;`.
- Decide now whether `constants.spec.ts` survives or is split.
- Consider `build_gui.ps1 -Test` if runtime coverage is available.

**Risk Assessment**
**HIGH**. Codex remains most concerned about silent CXX registration and consumer-sweep failures.

### 03-04-PLAN.md

**Summary**
Codex sees this as a good docs/parity closure plan, but not yet a full phase-closure plan because the strongest workspace-level Rust proof is still missing.

**Strengths**
- Docs and parity closure are separated cleanly.
- Target-map cleanup happens before baseline regeneration.
- Obsolete API docs are redistributed to the correct owners.
- All three parity systems remain in final verification.
- Active-file sweeps reduce stale-name drift.

**Concerns**
- **HIGH**: There is still no final `cargo build --workspace` and `cargo test --workspace`, even though the phase success criteria require them.
- **HIGH**: Node baseline regeneration is not explicit; `bun run parity:gate:local` may validate rather than regenerate.
- **MEDIUM**: Active-doc scope may still be incomplete versus D-29, especially `AGENTS.md` and possibly roadmap/requirements context.
- **MEDIUM**: The stale-reference sweep may miss old names inside modified parity artifacts and fixtures.

**Suggestions**
- Add final workspace-level Rust validation in `03-04`.
- Make the Node baseline refresh command explicit before the Node gate.
- State clearly whether prerequisite docs already covered roadmap/requirements updates, and add `AGENTS.md` if still in active scope.
- Expand stale-reference sweeps to all modified parity artifacts and fixtures.

**Risk Assessment**
**HIGH**. Codex still sees closure risk because the final end-to-end Rust and Node proofs are not explicit enough.

### Overall Assessment

Codex considers the plan set directionally strong but still exposed at the wave-boundary and final-closure levels. The main unresolved issues are the intentionally broken intermediate state, CXX registration/sweep completeness, and missing explicit final workspace Rust validation.

---

## Consensus Summary

This second review round is much stronger than the first. All three reviewers agree the replanned set fixed the original structural failures: test migration is now early, binding `Cargo.toml` cleanup happens before deleting the Rust source crate, Python module retagging is explicit, the GUI consumer is in scope, and parity work is more safely ordered.

### Agreed Strengths
- The previous HIGH-severity sequencing bugs in `03-01` are fixed.
- Python retagging, `classic_scanlog` rebuilds, and smoke-test ownership are now explicit in `03-02`.
- `03-03` now includes the missing GUI consumer and treats CXX registration as first-class work.
- `03-04` now uses a better parity regeneration order and no longer duplicates Python smoke ownership.

### Agreed Concerns
- **Top concern:** `03-03` still needs tighter execution specificity around Node/CXX closure. Both Claude and Codex want the `constants.spec.ts` decision nailed down, and Codex additionally wants a stronger proof that all active `classic::constants` / `constants.h` uses are gone.
- **Second concern:** `03-04` still needs stronger closure proof. Codex explicitly wants final `cargo build --workspace` and `cargo test --workspace`, plus a clearly explicit Node baseline regeneration path. Claude also wants parity ownership updates to be more deterministic.
- **Third concern:** There are still a few `03-01`/`03-02` execution details to tighten: `classic-config-core` and active-path Rust sweeps, exact `NULL_VERSION` and `SETTINGS_IGNORE_NONE` Python behavior, negative `classic_constants` import checks, and rebuild-script argument certainty.

### Divergent Views
- **Gemini** is now comfortable calling the plan set **LOW risk** overall and only flags minor metadata/CMake cleanup issues.
- **Claude** rates the replan **LOW-MEDIUM risk** and sees only execution-level cleanup work left.
- **Codex** remains the strictest reviewer and still rates the overall set **HIGH risk** because of the intentionally broken intermediate state, possible under-scoped CXX registration/sweeps, and missing explicit final workspace Rust validation.

### Recommended Replan Inputs
1. In `03-03`, choose one `constants.spec.ts` strategy now and add an active-path sweep for `classic::constants`, `classic_cxx_bridge/constants.h`, and `mod constants;`.
2. In `03-03`, confirm whether `include/classic_cxx_bridge/` and `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml` are generated-only or should be explicit `files_modified` touchpoints.
3. In `03-04`, add final `cargo build --workspace` and `cargo test --workspace`, and make the Node baseline regeneration command explicit before the Node parity gate.
4. In `03-01`, add an active Rust-path sweep for remaining `classic_constants_core` imports and explicitly cover `classic-config-core` in the Cargo scan.
5. In `03-02`, lock the exact Python `NULL_VERSION` contract, clarify `SETTINGS_IGNORE_NONE` exposure, and add a negative `classic_constants` import check plus any needed stale-artifact cleanup.
