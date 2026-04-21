---
phase: 10
reviewers: [gemini, claude, codex]
reviewed_at: 2026-04-13T19:13:05.3940690-07:00
plans_reviewed:
  - 10-01-PLAN.md
  - 10-02-PLAN.md
  - 10-03-PLAN.md
  - 10-04-PLAN.md
  - 10-05-PLAN.md
  - 10-06-PLAN.md
  - 10-07-PLAN.md
---

# Cross-AI Plan Review — Phase 10

## Gemini Review

Here is the review of the implementation plans for Phase 10.

### 1. Summary
The plans outline a highly structured and comprehensive approach to updating the documentation, codebase maps, and agent skills to reflect the new repository-root workspace layout. The strategy to implement a single `workspace-migration-matrix.md` effectively mitigates the risk of translation drift across multiple documents. Furthermore, the hybrid regression tripwires proposed in Plan 10-07 align perfectly with the repository's established validation patterns, ensuring durable protection against stale `ClassicLib-rs` instructions.

### 2. Strengths
* **Centralized Source of Truth:** Plan 10-01 creates a single `workspace-migration-matrix.md` and fans out relative links to it, completely avoiding the anti-pattern of duplicating old/new command translations across multiple pages.
* **Thorough Agent Skill Coverage:** Plans 10-03 and 10-04 systematically catch all agent skill mirrors (`.agents`, `.opencode`, `.claude`, and `.agent`), ensuring that AI assistants won't regress to offering stale paths.
* **Deterministic Tripwires:** Plan 10-07 leverages PowerShell AST parsing (`Parser.ParseFile`) and Python `unittest` sweeps, staying consistent with the strict, file-backed validation architecture defined in Phase 06 and Phase 09.
* **Clear Semantic Boundaries:** The plans explicitly enforce that any remaining `ClassicLib-rs` references must be strictly labeled as `Historical note:` or `Migration note:`, preserving valuable context while removing operational ambiguity.

### 3. Concerns
* **HIGH: Delayed Validation Scaffold (Anti-TDD).** By placing the validation tripwires (Plan 10-07) in Wave 3—depending on Plans 10-01 through 10-06—the implementation plans lack automated verification during their own execution. In earlier phases (like Phase 06 and 09), the validation scaffold was bootstrapped in Wave 0/1 so subsequent plans could run the tests to verify their work.
* **MEDIUM: Complexity of Context-Aware Sweeps.** Plan 10-07 requires the Python script to fail on forbidden phrases "unless they appear inside an explicitly allowed historical or migration note." Parsing Markdown context to reliably associate a forbidden string with a "Historical note" label in a simple Python script can be brittle and error-prone if dealing with multi-line blocks or tables.
* **LOW: PowerShell Test Overlap.** `tests/powershell/rebuild_rust.general_target.test.ps1` already checks for some `ClassicLib-rs` paths. Creating `phase10_guidance_tripwires.test.ps1` introduces a slight overlap, though it is acceptable since it broadens coverage to `classic-cli` and `classic-gui` wrappers.

### 4. Suggestions
* **Bootstrap Validation First:** Move the creation of `test_phase10_validation.py` and `phase10_guidance_tripwires.test.ps1` into a `10-00-PLAN.md` (Wave 0/1), and make Plans 10-01 through 10-06 depend on it. The tests will initially fail, giving the autonomous agent a concrete verification target (TDD) as it executes the document updates.
* **Simplify the Exclusion Logic:** In Plan 10-07, instruct the agent to use a strictly scoped line-based check for the historical notes (e.g., `ClassicLib-rs` is only allowed if the exact line starts with `> Historical note:` or `**Migration note:**`), or provide an explicit line-number/file exclusion dictionary. This prevents the agent from writing a brittle multi-line parser.
* **Ensure Matrix Completeness:** In Plan 10-01, explicitly add translations for the Node and Python parity gates (e.g., `bun run parity:gate` and `check_parity_gate.py`) to the migration matrix, as they are high-traffic workflows that underwent path changes in Phase 08.

### 5. Risk Assessment
**LOW.** The scope of this phase is strictly confined to documentation, agent instructions, codebase maps, and testing scripts. There is zero risk to the compiled Rust/C++ runtime code or application logic. The primary risk is a noisy test suite due to overly aggressive regex matching during the stale-path sweep, which is mitigated by the scoped exclusions defined in the plans.

---

## the agent Review

The Phase 10 plan review is complete. Three HIGH-severity findings: missing `CLAUDE.md` from all plans, fragile historical-marker sweep logic in Plan 10-07, and underspecified `docs/api/README.md` rewrite scope in Plan 10-02. Overall risk is MEDIUM, dropping to LOW if those three items are addressed before execution.

---

## Codex Review

