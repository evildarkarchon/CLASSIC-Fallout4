---
phase: 4
reviewers: [claude, codex]
reviewed_at: 2026-04-09T12:00:00-07:00
review_round: 2
supersedes: "Round 1 REVIEWS.md (2026-04-09T00:00:00-07:00) which reviewed the original 6 Phase 4 plans and surfaced D1 (version-pe-shape row incorrectly dropped), H1/H2/H3 (agreed HIGHs), and U1-U5 (unique HIGHs). That review drove /gsd:plan-phase 4 --reviews commit 1aee1943, which added 667 lines across the 6 plans addressing every concern."
plans_reviewed:
  - 04-01-tooling-expansion-PLAN.md
  - 04-02-scanlog-promotion-PLAN.md
  - 04-03-config-promotion-PLAN.md
  - 04-04-version-registry-and-pe-version-PLAN.md
  - 04-05-aux-promotion-PLAN.md
  - 04-06-tier2-cleanup-cascade-PLAN.md
review_scope: "Round 2 verification review of the revised Phase 4 plans (commit 1aee1943). Both Claude and Codex received the same ~475 KB prompt containing PROJECT.md, ROADMAP, REQUIREMENTS, CONTEXT.md, RESEARCH.md (with Research Amendments A1–A7), VALIDATION.md, Round 1 REVIEWS.md (for continuity), and all 6 revised PLAN.md files. Primary job was auditing whether each of the 9 Round 1 concerns landed correctly and hunting for new issues introduced by the revisions."
---

# Cross-AI Plan Review — Phase 4: Node Tier Collapse (Round 2)

> Round 2 verification pass by Claude Opus 4.6 (separate CLI session) and Codex (GPT-5.4). Goal: audit whether the /gsd:plan-phase 4 --reviews revision landed Round 1's 9 concerns correctly, and hunt for new issues. Neither reviewer saw Round 2 work from the other — they critiqued the same commit (1aee1943) independently.

---

## Consensus Summary

**All 9 Round 1 concerns (D1, H1, H2, H3, U1, U2, U3, U4, U5) are mechanically addressed.** Both reviewers independently verified the revisions landed in the expected places with the expected shapes. The revision pass was structurally thorough — D1's row count restoration, H1's fail-closed guard, H2's count sweep, H3's frontmatter reconciliation, U1's Python cross-binding probe, U2's primary-source swap, U3's Phase 2c.1 loop, and U4's success-criterion rewording all verified as present and correct.

**However, both reviewers surfaced new HIGH issues introduced by the revisions themselves** — none structurally fatal, but enough that Phase 4 should NOT execute without a targeted cleanup pass. The consensus picture: Plan 06 still has M7-atomic-mechanics holes (frontmatter gaps, retry-discipline gray zones, placeholder trivial-pass), Plan 05's U5 precondition and routing ambiguity both have fail-closed gaps, Plan 03 has residual text drift that H2's sweep didn't catch, and Plan 04 re-introduced "likely" signature-guessing language in a spot U5 was trying to stamp out.

The two reviewers **diverge on U5's status** (Claude: RESOLVED with separate writeAutoscanReport HIGH; Codex: PARTIALLY RESOLVED with precondition self-block HIGH) — but these are **complementary**, not contradictory findings: Claude caught a routing-table fallback hole in Task 0, while Codex caught a precondition-logic bug in Tasks 1 and 2 that compares stale Plan 1 sizing counts against live post-Plan-4 counts. Both are real HIGH-severity Plan 05 issues; fix both.

### Round 1 Audit Table

