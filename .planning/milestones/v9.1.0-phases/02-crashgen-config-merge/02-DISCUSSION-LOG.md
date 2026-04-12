# Phase 2: Crashgen -> Config Merge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `02-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 02-crashgen-config-merge
**Areas discussed:** Dep cycle handling, Module layout, Parity gate timing, Binding file naming, yamldata.rs.bak cleanup, Tests

---

## Pre-discussion scouting findings

- `classic-crashgen-settings-core` is a 573-line single-file crate (`lib.rs` only), no `merge.rs`, no `tests/`, no `benches/`, only `thiserror` in Cargo deps
- No standalone Python or Node binding crate exists for crashgen (no `classic-crashgen-settings-py`)
- No CXX bridge module exists for crashgen (no `crashgen.rs` in `classic-cpp-bridge`)
- Rust core consumers: `classic-config-core`, `classic-scanlog-core`, `classic-scangame-core` (3)
- Binding consumers: `classic-node`, `classic-config-py`, `classic-scangame-py`, `classic-scanlog-py` (4)
- Use-site counts: scanlog-core/orchestrator.rs=11, scangame-core/toml.rs=4, others 1-2 each
- **Critical finding**: `scanlog-core` already depends on `classic-config-core`, but `scangame-core` does NOT — meaning the merge forces a new dep edge on one crate
- **Stray file found**: `classic-config-core/src/yamldata.rs.bak` (21 KB, dated 2025-12-13)

## Dep cycle handling

| Option | Description | Selected |
|--------|-------------|----------|
| Add config-core dep to scangame-core (Recommended) | Straightforward. Honors the roadmap's chosen merge target. Pulls yaml-rust2, indexmap, tokio-full, dirs, anyhow, serde as new transitive deps but compile-time cost is manageable. Matches Phase 1's 'absorb into heaviest consumer' precedent. | ✓ |
| Relocate rule model to a new layer | Create a crashgen-rules foundation crate or leave it renamed. Rejected — effectively cancels Phase 2's consolidation goal (19→16) because we haven't reduced crate count, just renamed. | |
| Duplicate types into scangame-core | Copy the rule model into scangame-core and remove the dep. Rejected — breaks single-source-of-truth; future changes would need sync across crates. | |

**User's choice:** Add config-core dep to scangame-core (Recommended)
**Notes:** Accepted the recommended default. Locked as D-05 and D-08 in CONTEXT.md.

---

## Module layout

| Option | Description | Selected |
|--------|-------------|----------|
| Single crashgen_rules.rs module (Recommended) | New sibling to config.rs and yamldata.rs. Matches existing binding-consumer filenames. Smallest diff, easiest grep, single git mv preserves full blame history. | ✓ |
| Split into crashgen/ subfolder | crashgen/{mod.rs, types.rs, evaluator.rs}. Cleaner logical split but higher churn, loses git blame. | |
| Two sibling modules: crashgen_types.rs + crashgen_eval.rs | Flat split mirroring Phase 1's yaml_ops.rs + yaml_merge.rs. Cleaner than subfolder but still loses some blame. | |

**User's choice:** Single crashgen_rules.rs module (Recommended)
**Notes:** Accepted the recommended default. Single-file source + full blame preservation outweighed Phase 1's split-file pattern. Locked as D-01 and D-02.

---

## Parity gate timing

| Option | Description | Selected |
|--------|-------------|----------|
| Verify-only, expect 0 drift (Recommended) | Run all three gates after the merge, expect zero drift. Phase 4 does cross-merge validation. Fastest, tightest feedback loop. Drift would indicate a real bug worth investigating. | ✓ |
| Regenerate baselines defensively | Match Phase 1 D-12 exactly. Safer if internal Rust signature hashes leak into contracts. Larger diff, could hide real drift. | |
| Defer gate work entirely to Phase 4 | Skip gate verification in Phase 2. Risk: Phase 2 + Phase 3 drift compounds, harder to debug. | |

**User's choice:** Verify-only, expect 0 drift (Recommended)
**Notes:** Accepted the recommended default. Deliberate departure from Phase 1 D-12 because Phase 2 adds no new binding surface. Locked as D-12 in CONTEXT.md with explicit note about the difference from Phase 1.

---

## Binding file naming

| Option | Description | Selected |
|--------|-------------|----------|
| Keep filenames, swap imports only (Recommended) | Simplest possible diff. Each binding crate keeps its crashgen_rules.rs and just changes use imports. No renames, no file moves, blame intact. | ✓ |
| Rename binding files to match parent crate | Rename crashgen_rules.rs → config.rs or merge into existing config module. More internally consistent but triggers file moves in 4 separate binding crates for zero API benefit. | |

**User's choice:** Keep filenames, swap imports only (Recommended)
**Notes:** Accepted the recommended default. Locked as D-09 and D-10.

---

## yamldata.rs.bak cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Delete as part of Phase 2 cleanup (Recommended) | We're touching the config-core directory anyway. Separate commit from the crashgen merge so deletion shows distinctly in git log. | ✓ |
| Handle as a separate quick task | Keep Phase 2 strictly scoped. /gsd:quick for the .bak cleanup. Slightly more ceremony for a trivial deletion. | |
| Ignore — out of scope | Leave the file until someone else notices. Risk: lingers indefinitely. | |

**User's choice:** Delete as part of Phase 2 cleanup (Recommended)
**Notes:** Accepted the recommended default. Locked as D-17 with explicit separate-commit requirement.

---

## Tests

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve zero coverage, no new tests (Recommended) | Phase 2 is strict structural refactor. Adding tests expands scope. Crashgen types are exercised transitively by scanlog/scangame integration tests. | ✓ |
| Add minimal smoke tests during the merge | Lock current behavior while code is in motion. Cons: expands scope, tests would just be testing code that already works. | |

**User's choice:** Preserve zero coverage, no new tests (Recommended)
**Notes:** Accepted the recommended default. Locked as D-16.

---

## Claude's Discretion

Explicit Claude-discretion items (from CONTEXT.md):
- Exact ordering of operations within each commit
- Internal import organization inside the moved crashgen_rules.rs
- Any incidental cargo fmt churn on neighboring lines
- Workspace Cargo.lock updates (mechanical)
- Any #[allow(...)] lint attributes carrying forward with moved code
- Whether to verify with cargo build --workspace after each subplan or only at the end

## Deferred Ideas

- Splitting rule model types from evaluator — preserved for blame history; candidate for future refactor
- Adding tests for crashgen rule model — candidate for future dedicated test-coverage phase
- Relocating crashgen rule types to a foundation-layer crate — would cancel consolidation goal
- Renaming binding-crate crashgen_rules.rs files to match parent crate — could be future binding-crate cleanup phase
