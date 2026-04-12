---
phase: 2
reviewers: [gemini, claude, codex]
reviewed_at: 2026-04-11
review_round: 1
plans_reviewed: [02-01-PLAN.md, 02-02-PLAN.md]
---

# Cross-AI Plan Review — Phase 2 (Crashgen -> Config Merge)

Three independent AI reviewers (Gemini, Claude CLI, Codex CLI) assessed Phase 2 plans 02-01 and 02-02. Risk verdicts: Gemini **LOW**, Claude **LOW**, Codex **HIGH** (02-01) / **MEDIUM** (02-02).

---

## Gemini Review

# Phase 2 — Cross-AI Plan Review: Crashgen -> Config Merge

The implementation plans for Phase 2 are exceptionally thorough, surgical, and well-aligned with the project's consolidation goals. They demonstrate high technical awareness of the repository's cross-language dependencies and parity tooling.

## Summary
The plans for Phase 2 are of **high quality and ready for execution**. They strictly adhere to the user's implementational decisions (D-01 through D-18), particularly the nuanced requirements for git blame preservation and isolated cleanup commits. The planner successfully identified and addressed critical "traps" flagged in the research, such as the Node.js parity generator crash risk and the missing dependency in `classic-scangame-py`. The two-plan structure appropriately balances execution efficiency with the need for a stable filesystem state before running parity gates.

## Strengths
*   **Blame Preservation:** Plan 01 Task 1 correctly isolates the `git mv` operation into a rename-only commit, ensuring that git's heuristic rename detection preserves the full history of the rule model.
*   **Critical Tooling Awareness:** Plan 02 Task 1 proactively fixes the hardcoded paths in the Node.js parity generator. Without this, the Node parity gate would crash post-deletion, preventing validation.
*   **Surgical Dependency Management:** The planner correctly identified that `classic-scangame-py` (Python binding) lacks the `classic-config-core` dependency that it will now require, a detail easily missed when only focusing on the Rust core.
*   **Cleanliness:** The separate commit for the `yamldata.rs.bak` cleanup (D-17) ensures the audit trail for the merge remains focused purely on the refactor.
*   **Comprehensive Doc Sweep:** The doc update task (Plan 02 Task 2) covers not just the primary API pages but also the re-indexing and example updates in adjacent docs (`classic-scanlog-core.md`, etc.).

## Concerns
*   **Crate Count Discrepancy (LOW):** Plan 02 Task 2 Step F suggests updating the crate count from "17" to "16". Based on the roadmap, the project started with 19 crates. Phase 1 reduced this to 18. Phase 2 should therefore reduce it to **17**. The "16" count is the goal for the *end* of Phase 3.
*   **Verification Latency (LOW):** `cargo test --workspace` is estimated at 300 seconds. While appropriate for wave-level verification, ensure that the incremental `cargo build` in Task 2 is sufficient to catch the majority of import errors before the long test run.

## Suggestions
*   **Explicit Crate Count:** In Plan 02 Task 2, explicitly verify the count in `CLAUDE.md`. If it currently says "18 business-logic crates" (post-Phase 1), update it to "**17**".
*   **Grep Verification:** During Task 2 of Plan 01, use a recursive grep after the consumer migration to ensure no `classic_crashgen_settings_core` strings remain in any `.rs` files to confirm the 100% migration.
*   **Cargo Lock Check:** Plan 01 Task 2 includes `Cargo.lock` in the commit. It is recommended to run `cargo tree -p classic-scangame-core` immediately after the `cargo build` to verify the new dependency tree visually.

## Risk Assessment: LOW
The risk is low because:
1.  The merge involves a pure-data-model crate with no complex side effects or external dependencies.
2.  Existing parity gates and workspace tests provide a high-confidence safety net.
3.  The plans follow the proven "rename then edit" pattern established in Phase 1.

---

## Claude Review

# Phase 2 Plan Review

## Summary

These two plans are thorough, well-sequenced, and faithful to the locked CONTEXT.md decisions. Plan 02-01 correctly separates the rename-only commit from content edits (D-13), enumerates all 35 consumer sites with exact reference counts matching research, and catches the scangame-py dep-add trap. Plan 02-02 correctly sequences the Node parity generator tooling update BEFORE the Node gate invocation, averting the crash risk flagged in research. Both plans are ready to execute with minor concerns noted below.

## Strengths