| Concern | Claude R2 | Codex R2 | Consensus |
|---|:--:|:--:|---|
| **D1** — Plan 04 version-pe-shape restoration | ✅ RESOLVED | ✅ RESOLVED | **LANDED** — row count 6→7 restored; row shape + Fallout4VersionInfo precedent + acceptance criteria all verified |
| **H1** — Plan 01 validate_contract_surface() fail-closed | ✅ RESOLVED | ✅ RESOLVED | **LANDED** — 3 malformed shapes explicitly rejected; pytest fixtures automate injection; >= 19 assertion (but see MEDIUM below on blank-string coverage) |
| **H2** — Plan 03 count drift swept to 11+23=34 | ✅ RESOLVED | ✅ RESOLVED | **LANDED** — title/objective/task name/acceptance all on 34; hard-coded crashgen set replaced with live surface lookup (but see HIGH on bullet 8 self-reference + MEDIUM on config.deferred drift) |
| **H3** — Plan 06 files_modified reconciliation | ✅ RESOLVED | ✅ RESOLVED | **LANDED** — STATE.md, ROADMAP.md, parity-artifacts all present; git status --porcelain integrity probe added (but see HIGH on node_api_surface.json omission + MEDIUM on SUMMARY.md gap) |
| **U1** — Plan 04 A6 Python cross-binding probe | ✅ RESOLVED | ✅ RESOLVED | **LANDED** — Task 1 Step 4.5 runs Python parity gate; Option A/B/C escalation documented; both gates required for commit |
| **U2** — Plan 01 A10 sizing primary source | ✅ RESOLVED | ✅ RESOLVED | **LANDED** — parity_diff_report.json::gaps is PRIMARY; schema has primary_source/cross_validation fields |
| **U3** — Plan 06 Phase 2c.1 loop re-sequencing | ✅ RESOLVED | ✅ RESOLVED | **LANDED** — explicit Phase 2a/2b/2c/2c.1/2d structure; working tree stays uncommitted across iterations |
| **U4** — Plan 06 success criterion 5 rewording | ✅ RESOLVED | ✅ RESOLVED | **LANDED** — "no Tier-2 SEMANTICS in baselines; governance file preserved but emptied" verified |
| **U5** — Plan 05 dual-source + locked routing table | ✅ RESOLVED | ⚠️ PARTIALLY RESOLVED | **MIXED** — dual-source check + locked routing table present, but reviewers found independent HIGH issues (Claude: writeAutoscanReport ambiguity; Codex: precondition self-block). See §Plan 05 HIGHs below. |

**Round 1 remediation verdict:** The revision pass was mechanically thorough and caught all 9 concerns in the right places. No concern was dropped; none were half-fixed at the surface level. This validates the `/gsd:plan-phase --reviews` workflow as working correctly for revision loops.

---

## Agreed HIGH Concerns (Round 2 — both reviewers raised or converged)

| # | Concern | Plan | Evidence | Reviewers |
|---|---------|:--:|---|---|
| **R2-H1** | **Plan 05 U5 mechanics have gaps** that independent reviewers caught from different angles. Claude flagged the `writeAutoscanReport` routing-table fallback as not fail-closed: Task 0 Step 2 says "document and proceed" if the symbol is in BOTH scangame.rs and scanlog.rs, or NEITHER — an executor could document the ambiguity and continue rather than escalating. Codex flagged the dual-source precondition as self-blocking: Task 1 and Task 2 both compare the original `04-01-A10-sizing.json` counts (captured at Wave 0 / Plan 01 time) against live `parity_diff_report.json::gaps` counts (measured after Plans 02/03/04 have already reduced scanlog/config/version_registry). The precondition will ALWAYS detect mismatches for owners that Plans 2-4 legitimately reduced — so it fires on a healthy execution, not just a broken one. | 05 | Claude: 05 Task 0 Step 2; Codex: 05 lines 262, 463 (Task 1 Step 1, Task 2 Step 1) | Claude + Codex converged at the Plan 05 U5 level, even though they caught different specific bugs |
| **R2-H2** | **Plan 06 Task 2 frontmatter and commit mechanics have two separate gaps.** (a) Claude flagged `parity-artifacts/node_api_surface.json` as missing from both `files_modified` AND the Task 2 Step 10 `git add` command, while all 6 other parity-artifacts mirrors ARE listed — asymmetric and likely to trip the Step 9 `git status --porcelain` integrity probe during execution. (b) Codex flagged Plan 06's conditional `SUMMARY.md` output as missing from `files_modified` entirely. Both are frontmatter-honesty regressions in exactly the area H3 tried to stamp out. | 06 | Claude: Plan 06 files_modified vs Step 10 git add asymmetry; Codex: Plan 06 line 9, 520 (files_modified vs SUMMARY.md creation) | Both reviewers flagged Plan 06 frontmatter but at different missing files |
| **R2-H3** | **Plan 06 Task 2 Phase 2b retry discipline is contradictory.** Claude: Step 6 says "EXACTLY ONE retry" for transient failures, but the next paragraph says "if diagnostic (guard fired, deferred_total > 0), do NOT retry — fix the underlying cause first." This leaves an ambiguous zone where an executor can't distinguish transient from diagnostic BEFORE retrying. An executor following the letter retries once on any failure then aborts — which means genuine diagnostic failures get a wasted retry before re-entering Phase 2a. Codex flagged this tangentially as part of U3 status but focused on the MEDIUM real-shape assertions instead. | 06 | Claude: Plan 06 Task 2 Step 6; Codex: noted but not separately flagged | Claude primary; structural issue Codex didn't separately hit |
| **R2-H4** | **Plan 05 conditional output files missing from files_modified.** Codex flagged: Plan 05 Task 0 may create `_plan05_routing_table.json` but it's absent from `files_modified`; Plan 05 Task 1 may edit `classic-crashgen-settings-core/src/lib.rs` but that path is not listed even though the task explicitly allows it. Same class of issue as R2-H2 (b) for Plan 06, different plan. | 05 | Codex: Plan 05 lines 35, 211, 323 | Codex primary; Claude didn't separately flag but the pattern matches Claude's `assert.ok(true)` concern. |