## Cross-plan findings
- `HIGH`: 10-02 and 10-07 do not line up. The repo still has many active `docs/api/*.md` pages with live `ClassicLib-rs/...` guidance beyond the three files in 10-02, but 10-07 proposes a broad `docs/**/*.md` sweep. As written, either 10-02 is under-scoped or 10-07 will fail late.
- `MEDIUM`: The dependency graph is incomplete. 10-04 reads output that 10-02 is supposed to refresh, and 10-06 reads files 10-05 is supposed to refresh, but those dependencies are not declared.
- `MEDIUM`: `CLAUDE.md` is still a stale agent-context surface and was treated as sync-critical in Phase 06 validation, but no Phase 10 plan updates or audits it.

## 10-01-PLAN.md
**Summary**  
Strong opening plan. It creates the right central artifact and repoints the highest-traffic top-level docs to a single migration source of truth, which is the right anti-drift move for DOCS-02.

**Strengths**
- Establishes one matrix page instead of duplicating translations.
- Acceptance criteria are concrete and easy to validate later.

**Concerns**
- `MEDIUM`: It defers all executable verification to 10-07, so a bad matrix shape or bad link pattern is only caught after multiple later plans depend on it.
- `LOW`: It updates top-level entry docs, but leaves other contributor-facing active docs stale during waves 1-2, which can create mixed guidance mid-phase.

**Suggestions**
- Add a minimal smoke assertion in 10-01 or explicitly require a manual `rg` pass before wave 2 starts.
- Call out that `classic-cli/` and `classic-gui/` must remain visible in the updated top-level layout text, not just the root Rust layer dirs.

**Risk Assessment**  
`MEDIUM` — sound design, but it becomes a dependency hub without early guardrails.

## 10-02-PLAN.md
**Summary**  
This is the weakest plan in the set. The intended direction is correct, but the scope is too small relative to the phase requirement and the planned 10-07 sweep.

**Strengths**
- Correctly routes API entry docs through the shared matrix.
- Rewrites the stub-validation command to the actual repo-root contract.

**Concerns**
- `HIGH`: Only three `docs/api/` files are included, but active contributor pages like `node-python-contract-map.md`, `binding-parity-policy.md`, `cxx-parity-gate.md`, and many crate docs still contain live `ClassicLib-rs/...` paths.
- `HIGH`: 10-07’s proposed `docs/**/*.md` scoped sweep will likely fail on untouched active API docs, so this plan does not fully support the later validation contract.
- `MEDIUM`: The acceptance criteria focus on a few path replacements, not on the broader “active API references” requirement from D-01.

**Suggestions**
- Expand 10-02 to include the active routed API pages that still teach live paths, at minimum the binding/parity workflow pages and the most-linked crate pages.
- If that expansion is intentionally out of scope, narrow 10-07 to a curated allowlist instead of `docs/**/*.md`.

**Risk Assessment**  
`HIGH` — likely leaves the phase unable to satisfy DOCS-01/DOCS-03 together.

## 10-03-PLAN.md
**Summary**  
Good plan for the always-on guidance layer. Updating `AGENTS.md` and all four skill entrypoint mirrors is necessary and correctly scoped.

**Strengths**
- Includes all four `SKILL.md` mirrors, including `.agent/`.
- Keeps matrix routing centralized instead of inventing mirror-specific migration prose.

**Concerns**
- `MEDIUM`: It ignores `CLAUDE.md`, which is still an active agent-context file and still contains many stale `ClassicLib-rs/...` references.
- `LOW`: It also ignores the mirror `trigger-evals.json` files, which are not primary guidance but still encode stale example paths and can drift from the new contract.
- `MEDIUM`: “Replace the project overview and quick notes” is slightly risky wording; it could accidentally drop existing repo rules about frontend ownership and Python legacy/support posture.

**Suggestions**
- Either include `CLAUDE.md` here or explicitly declare it out of scope with justification.
- Preserve existing policy text and only rewrite stale path/root examples unless a policy statement truly changed.

**Risk Assessment**  
`MEDIUM` — good core coverage, but one important agent surface is currently unowned.

## 10-04-PLAN.md
**Summary**  
This is a solid detailed-guidance plan, but its dependency declaration is wrong for the files it says it will use.

**Strengths**
- Covers the long-form repo-guide mirrors where exact commands and parity workflows actually live.
- Correctly treats parity trigger paths and artifact paths as part of the contract.

**Concerns**
- `MEDIUM`: Task 2 explicitly reads `docs/api/binding-contract-refresh-note.md`, but the plan depends only on 10-01, not 10-02. That creates a same-wave ordering hazard.
- `LOW`: The acceptance criteria are very string-specific and may pass while mirrors still differ semantically in surrounding instructions.

**Suggestions**
- Add `10-02` as a dependency.
- Add one synchronization check in 10-07 that the four repo-guide mirrors stay materially aligned, not just individually path-clean.

**Risk Assessment**  
`MEDIUM` — good content target, but sequencing needs correction.

## 10-05-PLAN.md
**Summary**  
Well-aimed plan for the operational codebase maps. It updates the maps most likely to misroute later agents and contributors.

**Strengths**
- Hits the right high-traffic `.planning/codebase` files first.
- Handles both directory layout and manifest/artifact path rewrites.

