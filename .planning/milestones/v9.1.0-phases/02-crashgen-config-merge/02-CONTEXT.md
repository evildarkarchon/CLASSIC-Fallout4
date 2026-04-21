# Phase 2: Crashgen -> Config Merge - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Absorb `classic-crashgen-settings-core` (573-line pure rule model + evaluator) into `classic-config-core` so that `classic-crashgen-settings-core` no longer exists as a separate crate. All public types, enums, structs, and the `evaluate_rules` function become available from `classic_config_core` at the same API surface. All 3 Rust core consumers and 4 binding crates migrate import paths. Zero consumer-visible behavior change.

Phase 2 is structurally simpler than Phase 1:
- No binding crate to delete (no `classic-crashgen-settings-py` exists)
- No CXX bridge module to rename or expand (no `crashgen.rs` in `classic-cpp-bridge`)
- No tests or benchmarks to migrate (crashgen-settings-core has none)
- Binding consumers already have `crashgen_rules.rs` files that just need import-path swaps

</domain>

<decisions>
## Implementation Decisions

### Module layout inside config-core
- **D-01:** Add crashgen-settings-core's code as a new sibling module: `crashgen_rules.rs` (from `classic-crashgen-settings-core/src/lib.rs` — contains `RuleSeverity`, `ConfigLayout`, `TargetValueType`, `ExpectedValue`, `Predicate`, `PreflightActionKind`, `RuleReportBucket`, `PreflightAction`, `PreflightRule`, `RuleTarget`, `RuleMessages`, `CheckRule`, `CrashgenSettingsRules`, `EvaluationContext`, `OutcomeKind`, `EvaluationOutcome`, `EvaluationResult`, and the `evaluate_rules` function). Existing modules (`config.rs`, `yamldata.rs`, `lib.rs`) stay untouched structurally.
- **D-02:** Single flat file — do NOT split into `crashgen/` subfolder or `crashgen_types.rs + crashgen_eval.rs` pair. Keeps the `git mv` rename clean and preserves full blame history on a single file.

### Re-export strategy
- **D-03:** Flat re-exports at the crate root. All crashgen-settings-core public types and functions re-exported from `classic_config_core` root via `pub use crashgen_rules::*;`. Consumers migrate by swapping `classic_crashgen_settings_core::X` -> `classic_config_core::X`. (Carries forward from Phase 1 D-04.)

### Dependency graph handling
- **D-04:** `classic-scanlog-core` already depends on `classic-config-core`, so its import-path swap is a pure content edit with no Cargo.toml dep change.
- **D-05:** `classic-scangame-core` does NOT currently depend on `classic-config-core`. It will gain `classic-config-core = { path = "../classic-config-core" }` as a new direct dependency in `classic-scangame-core/Cargo.toml`. This pulls yaml-rust2, indexmap, tokio-full, dirs, anyhow, and serde as new transitive deps, but honors the roadmap's chosen merge target and matches the "absorb into heaviest consumer" precedent. Alternatives (relocating the rule model to a new crate or duplicating types) were rejected because they either cancel Phase 2's consolidation goal or break single-source-of-truth.

### Rust core consumer updates (scope: 3 crates)
- **D-06:** `classic-config-core` — remove `classic-crashgen-settings-core = { path = "../classic-crashgen-settings-core" }` from Cargo.toml. Update internal imports in `yamldata.rs` (1 reference) from `classic_crashgen_settings_core::X` to direct module path (already in same crate after merge).
- **D-07:** `classic-scanlog-core` — swap the `classic-crashgen-settings-core` Cargo dep for `classic-config-core` (already present), then update imports in `orchestrator.rs` (11 references), `settings_validator.rs` (2 references), and `crashgen_registry.rs` (1 reference). Dep graph unchanged since config-core was already in scope.
- **D-08:** `classic-scangame-core` — add `classic-config-core` dep per D-05, remove `classic-crashgen-settings-core` dep, update imports in `orchestrator.rs` (1 ref), `crashgen_orchestrator.rs` (1 ref), and `toml.rs` (4 refs).