## Divergent-But-Complementary HIGH Concerns (unique per reviewer, both real)

| # | Reviewer | Concern | Severity | Notes |
|---|---|---|:--:|---|
| **R2-H5** | Claude | **Plan 03 must_haves.truths bullet 8 uses self-referential edit-history language.** The bullet reads: "... This bullet REPLACES the earlier 'all new rows have rustCrate: classic-config-core' wording, which contradicted Task 1 Step 2/3 cross-crate routing." Plan text should describe the CURRENT desired state, not its edit history. | HIGH | Claude: Plan 03 must_haves.truths bullet 8. **Fix:** Drop "This bullet REPLACES..." clause; make the bullet declarative about current routing only. |
| **R2-H6** | Codex | **Plan 03 still has residual goal drift after H2 sweep.** must_have says `config.deferred may end at 0 (or ≤2 if any residuals surface that Plan 5/7 absorbs)` — but (a) the objective and acceptance path require `0`, not `≤2`, and (b) **there is no Plan 7 in this phase**. The H2 sweep caught the count math but missed this deferred-target drift + stale plan reference. | HIGH | Codex: Plan 03 lines 35, 67. **Fix:** Change `0 (or ≤2)` to `0`; remove "Plan 7" reference (route to Plan 5 only). |

## Agreed MEDIUM Concerns