**Concerns**
- `LOW`: It relies on later tests for all validation, so structural mistakes in `STRUCTURE.md` or `STACK.md` propagate until wave 3.
- `LOW`: It may over-rotate away from mentioning `ClassicLib-rs` residue paths that still matter for legacy cleanup unless the “historical/generated residue” labeling is applied carefully.

**Suggestions**
- Keep explicit labeled residue references where Phase 09 still cares about them.
- Make sure the rewritten maps still explain `classic-cli/` and `classic-gui/` ownership boundaries, not just Rust layer ownership.

**Risk Assessment**  
`LOW` — good scope and low implementation risk.

## 10-06-PLAN.md
**Summary**  
Necessary cleanup plan, but it also has a dependency problem and is more brittle than 10-05 because it references files another plan is supposed to rewrite first.

**Strengths**
- Targets the remaining codebase maps that agents actually use for day-to-day routing.
- Correctly treats testing guidance as operational contract, not incidental prose.

**Concerns**
- `MEDIUM`: Task 2 reads `STRUCTURE.md` and `ARCHITECTURE.md`, but the plan depends only on 10-01, not 10-05.
- `MEDIUM`: `TESTING.md` currently contains many stale examples; the acceptance criteria only sample a few strings, so the edit can still miss a lot of active stale guidance until 10-07.

**Suggestions**
- Add `10-05` as a dependency.
- Consider splitting `TESTING.md` into a more exhaustive checklist inside the plan, since it is one of the densest stale-path surfaces in the repo.

**Risk Assessment**  
`MEDIUM` — reasonable scope, but sequencing and completeness need tightening.

## 10-07-PLAN.md
**Summary**  
The hybrid validation approach is correct and matches repo precedent, but the plan is currently too broad relative to what earlier plans actually update.

**Strengths**
- Reuses the repo’s preferred pattern: explicit `unittest` audits plus narrow PowerShell tripwires.
- Uses fixed constants and exclusions instead of vague prose-only validation.

**Concerns**
- `HIGH`: The proposed scoped sweep over `docs/**/*.md` is wider than the implementation scope of 10-01 through 10-06. With the repo’s current state, that likely catches many untouched active docs and makes the phase fail late.
- `MEDIUM`: “Assert the matrix link exists on the must-read surfaces” is over-specified. Earlier plans only require that link on selected entrypoints, not every codebase map or deep repo-guide page.
- `MEDIUM`: The allowed historical markers are too narrow as written; many valid notes may not use exactly `Historical note:` or `Migration note:` and could become false positives.
- `LOW`: The PowerShell target list may be missing other active wrapper surfaces such as `classic-cli/test_cli.ps1`.

**Suggestions**
- Narrow the sweep to a curated active-surface allowlist first, or expand 10-02 substantially.
- Separate `LINK_REQUIRED_SURFACES` from `MUST_READ_SURFACES` so not every audited file is forced to carry the matrix link.
- Define allowed historical-note patterns more flexibly, or allow explicit per-file exceptions with comments.

**Risk Assessment**  
`HIGH` — best validation design in principle, but currently mismatched to the planned edit scope.

## Overall risk
`HIGH` — the phase design is close, but 10-02 is under-scoped and 10-04/10-06 have real dependency-ordering gaps. If those are fixed, the rest of the phase is credible.

---

## Consensus Summary

All three reviewers agree that the phase direction is strong: a shared migration matrix, synchronized agent-guidance mirrors, and deterministic tripwires match the repo's architecture and validation style well. The main risks are not conceptual; they are scope and execution-shape problems inside the current plan set.

### Agreed Strengths
- The single `docs/workspace-migration-matrix.md` source-of-truth pattern is the right anti-drift design for DOCS-02.
- Updating mirrored guidance surfaces across `.agents`, `.opencode`, `.claude`, and `.agent` is necessary and correctly recognized as a first-class part of the phase.
- The hybrid regression-guard approach in `10-07` matches existing repo patterns and is the right long-term enforcement model.

### Agreed Concerns
- `10-02` is under-scoped relative to the broader active `docs/api/*.md` surface and the later `docs/**/*.md` sweep. Reviewers flagged this as the highest planning risk.
- `10-07`'s historical-note allowance logic is fragile as currently described. The allowed-marker detection needs to be simpler or more explicit to avoid false positives.
- `CLAUDE.md` remains an active stale-guidance surface but is not owned by any current Phase 10 plan.

### Divergent Views
- Gemini wants the validation scaffold moved earlier as a TDD-style bootstrap; Codex agrees the late validation is risky but frames it more as a dependency-hub issue than a required `10-00` plan.
- Codex specifically flags missing dependencies (`10-04` on `10-02`, `10-06` on `10-05`) and possible missing wrapper coverage like `classic-cli/test_cli.ps1`; Gemini does not focus on those sequencing details.
- Gemini additionally recommends expanding the migration matrix with Node and Python parity-gate translations, while Codex focuses more on broadening API-doc coverage or narrowing the later sweep.