### Binding consumer updates (scope: 4 crates, file renames deferred)
- **D-09:** Keep all binding-crate filenames as-is. `classic-node/src/crashgen_rules.rs`, `classic-config-py/src/crashgen_rules.rs` (or equivalent), `classic-scangame-py/src/crashgen_rules.rs`, and `classic-scanlog-py/src/crashgen_rules.rs` each keep their existing filename. Only the internal `use classic_crashgen_settings_core::X;` lines change to `use classic_config_core::X;`. No `git mv`, no blame disruption.
- **D-10:** Each binding crate's `Cargo.toml` drops `classic-crashgen-settings-core` and — if not already present — adds `classic-config-core`. Verify each binding's existing deps before editing to avoid duplicate entries.

### Crate deletion
- **D-11:** Delete the `ClassicLib-rs/business-logic/classic-crashgen-settings-core/` directory entirely (source, Cargo.toml, everything). Remove the `classic-crashgen-settings-core` entry from the workspace members list in `ClassicLib-rs/Cargo.toml`. Use `git rm -r` so deletion is tracked.

### Parity gate timing
- **D-12:** Verify-only strategy for Phase 2. Run CXX, Python, and Node parity gates after the merge lands. All three should exit 0 with zero drift because no exposed binding API names change — only internal imports. If drift appears, treat it as a real bug to investigate, not a reason to regenerate baselines. Phase 4 does final cross-merge validation across all three merges. (Differs from Phase 1 D-12 because Phase 1 added new bridge surface; Phase 2 does not.)

### Git history preservation
- **D-13:** Use `git mv ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs ClassicLib-rs/business-logic/classic-config-core/src/crashgen_rules.rs` to preserve blame history for the rule model. Content edits (import adjustments, `pub use` re-exports, doc comment updates) go in a separate commit after the rename commit. (Carries forward from Phase 1 D-15.)

### API documentation
- **D-14:** Merge `docs/api/classic-crashgen-settings-core.md` content into `docs/api/classic-config-core.md` as a new "Crashgen rule model" section. Delete `docs/api/classic-crashgen-settings-core.md`. Update `docs/api/README.md` index to remove the crashgen entry and expand the config-core entry description. (Carries forward from Phase 1 D-13.)