| Concern | Plans | Evidence | Reviewers |
|---------|:--:|---|---|
| **Real-shape smoke assertions still inconsistently applied.** Plan 04 Task 2 still uses `{} as JsCrashgenSettingsRules` + `toBeDefined()` for interface/function tests; Plan 05 runtime test still uses `{} as JsCheckRule` + `assert.ok(true)`. These are the exact weak patterns Round 1 tried to stamp out — the strengthening landed in Plans 02/03 but not 04/05. | 04, 05 | Claude (LOW on 05 assert.ok(true)) + Codex (MEDIUM explicit: Plan 04 lines 575, 587; Plan 05 lines 343, 409) | Both flagged |
| **Plan 04 `migrateGameVersionSetting` handoff unclear.** Plan 04 says "explicitly assigned to Plan 5 Task 1 cross-owner reconciliation." Plan 05's locked routing table lists it with `ownerModule: version_registry, rustCrate: classic-version-registry-core`. But if it IS a version_registry symbol, why does Plan 05 (aux promotion) handle it instead of Plan 04 (version_registry promotion)? The handoff rationale isn't articulated. | 04, 05 | Claude: Plan 04 interfaces block; Codex: flagged as part of U5 routing table | Both flagged at different lines |
| **Plan 04 version_registry rows have "likely" rustSymbol language.** Task 2 Step 6 says "rustSymbol values derived from reading classic-node/src/version_registry.rs to find the underlying core types (likely `CrashgenRegistryEntry`, `CrashgenSettingsRules`, `check_crashgen_config_with_rules`, `check_crashgen_full_with_rules`)." **The word "likely" is exactly what U5 was trying to eliminate from Plan 05.** Re-introducing it in Plan 04 Task 2 reverses that discipline. | 04 | Claude: Plan 04 Task 2 Step 6 | Claude primary; Codex didn't separately flag |
| **Plan 04 no rustCrate acceptance for 4 version_registry rows.** The PE-version 3 rows ARE checked (A3 enforcement asserts `rustCrate == classic-version-core`), but there's no corresponding check for the 4 version_registry rows carrying `rustCrate: classic-version-registry-core`. Plans 02/03/05 enforce rustCrate on new rows; Plan 04 drops enforcement for 4 of its 7 rows. | 04 | Claude: Plan 04 Task 2 acceptance criteria | Claude primary; Codex didn't separately flag but Codex's "cross-runtime coverage contradiction" (next row) is adjacent |
| **Plan 04 cross-runtime coverage contradicts itself.** must_have says "the runtime test includes both PE-version AND checkCrashgenConfigWithRules coverage," but the action text downgrades the version_registry runtime test to "if practical." | 04 | Codex: Plan 04 lines 37, 624 | Codex primary |
| **H1 guard still not fully fail-closed for exotic values.** Codex: the H1 implementation rejects only `None` for rustSymbol/nodeExport, not empty strings or wrong types. A row like `{"id": "...", "rustSymbol": "", "nodeExport": "Foo"}` or `{"rustSymbol": ["PeVersionResult"]}` would either slip past or throw an uncaught exception instead of producing a clean guard diagnostic. | 01 | Codex: Plan 01 lines 430, 444, 455, 465 | Codex primary; Claude didn't flag |
| **Plan 06 Phase 2c.1 placeholder value `-1` is trivial-pass.** Step 5 says use `-1` as the temporary placeholder value. But `assert len(tier1) >= -1` is always true — if the executor's Phase 2c.1 loop exits early or is skipped, the test passes silently with the `-1` placeholder still in place. Should use a fail-loud placeholder like `assert False, "COMPUTED_FLOOR placeholder — Phase 2c.1 must replace this"`. | 06 | Claude: Plan 06 Task 2 Step 5 | Claude primary |
| **Plan 06 Step 2 line-number drift mitigation weak.** Instructions say "Re-verify line numbers with Select-String before editing" but the specific expected line numbers from RESEARCH.md are cited DIRECTLY in the action body. Rushed executor trusts the numbers; they drift during tooling changes. Phase 3 Plan 09b's precedent was grep-anchored targets. | 06 | Claude: Plan 06 Task 2 Step 2 | Claude primary |
| **Plan 02 scanlog row count range `(57, 58)` not resolved.** Acceptance `assert len(rows) in (57, 58)` accepts either but doesn't commit to one. SUMMARY's "final reconciled count" becomes non-deterministic across runs. Same issue with `(8, 9)` for normal rows. | 02 | Codex: Plan 02 lines 5, 30; Claude: same (MEDIUM) | Both flagged |

## Agreed LOW Concerns