- **Commit discipline**: Plan 02-01 strictly isolates the `git mv` commit (Task 1) from content edits (Task 2), and explicitly warns that the workspace won't compile between them — matches D-13 and Phase 1 precedent exactly.
- **Trap guards surfaced**: Plan 02-01 Task 3 explicitly flags scangame-py as needing a NEW `classic-config-core` dep (research's "second dep-graph delta"). Plan 02-02 Task 1 correctly sequences the Node parity generator fix BEFORE Task 3's gate run, averting the `FileNotFoundError` crash.
- **Explicit file staging**: Both plans use explicit `git add <paths>` lists rather than `git add -A`, honoring CLAUDE.md git safety rules.
- **Grep-based acceptance criteria**: Every task has falsifiable post-conditions via `Select-String` on the exact patterns. The full-workspace sweep in Task 3 (`Get-ChildItem ... | Select-String 'classic_crashgen_settings_core|classic-crashgen-settings-core'` → 0 matches) is a strong final assertion.
- **Stray .bak as separate commit** (Task 4) correctly honors D-17.
- **yamldata.rs same-crate swap**: Plan 02-01 Task 2 Step A.3 correctly uses `use crate::...` rather than `use classic_config_core::...` since yamldata.rs now lives in the same crate as crashgen_rules.
- **Crate-root attribute awareness**: Task 2 Step A.2 notes that the moved file was formerly a crate root and may contain `#![...]` inner attributes that need to be stripped or relocated — a subtle trap a less careful plan would miss.

## Concerns

### HIGH

- **None.** No HIGH-severity issues found. The critical Node parity generator crash is correctly sequenced first in Plan 02-02.

### MEDIUM

- **Plan 02-01 Task 2, Step B.4 — brittle literal-line deletion**: The action says "delete exactly this literal line (verified at line 22 during planning)". Hardcoding line 22 is fragile; if anything shifts the file between planning and execution, "delete line 22" becomes meaningless. The acceptance criterion (grep returns 0 matches) is the right check, but the instruction should say "delete the line matching `classic-crashgen-settings-core = { path = ...}`" rather than citing a line number.

- **Plan 02-01 Task 2 — missing test for scangame-core inline tests**: The research notes 4 inline unit tests inside `crashgen_rules.rs`. Task 2's acceptance criteria rely on `cargo test --workspace` passing, but do not explicitly assert that those 4 tests now run under `classic-config-core::crashgen_rules::tests`. Adding `cargo test -p classic-config-core --lib crashgen_rules::tests` as an acceptance command would catch a rare failure mode where the tests somehow get excluded.

- **Plan 02-02 Task 1 — SQUAD_BY_OWNER removal safety**: Removing only one side of the dict pair could leave an inconsistency. Plan 02-02 should add a post-edit step that runs the FULL pytest suite in `tools/node_api_parity/tests/` (not just `test_generate_baseline_targets.py`) and additionally runs `python tools/node_api_parity/generate_baseline.py --dry-run` or equivalent to confirm the generator itself loads without error.

- **Plan 02-02 Task 1 Step B.7 — floor count update ambiguity**: The planner should run `Select-String` on the current floor value BEFORE editing, not assume the pre-Phase-2 value.

- **Plan 02-02 Task 2 — .planning/REQUIREMENTS.md edit risk**: Editing this file risks touching the CGEN-01/02/03 checkboxes that the verifier workflow expects to flip. Recommend either removing this file from `files_modified`, or adding an explicit rule "do not touch checkbox state for CGEN-*".

### LOW

- **Plan 02-01 Task 3 — Python binding build coverage**: Step G runs `cargo build --workspace`, which does compile the PyO3 rlib but not the Python wheel. Plan 02-02 Task 3 Step B jumps straight to the gate instead of running `./rebuild_rust.ps1 -Target python` first. **This could cause the Python gate to drift against a stale wheel.** Recommend adding `./rebuild_rust.ps1 -Target python` as an explicit preceding step.
- **Plan 02-02 Task 3 — no pre-gate grep validation**: cheap sanity grep worth adding.
- **Plan 02-02 Task 2 Step D.7/8 — may be no-op**: Recommend a pre-step grep before opening adjacent API doc files.
- **Plan 02-01 Task 2 — optional cargo clippy step**: Neither plan currently runs clippy. Recommend adding it to Task 2 Step F as a defensive check for unused-import warnings.

## Risk Assessment

**Overall risk: LOW.** Execute as written with the rebuild_rust.ps1 step added to Plan 02-02 Task 3.

---

## Codex Review

**02-01-PLAN.md**

**Summary**
The plan is well-researched and mostly complete on file coverage, but it is not executable as written because Task 2 requires `cargo build --workspace` and `cargo test --workspace` before Task 3 migrates the binding crates. Since the binding crates remain in the workspace and still depend on the deleted crate at that point, the current sequencing breaks the plan's own verification gates.

**Strengths**
- The consumer inventory is thorough and matches the repo archaeology: Rust core consumers, binding consumers, workspace-member removal, and the `yamldata.rs.bak` cleanup are all explicitly enumerated.
- D-13 blame preservation is handled correctly in principle with a rename-only `git mv` task separated from content edits.
- The plan correctly calls out the two new dependency edges that matter: `classic-scangame-core` and `classic-scangame-py` gaining `classic-config-core`.
- Keeping binding filenames unchanged avoids unnecessary churn and matches the "strict structural refactor" requirement.
- The separate `.bak` deletion commit is good audit hygiene and stays within scope.

**Concerns**
- **HIGH — 02-01 Task 2 Step F / Step H:** the plan asks for `cargo build --workspace` and `cargo test --workspace` before Task 3 updates `classic-node`, `classic-config-py`, `classic-scanlog-py`, and `classic-scangame-py`. After removing `classic-crashgen-settings-core` from workspace members, those crates will still reference the removed crate, so workspace verification cannot pass at that point.
- **HIGH — 02-01 objective + Task 1 done text:** the plan says "All commits preserve blame and stay buildable," but Task 1 explicitly creates and commits a non-compiling rename-only state. That contradiction needs to be resolved.
- **MEDIUM — 02-01 objective/output:** it claims Phase 2 yields a "16-crate business-logic topology." After Phase 1, Phase 2 should reduce `18 -> 17`, not `17 -> 16`. This is likely to propagate wrong documentation updates later.
- **MEDIUM — 02-01 Task 3 Step F / acceptance criteria:** the grep requires zero `classic[-_]crashgen[-_]settings[-_]core` matches in all `*.rs`/`*.toml`, but the research already identified source doc-comment mentions in the Python binding `crashgen_rules.rs` files. The task does not instruct updating those comments, so the acceptance gate is internally inconsistent.
- **LOW — 02-01 Task 1 acceptance criteria use `test -f`** while the plan is otherwise PowerShell-oriented.

**Suggestions**
- Move workspace-wide `cargo build/test` to after Task 3, or change Task 2 verification to package-scoped builds only: `classic-config-core`, `classic-scanlog-core`, and `classic-scangame-core`.
- If you want every post-Task-1 commit buildable, either merge Tasks 2 and 3 into one content commit, or migrate bindings before removing the old crate from workspace members.
- Fix every crate-count reference in this plan to Phase-2-correct state: `17` business-logic crates after this merge.
- Either update the Python binding source doc comments during Task 3 or narrow the grep to actual imports/Cargo deps instead of any raw string match.
- Replace shell-agnostic `test -f` checks with `Test-Path` for consistency.

**Risk Assessment**
**HIGH** — The file coverage is good, but the Task 2 / Task 3 dependency ordering is a real execution blocker. As written, the plan cannot satisfy its own workspace verification gates.

---

**02-02-PLAN.md**

**Summary**
This plan is structurally stronger than 02-01 and correctly treats the Node parity generator as a precondition rather than an afterthought. The main remaining issues are accuracy and verification discipline: it uses the wrong post-Phase-2 crate count, and it omits the Python rebuild step that the research explicitly said is required before running the Python parity gate.

**Strengths**
- The Node parity generator crash risk is identified and handled in the right order: tooling update first, gate run later.
- The plan avoids scope creep: no baseline regeneration, no feature work, and no test additions beyond existing parity-tooling tests.
- The API-doc consolidation approach is sensible.
- Acceptance criteria are concrete and grepable.

**Concerns**
- **HIGH — 02-02 Task 3 Step B:** the plan runs `python tools/python_api_parity/check_parity_gate.py --repo-root .` without the `./rebuild_rust.ps1 -Target python` step that the research called out as necessary. That risks stale installed-wheel surfaces and makes the Python parity result unreliable.
- **HIGH — 02-02 objective / Task 2 Step F / success criteria:** the plan repeatedly says docs should reflect a "16-crate topology." That is false for Phase 2; Phase 2 should leave `17` business-logic crates. This can directly produce incorrect updates to `CLAUDE.md`, `.planning/*`, and API docs.
- **MEDIUM — 02-02 Task 2 file scope:** `AGENTS.md` is included as a modified file and must-have target even though the research found no active matches there. That is unnecessary churn in a refactor phase that should stay minimal.
- **LOW — 02-02 Task 3 Step A:** the CXX gate command drops the researched `--repo-root .` argument.
- **LOW — 02-02 Task 2** asks for edits to `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` while also warning against rewriting historical phase records.

**Suggestions**
- Add `./rebuild_rust.ps1 -Target python` immediately before the Python parity gate in Task 3.
- Correct all Phase-2 state references from `16` to `17`; reserve `16` for after Phase 3 / final Phase 4 validation.
- Drop `AGENTS.md` from `files_modified` unless a concrete current-state reference is found during execution.
- Use the researched CXX gate invocation verbatim for consistency.
- Tighten the `.planning/*` doc-update instructions so only present-tense architecture/count statements change, not phase-history text.

**Risk Assessment**
**MEDIUM** — The Node-parity sequencing is good and the scope is controlled, but the missing Python rebuild step and wrong crate-count target are material enough that I would not execute this plan unchanged.

---

## Consensus Summary

### Agreed Strengths (2+ reviewers)

- **D-13 blame preservation** via isolated `git mv` commit separated from content edits — all three reviewers praised this (Gemini, Claude, Codex).
- **Node parity generator tooling fix sequenced before gate run** — all three reviewers recognized this as correctly handled.
- **scangame-py dep-add trap surfaced** — Gemini and Claude explicitly praised the dual dep-graph awareness; Codex implicitly endorsed via his positive strengths note.
- **Separate yamldata.rs.bak cleanup commit (D-17)** — Gemini and Codex both praised.
- **Explicit staging / no `git add -A`** — Claude praised; Codex implicitly accepted.

### Agreed Concerns — HIGH PRIORITY (2+ reviewers)

**1. CRATE COUNT WRONG — Phase 2 ends at 17, not 16** (Gemini LOW, Codex HIGH — consensus across 2 reviewers)
- Plans state "16-crate topology" but Phase 1 went 19→18, so Phase 2 goes 18→17. "16" is reserved for end of Phase 3.
- Touches CLAUDE.md, docs/api/*, .planning/ROADMAP.md, .planning/REQUIREMENTS.md, .planning/PROJECT.md
- **Impact**: Without correction, plans will actively MIS-UPDATE the docs during execution.

**2. MISSING `rebuild_rust.ps1 -Target python` BEFORE PYTHON PARITY GATE** (Claude LOW, Codex HIGH — consensus across 2 reviewers)
- Plan 02-02 Task 3 Step B jumps to `check_parity_gate.py` without refreshing the PyO3 wheel first.
- Research Section 5 explicitly calls out that the Python parity gate requires the wheel to be current.
- **Impact**: Python parity gate could drift against a stale wheel, producing false positives/negatives.

### Codex-Only HIGH Findings (single-reviewer but credible)

**3. TASK 2 VERIFICATION SEQUENCING BUG — WORKSPACE BUILD WILL FAIL** (Codex HIGH, others missed)
- Plan 02-01 Task 2 runs `cargo build --workspace` + `cargo test --workspace` BEFORE Task 3 migrates the 4 binding crates.
- At that point, the workspace still contains the binding crates that import `classic_crashgen_settings_core::*` and the `classic-crashgen-settings-core` crate directory has been deleted (Task 2 Step E).
- Workspace verification CANNOT pass until the bindings migrate in Task 3.
- **This is a real execution blocker** — the plan cannot satisfy its own verification gates as written.
- Fix options: (a) move workspace verification to end of Task 3, or (b) scope Task 2 verification to `cargo build -p classic-config-core -p classic-scanlog-core -p classic-scangame-core`, or (c) migrate bindings before deleting the crate directory.

**4. OBJECTIVE/TASK-1 CONTRADICTION** (Codex HIGH)
- Objective says "all commits preserve blame and stay buildable" but Task 1 creates a non-compiling rename-only state deliberately.
- Need to resolve the contradictory language — D-13 means blame preservation, not "every commit builds"; Task 1 intentionally produces a non-building intermediate state. The claim in the objective is just wrong.

### Codex-Only MEDIUM Findings

**5. scangame-py/classic-node/etc. crashgen_rules.rs doc-comment inconsistency** (Codex MEDIUM)
- Plan 02-01 Task 3 grep acceptance requires zero `classic[-_]crashgen[-_]settings[-_]core` matches in `*.rs`, but the Python binding source has doc comments mentioning the crate name.
- Either expand Task 3 to update those doc comments, OR narrow the grep pattern.

**6. AGENTS.md in 02-02 files_modified is unnecessary churn** (Codex MEDIUM)
- Research did not find any `classic-crashgen-settings-core` matches in AGENTS.md.
- Drop from `files_modified` unless a grep during execution finds something.

### Claude-Only MEDIUM Findings

**7. SQUAD_BY_OWNER / RUST_OWNER_BY_CRATE consistency verification** (Claude MEDIUM)
- Claude wants a post-edit `generate_baseline.py --dry-run` + full tests/ pytest suite run to catch any remaining dict-pair inconsistencies.

**8. Floor count pre-read (Plan 02-02 Task 1 Step B.7)** (Claude MEDIUM)
- The planner assumed the pre-edit floor was 19, but Phase 1 may have already lowered it to 18. Should read the current value first.

**9. .planning/REQUIREMENTS.md checkbox protection** (Claude MEDIUM)
- Task 2 edits REQUIREMENTS.md but must NOT touch CGEN-* checkboxes (verifier workflow updates those).

### Divergent Views

- **Overall risk**: Gemini and Claude say **LOW**; Codex says **HIGH** for 02-01 and **MEDIUM** for 02-02.
- Gemini and Claude both gave clean executes with minor polish; Codex said "I would not execute this plan unchanged."
- The divergence is explained by Codex catching the Task 2/3 sequencing bug that the other two missed. If that bug is real (and on inspection it appears to be — the workspace members list is edited in Task 2 Step E, binding migrations are in Task 3, and workspace build runs in Task 2 Step F), Codex's HIGH rating is more accurate.

### Reviewer Accuracy Notes

- **Codex** did the deepest structural analysis and caught the critical sequencing bug — this is exactly the class of issue (hidden ordering constraint between task boundaries) that benefits from adversarial cross-AI review.
- **Gemini** and **Claude** both missed the Task 2/3 ordering issue but made the same observation about the Python rebuild step, arriving from different angles.
- All three agreed on the Phase-2 strengths (blame preservation, parity generator ordering, scope discipline).

---

## Recommended Next Action

**Run `/gsd:plan-phase 2 --reviews` to incorporate this feedback before execution.**

Priority fixes (in order of severity):

1. **HIGH**: Fix Task 2 / Task 3 sequencing in Plan 02-01 so `cargo build/test --workspace` runs AFTER bindings migrate (Codex concern #3).
2. **HIGH**: Remove the "all commits buildable" claim from Plan 02-01 objective, or re-align Task 1 to produce a buildable state (Codex concern #4).
3. **HIGH**: Correct all "16 crate" references to "17 crate" across both plans (Gemini + Codex consensus, concern #1).
4. **HIGH**: Add `./rebuild_rust.ps1 -Target python` before Python parity gate in Plan 02-02 Task 3 Step B (Claude + Codex consensus, concern #2).
5. **MEDIUM**: Resolve scangame-py doc-comment grep inconsistency (Codex concern #5).
6. **MEDIUM**: Add post-Node-generator-edit dry-run check (Claude concern #7).
7. **MEDIUM**: Pre-read floor count before editing (Claude concern #8).
8. **MEDIUM**: Replace line-22 literal with pattern match (Claude).
9. **MEDIUM**: Protect CGEN-* checkboxes in REQUIREMENTS.md edit (Claude concern #9).
10. **MEDIUM**: Drop AGENTS.md from 02-02 files_modified unless execution grep finds something (Codex concern #6).
11. **LOW**: PowerShell consistency — replace `test -f` with `Test-Path` (Codex).
12. **LOW**: Add `cargo tree -p classic-scangame-core` after build for dep-tree visual confirmation (Gemini).
13. **LOW**: Add `cargo clippy --workspace` to Task 2 defensive checks (Claude).