### Cross-reference cleanup scope
- **D-15:** Update references in active docs only: `CLAUDE.md`, `docs/api/*.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `.planning/codebase/*.md`, `AGENTS.md`. Skip archived milestone plans and historical docs (`.planning/milestones/*`, `docs/plans/*`, `docs/prd/complete/*`) — they are snapshots in time. (Carries forward from Phase 1 D-14.)

### Tests
- **D-16:** Preserve zero coverage for the absorbed crashgen module. Phase 2 is a strict structural refactor — "no consumer-visible behavior change" per ROADMAP.md success criteria. Adding tests expands scope and dilutes the "pure merge" guarantee. Crashgen rule types are already exercised transitively by scanlog-core and scangame-core integration tests. Coverage gaps, if any, are a separate concern.

### yamldata.rs.bak cleanup
- **D-17:** Delete `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs.bak` (21 KB, dated 2025-12-13) as part of Phase 2. Separate commit from the crashgen merge so the deletion shows up distinctly in `git log`. Using `git rm` to track the removal. Latent cleanup that costs nothing and removes cruft from the directory we're already touching.

### Workspace member removal
- **D-18:** Remove `"business-logic/classic-crashgen-settings-core"` from the `members = [...]` list in `ClassicLib-rs/Cargo.toml`. Same commit as the directory deletion so the workspace is never in a half-removed state.

### Claude's Discretion
- Exact ordering of operations within each commit
- Internal import organization inside the moved `crashgen_rules.rs` (whether `use std::collections::{HashMap, HashSet};` stays at top, etc.)
- How to handle any incidental `cargo fmt` churn on neighboring lines
- Workspace Cargo.lock updates (mechanical, handled automatically)
- Any `#[allow(...)]` lint attributes that need to carry forward with the moved code
- Whether to verify with `cargo build --workspace` after each subplan or only at the end

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Rust crate sources (merge source and target)
- `ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs` — Full source of crashgen-settings-core (rule model, predicates, evaluator, `evaluate_rules` function). 573 lines.
- `ClassicLib-rs/business-logic/classic-crashgen-settings-core/Cargo.toml` — Source crate dependencies (only `thiserror` from workspace)
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs` — config-core crate root and current re-exports (27 lines — minimal, just re-exports)
- `ClassicLib-rs/business-logic/classic-config-core/src/config.rs` — config-core primary implementation (1633 lines)
- `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs` — YAML-data consumer of crashgen types (1 import reference)
- `ClassicLib-rs/business-logic/classic-config-core/Cargo.toml` — config-core current dependencies (includes classic-crashgen-settings-core to remove)

### Workspace root
- `ClassicLib-rs/Cargo.toml` — Workspace members list (`classic-crashgen-settings-core` entry to remove)

### Rust core consumers (import path updates)
- `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` — depends on classic-crashgen-settings-core AND classic-config-core (pure import swap)
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs` — 11 crashgen references
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs` — 2 crashgen references
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/crashgen_registry.rs` — 1 crashgen reference
- `ClassicLib-rs/business-logic/classic-scangame-core/Cargo.toml` — depends on classic-crashgen-settings-core but NOT classic-config-core (needs new dep per D-05)
- `ClassicLib-rs/business-logic/classic-scangame-core/src/orchestrator.rs` — 1 crashgen reference
- `ClassicLib-rs/business-logic/classic-scangame-core/src/crashgen_orchestrator.rs` — 1 crashgen reference
- `ClassicLib-rs/business-logic/classic-scangame-core/src/toml.rs` — 4 crashgen references

### Binding consumers (import path updates, no file renames)
- `ClassicLib-rs/node-bindings/classic-node/Cargo.toml` — Node binding crate deps
- `ClassicLib-rs/node-bindings/classic-node/src/crashgen_rules.rs` — Node crashgen consumer module
- `ClassicLib-rs/python-bindings/classic-config-py/Cargo.toml` — Python config-py deps
- `ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs` — Python config-py root (verify crashgen imports)
- `ClassicLib-rs/python-bindings/classic-scanlog-py/Cargo.toml` — Python scanlog-py deps
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/crashgen_rules.rs` — Python scanlog-py crashgen consumer
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/settings_validator.rs` — Python scanlog-py settings validator (uses crashgen types)
- `ClassicLib-rs/python-bindings/classic-scangame-py/Cargo.toml` — Python scangame-py deps
- `ClassicLib-rs/python-bindings/classic-scangame-py/src/crashgen_rules.rs` — Python scangame-py crashgen consumer

### Parity gates (verify-only, no regeneration expected)
- `tools/cxx_api_parity/` — CXX parity gate tooling
- `tools/python_api_parity/check_parity_gate.py` — Python parity gate (expect `deferred_total == 0`)
- `ClassicLib-rs/node-bindings/classic-node/` — Node parity gate entry: `bun run parity:gate:local`

### API documentation
- `docs/api/classic-crashgen-settings-core.md` — Crashgen-settings API doc (merge into config-core, then delete)
- `docs/api/classic-config-core.md` — Config core API doc (expand with rule model section)
- `docs/api/README.md` — API doc index (update entry list)
- `docs/api/binding-parity-overview.md` — Binding surface reference (update for merged crate)
- `docs/api/classic-config-core-yaml-schema.md` — Runtime YAML schema contract for config-core

### Phase 1 precedent (carried-forward decisions)
- `.planning/phases/01-yaml-settings-merge/01-CONTEXT.md` — Phase 1 context with D-01 through D-15 decisions (re-export strategy D-04, git history D-15, cross-ref scope D-14, API docs D-13, parity gate timing D-12 — adapted for Phase 2)
- `.planning/phases/01-yaml-settings-merge/01-VERIFICATION.md` — Phase 1 verification artifact (template for Phase 2 verification)

### Stray file
- `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs.bak` — 21 KB stray backup from 2025-12-13; delete per D-17

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `classic-config-core/src/lib.rs` is only 27 lines (minimal crate root with re-exports) — adding `mod crashgen_rules; pub use crashgen_rules::*;` is a low-risk 2-line change
- `classic-config-core` already has the re-export infrastructure for public types (matches Phase 1 settings-core pattern)
- Binding crates already have `crashgen_rules.rs` files named identically to the planned target module inside config-core, which means no file renaming is needed on the binding side

### Established Patterns
- **Single-file absorption**: Phase 1 moved `yaml-core/src/lib.rs` + `merge.rs` into settings-core as `yaml_ops.rs` + `yaml_merge.rs`. Phase 2's source is a single 573-line file, so the absorption collapses to a single `git mv` with no split decisions needed.
- **Absorb-into-heaviest-consumer rule**: Phase 1 absorbed yaml-core into settings-core because settings-core was the primary consumer. Phase 2 absorbs crashgen-settings-core into config-core for the same reason, per ROADMAP.md's merge-target choice.
- **Flat re-exports** at crate root (`pub use submodule::*;`) — standard pattern across all merged crates
- **Parity gate baselines track EXPOSED binding API**, not internal Rust imports, so import-path changes inside binding crates don't drift the baselines (verify-only D-12 is safe)
- **git mv then edit**: preserve blame history by separating file moves from content edits into two commits — Phase 1 D-15 precedent

### Integration Points
- `classic-config-core` is where the absorbed code lands — Cargo.toml, lib.rs, and new `crashgen_rules.rs`
- `classic-scanlog-core` and `classic-scangame-core` are the heaviest consumers by reference count (11 + 6 references respectively)
- `classic-scangame-core/Cargo.toml` is the only consumer that needs a NEW Cargo dep (config-core was not previously in scope) — this is the only dep-graph-affecting change in Phase 2
- `ClassicLib-rs/Cargo.toml` workspace members list needs the `classic-crashgen-settings-core` entry removed
- `Cargo.lock` will update automatically when `classic-crashgen-settings-core` is removed and scangame-core gains `classic-config-core`

</code_context>

<specifics>
## Specific Ideas

- Phase 2 is deliberately simpler than Phase 1 — no new bridge surface, no binding crate deletion, no test migration. The planner should NOT recreate Phase 1's multi-subplan structure by analogy; Phase 2 likely needs fewer, smaller plans.
- User explicitly wants the `yamldata.rs.bak` stray file deleted as a separate commit within Phase 2 (not a quick task, not ignored) — keeps the audit trail clean.
- Verify-only parity gate strategy is a deliberate departure from Phase 1 D-12. The planner should not default to regenerating baselines "because Phase 1 did." Phase 2's scope genuinely differs.
- scangame-core gaining a new `classic-config-core` dep is the only dep-graph-affecting change in the entire phase — it deserves explicit verification in the plan (cargo tree check, compile time delta noted).
- All filenames in binding crates stay exactly as they are. No renames. This is the fastest, cleanest, most blame-preserving approach.
- `git mv` for the single source file move (lib.rs -> crashgen_rules.rs) in its own commit, content edits in a second commit — matches Phase 1 D-15 precedent exactly.

</specifics>

<deferred>
## Deferred Ideas

- **Splitting the rule model types from the evaluator** (into `crashgen_types.rs` + `crashgen_eval.rs` or `crashgen/` subfolder) — rejected for Phase 2 to preserve git blame; could be a future refactor if the file grows
- **Adding tests for crashgen rule model** — preserved at zero coverage for Phase 2; candidate for a future dedicated test-coverage phase
- **Relocating crashgen rule types to a foundation-layer crate** — rejected because it would cancel Phase 2's consolidation goal (19 -> 16); if cross-cutting rule-model layering becomes a concern, it belongs in its own refactor milestone
- **Renaming binding-crate `crashgen_rules.rs` files to match parent crate conventions** — rejected for Phase 2 to preserve blame; could be revisited during a future binding-crate internal cleanup phase

</deferred>

---

*Phase: 02-crashgen-config-merge*
*Context gathered: 2026-04-10*