- **PowerShell vs Bash residuals cross-plan**. Plan 04 Task 1 verify block uses `grep -q` via automation string; Plan 06 Task 1 acceptance has `-ge 50` bash syntax. Minor but forces Git Bash for some verification steps. Both reviewers flagged.
- **Plan 05 `assert.ok(true)` for interface coverage**. Same as MEDIUM real-shape assertion issue, different classification (Claude LOW, Codex MEDIUM).
- **Plan 01 U2 acceptance tolerates `scanlog['deferred_primary'] in (66, 67)`** even though the sizing script filters GLOBAL_FCX_HANDLER — should force 66. Codex primary.
- **Plan 01 Task 3 `bun run build` may regenerate `index.d.ts`** even in a no-source-change plan; no explicit cleanup instruction. Claude primary.
- **Plan 06 ripgrep regex has PowerShell quoting ambiguity** (`['"]` character class inside double-quoted string). Claude primary.
- **Plan 03 `detectConfigDuplicates([])` test** passes empty array with "adjust signature based on live index.d.ts" comment — same class as Plan 04's signature-guessing MEDIUM. Claude primary.
- **Plan 04 Task 2 Step 2 `Select-String` pattern imprecise** — matches any line containing "extractPeVersion", not just the declaration. Claude primary.
- **Plan 04 Task 1 Step 4 `rust_api_surface.json` schema not pre-verified** — lookup assumes `crate` field per symbol entry; if schema has evolved, lookup returns empty set and assertion falsely passes. Claude primary.

---

## Full Review — Claude

**Reviewer:** Claude Opus 4.6 (separate CLI session via `claude -p` with stdin pipe)
**Output size:** 22.9 KB, 124 lines
**Token usage:** (not emitted by Claude CLI)

### Summary

All 9 Round 1 concerns mechanically resolved. Revision was structurally sound. Four new HIGH issues found: (1) Plan 06 files_modified omits `parity-artifacts/node_api_surface.json` while listing all 6 other mirrors, (2) Plan 06 Phase 2b retry discipline is contradictory between transient and diagnostic failure paths, (3) Plan 03 must_haves bullet 8 contains edit-history self-referential language, (4) Plan 05 Task 0 `writeAutoscanReport` routing-table fallback is not fail-closed. Plus 8 MEDIUM and 7 LOW concerns around acceptance criterion completeness, signature pre-verification, and placeholder safety.

### Risk Assessment (Claude)

| Plan | Risk | Justification |
|------|------|---------------|
| 04-01 Tooling Expansion | LOW | All Round 1 concerns resolved. H1 fail-closed is mechanically correct. Dual-source A10 sizing is implemented. One LOW concern (index.d.ts accidental regeneration). |
| 04-02 Scanlog Promotion | LOW-MEDIUM | Proven Scenario E pattern. Row count acceptance accepts `(57, 58)` range but reconciliation logic is correct. |
| 04-03 Config Promotion | MEDIUM | H2 count drift swept to 34. Cross-crate routing uses live surface lookup. Bullet 8 self-reference (HIGH) needs cleanup. |
| 04-04 Version Registry + PE | MEDIUM | D1 restored. U1 cross-binding probe wired. Missing rustCrate acceptance check for 4 VR rows. "likely" rustSymbol language re-introduced for VR rows. |
| 04-05 Aux Promotion | MEDIUM | U5 dual-source precondition explicit. Locked routing table. writeAutoscanReport fallback-ambiguity not fail-closed (HIGH). assert.ok(true) in runtime.node.test.mjs (LOW). |
| 04-06 Tier-2 Cleanup Cascade | **HIGH** | Most bisect-sensitive plan. Phase 2a/2b/2c/2c.1/2d re-sequencing is correct. TWO HIGH issues (parity-artifacts omission, retry discipline contradiction) + placeholder-value trivial-pass bug + line-number drift mitigation is weak. Execution requires careful reading. |

### Claude Recommendation

**PROCEED WITH TARGETED REVISIONS.** Do not re-enter the full cross-AI review cycle — Round 1 remediation was thorough and remaining issues are acceptance-criterion completeness and Plan 06 mechanics, not structural bugs.

Must-fix before `/gsd:execute-phase 4`:
1. Plan 06 files_modified: add `parity-artifacts/node_api_surface.json` OR document why it's absent
2. Plan 06 Task 2 Phase 2b retry discipline: clarify the retry gate — distinguish transient vs diagnostic paths
3. Plan 06 Task 2 Step 5 placeholder: use a fail-loud placeholder (`assert False`) not `-1`
4. Plan 05 Task 0 Step 2: fail-closed on writeAutoscanReport ambiguity (no silent "document and proceed")
5. Plan 04 acceptance criteria: add rustCrate enforcement for the 4 version_registry rows

