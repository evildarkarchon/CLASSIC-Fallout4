---
phase: 4
reviewers: [claude, codex]
reviewed_at: 2026-04-09T00:00:00-07:00
review_round: 1
plans_reviewed:
  - 04-01-tooling-expansion-PLAN.md
  - 04-02-scanlog-promotion-PLAN.md
  - 04-03-config-promotion-PLAN.md
  - 04-04-version-registry-and-pe-version-PLAN.md
  - 04-05-aux-promotion-PLAN.md
  - 04-06-tier2-cleanup-cascade-PLAN.md
review_scope: "First-round review of all 6 Phase 4 plans (unshipped). Internal plan-checker had already run 2 revision iterations before external review. Both reviewers received the same ~412 KB prompt containing PROJECT.md, ROADMAP, REQUIREMENTS, CONTEXT.md (with Research Amendments A1–A7), RESEARCH.md, VALIDATION.md, all 6 PLAN.md files, and the Phase 3 Plan 09b SUMMARY.md precedent document. Plans 01 and 06 were pre-flagged as high-risk load-bearing for deeper scrutiny."
---

# Cross-AI Plan Review — Phase 4: Node Tier Collapse (Round 1)

> Independent peer review by Claude Opus 4.6 (separate CLI session) and Codex (GPT-5.4). This review ran AFTER the internal plan-checker had converged on a clean verdict through 2 revision iterations — so any issues surfaced here are things the internal checker missed. That makes this review load-bearing: the concerns flagged below represent the delta between "internally verified" and "adversarially stress-tested."

---

## Consensus Summary

**Both reviewers agree the plan set is structurally strong** — wave serialization is correct, all requirement IDs are covered, the two load-bearing plans are explicitly treated as such, and the Phase 3 precedent (M7 atomic cascade, `@rust`-suffix proxy pattern, `_stable_id_hash` discipline) is correctly adapted. Both also agree the remaining risk is not missing work, but **count/schema drift inside the plans themselves and one unresolved correctness question around Plan 04's Issue 9 fix.**

However, the two reviewers **directly contradict each other on whether dropping the `version-pe-shape` row is correct** — this divergence cannot be auto-resolved without user adjudication or an empirical test. It is the single most important finding of this review.

### Agreed Strengths (both reviewers)

- **Plan 01's bidirectional `validate_contract_surface()` guard** is correctly placed before any promotion plan runs; the `@rust`-suffix proxy handling is the right adaptation of Phase 3's Scenario E pattern.
- **Plan 01 Task 1 Step 0 pre-state enumeration** (`assert len(gb.RUST_TARGET_CRATES) == 10` before mutating) is excellent defensive practice — caught the Iteration-1 bug where the "9 new entries" list was wrong.
- **A1 crashgen-settings-core inclusion** is correctly propagated through `RUST_TARGET_CRATES` as 19 crates (not 18).
- **Plan 06 Task 2 BLOCKER Issue 1 fix** (single `bun run parity:gate:local` invocation, no standalone `generate_baseline.py --write-baseline` pre-call) is mechanically correct and matches Phase 3 Plan 09b's proven atomic pipeline.
- **Plan 06 Task 1 recursive ripgrep audit** (M8 discipline) with `Tier 2 Gaps` in the pattern is the right fix for prior cascade-audit blind spots.
- **Plan 04 Task 1 A6 sequencing** correctly splits `pub use is_valid_executable_path` into its own commit before the NAPI wrapper lands — bisect-clean.
- **Plan 03 Issue 4 reconciliation** via inline `<notes>` block cross-referencing Plan 5 as canonical owner of `JsModConflictEntry` is good cross-plan discipline.
- **`GLOBAL_FCX_HANDLER` handled in the same atomic cleanup working tree** as the rest of Plan 6 — right place for it.

### Agreed HIGH Concerns (both reviewers converged)

| # | Concern | Severity | Evidence |
|---|---------|:--:|---|
| **H1** | **Plan 01 `validate_contract_surface()` has logic holes** — Claude flagged that a row with neither `rustSymbol` nor `nodeExport` would silently pass (LOW severity). Codex flagged that a row with *missing* `rustSymbol` would also pass, and that any row with no `nodeExport` is treated as a proxy row regardless of `@rust` suffix, meaning a malformed normal row bypasses validation entirely (HIGH severity). The two converge at the structural level: the guard's current shape doesn't fail-closed on all malformed row shapes. | HIGH | Claude: "validate_contract_surface has no diagnostic for completely-empty rows"; Codex: "does not fail rows that are missing rustSymbol, and treats any row with no nodeExport as a proxy row" at Task 2 `behavior` bullets 2-4 and Step 2 pseudocode |
| **H2** | **Plan 03 count drift + crashgen crate ownership inconsistency** — Claude flagged the hard-coded crashgen_settings rust_crate set in Task 1 Step 3 helper as brittle. Codex flagged that Plan 03 still has stale "12 proxy / 23 normal / 35 total" text in the title, objective, Task 1 name, Step 1, and success_criteria despite the Iteration-1 Issue 4 fix that should have dropped it to 11 proxy / 23 normal / 34 total. Additionally, `must_haves.truths` bullet 8 says all new rows have `rustCrate: classic-config-core` while Task 1 Step 2/3 explicitly routes some proxy rows to `classic-crashgen-settings-core` — internal contradiction. | HIGH | Claude: Plan 3 Task 1 Step 3 helper script; Codex: Plan 3 title, objective, Task 1 name, Task 1 Step 1, `success_criteria`, plus `must_haves.truths` bullet 8 vs Task 1 Step 2/3 |
| **H3** | **Plan 06 `files_modified` frontmatter drift** — Claude flagged that Step 11 `git add` example includes `parity-artifacts/parity_contract.{json,md}` but the frontmatter `files_modified` omits them. Codex additionally flagged that `files_modified` omits `.planning/STATE.md` and `.planning/ROADMAP.md` which Task 3 Steps 4-6 explicitly edit. Either the commit will fail on pathspec (if paths don't exist) OR the frontmatter is incomplete and pre-commit hooks / parity-artifacts detection may reject stray files. | HIGH | Claude: Plan 06 lines 19-25 frontmatter vs Task 2 Step 11 git add example; Codex: Plan 06 frontmatter vs Task 2 Step 10 + Task 3 Steps 4-6 |

### Divergent View — RESOLVED 2026-04-09

| # | Concern | Claude's Position | Codex's Position | Resolution |
|---|---------|-------------------|------------------|------------|
| **D1 (BLOCKER → RESOLVED)** | **Plan 04 Issue 9 `version-pe-shape` row drop** — Is dropping the `version-pe-shape` row with `rustSymbol: "PeVersionResult"` correct, or does it orphan `JsPeVersion` as a new deferred backlog entry? | **HIGH BLOCKER — restore the row.** `parse_rust_surface()` parses `pub type` declarations; `classic-version-core/src/lib.rs` line 43 already re-exports `PeVersionResult`, so the bidirectional guard would accept the contract row. Without the row, `JsPeVersion` becomes an orphaned Node surface entry → new deferred entry → Plan 04's plan-local invariant fails. | **Technically correct — keep it dropped.** "The JsPeVersion shape is already carried by `extractPeVersion(...): JsPeVersion` in `index.d.ts`." | **✅ Claude is correct. `version-pe-shape` row MUST be restored.** Adjudicated via read-only empirical probe 2026-04-09. See §"D1 Adjudication" below for the empirical chain of evidence. |

### D1 Adjudication (Empirical Probe — 2026-04-09)

Rather than mutating `index.d.ts` on a scratch branch and running `--write-baseline` (which would overwrite committed baseline files), the probe was conducted read-only by examining `parse_node_surface()` directly, cross-referencing existing interfaces in the committed baselines, and checking the deferred backlog for precedent.

**Chain of evidence (all read-only, no files modified):**

1. **`parse_node_surface()` emits standalone entries for every `export interface`**, independent of any function that returns them. Source: `tools/node_api_parity/generate_baseline.py` line 301 (`interface_re = re.compile(r"^export\s+interface\s+([A-Za-z0-9_]+)")`); every match is appended to `exports` with `kind: "interface"` and deduplicated by `(name, kind)` tuple.

2. **The committed `node_api_surface.json` has 68 `kind: "interface"` entries** across 306 total exports. Interfaces routinely get their own slots in the surface.

3. **`Fallout4VersionInfo` (an existing `export interface` at `index.d.ts:1686`) IS tracked as a tier1Mapping row** with the exact shape Claude said to use for `JsPeVersion`:
   - `id: "version-registry-promote-fallout4-version-info"`
   - `rustSymbol: "VersionInfo"` (a Rust struct)
   - `nodeExport: "Fallout4VersionInfo"`
   - `nodeKind: "interface"`

4. **`node_api_surface.json` is 23 days stale** (mtime 2026-03-16 vs `index.d.ts` mtime 2026-04-09). 7 interfaces exist in the current `index.d.ts` but are absent from the baseline surface file: `HashCacheStats`, `JsFcxConfigIssue`, `JsModSolutionCriteria`, `JsModSolutionEntry`, `JsSuspectErrorRule`, `JsSuspectStackCountRule`, `JsSuspectStackRule`. Plan 04's `bun run parity:gate:local` will regenerate the surface and these will land.

5. **`node-deferred-aux-108` exists in `deferred_runtime_backlog.json`** with the following shape:
   ```
   classification: "deferred"
   tier: "tier2"
   ownerModule: "aux"
   deferReason: "Node export is outside Tier-1 mapping scope (deferred)."
   bindingIdentifiers: [
     "JsModSolutionCriteria",
     "JsModSolutionEntry",
     "JsSuspectErrorRule",
     "JsSuspectStackCountRule",
     "JsSuspectStackRule"
   ]
   rustSymbols: []
   ```
   **This empirically proves that interfaces without tier1Mappings rows ARE tracked as deferred backlog entries.** 5 of the 7 "missing from surface" interfaces are already bundled into this deferred entry, contributing to the `deferred_total` count that Phase 4 must drive to 0.

6. **`classic-version-core/src/lib.rs:43` contains `pub use pe_version::{PeVersionError, PeVersionResult, extract_pe_version};`** — confirmed via direct grep. `PeVersionResult` IS on the Rust public surface. The contract row `version-pe-shape` with `rustSymbol: "PeVersionResult"` would be validated by `parse_rust_surface()` picking up the re-export.

**Verdict:**

When Plan 4 adds `export interface JsPeVersion { major, minor, patch, build }` to `index.d.ts` and runs `bun run parity:gate:local`:

a. `parse_node_surface()` emits a standalone `{ export: "JsPeVersion", kind: "interface" }` entry (inevitable per findings 1–3).
b. Without a corresponding `tier1Mappings` row, `JsPeVersion` is classified `tier=tier2`, `classification=deferred` (empirically proven by `node-deferred-aux-108` precedent in finding 5).
c. `deferred_total` increases by 1 (JsPeVersion becomes a new deferred binding identifier).
d. Plan 4's plan-local invariant fails — it was supposed to decrease `deferred_total` by the exact row count it adds, but instead adds N rows while creating 1 new deferred entry → net change is N−1, not N.

**Codex's "implicit coverage via typed return" claim is mechanically wrong.** The tooling does NOT subsume interfaces into the functions that return them — each interface gets its own standalone entry, and each entry needs its own tier1 treatment.

**Claude's chain of reasoning is empirically verified.** The `version-pe-shape` contract row MUST be restored with the normal tier1 mapping shape (following the `Fallout4VersionInfo` precedent):

```json
{
  "id": "version-pe-shape",
  "rustSymbol": "PeVersionResult",
  "nodeExport": "JsPeVersion",
  "nodeKind": "interface",
  "rustCrate": "classic-version-core"
}
```

**Plan 04 row count reverts from 6 → 7** (2 PE function rows + 1 PE shape row + 4 version_registry rows = 7). All 9 of the iteration-1 Issue 9 "7→6" edits in Plan 04 (lines 34, 38, 56, 82, 307, 311, 530, 567, 576, 610, 617) need to be REVERTED in the next revision pass. The iteration-1 plan-checker's reasoning for Issue 9 was mechanically wrong — it conflated `PeVersionResult` (a type alias that `parse_rust_surface()` DOES parse via the `pub type` regex) with "covered implicitly" (which the tooling doesn't do). Three internal passes agreed on a bug; only cross-AI review (specifically Claude's empirical chain of reasoning) caught it. This is exactly the class of bug the `feedback_review_before_execute_encoded_logic` memory was written for.

### Unique HIGH Concerns (flagged by one reviewer only)

| # | Reviewer | Concern | Severity | Plan / File | Notes |
|---|----------|---------|:--:|---|---|
| **U1** | Codex | **Plan 04 A6 `pub use is_valid_executable_path` is a cross-binding regression risk.** Adding this symbol to `classic-version-core`'s public Rust surface affects ALL binding parity gates, not just Node. Python's Phase 3 parity gate also reads this crate's surface. If Python doesn't already have a binding for `is_valid_executable_path` (i.e., Phase 3 didn't already expose it), Phase 4 would silently introduce a new `gap_type=rust_unmapped` row into Python's now-closed deferred_total, potentially regressing Phase 3's shipped state. | HIGH | 04-04 Task 1 action Steps 2-5 | **Claude did not raise this.** This is the kind of cross-phase contamination that's easy to miss when reviewing a single phase in isolation. |
| **U2** | Codex | **Plan 01 A10 sizing report is derived from the wrong source.** The plan reads `runtime_coverage_summary.json` and models the 101-vs-109 reconciliation as "entries in the summary but not in backlog::entries[]". That's the wrong model — the 109 comes from tracked-surface expansion INSIDE the same backlog entries (sum of `bindingIdentifiers + rustSymbols` per entry), not "8 extra entries." If the A10 report reads coverage summary + deferred counts instead of the live diff inventory (`parity_diff_report.json::gaps`), it will miss newly surfaced residuals from the 10→19 crate expansion. Plan 05 (which sources its residual set from `04-01-A10-sizing.json`) then inherits the gap. | HIGH | 04-01 Task 3 action Step 2 and Step 2.6; 04-05 depends on 04-01 output | This is the same "wrong numerator source" trap Phase 3 Plan 09a fell into (surfaced 593 unexpected residuals). Phase 4 is supposed to front-load sizing to avoid this — if the sizing script reads the wrong source, front-loading doesn't help. |
| **U3** | Claude | **Plan 06 Task 2 Step 5 chicken-and-egg with `test_tier1_contract_total_baseline_floor`.** The step says: "If the test must be authored BEFORE Phase 2b, use a placeholder `<COMPUTED_FLOOR>` and fill it in after running Phase 2b once, then re-run." That violates the Phase 2a→2b→2c→2d single-atomic-pipeline discipline. In practice the flow becomes: edit placeholder → run parity:gate:local → read tier1Mappings count → edit test file (NEW source edit) → run pytest → stage+commit. Step 4 is a source edit post-Phase-2b that isn't re-verified by the single pipeline. If pytest fails, the fix re-enters Phase 2a and restarts the entire pipeline — but the plan doesn't describe this loop. | HIGH | 04-06 Task 2 Step 5 | **Codex did not raise this** — Codex focused on success-criterion drift and frontmatter misalignment instead. |
| **U4** | Codex | **Plan 06 success_criteria item 5 vs objective/Task 2 Step 4 contradiction.** Plan 06 claims Phase 4 closes with "no references to Tier-2 governance files", but Task 2 explicitly preserves `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` with `entries: []` for Phase 6 deletion. Those statements cannot both be true. | HIGH | 04-06 success_criteria item 5 vs objective / Task 2 Step 4 | **Claude did not raise this.** Worth fixing the success criterion text to reflect the actual Phase 4 scope: "no Tier-2 *semantics* remain in generated baselines; governance backlog file preserved but emptied until Phase 6 deletion." |
| **U5** | Codex | **Plan 05 is most exposed to hidden residuals.** If Plan 01's A10 sizing report is incomplete (per U2), Plan 05 can finish "green" while leaving real residuals that Plan 06 then has to absorb — but Plan 06 is a cleanup plan, not a promotion plan, so it can't author new rows. Result: Phase 4 closes with `deferred_total > 0` and the gate is NOT green. | HIGH | 04-05 objective + Task 2 action Steps 1-2 (reads `04-01-A10-sizing.json`) | **Claude did not raise this directly** but Claude's "hardcoded len == 19" concern is adjacent (if there are more than 19 crates after sizing, both reviewers' concerns converge). |

### Agreed MEDIUM Concerns

- **Plan 02 test smoke coverage is too weak.** Both reviewers: `{} as Type` + `expect(...).toBeDefined()` patterns are nearly no-ops. Claude additionally flagged that the Task 2 acceptance criterion `print(f'scanlog normal rows: {len(rows)}')` doesn't `assert` — it only prints, so the acceptance check passes regardless of count.
- **Plans 02, 03, 05 omit `pub use` / `lib.rs` files from `files_modified`** even when the action text explicitly allows the executor to add a new `pub use` re-export if the bidirectional guard demands one. This is a frontmatter honesty gap.

### Agreed LOW Concerns

- **PowerShell-preferred plans still use `grep -q` / `test -f` / `wc` in acceptance criteria.** Both reviewers flagged this as Windows-execution friction. Plans 01, 04, 06 all mix shell checks into PowerShell-preferred contexts.

---

## Divergent Findings (unique perspective from one reviewer)

### Unique from Claude

- **[HIGH] Plan 04 Issue 9 (see D1 above).** Already covered in Divergent Views.
- **[MEDIUM] Plan 02 Task 2 acceptance criterion is non-enforcing.** Uses `print(...)` rather than `assert` — check passes regardless of count.
- **[MEDIUM] Plan 04 Task 2 Step 4 uses pseudo-signatures for `checkCrashgen*WithRules` tests** without pre-test signature verification. If the real signature differs, tests `TypeError` at runtime.
- **[MEDIUM] Plan 05 `setApplicationDir` / `getApplicationDir` roundtrip test mutates process-wide state** guarded by an `Once` initializer. Test either fails (Once already initialized) or permanently mutates state (downstream flakiness).
- **[MEDIUM] Plan 06 Task 2 Step 2 markdown column edit at two locations** (header line + cell expression) is described as a single edit. If only one is deleted, the markdown table becomes malformed.
- **[MEDIUM] Plan 06 Task 2 Step 6 retry discipline wording is ambiguous** — "ONCE" clashes with "retries (plural)."
- **[MEDIUM] Plan 06 floor calculation example math is stale** — Plan 06 Step 5 says "expect ~372" but with Issue 4 (34 not 35) and Issue 9 (6 not 7), the actual expected sum is 382. (Note: Claude's math assumes Issue 9 is fixed per Claude's own HIGH blocker; Codex disputes this.)
- **[MEDIUM] Plan 04 acceptance criteria omit the `rustCrate` field check** for the 6 new rows, breaking parity with Plans 02/03/05 which DO enforce `rustCrate` on new rows (A3).
- **[MEDIUM] Plan 01 Task 1 hard-coded `assert len(gb.RUST_TARGET_CRATES) == 19`** is brittle vs. `>= 19` — blocks Plan 5 residual absorption if A10 surfaces a 20th crate.
- **[MEDIUM] Plan 01 Task 2 acceptance criteria include a manual "inject bad row" verification step** that isn't automated and risks the executor forgetting to revert.
- **[LOW] Plan 03 Task 1 hard-coded crashgen_settings set drops `ModConflictEntry` twice** (once at loop top via Issue 4 continue; once via set membership). Works today but fragile.
- **[LOW] Plan 06 Task 1 ripgrep regex `tierDefinitions\.?tier2` doesn't match bracket syntax** `tierDefinitions["tier2"]` or `tierDefinitions['tier2']`.
- **[LOW] Plans 02/03 smoke tests use shallow `toBeDefined()` assertions** — borderline no-ops per D-TEST-02.
- **[LOW] Plan 02 Task 2 Step 5 `parseXseLog("")` lacks try/catch** — will throw and fail node:test if empty input isn't parseable.
- **[LOW] Plan 03 Task 2 Step 5 `resetHashCacheStats + getHashCacheStats` test has implicit ordering assumption** — cache could be populated between reset and read if Bun parallelizes describe blocks.

### Unique from Codex

- **[HIGH] Plan 04 A6 cross-binding regression risk (see U1 above).** Already covered in Unique HIGHs.
- **[HIGH] Plan 01 A10 sizing wrong source (see U2 above).** Already covered in Unique HIGHs.
- **[HIGH] Plan 05 exposure to hidden residuals (see U5 above).** Already covered in Unique HIGHs.
- **[HIGH] Plan 06 success criterion contradiction (see U4 above).** Already covered in Unique HIGHs.
- **[MEDIUM] Plan 01 owner selection allows "default to aux if no match" fallback** for `classic-crashgen-settings-core` — weaker than A5's "19 distinct owners" intent.
- **[MEDIUM] Plan 02 `must_haves.truths` bullet 4 says "No Rust source code changes"** but Step 5 explicitly allows adding `pub use` at `classic-scanlog-core/src/lib.rs`. `files_modified` doesn't include it.
- **[MEDIUM] Plan 04 `migrateGameVersionSetting` unresolved note** — if it's a real fifth row, it needs explicit handoff to Plan 5 or formal exclusion.
- **[MEDIUM] Plan 05 cross-owner overlap routing is "likely" for 5 candidates** — too loose for a late-wave residual plan.
- **[MEDIUM] Plan 06 Task 3 reruns `bun run parity:gate:local` after the atomic cleanup commit** — not incorrect but weakens the "single pipeline, single refresh" discipline and can cause mirror churn.
- **[LOW] Plan 05 Task 1 Step 8 `assert.ok(true)` for interface coverage** is not meaningful smoke coverage.

---

## Full Review — Claude

**Reviewer:** Claude Opus 4.6 (separate CLI session via `claude -p` with stdin pipe)
**Output size:** 22.7 KB, 100 lines

### Summary
Plans 01 and 06 are mostly well-structured and absorb the hard-learned lessons from Phase 3 (M7 atomic cascade, bidirectional guard, `_stable_id_hash` discipline, recursive cascade audit). The internal check loop has clearly done useful work — Issue 1/3/4/9 fixes are visible throughout. However, I found one HIGH-severity correctness bug in Plan 4 (Issue 9's reasoning is mechanically wrong and will leave `JsPeVersion` as an orphaned export), one HIGH-severity inconsistency between Plan 06's `files_modified` frontmatter and its Step 11 git add example, and several MEDIUM concerns around count ambiguities, test isolation, and placeholder-resolution ordering. Plans 02, 03, 05 are largely sound promotion mechanics copied from Phase 3's proven pattern. I'd ship Plan 01 with minor tightening, ship Plans 02/03/05 after executor discretion on acceptance-count tolerance, and block Plans 04 and 06 pending fixes to the issues flagged below.

### Risk Assessment
| Plan | Risk | Justification |
|------|------|---------------|
| 04-01 Tooling Expansion | LOW-MEDIUM | Bidirectional guard is well-designed; test scaffold is TDD-correct; Step 0 pre-state check is excellent. Main concerns are soft. Ship with minor tightening. |
| 04-02 Scanlog Promotion | MEDIUM | Uses proven Phase 3 Scenario E pattern. Count ambiguity (57 vs 58) should be locked before execution. Non-enforcing `print(...)` acceptance criterion is a ship-blocker. |
| 04-03 Config Promotion | MEDIUM | Issue 4 handled well in prose but hard-coded crashgen_settings set is brittle. Ship after helper refactor. |
| 04-04 Version Registry + PE-Version | **HIGH (BLOCKED)** | Issue 9 reasoning is mechanically wrong — will orphan `JsPeVersion`. Do not ship until restored OR explicitly covered via selector. |
| 04-05 Aux Promotion | MEDIUM | Residual absorption deferred to execution-time A10. `setApplicationDir` roundtrip test has state-mutation concerns. |
| 04-06 Tier-2 Cleanup Cascade | **HIGH (BLOCKED)** | Core M7 discipline and Issue 1 fix correct. But: frontmatter vs git add example inconsistency; Step 5 placeholder resolution disrupts single-pipeline; markdown column edit risks malformed output. Do not ship. |

*(Full Claude review preserved at `$env:TEMP/gsd-review-claude-4.md` if raw text is needed.)*

---

## Full Review — Codex

**Reviewer:** Codex (GPT-5.4 via `codex exec --skip-git-repo-check` with stdin pipe)
**Output size:** 441 KB transcript (includes tool-call exec blocks from Codex's own investigation); review content extracted from the second-copy final summary
**Token usage:** 143,733 tokens

### Summary
The plan set is structurally strong: the wave chain is strictly sequential (`04-01 → 04-02 → 04-03 → 04-04 → 04-05 → 04-06`), all required IDs appear in at least one `requirements_addressed` field, and the two load-bearing plans are explicitly treated as such. The main remaining risk is not missing work, but count/schema drift inside the plans themselves. Plan 01 still has a real logic hole in `validate_contract_surface()` and an A10 sizing design that is not strong enough to budget residuals created by the 10→19 crate expansion. Plan 06 is much better than the typical cleanup plan, but it still has a goal/backward mismatch: it promises "no references to Tier-2 governance files" while explicitly preserving the empty backlog file for Phase 6.

### Risk Assessment
| Plan | Risk | Justification |
|------|------|---------------|
| 04-01 Tooling Expansion | **HIGH** | Encodes the two load-bearing algorithms for the phase. If guard or sizing logic is wrong, every downstream plan can be "green" while still missing rows. |
| 04-02 Scanlog Promotion | MEDIUM | Structure is fine, but unresolved 57/58 and 8/9 ranges make it too easy to land the wrong total and still call the plan done. |
| 04-03 Config Promotion | **HIGH** | Still contains enough internal count/crate drift to cause the executor to implement the wrong target set. |
| 04-04 Version Registry + PE-Version | MEDIUM | Node-side implementation is solid, but the shared-Rust-surface A6 change is a real cross-binding regression risk unless explicitly checked. |
| 04-05 Aux Promotion | **HIGH** | Most exposed to hidden residuals. If Plan 01's sizing is incomplete, Plan 05 can finish "green" while leaving real gaps for Plan 06. |
| 04-06 Tier-2 Cleanup Cascade | **HIGH** | Cleanup algorithm itself is now mostly correct, but this is still the most bisect-sensitive plan in the phase, and it still contains plan-vs-goal and frontmatter-vs-action drift. |

*(Full Codex review extracted from `$env:TEMP/gsd-review-codex-4.md` lines 5300–5429 — second copy per memory convention, preserved in that temp file if raw text is needed.)*

---

## Recommended Action

**Plan 4 is BLOCKED on the D1 divergence.** Do NOT execute Phase 4 until D1 is adjudicated via the probe described above. If the probe confirms Claude's analysis, the `version-pe-shape` row MUST be restored and Plan 04 re-enters the revision loop.

**Independently, the following HIGH concerns need targeted revisions (via `/gsd:plan-phase 4 --reviews`):**

1. **H1 — Plan 01 `validate_contract_surface()` fail-closed hardening.** Add explicit diagnostics for: (a) missing `rustSymbol` on any row, (b) missing `nodeExport` on non-`@rust` rows, (c) empty rows (neither field present). Only `rustSymbol.endswith("@rust")` should skip the Node-side check.
2. **H2 — Plan 03 count drift sweep.** Normalize every count in Plan 03 (title, objective, Task 1 name, Task 1 Step 1, success_criteria, must_haves.truths) to the post-Issue-4 total: `11 proxy + 23 normal = 34`. Fix the crate ownership contradiction between `must_haves.truths` bullet 8 and Task 1 Step 2/3. Replace the hard-coded crashgen_settings set with a `rust_api_surface.json` lookup.
3. **H3 — Plan 06 frontmatter reconciliation.** Add `parity-artifacts/parity_contract.{json,md}`, `.planning/STATE.md`, `.planning/ROADMAP.md` to `files_modified` OR document why they're staged outside the declared set. Probe via `git status --porcelain` before staging.
4. **U1 — Plan 04 A6 cross-binding regression probe.** Before Plan 4 executes, verify Python's shipped parity gate against `classic-version-core` with the `is_valid_executable_path` re-export added. If Python's gate fires a new `gap_type=rust_unmapped` row, Plan 04 Task 1 must include a companion Python binding addition OR the re-export must be narrower (e.g., `pub use` under a feature gate).
5. **U2 — Plan 01 A10 sizing source fix.** Redefine A10 as a merged report from `parity_diff_report.json::gaps` (the live diff inventory) PLUS `runtime_coverage_summary.json` (for validation/cross-reference), with per-owner row inventories. Currently the plan reads only the coverage summary, which misses newly-surfaced residuals from the 10→19 crate expansion.
6. **U3 — Plan 06 Task 2 Step 5 test floor re-sequencing.** Move placeholder resolution + pytest rerun explicitly into a new Phase 2c.1 sub-step. State explicitly that if pytest fails, the working tree stays uncommitted and the executor iterates the entire atomic cycle.
7. **U4 — Plan 06 success criterion rewording.** Change success criterion 5 from "no references to Tier-2 governance files" to "no Tier-2 semantics remain in generated baselines; governance backlog file preserved but emptied until Phase 6 deletion." This reflects the actual Phase 4 scope boundary with Phase 6.
8. **U5 — Plan 05 dual-source residual check.** Make Task 2 start from BOTH `04-01-A10-sizing.json` AND live `parity_diff_report.json`; fail if they disagree. Lock the cross-owner overlap routing table BEFORE execution (no "likely" language).

**Plus all agreed MEDIUM concerns (test smoke coverage strengthening, `files_modified` honesty across Plans 02/03/05).**

---

## Next Steps

1. **Adjudicate D1 via empirical probe** (recommended command sequence documented above). This decides whether Plan 04 Issue 9 rollback is needed.
2. **Run `/gsd:plan-phase 4 --reviews`** to feed this REVIEWS.md back into the planner for targeted revision incorporating all HIGH concerns.
3. After revision passes, re-run the internal plan-checker via the normal `/gsd:plan-phase` verification loop.
4. If a second round of cross-AI review is warranted (D1 is still contested), run `/gsd:review --phase 4 --claude --codex` again — the new REVIEWS.md will auto-number as Round 2 and supersede this one.

**Raw review outputs preserved at:**
- `$env:TEMP/gsd-review-claude-4.md` (Claude, clean markdown)
- `$env:TEMP/gsd-review-codex-4.md` (Codex, full transcript; review content at lines 5300–5429)
- `$env:TEMP/gsd-review-prompt-4.md` (shared prompt; 411.7 KB, 5153 lines)