Should-fix (non-blocking but worth a quick sweep):
6. Plan 04 rustSymbol pre-verification: add grep step for checkCrashgen*WithRules signatures
7. Plan 03 bullet 8: drop self-referential "This bullet REPLACES..." phrasing
8. Plan 05 `assert.ok(true)`: replace with at least a minimal shape assertion
9. Plan 06 line numbers: sweep to grep-anchor references

*(Full Claude review preserved at `$env:TEMP/gsd-review-claude-4.md` if raw text is needed.)*

---

## Full Review — Codex

**Reviewer:** Codex (GPT-5.4 via `codex exec --skip-git-repo-check` with stdin pipe)
**Output size:** 797 KB transcript; review content extracted from the second-copy final summary (lines 8261-8314)
**Token usage:** not captured from this run

### Summary

All 8 of D1/H1/H2/H3/U1/U2/U3/U4 resolved cleanly. U5 status is "PARTIALLY RESOLVED" because the dual-source precondition is mechanically wrong: both Task 1 and Task 2 compare the ORIGINAL Plan 1 sizing counts (captured at Wave 0) against the LIVE `parity_diff_report.json::gaps` counts (measured post-Plans 2-4), across all owners including scanlog/config/version_registry — which Plans 2-4 have already reduced. The mismatch path fires even in a healthy execution. Another revision cycle is needed before execution. Plus MEDIUM drift in Plan 03 (`config.deferred` target drift + stale "Plan 7" reference), Plan 04 (runtime-test contradiction between must-have and action text), and test-quality patterns (Plan 04 + Plan 05 still use `{} as Type` + `assert.ok(true)`).

### Risk Assessment (Codex)

| Plan | Risk | Justification |
|------|------|---------------|
| 04-01 Tooling Expansion | MEDIUM | Round 1 fixes landed, but the guard implementation still has malformed-type holes and the sizing acceptance still tolerates stale scanlog math |
| 04-02 Scanlog Promotion | MEDIUM | Structure is solid, but the 57/58 and 8/9 split is still unresolved in active prose |
| 04-03 Config Promotion | MEDIUM | H2 mostly landed, but `config.deferred` target still drifts between `0` and `≤2`, and the stray `Plan 7` mention is a plan-integrity smell |
| 04-04 Version Registry + PE | MEDIUM | D1 and U1 landed correctly, but version_registry runtime test is still softened by "if practical," and conditional Python fallback path is broader than the frontmatter admits |
| 04-05 Aux Promotion | **HIGH** | Revised U5 mechanism introduced a blocking logic bug in the precondition check; still frontmatter/test-quality drift around routing-table and aux work |
| 04-06 Tier-2 Cleanup Cascade | MEDIUM | H3/U3/U4 landed well; still frontmatter drift for Plan 6 summary artifact; minor wording inconsistencies |

**Overall phase risk: HIGH**

### Codex Recommendation

**Another revision cycle is needed before execution.**

The blocker is Plan 05: the new U5 precondition compares the wrong datasets at the wrong time and will abort once Plans 2-4 have already reduced the live gap counts. Fix that first, then do a short cleanup pass for the remaining drift:
- Tighten Plan 01's guard to reject blank/non-string fields cleanly
- Make Plan 04's version_registry runtime test mandatory, not optional
- Sweep Plan 03's `config.deferred` / `Plan 7` contradiction
- Reconcile `files_modified` with the newly introduced conditional helper/summary files

*(Full Codex review extracted from `$env:TEMP/gsd-review-codex-4.md` lines 8261-8314 — second copy per memory convention.)*

---

## Reviewer Convergence & Divergence

### Strong Convergence (both reviewers flagged)

- **All 9 Round 1 concerns mechanically addressed** (D1/H1/H2/H3/U1/U2/U3/U4 unanimous RESOLVED; U5 mixed)
- **Plan 06 is still the highest-risk plan** (both: "most bisect-sensitive")
- **Plan 05 has HIGH-severity residual U5-adjacent issues** (complementary findings: Claude = routing fallback; Codex = precondition logic)
- **Frontmatter drift reappeared** for conditionally-created files (Plan 06 SUMMARY, Plan 05 routing table + crashgen lib.rs)
- **Plan 04 acceptance criterion completeness is the weakest** (both: version_registry rows under-enforced)
- **Test-quality patterns persist** in Plans 04 and 05 (both: `{} as Type` + `assert.ok(true)` are still no-op smoke)
- **PowerShell-vs-Bash consistency imperfect cross-plan** (both flagged as LOW)

### Divergent Final Recommendations

| Question | Claude | Codex |
|---|---|---|
| Should Phase 4 execute as-is? | **No — 5 targeted must-fixes first**, then ship; do NOT run Round 3 | **No — another revision cycle needed**; fix Plan 05 precondition blocker + 4 cleanup items |
| Must-fix count | 5 blockers + 4 should-fixes | 1 blocker (Plan 05 U5 precondition) + 4 cleanup items |
| Overall phase risk | MEDIUM | HIGH |
| Round 3 review needed? | No ("marginal return is low") | Not explicitly discussed but recommendation implies no |

**The recommendations are compatible in practice.** Both reviewers agree: (a) revise in a single `/gsd:plan-phase 4 --reviews` pass, (b) do not replan from scratch, (c) the must-fix list is roughly the same shape (Plan 06 frontmatter + Plan 05 routing + Plan 03/04 drift). Claude frames the remaining issues as "localized and executor-catchable"; Codex frames them as "structural enough that a pre-exec revision is needed." The delta is whether Plan 05's U5 precondition bug alone justifies HIGH phase risk (Codex) or whether the bundled set of fixes is a MEDIUM-risk revision (Claude).

**Net verdict:** Another `/gsd:plan-phase 4 --reviews` pass is warranted. The scope is targeted (5-9 fixes depending on which reviewer you follow) and the work is cleanup-class, not structural. Neither reviewer argued for Round 3 cross-AI review — both consider the marginal return too low.

---

## Recommended Action

**Phase 4 is BLOCKED on a targeted revision pass before execution.** The Round 1 revision was heroic — all 9 concerns resolved — but introduced enough new drift that a second cleanup pass is needed. **This pass should NOT trigger Round 3 cross-AI review** unless the cleanup itself surfaces a structural disagreement.

### Must-fix before `/gsd:execute-phase 4` (consensus of both reviewers)

1. **[PLAN 05 — HIGH]** Fix U5 dual-source precondition logic bug (Codex): Task 1 and Task 2 compare stale Plan 1 sizing counts against live post-Plan-4 counts for ALL owners. Restrict the comparison to the `aux` owner only (or owners NOT already reduced by Plans 2-4), OR sequence the comparison to run BEFORE Plans 2-4 write to the baseline.

2. **[PLAN 05 — HIGH]** Fail-closed Task 0 `writeAutoscanReport` routing (Claude): explicit escalate-to-checkpoint path if present in BOTH or NEITHER of scangame.rs / scanlog.rs. Remove the "document and proceed" ambiguity.

3. **[PLAN 06 — HIGH]** Add `parity-artifacts/node_api_surface.json` to `files_modified` and the Task 2 Step 10 `git add` command, OR document why it's absent (the other 6 mirrors ARE listed).

4. **[PLAN 06 — HIGH]** Clarify Phase 2b retry discipline: explicit split between transient-retry path and diagnostic-no-retry path. Remove ambiguity over which path an executor takes BEFORE retrying.

5. **[PLAN 06 — MEDIUM (upgrade to blocker)]** Replace Phase 2c.1 placeholder value `-1` with a fail-loud sentinel (`assert False, "COMPUTED_FLOOR placeholder — Phase 2c.1 must replace this"`). The `-1` placeholder is trivially true and can silently pass if the loop exits early.

6. **[PLAN 06 — MEDIUM]** Add `04-06-...-SUMMARY.md` to `files_modified` OR explicitly document that Plan 06's SUMMARY is created outside the atomic commit.

7. **[PLAN 05 — MEDIUM]** Add `_plan05_routing_table.json` and `classic-crashgen-settings-core/src/lib.rs` to `files_modified` where the tasks explicitly allow their creation/editing.

8. **[PLAN 04 — HIGH cleanup]** Add rustCrate acceptance check for the 4 version_registry rows (mirror the 3 PE rows' A3 enforcement pattern).

9. **[PLAN 04 — HIGH cleanup]** Remove "likely" language from Task 2 Step 6 rustSymbol specification. Add a pre-authoring grep step to lock the exact rustSymbol values from `classic-node/src/version_registry.rs` before row authoring.

10. **[PLAN 04 — MEDIUM]** Resolve cross-runtime coverage contradiction: either make the version_registry runtime test mandatory (matching the must-have) or remove the must-have's "both PE and checkCrashgen*" requirement.

11. **[PLAN 04 — MEDIUM]** Articulate the `migrateGameVersionSetting` handoff rationale: why does Plan 05 (aux) own a version_registry symbol?

12. **[PLAN 03 — HIGH cleanup]** Drop self-referential "This bullet REPLACES..." edit-history language in must_haves.truths bullet 8. State the current routing rule declaratively.

13. **[PLAN 03 — HIGH cleanup]** Fix `config.deferred` target drift: change `0 (or ≤2)` to `0`; remove stale "Plan 7" reference (route residuals to Plan 5 only).

14. **[PLAN 01 — MEDIUM]** Tighten H1 guard to reject blank strings and non-string container values, not just `None` — current implementation has exotic-value holes Codex flagged.

### Should-fix (non-blocking but worth the same revision pass)

- Plan 04 Task 2 signature pre-verification grep for `checkCrashgen*WithRules` (matches the D-07 rule)
- Plan 05 `assert.ok(true)` replacement with minimal shape assertion
- Plan 06 Step 2 line-number drift mitigation: replace hardcoded line numbers with grep-anchored semantic targets
- Plan 02 scanlog row count: commit to single value after reconciliation script runs, don't leave `(57, 58)` in acceptance
- Plan 01 U2 acceptance: tighten scanlog range to single expected value (66 after GLOBAL_FCX_HANDLER exclusion)
- Plan 04 + 05 real-shape assertions: replace `{} as Type` + `toBeDefined()` / `assert.ok(true)` with typed-field checks
- Cross-plan PowerShell sweep: remove residual `grep -q` / `test -f` / `-ge N` bash syntax from acceptance/verify blocks

### Can ship as-is with executor discretion (LOW severity)

- Plan 06 ripgrep regex PowerShell quoting quirks
- Plan 01 Task 3 `bun run build` `index.d.ts` accidental regeneration
- Plan 04 Task 2 Step 2 `Select-String` precision for `extractPeVersion`
- Plan 04 Task 1 Step 4 `rust_api_surface.json` schema assumption check
- Plan 03 `detectConfigDuplicates` signature pre-verification

---

## Next Steps

1. **Run `/gsd:plan-phase 4 --reviews`** to feed this REVIEWS.md back into the planner for a targeted cleanup pass incorporating the 14-item must-fix list.
2. After revision passes, re-run the internal plan-checker via the normal `/gsd:plan-phase` verification loop.
3. **Do NOT run Round 3 cross-AI review.** Both reviewers explicitly or implicitly discouraged it; the remaining issues are localized cleanup class, not structural.
4. After revision lands clean, proceed to `/gsd:execute-phase 4`.

**Raw review outputs preserved at:**
- `$env:TEMP/gsd-review-claude-4.md` (Claude, clean markdown, 22.9 KB / 124 lines)
- `$env:TEMP/gsd-review-codex-4.md` (Codex, full transcript; review content at lines 8261-8314)
- `$env:TEMP/gsd-review-prompt-4.md` (shared prompt; 475.6 KB, 5666 lines)
